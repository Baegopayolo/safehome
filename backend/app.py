"""Flask 애플리케이션 메인 파일 - 순수 라우팅 허브"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
import os

app = Flask(__name__, template_folder='../frontend', static_folder='../static')
if os.getenv('TRUST_NGINX_PROXY') == '1':
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
CORS(app)
os.environ['TZ'] = 'Asia/Seoul'
secret_key = os.getenv('SECRET_KEY')
if not secret_key or not secret_key.strip() or secret_key.strip() in {
    'your_very_secret_key',
    'your_secret_key_here',
    'replace-with-your-existing-production-secret',
}:
    raise RuntimeError('SECRET_KEY must be set to a private secret before starting SafeHome.')
app.config['SECRET_KEY'] = secret_key
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///site.db')
app.config['DASHBOARD_STALE_HOURS'] = int(os.getenv('DASHBOARD_STALE_HOURS', '192'))
app.config['DASHBOARD_RECENT_STALE_HOURS'] = int(os.getenv('DASHBOARD_RECENT_STALE_HOURS', '36'))
app.config['DASHBOARD_LOCK_PATH'] = os.getenv('DASHBOARD_LOCK_PATH')
db = SQLAlchemy(app)
migrate = Migrate(app, db)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
import models
model_classes = models.init_models(db)
User = model_classes['User']
SearchHistory = model_classes['SearchHistory']
Favorite = model_classes['Favorite']
Review = model_classes['Review']
Report = model_classes['Report']
Notification = model_classes['Notification']
RealTransaction = model_classes['RealTransaction']
HeatmapData = model_classes['HeatmapData']
models.User = User
models.SearchHistory = SearchHistory
models.Favorite = Favorite
models.Review = Review
models.Report = Report
models.Notification = Notification
models.RealTransaction = RealTransaction
models.HeatmapData = HeatmapData

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

from routes import pages, auth, api, oauth
pages.register_page_routes(app)
auth.register_auth_routes(app, db, bcrypt)
api.register_api_routes(app, db)
oauth.register_oauth_routes(app, db, bcrypt)
from dashboard import register_dashboard
register_dashboard(app, db)

# Schema changes are explicit: run flask db upgrade before starting the app.

if __name__ == '__main__':
    app.run(debug=True)
