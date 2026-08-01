"""
仲裁/纠纷路由
"""
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from utils.db import get_db
from models import Dispute, Order, User
from dependencies import get_current_user
from utils.content_guard import guard_user_content
from services.order_machine import add_timeline_entry, can_transition

router = APIRouter(prefix="/api/v1/disputes", tags=["仲裁"])


# ═══════════════════════════════════════════════════════════
# 仲裁类型定义
# ═══════════════════════════════════════════════════════════

DISPUTE_TYPES = [
    {
        "id": "quality",
        "name": "服务质量问题",
        "description": "服务者未按约定提供符合要求的服务",
        "icon": "icon-quality",
    },
    {
        "id": "delay",
        "name": "超时未完成",
        "description": "服务者超过约定时间未完成服务",
        "icon": "icon-time",
    },
    {
        "id": "attitude",
        "name": "态度问题",
        "description": "服务者态度恶劣或沟通不畅",
        "icon": "icon-chat",
    },
    {
        "id": "refund",
        "name": "退款争议",
        "description": "对退款金额或方式存在分歧",
        "icon": "icon-money",
    },
    {
        "id": "cheating",
        "name": "作弊/欺诈",
        "description": "发现对方存在欺诈行为",
        "icon": "icon-warning",
    },
    {
        "id": "other",
        "name": "其他问题",
        "description": "其他需要平台介入的情况",
        "icon": "icon-more",
    },
]

EXPECTED_ACTIONS = [
    {"id": "re_deliver", "name": "重新服务", "description": "由服务者重新履行服务"},
    {"id": "platform_coordination", "name": "平台协调", "description": "由平台联系双方协调处理"},
    {"id": "re_deliver", "name": "重新服务", "description": "服务者重新提供服务"},
    {"id": "platform_compensation", "name": "平台补偿", "description": "申请平台额外补偿"},
    {"id": "other", "name": "其他处理", "description": "其他合理的处理方式"},
]


@router.get("/types")
def get_dispute_types():
    """获取仲裁类型列表"""
    return {
        "code": 0,
        "data": {
            "dispute_types": DISPUTE_TYPES,
            "expected_actions": EXPECTED_ACTIONS,
        }
    }


def generate_dispute_id():
    """生成纠纷ID"""
    return f"DSP{uuid.uuid4().hex[:12].upper()}"


class DisputeCreate(BaseModel):
    order_id: str
    dispute_type: str
    description: str
    evidence_images: list[str] = []
    expected_action: str
    user_role: str = "seeker"


class DisputeResolve(BaseModel):
    resolution: str
    admin_remark: str = ""


