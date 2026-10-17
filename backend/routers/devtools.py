"""
运维工具路由（/api/v1/dev/*）

用途：无法直连云托管内网 MySQL 时，通过带令牌的 HTTP 接口完成用户角色指派等运维操作。
安全：必须在环境变量中配置 DEV_ADMIN_TOKEN 后整组接口才启用，未配置时一律 404。
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from config import get_settings
from models import User, UserRole
from utils.db import get_db
from services import role_service

router = APIRouter(prefix="/api/v1/dev", tags=["运维工具"])


def verify_dev_token(x_dev_token: str = Header(default="", alias="X-Dev-Token")) -> None:
    settings = get_settings()
    if not settings.dev_admin_token:
        raise HTTPException(status_code=404, detail="dev tools disabled")
    if not x_dev_token or x_dev_token != settings.dev_admin_token:
        raise HTTPException(status_code=401, detail="invalid dev token")


def _user_brief(u: User) -> dict:
    return {
        "openid": u.openid,
        "nickname": u.nickname,
        "role": u.role,
        "enabled_roles": u.enabled_roles or [],
        "current_role": u.current_role,
        "cert_status": u.cert_status,
        "school": u.school,
        "status": u.status,
        "created_at": u.created_at.isoformat() if u.created_at else "",
    }


class AssignRoleRequest(BaseModel):
    identifier: str = Field(..., description="openid 或昵称（昵称支持模糊匹配）")
    role: str = Field(..., pattern="^(seeker|provider|elder|admin)$")
    exact: bool = Field(default=False, description="True 时昵称必须完全相等")


# ── 接口 ────────────────────────────────────────────────

@router.get("/ping")
def ping(_: None = Depends(verify_dev_token)):
    settings = get_settings()
    return {
        "status": "ok",
        "environment": settings.environment,
        "presets": settings.dev_role_presets,
    }


@router.get("/users", response_model=List[dict])
def search_users(
    q: str = Query(default="", description="昵称关键字或 openid"),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: None = Depends(verify_dev_token),
):
    """按昵称/openid 搜索用户"""
    query = db.query(User)
    if q:
        query = query.filter(or_(User.nickname.like(f"%{q}%"), User.openid == q))
    users = query.order_by(User.created_at.desc()).limit(limit).all()
    return [_user_brief(u) for u in users]


@router.post("/assign-role")
def assign_role(
    req: AssignRoleRequest,
    db: Session = Depends(get_db),
    _: None = Depends(verify_dev_token),
):
    """强制指派角色（跳过解锁条件），identifier 可为 openid 或昵称"""
    key = req.identifier.strip()
    if not key:
        raise HTTPException(status_code=400, detail="identifier 不能为空")

    user = db.query(User).filter(User.openid == key).first()
    if not user:
        if req.exact:
            user = db.query(User).filter(User.nickname == key).first()
        else:
            candidates = db.query(User).filter(User.nickname.like(f"%{key}%")).all()
            if len(candidates) > 1:
                return {
                    "success": False,
                    "detail": "昵称匹配到多个用户，请使用 openid 或开启 exact",
                    "candidates": [_user_brief(u) for u in candidates],
                }
            user = candidates[0] if candidates else None

    if not user:
        raise HTTPException(status_code=404, detail=f"未找到用户：{key}")

    role_service.force_assign_role(db, user, req.role, reason="管理员指派")
    db.refresh(user)

    return {
        "success": True,
        "role": req.role,
        "role_name": role_service.ROLE_CONFIG.get(req.role, {}).get("name", req.role),
        "user": _user_brief(user),
        "roles": role_service.get_user_roles(db, user.openid),
    }


@router.get("/presets")
def list_presets(
    db: Session = Depends(get_db),
    _: None = Depends(verify_dev_token),
):
    """查看开发者角色预置名单及其匹配情况"""
    raw = get_settings().dev_role_presets
    items = []
    for key, role in role_service.parse_role_presets(raw):
        matched = db.query(User).filter(
            or_(User.nickname.like(f"%{key}%"), User.openid == key)
        ).all()
        items.append({
            "key": key,
            "role": role,
            "role_name": role_service.ROLE_CONFIG.get(role, {}).get("name", role),
            "matched": [_user_brief(u) for u in matched],
        })
    return {"raw": raw, "items": items}


@router.post("/apply-presets")
def apply_presets(
    db: Session = Depends(get_db),
    _: None = Depends(verify_dev_token),
):
    """对库中已有用户批量应用预置名单（新登录用户会即时自动应用，此接口用于存量用户）"""
    raw = get_settings().dev_role_presets
    results = []
    for key, role in role_service.parse_role_presets(raw):
        users = db.query(User).filter(
            or_(User.nickname.like(f"%{key}%"), User.openid == key)
        ).all()
        for u in users:
            applied = role_service.apply_dev_role_presets(db, u)
            results.append({
                "key": key,
                "openid": u.openid,
                "nickname": u.nickname,
                "applied": applied,
                "role": u.role,
                "enabled_roles": u.enabled_roles or [],
            })
    return {"success": True, "results": results}


@router.get("/user/{openid}/roles")
def user_roles(
    openid: str,
    db: Session = Depends(get_db),
    _: None = Depends(verify_dev_token),
):
    """查看指定用户的完整角色明细"""
    user = db.query(User).filter(User.openid == openid).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    rows: Optional[List[UserRole]] = db.query(UserRole).filter(
        UserRole.user_openid == openid
    ).all()
    return {
        "user": _user_brief(user),
        "roles": role_service.get_user_roles(db, openid),
        "user_role_rows": [
            {
                "role": r.role,
                "status": r.status,
                "level": r.level,
                "verified": r.verified,
                "unlock_condition": r.unlock_condition,
                "total_services_published": r.total_services_published,
            }
            for r in (rows or [])
        ],
    }
