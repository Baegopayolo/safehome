import os
from pathlib import Path
import sys
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
