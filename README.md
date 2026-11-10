#  세이프홈 (SafeHome)

전세사기 예방을 위한 종합 플랫폼입니다. 등기부등본 분석부터 지역별 위험도 확인까지 매물의 안전성을 분석해드립니다.

##  주요 기능

### 매물 분석
1. 검색/스캔 페이지(`/searchscan`)에서 지역과 매물 정보 입력
2. 등기부등본 정보를 기반으로 자동 분석
3. 전세가율 계산 및 위험도 점수 산출
4. 위험 요소 경고 및 안전 체크리스트 제공

### 히트맵
1. 지도 페이지(`/map`)에서 지역별 위험도 확인
2. 색상으로 구분된 위험도 시각화 (빨강: 위험, 노랑: 주의, 초록: 안전)
3. 지역 클릭하여 상세 정보 확인
4. 실거래 데이터 표시 및 분석

### 자가진단 체크리스트
1. 자가진단 페이지(`/self-check`)에서 체크리스트 진행
2. 각 항목별 안전도 점검
3. 종합 결과 및 권장사항 확인

###  사기 유형 학습
1. 깡통전세, 신탁사기 등 대표적인 전세사기 유형 학습
2. 각 사기 유형별 예방법 및 대응 방법 제공

### 리뷰 시스템
1. 리뷰 페이지(`/reviews`)에서 지역별 리뷰 확인
2. 마이페이지에서 내 리뷰 관리 (작성, 수정, 삭제)
3. 평점 및 리뷰 내용 작성

 ### 사용자 기능
1. 회원가입 및 로그인
2. 즐겨찾기 지역 저장
3. 리뷰 작성, 수정, 삭제
4. 신고 기능
5. 알림 시스템
6. 마이페이지에서 통합 관리


##  기술 스택

### Frontend
- **HTML5** / **CSS3** / **JavaScript (Vanilla JS)**
- **Jinja2** - 템플릿 엔진
- **Kakao Maps API** - 지도 서비스
- **React** (마이크로 프론트엔드) - 지도 컴포넌트만 React로 빌드
- **Vite** - React 빌드 도구


### Backend
- **Python 3.13**
- **Flask** - 웹 프레임워크 (템플릿 기반 서버 사이드 렌더링)
- **Flask-SQLAlchemy** - ORM
- **Flask-Migrate** - 데이터베이스 마이그레이션
- **Flask-Bcrypt** - 비밀번호 암호화
- **Flask-Login** - 사용자 인증
- **Flask-CORS** - CORS 처리
- **Requests** - 외부 API 호출
- **SQLite** - 데이터베이스


### 외부 API
- **Kakao Maps API** - 지도 및 주소 검색
- **국토교통부 실거래 공개시스템** - 실거래 데이터

##  설치 방법

### 1. 저장소 클론
```bash
git clone https://github.com/Baegopayolo/safehome.git
cd safehome
```

### 2. Python 가상 환경 생성 및 활성화
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Python 의존성 설치
```bash
pip install -r requirements.txt
```

### 4. 지도 모듈 빌드 (선택사항)
지도 컴포넌트를 React로 빌드하려면:

```bash
cd map-module
npm install
npm run build
```

빌드가 완료되면 `static/js/map-react.js` 파일이 생성됩니다.

### 4. 지도 모듈 빌드 (선택사항)
지도 컴포넌트를 React로 빌드하려면:

```bash
cd map-module
npm install
npm run build
```

빌드가 완료되면 `static/js/map-react.js` 파일이 생성됩니다.

> **참고**: 현재는 기존 `map.js`를 사용 중이며, React 빌드는 향후 마이그레이션을 위한 것입니다.

### 5. 환경 변수 설정
`.env` 파일을 생성하고 다음 내용을 추가하세요:

```env
KAKAO_APP_KEY=your_kakao_app_key_here
SECRET_KEY=
```

`SECRET_KEY`는 필수입니다. 빈 값이나 기존 공개 예시 키를 사용하면 웹 서버와 Flask 관리 명령은 시작되지 않습니다.
로컬 개발용 키는 `python -c "import secrets; print(secrets.token_hex(32))"`로 생성해 설정하세요.
실제 키와 `.env`는 Git에 커밋하지 마세요. Flask CLI는 `.env`를 읽으며, Python 직접 실행이나 운영 서비스는 프로세스 환경에 키를 전달해야 합니다.
운영 웹 서비스와 수집 서비스에는 기존 비공개 키를 유지하세요. 키를 변경하면 기존 로그인 세션은 무효화됩니다.

