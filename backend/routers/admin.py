"""小紫薯应用中心统一运维接口。"""
from datetime import datetime, timedelta
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from dependencies import require_role
from models import (
    AdminAuditLog, ContentReport, Demand, Dispute, Opportunity, Order,
    Resource, Service, Team, User,
)
from utils.db import get_db

router = APIRouter(prefix="/api/v1/admin", tags=["应用中心"])


def iso(value):
    return value.isoformat() if value else ""


def audit(db: Session, admin: User, action: str, target_type: str, target_id: str, detail: dict):
    db.add(AdminAuditLog(
        id=f"AUD{uuid.uuid4().hex[:12].upper()}",
        admin_openid=admin.openid,
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=detail,
    ))


class UserUpdate(BaseModel):
    status: str | None = Field(default=None, pattern="^(active|suspended|deleted)$")
    role: str | None = Field(default=None, pattern="^(seeker|provider|elder|admin)$")
    cert_status: str | None = Field(default=None, pattern="^(none|pending|verified|rejected)$")


class WalletAdjustment(BaseModel):
    delta: int = Field(ge=-10000000, le=10000000)
    reason: str = Field(min_length=2, max_length=200)


class ContentUpdate(BaseModel):
    status: str
    reason: str = Field(default="", max_length=200)


@router.get("/overview")
def overview(admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    week_start = datetime.now() - timedelta(days=7)
    pending_content = (
        db.query(Service).filter(Service.status == "reviewing").count()
        + db.query(Resource).filter(Resource.review_status == "pending").count()
        + db.query(Opportunity).filter(Opportunity.review_status == "pending").count()
    )
    return {
        "counts": {
            "users": db.query(User).filter(User.status != "deleted").count(),
            "services": db.query(Service).count(),
            "orders": db.query(Order).count(),
            "resources": db.query(Resource).count(),
            "demands": db.query(Demand).count(),
            "teams": db.query(Team).count(),
        },
        "pending": {
            "content": pending_content,
            "reports": db.query(ContentReport).filter(ContentReport.status == "pending").count(),
            "disputes": db.query(Dispute).filter(Dispute.status.in_(["pending", "reviewing"])).count(),
            "certifications": db.query(User).filter(User.cert_status == "pending").count(),
        },
        "wallet": {
            "total": db.query(func.coalesce(func.sum(User.spirit_stones), 0)).scalar() or 0,
            "frozen": db.query(func.coalesce(func.sum(User.spirit_stones_frozen), 0)).scalar() or 0,
        },
        "activity": {
            "new_users_7d": db.query(User).filter(User.created_at >= week_start).count(),
            "orders_7d": db.query(Order).filter(Order.created_at >= week_start).count(),
        },
        "generated_at": datetime.now().isoformat(),
    }


@router.get("/users")
def users(
    search: str = "", status: str = "", role: str = "",
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    admin: User = Depends(require_role("admin")), db: Session = Depends(get_db),
):
    query = db.query(User)
    if search:
        query = query.filter(or_(User.nickname.contains(search), User.openid.contains(search), User.school.contains(search)))
    if status:
        query = query.filter(User.status == status)
    if role:
        query = query.filter(User.role == role)
    total = query.count()
    rows = query.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "items": [{
        "openid": row.openid, "nickname": row.nickname, "role": row.role,
        "enabled_roles": row.enabled_roles or [], "status": row.status,
        "cert_status": row.cert_status, "school": row.school,
        "level": row.level, "spirit_stones": row.spirit_stones,
        "frozen": row.spirit_stones_frozen, "created_at": iso(row.created_at),
    } for row in rows]}


@router.patch("/users/{openid}")
def update_user(openid: str, body: UserUpdate, admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.openid == openid).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if openid == admin.openid and body.status in {"suspended", "deleted"}:
        raise HTTPException(status_code=400, detail="不能停用当前管理员账号")
    changes = body.model_dump(exclude_none=True)
    before = {key: getattr(user, key) for key in changes}
    for key, value in changes.items():
        setattr(user, key, value)
    if body.role:
        roles = set(user.enabled_roles or ["seeker"])
        roles.add(body.role)
        user.enabled_roles = sorted(roles)
        user.current_role = body.role
    audit(db, admin, "user.update", "user", openid, {"before": before, "after": changes})
    db.commit()
    return {"success": True}


