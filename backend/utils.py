import os
import json
import re
from datetime import datetime, timezone, timedelta
import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed

def parse_date(deal_date_str):
    """deal_date 문자열을 datetime으로 변환 (utils.py 내부용)"""
    try:
        date_str = deal_date_str.replace('-', '') if '-' in deal_date_str else deal_date_str
        if len(date_str) >= 8:
            return datetime(int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8]))
    except (ValueError, TypeError):
        pass
    return None

MOLIT_API_KEY = 'CzO0x1MCWDpXH4ZfHg66YC8pxiE7%2F9Bi%2FKRbaQ%2BDnCvBUL4qDOUT7hsha0dXMt7HoK0eqBwrnuwaH1w5eHAG4A%3D%3D'
MOLIT_RENT_API_KEY = 'CzO0x1MCWDpXH4ZfHg66YC8pxiE7%2F9Bi%2FKRbaQ%2BDnCvBUL4qDOUT7hsha0dXMt7HoK0eqBwrnuwaH1w5eHAG4A%3D%3D' # 전월세 API 키 

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
    dong_name = txt('법정동') or txt('법정동명') or txt('법정동주소')
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
        'region_code': txt('지역코드') or txt('lawdCd') or '',
        'txt_func': txt
    }

def _parse_transactions(xml_bytes: bytes):
    """XML 응답을 파싱하여 거래 데이터 추출 (매매)"""
    root = ET.fromstring(xml_bytes)
    items = []
    for it in root.findall('.//item'):
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

def _parse_rent_transactions(xml_bytes: bytes):
    """XML 응답을 파싱하여 전월세 거래 데이터 추출"""
    root = ET.fromstring(xml_bytes)
    items = []
    for it in root.findall('.//item'):
        common = _parse_common_fields(it)
        jeonse_price_raw = common['txt_func']('보증금') or common['txt_func']('보증금액') or common['txt_func']('deposit') or ''
        monthly_rent_raw = common['txt_func']('월세금액') or common['txt_func']('월세') or common['txt_func']('rent') or ''
        
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
            '거래일자': common['deal_date'],
            '지번': common['jibun'],
            '지역코드': common['region_code'],
        })
    return items

def _save_transactions_to_db(db, RealTransaction, lawd_cd: str, deal_ymd: str, region: str, dong: str, transactions: list):
    """실거래 데이터를 DB에 저장"""
    try:
        for tx in transactions:
            existing = RealTransaction.query.filter_by(
                lawd_cd=lawd_cd, deal_ymd=deal_ymd,
                apt_name=tx.get('아파트'), dong_name=tx.get('법정동'),
                price=tx.get('거래금액'), deal_date=tx.get('거래일자')
            ).first()
            if not existing:
                rt = RealTransaction(
                    lawd_cd=lawd_cd, deal_ymd=deal_ymd, region=region, dong=dong,
                    apt_name=tx.get('아파트'), dong_name=tx.get('법정동'),
                    price=tx.get('거래금액'), price_raw=tx.get('거래금액원문'),
                    area=tx.get('전용면적'), floor=tx.get('층'),
                    build_year=tx.get('건축년도'), deal_date=tx.get('거래일자'),
                    jibun=tx.get('지번'), region_code=tx.get('지역코드')
                )
                db.session.add(rt)
        db.session.commit()
    except Exception:
        db.session.rollback()

def _load_transactions_from_db(RealTransaction, lawd_cd: str, deal_ymd: str, dong: str = None):
    """DB에서 실거래 데이터 불러오기 (동 이름 유연하게 매칭)"""
    try:
        # 먼저 lawd_cd와 deal_ymd로 필터링
        query = RealTransaction.query.filter_by(lawd_cd=lawd_cd, deal_ymd=deal_ymd)
        transactions = query.all()
        if not transactions:
            return None
        
        # Python에서 동 이름 필터링 (SQLite의 endswith 제한 회피)
        result = [{
            '아파트': tx.apt_name, '법정동': tx.dong_name, '전용면적': tx.area,
            '층': tx.floor, '건축년도': tx.build_year, '거래금액': tx.price,
            '거래금액원문': tx.price_raw, '거래일자': tx.deal_date,
            '지번': tx.jibun, '지역코드': tx.region_code,
        } for tx in transactions]
        
        # 동 이름이 있으면 유연하게 필터링 (결과가 없으면 원본 반환)
        if dong:
            filtered = _filter_by_dong(result, dong)
            # 필터링 결과가 있으면 사용, 없으면 원본 사용 (너무 엄격한 필터링 방지)
            result = filtered if filtered and len(filtered) > 0 else result
        
        return result if result else None
    except Exception:
        return None

