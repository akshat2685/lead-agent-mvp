import os
import jwt
import bcrypt
from datetime import datetime, timedelta
from .db import get_session
from .models import User

JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-key-change-in-prod")
JWT_ALGORITHM = "HS256"

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def generate_token(user_id: int, role: str, expires_in_hours: int = 24) -> str:
    payload = {
        "sub": user_id,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=expires_in_hours)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def authenticate_user(email: str, password: str) -> dict:
    session = get_session()
    try:
        user = session.query(User).filter(User.email == email).first()
        if user and verify_password(password, user.password_hash):
            token = generate_token(user.id, user.role)
            return {"token": token, "user": {"id": user.id, "email": user.email, "role": user.role}}
        return None
    finally:
        session.close()

def create_initial_admin():
    session = get_session()
    try:
        if not session.query(User).first():
            admin = User(email="admin@edysor.ai", password_hash=hash_password("admin123"), role="admin")
            session.add(admin)
            session.commit()
    finally:
        session.close()
