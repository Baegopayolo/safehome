# 삭제 가능한 파일 목록

## ✅ 안전하게 삭제 가능한 파일들

### 테스트/개발용 스크립트
1. **`backend/quick_test.py`** - 로그인 테스트 스크립트 (프로덕션 코드에서 사용 안 함)
2. **`backend/test_login.py`** - 로그인 기능 테스트 스크립트 (프로덕션 코드에서 사용 안 함)
3. **`backend/scanner.py`** - mock_data.json을 읽는 테스트 스크립트 (프로덕션 코드에서 사용 안 함)
4. **`backend/mock_data.json`** - 테스트용 모의 데이터 (scanner.py에서만 사용)

### 중복/대체 가능한 파일
5. **`backend/create_sample_data.py`** - 샘플 데이터 생성 (seed_data.py와 중복 기능)
6. **`frontend/instance/site.db`** - 중복 DB 파일 (backend/instance/site.db가 실제 사용됨)

### 문서 파일
7. **`backend/STRUCTURE_COMPARISON.md`** - 구조 비교 문서 (참고용 문서)

### 선택적 삭제 (유틸리티 스크립트)
8. **`backend/reset_password.py`** - 비밀번호 재설정 스크립트 (관리용, 필요시 유지 가능)

## ⚠️ 유지해야 할 파일들

- **`backend/seed_data.py`** - 초기화 스크립트에서 사용됨 (reset 폴더의 스크립트들이 참조)
- **`backend/reset/`** 폴더 전체 - 데이터베이스 초기화 스크립트들

## 삭제 명령어

```bash
# 테스트 파일들 삭제
rm backend/quick_test.py
rm backend/test_login.py
rm backend/scanner.py
rm backend/mock_data.json
rm backend/create_sample_data.py
rm backend/STRUCTURE_COMPARISON.md

# 중복 DB 파일 삭제
rm frontend/instance/site.db

# 선택적: 비밀번호 리셋 스크립트 (필요시 유지)
# rm backend/reset_password.py
```

