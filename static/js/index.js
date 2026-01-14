function loadTopRiskRegions() {
    const rankingContainer = document.getElementById('danger-ranking');
    if (!rankingContainer) return;
    
    fetch('/heatmap')
        .then(response => {
            if (!response.ok) {
                throw new Error('API 호출 실패');
            }
            return response.json();
        })
        .then(data => {
            if (!data || !Array.isArray(data) || data.length === 0) {
                rankingContainer.innerHTML = '<div class="rank-item"><span class="rank-region">데이터가 없습니다</span></div>';
                return;
            }
            
            // 전세가율 80% 이상인 위험 지역만 필터링 (score는 전세가율을 의미)
            const dangerousRegions = data.filter(region => {
                const score = region.score || 0;
                // 전세가율 80% 이상이면 위험 지역
                return score >= 80;
            })
            .sort((a, b) => (b.score || 0) - (a.score || 0))
            .slice(0, 5);
            
            if (dangerousRegions.length === 0) {
                rankingContainer.innerHTML = '<div class="rank-item"><span class="rank-region">위험 지역 데이터가 없습니다</span></div>';
                return;
            }
            
            rankingContainer.innerHTML = dangerousRegions.map((region, index) => {
                const rank = index + 1;
                const jeonseRate = region.score || 0;
                const scoreClass = 'danger'; // 위험 지역이므로 항상 danger 클래스
                return `<div class="rank-item">
                    <span class="rank-num">${rank}</span>
                    <span class="rank-region">${region.region}</span>
                    <span class="rank-score ${scoreClass}">${jeonseRate.toFixed(1)}%</span>
                </div>`;
            }).join('');
        })
        .catch(error => {
            console.error('위험 지역 데이터 로드 실패:', error);
            rankingContainer.innerHTML = '<div class="rank-item"><span class="rank-region">데이터를 불러올 수 없습니다</span></div>';
        });
}

function loadYearlyStats() {
    const chartContainer = document.getElementById('yearly-chart');
    fetch('/api/yearly-reports')
        .then(response => {
            if (!response.ok) {
                throw new Error('API 호출 실패');
            }
            return response.json();
        })
        .then(data => {
            if (!data || !Array.isArray(data) || data.length === 0) {
                console.warn('년도별 데이터가 없습니다');
                return;
            }
            const maxCount = Math.max(...data.map(item => item.count), 1);
            chartContainer.innerHTML = data.map(item => {
                const heightPercent = maxCount > 0 ? (item.count / maxCount) * 100 : 0;
                return `<div class="bar" style="height: ${heightPercent}%"><span>${item.count}</span></div>`;
            }).join('');
        })
        .catch(error => {
            console.error('년도별 통계 로드 실패:', error);
        });
}

function loadMainStats() {
    fetch('/api/stats')
        .then(response => {
            if (!response.ok) {
                throw new Error('API 호출 실패');
            }
            return response.json();
        })
        .then(data => {
            function formatNumber(num) {
                if (num === null || num === undefined) return '0';
                return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
            }
            const totalAnalysesEl = document.getElementById('total-analyses');
            if (totalAnalysesEl) {
                totalAnalysesEl.textContent = formatNumber(data.total_analyses || 0);
            }
            const accuracyEl = document.getElementById('accuracy');
            if (accuracyEl) {
                accuracyEl.textContent = (data.accuracy || 0).toFixed(1) + '%';
            }
            const avgTimeEl = document.getElementById('avg-analysis-time');
            if (avgTimeEl) {
                avgTimeEl.textContent = (data.avg_analysis_time || 0).toFixed(1) + '초';
            }
            const blockedCasesEl = document.getElementById('blocked-cases');
            if (blockedCasesEl) {
                blockedCasesEl.textContent = formatNumber(data.blocked_cases || 0);
            }
        })
        .catch(error => {
            console.error('메인 페이지 통계 로드 실패:', error);
            const totalAnalysesEl = document.getElementById('total-analyses');
            if (totalAnalysesEl) totalAnalysesEl.textContent = '0';
            const accuracyEl = document.getElementById('accuracy');
            if (accuracyEl) accuracyEl.textContent = '0%';
            const avgTimeEl = document.getElementById('avg-analysis-time');
            if (avgTimeEl) avgTimeEl.textContent = '0초';
            const blockedCasesEl = document.getElementById('blocked-cases');
            if (blockedCasesEl) blockedCasesEl.textContent = '0';
        });
}

