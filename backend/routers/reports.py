import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from dependencies import get_current_user, require_role
from models import ContentReport, User
from utils.content_guard import guard_user_content
from utils.db import get_db

router = APIRouter(prefix="/api/v1/reports", tags=["内容治理"])
ALLOWED_TARGETS = {"service", "resource", "review", "comment", "user", "platform"}
ALLOWED_REASONS = {"spam", "fake", "inappropriate", "harassment", "copyright", "other"}


class ReportCreate(BaseModel):
    target_type: str
    target_id: str = Field(..., min_length=1, max_length=64)
    reason: str
    description: str = Field(default="", max_length=500)


class ReportHandle(BaseModel):
    status: str = Field(pattern="^(resolved|rejected)$")


@router.post("")
def create_report(
    body: ReportCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.target_type not in ALLOWED_TARGETS or body.reason not in ALLOWED_REASONS:
        raise HTTPException(status_code=400, detail="举报类型不合法")
    guard_user_content(user.openid, body.description)
    existing = db.query(ContentReport).filter(
        ContentReport.reporter_openid == user.openid,
        ContentReport.target_type == body.target_type,
        ContentReport.target_id == body.target_id,
        ContentReport.status == "pending",
    ).first()
    if existing:
        return {"success": True, "id": existing.id, "message": "举报已提交"}
    report = ContentReport(
        id=f"RPT{uuid.uuid4().hex[:12].upper()}",
        reporter_openid=user.openid,
        target_type=body.target_type,
        target_id=body.target_id,
        reason=body.reason,
        description=body.description,
    )
    db.add(report)
    db.commit()
    return {"success": True, "id": report.id, "message": "举报已提交"}


@router.get("")
def list_reports(
    status: str = Query("pending"),
    admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    rows = db.query(ContentReport).filter(ContentReport.status == status).order_by(ContentReport.created_at.desc()).all()
    return {"reports": [{
        "id": row.id,
        "target_type": row.target_type,
        "target_id": row.target_id,
        "reason": row.reason,
        "description": row.description,
        "status": row.status,
        "created_at": row.created_at.isoformat() if row.created_at else "",
    } for row in rows]}


@router.put("/{report_id}")
def handle_report(
    report_id: str,
    body: ReportHandle,
    admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    report = db.query(ContentReport).filter(ContentReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="举报不存在")
    report.status = body.status
    report.handled_by = admin.openid
    report.handled_at = datetime.now()
    db.commit()
    return {"success": True}
