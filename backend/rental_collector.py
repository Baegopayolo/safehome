"""Complete region/month snapshots from MOLIT's apartment rent endpoint."""
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from urllib.parse import unquote

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from utils import SEOUL_SIGUNGU_CODES

API_URL = 'https://apis.data.go.kr/1613000/RTMSDataSvcAptRent/getRTMSDataSvcAptRent'
SOURCE = {'name': '국토교통부 아파트 전월세 실거래가 자료',
          'url': 'https://www.data.go.kr/data/15126474/openapi.do'}


class CollectionError(Exception):
    """Only a non-sensitive code may be persisted or printed."""


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def months_for(today, count=12):
    end = today.year * 12 + today.month - 1
    return [f'{i // 12:04d}{i % 12 + 1:02d}' for i in range(end-count+1, end+1)]


def validate_scope(region, month, today):
    if region not in SEOUL_SIGUNGU_CODES.values():
        raise CollectionError('INVALID_SEOUL_REGION')
    try:
        if not re.fullmatch(r'[0-9]{6}', month):
            raise ValueError()
        start = datetime.strptime(month, '%Y%m').date()
        if start > today.replace(day=1):
            raise ValueError()
    except ValueError:
        raise CollectionError('INVALID_MONTH') from None


def make_session():
    session = requests.Session()
    retry = Retry(total=3, connect=3, read=3, status=3, backoff_factor=1,
                  status_forcelist=[429, 500, 502, 503, 504], allowed_methods=['GET'],
                  respect_retry_after_header=False)
    session.mount('https://', HTTPAdapter(max_retries=retry))
    return session


