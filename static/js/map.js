// 초기화 영역: 변수 선언 및 전역 설정
let map;
let regionData = {};
// HTML에서 정의한 전역 설정 사용
const scannerBaseUrl = typeof SAFEHOME_CONFIG !== 'undefined' ? SAFEHOME_CONFIG.scannerUrl : '/searchscan';
let currentFilter = 'all';
let regions = [];
let regionPopup;
let mapSearch;

const unknownMapIndicator = { category: 'unknown', text: '판단 불가', color: '#6b7280' };
const mapUnavailableReasons = {
    uncollected: '아직 정상 수집된 자료가 없습니다.',
    unmapped: '이 위치와 연결할 법정동이 확인되지 않았습니다.',
    stale: '현재 계약 기간에 맞는 최신 자료가 없습니다.'
};
const mapUpdateFormat = new Intl.DateTimeFormat('ko-KR', {
    dateStyle: 'medium', timeStyle: 'short', hourCycle: 'h23', timeZone: 'Asia/Seoul'
});

function getMapIndicator(region) {
    const score = region.score;
    if (region.status !== 'available' || !Number.isFinite(score) || score <= 0 ||
        !Number.isInteger(region.sale_sample_count) ||
        region.sale_sample_count < (region.minimum_sale_sample_count ?? 5) ||
        !region.period?.from || !region.period?.to || !region.last_updated) {
        return unknownMapIndicator;
    }
    if (score >= 80) return { category: 'danger', text: '높음', color: '#dc3545' };
    if (score >= 60) return { category: 'warning', text: '중간', color: '#a16207' };
    return { category: 'safe', text: '낮음', color: '#166534' };
}

window.regionData = regionData;
window.regions = regions;

