"""
JWT 工具
"""
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from config import get_settings

settings = get_settings()


def create_access_token(openid: str, role: str, expires_delta: timedelta = None) -> str:
    """创建 JWT Access Token"""
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload = {
        "sub": openid,
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict | None:
    """解码 JWT Token"""
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
