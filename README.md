# SafeHome · 세이프홈

공공데이터 기반 전세 계약 확인 도구입니다. 국토교통부 아파트 매매·전월세 실거래를 조회하고, 유사한 순수 전세 거래로 계산한 참고 전세가율과 계약 전 확인사항을 제공합니다.

[운영 사이트](https://safehome-kr.com/) · [지역별 지도](https://safehome-kr.com/map) · [아파트 실거래 분석](https://safehome-kr.com/searchscan) · [운영·배포 안내](docs/dashboard-deployment.md)

## 주요 기능

| 화면 | 제공하는 정보 |
| --- | --- |
| 메인 대시보드 `/` | 서울 25개 자치구의 아파트 순수 전세 거래량, 자치구별·월별 차트, 수집 범위와 갱신 상태 |
| 지역별 지도 `/map` | 52개 위치의 법정동별 참고 전세가율, 매매 건수, 비교 가능한 매매 표본 수, 계약 기간과 마지막 정상 갱신일 |
| 실거래 분석 `/searchscan` | 최근 6개 계약월의 아파트 매매 내역, 계약일, 비교 전세 보증금 중앙값, 참고 전세가율, 확인사항과 체크리스트 |
| 실거래 비교 | 같은 단지의 서로 다른 거래 비교, 계약일·매매가를 포함한 비교표와 CSV 내려받기 |
| 자가진단·사기 유형 | 계약 전 점검 항목, 대표적인 사기 유형과 예방 정보 |
| 회원 기능 | 일반·소셜 로그인, 지역 즐겨찾기, 검색 기록, 리뷰, 신고, 알림, 마이페이지 |

지도 원은 고정 크기로 지역의 위치를 나타냅니다. 원을 누르면 집계 근거가 열리고, **개별 매물 조회**를 누르면 해당 자치구·법정동의 실거래 분석 화면으로 이동합니다. 지도 검색 결과는 오른쪽 패널에도 표시합니다.

조회 결과는 신고된 과거 아파트 거래입니다. 전세가율은 거래 가격을 비교한 참고 지표이며, 계약 안전을 판단하려면 등기부등본·선순위 권리·보증 가입 요건 등을 별도로 확인해야 합니다.

## 데이터 출처와 조회 범위

- [국토교통부 아파트 매매 실거래가 상세 자료](https://www.data.go.kr/data/15126468/openapi.do)
- [국토교통부 아파트 전월세 실거래가 자료](https://www.data.go.kr/data/15126474/openapi.do)
- [Kakao Maps API](https://apis.map.kakao.com/web/)를 이용한 지도 표시와 주소 검색

금액 계산의 기본 단위는 **만 원**, 면적은 **㎡**입니다. 한국시간을 기준으로 계약월 범위를 선택하고, DB 수집 시각은 UTC로 저장한 뒤 화면과 API에서 한국시간으로 표시합니다.

| 기능 | 계약 기간 | 조회 방식 |
| --- | --- | --- |
| 전세 대시보드 | 현재 월을 포함한 최근 12개월 | 예약 수집한 DB의 거래·집계·수집 로그 조회 |
| 지도 참고 전세가율 | 직전 완료 월까지 최근 3개월 | 별도 수집 작업이 저장한 법정동별 집계 조회 |
| 개별 실거래 분석 | 현재 월을 포함한 최근 6개월 | 국토부 매매·전월세 API 조회 및 완전히 수신한 지역·월 자료의 5분 캐시 |
| 월별 실거래 목록 | 화면에서 선택한 최근 1~3개월 | 월별 매매 자료를 조회하고 페이지별 표시 |

예를 들어 2026년 11월에는 대시보드가 2025년 12월부터, 개별 분석이 2026년 6월부터 조회합니다. 지도는 2026년 8~10월 계약을 집계합니다. 진행 중인 월은 신고가 추가될 수 있습니다.

### 대시보드 집계

- 서울 25개 자치구 × 12개월의 **300개 자치구·월 조합**을 수집합니다. 화면의 `300/300`은 수집 범위를 뜻합니다.
- 보증금이 양수이고 월세가 0원인 아파트 공개 레코드를 집계합니다. 계약일·지역·가격·면적을 검증하며, 제공된 취소 정보를 반영합니다.
- 공개 필드를 정규화한 지문과 지역·월의 고유 제약으로 중복을 방지합니다. 동일한 공개 필드를 가진 별개 계약은 하나로 합쳐질 수 있습니다.
- 모든 페이지의 응답 코드, 페이지 번호, 전체 건수, 누락·반복을 확인한 뒤 지역·월 단위로 거래·집계·성공 로그를 같은 트랜잭션에서 갱신합니다.
- 실패한 범위의 이전 정상 데이터는 보존하고 실패 로그를 남깁니다. 재수집은 원천자료의 정정·삭제를 반영합니다.
- 요약과 지역별·월별 차트는 같은 집계 결과로 제공합니다. 저장된 건수와 실제 거래 행 수가 어긋나면 503으로 응답합니다.

| 상태 | 기준 |
| --- | --- |
| `unavailable` | 정상 수집된 범위가 없음 |
| `partial` | 미수집 범위 또는 마지막 정상 수집 이후의 실패·진행 로그가 있음 |
| `stale` | 전체 범위를 수집했지만 일부가 갱신 기한을 초과함 |
| `complete` | 목표 범위가 수집됐고 최신 상태 조건을 충족함 |

기본 갱신 지연 기준은 현재 월을 포함한 최근 3개월이 **36시간**, 이전 9개월이 **192시간**입니다. 정상 수집된 0건은 `0`, 미수집은 `null`로 구분합니다. `coverage`에서 누락·실패·지연 범위를 확인할 수 있습니다.

### 참고 전세가율 계산

개별 매매에 대해 다음 조건을 만족하는 전세 거래를 선택합니다.

1. 같은 자치구·법정동·단지의 순수 전세 거래
2. 전용면적 차이 ±1㎡ 이내, 계약일 차이 ±30일 이내
3. 양쪽에 지번이나 건축연도가 있으면 일치 여부 확인. 지번 쌍이 없으면 같은 건축연도 필요
4. 양수 보증금, 공개 필드 기준 중복 제거, 매매가의 1% 이상인 보증금

비교 전세가 **3건 이상**이면 보증금 중앙값을 계산합니다.

```text
개별 참고 전세가율(%) = 비교 전세 보증금 중앙값 ÷ 매매 실거래가 × 100
지도 참고 전세가율(%) = 같은 법정동에서 계산 가능한 개별 전세가율들의 중앙값
```

지도 수치 공개에는 계산 가능한 **매매 표본 5건 이상**이 필요합니다. 팝업의 **기간 내 매매**는 집계 대상으로 검증·중복 제거한 매매 수이고, **비교 가능한 매매**는 전세 표본 조건까지 충족해 비율을 계산한 매매 수입니다.

| 참고 전세가율 | 지도 구간 |
| --- | --- |
| 60% 미만 | 낮음 |
| 60% 이상 80% 미만 | 중간 |
| 80% 이상 | 높음 |
| 집계 없음·표본 부족·기간 불일치·36시간 초과 | 회색, 판단 불가 |

개별 분석은 전세 표본 부족 또는 전세 자료 조회 실패 시 참고 전세가율을 `null`, 구간을 `unknown`으로 반환합니다. 지도 `score` 필드에는 참고 전세가율이 담깁니다. 매매·전월세는 신고 지연과 정정이 있으며, 공개 필드만으로 같은 세대의 거래 여부를 확정하기 어렵습니다.

지도 52곳의 조회 대상은 **자치구 코드 + 법정동**으로 관리합니다. 행정동과 법정동이 다른 지점은 팝업에 집계 법정동을 표시합니다. 서원동과 관악구 삼성동은 법정동 신림동의 같은 집계를 사용합니다. 신사동을 실거래 검색창에 직접 입력할 때는 강남구·은평구를 함께 입력합니다.

## 기술 구성

| 구분 | 사용 기술 |
| --- | --- |
| 화면 | HTML, CSS, Vanilla JavaScript, Jinja2 |
| 지도 | Kakao Maps JavaScript SDK |
| 서버 | Flask, SQLAlchemy, Flask-Migrate, Requests |
| 인증 | Flask-Login, Flask-Bcrypt, 네이버·카카오 OAuth |
| 로컬 개발 | Python 3.13, SQLite, `requirements.txt` |
| 운영·CI | Python 3.14, PostgreSQL 18, `requirements-production.txt` |
| 배포 | Ubuntu EC2, Gunicorn, Nginx, systemd 서비스·타이머 |
| 운영 지원 | 비공개 S3 원격 백업, SNS 이메일 알림, 격리 PostgreSQL 복원 훈련 |
| 검증 | Python unittest, Node.js 테스트, Playwright, GitHub Actions |

현재 지도 진입점은 `static/js/map.js`입니다. `map-module/`과 `static/js/map-react.js`는 이전 React/Vite 지도 구현을 보관합니다.

## 로컬 실행

저장소 루트에서 실행합니다.

```bash
git clone https://github.com/Baegopayolo/safehome.git
cd safehome
python -m venv .venv
```

Windows PowerShell에서 가상환경을 활성화합니다.

```powershell
.\.venv\Scripts\Activate.ps1
```

macOS/Linux에서는 다음 명령을 사용합니다.

```bash
source .venv/bin/activate
```

```bash
python -m pip install -r requirements.txt
python -c "import secrets; print(secrets.token_hex(32))"
```

생성한 키를 저장소 루트의 `.env`에 설정합니다. 아래는 로컬 SQLite 설정 형태입니다. 실제 API 키와 비밀 키는 환경별로 주입하며 Git에 커밋하지 않습니다.

```dotenv
SECRET_KEY=<생성한 비공개 키>
DATABASE_URL=sqlite:///site.db
MOLIT_API_KEY=<아파트 매매 상세 API 승인 키>
MOLIT_RENT_API_KEY=<아파트 전월세 API 승인 키>
KAKAO_APP_KEY=<카카오 지도 JavaScript 키>
```

`SECRET_KEY`는 필수입니다. Flask CLI는 `.env`를 읽습니다. 로그인 세션을 유지하려면 재시작·릴리스 전환 시 같은 비공개 키를 사용합니다. 소셜 로그인 설정 이름은 [.env.example](.env.example)에 있습니다.

```bash
python -m flask --app backend/app db upgrade
python -m flask --app backend/app run
```

브라우저에서 [로컬 개발 서버](http://127.0.0.1:5000)에 접속합니다. 카카오 지도 키에는 개발 도메인을 등록합니다. 최초 마이그레이션 후 대시보드·지도 데이터를 준비하려면 승인된 국토부 키로 수집 명령을 실행합니다.

```bash
python -m flask --app backend/app sync-dashboard --mode full
python -m flask --app backend/app sync-map-indicators
```

대시보드의 `--mode recent`는 최근 3개월과 미수집·마지막 실패 범위를 갱신합니다. `--mode scheduled`는 월~토에 recent, 일요일에 full로 실행합니다. 범위를 지정해 재시도할 수 있습니다.

```bash
python -m flask --app backend/app sync-dashboard --region 11680 --month 202610
python -m flask --app backend/app sync-map-indicators --region 11680
python -m flask --app backend/app check-data-storage
```

API 활용 승인이 완료된 키가 필요합니다. 수집 전에는 `unavailable` 상태로 표시하고, 수집 오류가 발생하면 이전 정상 데이터와 실패 상태를 제공합니다.

## 주요 API

| 메서드와 경로 | 기능 |
| --- | --- |
| `GET /api/dashboard/summary` | 전세 요약과 같은 시점의 지역·월별 차트 |
| `GET /api/dashboard/stats` | summary 별칭 |
| `GET /api/dashboard/regions` | 자치구별 전세 거래량 |
| `GET /api/dashboard/trends` | 월별 전세 거래량 |
| `GET /api/dashboard/data-status` | 수집 기간·범위·누락·실패·지연 |
| `GET /heatmap` | 지도 위치, 조회 법정동, 참고 전세가율, 표본 수, 사유, 기간, 갱신일 |
| `GET /api/analyze?region=강남구%20역삼동` | 개별 매매와 참고 전세가율. `/analyze`도 같은 응답 |
| `GET /api/advanced-search` | 지역·가격·참고 전세가율 구간으로 검색 |
| `GET /api/real-transactions?region=강남구%20역삼동&deal_ymd=202610&pageNo=1&numOfRows=15` | 월별 실거래 페이지와 전체 건수·다음 페이지 여부 |

지도 갱신은 `sync-map-indicators` CLI와 예약 작업에서 수행합니다. 기존 `POST /api/heatmap/refresh`, `POST /api/heatmap/update`는 비로그인 401, 일반 회원 403, 관리자 409로 응답합니다. 지도 조회는 DB를 변경하지 않습니다.

회원용 API는 `/api/favorites`, `/api/search-history`, `/api/reviews`, `/api/reports`, `/api/notifications`에서 제공합니다. 즐겨찾기는 `DELETE /api/favorites`에 지역을 보내거나 `DELETE /api/favorites/<id>`로 삭제할 수 있습니다. 관리자 신고 관리는 `/api/admin/reports`를 사용합니다.

## 운영과 배포

운영은 커밋별 릴리스 디렉터리를 준비한 뒤 `/home/ubuntu/safehome-current` 링크를 전환하는 구조입니다. Nginx의 정적 파일 경로도 `safehome-current/static/`을 가리킵니다. DB 마이그레이션 전에는 백업을 검증하고, 전환 후 웹과 API를 확인하며, 문제가 생기면 이전 릴리스로 복구합니다.

| 예약 작업 | 한국시간 일정 | 완료 기한 |
| --- | --- | --- |
| PostgreSQL 백업 | 매일 02:30 | 04:30 |
| 전세 대시보드 수집 | 매일 03:10~03:15 | 08:00 |
| 지도 지표 수집 | 매일 05:30~05:35 | 06:45 |
| 격리 PostgreSQL 복원 | 일요일 09:30 | 12:00 |
| 운영 감시 | 15분 간격 및 작업 실패 시 | 실패·지연·복구 상태 변경 감지 |

백업은 로컬과 비공개 S3에 보관하며, 체크섬 검증과 30일 보존 정책을 적용합니다. 복원 훈련은 S3 복사본을 격리 PostgreSQL에 복원해 확인합니다. 감시 결과는 설정된 SNS 주제의 확인된 이메일 구독으로 전달합니다.

운영 환경 변수, 백업·복구, 서비스 설치와 실패 대응은 [배포 운영 안내](docs/dashboard-deployment.md)에 정리했습니다. [2026-11-08 배포 기록](docs/deployment-status-2026-11-08.md)은 당시 환경을 기록한 문서입니다. 최신 수집 상태는 [운영 상태 API](https://safehome-kr.com/api/dashboard/data-status)에서 확인할 수 있습니다.

## 테스트와 CI

```bash
python -B -m unittest discover -s tests -v
node --test tests/test_dashboard_frontend.cjs
```

PostgreSQL 통합 테스트는 Linux의 PostgreSQL 서버·클라이언트 도구를 사용합니다. 아래 환경 변수를 설정하면 임시 클러스터에서 마이그레이션·수집·롤백·백업·복원을 검증합니다.

```bash
SAFEHOME_TEST_POSTGRES_BIN=/usr/lib/postgresql/18/bin python -B -m unittest discover -s tests -v
```

Playwright는 별도 테스트 환경에 설치할 수 있습니다. `SAFEHOME_APP_PYTHON`은 Flask 의존성을 설치한 Python 실행 파일을 지정합니다.

```bash
python -m pip install playwright==1.64.1
python -m playwright install chromium
python -B tests/browser_dashboard.py
```

검증 범위에는 중복·취소·정정 처리, 페이지 누락·반복, 실패 시 기존 데이터 보존, 집계 정합성, 전세가율 60%·80% 경계, 표본 부족, 지도 52곳의 조회 대상, 매물 비교와 CSV, 입력 문자열 렌더링, 모바일 대시보드와 오류 재시도가 포함됩니다. 테스트는 메모리·임시 DB와 모의 API를 사용하며, 브라우저 테스트는 카카오 SDK 대역을 사용합니다.

[GitHub Actions](.github/workflows/safehome-ci.yml)는 `main` 푸시와 `main` 대상 PR에서 백엔드·PostgreSQL 통합·프런트엔드·Chromium 검증을 실행합니다. 운영 전환은 [배포 절차](docs/dashboard-deployment.md)에 따라 수행합니다.

## 프로젝트 구조

```text
safehome/
├── backend/
│   ├── app.py                 # Flask 앱과 모듈 등록
│   ├── models.py              # 회원·즐겨찾기·리뷰 등 기존 모델
│   ├── dashboard_models.py    # 전세 원본·집계·수집 로그
│   ├── rental_collector.py    # 지역·월별 전세 수집
│   ├── dashboard.py           # 전세 집계 API와 수집 CLI
│   ├── map_indicators.py      # 법정동 지도 집계·map_snapshots
│   ├── dashboard_ops.py       # 수집 잠금·백업·저장소 점검
│   ├── utils.py               # 실거래 조회·지역 매핑·전세 비교
│   └── routes/                # 페이지·인증·사용자 API·OAuth
├── frontend/                  # Jinja2 화면과 공통 템플릿
├── static/                    # CSS·Vanilla JS·이미지
├── migrations/                # 명시적 DB 스키마 마이그레이션
├── deploy/                    # 릴리스 준비·감시·백업·systemd 설정
├── tests/                     # 백엔드·프런트엔드·브라우저 검증
├── docs/                      # 운영 절차와 배포 기록
├── map-module/                # 이전 React/Vite 지도 소스
├── .github/workflows/         # GitHub Actions
├── .env.example               # 환경 변수 이름 안내
├── requirements.txt           # 로컬 개발 의존성
└── requirements-production.txt # 운영·CI 의존성
```

`real_transaction`은 기존 매매 캐시 테이블이고, `real_transactions`는 대시보드용 전세 원본 테이블입니다. `map_snapshots`에 지도용 법정동 집계를 저장합니다. 회원·리뷰와 기존 테이블의 데이터 보존은 명시적 마이그레이션과 백업·복구 절차로 관리합니다.