def normalize(fields, region, month, today):
    """Missing rent is invalid, never interpreted as zero (jeonse)."""
    try:
        deposit = int(fields['deposit'].replace(',', '').replace(' ', ''))
        rent = int(fields['monthlyRent'].replace(',', '').replace(' ', ''))
        area = Decimal(fields['excluUseAr'])
        day = date(int(fields['dealYear']), int(fields['dealMonth']), int(fields['dealDay']))
        if not area.is_finite() or area <= 0 or area >= Decimal('100000000') or area.as_tuple().exponent < -4:
            raise ValueError()
        if deposit < 0 or rent < 0 or deposit > 10**12 or rent > 10**12 or day > today or day.strftime('%Y%m') != month:
            raise ValueError()
        if fields.get('sggCd', region) != region or not fields.get('aptNm') or not fields.get('umdNm'):
            raise ValueError()
        cancellation = fields.get('cdealType', '')
        if cancellation not in ('', 'O', 'Y', '1', 'N', '0', '-'):
            raise ValueError()
    except (KeyError, ValueError, TypeError, InvalidOperation):
        raise CollectionError('INVALID_RECORD') from None
    if rent > 0:
        return None
    if deposit <= 0:
        raise CollectionError('INVALID_JEONSE_DEPOSIT')
    # Normalize key numeric fields. Preserve all other public fields to avoid
    # collapsing distinct renewal / contract records as far as the source permits.
    identity = {k: v for k, v in fields.items() if k not in ('cdealType', 'cdealDay')}
    identity.update(deposit=str(deposit), monthlyRent=str(rent), excluUseAr=str(area.normalize()),
                    dealYear=str(day.year), dealMonth=str(day.month), dealDay=str(day.day))
    key = hashlib.sha256(json.dumps(identity, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return dict(fingerprint=key, transaction_type='jeonse', deposit=deposit, monthly_rent=rent,
                contract_date=day, area=area, apartment=fields['aptNm'], dong=fields['umdNm'],
                floor=fields.get('floor',''), cancelled=cancellation in ('O','Y','1') or
                fields.get('cdealDay','') not in ('','-'))


def fetch_month(region, month, key, today, session=None):
    validate_scope(region, month, today)
    if not key:
        raise CollectionError('MISSING_API_KEY')
    own_session = session is None
    session = session or make_session()
    records, seen_pages = {}, set()
    total, received, page = None, 0, 1
    try:
        while True:
            response = session.get(API_URL, params={'serviceKey': unquote(key), 'LAWD_CD': region,
                'DEAL_YMD': month, 'pageNo': page, 'numOfRows': 1000}, timeout=(5, 20))
            response.raise_for_status()
            root = ET.fromstring(response.content)
            if root.findtext('./header/resultCode') not in ('00', '000'):
                raise CollectionError('UPSTREAM_REJECTED')
            count = int(root.findtext('./body/totalCount', '-1'))
            if count < 0 or (total is not None and count != total):
                raise CollectionError('CHANGED_TOTAL')
            total = count
            if int(root.findtext('./body/pageNo', '-1')) != page:
                raise CollectionError('WRONG_PAGE')
            items = root.findall('./body/items/item')
            if not items and received < total:
                raise CollectionError('MISSING_PAGE')
            parsed = [{child.tag:(child.text or '').strip() for child in item} for item in items]
            page_hash = hashlib.sha256(json.dumps(parsed, sort_keys=True).encode()).hexdigest()
            if items and page_hash in seen_pages:
                raise CollectionError('REPEATED_PAGE')
            seen_pages.add(page_hash)
            for fields in parsed:
                tx = normalize(fields, region, month, today)
                if tx is not None:
                    previous = records.get(tx['fingerprint'])
                    if previous:
                        tx['cancelled'] = tx['cancelled'] or previous['cancelled']
                    records[tx['fingerprint']] = tx
            received += len(items)
            if received > total:
                raise CollectionError('COUNT_MISMATCH')
            if received == total:
                return list(records.values()), total
            page += 1
            if page > 10000:
                raise CollectionError('PAGE_LIMIT')
    except requests.RequestException:
        raise CollectionError('NETWORK_OR_HTTP_ERROR') from None
    except (ET.ParseError, ValueError):
        raise CollectionError('INVALID_RESPONSE') from None
    finally:
        if own_session:
            session.close()


def collect_scope(db, models, region, month, key, today, fetch=None):
    Region, Transaction, Stat, Log = models
    validate_scope(region, month, today)
    log = Log(region_code=region, deal_month=month, status='running', started_at=utcnow())
    db.session.add(log)
    db.session.commit()
    log_id = log.id
    try:
        records, source_count = (fetch or fetch_month)(region, month, key, today)
        completed = utcnow()
        if db.session.get(Region, region) is None:
            name = next(n for n, code in SEOUL_SIGUNGU_CODES.items() if code == region)
            db.session.add(Region(code=region, name=name))
            db.session.flush()
        # Reconcile the ENTIRE verified month atomically: disappeared/corrected
        # source records are removed; failed/incomplete fetches never reach here.
        Transaction.query.filter_by(region_code=region, deal_month=month).delete(synchronize_session=False)
        db.session.add_all([Transaction(region_code=region, deal_month=month, collected_at=completed, **r) for r in records])
        db.session.flush()
        count = Transaction.query.filter_by(region_code=region, deal_month=month, cancelled=False).count()
        stat = db.session.get(Stat, (region, month))
        if stat is None:
            stat = Stat(region_code=region, deal_month=month)
            db.session.add(stat)
        stat.transaction_count, stat.source_count, stat.calculated_at = count, source_count, completed
        log = db.session.get(Log, log_id)
        log.status, log.source_count, log.transaction_count, log.finished_at = 'success', source_count, count, completed
        db.session.commit()
        return True
    except Exception as exc:
        db.session.rollback()
        log = db.session.get(Log, log_id)
        log.status, log.finished_at = 'failed', utcnow()
        log.error_code = str(exc) if isinstance(exc, CollectionError) else 'STORAGE_OR_INTERNAL_ERROR'
        db.session.commit()
        return False