@router.post("/users/{openid}/wallet-adjustment")
def adjust_wallet(openid: str, body: WalletAdjustment, admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.openid == openid).with_for_update().first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    before = user.spirit_stones or 0
    after = before + body.delta
    if after < (user.spirit_stones_frozen or 0):
        raise HTTPException(status_code=400, detail="调整后余额不能小于冻结灵石")
    user.spirit_stones = after
    user.balance = after
    audit(db, admin, "wallet.adjust", "user", openid, {
        "delta": body.delta, "reason": body.reason, "before": before, "after": after,
    })
    db.commit()
    return {"success": True, "balance": after}


CONTENT_MODELS = {
    "service": (Service, Service.status),
    "resource": (Resource, Resource.review_status),
    "demand": (Demand, Demand.status),
    "team": (Team, Team.status),
    "opportunity": (Opportunity, Opportunity.review_status),
}


@router.get("/content")
def content(
    content_type: str = "service", status: str = "", search: str = "",
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    admin: User = Depends(require_role("admin")), db: Session = Depends(get_db),
):
    if content_type not in CONTENT_MODELS:
        raise HTTPException(status_code=400, detail="内容类型不支持")
    model, status_col = CONTENT_MODELS[content_type]
    query = db.query(model)
    if status:
        query = query.filter(status_col == status)
    if search:
        query = query.filter(model.title.contains(search))
    total = query.count()
    rows = query.order_by(model.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "items": [{
        "id": row.id, "type": content_type, "title": row.title,
        "status": getattr(row, status_col.key), "owner": getattr(row, "provider_openid", None) or getattr(row, "author_openid", None) or getattr(row, "openid", None) or getattr(row, "creator_openid", ""),
        "created_at": iso(row.created_at),
    } for row in rows]}


@router.patch("/content/{content_type}/{content_id}")
def update_content(content_type: str, content_id: str, body: ContentUpdate, admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    if content_type not in CONTENT_MODELS:
        raise HTTPException(status_code=400, detail="内容类型不支持")
    allowed = {
        "service": {"on_sale", "off_sale", "reviewing", "rejected"},
        "resource": {"pending", "approved", "rejected"},
        "demand": {"open", "matched", "closed", "cancelled"},
        "team": {"recruiting", "full", "closed", "in_progress", "completed"},
        "opportunity": {"pending", "approved", "rejected"},
    }[content_type]
    if body.status not in allowed:
        raise HTTPException(status_code=400, detail="状态值不合法")
    model, status_col = CONTENT_MODELS[content_type]
    row = db.query(model).filter(model.id == content_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="内容不存在")
    before = getattr(row, status_col.key)
    setattr(row, status_col.key, body.status)
    if hasattr(row, "reject_reason"):
        row.reject_reason = body.reason
    audit(db, admin, "content.moderate", content_type, content_id, {"before": before, "after": body.status, "reason": body.reason})
    db.commit()
    return {"success": True}


@router.get("/orders")
def orders(
    status: str = "", search: str = "", page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    admin: User = Depends(require_role("admin")), db: Session = Depends(get_db),
):
    query = db.query(Order)
    if status:
        query = query.filter(Order.status == status)
    if search:
        query = query.filter(or_(Order.id.contains(search), Order.service_title.contains(search)))
    total = query.count()
    rows = query.order_by(Order.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "items": [{
        "id": row.id, "title": row.service_title, "status": row.status,
        "seeker": row.seeker_openid, "provider": row.provider_openid,
        "amount": row.total_paid or row.service_fee, "created_at": iso(row.created_at),
    } for row in rows]}


@router.get("/audit-logs")
def audit_logs(limit: int = Query(50, ge=1, le=200), admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    rows = db.query(AdminAuditLog).order_by(AdminAuditLog.created_at.desc()).limit(limit).all()
    return {"items": [{
        "id": row.id, "admin": row.admin_openid, "action": row.action,
        "target_type": row.target_type, "target_id": row.target_id,
        "detail": row.detail or {}, "created_at": iso(row.created_at),
    } for row in rows]}
