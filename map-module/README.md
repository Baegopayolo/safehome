# Map Module (React 마이크로 프론트엔드)

지도 컴포넌트만 React로 빌드하여 Flask 템플릿에 통합하는 마이크로 프론트엔드 모듈입니다.

## 설치 및 빌드

```bash
# 의존성 설치
npm install

# 빌드 (결과물이 static/js/map-react.js로 생성됨)
npm run build
```

이 모듈은 이전 실험용입니다. 운영 지도 `frontend/map.html`은 검증 상태를 처리하는 `static/js/map.js`를 사용합니다.

## 구조

- `src/main.jsx`: 진입점, 전역 함수 제공
- `src/MapComponent.jsx`: 지도 React 컴포넌트
- `vite.config.js`: 단일 JS 파일로 빌드 설정
