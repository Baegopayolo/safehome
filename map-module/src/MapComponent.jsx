import React, { useEffect, useRef, useState } from 'react';

const MapComponent = () => {
  const mapContainerRef = useRef(null);
  const mapRef = useRef(null);
  const circlesRef = useRef([]);
  const regionDataRef = useRef({});
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    // 카카오맵 SDK 로드 확인
    const checkKakaoSDK = () => {
      if (window.kakao && window.kakao.maps) {
        initMap();
        return true;
      }
      return false;
    };

    // SDK가 이미 로드되어 있으면 바로 초기화
    if (checkKakaoSDK()) {
      return;
    }

    // SDK 로드 대기 (최대 5초)
    let attempts = 0;
    const maxAttempts = 25; // 5초 (200ms * 25)
    const interval = setInterval(() => {
      attempts++;
      if (checkKakaoSDK() || attempts >= maxAttempts) {
        clearInterval(interval);
        if (attempts >= maxAttempts) {
          console.error('카카오맵 SDK 로드 실패');
        }
      }
    }, 200);

    return () => clearInterval(interval);
  }, []);

  const initMap = () => {
    if (!mapContainerRef.current || !window.kakao || !window.kakao.maps) {
      return;
    }

    const mapOption = {
      center: new window.kakao.maps.LatLng(37.566826, 126.9786567), // 서울 시청
      level: 9
    };

    const map = new window.kakao.maps.Map(mapContainerRef.current, mapOption);
    mapRef.current = map;

    // 지도 인스턴스를 전역으로 노출 (기존 map.js 함수들이 사용할 수 있도록)
    window.map = map;

    // 히트맵 데이터 로드
    loadHeatmapData(map);
    setIsLoaded(true);
  };

  const loadHeatmapData = (map) => {
    fetch('/heatmap')
      .then(response => {
        if (!response.ok) {
          throw new Error(`API 호출 실패: ${response.status}`);
        }
        return response.json();
      })
      .then(data => {
        if (!data || !Array.isArray(data) || data.length === 0) {
          console.warn('히트맵 데이터가 없습니다.');
          return;
        }

        const validData = data.filter(region => 
          region && region.region && 
          typeof region.lat === 'number' && 
          typeof region.lng === 'number' &&
          !isNaN(region.lat) && !isNaN(region.lng)
        );

        if (validData.length === 0) {
          console.error('유효한 히트맵 데이터가 없습니다.');
          return;
        }

        // 전역 변수 초기화 (기존 map.js 함수들과 연동)
        // 중요: localStorage에서 복원할 데이터를 먼저 백업
        const storedJeonseRates = (() => {
          try {
            const stored = JSON.parse(localStorage.getItem('regionJeonseRates') || '{}');
            const now = Date.now();
            const maxAge = 7 * 24 * 60 * 60 * 1000; // 7일
            const valid = {};
            Object.keys(stored).forEach(region => {
              if (stored[region].timestamp && (now - stored[region].timestamp) <= maxAge) {
                valid[region] = stored[region];
              }
            });
            return valid;
          } catch (e) {
            return {};
          }
        })();
        
        if (!window.regionData) {
          window.regionData = {};
        }
        if (!window.regions) {
          window.regions = [];
        }
        
        // 기존 배열 초기화 (하지만 localStorage 데이터는 보존)
        window.regions = [];
        window.regionData = {};

        // 지도에 원 그리기
        validData.forEach(region => {
          try {
            let color = '#28a745'; // 안전 (초록)
            if (region.score >= 80) color = '#dc3545'; // 위험 (빨강)
            else if (region.score >= 60) color = '#ffc107'; // 주의 (노랑)

            const circle = new window.kakao.maps.Circle({
              center: new window.kakao.maps.LatLng(region.lat, region.lng),
              radius: 400,
              fillColor: color,
              fillOpacity: 0.4,
              strokeWeight: 0
            });
            circle.setMap(map);

            const scannerBaseUrl = typeof window.SAFEHOME_CONFIG !== 'undefined' 
              ? window.SAFEHOME_CONFIG.scannerUrl 
              : '/searchscan';

            let statusText = '안전';
            if (region.score >= 80) statusText = '위험 (전세가율 높음)';
            else if (region.score >= 60) statusText = '주의 (전세가율 보통)';

            const content = `
              <div class="infowindow-content" style="padding:15px; min-width:220px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                  <strong style="font-size:16px;">${region.region}</strong>
                  <button onclick="window.toggleFavorite && window.toggleFavorite('${region.region}')" 
                          style="background:none; border:none; font-size:20px; cursor:pointer; padding:0; line-height:1;">
                    ⭐
                  </button>
                </div>
                <div style="margin-bottom:8px;">
                  평균 전세가율: <strong>${typeof region.score === 'number' ? region.score.toFixed(1) : region.score}%</strong><br>
                  상태: <span style="color: ${color}">${statusText}</span>
                </div>
                <div style="display:flex; gap:6px;">
                  <a href="${scannerBaseUrl}?region=${encodeURIComponent(region.region)}" 
                     style="flex:1; background:#1565c0; color:white; text-align:center; padding:6px; text-decoration:none; border-radius:4px; font-size:12px;">
                    매물 분석
                  </a>
                  <button onclick="window.searchAddressFromMap && window.searchAddressFromMap('${region.region}')" 
                          style="flex:1; background:#28a745; color:white; border:none; padding:6px; border-radius:4px; cursor:pointer; font-size:12px;">
                    지도 이동
                  </button>
                </div>
              </div>
            `;

            // InfoWindow는 생성하지 않음 (검색 결과 InfoWindow만 사용)

            const regionInfo = {
              circle: circle,
              infowindow: null, // InfoWindow 제거
              category: region.score >= 80 ? 'danger' : region.score >= 60 ? 'warning' : 'safe',
              data: region
            };

            // React ref에 저장
            regionDataRef.current[region.region] = regionInfo;
            circlesRef.current.push(circle);

            // 전역 변수에도 저장 (기존 map.js 함수들과 연동)
            window.regionData[region.region] = regionInfo;
            
            // localStorage에서 복원된 전세가율 데이터가 있으면 적용
            if (storedJeonseRates[region.region]) {
              const stored = storedJeonseRates[region.region];
                    regionInfo.calculatedScore = stored.score;
                    regionInfo.riskLevel = {
                        category: stored.category,
                        text: stored.text,
                        color: stored.color
                    };
            }
            
            window.regions.push({
              region: region.region,
              score: region.score,
              category: regionInfo.category,
              lat: region.lat,
              lng: region.lng
            });

            // 원 클릭 시 즉시 검색 함수 호출 (검색 결과 InfoWindow 자동 표시)
            window.kakao.maps.event.addListener(circle, 'click', function() {
              // 모든 정보창 닫기
              Object.values(window.regionData).forEach(data => {
                if (data.infowindow) data.infowindow.close();
              });
              if (window.realTxInfoWindow) {
                window.realTxInfoWindow.close();
                window.realTxInfoWindow = null;
              }
              
              // 검색 입력창에 지역명 설정
              const searchInput = document.getElementById('address-search');
              if (searchInput) {
                searchInput.value = region.region;
              }
              
              // 검색 함수 호출하여 검색 결과 InfoWindow 즉시 표시
              if (window.searchAddress) {
                window.searchAddress();
              } else if (window.searchAddressFromMap) {
                window.searchAddressFromMap(region.region);
              }
            });
          } catch (error) {
            console.error(`[히트맵] ${region.region} 원 생성 실패:`, error);
          }
        });

        // 기존 map.js 함수들 호출 (UI 업데이트)
        if (typeof window.updateRegionList === 'function') {
          window.updateRegionList();
        }
        if (typeof window.updateStats === 'function') {
          window.updateStats();
        }
        
        // localStorage에서 전세가율 데이터 복원 (React 모듈 로드 후)
        if (typeof window.restoreJeonseRatesFromStorage === 'function') {
          setTimeout(() => {
            window.restoreJeonseRatesFromStorage();
            if (typeof window.updateRegionList === 'function') {
              window.updateRegionList();
            }
            if (typeof window.loadRecentSearches === 'function') {
              window.loadRecentSearches();
            }
          }, 200);
        }
        
        // 사이드바 로딩 (지도 페이지인 경우)
        if (window.location.pathname === '/map') {
          if (typeof window.loadRecentSearches === 'function') {
            setTimeout(() => window.loadRecentSearches(), 100);
          }
          if (typeof window.loadFavorites === 'function') {
            setTimeout(() => window.loadFavorites(), 100);
          }
        }
      })
      .catch(error => {
        console.error('[히트맵] 데이터 로드 중 오류:', error);
      });
  };

  return (
    <div 
      id="map" 
      ref={mapContainerRef}
      style={{ width: '100%', height: '100%' }}
    />
  );
};

export default MapComponent;
