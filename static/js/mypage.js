function removeFavorite(id) {
    if (confirm('이 즐겨찾기를 삭제하시겠습니까?')) {
        fetch('/api/favorites/' + id, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' }
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    location.reload();
                } else {
                    alert('삭제 중 오류가 발생했습니다.');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('삭제 중 오류가 발생했습니다.');
            });
    }
}

function searchFromFavorite(region) {
    window.location.href = "{{ url_for('searchscan_page') }}?region=" + encodeURIComponent(region);
}

function deleteSearchHistory(historyId) {
    if (!confirm('이 검색 기록을 삭제하시겠습니까?')) {
        return;
    }
    fetch(`/api/search-history/${historyId}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin'
    })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                const toast = document.createElement('div');
                toast.textContent = '검색 기록이 삭제되었습니다.';
                toast.style.cssText = 'position: fixed; top: 20px; right: 20px; background: #10b981; color: white; padding: 12px 24px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); z-index: 10000; animation: slideIn 0.3s ease-out;';
                document.body.appendChild(toast);
                setTimeout(() => {
                    location.reload();
                }, 1000);
            } else {
                alert('삭제에 실패했습니다: ' + (data.error || '알 수 없는 오류'));
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('삭제 중 오류가 발생했습니다: ' + error.message);
        });
}

function deleteAllSearchHistory() {
    if (!confirm('모든 검색 기록을 삭제하시겠습니까?\n이 작업은 되돌릴 수 없습니다.')) {
        return;
    }
    fetch('/api/search-history/all', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin'
    })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                const toast = document.createElement('div');
                toast.textContent = `모든 검색 기록이 삭제되었습니다. (${data.deleted_count || 0}개)`;
                toast.style.cssText = 'position: fixed; top: 20px; right: 20px; background: #10b981; color: white; padding: 12px 24px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); z-index: 10000; animation: slideIn 0.3s ease-out;';
                document.body.appendChild(toast);
                setTimeout(() => {
                    location.reload();
                }, 1000);
            } else {
                alert('삭제에 실패했습니다: ' + (data.error || '알 수 없는 오류'));
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('삭제 중 오류가 발생했습니다: ' + error.message);
        });
}

function markAllNotificationsAsRead() {
    if (!confirm('모든 알림을 읽음으로 표시하시겠습니까?')) {
        return;
    }
    fetch('/api/notifications/read-all', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin'
    })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                location.reload();
            } else {
                alert(data.message || '알림 읽음 처리에 실패했습니다.');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('알림 읽음 처리 중 오류가 발생했습니다.');
        });
}

function readNotification(id) {
    fetch('/api/notifications/' + id + '/read', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin'
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                location.reload();
            }
        })
        .catch(error => {
            console.error('Error:', error);
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
    const form = document.getElementById('review-form');
    if (form) {
        form.reset();
        document.getElementById('review-rating').value = '0';
        document.querySelectorAll('#rating-stars .star').forEach(star => {
            star.style.color = '#ddd';
        });
    }
}

function editReview(reviewId) {
    fetch('/api/reviews')
        .then(response => response.json())
        .then(data => {
            const reviews = data.reviews || (Array.isArray(data) ? data : []);
            const review = reviews.find(r => r.id === reviewId);
            if (!review) {
                alert('리뷰를 찾을 수 없습니다.');
                return;
            }
            openReviewModal();
            document.getElementById('review-region').value = review.region || '';
            document.getElementById('review-rating').value = review.rating || 0;
            document.getElementById('review-content').value = review.content || '';
            const rating = parseInt(review.rating) || 0;
            document.querySelectorAll('#rating-stars .star').forEach((star, index) => {
                star.style.color = index < rating ? '#ffc107' : '#ddd';
            });
            const form = document.getElementById('review-form');
            const originalSubmit = form.onsubmit;
            form.onsubmit = function(e) {
                e.preventDefault();
                const region = document.getElementById('review-region').value.trim();
                const rating = parseInt(document.getElementById('review-rating').value);
                const content = document.getElementById('review-content').value.trim();
                if (!region || rating === 0 || !content) {
                    alert('모든 항목을 입력해주세요.');
                    return;
                }
                fetch(`/api/reviews/${reviewId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'same-origin',
                    body: JSON.stringify({ region: region, rating: rating, content: content })
                })
                    .then(response => response.json())
                    .then(data => {
                        if (data.status === 'success') {
                            alert('리뷰가 수정되었습니다.');
                            closeReviewModal();
                            location.reload();
                        } else {
                            alert(data.error || '리뷰 수정에 실패했습니다.');
                        }
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        alert('리뷰 수정 중 오류가 발생했습니다.');
                    });
            };
        })
        .catch(error => {
            console.error('Error:', error);
            alert('리뷰 정보를 불러오는 중 오류가 발생했습니다.');
        });
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
                alert('리뷰가 삭제되었습니다.');
                location.reload();
            } else {
                alert(data.error || '리뷰 삭제에 실패했습니다.');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('리뷰 삭제 중 오류가 발생했습니다.');
        });
}

document.addEventListener('DOMContentLoaded', function() {
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
                        alert('리뷰가 등록되었습니다.');
                        closeReviewModal();
                        location.reload();
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
    const ratingStars = document.getElementById('rating-stars');
    if (ratingStars) {
        ratingStars.addEventListener('mouseleave', function() {
            const currentRating = parseInt(document.getElementById('review-rating').value) || 0;
            document.querySelectorAll('#rating-stars .star').forEach((s, index) => {
                s.style.color = index < currentRating ? '#ffc107' : '#ddd';
            });
        });
    }
});

function showMoreNotifications() {
    const hiddenDiv = document.getElementById('hidden-notifications');
    const showMoreBtn = document.getElementById('show-more-notifications');
    const notificationList = document.getElementById('notification-list');
    if (hiddenDiv && showMoreBtn) {
        const hiddenItems = hiddenDiv.querySelectorAll('.notification-item');
        hiddenItems.forEach(item => {
            notificationList.insertBefore(item, showMoreBtn.parentElement);
        });
        showMoreBtn.parentElement.remove();
        hiddenDiv.remove();
    }
}

function toDongUnit(region) {
    if (!region || typeof region !== 'string') return region;
    const dongMatch = region.match(/([가-힣0-9]+동)/);
    if (dongMatch) return dongMatch[1];
    const gaMatch = region.match(/([가-힣0-9]+가)/);
    if (gaMatch) return gaMatch[1];
    const riMatch = region.match(/([가-힣0-9]+리)/);
    if (riMatch) return riMatch[1];
    return region;
}

document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.history-item .item-title').forEach(el => {
        el.textContent = toDongUnit(el.textContent);
    });
});
