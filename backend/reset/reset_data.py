"""
데이터베이스 초기화 스크립트
- 모든 사용자 데이터 삭제
- 테스트 계정과 샘플 데이터 재생성
"""
from app import app, db
import os

def reset_database():
    with app.app_context():
        print("=" * 60)
        print("데이터베이스 초기화 중...")
        print("=" * 60)
        
        # 데이터베이스 파일 경로
        db_path = os.path.join(os.path.dirname(__file__), 'instance', 'site.db')
        
        if os.path.exists(db_path):
            print(f"\n✓ 기존 데이터베이스 발견: {db_path}")
            
            # 데이터베이스 삭제
            try:
                os.remove(db_path)
                print("✓ 기존 데이터베이스 삭제 완료")
            except Exception as e:
                print(f"✗ 삭제 실패: {e}")
                print("  서버를 종료한 후 다시 시도하세요.")
                return False
        
        # 새 데이터베이스 생성
        try:
            db.create_all()
            print("✓ 새 데이터베이스 생성 완료")
        except Exception as e:
            print(f"✗ 생성 실패: {e}")
            return False
        
        print("\n" + "=" * 60)
        print("✅ 초기화 완료!")
        print("=" * 60)
        print("\n다음 명령어로 샘플 데이터를 생성하세요:")
        print("  python seed_data.py")
        print("\n또는 모두 한번에 실행:")
        print("  python reset_data.py && python seed_data.py")
        
        return True

if __name__ == '__main__':
    reset_database()
