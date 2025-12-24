import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.security import get_password_hash

def rehash_users_data():
    """Re-hash passwords ในไฟล์ users.json"""
    
    users_file = Path("app/data/users.json")
    
    if not users_file.exists():
        print("users.json not found!")
        return
    
    # อ่านข้อมูล
    with open(users_file, 'r', encoding='utf-8') as f:
        users = json.load(f)
    
    # Re-hash passwords
    print("Re-hashing passwords...\n")
    
    for user in users:
        username = user.get('username')
        # สมมติว่า password เดิมคือ "password123" สำหรับทุกคน
        new_hash = get_password_hash("password123")
        user['hashed_password'] = new_hash
        print(f"Updated: {username}")
    
    # บันทึกกลับ
    with open(users_file, 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=2, ensure_ascii=False)
    
    print("\nAll passwords re-hashed successfully!")
    print("Default password for all users: password123")

if __name__ == "__main__":
    rehash_users_data()