function openReviewModal() {
    const modal = document.getElementById('review-modal');
    if (modal) {
        modal.style.display = 'flex';
        modal.style.position = 'fixed';
        modal.style.top = '0';
        modal.style.left = '0';
        modal.style.width = '100%';
        modal.style.height = '100%';
        modal.style.backgroundColor = 'rgba(0,0,0,0.5)';
        modal.style.zIndex = '10000';
        modal.style.alignItems = 'center';
        modal.style.justifyContent = 'center';
    }
}

function closeReviewModal() {
    const modal = document.getElementById('review-modal');
    if (modal) {
        modal.style.display = 'none';
    }
    document.getElementById('review-form').reset();
    document.getElementById('review-rating').value = '0';
    document.querySelectorAll('#rating-stars .star').forEach(star => {
        star.style.color = '#ddd';
    });
}

document.addEventListener('DOMContentLoaded', function() {
    loadMainStats();
    loadTopRiskRegions();
    loadYearlyStats();
    
    // 위험 지역 실시간 업데이트 (30초마다)
    let riskRegionsUpdateInterval = setInterval(() => {
        loadTopRiskRegions();
    }, 30000); // 30초마다 업데이트
    
    // 페이지가 보일 때만 업데이트 (탭 전환 시 중지/재개)
    document.addEventListener('visibilitychange', function() {
        if (document.hidden) {
            // 페이지가 숨겨지면 업데이트 중지
            if (riskRegionsUpdateInterval) {
                clearInterval(riskRegionsUpdateInterval);
                riskRegionsUpdateInterval = null;
            }
        } else {
            // 페이지가 보이면 즉시 업데이트하고 주기적 업데이트 재개
            loadTopRiskRegions();
            if (!riskRegionsUpdateInterval) {
                riskRegionsUpdateInterval = setInterval(() => {
                    loadTopRiskRegions();
                }, 30000);
            }
        }
    });
    const writeReviewBtn = document.getElementById('write-review-btn');
    if (writeReviewBtn) {
        writeReviewBtn.addEventListener('click', function() {
            fetch('/api/reviews')
                .then(() => openReviewModal())
                .catch(() => {
                    if (confirm('리뷰를 작성하려면 로그인이 필요합니다. 로그인 페이지로 이동하시겠습니까?')) {
                        window.location.href = '/login';
                    }
                });
        });
    }
    const ratingStarsContainer = document.getElementById('rating-stars');
    if (ratingStarsContainer) {
        document.querySelectorAll('#rating-stars .star').forEach(star => {
            star.addEventListener('click', function() {
                const rating = parseInt(this.dataset.rating);
                document.getElementById('review-rating').value = rating;
                document.querySelectorAll('#rating-stars .star').forEach((s, index) => {
                    s.style.color = index < rating ? '#ffc107' : '#ddd';
                });
            });
            star.addEventListener('mouseenter', function() {
                const rating = parseInt(this.dataset.rating);
                document.querySelectorAll('#rating-stars .star').forEach((s, index) => {
                    s.style.color = index < rating ? '#ffc107' : '#ddd';
                });
            });
        });
        ratingStarsContainer.addEventListener('mouseleave', function() {
            const currentRating = parseInt(document.getElementById('review-rating').value) || 0;
            document.querySelectorAll('#rating-stars .star').forEach((s, index) => {
                s.style.color = index < currentRating ? '#ffc107' : '#ddd';
            });
        });
    }
    const reviewForm = document.getElementById('review-form');
    if (reviewForm) {
        reviewForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const region = document.getElementById('review-region').value.trim();
            const rating = parseInt(document.getElementById('review-rating').value);
            const content = document.getElementById('review-content').value.trim();
            if (!region) {
                alert('지역명을 입력해주세요.');
                return;
            }
            if (rating === 0) {
                alert('평점을 선택해주세요.');
                return;
            }
            if (!content) {
                alert('리뷰 내용을 입력해주세요.');
                return;
            }
            fetch('/api/reviews', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify({ region: region, rating: rating, content: content })
            })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        alert('리뷰가 등록되었습니다. 마이페이지에서 확인하실 수 있습니다.');
                        closeReviewModal();
                    } else {
                        alert(data.error || '리뷰 등록에 실패했습니다.');
                        if (data.error && data.error.includes('로그인')) {
                            window.location.href = '/login';
                        }
                    }
                })
                .catch(error => {
                    console.error('리뷰 등록 오류:', error);
                    alert('리뷰 등록 중 오류가 발생했습니다.');
                });
        });
    }
});
