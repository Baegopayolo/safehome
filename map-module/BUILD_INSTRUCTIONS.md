# 빌드 실행 방법

## 1단계: 의존성 설치

```bash
cd map-module
npm install
```

## 2단계: 빌드 실행

```bash
npm run build
```

빌드가 완료되면 `static/js/map-react.js` 파일이 생성됩니다.

## 3단계: Flask 서버 재시작

빌드 후 Flask 서버를 재시작하고 `/map` 페이지를 확인하세요.

## 문제 해결

### 빌드 오류가 발생하는 경우

1. Node.js가 설치되어 있는지 확인:
   ```bash
   node --version
   npm --version
   ```

2. `node_modules` 폴더 삭제 후 재설치:
   ```bash
   rm -rf node_modules
   npm install
   ```

3. Vite 버전 확인:
   ```bash
   npm list vite
   ```

### 지도가 표시되지 않는 경우

1. 브라우저 콘솔에서 에러 확인
2. `map-react.js` 파일이 `static/js/` 폴더에 있는지 확인
3. 카카오맵 SDK가 먼저 로드되었는지 확인 (map.html의 script 순서)
