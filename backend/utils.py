import os
import json
import re
from datetime import datetime, timezone, timedelta
import requests
import xml.etree.ElementTree as ET
from collections import OrderedDict
from math import isfinite
from statistics import median
from threading import Lock
from time import monotonic
from urllib.parse import unquote
from concurrent.futures import ThreadPoolExecutor

def parse_date(deal_date_str):
    """deal_date 문자열을 datetime으로 변환 (utils.py 내부용)"""
    if not isinstance(deal_date_str, str):
        return None
    try:
        date_str = deal_date_str.replace('-', '') if '-' in deal_date_str else deal_date_str
        if len(date_str) >= 8:
            return datetime(int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8]))
    except (ValueError, TypeError):
        pass
    return None

MOLIT_API_KEY = ''
MOLIT_RENT_API_KEY = '' 

SEOUL_SIGUNGU_CODES = {
    '종로구': '11110', '중구': '11140', '용산구': '11170', '성동구': '11200', '광진구': '11215',
    '동대문구': '11230', '중랑구': '11260', '성북구': '11290', '강북구': '11305', '도봉구': '11320',
    '노원구': '11350', '은평구': '11380', '서대문구': '11410', '마포구': '11440', '양천구': '11470',
    '강서구': '11500', '구로구': '11530', '금천구': '11545', '영등포구': '11560', '동작구': '11590',
    '관악구': '11620', '서초구': '11650', '강남구': '11680', '송파구': '11710', '강동구': '11740'
}

def _get_api_key(rent=False):
    """API 키 가져오기 (rent=True면 전월세 API 키)"""
    env_key = 'MOLIT_RENT_API_KEY' if rent else 'MOLIT_API_KEY'
    key = os.getenv(env_key)
    if key:
        return key
    config_path = os.path.join(os.path.dirname(__file__), 'instance', 'config.json')
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
                config_key = 'MOLIT_RENT_API_KEY' if rent else 'MOLIT_API_KEY'
                if cfg.get(config_key):
                    return cfg[config_key]
    except Exception:
        pass
    return MOLIT_RENT_API_KEY if rent else MOLIT_API_KEY

def _format_price_to_eok(price_manwon):
    """만원 단위 가격을 억원 단위로 변환"""
    if not price_manwon or price_manwon == 0:
        return '가격 정보 없음'
    try:
        price_eok = price_manwon / 10000
        return f"{price_eok:.1f}억" if price_eok >= 1 else f"{price_manwon}만원"
    except (TypeError, ValueError):
        return '가격 정보 없음'

def _extract_dong(region: str) -> str:
    """주소/지역 문자열에서 '동' 단위 추출"""
    if not region or not isinstance(region, str):
        return region
    for pattern in [r'([가-힣0-9]+동)', r'([가-힣0-9]+가)', r'([가-힣0-9]+리)']:
        match = re.search(pattern, region)
        if match:
            return match.group(1)
    return region

