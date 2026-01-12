"""
기존 사용자 비밀번호 재설정 스크립트
기존 사용자의 비밀번호를 새로운 해시로 업데이트합니다.
"""
from app import app, db, User
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()

def reset_user_password(username, new_password):
    """특정 사용자의 비밀번호를 재설정"""
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if not user:
            print(f"❌ 사용자 '{username}'를 찾을 수 없습니다.")
            return False
        
        hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        print(f"✓ 사용자 '{username}'의 비밀번호가 성공적으로 재설정되었습니다.")
        return True

def reset_all_passwords():
    """모든 사용자의 비밀번호를 기본값으로 재설정 (주의: 테스트용)"""
    with app.app_context():
        users = User.query.all()
        default_password = 'test123'
        
        for user in users:
            hashed_password = bcrypt.generate_password_hash(default_password).decode('utf-8')
            user.password = hashed_password
            print(f"✓ {user.username}의 비밀번호 재설정")
        
        db.session.commit()
        print(f"\n✓ 총 {len(users)}명의 사용자 비밀번호가 '{default_password}'로 재설정되었습니다.")

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == '--all':
            print("⚠️  모든 사용자 비밀번호를 재설정합니다...")
            reset_all_passwords()
        elif len(sys.argv) == 3:
            username = sys.argv[1]
            new_password = sys.argv[2]
            reset_user_password(username, new_password)
        else:
            print("사용법:")
            print("  python reset_password.py <username> <new_password>")
            print("  python reset_password.py --all  # 모든 사용자를 test123으로 재설정")
    else:
        print("사용법:")
        print("  python reset_password.py <username> <new_password>")
        print("  python reset_password.py --all  # 모든 사용자를 test123으로 재설정")

