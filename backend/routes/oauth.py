"""소셜 로그인(OAuth) 라우트 핸들러 - 네이버, 카카오

Google은 리다이렉트 URI에 도메인+HTTPS가 반드시 필요해서(공인 IP만으로는 등록 불가)
도메인을 연결하기 전까지는 구현하지 않습니다.
"""
import os
import secrets
import requests
from flask import redirect, url_for, flash, request, session
from flask_login import login_user, current_user


def register_oauth_routes(app, db, bcrypt):
    from models import User

    def _login_or_create(provider, provider_id, display_name=None):
        """소셜 계정으로 로그인하고, 처음 로그인하는 사용자면 새 계정을 만든다.

        username(=naver_<고유ID>)은 내부 식별/로그인용으로만 쓰고, 화면에는
        display_name(네이버 이름/카카오 닉네임)을 대신 보여준다.
        """
        username = f"{provider}_{provider_id}"
        user = User.query.filter_by(username=username).first()
        if user is None:
            random_password = bcrypt.generate_password_hash(secrets.token_hex(32)).decode('utf-8')
            user = User(username=username, password=random_password)
            db.session.add(user)
            db.session.commit()
        login_user(user)
        if display_name:
            session['display_name'] = display_name
        else:
            session.pop('display_name', None)

    # ---------------- 네이버 로그인 ----------------
    @app.route('/login/naver')
    def naver_login():
        if current_user.is_authenticated:
            return redirect(url_for('home'))
        client_id = os.environ.get('NAVER_CLIENT_ID')
        if not client_id:
            flash('네이버 로그인이 아직 설정되지 않았습니다. 관리자에게 문의해주세요.', 'danger')
            return redirect(url_for('login'))
        state = secrets.token_urlsafe(16)
        session['naver_oauth_state'] = state
        redirect_uri = url_for('naver_callback', _external=True)
        auth_url = (
            'https://nid.naver.com/oauth2.0/authorize'
            f'?response_type=code&client_id={client_id}'
            f'&redirect_uri={redirect_uri}&state={state}'
        )
        return redirect(auth_url)

    @app.route('/login/naver/callback')
    def naver_callback():
        if request.args.get('error'):
            flash('네이버 로그인이 취소되었습니다.', 'info')
            return redirect(url_for('login'))
        code = request.args.get('code')
        state = request.args.get('state')
        if not code or not state or state != session.pop('naver_oauth_state', None):
            flash('네이버 로그인 요청이 올바르지 않습니다. 다시 시도해주세요.', 'danger')
            return redirect(url_for('login'))
        client_id = os.environ.get('NAVER_CLIENT_ID')
        client_secret = os.environ.get('NAVER_CLIENT_SECRET')
        redirect_uri = url_for('naver_callback', _external=True)
        try:
            token_res = requests.get(
                'https://nid.naver.com/oauth2.0/token',
                params={
                    'grant_type': 'authorization_code',
                    'client_id': client_id,
                    'client_secret': client_secret,
                    'code': code,
                    'state': state,
                    'redirect_uri': redirect_uri,
                },
                timeout=10,
            )
            token_data = token_res.json()
            access_token = token_data.get('access_token')
            if not access_token:
                raise ValueError(f'토큰 발급 실패: {token_data}')
            profile_res = requests.get(
                'https://openapi.naver.com/v1/nid/me',
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=10,
            )
            profile = profile_res.json().get('response') or {}
            naver_id = profile.get('id')
            if not naver_id:
                raise ValueError(f'프로필 조회 실패: {profile_res.text}')
        except Exception as e:
            app.logger.error(f'네이버 로그인 실패: {e}')
            flash('네이버 로그인 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.', 'danger')
            return redirect(url_for('login'))
        display_name = profile.get('name') or profile.get('nickname')
        _login_or_create('naver', naver_id, display_name)
        return redirect(url_for('mypage'))

    # ---------------- 카카오 로그인 ----------------
    @app.route('/login/kakao')
    def kakao_login():
        if current_user.is_authenticated:
            return redirect(url_for('home'))
        client_id = os.environ.get('KAKAO_REST_API_KEY')
        if not client_id:
            flash('카카오 로그인이 아직 설정되지 않았습니다. 관리자에게 문의해주세요.', 'danger')
            return redirect(url_for('login'))
        state = secrets.token_urlsafe(16)
        session['kakao_oauth_state'] = state
        redirect_uri = url_for('kakao_callback', _external=True)
        auth_url = (
            'https://kauth.kakao.com/oauth/authorize'
            f'?response_type=code&client_id={client_id}'
            f'&redirect_uri={redirect_uri}&state={state}'
        )
        return redirect(auth_url)

    @app.route('/login/kakao/callback')
    def kakao_callback():
        if request.args.get('error'):
            flash('카카오 로그인이 취소되었습니다.', 'info')
            return redirect(url_for('login'))
        code = request.args.get('code')
        state = request.args.get('state')
        if not code or not state or state != session.pop('kakao_oauth_state', None):
            flash('카카오 로그인 요청이 올바르지 않습니다. 다시 시도해주세요.', 'danger')
            return redirect(url_for('login'))
        client_id = os.environ.get('KAKAO_REST_API_KEY')
        client_secret = os.environ.get('KAKAO_CLIENT_SECRET')  # 선택 사항 (활성화했다면)
        redirect_uri = url_for('kakao_callback', _external=True)
        try:
            data = {
                'grant_type': 'authorization_code',
                'client_id': client_id,
                'redirect_uri': redirect_uri,
                'code': code,
            }
            if client_secret:
                data['client_secret'] = client_secret
            token_res = requests.post(
                'https://kauth.kakao.com/oauth/token',
                data=data,
                headers={'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8'},
                timeout=10,
            )
            token_data = token_res.json()
            access_token = token_data.get('access_token')
            if not access_token:
                raise ValueError(f'토큰 발급 실패: {token_data}')
            profile_res = requests.get(
                'https://kapi.kakao.com/v2/user/me',
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=10,
            )
            profile = profile_res.json()
            kakao_id = profile.get('id')
            if not kakao_id:
                raise ValueError(f'프로필 조회 실패: {profile_res.text}')
        except Exception as e:
            app.logger.error(f'카카오 로그인 실패: {e}')
            flash('카카오 로그인 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.', 'danger')
            return redirect(url_for('login'))
        kakao_account = profile.get('kakao_account') or {}
        kakao_profile = kakao_account.get('profile') or {}
        display_name = kakao_profile.get('nickname')
        _login_or_create('kakao', kakao_id, display_name)
        return redirect(url_for('mypage'))