def _resolve_lawd_cd(region: str, fallback: str = '11110') -> str:
    """지역명에서 법정동 코드 추출"""
    if not region:
        return fallback
    for gu, code in SEOUL_SIGUNGU_CODES.items():
        if gu in region:
            return code
    dong_to_gu = {
        '청담동': '강남구', '역삼동': '강남구', '삼성동': '강남구', '대치동': '강남구',
        '압구정동': '강남구', '논현동': '강남구', '신사동': '강남구', '도곡동': '강남구',
        '개포동': '강남구', '수서동': '강남구', '일원동': '강남구', '세곡동': '강남구',
        '화곡동': '강서구', '등촌동': '강서구', '마곡동': '강서구', '가양동': '강서구',
        '방화동': '강서구', '공항동': '강서구', '염창동': '강서구', '신정동': '강서구',
        '목동': '양천구', '신월동': '양천구',
        '서교동': '마포구', '연남동': '마포구', '성산동': '마포구', '합정동': '마포구',
        '상암동': '마포구', '공덕동': '마포구', '아현동': '마포구', '도화동': '마포구',
        '문래동': '영등포구', '여의도동': '영등포구', '당산동': '영등포구', '신길동': '영등포구',
        '대림동': '영등포구', '양평동': '영등포구', '도림동': '영등포구',
        '독산동': '금천구', '가산동': '금천구', '시흥동': '금천구',
        '신림동': '관악구', '봉천동': '관악구', '남현동': '관악구', '서원동': '관악구',
        '잠실동': '송파구', '신천동': '송파구', '방이동': '송파구', '문정동': '송파구',
        '가락동': '송파구', '거여동': '송파구', '마천동': '송파구', '장지동': '송파구',
        '석촌동': '송파구', '오금동': '송파구', '송파동': '송파구', '잠실본동': '송파구',
        '명일동': '강동구', '고덕동': '강동구', '상일동': '강동구', '천호동': '강동구',
        '길동': '강동구', '둔촌동': '강동구', '암사동': '강동구',
        '사직동': '종로구', '삼청동': '종로구', '혜화동': '종로구', '이화동': '종로구',
        '명륜동': '종로구', '와룡동': '종로구', '무악동': '종로구', '교남동': '종로구',
        '반포동': '서초구', '잠원동': '서초구', '방배동': '서초구', '양재동': '서초구',
        '내곡동': '서초구', '염곡동': '서초구', '서초동': '서초구',
        '미아동': '강북구', '번동': '강북구', '수유동': '강북구', '우이동': '강북구',
        '월계동': '노원구', '공릉동': '노원구', '하계동': '노원구', '중계동': '노원구', '상계동': '노원구',
        '불광동': '은평구', '녹번동': '은평구', '응암동': '은평구', '신사동': '은평구',
        '역촌동': '은평구', '구산동': '은평구', '갈현동': '은평구',
        '이태원동': '용산구', '한남동': '용산구', '이촌동': '용산구',
        '왕십리동': '성동구', '성수동': '성동구', '행당동': '성동구',
        '용산동': '용산구', '한강로동': '용산구',
    }
    for dong_name, gu_name in dong_to_gu.items():
        if dong_name in region:
            for gu, code in SEOUL_SIGUNGU_CODES.items():
                if gu == gu_name:
                    return code
    
    # 매칭 실패 시 경고 및 기본값 반환
    print(f"[경고] _resolve_lawd_cd: '{region}'에 대한 법정동 코드를 찾지 못함, 기본값({fallback}) 반환")
    return fallback

def _parse_common_fields(item):
    """공통 필드 파싱 헬퍼 함수"""
    def txt(tag):
        el = item.find(tag)
        return el.text.strip() if el is not None and el.text else ''
    
    apt_name = txt('아파트') or txt('aptNm') or txt('아파트명')
    dong_name = txt('법정동') or txt('법정동명') or txt('법정동주소') or txt('umdNm')
    bonbun = txt('본번') or txt('bonbun') or ''
    bubun = txt('부번') or txt('bubun') or ''
    jibun = txt('지번') or (f"{bonbun}-{bubun}" if bonbun or bubun else '')
    deal_year = txt('년') or txt('dealYear') or txt('거래년도')
    deal_month = txt('월') or txt('dealMonth') or txt('거래월')
    deal_day = txt('일') or txt('dealDay') or txt('거래일')
    deal_date = f"{deal_year}-{deal_month.zfill(2)}-{deal_day.zfill(2)}" if deal_year and deal_month and deal_day else ''
    area = (txt('전용면적') or txt('전용면적㎡') or txt('전용면적(㎡)') or 
            txt('면적') or txt('면적㎡') or txt('area') or txt('전용면적(평)') or 
            txt('excluUseAr') or '')
    
    return {
        'apt_name': apt_name,
        'dong_name': dong_name,
        'jibun': jibun,
        'deal_date': deal_date,
        'area': area,
        'floor': txt('층') or txt('층수') or txt('floor') or '',
        'build_year': txt('건축년도') or txt('buildYear') or txt('건축년') or '',
        'region_code': txt('지역코드') or txt('lawdCd') or txt('sggCd') or '',
        'txt_func': txt
    }

