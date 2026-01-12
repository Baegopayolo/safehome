let allReviews = [];
let currentFilter = 'all';
let editingReviewId = null;
let currentUserId = null;

function loadReviews() {
    const container = document.getElementById('reviews-container');
    container.innerHTML = '<div class="loading">리뷰를 불러오는 중...</div>';
    fetch('/api/reviews')
        .then(response => {
            if (!response.ok) {
                throw new Error('API 호출 실패');
            }
            return response.json();
        })
        .then(data => {
            if (data.reviews) {
                allReviews = data.reviews;
                currentUserId = data.current_user_id || null;
            } else {
                allReviews = Array.isArray(data) ? data : [];
            }
            displayReviews(allReviews);
        })
        .catch(error => {
            console.error('리뷰 로드 실패:', error);
            container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">⚠️</div>
                <h3>리뷰를 불러올 수 없습니다</h3>
                <p>잠시 후 다시 시도해주세요.</p>
            </div>`;
        });
}

function displayReviews(reviews) {
    const container = document.getElementById('reviews-container');
    if (!reviews || reviews.length === 0) {
        container.innerHTML = `
        <div class="empty-state">
            <div class="empty-state-icon">⭐</div>
            <h3>아직 등록된 리뷰가 없습니다</h3>
            <p>첫 번째 리뷰를 작성해보세요!</p>
            <button class="write-review-btn" onclick="openReviewModal()" style="margin-top: 16px;">리뷰 작성하기</button>
        </div>
        `;
        return;
    }
    container.innerHTML = '<div class="reviews-grid"></div>';
    const grid = container.querySelector('.reviews-grid');
    reviews.forEach(review => {
        const card = createReviewCard(review);
        grid.appendChild(card);
    });
}

function createReviewCard(review) {
    const card = document.createElement('div');
    card.className = 'review-card';
    const isMyReview = review.user_id && typeof currentUserId !== 'undefined' && review.user_id === currentUserId;
    const userInitial = review.username ? review.username.charAt(0).toUpperCase() : '익';
    const stars = '★'.repeat(review.rating) + '☆'.repeat(5 - review.rating);

    card.innerHTML = `
        <div class="review-header">
          <div class="review-user">
            <div class="user-avatar">${userInitial}</div>
            <div class="user-info">
              <h4>${review.username || '익명'}</h4>
              <div class="region">${review.region || '지역 정보 없음'}</div>
            </div>
          </div>
          <div class="review-rating">
            ${stars.split('').map((star, i) =>
                `<span class="${star === '★' ? 'star' : 'star-empty'}">${star}</span>`
            ).join('')}
          </div>
        </div>
        <div class="review-content">${review.content || '내용 없음'}</div>
        <div class="review-footer">
          <div class="review-date">${review.created_at || ''}</div>
          ${isMyReview ? `
            <div class="review-actions">
                <button class="action-btn edit" onclick="editReview(${review.id})">수정</button>
                <button class="action-btn delete" onclick="deleteReview(${review.id})">삭제</button>
            </div>
          ` : ''}
        </div>
    `;
    return card;
}

function filterReviews(filter) {
    currentFilter = filter;
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.filter === filter);
    });
    let filtered = [...allReviews];
    if (filter === 'my' && typeof currentUserId !== 'undefined' && currentUserId !== null) {
        filtered = filtered.filter(r => r.user_id === currentUserId);
    }
    displayReviews(filtered);
}

function filterByRegion() {
    const region = document.getElementById('region-filter').value.toLowerCase();
    let filtered = [...allReviews];
    if (currentFilter === 'my' && typeof currentUserId !== 'undefined' && currentUserId !== null) {
        filtered = filtered.filter(r => r.user_id === currentUserId);
    }
    if (region) {
        filtered = filtered.filter(r => r.region && r.region.toLowerCase().includes(region));
    }
    const rating = document.getElementById('rating-filter').value;
    if (rating !== 'all') {
        filtered = filtered.filter(r => r.rating >= parseInt(rating));
    }
    displayReviews(filtered);
}

function filterByRating() {
    const rating = document.getElementById('rating-filter').value;
    let filtered = [...allReviews];
    if (currentFilter === 'my' && typeof currentUserId !== 'undefined' && currentUserId !== null) {
        filtered = filtered.filter(r => r.user_id === currentUserId);
    }
    if (rating !== 'all') {
        filtered = filtered.filter(r => r.rating >= parseInt(rating));
    }
    const region = document.getElementById('region-filter').value.toLowerCase();
    if (region) {
        filtered = filtered.filter(r => r.region && r.region.toLowerCase().includes(region));
    }
    displayReviews(filtered);
}

function openReviewModal() {
    editingReviewId = null;
    document.getElementById('modal-title').textContent = '리뷰 작성';
    document.getElementById('review-form').reset();
    document.getElementById('review-rating').value = '0';
    document.querySelectorAll('#rating-stars .star').forEach(star => {
        star.style.color = '#ddd';
    });
    const modal = document.getElementById('review-modal');
    modal.style.display = 'flex';
}

function editReview(reviewId) {
    const review = allReviews.find(r => r.id === reviewId);
    if (!review) {
        alert('리뷰를 찾을 수 없습니다.');
        return;
    }
    editingReviewId = reviewId;
    document.getElementById('modal-title').textContent = '리뷰 수정';
    document.getElementById('review-region').value = review.region || '';
    document.getElementById('review-rating').value = review.rating || 0;
    document.getElementById('review-content').value = review.content || '';
    const rating = parseInt(review.rating) || 0;
    document.querySelectorAll('#rating-stars .star').forEach((star, index) => {
        star.style.color = index < rating ? '#ffc107' : '#ddd';
    });
    const modal = document.getElementById('review-modal');
    modal.style.display = 'flex';
}

function deleteReview(reviewId) {
    if (!confirm('이 리뷰를 삭제하시겠습니까?')) {
        return;
    }
    fetch(`/api/reviews/${reviewId}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin'
    })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showToast('리뷰가 삭제되었습니다.');
                loadReviews();
            } else {
                alert(data.error || '리뷰 삭제에 실패했습니다.');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('리뷰 삭제 중 오류가 발생했습니다.');
        });
}