def _fetch_rtms(lawd_cd: str, deal_ymd: str, page_no: int = 1, rows: int = 50):
    """국토부 RTMS API 호출 (매매)"""
    api_key = _get_api_key()
    if not api_key:
        return {'error': 'API key is missing. Set MOLIT_API_KEY.'}, 500
    encoded_key = api_key if '%' in api_key else quote(api_key, safe='')
    url = f"http://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev?serviceKey={encoded_key}&LAWD_CD={lawd_cd}&DEAL_YMD={deal_ymd}&pageNo={page_no}&numOfRows={rows}"
    try:
        resp = requests.get(url, timeout=8)
        if resp.status_code != 200:
            return {'error': f'HTTP {resp.status_code}', 'detail': resp.text[:500]}, resp.status_code
        return {'transactions': _parse_transactions(resp.content)}, 200
    except requests.exceptions.HTTPError as e:
        return {'error': f'HTTP {e.response.status_code}', 'detail': (resp.text[:500] if hasattr(resp, 'text') else str(e))}, e.response.status_code
    except requests.exceptions.Timeout:
        return {'error': 'Request timed out'}, 504
    except requests.exceptions.RequestException as e:
        return {'error': f'Network error: {e}'}, 502
    except ET.ParseError:
        return {'error': 'Failed to parse XML response'}, 500
    except Exception as e:
        return {'error': f'Unexpected error: {str(e)}'}, 500

def _fetch_rent_rtms(lawd_cd: str, deal_ymd: str, page_no: int = 1, rows: int = 50):
    """국토부 RTMS API 호출 (전월세)"""
    api_key = _get_api_key(rent=True)
    if not api_key:
        # 전월세 API 키가 없으면 매매 API 키 사용 (fallback)
        api_key = _get_api_key(rent=False)
    if not api_key:
        return {'error': 'API key is missing. Set MOLIT_RENT_API_KEY or MOLIT_API_KEY.'}, 500
    encoded_key = api_key if '%' in api_key else quote(api_key, safe='')
    url = f"https://apis.data.go.kr/1613000/RTMSDataSvcAptRent/getRTMSDataSvcAptRent?serviceKey={encoded_key}&LAWD_CD={lawd_cd}&DEAL_YMD={deal_ymd}&pageNo={page_no}&numOfRows={rows}"
    try:
        resp = requests.get(url, timeout=8)
        if resp.status_code != 200:
            return {'error': f'HTTP {resp.status_code}', 'detail': resp.text[:500]}, resp.status_code
        return {'transactions': _parse_rent_transactions(resp.content)}, 200
    except requests.exceptions.HTTPError as e:
        return {'error': f'HTTP {e.response.status_code}', 'detail': (resp.text[:500] if hasattr(resp, 'text') else str(e))}, e.response.status_code
    except requests.exceptions.Timeout:
        return {'error': 'Request timed out'}, 504
    except requests.exceptions.RequestException as e:
        return {'error': f'Network error: {e}'}, 502
    except ET.ParseError:
        return {'error': 'Failed to parse XML response'}, 500
    except Exception as e:
        return {'error': f'Unexpected error: {str(e)}'}, 500

def _load_heatmap_from_db(HeatmapData):
    """DB에서 히트맵 데이터 불러오기 (score는 정수로 저장되어 있지만, Float로 반환하여 일관성 유지)"""
    try:
        heatmap_records = HeatmapData.query.all()
        # DB에 저장된 정수 값을 Float로 변환 (소수점 표시를 위해)
        return [{'region': h.region, 'score': float(h.score), 'lat': h.lat, 'lng': h.lng} for h in heatmap_records] if heatmap_records else None
    except Exception:
        return None