def _is_cancelled(item):
    return (item.findtext('cdealType', '').strip().upper() in {'O', 'Y', '1'}
            or item.findtext('cdealDay', '').strip() not in {'', '-', '0'})


def _parse_transactions(records):
    items = []
    for it in records:
        if _is_cancelled(it):
            continue
        common = _parse_common_fields(it)
        price_raw = common['txt_func']('거래금액') or common['txt_func']('dealAmount')
        try:
            price = int(price_raw.replace(',', '').replace(' ', '')) if price_raw else None
        except ValueError:
            price = None
        
        items.append({
            '아파트': common['apt_name'],
            '법정동': common['dong_name'],
            '전용면적': common['area'],
            '층': common['floor'],
            '건축년도': common['build_year'],
            '거래금액': price,
            '거래금액원문': price_raw,
            '거래일자': common['deal_date'],
            '지번': common['jibun'],
            '지역코드': common['region_code'],
        })
    return items

def _parse_rent_transactions(records):
    items = []
    for it in records:
        if _is_cancelled(it):
            continue
        common = _parse_common_fields(it)
        jeonse_price_raw = common['txt_func']('보증금') or common['txt_func']('보증금액') or common['txt_func']('deposit') or ''
        monthly_rent_raw = common['txt_func']('월세금액') or common['txt_func']('월세') or common['txt_func']('monthlyRent') or common['txt_func']('rent') or ''
        
        try:
            jeonse_price = int(jeonse_price_raw.replace(',', '').replace(' ', '')) if jeonse_price_raw else None
        except ValueError:
            jeonse_price = None
        try:
            monthly_rent = int(monthly_rent_raw.replace(',', '').replace(' ', '')) if monthly_rent_raw else None
        except ValueError:
            monthly_rent = None
        
        items.append({
            '아파트': common['apt_name'],
            '법정동': common['dong_name'],
            '전용면적': common['area'],
            '층': common['floor'],
            '건축년도': common['build_year'],
            '전세금액': jeonse_price,
            '전세금액원문': jeonse_price_raw,
            '월세금액': monthly_rent,
            '월세금액원문': monthly_rent_raw,
            '계약구분': common['txt_func']('contractType'),
            '계약기간': common['txt_func']('contractTerm'),
            '거래일자': common['deal_date'],
            '지번': common['jibun'],
            '지역코드': common['region_code'],
        })
    return items

class TransactionSourceError(Exception):
    """A region/month could not be fully read from the public source."""


_snapshot_cache = OrderedDict()
_snapshot_lock = Lock()


