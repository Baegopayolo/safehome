# Map Module (React 마이크로 프론트엔드)

지도 컴포넌트만 React로 빌드하여 Flask 템플릿에 통합하는 마이크로 프론트엔드 모듈입니다.

## 설치 및 빌드

```bash
# 의존성 설치
npm install

# 빌드 (결과물이 static/js/map-react.js로 생성됨)
npm run build
```

## 사용법

빌드 후 `frontend/map.html`에서 다음과 같이 사용:

```html
<script src="{{ url_for('static', filename='js/map-react.js') }}"></script>
<script>
  // 지도 컨테이너가 준비되면 자동으로 초기화됩니다
  // 또는 수동으로 초기화하려면:
  // window.initMapModule('map');
</script>
```

## 구조

- `src/main.jsx`: 진입점, 전역 함수 제공
- `src/MapComponent.jsx`: 지도 React 컴포넌트
- `vite.config.js`: 단일 JS 파일로 빌드 설정
