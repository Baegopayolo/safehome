import React from 'react';
import ReactDOM from 'react-dom/client';
import MapComponent from './MapComponent';

// 전역으로 마운트할 함수
window.initMapModule = function(containerId = 'map') {
  const container = document.getElementById(containerId);
  if (!container) {
    console.error(`지도 컨테이너를 찾을 수 없습니다: #${containerId}`);
    return;
  }

  const root = ReactDOM.createRoot(container);
  root.render(<MapComponent />);
};

// DOMContentLoaded 시 자동 초기화
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('map')) {
      window.initMapModule('map');
    }
  });
} else {
  if (document.getElementById('map')) {
    window.initMapModule('map');
  }
}
