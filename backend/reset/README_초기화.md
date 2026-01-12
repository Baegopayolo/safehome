# 세이프홈 데이터 초기화 가이드

## 🔄 데이터 초기화 방법

### 방법 1: 간단한 명령어 (추천)

PowerShell에서 다음 명령어를 한 줄로 실행:

```powershell
cd "c:\Users\hsue1\OneDrive\바탕 화면\safehome\backend" ; Stop-Process -Name python -Force -ErrorAction SilentlyContinue ; Start-Sleep -Seconds 2 ; Remove-Item "instance\site.db" -Force ; python -c "from app import app, db; app.app_context().push(); db.create_all(); print('✓ DB 생성')" ; python seed_data.py
```

### 방법 2: 단계별 실행

1. **서버 종료**
```powershell
Stop-Process -Name python -Force -ErrorAction SilentlyContinue
```

2. **데이터베이스 삭제**
```powershell
cd "c:\Users\hsue1\OneDrive\바탕 화면\safehome\backend"
Remove-Item "instance\site.db" -Force
```

3. **새 데이터베이스 생성**
```powershell
python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

4. **샘플 데이터 생성**
```powershell
python seed_data.py
```

### 방법 3: 배치 파일 사용

`초기화.bat` 파일을 더블 클릭하거나 실행:
```cmd
초기화.bat
```

## 📊 초기화 후 데이터

초기화하면 다음 데이터가 생성됩니다:

- **테스트 계정**: test / test123
- **즐겨찾기**: 5개 (강남구, 마포구, 강서구, 종로구, 금천구)
- **검색 히스토리**: 7개
- **알림**: 5개 (읽음/안 읽음 혼합)
- **신고**: 2개

## 🚀 서버 시작

초기화 후 서버를 시작하려면:

```powershell
python app.py
```

## ⚠️ 주의사항

- 초기화하면 **모든 사용자 데이터가 삭제**됩니다
- 서버가 실행 중이면 먼저 종료해야 합니다
- 백업이 필요한 경우 `instance/site.db` 파일을 복사하세요

## 🔍 문제 해결

### "다른 프로세스가 파일을 사용 중" 오류

서버가 아직 실행 중입니다. 다음 명령어로 강제 종료:

```powershell
Get-Process python | Stop-Process -Force
```

### 데이터베이스 파일을 찾을 수 없음

데이터베이스가 없는 경우 바로 생성:

```powershell
python -c "from app import app, db; app.app_context().push(); db.create_all()"
python seed_data.py
```

## 📝 커스텀 데이터

`seed_data.py` 파일을 수정하여 원하는 샘플 데이터를 추가할 수 있습니다.
