"""
마이페이지 테스트를 위한 샘플 데이터 생성 스크립트
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User, SearchHistory, Favorite, Notification, Report
from flask_bcrypt import Bcrypt
from datetime import datetime, timedelta

bcrypt = Bcrypt(app)

def seed_data():
    with app.app_context():
        # 기존 데이터 삭제 (옵션)
        # db.drop_all()
        # db.create_all()
        
        # 테스트 사용자 생성 (이미 있으면 건너뛰기)
        test_user = User.query.filter_by(username='test').first()
        if not test_user:
            hashed_password = bcrypt.generate_password_hash('test123').decode('utf-8')
            test_user = User(username='test', password=hashed_password, email='test@example.com')
            db.session.add(test_user)
            db.session.commit()
            print("✓ 테스트 사용자 생성 완료 (아이디: test, 비밀번호: test123)")
        else:
            print("✓ 테스트 사용자가 이미 존재합니다 (기존 데이터에 추가합니다)")
        
        # 즐겨찾기 샘플 데이터
        favorite_regions = [
            '서울 강남구 대치동',
            '서울 마포구 연남동',
            '서울 강서구 화곡동',
            '서울 종로구 삼청동',
            '서울 금천구 독산동'
        ]
        
        for region in favorite_regions:
            existing = Favorite.query.filter_by(user_id=test_user.id, region=region).first()
            if not existing:
                fav = Favorite(
                    user_id=test_user.id,
                    region=region,
                    created_at=datetime.now() - timedelta(days=len(favorite_regions) - favorite_regions.index(region))
                )
                db.session.add(fav)
        
        # 검색 히스토리 샘플 데이터
        search_queries = [
            ('서울 강남구 역삼동', 45),
            ('서울 송파구 잠실동', 62),
            ('서울 용산구 이촌동', 38),
            ('서울 서초구 반포동', 51),
            ('서울 영등포구 여의도동', 55),
            ('서울 동작구 사당동', 68),
            ('서울 관악구 신림동', 72)
        ]
        
        for i, (query, risk_score) in enumerate(search_queries):
            existing = SearchHistory.query.filter_by(user_id=test_user.id, region=query).first()
            if not existing:
                history = SearchHistory(
                    user_id=test_user.id,
                    region=query,
                    risk_score=risk_score,
                    search_date=datetime.now() - timedelta(hours=len(search_queries) - i)
                )
                db.session.add(history)
        
        # 알림은 실제 데이터 기반으로 자동 생성됩니다 (api.py의 generate_real_notifications 함수)
        
        # 신고 샘플 데이터
        reports_data = [
            {
                'region': '서울 강서구 화곡동',
                'property_address': '화곡동 123-45 ABC빌라 301호',
                'report_type': 'suspicious',
                'description': '시세보다 현저히 낮은 가격으로 급매물로 올라왔습니다',
                'status': 'investigating'
            },
            {
                'region': '서울 금천구 독산동',
                'property_address': '독산동 678-90 XYZ오피스텔 502호',
                'report_type': 'scam',
                'description': '임대인이 다중채무자로 확인되었습니다',
                'status': 'resolved'
            }
        ]
        
        for i, report_data in enumerate(reports_data):
            report = Report(
                user_id=test_user.id,
                region=report_data['region'],
                property_address=report_data['property_address'],
                report_type=report_data['report_type'],
                description=report_data['description'],
                status=report_data['status'],
                created_at=datetime.now() - timedelta(days=i * 3)
            )
            db.session.add(report)
        
        db.session.commit()
        print("✓ 샘플 데이터 생성 완료!")
        print("\n=== 테스트 계정 정보 ===")
        print("아이디: test")
        print("비밀번호: test123")
        print("\n마이페이지에서 다음 데이터를 확인할 수 있습니다:")
        print(f"- 즐겨찾기: {len(favorite_regions)}개")
        print(f"- 검색 히스토리: {len(search_queries)}개")
        print(f"- 알림: 실제 데이터 기반으로 자동 생성됩니다")
        print(f"- 신고: {len(reports_data)}개")

if __name__ == '__main__':
    seed_data()