document.addEventListener('DOMContentLoaded', function() {
    initMap();
    setupEventListeners();

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
            resetMapSearch();
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

    if (typeof window.toggleRightSidebar === 'function') {
        window.toggleRightSidebar = () => {
            setRightSidebarOpen(!document.getElementById('right-sidebar').classList.contains('active'));
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
    if (!window.kakao?.maps) {
        document.querySelector('.map-title').textContent = '지도를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.';
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

    // 기본 지도 위치와 검증 상태를 읽습니다.
    fetch('/heatmap', { cache: 'no-store' })
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
                        
            regions = validData.map(region => ({ ...region, indicator: getMapIndicator(region) }));
            window.regions = regions;

            for (const region of regions) {
                const position = new kakao.maps.LatLng(region.lat, region.lng);
                const circle = new kakao.maps.Circle({
                    center: position,
                    radius: 400,
                    fillColor: region.indicator.color,
                    fillOpacity: 0.4,
                    strokeWeight: 0
                });
                regionData[region.region] = { circle, category: region.indicator.category, data: region };
                kakao.maps.event.addListener(circle, 'click', () => selectMapRegion(region.region, position));
            }
            filterMapCircles();
            updateStats();
            updateRegionList();
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

function selectMapRegion(region, position) {
    resetMapSearch();
    setRightSidebarOpen(false);
    if (window.matchMedia('(max-width: 960px)').matches) {
        const panel = document.getElementById('side-panel');
        panel.classList.remove('active');
        panel.classList.add('hidden');
    }
    map.setCenter(position);
    map.setLevel(5);
    document.getElementById('address-search').value = region;

    const data = regionData[region].data;
    const content = document.getElementById('map-indicator-template').content.firstElementChild.cloneNode(true);
    const field = name => content.querySelector(`[data-field="${name}"]`);
    const minimum = data.minimum_sale_sample_count ?? 5;
    const hasSamples = Number.isInteger(data.sale_sample_count);
    content.dataset.category = data.indicator.category;
    field('region').textContent = region;
    field('ratio').textContent = data.indicator.category === 'unknown' ? '—' : `${data.score.toFixed(1)}%`;
    field('status').textContent = data.indicator.text;
    field('samples').hidden = !hasSamples;
    field('total').textContent = Number.isInteger(data.sale_transaction_count)
        ? `${data.sale_transaction_count.toLocaleString('ko-KR')}건` : '—';
    field('matched').textContent = hasSamples
        ? `${data.sale_sample_count.toLocaleString('ko-KR')}건 / 최소 ${minimum}건` : '—';
    field('note').textContent = data.reason === 'insufficient'
        ? '매매마다 같은 단지에서 면적과 계약일이 비슷한 순수 전세가 3건 이상 필요합니다.'
        : mapUnavailableReasons[data.reason] || '비교 가능한 매매를 기준으로 계산한 참고 지표입니다.';
    field('period').textContent = data.period
        ? `${data.period.from.replaceAll('-', '.')} – ${data.period.to.replaceAll('-', '.')}` : '—';
    const updated = Date.parse(data.last_updated);
    field('updated').textContent = Number.isFinite(updated) ? `${mapUpdateFormat.format(updated)} KST` : '—';
    const close = content.querySelector('.map-popup-close');
    close.onclick = () => {
        closeRegionPopup();
        document.querySelector('.sidebar-toggle-btn.left-toggle')?.focus({ preventScroll: true });
    };
    content.addEventListener('keydown', event => {
        if (event.key === 'Escape') close.click();
    });
    content.querySelector('.map-popup-search').href = propertyResultsUrl(region);
    regionPopup = new kakao.maps.CustomOverlay({ map, position, content, clickable: true, yAnchor: 1, zIndex: 10 });
    map.panBy(0, -126);
    close.focus({ preventScroll: true });
}

function closeRegionPopup() {
    regionPopup?.setMap(null);
    regionPopup = null;
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
    const resultButton = document.getElementById('map-results-favorite');
    const selected = favoriteRegions.has(resultButton.dataset.region);
    resultButton.textContent = selected ? '⭐' : '☆';
    resultButton.title = selected ? '즐겨찾기 해제' : '즐겨찾기 추가';
    resultButton.setAttribute('aria-label', resultButton.title);
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
    
    // 초기화된 지도와 위치 목록을 사용합니다.
    const globalRegionData = window.regionData || regionData;
    const globalMap = window.map || map;
    
    // 지도 인스턴스가 없으면 에러
    if (!globalMap) {
        console.error('지도 인스턴스가 없습니다.');
        alert('지도가 아직 로드되지 않았습니다. 잠시 후 다시 시도해주세요.');
        return;
    }
    
    resetMapSearch();

    // 지역명 정규화 (검색어와 정규화된 버전 모두 시도)
    const normalizedKeyword = normalizeRegionName(searchKeyword);
    
    // 지역 데이터에서 먼저 찾기 (정확한 매칭 우선)
    let targetRegion = globalRegionData[searchKeyword] || globalRegionData[normalizedKeyword];
    
    // 정확한 매칭이 없으면 부분 매칭 시도
    if (!targetRegion) {
        const matchedKeys = Object.keys(globalRegionData).filter(key => {
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
        
        if (matchedKeys.length > 1) {
            alert('지역을 구분할 수 있도록 자치구와 동 이름을 함께 입력해 주세요.');
            return;
        }
        if (matchedKeys.length === 1) {
            targetRegion = globalRegionData[matchedKeys[0]];
        }
    }
    
    const controller = new AbortController();
    mapSearch = controller;
    if (targetRegion) {
        globalMap.setCenter(targetRegion.circle.getPosition());
        globalMap.setLevel(5);
        loadMapProperties(targetRegion.data.region, controller.signal);
    } else {
        const geocoder = new kakao.maps.services.Geocoder();
        geocoder.addressSearch(searchKeyword, (result, status) => {
            if (controller.signal.aborted) return;
            if (status === kakao.maps.services.Status.OK) {
                globalMap.setCenter(new kakao.maps.LatLng(result[0].y, result[0].x));
                globalMap.setLevel(5);
                loadMapProperties(normalizedKeyword, controller.signal);
            } else {
                alert(`'${searchKeyword}' 지역을 찾을 수 없습니다. 정확한 동 이름을 입력해 주세요.`);
            }
        });
    }
}

function propertyResultsUrl(region) {
    return `${scannerBaseUrl}?region=${encodeURIComponent(region)}#search-result`;
}

function setRightSidebarOpen(open) {
    const sidebar = document.getElementById('right-sidebar');
    sidebar.classList.toggle('active', open);
    sidebar.classList.toggle('hidden', !open);
    sidebar.style.visibility = open ? 'visible' : 'hidden';
}

function resetMapSearch() {
    mapSearch?.abort();
    mapSearch = null;
    closeRegionPopup();
    document.getElementById('map-results-title').textContent = '실거래가 조회';
    document.getElementById('real-tx-results').textContent = '지역을 검색하면 매물이 표시됩니다.';
    document.getElementById('map-results-favorite').hidden = true;
    document.getElementById('map-results-all').hidden = true;
}

async function loadMapProperties(region, signal) {
    const results = document.getElementById('real-tx-results');
    const favorite = document.getElementById('map-results-favorite');
    const all = document.getElementById('map-results-all');
    document.getElementById('map-results-title').textContent = `${region} 매물`;
    results.textContent = '매물을 불러오는 중입니다.';
    setRightSidebarOpen(true);
    if (window.matchMedia('(max-width: 960px)').matches) {
        const panel = document.getElementById('side-panel');
        panel.classList.remove('active');
        panel.classList.add('hidden');
    }
    document.getElementById('right-sidebar').scrollTop = 0;

    try {
        const response = await fetch(`/analyze?region=${encodeURIComponent(region)}`, { signal });
        if (!response.ok) throw new Error(`매물 조회 실패 (${response.status})`);
        const { properties } = await response.json();
        if (signal.aborted) return;
        if (!Array.isArray(properties)) throw new Error('매물 응답 형식 오류');
        if (!properties.length) {
            results.textContent = '조회된 매물이 없습니다.';
            return;
        }
        updateRealTransactionResults(properties);
        favorite.dataset.region = region;
        favorite.onclick = () => toggleFavorite(region, favorite.id);
        favorite.hidden = false;
        updateFavoriteButtons();
        all.href = propertyResultsUrl(region);
        all.hidden = false;
        saveSearchHistory(region);
    } catch (error) {
        if (signal.aborted) return;
        results.textContent = '매물을 불러오지 못했습니다. 다시 검색해 주세요.';
        console.error(error);
    }
}

// 검색 기록은 위치만 저장합니다.
function saveSearchHistory(region) {
    if (!region) return;
    
    fetch('/api/search-history', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ region })
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

function filterMapCircles() {
    for (const { circle, category } of Object.values(regionData)) {
        circle.setMap(currentFilter === 'all' || category === currentFilter ? map : null);
    }
}

function updateRegionList() {
    const list = document.getElementById('region-list');
    if (!list) return;
    list.replaceChildren();
    const filtered = regions.filter(region => currentFilter === 'all' || region.indicator.category === currentFilter);

    for (const region of filtered) {
        const item = document.createElement('button');
        item.type = 'button';
        item.className = 'region-item ' + region.indicator.category;

        const name = document.createElement('span');
        name.className = 'region-name';
        name.textContent = region.region;
        const label = document.createElement('span');
        label.className = 'region-status';
        label.style.color = region.indicator.color;
        label.textContent = region.indicator.category === 'unknown'
            ? region.indicator.text : region.score.toFixed(1) + '% · ' + region.indicator.text;
        item.append(name, label);
        item.onclick = () => selectMapRegion(region.region, regionData[region.region].circle.getPosition());
        list.append(item);
    }

    if (!filtered.length) list.textContent = '이 분류에 해당하는 지역이 없습니다.';
}

function updateStats() {
    const counts = { danger: 0, warning: 0, safe: 0, unknown: 0 };
    for (const region of regions) counts[region.indicator.category]++;
    for (const [category, count] of Object.entries(counts)) {
        const element = document.getElementById(category + '-count');
        if (element) element.textContent = count;
    }
    const total = document.getElementById('total-regions');
    if (total) total.textContent = regions.length;
}

// 사이드바 실거래 결과 업데이트
function updateRealTransactionResults(properties) {
    const resultsDiv = document.getElementById('real-tx-results');
    if (!resultsDiv) return;
    
    if (properties.length === 0) {
        resultsDiv.innerHTML = '<div style="color: #999; font-size: 13px; padding: 10px;">매물 데이터가 없습니다</div>';
        return;
    }
    
    const html = properties.slice(0, 10).map(prop => {
        const jeonseRateText = prop.jeonse_rate == null ? '판단 불가' : `${prop.jeonse_rate}%`;
        const jeonseRateColor = prop.jeonse_rate == null ? '#6b7280' :
            prop.jeonse_rate >= 80 ? '#dc3545' : prop.jeonse_rate >= 60 ? '#a16207' : '#166534';
        return `
        <div style="padding: 10px; border-bottom: 1px solid #eee; font-size: 13px;">
            <div style="font-weight: 600; margin-bottom: 4px;">${prop.name || '정보없음'}</div>
            <div style="color: #666; margin-bottom: 2px;">${prop.address || ''}</div>
            <div style="color: #1565c0; font-weight: 600; margin-bottom: 2px;">
                매매가: ${prop.price || '정보 없음'}
            </div>
            ${prop.jeonse_price_raw != null ? `
            <div style="color: #666; margin-bottom: 2px;">
                전세 보증금 중앙값: ${prop.jeonse_price}
            </div>
            ` : ''}
            <div style="margin-top: 4px;">
                참고 전세가율: <span style="color: ${jeonseRateColor}; font-weight: 600;">${jeonseRateText}</span>
            </div>
        </div>
    `;
    }).join('');
    
    resultsDiv.innerHTML = html;
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
                
                return `
                    <div class="recent-search-item">
                        <div class="search-info" onclick="searchFromHistory('${item.region}')" style="flex: 1; cursor: pointer;">
                            <div class="search-region">${item.region}</div>
                            <div class="search-time">${timeAgo}</div>
                        </div>
                        <div style="display: flex; align-items: center; gap: 8px;">
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

