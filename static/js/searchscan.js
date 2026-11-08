// 검색 관련 변수
let currentRegion = '';
let comparisonProperties = [];
let isAdvancedSearch = false;
let favoriteRegions = new Set();

// 즐겨찾기 로드
function loadFavorites() {
    fetch('/api/favorites')
        .then(res => res.ok ? res.json() : [])
        .then(data => {
            favoriteRegions = new Set(data.map(f => f.region));
            updateFavoriteButtons();
        })
        .catch(err => console.error('즐겨찾기 로드 실패:', err));
}

function updateFavoriteButtons() {
    favoriteRegions.forEach(region => {
        document.querySelectorAll(`[onclick*="toggleFavoriteRegion('${region}'"]`).forEach(btn => {
            btn.textContent = '⭐';
            btn.style.color = '#ffc107';
            btn.title = '즐겨찾기 해제';
        });
    });
}

function toggleFavoriteRegion(region, buttonId) {
    const isFavorite = favoriteRegions.has(region);
    const btn = document.getElementById(buttonId);
    
    if (isFavorite) {
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
                if (btn) {
                    btn.textContent = '☆';
                    btn.style.color = '#ccc';
                    btn.title = '즐겨찾기 추가';
                }
            }
        })
        .catch(err => {
            console.error('즐겨찾기 제거 실패:', err);
        });
    } else {
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
                if (btn) {
                    btn.textContent = '⭐';
                    btn.style.color = '#ffc107';
                    btn.title = '즐겨찾기 해제';
                }
            }
        })
        .catch(err => {
            console.error('즐겨찾기 추가 실패:', err);
        });
    }
}

// 공통 함수: 동 이름 검증
function isValidDongName(region) {
    return /동$|가$|리$|동\s|가\s|리\s/.test(region) || 
           /[가-힣]+동|[가-힣]+가|[가-힣]+리/.test(region);
}

// 공통 함수: 주소 매칭 확인
function checkAddressMatch(region, properties) {
    const regionClean = region.replace(/동|가|리/g, '').trim();
    const firstProp = properties[0];
    if (firstProp?.address) {
        const address = firstProp.address.replace(/동|가|리/g, '');
        if (address.includes(regionClean) || regionClean.includes(address)) return true;
    }
    return properties.some(prop => {
        const address = (prop.address || '').replace(/동|가|리/g, '');
        return address.includes(regionClean) || regionClean.includes(address);
    });
}

// 공통 함수: 검색 결과 처리 (성능 최적화)
function handleSearchResult(region, props, resultDiv, isAdvanced = false) {
    if (props.length === 0) {
        resultDiv.innerHTML = '';
        const msg = isAdvanced 
            ? `'${region}' 지역의 검색 결과가 없습니다.\n\n검색 조건을 변경하거나 정확한 동 이름(예: 청담동, 역삼동)을 입력해주세요.`
            : `'${region}' 지역의 검색 결과가 없습니다.\n\n정확한 동 이름(예: 청담동, 역삼동)을 입력해주세요.`;
        alert(msg);
        return;
    }
    
    // 빠른 주소 매칭 (첫 번째 항목만 확인)
    const regionClean = region.replace(/동|가|리/g, '').trim();
    const firstProp = props[0];
    let addressMatch = false;
    
    if (firstProp?.address) {
        const address = firstProp.address.replace(/동|가|리/g, '');
        addressMatch = address.includes(regionClean) || regionClean.includes(address);
    }
    
    // 첫 번째 매칭 실패 시에만 전체 검색
    if (!addressMatch && props.length > 1) {
        addressMatch = checkAddressMatch(region, props);
    }
    
    if (!addressMatch) {
        resultDiv.innerHTML = '';
        const msg = isAdvanced 
            ? `'${region}' 지역의 검색 결과가 없습니다.\n\n검색 조건을 변경하거나 정확한 동 이름(예: 청담동, 역삼동)을 입력해주세요.`
            : `'${region}' 지역의 검색 결과가 없습니다.\n\n정확한 동 이름(예: 청담동, 역삼동)을 입력해주세요.`;
        alert(msg);
        return;
    }
    
    // 즉시 결과 렌더링 (사용자 경험 개선)
    renderResults(region, props, resultDiv);
    
    // 비동기 작업들은 백그라운드에서 처리 (블로킹 없음)
    // 검색 히스토리 저장 (비동기, 즉시 실행) - 전세가율 계산 후 저장
    saveSearchHistory(region, props);
    
    // 최근 검색어 드롭다운 업데이트
    if (typeof loadRecentSearches === 'function') {
        loadRecentSearches();
    }
    
    // 사이드바 최근 검색 업데이트는 _left_sidebar.html의 함수가 자동으로 처리
    
    // 실거래 데이터 로딩 (비동기, 약간의 지연 후 실행하여 메인 결과가 먼저 표시되도록)
    setTimeout(() => {
        loadRealTransactions(region);
    }, 100);
}

