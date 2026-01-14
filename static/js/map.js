// 초기화 영역: 변수 선언 및 전역 설정
let map;
let regionData = {};
// HTML에서 정의한 전역 설정 사용
const scannerBaseUrl = typeof SAFEHOME_CONFIG !== 'undefined' ? SAFEHOME_CONFIG.scannerUrl : '/searchscan';
let currentFilter = 'all';
let regions = [];

// 공통 위험도 계산 함수 (전세가율 기준)
// 기준: >= 80% (위험), >= 60% (주의), < 60% (안전)
function calculateRiskLevel(score) {
    if (score === null || score === undefined || isNaN(score)) {
        return { category: 'safe', text: '안전', color: '#28a745' };
    }
    
    if (score >= 80) {
        return { category: 'danger', text: '위험', color: '#dc3545' };
    } else if (score >= 60) {
        return { category: 'warning', text: '주의', color: '#ffc107' };
    } else {
        return { category: 'safe', text: '안전', color: '#28a745' };
    }
}

// 전역으로 노출 (다른 스크립트에서도 사용 가능)
window.calculateRiskLevel = calculateRiskLevel;

// 전역 변수로 노출 (React 모듈과 공유)
if (typeof window.regionData === 'undefined') {
    window.regionData = regionData;
} else {
    regionData = window.regionData;
}
if (typeof window.regions === 'undefined') {
    window.regions = regions;
} else {
    regions = window.regions;
}

// localStorage에서 전세가율 데이터 복원
function restoreJeonseRatesFromStorage() {
    try {
        const storedRates = JSON.parse(localStorage.getItem('regionJeonseRates') || '{}');
        const now = Date.now();
        const maxAge = 7 * 24 * 60 * 60 * 1000; // 7일
        
        // window.regionData가 초기화된 후에 복원
        if (!window.regionData) {
            window.regionData = {};
        }
        
        let restoredCount = 0;
        Object.keys(storedRates).forEach(region => {
            const data = storedRates[region];
            // 7일 이상 된 데이터는 제거
            if (!data.timestamp || (now - data.timestamp > maxAge)) {
                delete storedRates[region];
                return;
            }
            
            // regionData에 복원 (regionData[region]이 없어도 생성)
            if (!window.regionData[region]) {
                window.regionData[region] = {};
            }
            
            window.regionData[region].calculatedScore = data.score;
            window.regionData[region].riskLevel = {
                category: data.category,
                text: data.text,
                color: data.color
            };
            restoredCount++;
        });
        
        // 오래된 데이터 제거 후 다시 저장
        localStorage.setItem('regionJeonseRates', JSON.stringify(storedRates));
    } catch (e) {
        console.warn('[전세가율 복원] localStorage 복원 실패:', e);
    }
}

// [초기화] 페이지 로드 시 실행
document.addEventListener('DOMContentLoaded', function() {
    // React 모듈이 로드되었는지 확인 (React 모듈이 지도 렌더링을 담당)
    const isReactModuleLoaded = typeof window.initMapModule === 'function';
    
    // React 모듈이 없을 때만 기존 방식으로 지도 초기화
    if (!isReactModuleLoaded) {
        initMap();
    }
    
    // 이벤트 리스너는 항상 설정 (검색, 필터 등 기능)
    setupEventListeners();
    
    // localStorage에서 전세가율 데이터 복원 (지도 로드 후)
    setTimeout(() => {
        restoreJeonseRatesFromStorage();
        // 복원 후 사이드바 업데이트
        if (typeof updateRegionList === 'function') {
            updateRegionList();
        }
        if (typeof loadRecentSearches === 'function') {
            loadRecentSearches();
        }
    }, 1500); // 지도와 히트맵 데이터 로드 후 복원
    
    // URL 파라미터에서 region이 있으면 자동 검색
    const urlParams = new URLSearchParams(window.location.search);
    const regionParam = urlParams.get('region');
    if (regionParam) {
        setTimeout(() => {
            document.getElementById('address-search').value = regionParam;
            searchAddress();
        }, 1000); // 지도 로드 후 검색
    }
});

// 이벤트 리스너 설정
function setupEventListeners() {
    // 검색 버튼
    const searchBtn = document.getElementById('search-btn');
    if (searchBtn) {
        searchBtn.addEventListener('click', searchAddress);
    }

    // 엔터키 검색
    const searchInput = document.getElementById('address-search');
    if (searchInput) {
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') searchAddress();
        });
    }

    // 초기화 버튼
    const clearBtn = document.getElementById('clear-btn');
    if (clearBtn) {
        clearBtn.onclick = function() {
            document.getElementById('address-search').value = '';
            // 실거래 원 제거
            clearRealTransactionCircles();
            // 지도 초기화 (전역 map 사용)
            const globalMap = window.map || map;
            if (globalMap) {
                globalMap.setCenter(new kakao.maps.LatLng(37.566826, 126.9786567));
                globalMap.setLevel(9);
            }
        };
    }

    // 지도 페이지의 왼쪽 사이드 패널을 제어하도록 toggleLeftSidebar 오버라이드
    if (typeof window.toggleLeftSidebar === 'function') {
        const originalToggleLeftSidebar = window.toggleLeftSidebar;
        window.toggleLeftSidebar = function() {
            const sidePanel = document.getElementById('side-panel');
            if (sidePanel) {
                // 지도 페이지의 side-panel 토글
                sidePanel.classList.toggle('active');
                sidePanel.classList.toggle('hidden');
            } else {
                // 다른 페이지에서는 원래 함수 실행
                originalToggleLeftSidebar();
            }
        };
    }

    // 지도 페이지의 오른쪽 사이드 패널을 제어하도록 toggleRightSidebar 오버라이드
    if (typeof window.toggleRightSidebar === 'function') {
        const originalToggleRightSidebar = window.toggleRightSidebar;
        window.toggleRightSidebar = function() {
            const rightSidebar = document.getElementById('right-sidebar');
            if (rightSidebar) {
                // 지도 페이지의 right-sidebar 토글 (원래 함수와 동일한 로직 사용)
                const isActive = rightSidebar.classList.contains('active');
                rightSidebar.classList.toggle('active');
                rightSidebar.classList.toggle('hidden');
                
                // CSS transform과 visibility 직접 설정
                if (rightSidebar.classList.contains('active')) {
                    rightSidebar.style.transform = 'translateX(0)';
                    rightSidebar.style.visibility = 'visible';
                } else {
                    rightSidebar.style.transform = 'translateX(100%)';
                    rightSidebar.style.visibility = 'hidden';
                }
            } else {
                // 다른 페이지에서는 원래 함수 실행
                originalToggleRightSidebar();
            }
        };
    }

    // 필터 버튼 클릭
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            currentFilter = this.dataset.filter;
            updateRegionList();
            filterMapCircles();
        });
    });
}