def _save_heatmap_to_db(db, HeatmapData, heatmap_data):
    """히트맵 데이터를 DB에 저장 (score는 정수로 저장, Float 타입이면 소수점 첫째 자리까지)"""
    try:
        for data in heatmap_data:
            existing = HeatmapData.query.filter_by(region=data['region']).first()
            # score를 정수로 변환 (DB는 Integer 타입이므로)
            score_value = int(round(data['score'])) if isinstance(data['score'], float) else data['score']
            if existing:
                existing.score, existing.lat, existing.lng = score_value, data['lat'], data['lng']
                # 한국 시간 (UTC+9)
                kst = timezone(timedelta(hours=9))
                existing.updated_at = datetime.now(kst)
            else:
                db.session.add(HeatmapData(region=data['region'], score=score_value, lat=data['lat'], lng=data['lng']))
        db.session.commit()
    except Exception:
        db.session.rollback()

def _calculate_jeonse_rate_score(properties):
    """매물 리스트에서 평균 전세가율을 계산하여 점수로 변환"""
    if not properties:
        return 0.0
    properties_with_rate = [p for p in properties if p.get('jeonse_rate') is not None and p.get('jeonse_rate') > 0]
    if not properties_with_rate:
        return 0.0
    avg_rate = sum(p['jeonse_rate'] for p in properties_with_rate) / len(properties_with_rate)
    # 전세가율을 소수점 첫째 자리까지 반올림 (일관성 유지)
    return round(avg_rate, 1)