// 기본 검색
function searchRegion() {
    isAdvancedSearch = false;
    const region = document.getElementById('region-input').value.trim();
    const resultDiv = document.getElementById('search-result');
    
    if (!region) {
        resultDiv.innerHTML = '<p style="color:#d9534f">지역명을 입력하세요.</p>';
        return;
    }

    if (!isValidDongName(region)) {
        resultDiv.innerHTML = '';
        alert(`'${region}' 지역의 검색 결과가 없습니다.\n\n정확한 동 이름(예: 청담동, 역삼동)을 입력해주세요.`);
        return;
    }

    currentRegion = region;
    resultDiv.innerHTML = '<div class="loading"><span class="spinner"></span><span>분석 중입니다...</span></div>';

    fetch(`/analyze?region=${encodeURIComponent(region)}`)
        .then(res => {
            if (!res.ok) {
                // HTTP 에러 상태 코드 처리
                return res.json().then(errData => {
                    throw new Error(errData.error || `서버 오류 (${res.status})`);
                });
            }
            return res.json();
        })
        .then(data => {
            // 에러 응답 확인
            if (data.error) {
                resultDiv.innerHTML = '';
                alert(`오류: ${data.error}`);
                return;
            }
            // 정상 응답 처리
            const props = Array.isArray(data.properties) ? data.properties : (Array.isArray(data) ? data : []);
            handleSearchResult(region, props, resultDiv);
        })
        .catch(error => {
            console.error('검색 오류:', error);
            resultDiv.innerHTML = '';
            alert(`서버 오류가 발생했습니다: ${error.message || '알 수 없는 오류'}`);
        });
}

// 고급 검색
function advancedSearch() {
    const region = document.getElementById('region-input').value.trim();
    const minPrice = document.getElementById('min-price').value;
    const maxPrice = document.getElementById('max-price').value;
    const propertyType = document.getElementById('property-type').value;
    const riskLevel = document.getElementById('risk-level').value;
    
    if (!region) {
        alert('지역명을 입력하세요.');
        return;
    }
    
    if (!isValidDongName(region)) {
        document.getElementById('search-result').innerHTML = '';
        alert(`'${region}' 지역의 검색 결과가 없습니다.\n\n정확한 동 이름(예: 청담동, 역삼동)을 입력해주세요.`);
        return;
    }
    
    isAdvancedSearch = true;
    currentRegion = region;
    
    const params = new URLSearchParams({
        region, min_price: minPrice, max_price: maxPrice,
        property_type: propertyType, risk_level: riskLevel
    });
    
    const resultDiv = document.getElementById('search-result');
    resultDiv.innerHTML = '<div class="loading"><span class="spinner"></span><span>고급 검색 중입니다...</span></div>';
    
    fetch(`/api/advanced-search?${params}`)
        .then(res => {
            if (!res.ok) {
                return res.json().then(errData => {
                    throw new Error(errData.error || `서버 오류 (${res.status})`);
                });
            }
            return res.json();
        })
        .then(data => {
            if (data.error) {
                resultDiv.innerHTML = '';
                alert(`오류: ${data.error}`);
                return;
            }
            const props = Array.isArray(data.properties) ? data.properties : (Array.isArray(data) ? data : []);
            handleSearchResult(region, props, resultDiv, true);
        })
        .catch(error => {
            console.error('고급 검색 오류:', error);
            resultDiv.innerHTML = '';
            alert(`서버 오류가 발생했습니다: ${error.message || '알 수 없는 오류'}`);
        });
}

// 위험도 점수 계산
function calculateRiskScore(properties) {
    if (!properties?.length) return null;
    const totalWarnings = properties.reduce((sum, prop) => sum + (prop.warnings?.length || 0), 0);
    return Math.min(100, Math.round((totalWarnings / properties.length) * 20));
}

// 검색 히스토리 저장 (전세가율 계산 후 저장)
function saveSearchHistory(region, properties) {
    // 전세가율 계산 (지역의 평균 전세가율)
    let jeonseRate = null;
    if (properties && properties.length > 0) {
        const propertiesWithRate = properties.filter(p => p.jeonse_rate !== null && p.jeonse_rate !== undefined && p.jeonse_rate > 0);
        if (propertiesWithRate.length > 0) {
            const avgRate = propertiesWithRate.reduce((sum, p) => sum + p.jeonse_rate, 0) / propertiesWithRate.length;
            jeonseRate = Math.round(avgRate * 10) / 10; // 소수점 첫째 자리까지
        }
    }
    
    fetch('/api/search-history', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ region, risk_score: jeonseRate })  // 전세가율을 risk_score 필드에 저장
    })
    .then(() => {
        if (typeof loadRecentSearches === 'function') loadRecentSearches();
    })
    .catch(err => console.error('검색 히스토리 저장 실패:', err));
}

