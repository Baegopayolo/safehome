import os
import secrets
from contextlib import closing
import sys
import sqlite3
import subprocess
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'backend'))
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dashboard import build_dashboard, register_dashboard
from rental_collector import (CollectionError, collect_scope, fetch_month, make_session,
                              months_for, normalize, utcnow)
from dashboard_ops import collection_lock
from utils import SEOUL_SIGUNGU_CODES

TODAY = date(2026,11,5)
MONTH = '202610'


def fields(**changes):
    value = dict(dealYear='2026',dealMonth='10',dealDay='1',deposit='50,000',monthlyRent='0',
        excluUseAr='84.90',sggCd='11110',aptNm='테스트',umdNm='사직동',floor='5',cdealType='',cdealDay='')
    value.update(changes)
    return value


def response(records=(), total=None, page=1, code='000'):
    xml = ''.join('<item>'+''.join(f'<{k}>{escape(v)}</{k}>' for k,v in row.items())+'</item>' for row in records)
    total = len(records) if total is None else total
    return Mock(content=(f'<response><header><resultCode>{code}</resultCode></header>'
        f'<body><pageNo>{page}</pageNo><totalCount>{total}</totalCount><items>{xml}</items></body></response>').encode())


class CollectorTests(unittest.TestCase):
    def test_month_boundary(self):
        self.assertEqual(months_for(date(2026,1,1))[0],'202502')
        self.assertEqual(months_for(TODAY)[-1],'202611')

    def test_pages_duplicates_rent_and_cancellation(self):
        session = Mock()
        session.get.side_effect = [response([fields(),fields(),fields(floor='6')],5),
            response([fields(floor='6',cdealType='O'),fields(monthlyRent='50')],5,2)]
        records,total = fetch_month('11110',MONTH,'secret',TODAY,session)
        self.assertEqual(total,5)
        self.assertEqual(len(records),2)
        self.assertEqual(sum(not r['cancelled'] for r in records),1)
        self.assertEqual(session.get.call_args.kwargs['params']['pageNo'],2)
        self.assertEqual(session.get.call_args.kwargs['timeout'],(5,20))

    def test_normalizes_numbers_and_preserves_distinct_floors(self):
        a = normalize(fields(), '11110',MONTH,TODAY)
        b = normalize(fields(deposit='50000',excluUseAr='84.9000',dealDay='01'), '11110',MONTH,TODAY)
        self.assertEqual(a['fingerprint'],b['fingerprint'])
        self.assertNotEqual(a['fingerprint'],normalize(fields(floor='6'),'11110',MONTH,TODAY)['fingerprint'])

    def test_validation(self):
        for change in [dict(monthlyRent=''),dict(deposit='0'),dict(excluUseAr='NaN'),dict(dealDay='32'),
                       dict(sggCd='99999'),dict(dealMonth='9'),dict(cdealType='unknown')]:
            with self.subTest(change=change), self.assertRaises(CollectionError):
                normalize(fields(**change),'11110',MONTH,TODAY)

    def test_incomplete_error_changed_and_repeated_pages(self):
        for responses in [[response(code='30')],[response(total=1)],
            [response([fields()],2),response([fields(floor='6')],3,2)],
            [response([fields()],2),response([fields()],2,2)],
            [response([fields()],2),response([fields(floor='6')],2,1)]]:
            with self.subTest(responses=responses), self.assertRaises(CollectionError):
                fetch_month('11110',MONTH,'key',TODAY,Mock(get=Mock(side_effect=responses)))

    def test_empty_success_and_missing_key(self):
        self.assertEqual(fetch_month('11110',MONTH,'key',TODAY,Mock(get=Mock(return_value=response()))),([],0))
        with self.assertRaisesRegex(CollectionError,'MISSING_API_KEY'):
            fetch_month('11110',MONTH,'',TODAY)

    def test_retry_configuration(self):
        session = make_session()
        retry = session.get_adapter('https://').max_retries
        self.assertEqual(retry.total,3)
        self.assertIn(429,retry.status_forcelist)
        self.assertIn(503,retry.status_forcelist)
        session.close()

    def test_network_error_is_redacted(self):
        import requests
        with self.assertRaisesRegex(CollectionError,'NETWORK_OR_HTTP_ERROR') as cm:
            fetch_month('11110',MONTH,'secret',TODAY,Mock(get=Mock(side_effect=requests.Timeout('serviceKey=secret'))))
        self.assertNotIn('secret',str(cm.exception))


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True,SQLALCHEMY_DATABASE_URI='sqlite://')
        self.db = SQLAlchemy(self.app)
        self.models = register_dashboard(self.app,self.db)
        self.Region,self.Tx,self.Stat,self.Log = self.models
        self.context = self.app.app_context(); self.context.push()
        self.db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        self.db.session.remove(); self.db.drop_all(); self.db.engine.dispose(); self.context.pop()

    def collect(self, records=None, region='11110', month=MONTH, fail=False):
        records = records if records is not None else [normalize(fields(),'11110',MONTH,TODAY)]
        fetch = Mock(side_effect=CollectionError('NETWORK_OR_HTTP_ERROR')) if fail else Mock(return_value=(records,len(records)))
        return collect_scope(self.db,self.models,region,month,'key',TODAY,fetch)

    def payload(self, **kw):
        return build_dashboard(self.db,self.models,today=TODAY,**kw)

    def test_no_collection_and_successful_zero_distinct(self):
        self.assertEqual(self.payload()['status'],'unavailable')
        self.assertIsNone(self.payload()['summary']['transaction_count'])
        self.collect([])
        p = self.payload()
        self.assertEqual(p['status'],'partial')
        self.assertEqual(p['summary']['transaction_count'],0)
        self.assertEqual(p['coverage']['completed'],1)
        self.assertEqual(len(p['coverage']['missing']),299)

    def test_idempotence_cancellation_corrections_and_atomic_failure(self):
        self.collect();self.collect()
        self.assertEqual(self.Tx.query.count(),1)
        self.assertEqual(self.Stat.query.count(),1)
        stamp = self.Stat.query.one().calculated_at
        self.assertFalse(self.collect(fail=True))
        self.assertEqual(self.Tx.query.count(),1)
        self.assertEqual(self.Stat.query.one().calculated_at,stamp)
        self.assertEqual(self.Log.query.order_by(self.Log.id.desc()).first().status,'failed')
        corrected = normalize(fields(deposit='60000'),'11110',MONTH,TODAY)
        self.collect([corrected])
        self.assertEqual(self.Tx.query.one().deposit,60000)
        corrected['cancelled'] = True
        self.collect([corrected])
        self.assertEqual(self.payload()['summary']['transaction_count'],0)
        self.collect([])
        self.assertEqual(self.Tx.query.count(),0)

    def test_storage_failure_rolls_back_replacement(self):
        self.collect()
        broken = normalize(fields(),'11110',MONTH,TODAY)
        broken['deposit'] = -1
        self.assertFalse(self.collect([broken]))
        self.assertEqual(self.Tx.query.one().deposit,50000)
        self.assertEqual(self.Stat.query.one().transaction_count,1)

    def test_region_month_and_total_match(self):
        self.collect()
        self.collect([normalize(fields(sggCd='11680'),'11680',MONTH,TODAY)],region='11680')
        p=self.payload()
        self.assertEqual(p['summary']['transaction_count'],2)
        self.assertEqual(sum(r['transaction_count'] or 0 for r in p['regions']),2)
        self.assertEqual(sum(r['transaction_count'] or 0 for r in p['trends']),2)
        self.assertEqual(p['summary']['region_count'],2)

    def test_full_coverage_freshness_and_failed_refresh(self):
        stamp=utcnow()
        for name,code in SEOUL_SIGUNGU_CODES.items():
            self.db.session.add(self.Region(code=code,name=name))
            for month in months_for(TODAY):
                self.db.session.add(self.Stat(region_code=code,deal_month=month,transaction_count=0,source_count=0,calculated_at=stamp))
        self.db.session.commit()
        self.assertEqual(self.payload(now=stamp)['status'],'complete')
        self.assertEqual(self.payload(now=stamp+timedelta(days=9))['status'],'stale')
        self.collect(fail=True)
        self.assertEqual(self.payload()['status'],'partial')
        self.assertEqual(self.payload()['coverage']['completed'],300)

    def test_four_endpoints_and_no_network_on_reads(self):
        self.collect()
        with patch('requests.Session.get',side_effect=AssertionError('No network')):
            for path in ('summary','regions','trends','data-status'):
                r=self.client.get('/api/dashboard/'+path)
                self.assertEqual(r.status_code,200)
                self.assertIn('source',r.json);self.assertIn('period',r.json)
                self.assertIn('last_updated',r.json);self.assertIn('coverage',r.json)
                self.assertEqual(r.headers['Cache-Control'],'no-store')

    def test_query_error_is_503_not_zero(self):
        self.db.drop_all()
        with self.assertLogs(self.app.logger,level='ERROR'):
            r=self.client.get('/api/dashboard/summary')
        self.assertEqual(r.status_code,503)
        self.assertEqual(r.json['status'],'unavailable')
        self.assertNotIn('summary',r.json)

    def test_cached_count_corruption_rejected(self):
        self.collect()
        self.Stat.query.one().transaction_count=123
        self.db.session.commit()
        with self.assertLogs(self.app.logger,level='ERROR'):
            r=self.client.get('/api/dashboard/summary')
        self.assertEqual(r.status_code,503)

    def test_database_duplicate_constraint(self):
        from sqlalchemy.exc import IntegrityError
        self.collect()
        tx=normalize(fields(),'11110',MONTH,TODAY)
        self.db.session.add(self.Tx(region_code='11110',deal_month=MONTH,collected_at=utcnow(),**tx))
        with self.assertRaises(IntegrityError): self.db.session.commit()
        self.db.session.rollback()

    def test_collection_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            with collection_lock(str(Path(directory)/'lock')):
                with self.assertRaises(Exception):
                    with collection_lock(str(Path(directory)/'lock')): pass


