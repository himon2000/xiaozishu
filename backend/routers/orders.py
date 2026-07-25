"""
订单路由：订单全生命周期
"""
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
from utils.db import get_db
from models import Order, Service, User
from dependencies import get_current_user
from services.order_machine import (
    generate_order_id, can_transition, add_timeline_entry,
    calculate_order_amounts, get_status_display_name, get_status_progress,
)
from services.payment_service import create_unified_order
from services.level_service import add_exp
from services import mentor_service

router = APIRouter(prefix="/api/v1/orders", tags=["订单"])


class OrderCreate(BaseModel):
    service_id: str
    sessions: int = Field(1, ge=1, le=100)
    group_members: list[str] = Field(default_factory=list, max_length=20)


class StatusUpdate(BaseModel):
    status: str
    remark: str = ""


class SessionLogCreate(BaseModel):
    session_no: int = Field(..., ge=1)
    duration_min: int = 0
    summary: str = Field(default="", max_length=500)


@router.post("")
def create_order(
    body: OrderCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建订单（散修视角）"""
    svc = db.query(Service).filter(Service.id == body.service_id).first()
    if not svc:
        raise HTTPException(status_code=404, detail="服务不存在")
    if svc.status != "on_sale":
        raise HTTPException(status_code=400, detail="该服务已下架")

    sessions = max(body.sessions, svc.min_sessions or 1)
    service_fee = svc.price * sessions

    order = Order(
        id=generate_order_id(),
        dao_fa_type=svc.dao_fa_type,
        order_type="group_quest" if body.group_members else "single",
        seeker_openid=user.openid,
        provider_openid=svc.provider_openid,
        group_members=body.group_members,
        service_id=svc.id,
        service_title=svc.title,
        service_dao_fa=svc.dao_fa_type,
        service_cover=svc.cover_image,
        service_price=svc.price,
        service_unit=svc.unit,
        status="pending_payment",
        sessions_total=sessions,
        sessions_done=0,
        total_paid=service_fee,
    )

    amounts = calculate_order_amounts(order)
    order.service_fee = amounts["service_fee"]
    order.platform_commission = amounts["platform_commission"]
    order.provider_income = amounts["provider_income"]
    order.mentor_bonus = amounts["mentor_bonus"]

    add_timeline_entry(order, "pending_payment", "散修发起订单")
    db.add(order)
    db.commit()
    db.refresh(order)

    return {
        "id": order.id,
        "status": order.status,
        "service_fee": order.service_fee,
        "total_paid": order.total_paid,
        "status_display": get_status_display_name(order.status),
    }


@router.get("")
def list_orders(
    role: Optional[str] = Query(None),  # seeker | provider | all
    status_filter: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=20),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    我的订单列表（双视图）
    - seeker：我是散修，所有向我收费的订单
    - provider：我是大虾，所有向我付款的订单
    """
    query = db.query(Order)

    if role == "seeker":
        query = query.filter(Order.seeker_openid == user.openid)
    elif role == "provider":
        query = query.filter(Order.provider_openid == user.openid)
    else:
        query = query.filter(
            (Order.seeker_openid == user.openid) | (Order.provider_openid == user.openid)
        )

    if status_filter:
        query = query.filter(Order.status == status_filter)

    total = query.count()
    orders = query.order_by(Order.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "orders": [_order_to_dict(o, db) for o in orders],
    }


@router.get("/{order_id}")
def get_order(order_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """订单详情"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    # 权限检查：只有订单双方可见
    if user.openid not in [order.seeker_openid, order.provider_openid] and user.role != "admin":
        raise HTTPException(status_code=403, detail="无权查看此订单")

    result = _order_to_dict(order, db)
    # 追加双方用户信息
    seeker = db.query(User).filter(User.openid == order.seeker_openid).first()
    provider = db.query(User).filter(User.openid == order.provider_openid).first()
    result["seeker"] = _user_brief(seeker) if seeker else None
    result["provider"] = _user_brief(provider) if provider else None

    # 检查师徒关系
    has_mentorship = mentor_service.check_existing_mentorship(
        db, order.seeker_openid, order.provider_openid
    )
    result["has_mentorship"] = bool(has_mentorship)

    return result


@router.patch("/{order_id}/status")
def update_order_status(
    order_id: str,
    body: StatusUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新订单状态"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    # 权限检查（P0-4 修复：非订单参与方直接拒绝，admin 单独判断）
    is_seeker = user.openid == order.seeker_openid
    is_provider = user.openid == order.provider_openid
    is_admin = user.role == "admin"

    allowed = {
        "paid":          ["provider"],          # 大虾确认收款/接单
        "assigned":      ["provider"],           # 接单
        "in_progress":   ["provider", "admin"], # 开始服务
        "pending_confirm":["provider"],          # 大虾申请完成
        "completed":     ["seeker", "admin"],    # 散修确认完成
        "dispute":       ["seeker", "provider"], # 发起纠纷
    }

    if body.status not in allowed:
        raise HTTPException(status_code=400, detail="无效状态")

    if not is_admin:
        if not is_seeker and not is_provider:
            raise HTTPException(status_code=403, detail="您不是订单参与方，无权操作")
        role_key = "seeker" if is_seeker else "provider"
        if role_key not in allowed[body.status]:
            raise HTTPException(status_code=403, detail="您无权执行此操作")
    else:
        # admin 操作：记录审计日志到 timeline
        add_timeline_entry(order, f"admin_{body.status}",
                          f"执事 [{user.nickname}] 操作: {body.status}", user.nickname)

    if not can_transition(order.status, body.status):
        raise HTTPException(status_code=400, detail=f"无法从 {order.status} 流转到 {body.status}")

    order.status = body.status
    add_timeline_entry(order, body.status, body.remark, user.nickname)
    db.commit()

    # 订单完成：结算 + 修为 + 触发师徒关系
    if body.status == "completed":
        _settle_order(db, order)

    return {"success": True, "status": order.status, "display": get_status_display_name(body.status)}


@router.post("/{order_id}/session-log")
def add_session_log(
    order_id: str,
    body: SessionLogCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """大虾记录课次日志"""

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if user.openid != order.provider_openid:
        raise HTTPException(status_code=403, detail="只有大虾可以记录课次")

    logs = order.session_logs or []
    logs.append({
        "session_no": body.session_no,
        "date": datetime.now().isoformat(),
        "duration_min": body.duration_min,
        "summary": body.summary,
        "seeker_confirmed": False,
    })
    order.session_logs = logs
    order.sessions_done = len(logs)

    # 所有课次完成 → 自动进入待确认
    if order.sessions_done >= order.sessions_total:
        order.status = "pending_confirm"
        add_timeline_entry(order, "pending_confirm", "所有课次已完成，等待散修确认")

    db.commit()
    return {"success": True, "sessions_done": order.sessions_done}


async def _initiate_payment(order_id: str, openid: str, db: Session):
    """发起微信支付（内部调用）"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    pay_params = await create_unified_order(order, openid, description=order.service_title)
    return pay_params


@router.post("/{order_id}/pay")
async def initiate_payment(
    order_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """发起微信支付"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if user.openid != order.seeker_openid:
        raise HTTPException(status_code=403, detail="只能为自己付款")
    if order.status != "pending_payment":
        raise HTTPException(status_code=400, detail="订单状态不允许发起支付")

    pay_params = await create_unified_order(order, user.openid, description=order.service_title)
    return pay_params


def _settle_order(db: Session, order: Order):
    """
    订单完成时结算
    - 事务保护
    - 师傅奖励分成（5%）
    - 平台佣金记录
    """
    try:
        provider = db.query(User).filter(User.openid == order.provider_openid).first()
        if not provider:
            raise HTTPException(status_code=404, detail="服务者不存在")

        # 1. 服务者收入入账（使用灵石余额字段）
        provider.spirit_stones = (provider.spirit_stones or 0) + order.provider_income
        provider.spirit_stones_earned += order.provider_income
        provider.total_orders_done += 1

        # 2. 师傅奖励分成（如果有）
        if order.mentor_bonus and order.mentor_bonus > 0:
            # 查找师傅关系
            from models import Mentorship
            mentorship = db.query(Mentorship).filter(
                Mentorship.disciple_openid == provider.openid,
                Mentorship.status == "active"
            ).first()
            if mentorship:
                mentor = db.query(User).filter(User.openid == mentorship.mentor_openid).first()
                if mentor:
                    mentor.spirit_stones = (mentor.spirit_stones or 0) + order.mentor_bonus
                    mentorship.mentor_income_from_lineage += order.mentor_bonus
                    # 记录师傅分成日志
                    add_timeline_entry(
                        order, "mentor_bonus",
                        f"师傅 {mentor.nickname} 获得分成 {order.mentor_bonus} 灵石",
                        "系统"
                    )

        # 3. 平台佣金记录（预留扩展点）
        if order.platform_commission > 0:
            add_timeline_entry(
                order, "platform_commission",
                f"平台佣金 {order.platform_commission} 灵石",
                "系统"
            )

        # 4. 修为 +10（完成订单）
        add_exp(db, provider, "earn_order_done", related_id=order.id,
                remark=f"完成订单 {order.id}")

        # 5. 更新服务统计
        svc = db.query(Service).filter(Service.id == order.service_id).first()
        if svc:
            svc.order_count += 1

        # 6. 记录结算日志
        add_timeline_entry(
            order, "settled",
            f"订单结算完成：服务者收入 {order.provider_income} 灵石" +
            (f"，师傅分成 {order.mentor_bonus} 灵石" if order.mentor_bonus else ""),
            "系统"
        )

        db.commit()

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"订单结算失败: {str(e)}")


def _order_to_dict(order: Order, db: Session) -> dict:
    """Order 模型转字典"""
    # 计算超时信息
    timeout_info = _calculate_timeout(order)

    return {
        "id": order.id,
        "dao_fa_type": order.dao_fa_type,
        "order_type": order.order_type,
        "seeker_openid": order.seeker_openid,
        "provider_openid": order.provider_openid,
        "group_members": order.group_members or [],
        "service_id": order.service_id,
        "service_snapshot": {
            "title": order.service_title,
            "dao_fa_type": order.service_dao_fa,
            "cover": order.service_cover,
            "price": order.service_price,
            "unit": order.service_unit,
        },
        "status": order.status,
        "status_display": get_status_display_name(order.status),
        "status_progress": get_status_progress(order.status),
        "amounts": {
            "service_fee": order.service_fee,
            "platform_commission": order.platform_commission,
            "provider_income": order.provider_income,
            "mentor_bonus": order.mentor_bonus,
            "total_paid": order.total_paid,
        },
        # 兼容订单列表现有扁平字段。
        "service_fee": order.service_fee,
        "total_paid": order.total_paid,
        "sessions_total": order.sessions_total,
        "sessions_done": order.sessions_done,
        "session_logs": order.session_logs or [],
        "timeline": order.timeline or [],
        "timeout_info": timeout_info,
        "expected_duration_hours": order.expected_duration_hours or 24,
        "created_at": order.created_at.isoformat() if order.created_at else "",
        "updated_at": order.updated_at.isoformat() if order.updated_at else "",
        "review_id": order.review_id or "",
    }


def _calculate_timeout(order: Order) -> dict:
    """计算订单超时信息"""
    now = datetime.now()
    info = {
        "has_timeout_warning": False,
        "timeout_hours": 0,
        "remaining_hours": 0,
        "message": "",
    }

    # 仅对进行中的订单计算超时
    if order.status not in ["assigned", "in_progress", "pending_confirm"]:
        return info

    # 计算从开始到现在的小时数
    start_time = order.start_date or order.updated_at or order.created_at
    elapsed = (now - start_time).total_seconds() / 3600
    expected = order.expected_duration_hours or 24

    remaining = expected - elapsed

    if remaining < 0:
        # 已超时
        info["has_timeout_warning"] = True
        info["timeout_hours"] = abs(int(remaining))
        info["message"] = f"已超时 {info['timeout_hours']} 小时"
    elif remaining < 6:
        # 即将超时（6小时内）
        info["has_timeout_warning"] = True
        info["remaining_hours"] = int(remaining)
        info["message"] = f"还剩 {info['remaining_hours']} 小时"

    return info


def _user_brief(user: User) -> dict:
    if not user:
        return {}
    from services.level_service import get_level_info
    info = get_level_info(user.level)
    return {
        "openid": user.openid,
        "nickname": user.nickname,
        "avatar_url": user.avatar_url,
        "level": user.level,
        "level_name": info["name"],
        "level_color": info["color"],
        "level_icon": info["icon"],
        "school": user.school,
    }


# ==================== 订单增强接口 ====================

class RefundRequest(BaseModel):
    reason: str = Field(..., max_length=200)
    description: str = ""


class CancelRequest(BaseModel):
    reason: str = Field(..., max_length=200)


@router.post("/{order_id}/refund")
def apply_refund(
    order_id: str,
    body: RefundRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    申请退款
    - 仅购买者（seeker）可申请
    - 需在服务完成前申请
    - 退款原因：不想买了 | 服务不满意 | 联系不上 | 其他
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    if user.openid != order.seeker_openid:
        raise HTTPException(status_code=403, detail="只有购买者可以申请退款")

    if order.status in ["completed", "cancelled", "refunded"]:
        raise HTTPException(status_code=400, detail="该订单状态不允许申请退款")

    if order.refund_status == "pending":
        return {"success": False, "message": "退款申请正在处理中"}

    # 创建退款申请
    order.refund_status = "pending"
    order.refund_reason = body.reason
    order.refund_description = body.description
    order.refund_apply_at = datetime.now()

    add_timeline_entry(order, "refund_pending", f"申请退款：{body.reason}")
    db.commit()

    return {
        "success": True,
        "message": "退款申请已提交，请等待审核",
        "refund_status": "pending",
        "apply_at": order.refund_apply_at.isoformat(),
    }


@router.post("/{order_id}/cancel")
def cancel_order(
    order_id: str,
    body: CancelRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    取消订单
    - 仅未付款订单可取消
    - 双方均可取消
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    is_seeker = user.openid == order.seeker_openid
    is_provider = user.openid == order.provider_openid

    if not (is_seeker or is_provider):
        raise HTTPException(status_code=403, detail="您不是订单参与方")

    if order.status not in ["pending_payment"]:
        raise HTTPException(status_code=400, detail="只有未付款订单可以取消")

    order.status = "cancelled"
    order.cancelled_by = user.openid
    order.cancelled_reason = body.reason
    order.cancelled_at = datetime.now()

    add_timeline_entry(order, "cancelled", f"订单取消：{body.reason}", user.nickname)
    db.commit()

    return {"success": True, "message": "订单已取消"}


@router.get("/{order_id}/can-review")
def check_can_review(
    order_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    检查是否可以评价
    - 订单完成后且未评价
    """
    from models import Review

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    if user.openid != order.seeker_openid:
        raise HTTPException(status_code=403, detail="只有购买者可以评价")

    if order.status != "completed":
        return {"can_review": False, "reason": "订单未完成"}

    existing_review = db.query(Review).filter(
        Review.order_id == order_id,
        Review.reviewer_openid == user.openid
    ).first()

    if existing_review:
        return {"can_review": False, "reason": "已评价", "review_id": existing_review.id}

    return {"can_review": True}


@router.get("/stats/summary")
def get_order_stats_summary(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取订单统计汇总（使用 count 聚合优化）
    """
    from sqlalchemy import func

    # 作为购买者的订单统计（使用 count 聚合）
    seeker_total = db.query(func.count(Order.id)).filter(
        Order.seeker_openid == user.openid
    ).scalar() or 0
    seeker_completed = db.query(func.count(Order.id)).filter(
        Order.seeker_openid == user.openid,
        Order.status == "completed"
    ).scalar() or 0
    seeker_pending = db.query(func.count(Order.id)).filter(
        Order.seeker_openid == user.openid,
        Order.status.in_(["pending_payment", "paid", "assigned"])
    ).scalar() or 0
    seeker_in_progress = db.query(func.count(Order.id)).filter(
        Order.seeker_openid == user.openid,
        Order.status.in_(["in_progress", "pending_confirm"])
    ).scalar() or 0
    seeker_amount = db.query(func.sum(Order.total_paid)).filter(
        Order.seeker_openid == user.openid,
        Order.status.in_(["completed", "paid", "assigned", "in_progress", "pending_confirm"])
    ).scalar() or 0

    # 作为服务者的订单统计（使用 count 聚合）
    provider_total = db.query(func.count(Order.id)).filter(
        Order.provider_openid == user.openid
    ).scalar() or 0
    provider_completed = db.query(func.count(Order.id)).filter(
        Order.provider_openid == user.openid,
        Order.status == "completed"
    ).scalar() or 0
    provider_pending = db.query(func.count(Order.id)).filter(
        Order.provider_openid == user.openid,
        Order.status.in_(["pending_payment", "paid", "assigned"])
    ).scalar() or 0
    provider_in_progress = db.query(func.count(Order.id)).filter(
        Order.provider_openid == user.openid,
        Order.status.in_(["in_progress", "pending_confirm"])
    ).scalar() or 0
    provider_amount = db.query(func.sum(Order.total_paid)).filter(
        Order.provider_openid == user.openid,
        Order.status.in_(["completed", "paid", "assigned", "in_progress", "pending_confirm"])
    ).scalar() or 0

    return {
        "as_seeker": {
            "total": seeker_total,
            "completed": seeker_completed,
            "pending": seeker_pending,
            "in_progress": seeker_in_progress,
            "total_amount": seeker_amount,
        },
        "as_provider": {
            "total": provider_total,
            "completed": provider_completed,
            "pending": provider_pending,
            "in_progress": provider_in_progress,
            "total_amount": provider_amount,
        },
    }


@router.get("/timeline/{order_id}")
def get_order_timeline(
    order_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取订单时间线（简化版）
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    # 权限检查
    if user.openid not in [order.seeker_openid, order.provider_openid] and user.role != "admin":
        raise HTTPException(status_code=403, detail="无权查看此订单")

    timeline = order.timeline or []

    return {
        "order_id": order_id,
        "current_status": order.status,
        "timeline": [
            {
                "status": t.get("status"),
                "message": t.get("message"),
                "operator": t.get("operator"),
                "timestamp": t.get("timestamp"),
            }
            for t in timeline
        ]
    }