def load_transaction_snapshot(kind, lawd_cd, deal_ymd):
    """Cache only complete, unfiltered region/month results for five minutes."""
    scope = (kind, lawd_cd, deal_ymd)
    with _snapshot_lock:
        cached = _snapshot_cache.get(scope)
        if cached and cached[0] > monotonic():
            _snapshot_cache.move_to_end(scope)
            return cached[1]

    rent = kind == 'rent'
    key = (_get_api_key(rent=True) if rent else None) or _get_api_key()
    if not key:
        raise TransactionSourceError('MISSING_API_KEY')
    endpoint = 'RTMSDataSvcAptRent/getRTMSDataSvcAptRent' if rent else 'RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev'
    url = f'https://apis.data.go.kr/1613000/{endpoint}'
    records = []
    seen_pages = set()
    total = None
    deadline = monotonic() + 20
    try:
        with requests.Session() as session:
            for page in range(1, 21):
                if monotonic() >= deadline:
                    raise TransactionSourceError('PAGE_TIMEOUT')
                response = session.get(url, params={'serviceKey': unquote(key), 'LAWD_CD': lawd_cd,
                    'DEAL_YMD': deal_ymd, 'pageNo': page, 'numOfRows': 1000}, timeout=(4, 7))
                response.raise_for_status()
                root = ET.fromstring(response.content)
                if root.findtext('./header/resultCode') not in {'00', '000'}:
                    raise TransactionSourceError('UPSTREAM_REJECTED')
                reported_total = int(root.findtext('./body/totalCount', '-1'))
                if reported_total < 0 or (total is not None and reported_total != total):
                    raise TransactionSourceError('CHANGED_TOTAL')
                total = reported_total
                if int(root.findtext('./body/pageNo', '-1')) != page:
                    raise TransactionSourceError('WRONG_PAGE')
                batch = root.findall('./body/items/item')
                signature = tuple(ET.tostring(item) for item in batch)
                if len(records) + len(batch) > total or (not batch and len(records) < total) or signature in seen_pages:
                    raise TransactionSourceError('INVALID_PAGE')
                seen_pages.add(signature)
                records.extend(batch)
                if len(records) == total:
                    break
            else:
                raise TransactionSourceError('PAGE_LIMIT')
    except (requests.RequestException, ET.ParseError, ValueError):
        raise TransactionSourceError('SOURCE_UNAVAILABLE') from None

    transactions = (_parse_rent_transactions if rent else _parse_transactions)(records)
    transactions.sort(key=lambda tx: (tx['거래일자'], tx['아파트'], tx['법정동'], tx['지번'],
                                      tx['전용면적'], tx['층']), reverse=True)
    with _snapshot_lock:
        _snapshot_cache[scope] = (monotonic() + 300, transactions)
        _snapshot_cache.move_to_end(scope)
        if len(_snapshot_cache) > 32:
            _snapshot_cache.popitem(last=False)
    return transactions