class PostgresBackupTests(unittest.TestCase):
    def test_credentials_only_in_child_environment(self):
        from sqlalchemy.engine import make_url
        from dashboard_ops import postgres_backup
        url=make_url('postgresql://testuser:private-password@db.example/testdb?sslmode=require')
        with patch('dashboard_ops.shutil.which',return_value='/usr/bin/tool'), patch('dashboard_ops.subprocess.run',return_value=Mock(returncode=0)) as run:
            postgres_backup(url,Path('backup.dump.partial'))
        first=run.call_args_list[0]
        self.assertNotIn('private-password',str(first.args))
        self.assertEqual(first.kwargs['env']['PGPASSWORD'],'private-password')
        self.assertEqual(first.kwargs['env']['PGSSLMODE'],'require')
        self.assertEqual(run.call_args_list[1].args[0][0],'pg_restore')

    def test_failure_does_not_expose_upstream_error(self):
        from sqlalchemy.engine import make_url
        from dashboard_ops import postgres_backup
        import click
        with patch('dashboard_ops.shutil.which',return_value='/usr/bin/tool'), patch('dashboard_ops.subprocess.run',return_value=Mock(returncode=1,stderr='private-password')):
            with self.assertRaises(click.ClickException) as result:
                postgres_backup(make_url('postgresql://user:private-password@db.example/db'),Path('backup.dump.partial'))
        self.assertNotIn('private-password',str(result.exception))