function closeReviewModal() {
    const modal = document.getElementById('review-modal');
    modal.style.display = 'none';
    editingReviewId = null;
}

function showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

document.addEventListener('DOMContentLoaded', function () {
    loadReviews();

    document.querySelectorAll('#rating-stars .star').forEach(star => {
        star.addEventListener('click', function () {
            const rating = parseInt(this.dataset.rating);
            document.getElementById('review-rating').value = rating;
            document.querySelectorAll('#rating-stars .star').forEach((s, index) => {
                s.style.color = index < rating ? '#ffc107' : '#ddd';
            });
        });
        star.addEventListener('mouseenter', function () {
            const rating = parseInt(this.dataset.rating);
            document.querySelectorAll('#rating-stars .star').forEach((s, index) => {
                s.style.color = index < rating ? '#ffc107' : '#ddd';
            });
        });
    });

    document.getElementById('rating-stars').addEventListener('mouseleave', function () {
        const currentRating = parseInt(document.getElementById('review-rating').value) || 0;
        document.querySelectorAll('#rating-stars .star').forEach((s, index) => {
            s.style.color = index < currentRating ? '#ffc107' : '#ddd';
        });
    });

    document.getElementById('review-form').addEventListener('submit', function (e) {
        e.preventDefault();
        const region = document.getElementById('review-region').value.trim();
        const rating = parseInt(document.getElementById('review-rating').value);
        const content = document.getElementById('review-content').value.trim();

        if (!region || rating === 0 || !content) {
            alert('모든 항목을 입력해주세요.');
            return;
        }

        const url = editingReviewId ? `/api/reviews/${editingReviewId}` : '/api/reviews';
        const method = editingReviewId ? 'PUT' : 'POST';
        fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify({ region: region, rating: rating, content: content })
        })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    showToast(editingReviewId ? '리뷰가 수정되었습니다.' : '리뷰가 등록되었습니다.');
                    closeReviewModal();
                    loadReviews();
                } else {
                    alert(data.error || '리뷰 등록에 실패했습니다.');
                    if (data.error && data.error.includes('로그인')) {
                        window.location.href = '/login';
                    }
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('리뷰 등록 중 오류가 발생했습니다.');
            });
    });
});
