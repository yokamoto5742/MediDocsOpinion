import secrets

def generate_csrf_secret():
    return secrets.token_hex(32)

if __name__ == "__main__":
    secret_key = generate_csrf_secret()
    print(f"CSRF_SECRET_KEY={secret_key}")