class SecretKeyTests(unittest.TestCase):
    def start_app(self, key):
        env = {**os.environ, 'DATABASE_URL': 'sqlite://', 'PYTHONDONTWRITEBYTECODE': '1'}
        env.pop('SECRET_KEY', None)
        if key is not None:
            env['SECRET_KEY'] = key
        return subprocess.run(
            [sys.executable, '-B', '-c',
             "import sys; sys.path.insert(0, 'backend'); from app import app; "
             "import os; assert app.config['SECRET_KEY'] == os.environ['SECRET_KEY']; "
             "c = app.test_client(); "
             "assert c.get('/').status_code == 200"],
            cwd=ROOT, env=env, capture_output=True, text=True)

    def test_missing_blank_and_public_placeholder_keys_reject_startup(self):
        for key in (None, '', '   ', 'your_very_secret_key', 'your_secret_key_here',
                    'replace-with-your-existing-production-secret'):
            with self.subTest(key=key):
                result = self.start_app(key)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('SECRET_KEY must be set', result.stderr)

    def test_private_key_is_preserved_and_app_starts(self):
        key = secrets.token_hex(32)
        result = self.start_app(key)
        self.assertEqual(result.returncode, 0)
        self.assertNotIn(key, result.stdout + result.stderr)


class IntegrationTests(unittest.TestCase):
    def test_migration_existing_users_pages_api_backup_and_keyless_collection(self):
        with tempfile.TemporaryDirectory() as directory:
            dbpath=Path(directory)/'site.db'
            # A pre-migration legacy user table containing real-looking test state.
            with closing(sqlite3.connect(dbpath)) as c:
                c.execute('CREATE TABLE user (id INTEGER NOT NULL, username VARCHAR(64) NOT NULL, password VARCHAR(128) NOT NULL, email VARCHAR(120), created_at DATETIME, PRIMARY KEY (id), UNIQUE (username), UNIQUE (email))')
                c.execute("INSERT INTO user (username,password) VALUES ('preserved','hash')")
                c.commit()
            env={**os.environ,'DATABASE_URL':'sqlite:///'+dbpath.as_posix(),'PYTHONDONTWRITEBYTECODE':'1',
                 'SECRET_KEY':secrets.token_hex(32),
                 'MOLIT_API_KEY':'','MOLIT_RENT_API_KEY':''}
            def run(*args):
                result=subprocess.run([sys.executable,'-B',*args],cwd=ROOT,env=env,capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                return result.stdout
            run('-m','flask','--app','backend/app','db','upgrade')
            run('-m','flask','--app','backend/app','db','upgrade')
            run('-m','flask','--app','backend/app','db','check')
            with closing(sqlite3.connect(dbpath)) as c:
                self.assertEqual(c.execute('SELECT username FROM user').fetchone()[0],'preserved')
                self.assertEqual(c.execute('SELECT count(*) FROM regions').fetchone()[0],25)
            run('-m','flask','--app','backend/app','backup-db','--directory',directory)
            backup=next(Path(directory).glob('safehome-*.sqlite'))
            with closing(sqlite3.connect(backup)) as c:
                self.assertEqual(c.execute('PRAGMA integrity_check').fetchone()[0],'ok')
                self.assertEqual(c.execute('SELECT username FROM user').fetchone()[0],'preserved')
            run('-m','flask','--app','backend/app','check-data-storage')
            smoke = """import sys;sys.path.insert(0,'backend')
from app import app
from unittest.mock import patch
c=app.test_client()
for path in ('/','/map','/searchscan','/self-check','/scam-types','/login','/reviews','/api/dashboard/summary'):
    assert c.get(path).status_code==200,path
assert c.get('/api/analyze').status_code==400
assert c.get('/analyze').status_code==400
with patch('routes.api.load_transaction_snapshot',return_value=[]):
    assert c.get('/api/real-transactions?lawd_cd=11110&deal_ymd=202610').status_code==200
with patch('routes.api.fetch_properties_by_region',return_value=[]):
    assert c.get('/api/analyze?region=종로구').json=={'properties':[]}
with patch('dashboard._get_api_key',return_value=''):
    result=app.test_cli_runner().invoke(args=['sync-dashboard','--region','11110','--month','202610'])
    assert result.exit_code!=0
assert c.get('/api/dashboard/summary').json['summary']['transaction_count'] is None
assert 'accuracy' not in c.get('/api/stats').json
"""
            run('-c',smoke)


if __name__=='__main__': unittest.main()
