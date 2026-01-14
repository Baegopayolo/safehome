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
- **Flask-SQLAlchemy** - 데이터베이스
- **Flask-Migrate** - 데이터베이스 마이그레이션
- **Flask-Bcrypt** - 비밀번호 암호화
- **Flask-Login** - 사용자 인증
- **Flask-CORS** - CORS 처리
- **Requests** - 외부 API 호출


### 외부 API
- **Kakao Maps API** - 지도 및 주소 검색
- **국토교통부 실거래 공개시스템** - 실거래 데이터

##  설치 방법

### 1. 저장소 클론
```bash
git clone https://github.com/your-username/safehome.git
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


### 5. 데이터베이스 초기화
```bash
cd backend
python app.py
```

첫 실행 시 데이터베이스가 자동으로 생성됩니다.

### 6. 샘플 데이터 생성 (선택사항)
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
- `GET /heatmap` - 히트맵 데이터 조회
- `POST /api/heatmap/refresh` - 히트맵 데이터 새로고침
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
- `GET /api/stats` - 통계 데이터 조회

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
```bash
# 데이터베이스 재생성
cd backend
rm instance/site.db
python app.py
```

### 의존성 오류
```bash
# 가상 환경 재생성
rm -rf .venv
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```
