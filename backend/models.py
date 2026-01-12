"""데이터베이스 모델 정의"""
from flask_login import UserMixin

db = None

def _get_kst_now():
    from datetime import datetime, timezone, timedelta
    kst = timezone(timedelta(hours=9))
    return datetime.now(kst).replace(tzinfo=None)

def init_models(database):
    global db
    db = database
    class User(db.Model, UserMixin):
        id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String(64), unique=True, nullable=False)
        password = db.Column(db.String(128), nullable=False)
        email = db.Column(db.String(120), unique=True, nullable=True)
        created_at = db.Column(db.DateTime, default=_get_kst_now)
        search_history = db.relationship('SearchHistory', backref='user', lazy=True)
        favorites = db.relationship('Favorite', backref='user', lazy=True)
        reviews = db.relationship('Review', backref='user', lazy=True)
        reports = db.relationship('Report', backref='user', lazy=True)
        def __repr__(self):
            return f"User('{self.username}')"
    class SearchHistory(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
        region = db.Column(db.String(100), nullable=False)
        search_date = db.Column(db.DateTime, default=_get_kst_now)
        risk_score = db.Column(db.Integer, nullable=True)
    class Favorite(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        region = db.Column(db.String(100), nullable=False)
        created_at = db.Column(db.DateTime, default=_get_kst_now)
    class Review(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        region = db.Column(db.String(100), nullable=False)
        rating = db.Column(db.Integer, nullable=False)
        content = db.Column(db.Text, nullable=True)
        created_at = db.Column(db.DateTime, default=_get_kst_now)
    class Report(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        region = db.Column(db.String(100), nullable=False)
        property_address = db.Column(db.String(200), nullable=True)
        report_type = db.Column(db.String(50), nullable=False)
        description = db.Column(db.Text, nullable=True)
        status = db.Column(db.String(20), default='pending')
        created_at = db.Column(db.DateTime, default=_get_kst_now)
    class Notification(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
        title = db.Column(db.String(200), nullable=False)
        message = db.Column(db.Text, nullable=False)
        type = db.Column(db.String(50), nullable=False)
        is_read = db.Column(db.Boolean, default=False)
        created_at = db.Column(db.DateTime, default=_get_kst_now)
    class RealTransaction(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        lawd_cd = db.Column(db.String(10), nullable=False, index=True)
        deal_ymd = db.Column(db.String(6), nullable=False, index=True)
        region = db.Column(db.String(100), nullable=True, index=True)
        dong = db.Column(db.String(100), nullable=True)
        apt_name = db.Column(db.String(200))
        dong_name = db.Column(db.String(100))
        price = db.Column(db.Integer)
        price_raw = db.Column(db.String(50))
        area = db.Column(db.String(50))
        floor = db.Column(db.String(20))
        build_year = db.Column(db.String(10))
        deal_date = db.Column(db.String(20))
        jibun = db.Column(db.String(50))
        region_code = db.Column(db.String(10))
        created_at = db.Column(db.DateTime, default=_get_kst_now)
        updated_at = db.Column(db.DateTime, default=_get_kst_now, onupdate=lambda: _get_kst_now())
        __table_args__ = (db.Index('idx_lawd_deal', 'lawd_cd', 'deal_ymd'),)
    class HeatmapData(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        region = db.Column(db.String(100), nullable=False, unique=True, index=True)
        score = db.Column(db.Integer, nullable=False)
        lat = db.Column(db.Float, nullable=False)
        lng = db.Column(db.Float, nullable=False)
        created_at = db.Column(db.DateTime, default=_get_kst_now)
        updated_at = db.Column(db.DateTime, default=_get_kst_now, onupdate=lambda: _get_kst_now())
    return {
        'User': User,
        'SearchHistory': SearchHistory,
        'Favorite': Favorite,
        'Review': Review,
        'Report': Report,
        'Notification': Notification,
        'RealTransaction': RealTransaction,
        'HeatmapData': HeatmapData
    }
