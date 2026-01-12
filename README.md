# 🏠 세이프홈 (SafeHome)

전세사기 예방을 위한 종합 플랫폼입니다. 등기부등본 분석부터 지역별 위험도 확인까지, AI가 5초 만에 매물의 안전성을 분석해드립니다.

## ✨ 주요 기능

### 🔍 매물 분석 스캔
- 등기부등본 정보를 기반으로 매물의 위험도를 자동 분석
- 전세가율, 담보 상태, 근저당 등 핵심 지표 확인
- 0-100점 사이의 종합 위험도 점수 제공

### 🗺️ 안전 히트맵
- 지역별 전세 안전도를 시각적으로 확인
- 위험 지역을 미리 파악하여 안전한 계약 지원
- 실시간 데이터 기반 통계 제공

### 📋 자가진단 체크리스트
- 계약 전 필수 점검 항목을 체크하며 안전도 진단
- 단계별 가이드를 통한 체계적인 검토

### 📚 사기 유형 학습
- 깡통전세, 신탁사기 등 대표적인 전세사기 유형 학습
- 각 사기 유형별 예방법 및 대응 방법 제공

### 👤 사용자 기능
- 회원가입 및 로그인
- 검색 히스토리 관리
- 즐겨찾기 지역 저장
- 리뷰 작성 및 신고 기능
- 알림 시스템

## 🛠️ 기술 스택

### Backend
- **Python 3.13**
- **Flask** - 웹 프레임워크
- **Flask-SQLAlchemy** - ORM
- **Flask-Migrate** - 데이터베이스 마이그레이션
- **Flask-Bcrypt** - 비밀번호 암호화
- **Flask-Login** - 사용자 인증
- **Flask-CORS** - CORS 처리
- **SQLite** - 데이터베이스

### Frontend
- **HTML5** / **CSS3** / **JavaScript**
- **Kakao Maps API** - 지도 서비스

## 📦 설치 방법

### 1. 저장소 클론
```bash
git clone https://github.com/your-username/safehome.git
cd safehome
```

### 2. 가상 환경 생성 및 활성화
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. 의존성 설치
```bash
pip install -r requirements.txt
```

### 4. 환경 변수 설정
`.env` 파일을 생성하고 다음 내용을 추가하세요:

```env
KAKAO_APP_KEY=your_kakao_app_key_here
SECRET_KEY=your_secret_key_here
```

> **참고**: Kakao Maps API 키는 [Kakao Developers](https://developers.kakao.com/)에서 발급받을 수 있습니다.

### 5. 데이터베이스 초기화
```bash
cd backend
python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

### 6. 샘플 데이터 생성 (선택사항)
```bash
python seed_data.py
```

## 🚀 실행 방법

### 개발 서버 실행
```bash
cd backend
python app.py
```

서버가 실행되면 브라우저에서 `http://localhost:5000`으로 접속할 수 있습니다.

### 테스트 계정 (seed_data.py 실행 시)
- **사용자명**: `test`
- **비밀번호**: `test123`

## 📁 프로젝트 구조

```
safehome/
├── backend/                 # 백엔드 애플리케이션
│   ├── app.py              # Flask 앱 메인 파일
│   ├── models.py           # 데이터베이스 모델
│   ├── utils.py            # 유틸리티 함수
│   ├── time_utils.py       # 시간 관련 유틸리티
│   ├── seed_data.py        # 샘플 데이터 생성
│   ├── reset_password.py   # 비밀번호 재설정
│   ├── routes/             # 라우트 핸들러
│   │   ├── pages.py        # 페이지 라우트
│   │   ├── auth.py         # 인증 라우트
│   │   └── api.py          # API 라우트
│   ├── reset/              # 데이터 초기화 스크립트
│   └── instance/           # 데이터베이스 파일
│       └── site.db
├── frontend/               # 프론트엔드 템플릿
│   ├── index.html          # 메인 페이지
│   ├── map.html            # 지도 페이지
│   ├── searchscan.html     # 검색/스캔 페이지
│   ├── self-check.html     # 자가진단 페이지
│   ├── scam-types.html     # 사기 유형 페이지
│   ├── Login/              # 로그인 관련 페이지
│   └── _*.html             # 공통 컴포넌트
├── static/                 # 정적 파일
│   ├── css/                # 스타일시트
│   ├── js/                 # JavaScript 파일
│   └── logo.svg            # 로고
├── venv/                   # 가상 환경 (gitignore)
├── .env                    # 환경 변수 (gitignore)
└── requirements.txt        # Python 패키지 목록
```

## 🔧 주요 기능 설명

### 매물 분석
1. 검색/스캔 페이지에서 지역과 매물 정보 입력
2. 등기부등본 정보를 기반으로 자동 분석
3. 위험도 점수 및 상세 분석 결과 확인

### 히트맵
1. 지도 페이지에서 지역별 위험도 확인
2. 색상으로 구분된 위험도 시각화
3. 클릭하여 상세 정보 확인

### 자가진단
1. 자가진단 페이지에서 체크리스트 진행
2. 각 항목별 안전도 점검
3. 종합 결과 및 권장사항 확인

## 🔄 데이터 초기화

데이터베이스를 초기화하려면 `backend/reset/` 디렉토리의 스크립트를 사용하거나 다음 명령어를 실행하세요:

```bash
cd backend
python reset/reset_data.py
```

또는 PowerShell에서:
```powershell
cd backend
.\reset\초기화.ps1
```

## 📝 API 엔드포인트

### 인증
- `POST /register` - 회원가입
- `POST /login` - 로그인
- `GET /logout` - 로그아웃

### 매물 분석
- `POST /api/analyze` - 매물 분석
- `GET /api/heatmap` - 히트맵 데이터 조회
- `GET /api/properties` - 지역별 매물 조회

### 사용자 기능
- `GET /api/history` - 검색 히스토리 조회
- `POST /api/favorite` - 즐겨찾기 추가
- `GET /api/favorites` - 즐겨찾기 목록 조회
- `POST /api/review` - 리뷰 작성
- `POST /api/report` - 신고 제출

자세한 API 문서는 각 엔드포인트의 소스 코드를 참조하세요.

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다.

## ⚠️ 주의사항

- 이 서비스는 참고용이며, 실제 계약 시에는 전문가의 조언을 구하시기 바랍니다.
- 데이터는 실시간으로 업데이트되지만, 정확성을 보장하지 않습니다.
- 중요한 결정을 내리기 전에 반드시 추가 검증을 수행하세요.

## 📞 문의

프로젝트에 대한 문의사항이나 버그 리포트는 GitHub Issues를 통해 제출해주세요.

---

**세이프홈과 함께 안전한 전세 계약을 시작하세요! 🏠✨**