@router.post("")
def create_dispute(
    body: DisputeCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建仲裁申请"""
    guard_user_content(user.openid, body.description)
    # 检查订单是否存在
    order = db.query(Order).filter(Order.id == body.order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    # 检查权限
    if user.openid not in [order.seeker_openid, order.provider_openid]:
        raise HTTPException(status_code=403, detail="无权为此订单申请仲裁")

    # 检查是否已有待处理的仲裁
    existing = db.query(Dispute).filter(
        Dispute.order_id == body.order_id,
        Dispute.status.in_(["pending", "reviewing"])
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="此订单已有待处理的仲裁申请")

    # 创建仲裁
    dispute = Dispute(
        id=generate_dispute_id(),
        order_id=body.order_id,
        applicant_openid=user.openid,
        applicant_role=body.user_role,
        dispute_type=body.dispute_type,
        description=body.description,
        evidence_images=body.evidence_images,
        expected_action=body.expected_action,
        status="pending",
    )

    # 更新订单状态为纠纷
    if order.status != "dispute":
        order.status = "dispute"
        add_timeline_entry(order, "dispute", f"用户 {user.nickname} 发起仲裁申请", user.nickname)

    db.add(dispute)
    db.commit()
    db.refresh(dispute)

    return {
        "id": dispute.id,
        "status": dispute.status,
        "created_at": dispute.created_at.isoformat(),
    }


@router.get("/{dispute_id}")
def get_dispute(
    dispute_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取仲裁详情"""
    dispute = db.query(Dispute).filter(Dispute.id == dispute_id).first()
    if not dispute:
        raise HTTPException(status_code=404, detail="仲裁不存在")

    # 检查权限
    order = db.query(Order).filter(Order.id == dispute.order_id).first()
    if user.openid not in [order.seeker_openid, order.provider_openid] and user.role != "admin":
        raise HTTPException(status_code=403, detail="无权查看此仲裁")

    return _dispute_to_dict(dispute, order)


@router.get("/my")
def my_disputes(
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """我的仲裁列表"""
    query = db.query(Dispute).filter(Dispute.applicant_openid == user.openid)

    if status:
        query = query.filter(Dispute.status == status)

    total = query.count()
    disputes = query.order_by(Dispute.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "disputes": [_dispute_to_dict(d, None) for d in disputes],
    }


@router.get("/order/{order_id}")
def get_dispute_by_order(
    order_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """根据订单ID获取仲裁（如果有）"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    # 检查权限
    if user.openid not in [order.seeker_openid, order.provider_openid] and user.role != "admin":
        raise HTTPException(status_code=403, detail="无权查看此订单的仲裁")

    dispute = db.query(Dispute).filter(
        Dispute.order_id == order_id,
        Dispute.status.in_(["pending", "reviewing"])
    ).first()

    if not dispute:
        return {"has_dispute": False, "dispute": None}

    return {"has_dispute": True, "dispute": _dispute_to_dict(dispute, order)}


@router.post("/{dispute_id}/resolve")
def resolve_dispute(
    dispute_id: str,
    body: DisputeResolve,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """管理员处理仲裁"""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可处理仲裁")
    guard_user_content(user.openid, body.resolution, body.admin_remark)

    dispute = db.query(Dispute).filter(Dispute.id == dispute_id).first()
    if not dispute:
        raise HTTPException(status_code=404, detail="仲裁不存在")

    if dispute.status not in ["pending", "reviewing"]:
        raise HTTPException(status_code=400, detail="仲裁状态不允许此操作")

    dispute.status = "resolved"
    dispute.resolution = body.resolution
    dispute.admin_remark = body.admin_remark
    dispute.resolved_at = datetime.now()

    # 更新订单状态
    order = db.query(Order).filter(Order.id == dispute.order_id).first()
    if order:
        if body.resolution in {"full_refund", "partial_refund"}:
            raise HTTPException(status_code=503, detail="支付与退款功能暂未开放")
        order.status = "completed"

        add_timeline_entry(order, order.status, f"仲裁结果：{body.resolution}", "平台管理员")

    db.commit()

    return {"success": True, "status": dispute.status}


@router.post("/{dispute_id}/cancel")
def cancel_dispute(
    dispute_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """撤销仲裁申请"""
    dispute = db.query(Dispute).filter(Dispute.id == dispute_id).first()
    if not dispute:
        raise HTTPException(status_code=404, detail="仲裁不存在")

    if dispute.applicant_openid != user.openid and user.role != "admin":
        raise HTTPException(status_code=403, detail="无权撤销此仲裁")

    if dispute.status not in ["pending"]:
        raise HTTPException(status_code=400, detail="只有待处理的仲裁可以撤销")

    dispute.status = "cancelled"

    # 恢复订单状态
    order = db.query(Order).filter(Order.id == dispute.order_id).first()
    if order and order.status == "dispute":
        order.status = "in_progress"  # 恢复到进行中状态
        add_timeline_entry(order, "in_progress", "用户撤销仲裁申请", user.nickname)

    db.commit()

    return {"success": True}


def _dispute_to_dict(dispute: Dispute, order: Order = None) -> dict:
    """Dispute模型转字典"""
    result = {
        "id": dispute.id,
        "order_id": dispute.order_id,
        "applicant_openid": dispute.applicant_openid,
        "applicant_role": dispute.applicant_role,
        "dispute_type": dispute.dispute_type,
        "description": dispute.description,
        "evidence_images": dispute.evidence_images or [],
        "expected_action": dispute.expected_action,
        "status": dispute.status,
        "resolution": dispute.resolution,
        "admin_remark": dispute.admin_remark,
        "created_at": dispute.created_at.isoformat() if dispute.created_at else "",
        "updated_at": dispute.updated_at.isoformat() if dispute.updated_at else "",
        "resolved_at": dispute.resolved_at.isoformat() if dispute.resolved_at else "",
    }

    # 添加订单快照
    if order:
        result["order_snapshot"] = {
            "title": order.service_title,
            "amount": order.total_paid,
            "status": order.status,
        }

    return result


# ==================== 仲裁增强接口 ====================

@router.get("/stats/summary")
def get_dispute_stats(
    db: Session = Depends(get_db),
):
    """
    获取仲裁统计信息
    """
    from sqlalchemy import func

    total = db.query(Dispute).count()
    pending = db.query(Dispute).filter(Dispute.status == "pending").count()
    resolved = db.query(Dispute).filter(Dispute.status == "resolved").count()
    cancelled = db.query(Dispute).filter(Dispute.status == "cancelled").count()

    # 按类型统计
    type_stats = {}
    for dtype in DISPUTE_TYPES:
        count = db.query(Dispute).filter(Dispute.dispute_type == dtype["id"]).count()
        type_stats[dtype["id"]] = count

    # 按处理结果统计
    resolution_stats = {}
    for resolution in ["full_refund", "partial_refund", "re_deliver", "platform_compensation", "dismissed"]:
        count = db.query(Dispute).filter(Dispute.resolution == resolution).count()
        resolution_stats[resolution] = count

    return {
        "total": total,
        "pending": pending,
        "resolved": resolved,
        "cancelled": cancelled,
        "resolution_rate": round(resolved / total * 100, 1) if total > 0 else 0,
        "type_stats": type_stats,
        "resolution_stats": resolution_stats,
    }


@router.get("/progress/{dispute_id}")
def get_dispute_progress(
    dispute_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取仲裁进度时间线
    """
    dispute = db.query(Dispute).filter(Dispute.id == dispute_id).first()
    if not dispute:
        raise HTTPException(status_code=404, detail="仲裁不存在")

    # 检查权限
    order = db.query(Order).filter(Order.id == dispute.order_id).first()
    if user.openid not in [order.seeker_openid, order.provider_openid] and user.role != "admin":
        raise HTTPException(status_code=403, detail="无权查看此仲裁")

    # 构建进度时间线
    progress = [
        {
            "step": 1,
            "title": "提交仲裁申请",
            "description": f"申请人提交了{dict((t['id'], t['name']) for t in DISPUTE_TYPES).get(dispute.dispute_type, dispute.dispute_type)}类型的仲裁",
            "status": "completed",
            "timestamp": dispute.created_at.isoformat() if dispute.created_at else "",
        },
        {
            "step": 2,
            "title": "等待平台审核",
            "description": "平台将在1-3个工作日内审核您的申请",
            "status": "in_progress" if dispute.status == "pending" else (
                "completed" if dispute.status != "pending" else "pending"
            ),
        },
        {
            "step": 3,
            "title": "仲裁处理中",
            "description": "平台正在处理仲裁，请耐心等待",
            "status": "in_progress" if dispute.status == "reviewing" else (
                "pending" if dispute.status == "pending" else "completed"
            ),
        },
        {
            "step": 4,
            "title": "仲裁结果",
            "description": dispute.resolution or "等待仲裁结果",
            "status": "completed" if dispute.status == "resolved" else "pending",
            "timestamp": dispute.resolved_at.isoformat() if dispute.resolved_at and dispute.status == "resolved" else "",
        },
    ]

    return {
        "dispute_id": dispute_id,
        "current_status": dispute.status,
        "progress": progress,
    }


@router.post("/{dispute_id}/evidence")
def submit_evidence(
    dispute_id: str,
    evidence_type: str,  # text | image | file
    content: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    补充证据材料
    """
    guard_user_content(user.openid, content)
    dispute = db.query(Dispute).filter(Dispute.id == dispute_id).first()
    if not dispute:
        raise HTTPException(status_code=404, detail="仲裁不存在")

    # 检查权限
    order = db.query(Order).filter(Order.id == dispute.order_id).first()
    if user.openid not in [order.seeker_openid, order.provider_openid]:
        raise HTTPException(status_code=403, detail="无权为此仲裁添加证据")

    if dispute.status not in ["pending", "reviewing"]:
        raise HTTPException(status_code=400, detail="仲裁状态不允许添加证据")

    # 记录证据
    evidence = {
        "type": evidence_type,
        "content": content,
        "submitted_by": user.openid,
        "submitted_at": datetime.now().isoformat(),
    }

    if not dispute.evidence_extra:
        dispute.evidence_extra = []
    dispute.evidence_extra.append(evidence)

    dispute.updated_at = datetime.now()
    db.commit()

    return {"success": True, "evidence": evidence}


@router.get("/tips")
def get_dispute_tips():
    """
    获取仲裁申请须知
    """
    return {
        "code": 0,
        "data": {
            "tips": [
                {
                    "title": "准备充分的证据",
                    "content": "在申请仲裁前，请准备好相关的聊天记录、截图、文件等证据材料，以便平台公正处理。",
                },
                {
                    "title": "选择正确的仲裁类型",
                    "content": "根据实际情况选择最合适的仲裁类型，这将帮助平台更快地理解问题。",
                },
                {
                    "title": "明确您的诉求",
                    "content": "请清楚描述您期望的处理结果，如全额退款、部分退款或重新服务等。",
                },
                {
                    "title": "保持沟通畅通",
                    "content": "在仲裁处理期间，请保持联系方式畅通，以便平台在需要时与您联系。",
                },
                {
                    "title": "耐心等待处理",
                    "content": "平台将在1-3个工作日内完成审核，处理周期通常为3-7个工作日。",
                },
            ],
            "common_issues": [
                {
                    "question": "申请仲裁后还能撤销吗？",
                    "answer": "在仲裁状态为「待处理」时，您可以申请撤销仲裁。一旦平台开始处理，将无法撤销。",
                },
                {
                    "question": "仲裁需要收费吗？",
                    "answer": "目前平台仲裁服务完全免费，不收取任何费用。",
                },
                {
                    "question": "如果对仲裁结果不满意怎么办？",
                    "answer": "如果对仲裁结果有异议，您可以通过客服渠道进行申诉。",
                },
            ]
        }
    }