def get_heatmap_data():
    """Return map locations without scores that lack verified sample provenance."""
    # The fixed coordinates represent locations, rather than measured areas.
    default_regions = [
        # 강남구
        {'region': '청담동', 'lat': 37.5196, 'lng': 127.0473},
        {'region': '역삼동', 'lat': 37.5000, 'lng': 127.0364},
        {'region': '강남구 삼성동', 'lat': 37.5146, 'lng': 127.0491},
        {'region': '대치동', 'lat': 37.4932, 'lng': 127.0576},
        {'region': '압구정동', 'lat': 37.5275, 'lng': 127.0286},
        {'region': '논현동', 'lat': 37.5111, 'lng': 127.0216},
        {'region': '신사동', 'lat': 37.5208, 'lng': 127.0225},
        {'region': '도곡동', 'lat': 37.4905, 'lng': 127.0554},
        {'region': '개포동', 'lat': 37.4789, 'lng': 127.0525},
        {'region': '일원동', 'lat': 37.4833, 'lng': 127.0833},
        # 강서구
        {'region': '화곡동', 'lat': 37.5414, 'lng': 126.8404},
        {'region': '등촌동', 'lat': 37.5567, 'lng': 126.8567},
        {'region': '마곡동', 'lat': 37.5667, 'lng': 126.8267},
        {'region': '가양동', 'lat': 37.5617, 'lng': 126.8500},
        {'region': '염창동', 'lat': 37.5500, 'lng': 126.8667},
        {'region': '공항동', 'lat': 37.5583, 'lng': 126.8083},
        # 마포구
        {'region': '서교동', 'lat': 37.5563, 'lng': 126.9238},
        {'region': '연남동', 'lat': 37.5639, 'lng': 126.9250},
        {'region': '성산동', 'lat': 37.5667, 'lng': 126.9000},
        {'region': '합정동', 'lat': 37.5500, 'lng': 126.9139},
        {'region': '상암동', 'lat': 37.5767, 'lng': 126.8933},
        # 송파구
        {'region': '잠실동', 'lat': 37.5133, 'lng': 127.1028},
        {'region': '신천동', 'lat': 37.5142, 'lng': 127.1025},
        {'region': '방이동', 'lat': 37.5083, 'lng': 127.1250},
        {'region': '문정동', 'lat': 37.4850, 'lng': 127.1233},
        {'region': '가락동', 'lat': 37.4933, 'lng': 127.1183},
        {'region': '석촌동', 'lat': 37.5042, 'lng': 127.1025},
        # 관악구
        {'region': '신림동', 'lat': 37.4842, 'lng': 126.9294},
        {'region': '봉천동', 'lat': 37.4833, 'lng': 126.9500},
        {'region': '서원동', 'lat': 37.4767, 'lng': 126.9333},
        {'region': '관악구 삼성동', 'lat': 37.4700, 'lng': 126.9300},
        # 강동구
        {'region': '명일동', 'lat': 37.5500, 'lng': 127.1436},
        {'region': '천호동', 'lat': 37.5383, 'lng': 127.1233},
        {'region': '성내동', 'lat': 37.5283, 'lng': 127.1267},
        {'region': '길동', 'lat': 37.5367, 'lng': 127.1400},
        # 영등포구
        {'region': '여의도동', 'lat': 37.5217, 'lng': 126.9242},
        {'region': '당산동', 'lat': 37.5267, 'lng': 126.8967},
        {'region': '문래동', 'lat': 37.5167, 'lng': 126.8967},
        {'region': '신길동', 'lat': 37.5133, 'lng': 126.9133},
        # 서초구
        {'region': '반포동', 'lat': 37.5042, 'lng': 127.0058},
        {'region': '서초동', 'lat': 37.4833, 'lng': 127.0333},
        {'region': '방배동', 'lat': 37.4833, 'lng': 126.9967},
        {'region': '양재동', 'lat': 37.4700, 'lng': 127.0400},
        # 용산구
        {'region': '이촌동', 'lat': 37.5192, 'lng': 126.9767},
        {'region': '한남동', 'lat': 37.5333, 'lng': 127.0067},
        {'region': '이태원동', 'lat': 37.5342, 'lng': 126.9942},
        # 종로구
        {'region': '종로동', 'lat': 37.5700, 'lng': 126.9800},
        {'region': '혜화동', 'lat': 37.5867, 'lng': 127.0000},
        # 중구
        {'region': '명동', 'lat': 37.5633, 'lng': 126.9833},
        {'region': '을지로동', 'lat': 37.5667, 'lng': 126.9900},
        # 노원구
        {'region': '상계동', 'lat': 37.6633, 'lng': 127.0733},
        {'region': '하계동', 'lat': 37.6367, 'lng': 127.0700},
    ]
    
    return [dict(region, score=None, status='unavailable') for region in default_regions]


def filter_transactions_by_region(transactions, region):
    match = re.search(r'[가-힣0-9]+[동가리](?=[\s,]|$)', region or '')
    if not match:
        return transactions
    return [tx for tx in transactions if tx.get('법정동') == match.group()]


def _comparison_fields(tx):
    try:
        area = float(tx.get('전용면적'))
    except (TypeError, ValueError):
        return None
    day = parse_date(tx.get('거래일자'))
    if not day or not isfinite(area) or area <= 0 or not tx.get('아파트') or not tx.get('법정동'):
        return None
    lot = tx.get('지번') or ''
    if re.fullmatch(r'\d+(?:-\d+)?', lot):
        main, _, sub = lot.partition('-')
        lot = (int(main), int(sub or 0))
    return area, day, lot, tx.get('건축년도')


def _estimate_jeonse(sale, candidates):
    price = sale.get('거래금액')
    fields = _comparison_fields(sale)
    if fields is None or not price or price <= 0:
        return None, 0
    area, day, lot, year = fields
    deposits = []
    for (rent_area, rent_day, rent_lot, rent_year), deposit in candidates:
        if abs(area - rent_area) > 1 or abs((day - rent_day).days) > 30:
            continue
        if (lot and rent_lot and lot != rent_lot) or (year and rent_year and year != rent_year):
            continue
        if not (lot and rent_lot) and not (year and year == rent_year):
            continue
        if deposit >= price * 0.01:
            deposits.append(deposit)
    return (median(deposits) if len(deposits) >= 3 else None), len(deposits)


