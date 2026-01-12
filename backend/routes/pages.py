"""페이지 라우트 핸들러"""
from flask import render_template
import os

def register_page_routes(app):
    @app.route('/')
    def home():
        return render_template('index.html')
    @app.route('/map')
    def map_page():
        kakao_key = os.environ.get('KAKAO_APP_KEY', '')
        return render_template('map.html', kakao_app_key=kakao_key)
    @app.route('/searchscan')
    def searchscan_page():
        return render_template('searchscan.html')
    @app.route('/scam-types')
    def scam_types_page():
        return render_template('scam-types.html')
    @app.route('/about')
    def about_page():
        return render_template('about.html')
    @app.route('/intro')
    def intro_page():
        return render_template('intro.html')
    @app.route('/self-check')
    def selfcheck_page():
        return render_template('self-check.html')
    @app.route('/faq')
    def faq_page():
        return render_template('faq.html')
    @app.route('/reviews')
    def reviews_page():
        return render_template('reviews.html')
