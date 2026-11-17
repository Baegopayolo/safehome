"""인증 관련 라우트 핸들러"""
from flask import render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from models import User

def register_auth_routes(app, db, bcrypt):
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('home'))
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            user = User(username=username, password=hashed_password)
            db.session.add(user)
            db.session.commit()
            flash('회원가입이 완료되었습니다! 이제 로그인할 수 있습니다.', 'success')
            return redirect(url_for('login'))
        return render_template('Login/register.html')
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('home'))
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            user = User.query.filter_by(username=username).first()
            if user and bcrypt.check_password_hash(user.password, password):
                login_user(user)
                session.pop('display_name', None)
                return redirect(url_for('mypage'))
            flash('로그인에 실패했습니다. 아이디와 비밀번호를 확인해주세요.', 'danger')
        return render_template('Login/login.html')
    @app.route('/logout')
    def logout():
        session.pop('display_name', None)
        logout_user()
        return redirect(url_for('home'))
    @app.route('/change-password', methods=['POST'])
    @login_required
    def change_password():
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        if not bcrypt.check_password_hash(current_user.password, current_password):
            flash('현재 비밀번호가 일치하지 않습니다.', 'danger')
            return redirect(url_for('mypage'))
        if new_password != confirm_password:
            flash('새 비밀번호가 일치하지 않습니다.', 'danger')
            return redirect(url_for('mypage'))
        if len(new_password) < 6:
            flash('비밀번호는 최소 6자 이상이어야 합니다.', 'danger')
            return redirect(url_for('mypage'))
        current_user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        db.session.commit()
        flash('비밀번호가 성공적으로 변경되었습니다.', 'success')
        return redirect(url_for('mypage'))
    @app.route('/mypage')
    @login_required
    def mypage():
        from map_indicators import read_map_indicators
        from models import Favorite, Notification, Report
        from time_utils import format_kst_datetime, format_kst_date
        from utils import SEOUL_SIGUNGU_CODES
        favorites = Favorite.query.filter_by(user_id=current_user.id).order_by(Favorite.created_at.desc()).limit(5).all()
        favorite_data = []
        indicators = {}
        if favorites:
            districts = {code: name for name, code in SEOUL_SIGUNGU_CODES.items()}
            for row in read_map_indicators(app, db):
                if row['status'] != 'available':
                    continue
                indicators[f"{districts[row['region_code']]} {row['dong']}"] = row['score']
                if row['region'] != '신사동':  # This unqualified name also refers to a dong in Eunpyeong-gu.
                    indicators[row['region']] = row['score']
        for fav in favorites:
            favorite_data.append({
                'id': fav.id,
                'address': fav.region,
                'date_added': format_kst_date(fav.created_at),
                'jeonse_rate': indicators.get(' '.join(fav.region.split())),
            })
        notifications = Notification.query.filter(
            (Notification.user_id == current_user.id) | (Notification.user_id.is_(None))
        ).order_by(Notification.created_at.desc()).limit(10).all()
        notification_data = [{
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'type': n.type or 'info',
            'created_at': format_kst_datetime(n.created_at),
            'is_read': n.is_read
        } for n in notifications]
        reports = Report.query.filter_by(user_id=current_user.id).order_by(Report.created_at.desc()).all()
        # 신고 유형 한글 변환
        report_type_map = {
            'suspicious': '의심스러운 매물',
            'scam': '전세사기 의심',
            'fake': '가짜 매물',
            'other': '기타'
        }
        report_data = [{
            'id': r.id,
            'region': r.region,
            'property_address': r.property_address or '주소 정보 없음',
            'report_type': r.report_type,
            'report_type_kr': report_type_map.get(r.report_type, r.report_type),
            'status': r.status,
            'created_at': format_kst_datetime(r.created_at),
            'description': r.description[:200] + '...' if r.description and len(r.description) > 200 else (r.description or '')
        } for r in reports]
        from models import Review
        reviews = Review.query.filter_by(user_id=current_user.id).order_by(Review.created_at.desc()).all()
        review_data = [{
            'id': r.id,
            'region': r.region,
            'rating': r.rating,
            'content': r.content or '',
            'created_at': format_kst_datetime(r.created_at)
        } for r in reviews]
        return render_template('Login/mypage.html',
                             username=session.get('display_name', current_user.username),
                             join_date=format_kst_date(current_user.created_at, '%Y년 %m월 %d일'),
                             favorites=favorite_data,
                             notifications=notification_data,
                             reports=report_data,
                             reviews=review_data)
