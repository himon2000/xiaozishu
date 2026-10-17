"""
运维工具路由（/api/v1/dev/*）

用途：无法直连云托管内网 MySQL 时，通过带令牌的 HTTP 接口完成用户角色指派等运维操作。
安全：必须在环境变量中配置 DEV_ADMIN_TOKEN 后整组接口才启用，未配置时一律 404。
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from config import get_settings
from models import User, UserRole
from utils.db import get_db
from services import role_service

router = APIRouter(prefix="/api/v1/dev", tags=["运维工具"])


def verify_dev_token(
    request: Request,
    x_dev_token: str = Header(default="", alias="X-Dev-Token"),
) -> None:
    """
    鉴权满足其一即可：
      1. X-Dev-Token 等于环境变量 DEV_ADMIN_TOKEN（两端 strip，容忍误粘贴空格）
      2. 云托管内网调用且 X-WX-OPENID 落在 DEV_ADMIN_OPENIDS 白名单
    """
    settings = get_settings()
    token = (settings.dev_admin_token or "").strip()
    openids = [o.strip() for o in (settings.dev_admin_openids or "").split(",") if o.strip()]

    if not token and not openids:
        raise HTTPException(status_code=404, detail="dev tools disabled")

    if token and (x_dev_token or "").strip() == token:
        return

    wx_openid = request.headers.get("X-WX-OPENID") or request.headers.get("x-wx-openid") or ""
    if wx_openid and wx_openid in openids:
        return

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


class ServicePatch(BaseModel):
    """服务修补：ref 可为服务 id 或标题关键字（模糊且需唯一）"""
    ref: str = Field(..., description="服务 id 或标题关键字")
    cover_image: Optional[str] = Field(default=None, description="封面图 URL，留空不修改")
    status: Optional[str] = Field(default=None, pattern="^(on_sale|off_sale|reviewing|rejected)$")
    title: Optional[str] = None
    description: Optional[str] = None


class CopyCoverRequest(BaseModel):
    from_ref: str = Field(..., description="封面来源：服务 id 或标题关键字")
    to_ref: str = Field(..., description="封面目标：服务 id 或标题关键字")


def _find_service(db: Session, ref: str):
    """按 id 精确匹配，否则按标题模糊匹配（多条则报错，避免误改）"""
    from models import Service
    svc = db.query(Service).filter(Service.id == ref).first()
    if svc:
        return svc, None
    rows = db.query(Service).filter(Service.title.like(f"%{ref}%")).all()
    if len(rows) > 1:
        return None, [{"id": r.id, "title": r.title, "provider": r.provider_openid} for r in rows]
    return (rows[0] if rows else None), None


def _service_brief(s) -> dict:
    return {
        "id": s.id,
        "title": s.title,
        "provider_openid": s.provider_openid,
        "status": s.status,
        "cover_image": s.cover_image or "",
        "created_at": s.created_at.isoformat() if s.created_at else "",
    }


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


# ── 服务内容运维 ────────────────────────────────────────

@router.get("/services", response_model=List[dict])
def list_services(
    q: str = Query(default="", description="标题关键字"),
    provider: str = Query(default="", description="服务者 openid"),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: None = Depends(verify_dev_token),
):
    """列出服务，用于核对封面/状态等线上数据"""
    from models import Service
    query = db.query(Service)
    if q:
        query = query.filter(Service.title.like(f"%{q}%"))
    if provider:
        query = query.filter(Service.provider_openid == provider)
    rows = query.order_by(Service.created_at.desc()).limit(limit).all()
    return [_service_brief(s) for s in rows]


@router.post("/services/patch")
def patch_service(
    req: ServicePatch,
    db: Session = Depends(get_db),
    _: None = Depends(verify_dev_token),
):
    """修补服务字段（封面、状态、标题、描述），ref 支持 id 或标题关键字"""
    svc, candidates = _find_service(db, req.ref)
    if candidates:
        return {"success": False, "detail": "标题匹配到多条服务，请改用服务 id", "candidates": candidates}
    if not svc:
        raise HTTPException(status_code=404, detail=f"未找到服务：{req.ref}")

    before = _service_brief(svc)
    changed = {}
    for field in ("cover_image", "status", "title", "description"):
        value = getattr(req, field)
        if value is not None and value != "":
            setattr(svc, field, value)
            changed[field] = value
    if changed:
        from datetime import datetime as _dt
        svc.updated_at = _dt.now()
        db.commit()
        db.refresh(svc)
    return {"success": True, "changed": changed, "before": before, "after": _service_brief(svc)}


@router.post("/services/copy-cover")
def copy_cover(
    req: CopyCoverRequest,
    db: Session = Depends(get_db),
    _: None = Depends(verify_dev_token),
):
    """把一条服务的封面复制给另一条（用于补齐空白封面，无需重新上传图片）"""
    src, src_candidates = _find_service(db, req.from_ref)
    if src_candidates:
        return {"success": False, "detail": "来源匹配到多条服务", "candidates": src_candidates}
    if not src:
        raise HTTPException(status_code=404, detail=f"未找到来源服务：{req.from_ref}")
    if not src.cover_image:
        raise HTTPException(status_code=400, detail="来源服务本身没有封面")

    dst, dst_candidates = _find_service(db, req.to_ref)
    if dst_candidates:
        return {"success": False, "detail": "目标匹配到多条服务", "candidates": dst_candidates}
    if not dst:
        raise HTTPException(status_code=404, detail=f"未找到目标服务：{req.to_ref}")

    dst.cover_image = src.cover_image
    from datetime import datetime as _dt
    dst.updated_at = _dt.now()
    db.commit()
    db.refresh(dst)
    return {"success": True, "cover_image": dst.cover_image, "target": _service_brief(dst)}