### 6. 데이터베이스 초기화
```bash
python -m flask --app backend/app db upgrade
```

앱 시작 시 DB를 자동 생성하지 않습니다. 기존 운영 DB를 백업한 후 마이그레이션을 실행하세요.

### 7. 샘플 데이터 생성 (선택사항)
```bash
cd backend
python seed_data.py
```

##  실행 방법

### 개발 서버 실행
```bash
cd backend
python app.py
```

서버가 실행되면 브라우저에서 `http://127.0.0.1:5000` 또는 `http://localhost:5000`으로 접속할 수 있습니다.


### 테스트 계정 (seed_data.py 실행 시)
- **사용자명**: `test`
- **비밀번호**: `test123`

##  프로젝트 구조

```
safehome/
├── backend/                 # Flask 백엔드 애플리케이션
│   ├── app.py              # Flask 앱 메인 파일
│   ├── models.py           # 데이터베이스 모델
│   ├── utils.py            # 유틸리티 함수 (매물 분석, 히트맵 등)
│   ├── time_utils.py       # 시간 관련 유틸리티
│   ├── seed_data.py        # 샘플 데이터 생성
│   ├── reset_password.py   # 비밀번호 재설정
│   ├── routes/             # 라우트 핸들러
│   │   ├── pages.py        # 페이지 라우트 (템플릿 렌더링)
│   │   ├── auth.py         # 인증 라우트 (로그인, 회원가입, 마이페이지)
│   │   └── api.py          # API 라우트 (JSON 응답)
│   └── reset/              # 데이터 초기화 스크립트
│       ├── reset_data.py
│       ├── 초기화.bat
│       └── 초기화.ps1
│
├── frontend/               # Flask 템플릿 (서버 사이드 렌더링)
│   ├── index.html          # 메인 페이지
│   ├── map.html            # 지도 페이지
│   ├── searchscan.html     # 검색/스캔 페이지
│   ├── self-check.html     # 자가진단 페이지
│   ├── scam-types.html     # 사기 유형 페이지
│   ├── reviews.html        # 리뷰 페이지
│   ├── about.html          # 소개 페이지
│   ├── faq.html            # FAQ 페이지
│   ├── intro.html          # 인트로 페이지
│   ├── Login/              # 로그인 관련 페이지
│   │   ├── login.html
│   │   ├── register.html
│   │   ├── mypage.html     # 마이페이지
│   │   └── logout.html
│   └── _*.html             # 공통 컴포넌트
│       ├── _navbar.html    # 네비게이션 바
│       ├── _footer.html    # 푸터
│       ├── _left_sidebar.html   # 왼쪽 사이드바
│       └── _right_sidebar.html  # 오른쪽 사이드바
│
├── static/                 # 정적 파일
│   ├── css/                # 스타일시트
│   │   ├── 00_reset.css
│   │   ├── 01_layout.css
│   │   ├── 02_components.css
│   │   ├── 03_pages_index.css
│   │   ├── style.css
│   │   ├── map.css
│   │   ├── mypage.css
│   │   ├── reviews.css
│   │   └── searchscan.css
│   ├── js/                 # JavaScript 파일
│   │   ├── index.js        # 메인 페이지 스크립트
│   │   ├── map.js          # 지도 페이지 스크립트
│   │   ├── searchscan.js  # 검색/스캔 스크립트
│   │   ├── mypage.js       # 마이페이지 스크립트
│   │   └── reviews.js      # 리뷰 페이지 스크립트
│   └── logo.svg            # 로고
│
├── map-module/             # React 마이크로 프론트엔드 (지도 컴포넌트)
│   ├── src/
│   │   ├── main.jsx        # 진입점
│   │   └── MapComponent.jsx # 지도 React 컴포넌트
│   ├── package.json
│   ├── vite.config.js      # Vite 빌드 설정
│   └── README.md           # 빌드 가이드
│
├── .venv/                  # Python 가상 환경 (gitignore)
├── .env                    # 환경 변수 (gitignore)
├── requirements.txt        # Python 패키지 목록
└── README.md               # 프로젝트 문서
```

##  데이터 초기화

데이터베이스를 초기화하려면 `backend/reset/` 디렉토리의 스크립트를 사용하세요:

