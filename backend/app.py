from flask import Flask, jsonify, request, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_cors import CORS # 1. flask_cors를 import 합니다.
import json
# from datetime import datetime, timezone
# import requests
# from bs4 import BeautifulSoup

app = Flask(__name__, template_folder='../frontend', static_folder='../static') #template_folder를 frontend로 지정
CORS(app) # 2. CORS를 app에 적용합니다. 이 한 줄이 허용 규칙을 추가하는 코드입니다.

# --- ▼▼▼ 로그인 기능 설정 추가 ▼▼▼ ---

# 데이터베이스 설정
app.config['SECRET_KEY'] = 'your_very_secret_key' # 실제 서비스에서는 절대 노출되면 안 되는 키
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db' # SQLite DB를 사용
db = SQLAlchemy(app)
migrate = Migrate(app, db)
bcrypt = Bcrypt(app)

# 로그인 매니저 설정
login_manager = LoginManager(app)
login_manager.login_view = 'login' # 로그인 안 한 사용자가 @login_required 페이지 접근 시 'login' 함수로 리디렉션
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 사용자 모델(DB 테이블) 정의
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)

    def __repr__(self):
        return f"User('{self.username}')"
    

# --- ▼▼▼ 기존 API 라우트 ▼▼▼ ---

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/map')
def map_page():
    return render_template('map.html')

@app.route('/scanner')
def scanner_page():
    return render_template('scanner.html')


@app.route('/searchscan')
def searchscan_page():
    return render_template('searchscan.html')

@app.route('/scam-types')
def scam_types_page():
    return render_template('scam-types.html')

@app.route('/about')
def about_page():
    return render_template('about.html')

@app.route('/self-check')
def self_check_page():
    return render_template('self-check.html')

@app.route('/faq')
def faq_page():
    return render_template('faq.html')

@app.route('/heatmap')
def get_heatmap_data():
    # (실제로는 DB에서 데이터를 조회하는 로직)
    # 지금은 테스트를 위해 미리 만들어 둔 데이터를 반환
    heatmap_data = [
        # 강남구 (안전)
        {"region": "대치동", "score": 25, "lat": 37.4944, "lng": 127.0628},
        {"region": "압구정동", "score": 22, "lat": 37.5273, "lng": 127.0285},
        {"region": "청담동", "score": 31, "lat": 37.5244, "lng": 127.0468},

        # 강서구 (위험)
        {"region": "화곡동", "score": 92, "lat": 37.5410, "lng": 126.8402},
        {"region": "등촌동", "score": 78, "lat": 37.5599, "lng": 126.8533},
        {"region": "마곡동", "score": 65, "lat": 37.5606, "lng": 126.8248},

        # 마포구 (주의)
        {"region": "연남동", "score": 68, "lat": 37.5623, "lng": 126.9250},
        {"region": "서교동", "score": 71, "lat": 37.5562, "lng": 126.9221},
        {"region": "성산동", "score": 55, "lat": 37.5714, "lng": 126.9118},

        # 종로구 (양호)
        {"region": "사직동", "score": 45, "lat": 37.5765, "lng": 126.9689},
        {"region": "삼청동", "score": 41, "lat": 37.5833, "lng": 126.9806},
        {"region": "혜화동", "score": 58, "lat": 37.5857, "lng": 127.0018},

        # 금천구 (위험)
        {"region": "독산동", "score": 85, "lat": 37.4695, "lng": 126.8953},
        {"region": "가산동", "score": 76, "lat": 37.4764, "lng": 126.8843}
    ]
    return jsonify(heatmap_data)

@app.route('/analyze')
def analyze():
    region = request.args.get('region', '').strip()
    if not region:
        return jsonify({'error': '지역명을 입력하세요'}), 400
    
    # 크롤링 또는 DB에서 매물 데이터 가져오기 (예시)
    properties = fetch_properties_by_region(region)
    
    # 각 매물에 대해 위험 요소 분석
    analyzed = []
    for prop in properties:
        warnings = analyze_property_warnings(prop)
        checklist = generate_safety_checklist(prop)
        analyzed.append({
            'name': prop.get('name', '매물명'),
            'warnings': warnings,
            'checklist': checklist
        })
    
    return jsonify({'properties': analyzed})

def fetch_properties_by_region(region):
    """실제 크롤링 또는 DB 조회 로직"""
    # 예시: 네이버 부동산, 직방 등에서 크롤링
    # 여기서는 샘플 데이터 반환
    return [
        {'name': f'{region} A빌라', 'address': region, 'price': '1억'},
        {'name': f'{region} B아파트', 'address': region, 'price': '2억'},
    ]

def analyze_property_warnings(prop):
    """매물 위험 요소 분석"""
    warnings = []
    # 예: 가격, 건물 연한, 주변 환경 등 체크
    # 샘플
    if '빌라' in prop.get('name', ''):
        warnings.append('빌라는 전세사기 위험이 높습니다')
    if int(prop.get('price', '0억').replace('억','')) < 1.5:
        warnings.append('시세보다 낮은 가격 주의')
    return warnings

def generate_safety_checklist(prop):
    """안전 계약 체크리스트 생성"""
    return [
        '등기부등본 확인',
        '건축물대장 확인',
        '임대인 신분증 확인',
        '선순위 세입자 확인',
        '집주인 세금 체납 조회'
    ]

# --- 로그인/회원가입/마이페이지 라우트 추가 ---

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
            return redirect(url_for('mypage'))
        else:
            flash('로그인에 실패했습니다. 아이디와 비밀번호를 확인해주세요.', 'danger')
    return render_template('Login/login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/mypage')
@login_required # 이 데코레이터가 붙은 페이지는 반드시 로그인해야만 접근 가능
def mypage():
    return render_template('mypage.html', username=current_user.username)


# --- 데이터베이스 초기화 ---
# 처음 실행 시 한 번만 DB를 생성하기 위한 코드
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)