def fetch_properties_by_region(region, db=None, RealTransaction=None):
    """Compare recent sales with comparable pure-jeonse records."""
    if not region:
        return []
    lawd_cd = _resolve_lawd_cd(region, fallback=None)
    if not lawd_cd:
        raise ValueError('지원하는 서울 자치구 또는 법정동을 입력하세요.')
    district = next(name for name, code in SEOUL_SIGUNGU_CODES.items() if code == lawd_cd)
    today = datetime.now(timezone(timedelta(hours=9))).date()
    months = []
    month_start = today.replace(day=1)
    for _ in range(6):
        months.append(month_start.strftime('%Y%m'))
        month_start = (month_start - timedelta(days=1)).replace(day=1)
    with ThreadPoolExecutor(max_workers=6) as executor:
        jobs = {(kind, month): executor.submit(load_transaction_snapshot, kind, lawd_cd, month)
                for kind in ('sale', 'rent') for month in months}
        sales = [sale for month in months for sale in jobs['sale', month].result()]
        try:
            rents = [rent for month in months for rent in jobs['rent', month].result()]
            rent_available = True
        except TransactionSourceError:
            rents, rent_available = [], False

    candidates = {}
    seen = set()
    for rent in filter_transactions_by_region(rents, region):
        deposit = rent.get('전세금액')
        if rent.get('월세금액') != 0 or not deposit or deposit <= 0:
            continue
        fields = _comparison_fields(rent)
        if fields is None:
            continue
        key = (rent['아파트'], rent['법정동'])
        fingerprint = (key, fields, rent.get('층'), deposit, rent.get('계약구분'), rent.get('계약기간'))
        if fingerprint not in seen:
            candidates.setdefault(key, []).append((fields, deposit))
            seen.add(fingerprint)

    properties = []
    for sale in filter_transactions_by_region(sales, region):
        apt, dong = sale['아파트'], sale['법정동']
        area, floor = sale['전용면적'], sale['층']
        price = sale['거래금액']
        deposit, samples = _estimate_jeonse(sale, candidates.get((apt, dong), []))
        rate = round(deposit / price * 100, 2) if deposit is not None else None
        level, score = 'unknown', None
        if rate is not None:
            level, score = ('high', 80) if rate >= 80 else ('medium', 60) if rate >= 60 else ('low', 20)
        properties.append({
            'name': f'{apt} ({area}㎡, {floor}층)' if area and floor else apt,
            'address': ' '.join(part for part in (district, dong, sale.get('지번')) if part),
            'price': _format_price_to_eok(price) if price else sale['거래금액원문'],
            'price_raw': price, 'area': area, 'floor': floor, 'build_year': sale['건축년도'],
            'deal_date': sale['거래일자'], 'jeonse_price': deposit,
            'jeonse_price_formatted': _format_price_to_eok(deposit) if deposit is not None else None,
            'jeonse_rate': rate, 'risk_level': level, 'risk_score': score,
            'comparison_sample_count': samples if rent_available else None,
            'comparison_status': ('available' if rate is not None else
                                  'insufficient' if rent_available else 'source_unavailable'),
            'comparison_confidence': ('limited' if samples < 5 else 'moderate') if rate is not None else None,
        })
    return properties


