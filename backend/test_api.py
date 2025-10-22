import requests
import xml.etree.ElementTree as ET # XML 파싱을 위한 라이브러리
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import json

app = Flask(__name__)
CORS(app)

# 발급받은 API 키와 테스트하고 싶은 지역/기간 정보를 URL에 넣습니다.
# (API 활용 가이드 문서를 참고하여 URL을 만드세요)

API_KEY = "CzO0x1MCWDpXH4ZfHg66YC8pxiE7%2F9Bi%2FKRbaQ%2BDnCvBUL4qDOUT7hsha0dXMt7HoK0eqBwrnuwaH1w5eHAG4A%3D%3D"
LAWD_CD = "11110"
DEAL_YMD = "202401"
URL = f"http://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev?serviceKey=CzO0x1MCWDpXH4ZfHg66YC8pxiE7%2F9Bi%2FKRbaQ%2BDnCvBUL4qDOUT7hsha0dXMt7HoK0eqBwrnuwaH1w5eHAG4A%3D%3D&LAWD_CD={LAWD_CD}&DEAL_YMD={DEAL_YMD}&pageNo=1&numOfRows=10"

@app.route('/searchscan')
def searchscan():
    return render_template('searchscan.html')

@app.route('/analyze')
def analyze():
    region = request.args.get('region', '').strip()
    
    if not region:
        return jsonify({'properties': []})
    
    # 로컬 mock 데이터 또는 실제 API 호출
    # 현재는 샘플 데이터 반환
    properties = [
        {
            'name': f'{region} 101동 505호',
            'warnings': [
                '전세가율 90% 이상 (위험)',
                '최근 3개월 거래 없음',
                '건물 준공 후 20년 이상'
            ],
            'checklist': [
                '등기부등본 열람 (필수)',
                '건축물대장 확인',
                '임대인 신분증 대조',
                '선순위 세입자 확인서',
                '관리비·세금 체납 확인'
            ]
        },
        {
            'name': f'{region} 202동 1201호',
            'warnings': [
                '시세 대비 -15% 저가',
                '소유자 변경 이력 많음'
            ],
            'checklist': [
                '등기부등본 열람 (필수)',
                '건축물대장 확인',
                '임대인 신분증 대조',
                '전입세대 확인서',
                '국토부 실거래가 조회'
            ]
        },
        {
            'name': f'{region} 스카이빌 303호',
            'warnings': [],
            'checklist': [
                '등기부등본 열람 (필수)',
                '건축물대장 확인',
                '임대인 신분증 대조'
            ]
        }
    ]
    
    return jsonify({'properties': properties})

# API에 데이터 요청 보내기
r = requests.get(URL)
print("status:", r.status_code)
print("headers:", r.headers)
print("body:", r.text)
try:
    response = requests.get(URL, timeout=5)
    # ... (성공 시 데이터 처리)

except requests.exceptions.ConnectionError:
    print("API 서버에 연결할 수 없습니다. 서버가 점검 중이거나 다운된 것 같습니다.")
except requests.exceptions.Timeout:
    print("서버에서 응답이 없습니다.")
    
if response.status_code == 200:
    print("--- 데이터 해석 시작 ---")
    # 1. 서버가 보내준 XML 텍스트를 파싱 가능한 객체로 변환합니다.
    root = ET.fromstring(response.content)

    # 2. 원하는 데이터가 있는 위치를 찾아 반복합니다. (API 문서 참고)
    for item in root.findall('.//item'):
        # 3. '매매가'와 '아파트' 이름을 찾아서 추출하고 공백을 제거합니다.
        price = item.find('매매가').text.strip()
        apt_name = item.find('아파트').text.strip()
        print(f"아파트: {apt_name}, 매매가: {price}원")
else:
    print(f"에러 발생: {response.status_code}")
    print(response.text)

# 요청 결과 출력하기
# # --- 실제 api 사용 ---


# import json # ◀◀◀ 로컬 json 파일을 읽기 위해 json을 사용

# # (requests, xml.etree.ElementTree는 지금 당장 필요 없으므로 지워도 됩니다)

# def analyze_property(address):
#     print(f"\n--- '{address}' 분석 시작 ---\n")
#     print("--- (알림) 실제 API가 아닌 로컬 모의 데이터를 사용합니다. ---")

#     # --- ▼▼▼ 바로 이 부분이 바뀝니다 ▼▼▼ ---

#     # 1. (지우는 부분) 실제 API 서버에 접속할 URL 만들기
#     # API_KEY = "..."
#     # URL = f"http://openapi.molit.go.kr/..."

#     # 2. (지우는 부분) 인터넷으로 서버에 연결 시도
#     # response = requests.get(URL)

#     # 3. (추가하는 부분) 로컬 파일에서 데이터를 직접 읽어옵니다.
#     with open('mock_data.json', 'r', encoding='utf-8') as f:
#         items = json.load(f) # json 파일에서 item 목록을 바로 가져옴

#     # --- ▲▲▲ 여기까지 바뀝니다 ▲▲▲ ---

#     # 이제 'items' 변수에는 mock_data.json의 내용이 들어있습니다.
#     # 아래의 데이터 분석 로직은 거의 수정할 필요가 없습니다.
#     for item in items:
#         # ... (데이터 분석 및 체크리스트 생성 로직)
#         price = item['매매가'] # XML 방식(.find)이 아닌 JSON 방식(키)으로 수정
#         print(f"매매가: {price}원")


# # 메인 로직 실행
# analyze_property("서울시 강남구 (모의 데이터)")

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)