// 결과 렌더링
function renderResults(region, props, container) {
    const properties = [...props];

    const headerHTML = (count) => `
        <div class="result-head">
            <h2>"${region}" 매물 분석 결과 <span class="badge badge-neutral" id="result-count">${count}</span>
            ${isAdvancedSearch ? '<span class="badge badge-warn" style="margin-left:8px;">고급 검색</span>' : ''}</h2>
            <div class="controls">
                <label for="sort-select">정렬</label>
                <select id="sort-select" class="ctrl">
                    <option value="default">기본순</option>
                    <option value="warnDesc">위험요소 많음순</option>
                    <option value="warnAsc">위험요소 적음순</option>
                    <option value="jeonseRateDesc">전세가율 높음순</option>
                    <option value="jeonseRateAsc">전세가율 낮음순</option>
                </select>
                <label for="filter-input">필터</label>
                <input id="filter-input" class="ctrl" placeholder="경고 키워드 또는 매물명">
                <button id="expand-all" class="link-btn">전체 펼치기</button>
                <button id="collapse-all" class="link-btn">전체 접기</button>
            </div>
        </div>
    `;

    const buildCards = (list) => list.map((prop, idx) => {
        const name = prop.name || `매물 #${idx+1}`;
        const warns = Array.isArray(prop.warnings) ? prop.warnings : [];
        const checklist = Array.isArray(prop.checklist) ? prop.checklist : [];
        const warnCount = warns.length;
        const risk = prop.risk_level;
        const riskClass = risk === 'high' ? 'badge-danger' : risk === 'medium' ? 'badge-warn' : '';
        const riskLabel = {high: '전세가율 높음', medium: '전세가율 주의', low: '전세가율 낮음'}[risk] || '판단 불가';
        
        const warnItems = warns.length ? warns.map(w => `<li>⚠️ ${w}</li>`).join('') : '<li>추가 경고 항목 없음</li>';
        
        // 체크리스트를 동적으로 렌더링 (중요도 표시)
        const checklistItems = checklist.length ? checklist.map(c => {
            const isImportant = c.includes('⚠️') || c.includes('매우') || c.includes('추가');
            const itemClass = isImportant ? 'checklist-important' : '';
            const icon = isImportant ? '🔴' : '☑';
            return `<li class="${itemClass}">${icon} ${c.replace('⚠️ ', '')}</li>`;
        }).join('') : '<li>체크리스트 항목이 없습니다.</li>';
        
        let rateBadgeClass = 'badge-success';
        if (prop.jeonse_rate >= 80) rateBadgeClass = 'badge-danger';
        else if (prop.jeonse_rate >= 60) rateBadgeClass = 'badge-warn';
        
        const samples = Number.isInteger(prop.comparison_sample_count) ? prop.comparison_sample_count : null;
        const confidence = prop.comparison_confidence === 'moderate' ? '보통' : '제한적';
        const unavailable = prop.comparison_status === 'source_unavailable'
            ? '전세 자료 조회 실패' : '비교 표본 부족';
        const jeonseInfo = prop.jeonse_rate != null
            ? `<div class="comparison-evidence">전세 보증금 중앙값 <strong>${prop.jeonse_price}</strong> · 참고 전세가율 <span class="badge ${rateBadgeClass}">${prop.jeonse_rate}%</span> · 비교 ${samples}건 (신뢰도 ${confidence})</div>`
            : `<div class="comparison-evidence">전세가율 판단 불가 · ${unavailable}${samples === null ? '' : ` (${samples}건)`}</div>`;

        // 지역명 추출 (주소에서)
        const address = prop.address || '';
        const regionMatch = address.match(/([가-힣]+동|[가-힣]+가|[가-힣]+리)/);
        const regionName = regionMatch ? regionMatch[1] : region;
        const favoriteId = `favorite-prop-${idx}`;
        
        // 특이사항이 없는 경우 클래스 추가
        const noWarningsClass = warnCount === 0 ? 'no-warnings' : '';
        
        return `
            <div class="property-item ${noWarningsClass}" data-warnings="${warns.join(' ').toLowerCase()}" data-name="${(name||'').toLowerCase()}">
                <div class="card-head">
                    <div style="flex:1;">
                        <div style="display:flex; justify-content:space-between; align-items:start; margin-bottom:4px;">
                            <h3 style="margin:0; flex:1;">${name}</h3>
                            <button id="${favoriteId}" onclick="toggleFavoriteRegion('${regionName}', '${favoriteId}')" 
                                    style="background:none; border:none; font-size:18px; cursor:pointer; padding:4px; line-height:1; color:#ccc;"
                                    title="즐겨찾기 추가">
                                ☆
                            </button>
                        </div>
                        <div style="font-size:14px; font-weight:bold; color:#1565c0; margin-top:4px;">매매가: ${prop.price || '정보 없음'}</div>
                        ${jeonseInfo}
                    </div>
                    <div class="card-actions">
                        <span class="badge ${riskClass}">${riskLabel}</span>
                        <button class="compare-btn" onclick="addToComparisonFromButton(this)" data-property='${JSON.stringify(prop).replace(/'/g, "&apos;")}'>비교 추가</button>
                    </div>
                </div>
                <div class="warnings ${noWarningsClass}"><ul class="warn-list">${warnItems}</ul></div>
                <h4 class="check-toggle">[안전 계약 체크리스트] ▾</h4>
                <ul class="checklist collapsed">${checklistItems}</ul>
                <div class="property-actions">
                    <button class="action-btn location-btn" onclick="viewPropertyLocation(${JSON.stringify(address || regionName || '').replace(/"/g, '&quot;')})">📍 위치보기</button>
                    <button class="action-btn review-btn" onclick="showReviewModal('${name}')">리뷰 작성</button>
                    <button class="action-btn report-btn" onclick="showReportModal(${JSON.stringify({
                        name: name,
                        address: address || '',
                        price: prop.price || '',
                        jeonse_price: prop.jeonse_price || '',
                        jeonse_rate: prop.jeonse_rate || null,
                        region: regionName
                    }).replace(/"/g, '&quot;')})">신고하기</button>
                </div>
            </div>
        `;
    }).join('');

    container.innerHTML = `${headerHTML(properties.length)}<div class="property-list"></div>
        <div class="transaction-pagination" data-property-pagination>
            <button type="button" data-property-prev>이전</button>
            <span role="status" data-property-page></span>
            <button type="button" data-property-next>다음</button>
        </div>`;
    const propertyPageSize = 30;
    let propertyPage = 1;
    let filtered = properties;
    const pager = container.querySelector('[data-property-pagination]');
    const previous = pager.querySelector('[data-property-prev]');
    const next = pager.querySelector('[data-property-next]');
    const renderPage = () => {
        const pages = Math.max(1, Math.ceil(filtered.length / propertyPageSize));
        const offset = (propertyPage - 1) * propertyPageSize;
        container.querySelector('.property-list').innerHTML = buildCards(filtered.slice(offset, offset + propertyPageSize));
        document.getElementById('result-count').textContent = filtered.length;
        pager.hidden = pages === 1;
        previous.disabled = propertyPage === 1;
        next.disabled = propertyPage === pages;
        pager.querySelector('[data-property-page]').textContent = `${propertyPage} / ${pages}페이지`;
        attachCardHandlers();
    };
    previous.onclick = () => { propertyPage -= 1; renderPage(); };
    next.onclick = () => { propertyPage += 1; renderPage(); };

    const applyFilterAndSort = () => {
        const sortVal = document.getElementById('sort-select').value;
        const q = document.getElementById('filter-input').value.trim().toLowerCase();
        let list = [...properties];

        if (sortVal === 'warnDesc') list.sort((a, b) => (b.warnings?.length || 0) - (a.warnings?.length || 0));
        else if (sortVal === 'warnAsc') list.sort((a, b) => (a.warnings?.length || 0) - (b.warnings?.length || 0));
        else if (sortVal === 'jeonseRateDesc') list.sort((a, b) => (b.jeonse_rate ?? -1) - (a.jeonse_rate ?? -1));
        else if (sortVal === 'jeonseRateAsc') list.sort((a, b) => (a.jeonse_rate ?? Infinity) - (b.jeonse_rate ?? Infinity));

        if (q) {
            list = list.filter(p => 
                (p.warnings || []).join(' ').toLowerCase().includes(q) || 
                (p.name || '').toLowerCase().includes(q)
            );
        }

        filtered = list;
        propertyPage = 1;
        renderPage();
    };

    const attachCardHandlers = () => {
        document.querySelectorAll('.check-toggle').forEach(h => {
            h.addEventListener('click', () => {
                const container = h.closest('.property-item');
                const list = container?.querySelector('.checklist');
                if (!list) return;
                list.classList.toggle('collapsed');
                h.textContent = list.classList.contains('collapsed') ? '[안전 계약 체크리스트] ▾' : '[안전 계약 체크리스트] ▴';
            });
        });
    };

    renderPage();
    document.getElementById('sort-select').addEventListener('change', applyFilterAndSort);
    document.getElementById('filter-input').addEventListener('input', applyFilterAndSort);

    document.getElementById('expand-all').addEventListener('click', () => {
        document.querySelectorAll('.property-item').forEach(item => {
            const list = item.querySelector('.checklist');
            const toggle = item.querySelector('.check-toggle');
            if (list?.classList.contains('collapsed')) {
                list.classList.remove('collapsed');
                if (toggle) toggle.textContent = '[안전 계약 체크리스트] ▴';
            }
        });
    });

    document.getElementById('collapse-all').addEventListener('click', () => {
        document.querySelectorAll('.property-item').forEach(item => {
            const list = item.querySelector('.checklist');
            const toggle = item.querySelector('.check-toggle');
            if (list && !list.classList.contains('collapsed')) {
                list.classList.add('collapsed');
                if (toggle) toggle.textContent = '[안전 계약 체크리스트] ▾';
            }
        });
    });
}