### Windows
```powershell
cd backend
.\reset\초기화.ps1
```

### 모든 플랫폼
```bash
cd backend
python reset/reset_data.py
```

##  API 엔드포인트

### 인증
- `GET /login` - 로그인 페이지
- `POST /login` - 로그인 처리
- `GET /register` - 회원가입 페이지
- `POST /register` - 회원가입 처리
- `GET /logout` - 로그아웃
- `GET /mypage` - 마이페이지
- `POST /change-password` - 비밀번호 변경

### 매물 분석
- `GET /api/analyze?region=지역명` - 매물 분석 (전세가율 포함)
- `GET /heatmap` - 지도 위치와 검증 상태 조회. 검증된 지역 집계가 없는 위치는 `score: null`, `status: unavailable`로 반환합니다.
- `POST /api/heatmap/refresh`, `POST /api/heatmap/update` - 관리자 확인 후 갱신 보류 응답을 반환합니다. 검증된 지역 집계가 준비되기 전에는 저장하지 않습니다.
- `GET /api/properties?region=지역명` - 지역별 매물 조회
- `GET /api/real-transactions?region=지역명&deal_ymd=YYYYMM` - 실거래 데이터 조회

### 사용자 기능
- `GET /api/search-history` - 검색 히스토리 조회
- `POST /api/search-history` - 검색 히스토리 저장
- `DELETE /api/search-history/<id>` - 검색 히스토리 삭제
- `GET /api/favorites` - 즐겨찾기 목록 조회
- `POST /api/favorites` - 즐겨찾기 추가
- `DELETE /api/favorites/<id>` - 즐겨찾기 삭제
- `GET /api/reviews` - 리뷰 목록 조회
- `POST /api/reviews` - 리뷰 작성
- `PUT /api/reviews/<id>` - 리뷰 수정
- `DELETE /api/reviews/<id>` - 리뷰 삭제
- `POST /api/reports` - 신고 제출
- `GET /api/notifications` - 알림 목록 조회
- `PUT /api/notifications` - 알림 읽음 처리
- `POST /api/notifications/read-all` - 모든 알림 읽음 처리
- `GET /api/stats` - 기존 사이드바의 검색·신고·저장 지도 건수
- `GET /api/dashboard/summary` - 전세 대시보드 요약과 일관된 차트 데이터
- `GET /api/dashboard/regions` - 서울 자치구별 전세 거래량
- `GET /api/dashboard/trends` - 최근 12개월 월별 전세 거래량
- `GET /api/dashboard/data-status` - 수집 범위·누락·실패·지연 상태

##  아키텍처

### 서버 사이드 렌더링 (SSR)
- Flask가 HTML 템플릿을 렌더링하여 클라이언트에 전달
- Jinja2 템플릿 엔진 사용
- 세션 기반 인증

### 마이크로 프론트엔드
- 지도 컴포넌트만 React로 빌드 (`map-module/`)
- 빌드된 JS 파일을 Flask 템플릿에서 `<script>` 태그로 로드
- 기존 Flask 템플릿과 완전히 통합

### API 설계
- 페이지 렌더링: Flask 템플릿 사용
- 데이터 조회/수정: JSON API 엔드포인트 사용
- 인증: Flask-Login 세션 기반

##  문제 해결

### 지도가 표시되지 않는 경우
1. Kakao Maps API 키 확인
   - `frontend/map.html`의 API 키 확인
   - Kakao Developers 콘솔에서 도메인 등록 확인 (`localhost:5000`, `127.0.0.1:5000`)
2. 브라우저 콘솔 확인
   - Network 탭에서 스크립트 로드 상태 확인
   - Console 탭에서 에러 메시지 확인

### 데이터베이스 오류
운영 DB를 삭제하거나 reset 스크립트를 실행하지 마세요. 백업·마이그레이션·복구는
[Ubuntu 운영 안내](docs/dashboard-deployment.md)를 참고하세요.

### 의존성 오류
```bash
# 가상 환경 재생성
rm -rf .venv
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```



## 서울 아파트 전세 대시보드

Flask·SQLAlchemy·Jinja2·Vanilla JS 구조를 유지합니다. 메인에는 검증되지 않은
정확도, 분석 시간, 차단 건수, 위험 요소 백분율, 신고 기반 더미 차트를 표시하지 않습니다.
전세가율과 기존 매물 위험도 알고리즘의 고도화는 2차 개발 범위입니다.

