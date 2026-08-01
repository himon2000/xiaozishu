"""
FastAPI 依赖注入（认证守卫、角色权限）

支持两种认证模式：
1. 普通 HTTP 调用：使用 Authorization: Bearer <JWT> 头
2. 微信云托管内网调用：读取 X-WX-OPENID 头（由微信平台自动注入，无需验证）
"""
from fastapi import Depends, HTTPException, status, Request, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
import uuid
from utils.db import get_db
from utils.jwt_utils import decode_token
from models import User

security = HTTPBearer(auto_error=False)


def _get_openid_from_wx_header(request: Request) -> Optional[str]:
    """
    从微信云托管内网调用自动注入的 header 中读取 openid
    header 名称: X-WX-OPENID（官方文档标准字段）
    只有经过微信平台验证的内网请求才会携带此 header，可完全信任
    """
    return request.headers.get("X-WX-OPENID") or request.headers.get("x-wx-openid")


def _get_or_create_user_by_openid(openid: str, db: Session) -> User:
    """根据 openid 查找用户，不存在则自动创建"""
    user = db.query(User).filter(User.openid == openid).first()
    if user and user.status == "deleted":
        raise HTTPException(status_code=403, detail="账号已注销，请重新登录后启用")
    if not user:
        from services import wechat_auth as wx_auth
        user = User(
            id=f"U{uuid.uuid4().hex[:10].upper()}",
            openid=openid,
            nickname=f"散修{uuid.uuid4().hex[:4]}",
            role="seeker",
            referral_code=wx_auth.generate_referral_code(),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """获取当前用户（可选，未登录也返回None）"""
    # 优先：微信云托管内网 header
    wx_openid = _get_openid_from_wx_header(request)
    if wx_openid:
        return _get_or_create_user_by_openid(wx_openid, db)

    # 降级：JWT Bearer token
    if not credentials:
        return None
    payload = decode_token(credentials.credentials)
    if not payload:
        return None
    return db.query(User).filter(User.openid == payload["sub"]).first()


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """获取当前用户（必须登录）"""
    # 优先：微信云托管内网 header（完全可信）
    wx_openid = _get_openid_from_wx_header(request)
    if wx_openid:
        return _get_or_create_user_by_openid(wx_openid, db)

    # 降级：JWT Bearer token
    if not credentials:
        raise HTTPException(status_code=401, detail="请先登录")
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Token无效或已过期")
    user = db.query(User).filter(User.openid == payload["sub"]).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


def require_role(*roles: str):
    """
    角色权限装饰器工厂
    支持新旧两种角色系统
    """
    def checker(user: User = Depends(get_current_user)) -> User:
        # 新系统检查
        enabled = user.enabled_roles or []
        if any(r in enabled for r in roles):
            return user
        # 旧系统兼容
        if user.role in roles:
            return user
        raise HTTPException(status_code=403, detail="权限不足")
    return checker


def require_certified(user: User = Depends(get_current_user)) -> User:
    """要求用户已完成认证"""
    if user.cert_status != "verified":
        raise HTTPException(status_code=403, detail="请先完成身份认证")
    return user


def require_provider(user: User = Depends(get_current_user)) -> User:
    """
    要求用户具备服务提供资格（大虾/长老/执事）
    支持新旧两种角色系统：
    - 旧系统：user.role
    - 新系统：user.enabled_roles
    """
    # 新系统优先检查
    enabled_roles = user.enabled_roles or []
    if "provider" in enabled_roles or "elder" in enabled_roles or "admin" in enabled_roles:
        return user
    # 旧系统兼容检查
    if user.role in ("provider", "elder", "admin"):
        return user
    raise HTTPException(status_code=403, detail="您暂无服务提供资格，请先解锁「🍠 大虾」或「🏛️ 长老」角色")