def get_heatmap_data(db=None, HeatmapData=None, RealTransaction=None, force_update=False):
    """히트맵 데이터를 반환하는 함수 (전세가율 기반, 자동 계산)"""
    # 기본 지역 목록 (50개 동)
    default_regions = [
        # 강남구
        {'region': '청담동', 'lat': 37.5196, 'lng': 127.0473},
        {'region': '역삼동', 'lat': 37.5000, 'lng': 127.0364},
        {'region': '삼성동', 'lat': 37.5146, 'lng': 127.0491},
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
        {'region': '삼성동', 'lat': 37.4700, 'lng': 126.9300},
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
    
    # DB에서 기존 데이터 로드
    db_data_dict = {}
    if not force_update and db and HeatmapData:
        db_data = _load_heatmap_from_db(HeatmapData)
        if db_data and len(db_data) > 0:
            # DB 데이터를 딕셔너리로 변환 (빠른 조회를 위해)
            db_data_dict = {d['region']: d for d in db_data}
            print(f"[히트맵] DB에서 {len(db_data_dict)}개 지역 데이터 로드")
    
    # 전세가율 기반으로 자동 계산 (DB에 없는 지역만)
    # 중요: 히트맵 데이터 생성 시에는 /analyze API를 호출하지 않음
    # 히트맵 데이터는 DB에 저장된 데이터만 사용하거나 기본값(0) 사용
    heatmap_data = []
    for region_info in default_regions:
        region = region_info['region']
        
        # DB에 데이터가 있으면 사용
        if region in db_data_dict:
            heatmap_data.append(db_data_dict[region])
            continue
        
        # DB에 없으면 기본 점수 0으로 설정 (API 호출하지 않음)
        # 히트맵 데이터는 사용자가 검색할 때만 /analyze API를 호출하도록 변경
        heatmap_data.append({
            'region': region,
            'score': 0,
            'lat': region_info['lat'],
            'lng': region_info['lng']
        })
    
    # 계산된 데이터를 DB에 저장
    if db and HeatmapData and heatmap_data:
        try:
            _save_heatmap_to_db(db, HeatmapData, heatmap_data)
            print(f"[히트맵] {len(heatmap_data)}개 지역 데이터 계산 완료 및 DB 저장")
        except Exception as e:
            print(f"[히트맵] DB 저장 중 에러: {str(e)}")
    
    # 데이터가 비어있어도 최소한 기본 지역 목록은 반환 (점수 0으로라도)
    if not heatmap_data:
        print("[히트맵] 경고: 계산된 데이터가 없습니다. 기본 지역 목록을 점수 0으로 반환합니다.")
        heatmap_data = [{'region': r['region'], 'score': 0, 'lat': r['lat'], 'lng': r['lng']} for r in default_regions]
    
    return heatmap_data

def _filter_by_dong(transactions, dong):
    """동 이름으로 거래 데이터 필터링 (유연한 매칭)"""
    if not dong or not transactions:
        return transactions
    filtered = []
    dong_clean = dong.replace('동', '').replace('가', '').replace('리', '').strip()
    dong_with_suffix = dong if dong.endswith(('동', '가', '리')) else dong
    
    for t in transactions:
        dong_name = t.get('법정동', '').strip()
        if not dong_name:
            # 동 이름이 없으면 포함 (다른 필터로 걸러짐)
            continue
        
        # 정확한 매칭 우선
        if dong_name == dong or dong_name == dong_with_suffix:
            filtered.append(t)
            continue
        
        # 끝부분 매칭 (예: "청담동" == "청담동")
        if dong_name.endswith(dong) or dong_name.endswith(dong_with_suffix):
            filtered.append(t)
            continue
        
        # 동 이름만 추출하여 매칭 (예: "청담" == "청담동")
        if dong_clean:
            dong_name_clean = dong_name.replace('동', '').replace('가', '').replace('리', '').strip()
            # 정확히 일치하는 경우
            if dong_name_clean == dong_clean:
                filtered.append(t)
                continue
            # 끝부분이 일치하는 경우 (예: "청담동" == "청담동1가"의 "청담" 부분)
            if dong_name.endswith(dong_clean + '동') or dong_name.endswith(dong_clean + '가') or dong_name.endswith(dong_clean + '리'):
                filtered.append(t)
                continue
            # 포함 관계 확인 (예: "석촌"이 "석촌동"에 포함)
            if dong_clean in dong_name_clean or dong_name_clean in dong_clean:
                filtered.append(t)
                continue
    
    # 필터링된 결과가 있으면 반환, 없으면 원래 데이터 반환 (너무 엄격한 필터링 방지)
    return filtered if filtered else transactions

def fetch_properties_by_region(region, db=None, RealTransaction=None):
    """지역명을 받아 국토부 API를 조회하고, 매물 리스트를 반환하는 함수 (전세가율 포함) - 최적화 버전"""
    if not region:
        return []
    
    dong = _extract_dong(region)
    lawd_cd = _resolve_lawd_cd(region)
    
    # 법정동 코드가 기본값(종로구)이고 지역명이 종로구가 아닌 경우 경고
    if lawd_cd == '11110' and '종로' not in region and '종로동' not in region:
        print(f"[경고] 지역명 '{region}'에 대한 법정동 코드를 찾지 못해 기본값(종로구)을 사용합니다.")
        print(f"[경고] 추출된 동 이름: '{dong}', 지역명: '{region}'")
        # 서초동의 경우 명시적으로 처리
        if '서초' in region and ('동' in region or dong == '서초동'):
            print(f"[수정] 서초동을 서초구(11650)로 명시적으로 매핑합니다.")
            lawd_cd = '11650'  # 서초구 코드
    
    # 서초동 명시적 처리 (위에서 처리되지 않은 경우)
    if '서초' in region and ('동' in region or dong == '서초동') and lawd_cd != '11650':
        print(f"[수정] 서초동을 서초구(11650)로 명시적으로 매핑합니다.")
        lawd_cd = '11650'
    
    lawd_cds_to_try = [lawd_cd]
    if dong and dong != region:
        dong_to_gu = {
            '청담동': '강남구', '역삼동': '강남구', '삼성동': '강남구', '대치동': '강남구',
            '압구정동': '강남구', '논현동': '강남구', '신사동': '강남구', '도곡동': '강남구',
            '화곡동': '강서구', '등촌동': '강서구', '마곡동': '강서구', '가양동': '강서구',
            '서교동': '마포구', '연남동': '마포구', '성산동': '마포구', '합정동': '마포구',
            '문래동': '영등포구', '여의도동': '영등포구', '당산동': '영등포구', '신길동': '영등포구',
            '대림동': '영등포구', '양평동': '영등포구', '도림동': '영등포구',
            '독산동': '금천구', '가산동': '금천구', '시흥동': '금천구',
            '신림동': '관악구', '봉천동': '관악구', '남현동': '관악구',
            '잠실동': '송파구', '신천동': '송파구', '방이동': '송파구', '석촌동': '송파구',
            '명일동': '강동구', '고덕동': '강동구', '상일동': '강동구',
            '사직동': '종로구', '삼청동': '종로구', '혜화동': '종로구',
            '서초동': '서초구',
        }
        if dong in dong_to_gu:
            gu_name = dong_to_gu[dong]
            for gu, code in SEOUL_SIGUNGU_CODES.items():
                if gu == gu_name:
                    lawd_cds_to_try = [code]
                    break
        else:
            # dong_to_gu에 없는 동은 _resolve_lawd_cd에서 찾은 lawd_cd 사용
            # (예: 석촌동은 송파구이므로 11710)
            pass
    
    # 한국 시간 (UTC+9)
    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst)
    # 조회 범위 제한: 3개월 -> 2개월로 축소
    # 연도 변경을 고려한 날짜 계산
    deal_ymds = []
    for i in range(2):
        year = now.year
        month = now.month - i
        # 월이 0 이하가 되면 이전 연도로 이동
        while month <= 0:
            month += 12
            year -= 1
        # 월이 12를 초과하면 다음 연도로 이동
        while month > 12:
            month -= 12
            year += 1
        deal_ymds.append(f"{year}{month:02d}")
    
    # DB에서 먼저 매매 데이터 조회 (캐싱 활용, 정확한 동 이름 필터링)
    sale_properties = []
    if db and RealTransaction:
        for lawd_cd_try in lawd_cds_to_try:
            for deal_ymd in deal_ymds:
                db_transactions = _load_transactions_from_db(RealTransaction, lawd_cd_try, deal_ymd, dong)
                if db_transactions:
                    # _load_transactions_from_db에서 이미 필터링했으므로 추가 필터링 불필요
                    for item in db_transactions:
                        price = item.get('거래금액', 0)
                        sale_properties.append({
                            'apt_name': item.get('아파트', '이름 없음'),
                            'dong_name': item.get('법정동', ''),
                            'jibun': item.get('지번', ''),
                            'area': item.get('전용면적', ''),
                            'floor': item.get('층', ''),
                            'build_year': item.get('건축년도', ''),
                            'sale_price': price,
                            'sale_price_formatted': _format_price_to_eok(price) if price else item.get('거래금액원문', '가격 정보 없음'),
                            'deal_date': item.get('거래일자', ''),
                            'raw_data': item
                        })
    
    # DB에 없는 데이터만 API로 조회 (병렬 처리)
    # 전세 데이터는 DB에 저장되지 않으므로 항상 API 호출 필요
    api_tasks = []
    for lawd_cd_try in lawd_cds_to_try:
        for deal_ymd in deal_ymds:
            # 매매 데이터는 DB에 있는지 확인
            sale_in_db = False
            if db and RealTransaction:
                db_transactions = _load_transactions_from_db(RealTransaction, lawd_cd_try, deal_ymd, dong)
                if db_transactions:
                    sale_in_db = True
            
            # 매매 데이터가 DB에 없으면 API 호출
            if not sale_in_db:
                api_tasks.append(('sale', lawd_cd_try, deal_ymd))
            
            # 전세 데이터는 항상 API 호출 (DB에 저장되지 않음)
            api_tasks.append(('rent', lawd_cd_try, deal_ymd))
    
    # 병렬 처리로 API 호출
    def fetch_task(task_type, lawd_cd_try, deal_ymd):
        if task_type == 'sale':
            result, status_code = _fetch_rtms(lawd_cd_try, deal_ymd, page_no=1, rows=100)
            if status_code == 200:
                transactions = _filter_by_dong(result.get('transactions', []), dong)
                return ('sale', transactions)
        else:  # rent
            result, status_code = _fetch_rent_rtms(lawd_cd_try, deal_ymd, page_no=1, rows=100)
            if status_code == 200:
                transactions = _filter_by_dong(result.get('transactions', []), dong)
                return ('rent', transactions)
            return None
    rent_properties = []
    rent_api_count = 0
    rent_success_count = 0
    if api_tasks:
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = {executor.submit(fetch_task, task_type, lawd_cd, deal_ymd): (task_type, lawd_cd, deal_ymd) 
            for task_type, lawd_cd, deal_ymd in api_tasks}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    task_type, transactions = result
                    if task_type == 'sale':
                        for item in transactions:
                            price = item.get('거래금액', 0)
                            sale_properties.append({
                                'apt_name': item.get('아파트', '이름 없음'),
                                'dong_name': item.get('법정동', ''),
                                'jibun': item.get('지번', ''),
                                'area': item.get('전용면적', ''),
                                'floor': item.get('층', ''),
                                'build_year': item.get('건축년도', ''),
                                'sale_price': price,
                                'sale_price_formatted': _format_price_to_eok(price) if price else item.get('거래금액원문', '가격 정보 없음'),
                                'deal_date': item.get('거래일자', ''),
                                'raw_data': item
                            })
                    else:  # rent
                        rent_api_count += 1
                        if transactions:
                            rent_success_count += 1
                        for item in transactions:
                            jeonse_price = item.get('전세금액', 0)
                            monthly_rent = item.get('월세금액', 0)
                            
                            # 전세금액이 있거나 월세가 있는 경우 추가 (전세+월세 혼합도 포함)
                            if jeonse_price or monthly_rent:
                                # 전세+월세 혼합의 경우 전세금액을 우선 사용
                                # 전세금액이 없으면 월세의 보증금을 전세금액으로 간주하지 않음
                                if jeonse_price:
                                    # 전세가가 합리적인 범위인지 확인 (최소 1000만원 이상)
                                    if jeonse_price >= 1000:
                                        rent_properties.append({
                                            'apt_name': item.get('아파트', '이름 없음'),
                                            'dong_name': item.get('법정동', ''),
                                            'jibun': item.get('지번', ''),
                                            'area': item.get('전용면적', ''),
                                            'floor': item.get('층', ''),
                                            'jeonse_price': jeonse_price,
                                            'deal_date': item.get('거래일자', ''),
                                            'raw_data': item
                                        })
                                    else:
                                        print(f"[경고] 전세가({jeonse_price}만원)가 너무 낮습니다. 데이터 오류 가능성. 제외합니다.")
        
    # 매칭 로직 최적화: O(n*m) -> O(n) (딕셔너리 사용)
    def parse_area(area_str):
            if not area_str:
                return None
            try:
                match = re.search(r'(\d+\.?\d*)', str(area_str))
                return float(match.group(1)) if match else None
            except (ValueError, TypeError):
                return None
    
    # 전세 매물을 아파트명+동명으로 그룹화 (O(n))
    rent_by_key = {}
    for rent in rent_properties:
        key = (rent['apt_name'], rent['dong_name'])
        if key not in rent_by_key:
            rent_by_key[key] = []
        rent_by_key[key].append(rent)
    
    matched_properties = []
    for sale in sale_properties:
        matched_rent = None
        best_match_score = 0
        sale_area = parse_area(sale.get('area', ''))
        sale_date = parse_date(sale.get('deal_date', ''))  # pyright: ignore[reportUndefinedVariable]
        
        # 해당 아파트+동의 전세 매물만 확인 (O(1) 조회)
        key = (sale['apt_name'], sale['dong_name'])
        candidate_rents = rent_by_key.get(key, [])
        
        for rent in candidate_rents:
            match_score = 0
            if sale.get('jibun') and rent.get('jibun'):
                if sale['jibun'] == rent['jibun']:
                    match_score += 3
            elif not sale.get('jibun') and not rent.get('jibun'):
                match_score += 1
            rent_area = parse_area(rent.get('area', ''))
            if sale_area and rent_area:
                area_diff = abs(sale_area - rent_area)
                if area_diff < 1:
                    match_score += 2
                elif area_diff < 5:
                    match_score += 1
            if sale.get('floor') and rent.get('floor') and sale['floor'] == rent['floor']:
                match_score += 1
            if match_score >= best_match_score and rent.get('jeonse_price'):
                if match_score > best_match_score:
                    best_match_score = match_score
                    matched_rent = rent
                elif match_score == best_match_score:
                    rent_date = parse_date(rent.get('deal_date', ''))  # pyright: ignore[reportUndefinedVariable]
                    if rent_date and sale_date:
                        date_diff = abs((rent_date - sale_date).days)
                        if date_diff <= 180:
                            current_rent_date = parse_date(matched_rent.get('deal_date', '')) if matched_rent else None  # pyright: ignore[reportUndefinedVariable]
                            if not current_rent_date or (rent_date > current_rent_date):
                                matched_rent = rent
                    elif rent_date and not matched_rent:
                        matched_rent = rent
                elif not matched_rent:
                    best_match_score = match_score
                    matched_rent = rent
        if best_match_score < 1:
            matched_rent = None
        prop_data = {
            'name': f"{sale['apt_name']} ({sale['area']}㎡, {sale['floor']}층)" if sale['area'] and sale['floor'] else sale['apt_name'],
            'address': f"{region} {sale['dong_name']} {sale['jibun']}",
            'price': sale['sale_price_formatted'],
            'price_raw': sale['sale_price'],
            'area': sale['area'],
            'floor': sale['floor'],
            'build_year': sale['build_year'],
            'deal_date': sale['deal_date'],
            'raw_data': sale['raw_data']
        }
        if matched_rent and matched_rent['jeonse_price'] and sale['sale_price']:
            jeonse_price = matched_rent['jeonse_price']
            sale_price = sale['sale_price']
            
            # 전세가와 매매가가 합리적인 범위인지 확인
            # 전세가는 일반적으로 매매가의 50-90% 범위
            # 만약 전세가가 매매가의 1% 미만이면 데이터 오류로 간주
            if jeonse_price > 0 and sale_price > 0:
                if jeonse_price < sale_price * 0.01:
                    print(f"[경고] 전세가({jeonse_price}만원)가 매매가({sale_price}만원)의 1% 미만입니다. 데이터 오류 가능성.")
                    # 이 경우 전세가율을 계산하지 않음
                    prop_data['jeonse_price'] = None
                    prop_data['jeonse_price_formatted'] = None
                    prop_data['jeonse_rate'] = None
                    prop_data['risk_level'] = 'unknown'
                else:
                    jeonse_rate = (jeonse_price / sale_price) * 100 if sale_price > 0 else None
                    prop_data['jeonse_price'] = jeonse_price
                    prop_data['jeonse_price_formatted'] = _format_price_to_eok(jeonse_price)
                    prop_data['jeonse_rate'] = round(jeonse_rate, 2) if jeonse_rate else None
            else:
                jeonse_rate = None
                prop_data['jeonse_price'] = None
                prop_data['jeonse_price_formatted'] = None
                prop_data['jeonse_rate'] = None
            if jeonse_rate and jeonse_rate >= 80:
                prop_data['risk_level'] = 'high'
            elif jeonse_rate and jeonse_rate >= 60:
                prop_data['risk_level'] = 'medium'
            else:
                prop_data['risk_level'] = 'low'
        else:
            prop_data['jeonse_price'] = None
            prop_data['jeonse_price_formatted'] = None
            prop_data['jeonse_rate'] = None
            prop_data['risk_level'] = 'unknown'
        matched_properties.append(prop_data)
    return matched_properties

def analyze_property_warnings(prop):
    """매물 위험 요소 분석"""
    warnings = []
    if '빌라' in prop.get('name', '') or '오피스텔' in prop.get('name', ''):
        warnings.append('빌라/오피스텔은 아파트보다 전세사기 위험이 높을 수 있습니다.')
    jeonse_rate = prop.get('jeonse_rate')
    if jeonse_rate:
        if jeonse_rate >= 80:
            warnings.append(f'전세가율이 {jeonse_rate}%로 매우 높습니다. 전세사기 위험이 높을 수 있습니다.')
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