### 기존 코드 재사용과 변경

- `backend/utils.py`: 서울 25개 구 코드, 환경 변수/기존 설정 파일의 API 키 조회를 재사용합니다.
- `backend/models.py`: 회원·검색·리뷰와 기존 `RealTransaction` 모델을 유지합니다.
- `/api/real-transactions`: 기존 매매 검색용 부분 캐시를 유지합니다. 전세 통계의 근거로 사용하지 않습니다.
- `/analyze`: 기존 동작을 유지하고 README와 일치하도록 `/api/analyze` 별칭을 추가했습니다.
- `frontend/index.html`, `static/js/index.js`: 서비스 CTA, 실제 집계 카드, 자치구·월별 막대 차트, 출처/계산 기준을 표시합니다. 외부 차트 라이브러리 없이 숫자와 막대를 함께 제공해 모바일·접근성을 지원합니다.
- `backend/dashboard_models.py`: `regions`, `real_transactions`, `dashboard_stats`, `collection_logs` 모델을 정의합니다. 단수 `real_transaction`은 기존 매매 캐시, 복수 `real_transactions`는 신규 전세 테이블입니다.
- `backend/rental_collector.py`: 전월세 API의 전체 페이지 수집·정규화·검증·재시도·지역월 단위 원자적 교체를 담당합니다.
- `backend/dashboard.py`: 집계, API 4개, 수집 CLI를 제공합니다.
- `backend/dashboard_ops.py`: 배타적 수집 잠금, SQLite/PostgreSQL 백업, 저장소 점검을 제공합니다.
- `migrations/`: 기존 DB를 보존하는 baseline 및 전세 테이블 추가 migration입니다.
- `deploy/`: Ubuntu systemd 수집 서비스와 일일 타이머 예시입니다.

이전 작업의 `public_data_snapshot` 매매 집계는 새 전세 통계에 사용하지 않습니다.
기존 테이블이 있더라도 자동 삭제하지 않습니다. `/api/dashboard/stats`는 새 summary의 별칭입니다.

### 집계 범위·정확성

