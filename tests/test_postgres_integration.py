"""Real PostgreSQL integration on disposable data. Enable with SAFEHOME_TEST_POSTGRES_BIN."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'deploy'))
from dashboard_maintenance import verify_restore


@unittest.skipUnless(os.getenv('SAFEHOME_TEST_POSTGRES_BIN') and os.name == 'posix',
                     'Requires Linux PostgreSQL server binaries')
class PostgresIntegration(unittest.TestCase):
    def test_migrate_collect_rollback_backup_and_restore(self):
        bindir = Path(os.environ['SAFEHOME_TEST_POSTGRES_BIN'])
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            data = directory/'data'
            env = {k: v for k, v in os.environ.items() if not k.startswith('PG')}
            env['PATH'] = str(bindir) + os.pathsep + env['PATH']
            env['SECRET_KEY'] = 'safehome-postgres-ci-only'
            env['FLASK_SKIP_DOTENV'] = '1'
            with socket.socket() as listener:
                listener.bind(('127.0.0.1', 0))
                port = listener.getsockname()[1]

            def run(*args):
                result = subprocess.run(args, env=env, cwd=ROOT, timeout=60, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            run(bindir/'initdb', '-D', data, '-U', 'safehome_test', '--auth=trust',
                '--encoding=UTF8', '--locale=C')
            try:
                run(bindir/'pg_ctl', '-D', data, '-l', directory/'postgres.log', '-o',
                    f'-h 127.0.0.1 -p {port} -k {directory} -c shared_buffers=16MB -c max_connections=10', '-w', 'start')
                run(bindir/'createdb', '-h', '127.0.0.1', '-p', str(port), '-U', 'safehome_test', 'safehome_test')
                env['DATABASE_URL'] = f'postgresql://safehome_test@127.0.0.1:{port}/safehome_test'
                flask = (sys.executable, '-B', '-m', 'flask', '--app', 'backend/app')
                run(*flask, 'db', 'upgrade')
                run(*flask, 'db', 'check')
                run(sys.executable, '-B', '-c', """
import sys
sys.path.insert(0, 'backend')
from app import app, db
from dashboard import KST
from datetime import datetime
from map_indicators import comparison_period
from rental_collector import collect_scope, normalize, utcnow
with app.app_context():
    models = app.extensions['dashboard_models']
    today = datetime.now(KST).date()
    month = today.strftime('%Y%m')
    fields = dict(deposit='50000', monthlyRent='0', excluUseAr='84.9',
        dealYear=str(today.year), dealMonth=str(today.month), dealDay='1',
        aptNm='Fixture', umdNm='사직동', sggCd='11110')
    row = normalize(fields, '11110', month, today)
    cancelled = normalize(dict(fields, deposit='60000', cdealType='Y'), '11110', month, today)
    scope = (db, models, '11110', month, 'fixture', today)
    assert collect_scope(*scope, fetch=lambda *_: ([row, cancelled], 2))
    assert not collect_scope(*scope, fetch=lambda *_: ([dict(row, deposit=-1)], 1))
    assert models[1].query.count() == 2
    payload = app.test_client().get('/api/dashboard/summary').get_json()
    assert payload['summary']['transaction_count'] == 1
    assert sum(r['transaction_count'] or 0 for r in payload['regions']) == 1
    assert sum(r['transaction_count'] or 0 for r in payload['trends']) == 1
    assert payload['coverage']['failures'][0]['error_code'] == 'STORAGE_OR_INTERNAL_ERROR'
    _, start, end = comparison_period(today)
    Snapshot = app.extensions['map_snapshot']
    db.session.add(Snapshot(region_code='11680', period_start=start, period_end=end,
                           collected_at=utcnow(), indicators={'역삼동': {'score': 72, 'sale_sample_count': 5}}))
    db.session.commit()
    locations = app.test_client().get('/heatmap').get_json()
    yeoksam = next(location for location in locations if location['dong'] == '역삼동')
    assert (yeoksam['status'], yeoksam['score'], yeoksam['sale_sample_count']) == ('available', 72, 5)
""")
                run(*flask, 'backup-db', '--directory', directory)
            finally:
                if (data/'postmaster.pid').exists():
                    run(bindir/'pg_ctl', '-D', data, '-m', 'immediate', '-w', 'stop')
            verify_restore(next(directory.glob('safehome-*.dump')), bindir)
