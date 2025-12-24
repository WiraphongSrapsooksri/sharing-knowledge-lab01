import hashlib

def generate_hash(password: str) -> str:
    """สร้าง SHA256 hash"""
    return hashlib.sha256(password.encode()).hexdigest()

if __name__ == "__main__":
    passwords = {
        "admin123": generate_hash("admin123"),
        "password123": generate_hash("password123"),
        "test123": generate_hash("test123"),
    }
    
    print("=== Password Hashes ===\n")
    for pwd, hash_val in passwords.items():
        print(f"Password: {pwd}")
        print(f"Hash: {hash_val}\n")