def analyze_property_warnings(prop):
    """매물 위험 요소 분석"""
    warnings = []
    if '빌라' in prop.get('name', '') or '오피스텔' in prop.get('name', ''):
        warnings.append('빌라/오피스텔은 아파트보다 전세사기 위험이 높을 수 있습니다.')
    jeonse_rate = prop.get('jeonse_rate')
    if prop.get('comparison_status') == 'source_unavailable':
        warnings.append('전세 자료를 불러오지 못해 전세가율을 판단할 수 없습니다.')
    elif jeonse_rate is None:
        warnings.append('비교 가능한 전세 자료가 부족해 전세가율을 판단할 수 없습니다.')
    else:
        if jeonse_rate >= 80:
            warnings.append(f'전세가율이 {jeonse_rate}%로 높습니다. 보증금과 권리관계를 추가로 확인하세요.')
        elif jeonse_rate >= 70:
            warnings.append(f'전세가율이 {jeonse_rate}%로 높습니다. 계약 시 주의가 필요합니다.')
        elif jeonse_rate >= 60:
            warnings.append(f'전세가율이 {jeonse_rate}%입니다. 일반적인 수준입니다.')
    try:
        price_raw = prop.get('price_raw', 0)
        if price_raw and price_raw < 10000:
            warnings.append('시세 대비 낮은 가격은 위험 신호일 수 있습니다. 주변 시세를 다시 확인하세요.')
    except (ValueError, TypeError):
        pass
    try:
        build_year = prop.get('build_year', '')
        if build_year and datetime.now().year - int(build_year) > 30:
            warnings.append('건축년도가 오래된 건물은 노후화로 인한 문제가 발생할 수 있습니다.')
    except (ValueError, TypeError):
        pass
    return warnings

def generate_safety_checklist(prop):
    """안전 계약 체크리스트 생성 (매물 특성에 따라 동적 생성)"""
    checklist = []
    
    # 기본 필수 항목
    checklist.append('등기부등본 확인')
    checklist.append('건축물대장 확인')
    checklist.append('임대인 신분증 확인')
    checklist.append('선순위 세입자 확인')
    checklist.append('집주인 세금 체납 조회')
    
    # 전세가율이 높은 경우 (80% 이상)
    jeonse_rate = prop.get('jeonse_rate')
    if jeonse_rate and jeonse_rate >= 80:
        checklist.append('⚠️ 전세가율이 매우 높습니다. 추가 담보 확인 필요')
        checklist.append('전세금 반환 보증 보험 가입 여부 확인')
        checklist.append('임대인 신용도 추가 조회')
    
    # 전세가율이 높은 경우 (60-79%)
    elif jeonse_rate and jeonse_rate >= 60:
        checklist.append('전세금 반환 보증 보험 가입 여부 확인')
    
    # 빌라/오피스텔인 경우
    name = prop.get('name', '')
    if '빌라' in name or '오피스텔' in name:
        checklist.append('건물 소유권 확인 (분양권/전매제한 확인)')
        checklist.append('관리비 및 공용부담금 확인')
        checklist.append('상가/주거 혼용 여부 확인')
        checklist.append('화재보험 가입 여부 확인')
    
    # 노후 건물인 경우 (30년 이상)
    try:
        build_year = prop.get('build_year', '')
        if build_year:
            current_year = datetime.now().year
            age = current_year - int(build_year)
            if age > 30:
                checklist.append('⚠️ 노후 건물입니다. 구조 안전 점검 필요')
                checklist.append('리모델링/재건축 계획 확인')
                checklist.append('배관 및 전기 시설 점검')
                checklist.append('지하수 침수 이력 확인')
    except (ValueError, TypeError):
        pass
    
    # 시세 대비 낮은 가격인 경우
    try:
        price_raw = prop.get('price_raw', 0)
        if price_raw and price_raw < 10000:  # 1억 미만
            checklist.append('⚠️ 시세 대비 낮은 가격입니다. 추가 확인 필요')
            checklist.append('은행 감정가 확인')
            checklist.append('주변 유사 매물 시세 비교')
    except (ValueError, TypeError):
        pass
    
    # 전세가 정보가 없는 경우
    if not jeonse_rate:
        checklist.append('⚠️ 전세 실거래 정보가 없습니다. 주변 시세 확인 필요')
        checklist.append('부동산 중개사를 통한 시세 확인')
        checklist.append('온라인 부동산 플랫폼 시세 비교')
    
    return checklist
