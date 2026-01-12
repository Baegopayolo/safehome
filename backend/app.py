"""Flask 애플리케이션 메인 파일 - 순수 라우팅 허브"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_cors import CORS
import os

app = Flask(__name__, template_folder='../frontend', static_folder='../static')
CORS(app)
os.environ['TZ'] = 'Asia/Seoul'
app.config['SECRET_KEY'] = 'your_very_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
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

from routes import pages, auth, api
pages.register_page_routes(app)
auth.register_auth_routes(app, db, bcrypt)
api.register_api_routes(app, db)

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