// 지도 관련 함수

// 1. 지도 생성 및 히트맵(기본 데이터) 로드
function initMap() {
    // React 모듈이 이미 지도를 생성했는지 확인
    if (window.map && typeof window.map.setCenter === 'function') {
        map = window.map; // React 모듈이 생성한 지도 인스턴스 사용
        // 히트맵 데이터는 React 모듈이 이미 로드했으므로 여기서는 로드하지 않음
        return;
    }
    
    const mapContainer = document.getElementById('map');
    const mapOption = {
        center: new kakao.maps.LatLng(37.566826, 126.9786567), // 서울 시청
        level: 9
    };
    map = new kakao.maps.Map(mapContainer, mapOption);
    // 전역으로도 노출
    window.map = map;

    // 기본 히트맵 데이터 로드 (백엔드 DB/더미 데이터 사용)
    fetch('/heatmap')
        .then(response => {
            if (!response.ok) {
                console.error('히트맵 API 호출 실패:', response.status, response.statusText);
                throw new Error(`API 호출 실패: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (!data || !Array.isArray(data)) {
                console.error('히트맵 데이터 형식 오류:', typeof data, data);
                alert('히트맵 데이터를 불러오는데 실패했습니다. 페이지를 새로고침해주세요.');
                return;
            }
            if (data.length === 0) {
                console.warn('히트맵 데이터가 비어있습니다.');
                alert('히트맵 데이터가 없습니다. 잠시 후 다시 시도해주세요.');
                return;
            }
            
            // 유효한 데이터만 필터링 (lat, lng가 있는 것만)
            const validData = data.filter(region => {
                const isValid = region && region.region && 
                               typeof region.lat === 'number' && 
                               typeof region.lng === 'number' &&
                               !isNaN(region.lat) && !isNaN(region.lng);
                if (!isValid) {
                    console.warn('[히트맵] 유효하지 않은 데이터:', region);
                }
                return isValid;
            });
            
            if (validData.length === 0) {
                console.error('[히트맵] 유효한 데이터가 없습니다.');
                alert('유효한 히트맵 데이터가 없습니다.');
                return;
            }
                        
            regions = validData.map(region => ({
                ...region,
                category: region.score >= 80 ? 'danger' : region.score >= 60 ? 'warning' : 'safe'
            }));
            
            // 전역 변수에도 저장
            window.regions = regions;
            window.regionData = regionData;
            
            updateStats();
            updateRegionList();
            
            // 지도에 원 그리기
            let circleCount = 0;
            validData.forEach(region => {
                try {
                // 위험도에 따른 색상 결정 (전세가율 기반: 80% 이상 위험, 60-79% 주의, 60% 미만 안전)
                let color = '#28a745'; // 안전 (초록) - 전세가율 60% 미만
                if (region.score >= 80) color = '#dc3545'; // 위험 (빨강) - 전세가율 80% 이상
                else if (region.score >= 60) color = '#ffc107'; // 주의 (노랑) - 전세가율 60-79%

                const circle = new kakao.maps.Circle({
                    center: new kakao.maps.LatLng(region.lat, region.lng),
                    radius: 400, // 동 넓이에 맞게 조정 (약 0.5km²)
                    fillColor: color,
                    fillOpacity: 0.4, // 배경 히트맵은 투명하게
                    strokeWeight: 0
                });
                circle.setMap(map);
                    circleCount++;
                
                const scannerUrl = `${scannerBaseUrl}?region=${encodeURIComponent(region.region)}`;
                // 전세가율 기반 상태 텍스트
                let statusText = '안전';
                if (region.score >= 80) statusText = '위험 (전세가율 높음)';
                else if (region.score >= 60) statusText = '주의 (전세가율 보통)';
                
                    // 즐겨찾기 버튼을 포함한 정보창 내용
                    const favoriteId = `favorite-${region.region.replace(/\s/g, '-')}`;
                const content = `
                        <div class="infowindow-content" style="padding:15px; min-width:220px;">
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                                <strong style="font-size:16px;">${region.region}</strong>
                                <button id="${favoriteId}" onclick="toggleFavorite('${region.region}', '${favoriteId}')" 
                                        style="background:none; border:none; font-size:20px; cursor:pointer; padding:0; line-height:1;">
                                    ⭐
                                </button>
                            </div>
                            <div style="margin-bottom:8px;">
                        평균 전세가율: <strong>${typeof region.score === 'number' ? region.score.toFixed(1) : region.score}%</strong><br>
                                상태: <span style="color: ${color}">${statusText}</span>
                            </div>
                            <div style="display:flex; gap:6px;">
                                <a href="${scannerUrl}" 
                                   style="flex:1; background:#1565c0; color:white; text-align:center; padding:6px; text-decoration:none; border-radius:4px; font-size:12px;">
                                   매물 분석
                                </a>
                                <button onclick="searchAddressFromFavorite('${region.region}')" 
                                        style="flex:1; background:#28a745; color:white; border:none; padding:6px; border-radius:4px; cursor:pointer; font-size:12px;">
                                    지도 이동
                                </button>
                            </div>
                    </div>`;
                
                // InfoWindow는 생성하지 않음 (검색 결과 InfoWindow만 사용)

                regionData[region.region] = {
                    circle: circle,
                    infowindow: null, // InfoWindow 제거
                    category: region.score >= 80 ? 'danger' : region.score >= 60 ? 'warning' : 'safe',
                    data: region
                };
                
                // 원 클릭 시 즉시 검색 함수 호출 (검색 결과 InfoWindow 자동 표시)
                kakao.maps.event.addListener(circle, 'click', function() {
                    // 이전 실거래 원 제거 (중복 방지)
                    clearRealTransactionCircles();
                    
                    // 기존 정보창 모두 닫기 (전역 변수 사용)
                    const globalRegionData = window.regionData || regionData;
                    const globalMap = window.map || map;
                    Object.values(globalRegionData).forEach(data => {
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
        })
        .catch(error => {
            console.error('[히트맵] 데이터 로드 중 오류:', error);
            alert('히트맵 데이터를 불러오는데 실패했습니다. 페이지를 새로고침해주세요.\n오류: ' + error.message);
        });
    
    // 최근 검색 기록 로드
    loadRecentSearches();
    
    // 즐겨찾기 목록 로드
    loadFavorites();
}

// 즐겨찾기 관련 함수
let favoriteRegions = new Set();

function loadFavorites() {
    fetch('/api/favorites')
        .then(res => res.ok ? res.json() : [])
        .then(data => {
            favoriteRegions = new Set(data.map(f => f.region));
            updateFavoriteButtons();
            updateFavoriteSidebar(data);
        })
        .catch(err => {
            console.error('즐겨찾기 로드 실패:', err);
        });
}

function updateFavoriteButtons() {
    favoriteRegions.forEach(region => {
        const favoriteId = `favorite-${region.replace(/\s/g, '-')}`;
        const btn = document.getElementById(favoriteId);
        if (btn) {
            btn.textContent = '⭐';
            btn.style.color = '#ffc107';
            btn.title = '즐겨찾기 해제';
        }
    });
}

function toggleFavorite(region, buttonId) {
    const isFavorite = favoriteRegions.has(region);
    
    if (isFavorite) {
        // 즐겨찾기 제거
        fetch('/api/favorites', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ region: region })
        })
        .then(res => {
            if (res.status === 401) {
                window.location.href = '/login';
                return;
            }
            return res.json();
        })
        .then(data => {
            if (data && data.status === 'success') {
                favoriteRegions.delete(region);
                const btn = document.getElementById(buttonId);
                if (btn) {
                    btn.textContent = '☆';
                    btn.style.color = '#ccc';
                    btn.title = '즐겨찾기 추가';
                }
                loadFavorites(); // 사이드바 업데이트
            }
        })
        .catch(err => {
            console.error('즐겨찾기 제거 실패:', err);
        });
    } else {
        // 즐겨찾기 추가
        fetch('/api/favorites', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ region: region })
        })
        .then(res => {
            if (res.status === 401) {
                if (confirm('즐겨찾기 기능을 사용하려면 로그인이 필요합니다. 로그인 페이지로 이동하시겠습니까?')) {
                    window.location.href = '/login';
                }
                return;
            }
            return res.json();
        })
        .then(data => {
            if (data && data.status === 'success') {
                favoriteRegions.add(region);
                const btn = document.getElementById(buttonId);
                if (btn) {
                    btn.textContent = '⭐';
                    btn.style.color = '#ffc107';
                    btn.title = '즐겨찾기 해제';
                }
                loadFavorites(); // 사이드바 업데이트
            }
        })
        .catch(err => {
            console.error('즐겨찾기 추가 실패:', err);
        });
    }
}

function searchAddressFromFavorite(region) {
    // 지역명 정규화하여 입력
    const normalizedRegion = normalizeRegionName(region);
    document.getElementById('address-search').value = normalizedRegion;
    searchAddress();
}

function updateFavoriteSidebar(favorites) {
    const sidebar = document.getElementById('favorite-sidebar');
    if (!sidebar) return;
    
    if (favorites.length === 0) {
        sidebar.innerHTML = '<div style="color: #999; font-size: 13px; text-align: center; padding: 20px;">즐겨찾기한 지역이 없습니다</div>';
        return;
    }
    
    sidebar.innerHTML = favorites.slice(0, 10).map(fav => `
        <div class="favorite-sidebar-item" style="padding: 10px; margin-bottom: 8px; background: #f9fafb; border-radius: 6px; cursor: pointer; transition: background 0.2s;"
             onclick="searchAddressFromFavorite('${fav.region}')"
             onmouseover="this.style.background='#f0f0f0'"
             onmouseout="this.style.background='#f9fafb'">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-weight: 600; color: #333;">${fav.region}</span>
                <button onclick="event.stopPropagation(); toggleFavorite('${fav.region}', 'sidebar-${fav.id}')" 
                        style="background: none; border: none; font-size: 16px; cursor: pointer; color: #ffc107; padding: 0;">
                    ⭐
                </button>
            </div>
        </div>
    `).join('');
}

// 전역 함수 노출 (React 모듈에서 사용할 수 있도록)
window.searchAddressFromMap = function(region) {
    if (document.getElementById('address-search')) {
        // 지역명 정규화하여 입력
        const normalizedRegion = normalizeRegionName(region);
        document.getElementById('address-search').value = normalizedRegion;
        searchAddress();
    }
};

// 지역명 정규화 함수도 전역으로 노출
window.normalizeRegionName = normalizeRegionName;

// 전역 함수로 노출 (사이드바에서 사용)
window.searchAddress = searchAddress;
window.updateRegionList = updateRegionList;
window.updateStats = updateStats;
window.filterMapCircles = filterMapCircles;
window.restoreJeonseRatesFromStorage = restoreJeonseRatesFromStorage;

// 지역명 정규화 함수 (동, 가, 리 추가/제거)
function normalizeRegionName(region) {
    if (!region) return region;
    const trimmed = region.trim();
    
    // 이미 동/가/리로 끝나면 그대로 반환
    if (/동$|가$|리$/.test(trimmed)) {
        return trimmed;
    }
    
    // 동/가/리가 없으면 동 추가 시도
    // 단, 특수한 경우(예: "서울", "강남구" 등)는 제외
    if (!/구$|시$|도$|특별시$|광역시$/.test(trimmed)) {
        return trimmed + '동';
    }
    
    return trimmed;
}

// 2. 주소 검색 함수
function searchAddress() {
    const searchKeyword = document.getElementById('address-search').value.trim();
    if (!searchKeyword) {
        alert("지역명을 입력해주세요.");
        return;
    }
    
    // 전역 regionData 사용 (React 모듈이 설정한 경우)
    const globalRegionData = window.regionData || regionData;
    const globalMap = window.map || map;
    
    // 지도 인스턴스가 없으면 에러
    if (!globalMap) {
        console.error('지도 인스턴스가 없습니다. React 모듈이 로드되었는지 확인하세요.');
        alert('지도가 아직 로드되지 않았습니다. 잠시 후 다시 시도해주세요.');
        return;
    }
    
    // 기존 실거래 원 제거 및 이전 검색 결과 초기화
    clearRealTransactionCircles();
    
    // 진행 중인 모든 검색 요청 취소
    if (window.currentSearchAbortController) {
        window.currentSearchAbortController.abort();
        window.currentSearchAbortController = null;
    }
    
    // 모든 활성 검색 요청 취소
    if (window.activeSearchControllers) {
        window.activeSearchControllers.forEach(controller => {
            try {
                controller.abort();
            } catch (e) {
                // 이미 취소된 경우 무시
            }
        });
        window.activeSearchControllers = [];
    }
    
    // 진행 중인 모든 검색 요청 취소 플래그 제거
    Object.keys(window).forEach(key => {
        if (key.startsWith('search_')) {
            delete window[key];
        }
    });
    
    
    // 지역명 정규화 (검색어와 정규화된 버전 모두 시도)
    const normalizedKeyword = normalizeRegionName(searchKeyword);
    
    // 지역 데이터에서 먼저 찾기 (정확한 매칭 우선)
    let targetRegion = globalRegionData[searchKeyword] || globalRegionData[normalizedKeyword];
    
    // 정확한 매칭이 없으면 부분 매칭 시도
    if (!targetRegion) {
        const matchedKey = Object.keys(globalRegionData).find(key => {
            const keyClean = key.replace(/동|가|리/g, '').trim();
            const searchClean = searchKeyword.replace(/동|가|리/g, '').trim();
            const normalizedClean = normalizedKeyword.replace(/동|가|리/g, '').trim();
            
            // 정확한 매칭
            if (keyClean === searchClean || keyClean === normalizedClean) {
                return true;
            }
            
            // 부분 매칭
            if (keyClean.includes(searchClean) || searchClean.includes(keyClean) ||
                keyClean.includes(normalizedClean) || normalizedClean.includes(keyClean)) {
                return true;
            }
            
            return false;
        });
        
        if (matchedKey) {
            targetRegion = globalRegionData[matchedKey];
        }
    }
    
    // 지역을 찾았으면 지도 이동 및 검색
    if (targetRegion && targetRegion.circle) {
        const position = targetRegion.circle.getPosition();
        globalMap.setCenter(position);
        globalMap.setLevel(5);
        
        // 검색할 지역명 결정 (정규화된 키워드 우선)
        const regionToSearch = normalizedKeyword || searchKeyword || targetRegion.data.region;
        
        // 실거래 데이터 로드 (자동으로 InfoWindow 표시)
        loadRealTransactionsForMap(regionToSearch, position, true, false);
    } else {
        // 주소 검색 API 사용
        const geocoder = new kakao.maps.services.Geocoder();
        geocoder.addressSearch(searchKeyword, function(result, status) {
            if (status === kakao.maps.services.Status.OK) {
                const coords = new kakao.maps.LatLng(result[0].y, result[0].x);
                globalMap.setCenter(coords);
                globalMap.setLevel(5);
                
                // 정규화된 키워드로 검색
                loadRealTransactionsForMap(normalizedKeyword || searchKeyword, coords, true, false);
            } else {
                // 주소 검색 실패 시에도 검색 결과가 없다는 팝업
                alert(`'${searchKeyword}' 지역의 검색 결과가 없습니다.\n\n정확한 동 이름(예: 청담동, 역삼동)을 입력해주세요.`);
            }
        });
    }
}

// 3. 실제 데이터(매물 분석 결과) 가져오기
function loadRealTransactionsForMap(region, coords, autoOpenInfoWindow = true, showAlert = false) {
    const globalMap = window.map || map;
    
    // 지역명이 없거나 잘못된 경우 에러 처리
    if (!region || region.trim() === '') {
        console.error('[검색] 지역명이 없습니다.');
        if (showAlert) {
            alert('지역명이 올바르지 않습니다.');
        }
        return;
    }
    
    // 지역명 정리 (앞뒤 공백 제거)
    const cleanRegion = region.trim();
    
    // 중복 호출 방지: 같은 지역에 대한 동시 요청 방지
    const requestKey = `search_${cleanRegion}`;
    if (window[requestKey]) {
        return; // 이미 진행 중인 요청이 있으면 중복 호출 방지
    }
    
    // 이전 검색 요청 취소 (다른 지역 검색 시)
    if (window.currentSearchAbortController) {
        window.currentSearchAbortController.abort();
    }
    
    // 진행 중인 모든 검색 요청 취소 (다른 지역 검색 방지)
    if (!window.activeSearchControllers) {
        window.activeSearchControllers = [];
    }
    window.activeSearchControllers.forEach(controller => {
        if (controller && controller !== window.currentSearchAbortController) {
            try {
                controller.abort();
            } catch (e) {
                // 이미 취소된 경우 무시
            }
        }
    });
    window.activeSearchControllers = [];
    
    // 새로운 AbortController 생성
    const abortController = new AbortController();
    window.currentSearchAbortController = abortController;
    window.activeSearchControllers.push(abortController);
    window[requestKey] = true;
    
    // 즉시 로딩 중 InfoWindow 표시 (속도 개선)
    if (autoOpenInfoWindow && globalMap) {
        const loadingContent = `
            <div style="padding:15px; min-width:220px; font-size:13px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <h4 style="margin:0;">${cleanRegion} 분석 중...</h4>
                </div>
                <div style="text-align:center; padding:20px;">
                    <div style="display:inline-block; width:20px; height:20px; border:3px solid #f3f3f3; border-top:3px solid #1565c0; border-radius:50%; animation:spin 1s linear infinite;"></div>
                    <p style="margin-top:10px; color:#666;">데이터를 불러오는 중입니다...</p>
                </div>
            </div>
            <style>
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
            </style>
        `;
        
        // 기존 InfoWindow 닫기
        if (window.realTxInfoWindow) {
            window.realTxInfoWindow.close();
        }
        
        const loadingInfoWindow = new kakao.maps.InfoWindow({
            position: coords,
            content: loadingContent,
            removable: true
        });
        loadingInfoWindow.open(globalMap);
        window.realTxInfoWindow = loadingInfoWindow;
    }
    
    // /analyze API 호출 (전세가율 포함) - 정리된 지역명 사용
    // AbortSignal을 사용하여 요청 취소 가능하도록 함
    fetch(`/analyze?region=${encodeURIComponent(cleanRegion)}`, {
        signal: abortController.signal
    })
        .then(res => {
            if (!res.ok) {
                console.error(`[검색] API 응답 실패: ${res.status}`);
                return { properties: [] };
            }
            return res.json();
        })
        .then(data => {
            // 에러 응답 확인
            if (data.error) {
                console.error(`[검색] API 에러: ${data.error}`);
                if (window.realTxInfoWindow) {
                    window.realTxInfoWindow.close();
                    window.realTxInfoWindow = null;
                }
                if (showAlert) {
                    alert(`검색 중 오류가 발생했습니다: ${data.error}`);
                }
                return;
            }
            
            const properties = data.properties || [];
            console.log(`[검색] ${cleanRegion} 검색 결과: ${properties.length}건`);
            
            if (properties.length > 0) {
                // 데이터가 있으면 분석하여 원 그리기 (정보창 자동 열기 여부 전달)
                // 중요: 정리된 지역명을 사용하여 정보창에 올바른 지역명 표시
                displayRealTransactionCircles(cleanRegion, properties, coords, autoOpenInfoWindow);
                updateRealTransactionResults(cleanRegion, properties);
                
                // 검색 기록 저장 (위험도 점수 계산) - 정리된 지역명 사용
                const riskScore = calculateRiskScoreFromProperties(properties);
                saveSearchHistory(cleanRegion, riskScore);
            } else {
                // 데이터가 없으면 로딩 InfoWindow 닫기
                if (window.realTxInfoWindow) {
                    window.realTxInfoWindow.close();
                    window.realTxInfoWindow = null;
                }
                
                // 데이터가 없으면 아무것도 표시하지 않음 (검색 기록도 저장하지 않음)
                if (showAlert) {
                    alert(`'${region}' 지역의 검색 결과가 없습니다.\n\n정확한 동 이름(예: 청담동, 역삼동)을 입력해주세요.`);
                }
            }
        })
        .catch((error) => {
            // AbortError는 정상적인 취소이므로 에러로 처리하지 않음
            if (error.name === 'AbortError') {
                return;
            }
            
            // 에러 시 로딩 InfoWindow 닫기
            if (window.realTxInfoWindow) {
                window.realTxInfoWindow.close();
                window.realTxInfoWindow = null;
            }
            console.error('실거래 데이터를 불러오는데 실패했습니다:', error);
        })
        .finally(() => {
            // 요청 완료 후 플래그 제거 (성공/실패 관계없이)
            delete window[requestKey];
            // 현재 요청이 완료된 경우에만 AbortController 제거
            if (window.currentSearchAbortController === abortController) {
                window.currentSearchAbortController = null;
            }
        });
}

// 매물 리스트에서 위험도 점수 계산
function calculateRiskScoreFromProperties(properties) {
    if (!properties || properties.length === 0) return null;
    
    // 전세가율 기반으로 위험도 점수 계산
    const propertiesWithRate = properties.filter(p => p.jeonse_rate != null && p.jeonse_rate > 0);
    if (propertiesWithRate.length === 0) return null;
    
    const avgJeonseRate = propertiesWithRate.reduce((sum, p) => sum + p.jeonse_rate, 0) / propertiesWithRate.length;
    return Math.round(avgJeonseRate);
}

// 검색 기록 저장
function saveSearchHistory(region, riskScore) {
    if (!region) return;
    
    fetch('/api/search-history', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            region: region,
            risk_score: riskScore
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        // 저장 완료 후 약간의 지연을 두고 검색 기록 목록 업데이트
        setTimeout(() => {
        loadRecentSearches();
        }, 300);
    })
    .catch(error => {
        console.error('검색 기록 저장 실패:', error);
        // 저장 실패해도 검색 기록 목록은 업데이트 시도
        setTimeout(() => {
            loadRecentSearches();
        }, 300);
    });
}

// 4. [핵심] 실제 데이터를 분석하여 원 색상 및 정보창 표시 (전세가율 기반)
function displayRealTransactionCircles(region, properties, centerCoords, autoOpenInfoWindow = true) {
    // 전역 변수 사용 (React 모듈이 설정한 경우)
    const globalMap = window.map || map;
    const globalRegionData = window.regionData || regionData;
    
    // 현재 검색 중인 지역 저장 (필터 기능에서 사용)
    // 중요: 이전 검색 결과를 덮어쓰기 위해 명시적으로 설정
    window.currentSearchRegion = region;
    
    if (!globalMap) {
        console.error('지도 인스턴스가 없습니다.');
        return;
    }
    
    // 기존 실거래 원 제거
    if (window.realTxCircles) {
        window.realTxCircles.forEach(circle => circle.setMap(null));
    }
    window.realTxCircles = [];
    
    // (1) 전세가율 기반 위험도 계산
    // 전세가율이 있는 매물만 필터링 (0.5% 같은 비정상적인 값 제외)
    // 전세가율은 일반적으로 30% 이상이므로, 10% 미만은 데이터 오류로 간주
    const propertiesWithJeonseRate = properties.filter(p => {
        if (p.jeonse_rate == null || p.jeonse_rate <= 0) return false;
        // 전세가율이 10% 미만이면 데이터 오류로 간주하여 제외
        if (p.jeonse_rate < 10) {
            return false;
        }
        return true;
    });
    
    if (propertiesWithJeonseRate.length === 0) {
        // 전세가율 데이터가 없으면 표시하지 않음
        return;
    }
    
    // 평균 전세가율 계산
    const avgJeonseRate = propertiesWithJeonseRate.reduce((sum, p) => sum + p.jeonse_rate, 0) / propertiesWithJeonseRate.length;
    
    // (2) 전세가율에 따른 색상 결정 (공통 함수 사용)
    const riskLevel = calculateRiskLevel(avgJeonseRate);
    const color = riskLevel.color;
    let statusText = riskLevel.text;
    // 정보창에서는 더 자세한 설명 추가
    if (avgJeonseRate >= 80) {
        statusText = '위험 (전세가율 높음)';
    } else if (avgJeonseRate >= 60) {
        statusText = '주의 (전세가율 보통)';
    } else {
        statusText = '안전 (전세가율 낮음)';
    }
    
    // 전역 변수에 저장하여 다른 부분에서도 사용 가능하도록
    // regionData가 없으면 생성
    if (!window.regionData) {
        window.regionData = {};
    }
    if (!window.regionData[region]) {
        window.regionData[region] = {};
    }
    
    window.regionData[region].calculatedScore = avgJeonseRate;
    window.regionData[region].riskLevel = riskLevel;
    
    // localStorage에 전세가율 저장 (새로고침 후에도 유지)
    try {
        const storedRates = JSON.parse(localStorage.getItem('regionJeonseRates') || '{}');
        storedRates[region] = {
            score: avgJeonseRate,
            category: riskLevel.category,
            text: riskLevel.text,
            color: riskLevel.color,
            timestamp: Date.now()
        };
        localStorage.setItem('regionJeonseRates', JSON.stringify(storedRates));
    } catch (e) {
        console.warn('[전세가율 저장] localStorage 저장 실패:', e);
    }
    
    // 왼쪽 사이드바와 오른쪽 사이드바 업데이트 (정보창의 값 반영)
    if (typeof updateRegionList === 'function') {
        updateRegionList();
    }
    if (typeof loadRecentSearches === 'function') {
        setTimeout(() => loadRecentSearches(), 100);
    }

    // (3) 지도 위에 원 그리기
    const circle = new kakao.maps.Circle({
        center: centerCoords,
        radius: 350, // 동 넓이에 맞게 조정 (검색 결과는 조금 더 작고 진하게 표시)
        fillColor: color,
        fillOpacity: 0.7, 
        strokeWeight: 2,
        strokeColor: '#fff'
    });
    circle.setMap(globalMap);
    
    // 전역 변수에 저장 (나중에 지우기 위해)
    if (!window.realTxCircles) window.realTxCircles = [];
    window.realTxCircles.push(circle);

    // (4) 정보창(InfoWindow) 내용 생성 (즐겨찾기 버튼 포함)
    const favoriteId = `favorite-tx-${region.replace(/\s/g, '-')}`;
    const isFavorite = favoriteRegions.has(region);
    const favoriteIcon = isFavorite ? '⭐' : '☆';
    const favoriteColor = isFavorite ? '#ffc107' : '#ccc';
    
    const content = `
        <div style="padding:15px; min-width:220px; font-size:13px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <h4 style="margin:0;">${region} 분석 결과</h4>
                <button id="${favoriteId}" onclick="toggleFavorite('${region}', '${favoriteId}')" 
                        style="background:none; border:none; font-size:20px; cursor:pointer; padding:0; line-height:1; color:${favoriteColor};"
                        title="${isFavorite ? '즐겨찾기 해제' : '즐겨찾기 추가'}">
                    ${favoriteIcon}
                </button>
            </div>
            <div style="margin-bottom:5px;">
                <span style="font-weight:bold; color:${color}">● ${statusText}</span>
            </div>
            <div style="color:#666; margin-bottom:10px;">
                평균 전세가율: <strong>${avgJeonseRate.toFixed(1)}%</strong><br>
                분석 매물 수: ${propertiesWithJeonseRate.length}건<br>
                전체 매물 수: ${properties.length}건
            </div>
            <div style="display:flex; gap:6px;">
            <a href="${scannerBaseUrl}?region=${encodeURIComponent(region)}" 
                   style="flex:1; background:#1565c0; color:white; text-align:center; padding:6px; text-decoration:none; border-radius:4px; font-size:12px;">
                   매물 분석
            </a>
                <button onclick="searchAddressFromFavorite('${region}')" 
                        style="flex:1; background:#28a745; color:white; border:none; padding:6px; border-radius:4px; cursor:pointer; font-size:12px;">
                    지도 이동
                </button>
            </div>
        </div>
    `;

    const infowindow = new kakao.maps.InfoWindow({
        position: centerCoords,
        content: content,
        removable: true
    });
    
    // 원 클릭 시 정보창 열기 (검색 결과 InfoWindow)
    kakao.maps.event.addListener(circle, 'click', function() {
        // 기존 정보창 모두 닫기
        Object.values(globalRegionData).forEach(d => {
            if (d.infowindow) d.infowindow.close();
        });
        if (window.realTxInfoWindow) {
            window.realTxInfoWindow.close();
        }
        // 검색 결과 InfoWindow 즉시 표시
        infowindow.setPosition(centerCoords);
        infowindow.open(globalMap);
        window.realTxInfoWindow = infowindow;
        
        // 정보창이 열린 후 즐겨찾기 버튼 업데이트
        updateFavoriteButtonInInfoWindow(region);
    });
    
    // 검색 후 바로 정보창 띄우기 (autoOpenInfoWindow가 true일 때만)
    // 로딩 InfoWindow가 이미 열려있으면 닫고 실제 데이터 InfoWindow로 교체
    if (autoOpenInfoWindow) {
        // 기존 로딩 InfoWindow 닫기
        if (window.realTxInfoWindow) {
            window.realTxInfoWindow.close();
        }
        
        // 실제 데이터 InfoWindow 열기
        infowindow.open(globalMap);
        window.realTxInfoWindow = infowindow;
        
        // 정보창이 열린 후 즐겨찾기 버튼 업데이트
        updateFavoriteButtonInInfoWindow(region);
    }
    
    // 즐겨찾기 버튼 업데이트 헬퍼 함수
    function updateFavoriteButtonInInfoWindow(region) {
        setTimeout(() => {
            const favoriteId = `favorite-tx-${region.replace(/\s/g, '-')}`;
            const btn = document.getElementById(favoriteId);
            if (btn) {
                const isFavorite = favoriteRegions.has(region);
                btn.textContent = isFavorite ? '⭐' : '☆';
                btn.style.color = isFavorite ? '#ffc107' : '#ccc';
                btn.title = isFavorite ? '즐겨찾기 해제' : '즐겨찾기 추가';
            }
        }, 50);
    }
}

// 실거래 원 제거 및 기존 원 복원
function clearRealTransactionCircles() {
    // 실거래 원 제거
    if (window.realTxCircles) {
        window.realTxCircles.forEach(circle => circle.setMap(null));
        window.realTxCircles = [];
    }
    
    // 정보창 닫기
    if (window.realTxInfoWindow) {
        window.realTxInfoWindow.close();
        window.realTxInfoWindow = null;
    }
    
    // 현재 검색 지역 초기화
    window.currentSearchRegion = null;
    
    // 실거래가 조회 결과 영역 초기화 (이전 검색 결과 제거)
    const resultsDiv = document.getElementById('real-tx-results');
    if (resultsDiv) {
        resultsDiv.innerHTML = '<div style="color: #999; font-size: 13px; text-align: center; padding: 20px;">지역을 조회하세요</div>';
    }
}

// ============================================
// UI 업데이트 함수
// ============================================

// 지도의 원 필터링 (정보창의 계산된 위험도 고려)
function filterMapCircles() {
    const globalRegionData = window.regionData || regionData;
    const globalMap = window.map || map;
    Object.values(globalRegionData).forEach(data => {
        // 정보창에서 계산한 위험도가 있으면 그것을 사용, 없으면 기본 category 사용
        let displayCategory = data.category;
        if (data.calculatedScore !== undefined && data.riskLevel) {
            displayCategory = data.riskLevel.category;
        }
        
        if (currentFilter === 'all' || displayCategory === currentFilter) {
            data.circle.setMap(globalMap);
        } else {
            data.circle.setMap(null);
            if (data.infowindow) {
                data.infowindow.close();
            }
        }
    });
    
    // 실거래 원도 필터링 (검색 결과 원)
    if (window.realTxCircles && window.realTxCircles.length > 0) {
        const globalRegionData = window.regionData || regionData;
        // 현재 검색 중인 지역의 위험도 확인
        const searchRegion = window.currentSearchRegion;
        if (searchRegion && globalRegionData[searchRegion]) {
            const regionData = globalRegionData[searchRegion];
            let displayCategory = regionData.category;
            if (regionData.calculatedScore !== undefined && regionData.riskLevel) {
                displayCategory = regionData.riskLevel.category;
            }
            
            window.realTxCircles.forEach(circle => {
                if (currentFilter === 'all' || displayCategory === currentFilter) {
                    circle.setMap(globalMap);
                } else {
                    circle.setMap(null);
                }
            });
        }
    }
}

// 지역 목록 업데이트
function updateRegionList() {
    const listContainer = document.getElementById('region-list');
    if (!listContainer) return;
    
    listContainer.innerHTML = '';
    
    // 전역 regions 사용 (React 모듈이 설정한 경우)
    const globalRegions = window.regions || regions;
    const globalRegionData = window.regionData || regionData;
    const globalMap = window.map || map;
    
    // 필터링: 정보창에서 계산한 위험도를 고려
    let filtered = currentFilter === 'all' 
        ? globalRegions 
        : globalRegions.filter(r => {
            const regionData = globalRegionData[r.region];
            // 정보창에서 계산한 위험도가 있으면 그것을 사용, 없으면 기본 category 사용
            let displayCategory = r.category;
            if (regionData && regionData.calculatedScore !== undefined && regionData.riskLevel) {
                displayCategory = regionData.riskLevel.category;
            }
            return displayCategory === currentFilter;
        });
    
    // 정렬: 정보창에서 계산한 점수를 우선 사용
    filtered.sort((a, b) => {
        const aData = globalRegionData[a.region];
        const bData = globalRegionData[b.region];
        const aScore = (aData && aData.calculatedScore !== undefined) ? aData.calculatedScore : a.score;
        const bScore = (bData && bData.calculatedScore !== undefined) ? bData.calculatedScore : b.score;
        return bScore - aScore;
    });
    
    filtered.forEach(region => {
        const item = document.createElement('div');
        
        // 정보창에서 계산한 값이 있으면 우선 사용, 없으면 히트맵 데이터 사용
        // localStorage에서도 확인 (새로고침 후 복원된 데이터)
        let regionData = globalRegionData[region.region];
        let displayScore = (regionData && regionData.calculatedScore !== undefined) 
            ? regionData.calculatedScore 
            : region.score;
        
        // localStorage에서도 확인 (regionData에 없거나 0인 경우)
        if (!regionData || !regionData.calculatedScore || displayScore === region.score || displayScore === 0) {
            try {
                const storedRates = JSON.parse(localStorage.getItem('regionJeonseRates') || '{}');
                if (storedRates[region.region]) {
                    displayScore = storedRates[region.region].score;
                    // regionData가 없으면 생성
                    if (!regionData) {
                        regionData = {};
                        globalRegionData[region.region] = regionData;
                    }
                    // regionData에도 복원
                    regionData.calculatedScore = displayScore;
                    regionData.riskLevel = {
                        category: storedRates[region.region].category,
                        text: storedRates[region.region].text,
                        color: storedRates[region.region].color
                    };
                }
            } catch (e) {
                // localStorage 읽기 실패 시 무시
                console.warn(`[전세가율 복원] ${region.region} 복원 실패:`, e);
            }
        }
        
        // 상태 텍스트 및 색상 (공통 함수 사용)
        const riskLevel = calculateRiskLevel(displayScore);
        const statusText = riskLevel.text;
        const statusColor = riskLevel.color;
        const displayCategory = riskLevel.category;
        
        item.className = `region-item ${displayCategory}`;
        
        item.innerHTML = `
            <div class="region-header">
            <div class="region-name">${region.region}</div>
                <div class="region-status" style="color: ${statusColor}; font-weight: 600; font-size: 12px;">${statusText}</div>
            </div>
            <div class="region-details">
                <div class="region-score">
                    <span class="score-label">전세가율:</span>
                    <span class="score-value" style="color: ${statusColor}; font-weight: 600;">${typeof displayScore === 'number' ? displayScore.toFixed(1) : displayScore}%</span>
                </div>
                <div class="region-info">
                    <span class="info-text">${displayScore >= 80 ? '전세가율이 높아 위험합니다' : displayScore >= 60 ? '전세가율이 보통입니다' : '전세가율이 낮아 안전합니다'}</span>
                </div>
            </div>
        `;
        item.onclick = () => {
            const targetRegion = globalRegionData[region.region];
            if (targetRegion) {
                // 기존 검색 결과 제거 (이전 검색 결과가 남아있지 않도록)
                clearRealTransactionCircles();
                
                // 모든 정보창 닫기
                Object.values(globalRegionData).forEach(d => {
                    if (d.infowindow) d.infowindow.close();
                });
                
                // 해당 지역으로 이동
                const position = targetRegion.circle.getPosition();
                globalMap.setCenter(position);
                globalMap.setLevel(5);
                
                // 검색 입력창에 지역명 설정
                const searchInput = document.getElementById('address-search');
                if (searchInput) {
                    searchInput.value = region.region;
                }
                
                // 검색 결과 InfoWindow 자동 표시 (명시적으로 지역명 전달)
                const regionToSearch = region.region;
                loadRealTransactionsForMap(regionToSearch, position, true);
            }
        };
        listContainer.appendChild(item);
    });

    const totalRegionsElement = document.getElementById('total-regions');
    if (totalRegionsElement) {
        totalRegionsElement.textContent = filtered.length;
    }
}

// 통계 업데이트
function updateStats() {
    // 전역 regions 사용 (React 모듈이 설정한 경우)
    const globalRegions = window.regions || regions;
    const danger = globalRegions.filter(r => r.score >= 80).length;
    const warning = globalRegions.filter(r => r.score >= 60 && r.score < 80).length;
    const safe = globalRegions.filter(r => r.score < 60).length;
    
    const dangerEl = document.getElementById('danger-count');
    const warningEl = document.getElementById('warning-count');
    const safeEl = document.getElementById('safe-count');
    const totalEl = document.getElementById('total-regions');
    
    if (dangerEl) dangerEl.textContent = danger;
    if (warningEl) warningEl.textContent = warning;
    if (safeEl) safeEl.textContent = safe;
    if (totalEl) totalEl.textContent = regions.length;
}

// 사이드바 실거래 결과 업데이트
function updateRealTransactionResults(region, properties) {
    const resultsDiv = document.getElementById('real-tx-results');
    if (!resultsDiv) return;
    
    if (properties.length === 0) {
        resultsDiv.innerHTML = '<div style="color: #999; font-size: 13px; padding: 10px;">매물 데이터가 없습니다</div>';
        return;
    }
    
    const html = properties.slice(0, 10).map(prop => {
        const jeonseRateText = prop.jeonse_rate ? `${prop.jeonse_rate}%` : '정보 없음';
        const jeonseRateColor = prop.jeonse_rate >= 80 ? '#dc3545' : prop.jeonse_rate >= 60 ? '#ffc107' : '#28a745';
        return `
        <div style="padding: 10px; border-bottom: 1px solid #eee; font-size: 13px;">
            <div style="font-weight: 600; margin-bottom: 4px;">${prop.name || '정보없음'}</div>
            <div style="color: #666; margin-bottom: 2px;">${prop.address || ''}</div>
            <div style="color: #1565c0; font-weight: 600; margin-bottom: 2px;">
                매매가: ${prop.price || '정보 없음'}
            </div>
            ${prop.jeonse_price ? `
            <div style="color: #666; margin-bottom: 2px;">
                전세가: ${prop.jeonse_price}
            </div>
            ` : ''}
            <div style="margin-top: 4px;">
                전세가율: <span style="color: ${jeonseRateColor}; font-weight: 600;">${jeonseRateText}</span>
            </div>
        </div>
    `;
    }).join('');
    
    resultsDiv.innerHTML = html;
    
    // 검색 입력창에도 자동 입력
    const realTxInput = document.getElementById('real-tx-region');
    if (realTxInput) {
        realTxInput.value = region;
    }
}

// ============================================
// 검색 로직
// ============================================

// 히스토리에서 검색
// 최근 검색 기록 로드
function loadRecentSearches() {
    fetch('/api/search-history')
        .then(response => {
            if (!response.ok) {
                console.warn('[검색 기록] API 응답 실패:', response.status);
                return [];
            }
            return response.json();
        })
        .then(data => {
            
            // 검색창 datalist 업데이트 (동 이름만)
            const datalist = document.getElementById('recent-searches-list');
            if (!datalist) {
                console.warn('[검색 기록] datalist 요소를 찾을 수 없습니다');
                return;
            }
            
            // datalist를 완전히 재생성하여 브라우저 캐시 문제 해결
            const searchInput = document.getElementById('address-search');
            if (!searchInput) {
                console.warn('[검색 기록] 검색 입력창을 찾을 수 없습니다');
                return;
            }
            
            const oldDatalistId = datalist.id;
            const wasFocused = document.activeElement === searchInput;
            
            // 입력창의 list 속성 제거
            searchInput.removeAttribute('list');
            
            // 기존 datalist 제거
            datalist.remove();
            
            // 새로운 datalist 생성
            const newDatalist = document.createElement('datalist');
            newDatalist.id = oldDatalistId;
            
            // datalist를 추가하고 list 속성을 복원하는 공통 함수
            const attachDatalist = () => {
                searchInput.parentNode.insertBefore(newDatalist, searchInput.nextSibling);
                searchInput.setAttribute('list', oldDatalistId);
                if (wasFocused) {
                    setTimeout(() => searchInput.focus(), 10);
                }
            };
            
            if (!data || data.length === 0) {
                attachDatalist();
                return;
            }
            
            // 중복 제거하면서 순서 유지하고 최대 5개만 추출
            const seen = new Set();
            const uniqueRegions = [];
            
            for (const item of data) {
                const region = item.region ? item.region.trim() : '';
                if (region && !seen.has(region)) {
                    seen.add(region);
                    uniqueRegions.push(region);
                    if (uniqueRegions.length >= 5) {
                        break; // 5개만 선택
                    }
                }
            }
            
            if (uniqueRegions.length === 0) {
                attachDatalist();
                return;
            }
            
            // option 요소 직접 생성 (최대 5개)
            uniqueRegions.forEach(region => {
                const option = document.createElement('option');
                option.value = region;
                option.textContent = region;
                newDatalist.appendChild(option);
            });
            
            // datalist 추가 및 속성 복원
            attachDatalist();
            
            // 오른쪽 사이드바 업데이트
            const container = document.getElementById('recent-searches');
            if (!container) return;
            
            if (!data || data.length === 0) {
                container.innerHTML = '<div style="color: #999; font-size: 13px; text-align: center; padding: 20px;">검색 기록이 없습니다.</div>';
                return;
            }
            
            // 최대 5개만 표시
            const limitedData = data.slice(0, 5);
            
            container.innerHTML = limitedData.map(item => {
                const timeAgo = getTimeAgo(new Date(item.search_date));
                
                // 정보창에서 계산한 값이 있으면 우선 사용, 없으면 검색 기록의 risk_score 사용
                // localStorage에서도 확인 (새로고침 후 복원된 데이터)
                const regionData = window.regionData && window.regionData[item.region];
                let displayScore = (regionData && regionData.calculatedScore !== undefined)
                    ? regionData.calculatedScore
                    : item.risk_score;
                
                // localStorage에서도 확인 (regionData에 없을 경우)
                if (!displayScore || displayScore === 0) {
                    try {
                        const storedRates = JSON.parse(localStorage.getItem('regionJeonseRates') || '{}');
                        if (storedRates[item.region]) {
                            displayScore = storedRates[item.region].score;
                        }
                    } catch (e) {
                        // localStorage 읽기 실패 시 무시
                    }
                }
                
                // 공통 위험도 계산 함수 사용
                const riskLevel = calculateRiskLevel(displayScore);
                const badgeClass = riskLevel.category;
                const badgeText = riskLevel.text;
                
                return `
                    <div class="recent-search-item">
                        <div class="search-info" onclick="searchFromHistory('${item.region}')" style="flex: 1; cursor: pointer;">
                            <div class="search-region">${item.region}</div>
                            <div class="search-time">${timeAgo}</div>
                        </div>
                        <div style="display: flex; align-items: center; gap: 8px;">
                        <span class="search-badge ${badgeClass}">${badgeText}</span>
                            <button class="remove-btn" onclick="event.stopPropagation(); deleteSearchHistory(${item.id})" title="삭제" style="background: none; border: none; color: #dc3545; cursor: pointer; font-size: 18px; padding: 4px 8px; line-height: 1;">×</button>
                        </div>
                    </div>
                `;
            }).join('');
        })
        .catch(error => {
            console.error('검색 기록 로드 실패:', error);
            const container = document.getElementById('recent-searches');
            if (container) {
                container.innerHTML = '<div style="color: #999; font-size: 13px; text-align: center; padding: 20px;">검색 기록을 불러올 수 없습니다.</div>';
            }
        });
}

// 검색 히스토리 삭제 (확인 팝업 없이 바로 삭제)
function deleteSearchHistory(historyId) {
    fetch(`/api/search-history/${historyId}`, {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            loadRecentSearches(); // 목록 새로고침
        } else {
            alert('삭제에 실패했습니다.');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('삭제 중 오류가 발생했습니다.');
        });
}

// 상대 시간 표시 (예: "5분 전", "1시간 전", "2일 전")
function getTimeAgo(date) {
    const now = new Date();
    const diff = now - date;
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
    
    if (days > 0) {
        return `${days}일 전`;
    } else if (hours > 0) {
        return `${hours}시간 전`;
    } else if (minutes > 0) {
        return `${minutes}분 전`;
    } else {
        return '방금 전';
    }
}

function searchFromHistory(regionName) {
    // 지역명 정규화하여 검색
    const normalizedRegion = normalizeRegionName(regionName);
    const searchInput = document.getElementById('address-search');
    if (searchInput) {
        searchInput.value = normalizedRegion;
        searchAddress();
    }
}