[공공데이터포털의 국토교통부 아파트 전월세 실거래가 자료](https://www.data.go.kr/data/15126474/openapi.do)를 사용합니다.
서울 25개 자치구 × 현재 월 포함 12개월 = **300개 지역·월**이 목표 범위입니다.
예를 들어 2026-11-05에는 2025-12-01부터 2026-11-05까지를 대상으로 하며, 11월은 진행 중입니다.
최근 365일 또는 완료된 12개월과는 다른 달력월 기준입니다.

- 전세: 보증금 양수, 월세 0원, 유효 계약일·면적·지역인 아파트 공개 레코드입니다. 금액 단위는 만원, 면적은 ㎡입니다. 월세 필드가 없으면 전세로 추정하지 않고 수집을 실패 처리합니다.
- 지역 수: 위 범위에 유효 거래가 1건 이상인 자치구의 고유 개수입니다. 전체 12개월 수집 완료 지역 수는 별도 `fully_collected_regions`입니다.
- 거래 수: 취소되지 않은 `real_transactions`의 실제 행 수입니다. SQL에서 지역·월별 집계하고 요약·지역·월별 합계를 같은 결과에서 생성합니다. 저장된 집계와 불일치하면 503으로 응답합니다.
- 중복: 정규화한 모든 공개 필드(취소 메타데이터 제외)의 SHA-256에 지역·월을 묶어 UNIQUE 제약을 둡니다. 공개 식별번호가 없는 동일한 별개 계약은 구별할 수 없으며, 이는 공식 전체 계약 건수와 같다는 보장이 아닙니다.
- 취소·정정: 취소 필드가 제공되면 제외합니다. 전월세 API에 취소 필드가 없거나 원본이 수정·삭제되는 경우 지역·월 전체 재수집 후 교체하여 반영합니다. 기존 일부 캐시로 추측하지 않습니다.
- 정합성: 응답 코드, 전체 건수, 페이지 번호·누락·반복, 날짜·지역·가격·면적을 검증합니다. 오류가 있는 범위는 기존 거래·집계·정상 갱신일을 그대로 유지하고 실패 로그를 남깁니다.
- 원자성: 한 지역·월의 거래 교체, 집계 갱신, 성공 로그를 같은 DB 트랜잭션으로 커밋합니다. 다른 지역의 수집 성공은 보존합니다.
- 최신 갱신일: 범위 내 마지막 정상 수집 시각입니다. 원천기관 발표일이나 전체 300개 범위의 동시 갱신 시각이 아닙니다. 가장 오래된 갱신일도 함께 제공합니다. DB 시각은 UTC, API·화면은 KST입니다.

공공 API의 페이지 간 원본이 같은 전체 건수를 유지하면서 수정되는 경우까지 일관성을
보장할 수는 없습니다. 페이지 번호·전체 건수 변경/반복은 감지하지만 원천자료의 신고
지연, 누락, 식별 한계는 남습니다. 차트는 전세사기 확률이나 안전도 지표가 아닙니다.

### 수집 상태

| 상태 | 기준 | 화면 |
|---|---|---|
| `unavailable` | 정상 수집된 지역·월이 없음 | 숫자는 `—`, 수집 전 안내 |
| `partial` | 300개 중 미수집 범위 또는 최신 실패/진행 로그가 있음 | 수집분 합계와 완료 범위 표시 |
| `stale` | 전체 범위를 수집했지만 일부가 신선도 기준을 초과함 | 이전 수치와 갱신 지연 안내 |
| `complete` | 300개 범위 모두 정상·신선하고 더 최근 실패가 없음 | 전체 수집 완료 표시 |

기본 신선도 기준은 192시간(8일)으로 주간 전체 갱신과 맞춥니다. 부분 수집이면서
지연된 경우 상태는 `partial`이고 `coverage.stale`과 화면 안내로 지연을 함께 표시합니다.
정상 수집 0건은 `0`, 수집 실패/미수집은 `null` 또는 오류로 구별합니다. DB 오류는
HTTP 503 + `unavailable`이며 가짜 0으로 바꾸지 않습니다.

모든 API는 `source`, `period`, `last_updated`, `oldest_updated`, `computed_at`, `coverage`를
반환합니다. `coverage`에는 목표 300개, 완료 개수, 미수집/지연/실패 지역·월 목록이 포함됩니다.
`summary` 응답에는 같은 시점의 `summary`, `regions`, `trends`가 모두 들어 있어 프론트엔드가
수집 도중 서로 다른 응답의 합계를 섞지 않습니다. 숫자 API는 외부 공공 API를 호출하지 않습니다.

### 실행

실제 키는 `.env.example`을 참고하여 환경 변수로 설정합니다. `MOLIT_RENT_API_KEY`가
없으면 실제 수집할 수 없습니다. 키가 없는 상태에서 가짜 자료를 채우지 않습니다.
기존 `MOLIT_API_KEY`를 사용하려면 전월세 API의 활용 승인이 있어야 합니다.

```bash
python -m flask --app backend/app db upgrade
python -m flask --app backend/app sync-dashboard --mode full
python -m flask --app backend/app sync-dashboard --mode recent
python -m flask --app backend/app run
```

`recent`는 최근 3개월과 미수집·최신 실패 범위를 갱신합니다. `scheduled`는 월~토 recent,
일요일 full입니다. 특정 범위 재시도는 `--region 11110 --month 202610`처럼 지정합니다.
요청 타임아웃은 연결 5초/응답 20초이고 네트워크·429·5xx는 최대 3회 재시도합니다.
키 오류·잘못된 데이터는 재시도로 정상 자료처럼 처리하지 않습니다.

Ubuntu 서비스 설치, 환경 변수, 기존 DB 이전·백업·복구·스케줄러는
[배포 운영 안내](docs/dashboard-deployment.md)에 정리했습니다.

### 테스트

```bash
python -m unittest discover -s tests -v
node --test tests/test_dashboard_frontend.cjs
```

테스트용 모의 데이터는 격리된 메모리/임시 DB에서만 사용합니다. 중복·취소·정정,
페이지 오류, 기존 데이터 보존, 상태별 응답, 지역/월/전체 합계, 기존 회원 DB 마이그레이션,
백업 무결성, 주요 페이지와 기존 검색·분석 API, 프론트엔드의 빈 데이터/오류/지연 상태를 검증합니다.
운영 환경은 Ubuntu + Gunicorn/Nginx + PostgreSQL입니다. 실제 수집·배포 기록 및 운영 경로는 [배포 운영 안내](docs/dashboard-deployment.md)를 확인하세요.


실제 운영 배포 및 수집 완료 기록: [2026-11-08 배포 검증](docs/deployment-status-2026-11-08.md).