// 실거래 데이터 로드 (드롭다운으로 기간 선택 가능)
let transactionRequest = 0;

function loadRealTransactions(region, monthCount = null, page = 1) {
    const container = document.getElementById('real-transactions-container');
    if (!container || !region) return;
    const requestId = ++transactionRequest;

    // 선택된 개월 수 가져오기 (기본값: 1개월)
    const monthSelect = document.getElementById('month-select');
    const selectedMonths = monthCount !== null ? monthCount : (monthSelect ? parseInt(monthSelect.value) : 1);

    // 로딩 표시는 즉시 하지 않고 약간의 지연 후 표시 (빠른 응답 시 불필요한 로딩 방지)
    const loadingTimeout = setTimeout(() => {
        if (requestId !== transactionRequest) return;
        container.innerHTML = '<div class="loading"><span class="spinner"></span><span>실거래 데이터를 불러오는 중입니다...</span></div>';
    }, 200);  // 300ms -> 200ms로 단축

    const kst = new Intl.DateTimeFormat('sv-SE', {timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit'}).format(new Date());
    const [year, monthNumber] = kst.split('-').map(Number);
    const months = [];
    // 선택된 개월 수만큼 조회 (기본값: 1개월)
    for (let i = 0; i < selectedMonths; i++) {
        const date = new Date(Date.UTC(year, monthNumber - 1 - i, 1));
        months.push(date.getUTCFullYear() + String(date.getUTCMonth() + 1).padStart(2, '0'));
    }

    // 병렬 처리로 모든 개월 데이터 동시 조회 (최적화)
    Promise.all(months.map(month => 
        fetch(`/api/real-transactions?region=${encodeURIComponent(region)}&deal_ymd=${month}&numOfRows=15&pageNo=${page}`)
            .then(res => {
                if (!res.ok) throw new Error('거래 자료 조회 실패');
                return res.json();
            })
    )).then(results => {
        clearTimeout(loadingTimeout);
        if (requestId !== transactionRequest) return;
        const allTransactions = results.flatMap(data => data.transactions || []);
        const hasMore = results.some(data => data.has_more);
        
        if (allTransactions.length === 0 && page === 1) {
            container.innerHTML = '<div class="transaction-empty">최근 실거래 데이터가 없습니다.</div>';
            return;
        }
        
        container.innerHTML = `
            <div class="transactions-grid">
                ${allTransactions.map(item => {
                    const area = item['전용면적'] || '';
                    const areaNum = parseFloat(area);
                    const pyeong = areaNum ? (areaNum / 3.3).toFixed(1) : '';
                    const areaText = area ? `${area}㎡${pyeong ? ` (${pyeong}평)` : ''}` : '면적 정보 없음';
                    const price = item['거래금액'] ? (item['거래금액'] / 10000).toFixed(0) + '억' : item['거래금액원문'] || '가격 정보 없음';
                    return `
                        <div class="transaction-card">
                            <h4>${item['아파트'] || '정보없음'} · ${item['층'] || ''}층</h4>
                            <div class="transaction-meta">
                                <span class="transaction-price">${price}</span>
                                <span>${item['법정동'] || ''} · ${areaText}</span>
                                <span>거래일자: ${item['거래일자'] || ''}</span>
                                <span>건축년도: ${item['건축년도'] || '정보없음'}</span>
                            </div>
                        </div>
                    `;
                }).join('')}
            </div>
            <div class="transaction-pagination">
                <button type="button" data-transaction-prev ${page === 1 ? 'disabled' : ''}>이전</button>
                <span role="status">${page}페이지 · 월별 최대 15건</span>
                <button type="button" data-transaction-next ${hasMore ? '' : 'disabled'}>다음</button>
            </div>
        `;
        container.querySelector('[data-transaction-prev]').onclick = () => loadRealTransactions(region, selectedMonths, page - 1);
        container.querySelector('[data-transaction-next]').onclick = () => loadRealTransactions(region, selectedMonths, page + 1);
    }).catch(() => {
        clearTimeout(loadingTimeout);
        if (requestId !== transactionRequest) return;
        container.innerHTML = '<div class="transaction-empty">실거래 데이터를 불러오는 데 실패했습니다.</div>';
    });
}

// 개월 수 변경 핸들러
function changeMonthRange() {
    if (currentRegion) {
        const monthSelect = document.getElementById('month-select');
        const selectedMonths = parseInt(monthSelect.value);
        loadRealTransactions(currentRegion, selectedMonths);
    }
}

// 매물 비교 기능
function addToComparisonFromButton(button) {
    try {
        const propertyJson = button.getAttribute('data-property');
        if (!propertyJson) {
            console.error('매물 데이터를 찾을 수 없습니다.');
            return;
        }
        const property = JSON.parse(propertyJson.replace(/&apos;/g, "'"));
        addToComparison(property);
    } catch (e) {
        console.error('매물 데이터 파싱 오류:', e);
        alert('매물 정보를 불러오는 중 오류가 발생했습니다.');
    }
}

function addToComparison(property) {
    if (comparisonProperties.length >= 5) {
        alert('최대 5개까지만 비교할 수 있습니다.');
        return;
    }
    if (!comparisonProperties.find(p => p.name === property.name && p.address === property.address)) {
        comparisonProperties.push(property);
        updateComparisonUI();
        showComparisonToast(`${property.name || '매물'}이(가) 비교 목록에 추가되었습니다.`);
    } else {
        showComparisonToast('이미 비교 목록에 있는 매물입니다.');
    }
}

function removeFromComparison(index) {
    comparisonProperties.splice(index, 1);
    updateComparisonUI();
    if (comparisonProperties.length === 0) {
        closeComparison();
    }
}

function updateComparisonUI() {
    const panel = document.getElementById('property-comparison');
    const count = document.getElementById('comparison-count');
    const compareBtn = panel?.querySelector('.compare-btn');
    
    if (count) count.textContent = comparisonProperties.length;
    
    if (compareBtn) {
        compareBtn.disabled = comparisonProperties.length < 2;
        compareBtn.textContent = comparisonProperties.length < 2 
            ? `비교하기 (최소 2개)` 
            : `비교하기 (${comparisonProperties.length}개)`;
    }
    
    if (panel) {
        panel.classList.toggle('hidden', comparisonProperties.length === 0);
        updateComparisonList();
    }
}

function updateComparisonList() {
    const listContainer = document.getElementById('comparison-list');
    if (!listContainer) return;
    
    if (comparisonProperties.length === 0) {
        listContainer.innerHTML = '';
        return;
    }
    
    listContainer.innerHTML = comparisonProperties.map((prop, idx) => `
        <div class="comparison-item">
            <span class="comparison-item-name">${prop.name || '매물명 없음'}</span>
            <button class="comparison-remove" onclick="removeFromComparison(${idx})" title="제거">×</button>
        </div>
    `).join('');
}

function showComparison() {
    if (comparisonProperties.length < 2) {
        alert('최소 2개 이상의 매물을 선택해주세요.');
        return;
    }
    
    const modal = document.createElement('div');
    modal.className = 'comparison-modal';
    modal.innerHTML = generateComparisonModal();
    document.body.appendChild(modal);
    document.body.style.overflow = 'hidden';
}

function generateComparisonModal() {
    const getRiskLevel = (score) => {
        if (score == null) return { level: '판단 불가', class: 'risk-unknown', color: '#6b7280' };
        if (score >= 80) return { level: '높음', class: 'risk-danger', color: '#dc3545' };
        if (score >= 60) return { level: '주의', class: 'risk-warning', color: '#ffc107' };
        return { level: '낮음', class: 'risk-safe', color: '#28a745' };
    };
    
    const formatPrice = (price) => {
        if (!price) return '정보 없음';
        if (typeof price === 'number') {
            if (price >= 10000) return `${(price / 10000).toFixed(1)}억원`;
            return `${price}만원`;
        }
        return price;
    };
    
    return `
        <div class="modal-content comparison-modal-content">
            <div class="modal-header">
                <h3>매물 상세 비교</h3>
                <button onclick="closeComparison()" class="modal-close">×</button>
            </div>
            <div class="comparison-body">
                <div class="comparison-visual">
                    <h4>전세가율 참고 구간</h4>
                    <div class="risk-bars">
                        ${comparisonProperties.map((prop, idx) => {
                            const risk = getRiskLevel(prop.risk_score);
                            const rate = prop.jeonse_rate;
                            const width = rate == null ? 0 : Math.min(rate, 100);
                            return `
                                <div class="risk-bar-item">
                                    <div class="risk-bar-label">
                                        <span class="risk-property-name">${prop.name || '매물명 없음'}</span>
                                        <span class="risk-score ${risk.class}">${rate == null ? '판단 불가' : rate + '%'}</span>
                                    </div>
                                    <div class="risk-bar-container">
                                        <div class="risk-bar" style="width: ${width}%; background-color: ${risk.color};"></div>
                                    </div>
                                    <span class="risk-level ${risk.class}">${risk.level}</span>
                                </div>
                            `;
                        }).join('')}
                    </div>
                </div>
                
                <div class="comparison-table-wrapper">
                    <table class="comparison-table">
                        <thead>
                            <tr>
                                <th class="comparison-category">구분</th>
                                ${comparisonProperties.map(p => `<th>${p.name || '매물명 없음'}</th>`).join('')}
                            </tr>
                        </thead>
                        <tbody>
                            <tr class="comparison-section-header">
                                <td colspan="${comparisonProperties.length + 1}">기본 정보</td>
                            </tr>
                            <tr>
                                <td class="comparison-label">주소</td>
                                ${comparisonProperties.map(p => `<td>${p.address || '정보 없음'}</td>`).join('')}
                            </tr>
                            <tr>
                                <td class="comparison-label">매매가</td>
                                ${comparisonProperties.map(p => `<td>${formatPrice(p.price)}</td>`).join('')}
                            </tr>
                            <tr>
                                <td class="comparison-label">전세가</td>
                                ${comparisonProperties.map(p => `<td>${p.jeonse_price || '정보 없음'}</td>`).join('')}
                            </tr>
                            <tr>
                                <td class="comparison-label">전세가율</td>
                                ${comparisonProperties.map(p => {
                                    const rate = p.jeonse_rate;
                                    if (rate == null) return '<td>판단 불가</td>';
                                    const rateClass = rate >= 80 ? 'rate-high' : (rate >= 60 ? 'rate-medium' : 'rate-low');
                                    return `<td><span class="${rateClass}">${rate}%</span></td>`;
                                }).join('')}
                            </tr>
                            <tr>
                                <td class="comparison-label">면적</td>
                                ${comparisonProperties.map(p => `<td>${p.area || '정보 없음'}</td>`).join('')}
                            </tr>
                            <tr>
                                <td class="comparison-label">층수</td>
                                ${comparisonProperties.map(p => `<td>${p.floor || '정보 없음'}</td>`).join('')}
                            </tr>
                            <tr>
                                <td class="comparison-label">건축년도</td>
                                ${comparisonProperties.map(p => `<td>${p.build_year || '정보 없음'}</td>`).join('')}
                            </tr>
                            
                            <tr class="comparison-section-header">
                                <td colspan="${comparisonProperties.length + 1}">전세가율 참고 분석</td>
                            </tr>
                            <tr>
                                <td class="comparison-label">참고 구간</td>
                                ${comparisonProperties.map(p => {
                                    const risk = getRiskLevel(p.risk_score);
                                    return `<td><span class="risk-badge ${risk.class}">${risk.level}</span></td>`;
                                }).join('')}
                            </tr>
                            <tr>
                                <td class="comparison-label">경고 항목 수</td>
                                ${comparisonProperties.map(p => `<td><span class="warning-count">${p.warnings?.length || 0}개</span></td>`).join('')}
                            </tr>
                            <tr>
                                <td class="comparison-label">주요 경고</td>
                                ${comparisonProperties.map(p => {
                                    const warnings = p.warnings || [];
                                    const mainWarnings = warnings.slice(0, 3).map(w => w.message || w).join(', ');
                                    return `<td class="warning-list">${mainWarnings || '없음'}</td>`;
                                }).join('')}
                            </tr>
                            
                            <tr class="comparison-section-header">
                                <td colspan="${comparisonProperties.length + 1}">체크리스트</td>
                            </tr>
                            <tr>
                                <td class="comparison-label">체크리스트 항목</td>
                                ${comparisonProperties.map(p => `<td>${p.checklist?.length || 0}개</td>`).join('')}
                            </tr>
                        </tbody>
                    </table>
                </div>
                
                <div class="comparison-actions-footer">
                    <button class="btn btn-outline" onclick="clearComparison(); closeComparison();">비교 목록 초기화</button>
                    <button class="btn btn-primary" onclick="exportComparison()">비교 결과 내보내기</button>
                </div>
            </div>
        </div>
    `;
}

function closeComparison() {
    const modal = document.querySelector('.comparison-modal');
    if (modal) {
        modal.remove();
        document.body.style.overflow = '';
    }
}

function clearComparison() {
    comparisonProperties = [];
    updateComparisonUI();
}

function exportComparison() {
    const data = comparisonProperties.map(p => ({
        매물명: p.name,
        주소: p.address,
        매매가: p.price,
        전세가: p.jeonse_price,
        전세가율: p.jeonse_rate,
        참고전세가율구간: p.risk_level === 'unknown' ? '판단 불가' : p.risk_level,
        경고수: p.warnings?.length || 0
    }));
    
    const csv = [
        Object.keys(data[0]).join(','),
        ...data.map(row => Object.values(row).join(','))
    ].join('\n');
    
    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `매물비교_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
}

function showComparisonToast(message) {
    const toast = document.createElement('div');
    toast.className = 'comparison-toast';
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 2000);
}

// 고급 검색 토글
function toggleAdvancedSearch() {
    document.getElementById('advanced-search-panel').classList.toggle('hidden');
}

function resetAdvancedSearch() {
    document.getElementById('min-price').value = '';
    document.getElementById('max-price').value = '';
    document.getElementById('property-type').value = '';
    document.getElementById('risk-level').value = '';
}

// 리뷰 모달
function showReviewModal(propertyName) {
    document.getElementById('review-property-name').value = propertyName;
    document.getElementById('review-modal').classList.remove('hidden');
    document.querySelectorAll('.star').forEach(star => star.classList.remove('active'));
    document.getElementById('review-rating').value = '0';
}

function closeReviewModal() {
    document.getElementById('review-modal').classList.add('hidden');
    document.getElementById('review-form').reset();
}

// 매물 위치보기: 카카오맵 검색 결과 페이지를 새 탭으로 연다 (API 키/결제수단 등록 불필요)
function viewPropertyLocation(address) {
    if (!address) {
        alert('주소 정보가 없어 위치를 확인할 수 없습니다.');
        return;
    }
    const url = 'https://map.kakao.com/link/search/' + encodeURIComponent(address);
    window.open(url, '_blank', 'noopener');
}

// 신고 모달
function showReportModal(propertyData) {
    // propertyData가 문자열인 경우 (기존 호환성)
    if (typeof propertyData === 'string') {
        propertyData = { name: propertyData, address: '', region: '' };
    }
    
    // 매물 정보를 모달에 채우기
    document.getElementById('report-property-name').value = propertyData.name || '';
    const addressInput = document.getElementById('report-address');
    if (addressInput && propertyData.address) {
        addressInput.value = propertyData.address;
    }
    
    // 매물 정보를 data 속성에 저장 (제출 시 사용)
    const reportForm = document.getElementById('report-form');
    if (reportForm) {
        reportForm.dataset.propertyData = JSON.stringify(propertyData);
    }
    
    document.getElementById('report-modal').classList.remove('hidden');
}

function closeReportModal() {
    document.getElementById('report-modal').classList.add('hidden');
    document.getElementById('report-form').reset();
    // 저장된 매물 정보 제거
    const reportForm = document.getElementById('report-form');
    if (reportForm && reportForm.dataset.propertyData) {
        delete reportForm.dataset.propertyData;
    }
}

// 초기화
document.addEventListener('DOMContentLoaded', function() {
    // 즐겨찾기 로드 (버튼 상태 업데이트용)
    loadFavorites();
    
    // 사이드바 데이터는 _left_sidebar.html과 _right_sidebar.html에서 자동으로 로드됨
    
    // URL 파라미터 확인
    const urlParams = new URLSearchParams(window.location.search);
    const regionParam = urlParams.get('region');
    if (regionParam) {
        document.getElementById('region-input').value = regionParam;
        searchRegion();
    }

    // 별점 이벤트
    const stars = document.querySelectorAll('.star');
    const ratingInput = document.getElementById('review-rating');
    const ratingStars = document.getElementById('rating-stars');
    
    stars.forEach(star => {
        star.addEventListener('click', function() {
            const rating = parseInt(this.dataset.rating);
            ratingInput.value = rating;
            stars.forEach((s, index) => {
                s.classList.toggle('active', index < rating);
            });
        });
        
        star.addEventListener('mouseover', function() {
            const rating = parseInt(this.dataset.rating);
            stars.forEach((s, index) => {
                s.style.color = index < rating ? '#ffc107' : '#ddd';
            });
        });
    });
    
    ratingStars?.addEventListener('mouseleave', function() {
        const currentRating = parseInt(ratingInput.value);
        stars.forEach((s, index) => {
            s.style.color = index < currentRating ? '#ffc107' : '#ddd';
        });
    });

    // 리뷰 제출
    document.getElementById('review-form')?.addEventListener('submit', function(e) {
        e.preventDefault();
        const rating = document.getElementById('review-rating').value;
        if (rating === '0') {
            alert('평점을 선택해주세요.');
            return;
        }
        
        fetch('/api/reviews', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                region: document.getElementById('review-property-name').value,
                rating: parseInt(rating),
                content: document.getElementById('review-content').value
            })
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                alert('리뷰가 등록되었습니다.');
                closeReviewModal();
            } else {
                alert('리뷰 등록에 실패했습니다.');
            }
        })
        .catch(() => alert('리뷰 등록 중 오류가 발생했습니다.'));
    });

    // 신고 제출
    document.getElementById('report-form')?.addEventListener('submit', function(e) {
        e.preventDefault();
        const reportType = document.getElementById('report-type').value;
        const description = document.getElementById('report-description').value;
        const propertyName = document.getElementById('report-property-name').value;
        const propertyAddress = document.getElementById('report-address').value;
        
        if (!reportType) {
            alert('신고 유형을 선택해주세요.');
            return;
        }
        if (!description.trim()) {
            alert('신고 사유를 입력해주세요.');
            return;
        }
        
        // 저장된 매물 정보 가져오기
        let propertyData = {};
        try {
            const savedData = this.dataset.propertyData;
            if (savedData) {
                propertyData = JSON.parse(savedData);
            }
        } catch (e) {
            console.warn('매물 정보 파싱 실패:', e);
        }
        
        // 신고 데이터 구성
        const reportData = {
            region: propertyData.region || propertyName || '알 수 없음',
            property_name: propertyName,
            property_address: propertyAddress || propertyData.address || '',
            report_type: reportType,
            description: description
        };
        
        // 추가 정보가 있으면 description에 포함
        if (propertyData.price || propertyData.jeonse_price) {
            const additionalInfo = [];
            if (propertyData.price) additionalInfo.push(`매매가: ${propertyData.price}`);
            if (propertyData.jeonse_price) additionalInfo.push(`전세가: ${propertyData.jeonse_price}`);
            if (propertyData.jeonse_rate) additionalInfo.push(`전세가율: ${propertyData.jeonse_rate}%`);
            if (additionalInfo.length > 0) {
                reportData.description = `[매물 정보]\n${additionalInfo.join(', ')}\n\n[신고 사유]\n${description}`;
            }
        }
        
        fetch('/api/reports', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(reportData)
        })
        .then(res => {
            if (!res.ok) {
                return res.json().then(err => Promise.reject(err));
            }
            return res.json();
        })
        .then(data => {
            if (data.status === 'success') {
                alert('신고가 접수되었습니다. 마이페이지에서 신고 내역을 확인할 수 있습니다.');
                closeReportModal();
            } else {
                alert('신고 접수에 실패했습니다: ' + (data.error || '알 수 없는 오류'));
            }
        })
        .catch(err => {
            console.error('신고 접수 오류:', err);
            alert('신고 접수 중 오류가 발생했습니다. 로그인 상태를 확인해주세요.');
        });
    });

    // 검색 입력 이벤트
    document.getElementById('clear-btn-in')?.addEventListener('click', function() {
        document.getElementById('region-input').value = '';
        document.getElementById('region-input').focus();
    });

    document.getElementById('region-input')?.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') searchRegion();
    });
    
    // 최근 검색어 드롭다운 로드 (드롭다운용)
    loadRecentSearches();
});

// 사이드바 관련 함수들은 _left_sidebar.html에서 제공됨
// searchRegionFromSidebar, removeFavoriteFromSidebar, deleteSearchHistoryFromSidebar 등은
// _left_sidebar.html의 함수들을 사용하도록 변경됨

// 최근 검색 기록 로드 (드롭다운용)
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
            const datalist = document.getElementById('recent-searches-list');
            const searchInput = document.getElementById('region-input');
            
            if (!datalist || !searchInput) {
                return;
            }
            
            // 기존 옵션 제거
            datalist.innerHTML = '';
            
            if (!data || data.length === 0) {
                return;
            }
            
            // 최신순으로 정렬 (이미 백엔드에서 최신순으로 정렬되어 있지만, 확실히 하기 위해)
            const sortedData = [...data].sort((a, b) => {
                const dateA = new Date(a.search_date);
                const dateB = new Date(b.search_date);
                return dateB - dateA; // 최신순 (내림차순)
            });
            
            // 최대 5개만 표시 (가장 최근 검색어가 맨 위)
            const uniqueRegions = [];
            const seen = new Set();
            for (const item of sortedData) {
                const region = item.region;
                if (!seen.has(region) && uniqueRegions.length < 5) {
                    seen.add(region);
                    uniqueRegions.push(region);
                }
            }
            
            // datalist에 옵션 추가 (최신순)
            uniqueRegions.forEach(region => {
                const option = document.createElement('option');
                option.value = region;
                datalist.appendChild(option);
            });
        })
        .catch(error => {
            console.error('[검색 기록] 로드 실패:', error);
        });
}

