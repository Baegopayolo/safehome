import os
from datetime import date, timedelta
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
import utils


def page(number, total, *items, code='000'):
    body = ''.join(f'<item>{item}</item>' for item in items)
    xml = (f'<response><header><resultCode>{code}</resultCode></header><body>'
           f'<pageNo>{number}</pageNo><totalCount>{total}</totalCount>'
           f'<items>{body}</items></body></response>')
    return Mock(content=xml.encode())


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.addCleanup(utils._snapshot_cache.clear)
        utils._snapshot_cache.clear()

    def test_all_pages_are_verified_before_caching_and_rent_fields_are_parsed(self):
        mixed = '<aptNm>A</aptNm><umdNm>역삼동</umdNm><deposit>60,000</deposit><monthlyRent>10</monthlyRent>'
        pure = mixed.replace('>10<', '>0<')
        session = Mock()
        session.get.side_effect = [page(1, 2, mixed), page(2, 2, pure)]
        with patch.object(utils, '_get_api_key', return_value='test'), \
             patch.object(utils.requests, 'Session') as session_class:
            session_class.return_value.__enter__.return_value = session
            result = utils.load_transaction_snapshot('rent', '11680', '202610')
            self.assertEqual([10, 0], [tx['월세금액'] for tx in result])
            self.assertEqual(['역삼동'] * 2, [tx['법정동'] for tx in result])
            self.assertEqual([1, 2], [call.kwargs['params']['pageNo'] for call in session.get.call_args_list])
            self.assertEqual(utils.load_transaction_snapshot('rent', '11680', '202610'), result)
            self.assertEqual(session.get.call_count, 2)

    def test_partial_pages_are_never_cached(self):
        session = Mock()
        session.get.side_effect = [page(1, 2, '<aptNm>A</aptNm>'), page(2, 2)]
        with patch.object(utils, '_get_api_key', return_value='test'), \
             patch.object(utils.requests, 'Session') as session_class:
            session_class.return_value.__enter__.return_value = session
            with self.assertRaises(utils.TransactionSourceError):
                utils.load_transaction_snapshot('sale', '11680', '202610')
        self.assertEqual(utils._snapshot_cache, {})


class PropertyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch.dict(os.environ, {'SECRET_KEY': 'isolated-test-only', 'DATABASE_URL': 'sqlite://'}):
            from app import app
        cls.app = app

    def test_pure_jeonse_median_and_no_prior_ratio_leak(self):
        common = {'아파트': '테스트', '법정동': '역삼동', '건축년도': '2005', '지번': '123-0',
                  '전용면적': '84', '층': '3', '거래일자': '2026-11-01', '거래금액원문': ''}
        sales = [dict(common, 거래금액=100000), dict(common, 거래금액=10000000)]
        comparable = dict(common, 월세금액=0)
        rents = [dict(comparable, 전세금액=deposit) for deposit in (55000, 62000, 64000)]
        rents += [rents[0], dict(comparable, 전세금액=10000, 월세금액=40),
                  dict(comparable, 전세금액=10000, 월세금액=None),
                  dict(comparable, 전세금액=10000, 전용면적='88'),
                  dict(comparable, 전세금액=10000, 거래일자='2026-08-01'),
                  dict(comparable, 전세금액=10000, 지번='999')]

        def snapshot(kind, code, month):
            return (sales if kind == 'sale' else rents) if month == '202611' else []

        with patch.object(utils, 'load_transaction_snapshot', side_effect=snapshot), \
             patch.object(utils, 'datetime', wraps=utils.datetime) as clock:
            clock.now.return_value = utils.datetime(2026, 11, 8)
            response = self.app.test_client().get('/api/analyze', query_string={'region': '역삼동'})
            self.assertEqual(response.status_code, 200)
            first, second = response.json['properties']
        self.assertEqual((62.0, 3, 'limited', 'medium'), (first['jeonse_rate'],
                         first['comparison_sample_count'], first['comparison_confidence'], first['risk_level']))
        self.assertIsNone(second['jeonse_rate'])
        self.assertIsNone(second['risk_score'])
        self.assertEqual(second['risk_level'], 'unknown')

    def test_cache_pagination_filters_before_slicing(self):
        client = self.app.test_client()
        rows = [{'아파트': name, '법정동': dong} for name, dong in
                [('A', '역삼동'), ('Other', '삼성동'), ('B', '역삼동'), ('C', '역삼동')]]
        with patch('routes.api.load_transaction_snapshot', return_value=rows):
            args = {'region': '강남구 역삼동', 'deal_ymd': '202610', 'numOfRows': 2}
            first = client.get('/api/real-transactions', query_string=args).json
            second = client.get('/api/real-transactions', query_string=dict(args, pageNo=2)).json
            self.assertEqual([tx['아파트'] for tx in first['transactions']], ['A', 'B'])
            self.assertEqual([tx['아파트'] for tx in second['transactions']], ['C'])
            self.assertTrue(first['has_more'])
            self.assertFalse(second['has_more'])
            self.assertEqual(second['total_count'], 3)
            self.assertEqual(client.get('/api/real-transactions', query_string=dict(args, pageNo=0)).status_code, 400)

    def test_missing_rent_source_never_matches_low_band(self):
        sale = {'아파트': '테스트', '법정동': '역삼동', '전용면적': '84', '층': '3',
                '거래일자': '2026-11-01', '거래금액': 100000, '건축년도': '2005'}

        def snapshot(kind, code, month):
            if kind == 'rent':
                raise utils.TransactionSourceError('NETWORK_OR_HTTP_ERROR')
            return [sale]

        with patch.object(utils, 'load_transaction_snapshot', side_effect=snapshot):
            client = self.app.test_client()
            response = client.get('/api/advanced-search', query_string={'region': '역삼동', 'risk_level': 'low'})
            self.assertEqual(response.json['properties'], [])
            response = client.get('/api/advanced-search', query_string={'region': '역삼동', 'risk_level': 'unknown'})
            prop = response.json['properties'][0]
        self.assertEqual(prop['comparison_status'], 'source_unavailable')
        self.assertIsNone(prop['comparison_sample_count'])
        self.assertIsNone(prop['risk_score'])

    def test_source_failure_is_not_a_successful_empty_page(self):
        with patch('routes.api.load_transaction_snapshot', side_effect=utils.TransactionSourceError):
            response = self.app.test_client().get('/api/real-transactions?lawd_cd=11680')
        self.assertEqual(response.status_code, 502)
        self.assertNotIn('transactions', response.json)

    def test_operating_routes_are_present_in_checkout(self):
        client = self.app.test_client()
        self.assertIn('/login/naver', client.get('/login').get_data(as_text=True))
        self.assertIn('/login/kakao', client.get('/login').get_data(as_text=True))
        self.assertEqual(client.get('/privacy').status_code, 200)
        self.assertEqual(client.get('/api/admin/reports').status_code, 302)

    def test_map_reads_ignore_legacy_scores_without_writing(self):
        from app import db, HeatmapData
        with self.app.app_context():
            db.create_all()
            db.session.add(HeatmapData(region='역삼동', score=91, lat=0, lng=0))
            db.session.commit()
            try:
                client = self.app.test_client()
                for _ in range(2):
                    response = client.get('/heatmap')
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.headers['Cache-Control'], 'no-store')
                    by_region = {row['region']: row for row in response.json}
                    self.assertEqual(len(by_region), len(response.json))
                    self.assertEqual(by_region['역삼동']['status'], 'unavailable')
                    self.assertIsNone(by_region['역삼동']['score'])
                    self.assertNotEqual(by_region['역삼동']['lat'], 0)
                    self.assertIn('강남구 삼성동', by_region)
                    self.assertIn('관악구 삼성동', by_region)
                    self.assertTrue(all(row['score'] is None for row in response.json))
                db.session.expire_all()
                saved = HeatmapData.query.one()
                self.assertEqual((saved.score, saved.lat, saved.lng), (91, 0, 0))
            finally:
                db.drop_all()

    def test_map_sync_publishes_only_comparable_sales_and_preserves_previous_snapshot(self):
        from app import db
        from map_indicators import read_map_indicators
        from rental_collector import utcnow

        today = date(2026, 11, 10)
        common = {'아파트': '테스트', '법정동': '삼성동', '건축년도': '2005', '지번': '123-0',
                  '전용면적': '84', '층': '3', '거래일자': '2026-10-10'}
        sales = [dict(common, 거래금액=price) for price in (80000, 90000, 100000, 110000, 120000)]
        rents = [dict(common, 전세금액=deposit, 월세금액=0) for deposit in (55000, 60000, 62000)]
        rents += [rents[0], dict(common, 전세금액=10000, 월세금액=10)]

        def load(kind, code, month):
            self.assertIn(code, {'11620', '11680'})
            if month != '202610':
                return []
            other = dict(common, 법정동='역삼동')
            if kind == 'sale':
                unmatched = [dict(other, 전용면적='105', 거래금액=price) for price in range(90000, 90042)]
                return sales + [sales[0], dict(other, 거래금액=100000)] + unmatched
            return rents + [dict(rent, 법정동='역삼동') for rent in rents]

        with self.app.app_context(), TemporaryDirectory() as state, patch.dict(
            self.app.config, {'DASHBOARD_LOCK_PATH': str(Path(state) / 'dashboard.lock')},
        ):
            db.create_all()
            self.addCleanup(self.drop_map_test_db, db)
            clock_patch = patch('map_indicators.datetime', wraps=utils.datetime)
            with clock_patch as clock, patch('map_indicators.load_transaction_snapshot', side_effect=load) as source:
                clock.now.return_value = utils.datetime.combine(today, utils.datetime.min.time())
                runner = self.app.test_cli_runner()
                args = ['sync-map-indicators', '--region', '11680', '--region', '11620']
                result = runner.invoke(args=args)
                self.assertEqual(result.exit_code, 0, result.output)
                self.assertEqual(source.call_count, 12)
                before = {row['region']: row for row in self.app.test_client().get('/heatmap').json}
                gangnam = before['강남구 삼성동']
                self.assertEqual((gangnam['region_code'], gangnam['sale_sample_count'], gangnam['score']),
                                 ('11680', 5, 60))
                self.assertEqual(gangnam['sale_transaction_count'], 5)
                self.assertEqual(gangnam['period'], {'from': '2026-08-01', 'to': '2026-10-31'})
                self.assertEqual((before['관악구 삼성동']['region_code'], before['관악구 삼성동']['reason']),
                                 ('11620', 'unmapped'))
                self.assertEqual((before['역삼동']['sale_sample_count'], before['역삼동']['reason']),
                                 (1, 'insufficient'))
                self.assertEqual(before['역삼동']['sale_transaction_count'], 43)
                self.assertEqual(before['역삼동']['minimum_sale_sample_count'], 5)
                self.assertIsNone(before['역삼동']['score'])

                source.side_effect = utils.TransactionSourceError('UPSTREAM_REJECTED')
                self.assertEqual(runner.invoke(args=args).exit_code, 1)
                after = {row['region']: row for row in self.app.test_client().get('/heatmap').json}
                self.assertEqual(before, after)

            for day, now in ((today, utcnow() + timedelta(hours=37)), (date(2026, 12, 1), utcnow())):
                rows = read_map_indicators(self.app, db, today=day, now=now)
                stale = next(row for row in rows if row['region'] == '강남구 삼성동')
                self.assertEqual((stale['score'], stale['reason']), (None, 'stale'))

    def drop_map_test_db(self, db):
        with self.app.app_context():
            db.drop_all()

    def test_legacy_map_writes_are_blocked_for_every_role(self):
        from app import db, HeatmapData, User
        with self.app.app_context():
            db.create_all()
            db.session.add_all([
                HeatmapData(region='역삼동', score=91, lat=37.5, lng=127.0),
                User(username='map-user', password='test', is_admin=False),
                User(username='map-admin', password='test', is_admin=True),
            ])
            db.session.commit()
            roles = [(None, 401)] + [(user.id, 409 if user.is_admin else 403)
                                     for user in User.query.all()]
        try:
            for user_id, expected in roles:
                client = self.app.test_client()
                if user_id is not None:
                    with client.session_transaction() as session:
                        session['_user_id'] = str(user_id)
                for action in ('refresh', 'update'):
                    response = client.post('/api/heatmap/' + action, json=[{'region': '역삼동'}])
                    self.assertEqual(response.status_code, expected)
                if expected == 403:
                    response = client.post('/api/search-history', json={'region': '관악구 삼성동', 'risk_score': 91})
                    self.assertEqual(response.status_code, 200)
                    history = client.get('/api/search-history').json[0]
                    self.assertEqual(history['region'], '관악구 삼성동')
                    self.assertIsNone(history['risk_score'])
            with self.app.app_context():
                self.assertEqual(HeatmapData.query.one().score, 91)
        finally:
            with self.app.app_context():
                db.drop_all()
