// 초기화 영역: 변수 선언 및 전역 설정
let map;
const regionData = {};
// HTML에서 정의한 전역 설정 사용
const scannerBaseUrl = typeof SAFEHOME_CONFIG !== 'undefined' ? SAFEHOME_CONFIG.scannerUrl : '/searchscan';
let currentFilter = 'all';
let regions = [];

// [초기화] 페이지 로드 시 실행
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
            // 실거래 원 제거
            clearRealTransactionCircles();
            // 지도 초기화
            map.setCenter(new kakao.maps.LatLng(37.566826, 126.9786567));
            map.setLevel(9);
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
    const mapContainer = document.getElementById('map');
    const mapOption = {
        center: new kakao.maps.LatLng(37.566826, 126.9786567), // 서울 시청
        level: 9
    };
    map = new kakao.maps.Map(mapContainer, mapOption);

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
                
                const infowindow = new kakao.maps.InfoWindow({ content: content, removable: true });

                regionData[region.region] = {
                    circle: circle,
                    infowindow: infowindow,
                    category: region.score >= 80 ? 'danger' : region.score >= 60 ? 'warning' : 'safe',
                    data: region
                };
                
                // 원 클릭 시 정보창 표시 및 실거래 데이터 로드
                kakao.maps.event.addListener(circle, 'click', function() {
                    // 이전 실거래 원 제거 (중복 방지)
                    clearRealTransactionCircles();
                    
                        // 기존 정보창 모두 닫기
                    Object.values(regionData).forEach(data => data.infowindow.close());
                        if (window.realTxInfoWindow) {
                            window.realTxInfoWindow.close();
                            window.realTxInfoWindow = null;
                        }
                        
                    const position = circle.getPosition();
                        // 히트맵 정보창만 열기
                    infowindow.setPosition(position);
                    infowindow.open(map);
                    
                        // 정보창이 열린 후 즐겨찾기 버튼 업데이트
                        setTimeout(() => {
                            const favoriteId = `favorite-${region.region.replace(/\s/g, '-')}`;
                            const btn = document.getElementById(favoriteId);
                            if (btn) {
                                const isFavorite = favoriteRegions.has(region.region);
                                btn.textContent = isFavorite ? '⭐' : '☆';
                                btn.style.color = isFavorite ? '#ffc107' : '#ccc';
                                btn.title = isFavorite ? '즐겨찾기 해제' : '즐겨찾기 추가';
                            }
                        }, 100);
                        
                        // 실거래 데이터도 함께 로드 (정보창은 자동으로 열지 않음)
                        loadRealTransactionsForMap(region.region, position, false);
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
    document.getElementById('address-search').value = region;
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

// 2. 주소 검색 함수
function searchAddress() {
    const searchKeyword = document.getElementById('address-search').value.trim();
    if (!searchKeyword) {
        alert("지역명을 입력해주세요.");
        return;
    }
    
    // 기존 실거래 원 제거
    clearRealTransactionCircles();
    
    // 지역 데이터에서 먼저 찾기
    let targetRegion = regionData[searchKeyword];
    if (!targetRegion) {
        const matchedKey = Object.keys(regionData).find(key => {
            const keyLower = key.toLowerCase();
            const searchLower = searchKeyword.toLowerCase();
            return keyLower.includes(searchLower) || searchLower.includes(keyLower) || 
                   key.replace('동', '') === searchKeyword.replace('동', '');
        });
        if (matchedKey) targetRegion = regionData[matchedKey];
    }
    
    if (targetRegion) {
        // 히트맵에 있는 지역은 이미 데이터가 있다고 가정하고 지도를 먼저 이동
        // 모든 정보창 닫기
        Object.values(regionData).forEach(d => d.infowindow.close());
        if (window.realTxInfoWindow) {
            window.realTxInfoWindow.close();
            window.realTxInfoWindow = null;
        }
        
        // 해당 지역으로 이동 및 확대
        const position = targetRegion.circle.getPosition();
        map.setCenter(position);
        map.setLevel(4); // 더 확대해서 원이 잘 보이도록
        
        // 정보창 열기
        targetRegion.infowindow.setPosition(position);
        targetRegion.infowindow.open(map);
        
        // 실거래 데이터 가져오기 (정보창은 자동으로 열지 않음)
        // 백그라운드에서 데이터 확인 (데이터가 없으면 나중에 알림)
        loadRealTransactionsForMap(targetRegion.data.region, position, false, false);
        
        return;
    }
    
    // 검색어가 동 이름인지 확인 (동, 가, 리로 끝나거나 포함되어 있어야 함)
    const isDongName = /동$|가$|리$|동\s|가\s|리\s/.test(searchKeyword) || 
                       /[가-힣]+동|[가-힣]+가|[가-힣]+리/.test(searchKeyword);
    
    // 동 이름이 아니면 바로 팝업 표시
    if (!isDongName) {
        alert(`'${searchKeyword}' 지역의 검색 결과가 없습니다.\n\n정확한 동 이름을 입력해주세요.`);
        return;
    }
    
    // 카카오 주소 검색 API 사용
    const geocoder = new kakao.maps.services.Geocoder();
    // 이미 '서울'이 포함되어 있으면 추가하지 않음
    const searchQuery = searchKeyword.includes('서울') ? searchKeyword : searchKeyword + ' 서울';
    geocoder.addressSearch(searchQuery, function(result, status) {
        if (status === kakao.maps.services.Status.OK) {
            const coords = new kakao.maps.LatLng(result[0].y, result[0].x);
            
            // 지도를 먼저 이동 (사용자 경험 개선)
            map.setCenter(coords);
            map.setLevel(6); // 상세 레벨로 확대
            
            // 백그라운드에서 데이터 확인
            fetch(`/analyze?region=${encodeURIComponent(searchKeyword)}`)
                .then(res => res.ok ? res.json() : { properties: [] })
                .then(data => {
                    const properties = data.properties || [];
                    if (properties.length === 0) {
                        // 데이터가 없으면 검색 결과가 없다는 팝업 표시
                        alert(`'${searchKeyword}' 지역의 검색 결과가 없습니다.\n\n정확한 동 이름을 입력해주세요.`);
                        return;
                    }
                    
                    // 검색 결과의 주소가 검색어와 매칭되는지 확인 (첫 번째 매물만 빠르게 확인)
                    const searchKeywordClean = searchKeyword.replace(/동|가|리/g, '').trim();
                    const firstProp = properties[0];
                    if (firstProp && firstProp.address) {
                        const address = firstProp.address.replace(/동|가|리/g, '');
                        if (!address.includes(searchKeywordClean) && !searchKeywordClean.includes(address)) {
                            // 첫 번째 매물이 매칭되지 않으면 전체 확인 (하지만 이미 지도는 이동했음)
                            const hasMatchingAddress = properties.some(prop => {
                                const addr = (prop.address || '').replace(/동|가|리/g, '');
                                return addr.includes(searchKeywordClean) || searchKeywordClean.includes(addr);
                            });
                            if (!hasMatchingAddress) {
                                alert(`'${searchKeyword}' 지역의 검색 결과가 없습니다.\n\n정확한 동 이름(예: 청담동, 역삼동)을 입력해주세요.`);
                                return;
                            }
                        }
                    }
                    
                    // 데이터가 있으면 표시
            loadRealTransactionsForMap(searchKeyword, coords);
                })
                .catch(() => {
                    alert('매물 데이터를 확인하는 중 오류가 발생했습니다.');
                });
        } else {
            // 주소 검색 실패 시에도 검색 결과가 없다는 팝업
            alert(`'${searchKeyword}' 지역의 검색 결과가 없습니다.\n\n정확한 동 이름(예: 청담동, 역삼동)을 입력해주세요.`);
        }
    });
}

// 3. 실제 데이터(매물 분석 결과) 가져오기
function loadRealTransactionsForMap(region, coords, autoOpenInfoWindow = true, showAlert = false) {
    // /analyze API 호출 (전세가율 포함)
    fetch(`/analyze?region=${encodeURIComponent(region)}`)
        .then(res => res.ok ? res.json() : { properties: [] })
        .then(data => {
            const properties = data.properties || [];
            if (properties.length > 0) {
                // 데이터가 있으면 분석하여 원 그리기 (정보창 자동 열기 여부 전달)
                displayRealTransactionCircles(region, properties, coords, autoOpenInfoWindow);
                updateRealTransactionResults(region, properties);
                
                // 검색 기록 저장 (위험도 점수 계산)
                const riskScore = calculateRiskScoreFromProperties(properties);
                saveSearchHistory(region, riskScore);
            } else {
                // 데이터가 없으면 아무것도 표시하지 않음 (검색 기록도 저장하지 않음)
                if (showAlert) {
                    alert(`'${region}' 지역의 검색 결과가 없습니다.\n\n정확한 동 이름(예: 청담동, 역삼동)을 입력해주세요.`);
                }
            }
        })
        .catch(() => {
            console.error('실거래 데이터를 불러오는데 실패했습니다.');
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
    // 기존 실거래 원 제거
    if (window.realTxCircles) {
        window.realTxCircles.forEach(circle => circle.setMap(null));
    }
    window.realTxCircles = [];
    
    // 히트맵 원은 제거하지 않음 (검색 후에도 히트맵 원이 보이도록)
    // if (regionData[region] && regionData[region].circle) {
    //     regionData[region].circle.setMap(null);
    // }
    
    // (1) 전세가율 기반 위험도 계산
    // 전세가율이 있는 매물만 필터링
    const propertiesWithJeonseRate = properties.filter(p => p.jeonse_rate != null && p.jeonse_rate > 0);
    
    if (propertiesWithJeonseRate.length === 0) {
        return; // 전세가율 데이터가 없으면 표시하지 않음
    }
    
    // 평균 전세가율 계산
    const avgJeonseRate = propertiesWithJeonseRate.reduce((sum, p) => sum + p.jeonse_rate, 0) / propertiesWithJeonseRate.length;
    
    // (2) 전세가율에 따른 색상 결정
    let color = '#28a745'; // 안전 (초록)
    let statusText = '안전';
    
    if (avgJeonseRate >= 80) {
        color = '#dc3545'; // 위험 (빨강)
        statusText = '위험 (전세가율 높음)';
    } else if (avgJeonseRate >= 60) {
        color = '#ffc107'; // 주의 (노랑)
        statusText = '주의 (전세가율 보통)';
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
    circle.setMap(map);
    
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
    
    // 원 클릭 시 정보창 열기
    kakao.maps.event.addListener(circle, 'click', function() {
        // 기존 정보창 모두 닫기
        Object.values(regionData).forEach(d => d.infowindow.close());
        if (window.realTxInfoWindow) {
            window.realTxInfoWindow.close();
        }
        infowindow.setPosition(centerCoords);
        infowindow.open(map);
        window.realTxInfoWindow = infowindow;
        
        // 정보창이 열린 후 즐겨찾기 버튼 업데이트
        setTimeout(() => {
            const favoriteId = `favorite-tx-${region.replace(/\s/g, '-')}`;
            const btn = document.getElementById(favoriteId);
            if (btn) {
                const isFavorite = favoriteRegions.has(region);
                btn.textContent = isFavorite ? '⭐' : '☆';
                btn.style.color = isFavorite ? '#ffc107' : '#ccc';
                btn.title = isFavorite ? '즐겨찾기 해제' : '즐겨찾기 추가';
            }
        }, 100);
    });
    
    // 검색 후 바로 정보창 띄우기 (autoOpenInfoWindow가 true일 때만)
    if (autoOpenInfoWindow) {
    infowindow.open(map);
    window.realTxInfoWindow = infowindow;
        
        // 정보창이 열린 후 즐겨찾기 버튼 업데이트
        setTimeout(() => {
            const favoriteId = `favorite-tx-${region.replace(/\s/g, '-')}`;
            const btn = document.getElementById(favoriteId);
            if (btn) {
                const isFavorite = favoriteRegions.has(region);
                btn.textContent = isFavorite ? '⭐' : '☆';
                btn.style.color = isFavorite ? '#ffc107' : '#ccc';
                btn.title = isFavorite ? '즐겨찾기 해제' : '즐겨찾기 추가';
            }
        }, 100);
    }
    
    // 실거래 원 정보 저장
    if (!window.realTxCircleData) {
        window.realTxCircleData = {};
    }
    window.realTxCircleData[region] = {
        circle: circle,
        infowindow: infowindow,
        originalCircle: regionData[region] ? regionData[region].circle : null
    };
}

// 실거래 원 제거 및 기존 원 복원
function clearRealTransactionCircles() {
    // 실거래 원 제거
    if (window.realTxCircles) {
        window.realTxCircles.forEach(circle => circle.setMap(null));
        window.realTxCircles = [];
    }
    
    // 숨긴 기존 원 복원
    if (window.hiddenCircles) {
        Object.keys(window.hiddenCircles).forEach(region => {
            const originalCircle = window.hiddenCircles[region];
            if (originalCircle && regionData[region]) {
                originalCircle.setMap(map);
            }
        });
        window.hiddenCircles = {};
    }
    
    // 정보창 닫기
    if (window.realTxInfoWindow) {
        window.realTxInfoWindow.close();
        window.realTxInfoWindow = null;
    }
}

// ============================================
// UI 업데이트 함수
// ============================================

// 지도의 원 필터링
function filterMapCircles() {
    Object.values(regionData).forEach(data => {
        if (currentFilter === 'all' || data.category === currentFilter) {
            data.circle.setMap(map);
        } else {
            data.circle.setMap(null);
            data.infowindow.close();
        }
    });
}

// 지역 목록 업데이트
function updateRegionList() {
    const listContainer = document.getElementById('region-list');
    if (!listContainer) return;
    
    listContainer.innerHTML = '';
    
    const filtered = currentFilter === 'all' 
        ? regions 
        : regions.filter(r => r.category === currentFilter);
    
    filtered.sort((a, b) => b.score - a.score);
    
    filtered.forEach(region => {
        const item = document.createElement('div');
        item.className = `region-item ${region.category}`;
        
        // 상태 텍스트 및 색상
        let statusText = '안전';
        let statusColor = '#28a745';
        if (region.score >= 80) {
            statusText = '위험';
            statusColor = '#dc3545';
        } else if (region.score >= 60) {
            statusText = '주의';
            statusColor = '#ffc107';
        }
        
        item.innerHTML = `
            <div class="region-header">
            <div class="region-name">${region.region}</div>
                <div class="region-status" style="color: ${statusColor}; font-weight: 600; font-size: 12px;">${statusText}</div>
            </div>
            <div class="region-details">
                <div class="region-score">
                    <span class="score-label">전세가율:</span>
                    <span class="score-value" style="color: ${statusColor}; font-weight: 600;">${typeof region.score === 'number' ? region.score.toFixed(1) : region.score}%</span>
                </div>
                <div class="region-info">
                    <span class="info-text">${region.score >= 80 ? '전세가율이 높아 위험합니다' : region.score >= 60 ? '전세가율이 보통입니다' : '전세가율이 낮아 안전합니다'}</span>
                </div>
            </div>
        `;
        item.onclick = () => {
            const targetRegion = regionData[region.region];
            if (targetRegion) {
                // 모든 정보창 닫기
                Object.values(regionData).forEach(d => d.infowindow.close());
                
                // 해당 지역으로 이동
                const position = targetRegion.circle.getPosition();
                map.setCenter(position);
                map.setLevel(5);
                
                // 정보창 열기
                targetRegion.infowindow.setPosition(position);
                targetRegion.infowindow.open(map);
                
                // 실거래 데이터도 함께 로드 (정보창은 자동으로 열지 않음)
                loadRealTransactionsForMap(region.region, position, false);
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
    const danger = regions.filter(r => r.score >= 80).length;
    const warning = regions.filter(r => r.score >= 60 && r.score < 80).length;
    const safe = regions.filter(r => r.score < 60).length;
    
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
            
            container.innerHTML = data.map(item => {
                const timeAgo = getTimeAgo(new Date(item.search_date));
                const riskScore = item.risk_score;
                let badgeClass = 'safe';
                let badgeText = '안전';
                
                if (riskScore !== null && riskScore !== undefined) {
                    if (riskScore >= 80) {
                        badgeClass = 'danger';
                        badgeText = '위험';
                    } else if (riskScore >= 60) {
                        badgeClass = 'warning';
                        badgeText = '주의';
                    }
                }
                
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

// 검색 히스토리 삭제
function deleteSearchHistory(historyId) {
    if (!confirm('이 검색 기록을 삭제하시겠습니까?')) {
        return;
    }
    
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
    document.getElementById('address-search').value = regionName;
    searchAddress();
}

// 실거래가 조회 함수
function loadRealTransactions() {
    const region = document.getElementById('real-tx-region').value.trim();
    const resultsDiv = document.getElementById('real-tx-results');
    
    if (!region) {
        resultsDiv.innerHTML = '<div style="color: #dc3545; font-size: 13px; padding: 10px;">지역명을 입력하세요</div>';
        return;
    }
    
    // 검색어 유효성 검사 (한글 동 이름 패턴)
    const validPattern = /^[가-힣]+(동|가|리|구|시)$/;
    if (!validPattern.test(region)) {
        resultsDiv.innerHTML = '<div style="color: #dc3545; font-size: 13px; padding: 10px;">올바른 지역명을 입력하세요 (예: 청담동, 강남구)</div>';
        return;
    }
    
    resultsDiv.innerHTML = '<div style="color: #999; font-size: 13px; padding: 20px; text-align: center;">로딩 중...</div>';
    
    // 최근 3개월 데이터 조회
    const now = new Date();
    const months = [];
    for (let i = 0; i < 3; i++) {
        const date = new Date(now.getFullYear(), now.getMonth() - i, 1);
        months.push(date.getFullYear() + String(date.getMonth() + 1).padStart(2, '0'));
    }
    
    // 모든 월 데이터 가져오기
    Promise.all(months.map(month => 
        fetch(`/api/real-transactions?region=${encodeURIComponent(region)}&deal_ymd=${month}&numOfRows=100`)
            .then(res => {
                if (!res.ok) {
                    return { transactions: [], error: `HTTP ${res.status}` };
                }
                return res.json();
            })
            .catch(() => ({ transactions: [] }))
    )).then(results => {
        // 모든 거래 합치기
        const allTransactions = [];
        results.forEach(data => {
            if (data.transactions && Array.isArray(data.transactions)) {
                allTransactions.push(...data.transactions);
            }
        });
        
        // 실제 데이터가 있을 때만 표시
        if (allTransactions.length === 0) {
            resultsDiv.innerHTML = '<div style="color: #999; font-size: 13px; padding: 10px; text-align: center;">해당 지역의 거래 내역이 없습니다</div>';
            return;
        }
        
        const html = allTransactions.slice(0, 10).map(tx => `
            <div style="padding: 10px; border-bottom: 1px solid #eee; font-size: 13px;">
                <div style="font-weight: 600; margin-bottom: 4px;">${tx.아파트 || '정보없음'}</div>
                <div style="color: #666; margin-bottom: 2px;">${tx.법정동 || ''} ${tx.지번 || ''}</div>
                <div style="color: #1565c0; font-weight: 600; margin-bottom: 2px;">
                    ${tx.거래금액 ? (tx.거래금액 / 10000).toFixed(0) + '억' : tx.거래금액원문}
                </div>
                <div style="color: #999; font-size: 12px;">
                    ${tx.전용면적 ? tx.전용면적 + '㎡' : ''} · 
                    ${tx.층 ? tx.층 + '층' : ''} · 
                    ${tx.건축년도 || ''}년 · 
                    ${tx.거래일자 || ''}
                </div>
            </div>
        `).join('');
        
        resultsDiv.innerHTML = html;
    })
        .catch(() => {
            resultsDiv.innerHTML = '<div style="color: #dc3545; font-size: 13px; padding: 10px;">네트워크 오류</div>';
        });
}
