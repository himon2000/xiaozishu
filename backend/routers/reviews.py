"""
评价路由 - 服务评价增强
支持评价标签、图片、回复功能
"""
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, Field
from utils.db import get_db
from models import Review, Order, Service, User
from dependencies import get_current_user
from services.level_service import get_level_info

router = APIRouter(prefix="/api/v1/reviews", tags=["评价"])


# ── 预设评价标签 ────────────────────────────────────────

REVIEW_TAGS = [
    "认真负责", "时间准时", "讲解清晰", "有耐心",
    "专业度高", "内容丰富", "互动性好", "效果显著",
    "态度友善", "回复及时"
]


class ReviewCreate(BaseModel):
    order_id: str
    rating: int = Field(..., ge=1, le=5)
    content: str = Field(default="", max_length=500)
    tags: list[str] = Field(default_factory=list, max_length=5)
    images: list[str] = Field(default_factory=list, max_length=9)
    anonymous: bool = False


class ReviewReply(BaseModel):
    content: str = Field(..., max_length=300)


# ── API 端点 ─────────────────────────────────────────────

@router.get("/tags")
def list_review_tags():
    """获取预设评价标签"""
    return {"tags": REVIEW_TAGS}


@router.post("")
def create_review(
    body: ReviewCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建评价（订单完成后）"""
    order = db.query(Order).filter(Order.id == body.order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    # 验证订单状态
    if order.status not in ["completed", "resolved"]:
        raise HTTPException(status_code=400, detail="订单未完成，无法评价")

    # 验证用户身份
    if user.openid not in [order.seeker_openid, order.provider_openid]:
        raise HTTPException(status_code=403, detail="无权评价此订单")

    # 检查是否已评价
    existing = db.query(Review).filter(
        Review.order_id == body.order_id,
        Review.reviewer_openid == user.openid
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="您已评价过此订单")

    # 确定被评价者
    reviewee_openid = order.provider_openid if user.openid == order.seeker_openid else order.seeker_openid

    # 验证评分
    if not 1 <= body.rating <= 5:
        raise HTTPException(status_code=400, detail="评分必须在1-5之间")

    review_id = f"RV{uuid.uuid4().hex[:10].upper()}"
    review = Review(
        id=review_id,
        order_id=body.order_id,
        reviewer_openid=user.openid,
        reviewee_openid=reviewee_openid,
        rating=body.rating,
        content=body.content,
        tags=body.tags[:5],  # 最多5个标签
        images=body.images[:9],  # 最多9张图片
        anonymous=body.anonymous,
    )
    db.add(review)

    # 更新订单的评价状态
    order.review_id = review_id

    # 更新被评价者的统计
    reviewee = db.query(User).filter(User.openid == reviewee_openid).first()
    if reviewee:
        # 重新计算评分
        reviews = db.query(Review).filter(Review.reviewee_openid == reviewee_openid).all()
        total_rating = sum(r.rating for r in reviews) + body.rating
        reviewee.rating = round(total_rating / (len(reviews) + 1), 1)
        reviewee.rating_count = len(reviews) + 1

    # 更新服务的评分和评价数
    service = db.query(Service).filter(Service.id == order.service_id).first()
    if service:
        reviews = db.query(Review).filter(Review.order_id.in_(
            db.query(Order.id).filter(Order.service_id == service.id)
        )).all()
        if reviews:
            service.rating = round(sum(r.rating for r in reviews) / len(reviews), 1)
        service.review_count = len(reviews) + 1

    db.commit()
    db.refresh(review)

    return {"id": review_id, "success": True}


@router.get("/service/{service_id}")
def list_service_reviews(
    service_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """获取服务评价列表"""
    # 验证服务存在
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="服务不存在")

    # 获取该服务的所有订单ID
    order_ids = [o.id for o in db.query(Order).filter(Order.service_id == service_id).all()]

    query = db.query(Review).filter(Review.order_id.in_(order_ids))
    total = query.count()
    reviews = query.order_by(Review.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "reviews": [_review_to_dict(r, db) for r in reviews],
    }


@router.get("/provider/{openid}")
def list_provider_reviews(
    openid: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """获取服务者收到的所有评价"""
    query = db.query(Review).filter(Review.reviewee_openid == openid)
    total = query.count()
    reviews = query.order_by(Review.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "reviews": [_review_to_dict(r, db) for r in reviews],
    }


@router.get("/order/{order_id}")
def get_order_review(
    order_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取订单的评价"""
    review = db.query(Review).filter(Review.order_id == order_id).first()
    if not review:
        return {"review": None}

    # 权限检查
    if user.openid not in [review.reviewer_openid, review.reviewee_openid] and user.role != "admin":
        raise HTTPException(status_code=403, detail="无权查看此评价")

    return {"review": _review_to_dict(review, db)}


@router.get("/{review_id}")
def get_review(
    review_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取评价详情"""
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="评价不存在")

    # 权限检查
    if user.openid not in [review.reviewer_openid, review.reviewee_openid] and user.role != "admin":
        raise HTTPException(status_code=403, detail="无权查看此评价")

    return _review_to_dict(review, db)


@router.post("/{review_id}/reply")
def reply_review(
    review_id: str,
    body: ReviewReply,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """服务者回复评价"""
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="评价不存在")

    # 验证是服务者回复
    if user.openid != review.reviewee_openid:
        raise HTTPException(status_code=403, detail="只有被评价者可以回复")

    # 检查是否已回复
    if review.reply:
        raise HTTPException(status_code=400, detail="已回复过，不能重复回复")

    review.reply = body.content
    review.reply_at = datetime.now()
    db.commit()

    return {"success": True}


@router.get("/stats/service/{service_id}")
def get_service_review_stats(
    service_id: str,
    db: Session = Depends(get_db),
):
    """获取服务评价统计"""
    # 获取该服务的所有订单ID
    order_ids = [o.id for o in db.query(Order).filter(Order.service_id == service_id).all()]

    reviews = db.query(Review).filter(Review.order_id.in_(order_ids)).all()

    if not reviews:
        return {
            "total": 0,
            "rating_avg": 5.0,
            "rating_dist": {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0},
            "tag_stats": {},
        }

    # 计算评分分布
    rating_dist = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
    for r in reviews:
        rating_dist[str(r.rating)] += 1

    # 统计标签
    tag_stats = {}
    for r in reviews:
        for tag in (r.tags or []):
            tag_stats[tag] = tag_stats.get(tag, 0) + 1

    # 按热度排序标签
    tag_stats = dict(sorted(tag_stats.items(), key=lambda x: x[1], reverse=True))

    return {
        "total": len(reviews),
        "rating_avg": round(sum(r.rating for r in reviews) / len(reviews), 1),
        "rating_dist": rating_dist,
        "tag_stats": tag_stats,
    }


# ── 辅助函数 ─────────────────────────────────────────────

def _review_to_dict(review: Review, db: Session) -> dict:
    """Review 模型转字典"""
    # 获取评价者信息
    reviewer = db.query(User).filter(User.openid == review.reviewer_openid).first()
    reviewer_info = {}
    if reviewer and not review.anonymous:
        level_info = get_level_info(reviewer.level)
        reviewer_info = {
            "openid": reviewer.openid,
            "nickname": reviewer.nickname,
            "avatar_url": reviewer.avatar_url,
            "level": reviewer.level,
            "level_name": level_info.get("name", ""),
            "level_icon": level_info.get("icon", ""),
        }
    elif reviewer and review.anonymous:
        reviewer_info = {
            "openid": "",
            "nickname": "匿名用户",
            "avatar_url": "",
            "level": 0,
            "level_name": "",
            "level_icon": "",
        }

    # 获取订单信息
    order = db.query(Order).filter(Order.id == review.order_id).first()
    order_info = {}
    if order:
        order_info = {
            "service_title": order.service_title,
            "created_at": order.created_at.isoformat() if order.created_at else "",
        }

    return {
        "id": review.id,
        "order_id": review.order_id,
        "reviewer": reviewer_info,
        "reviewee_openid": review.reviewee_openid,
        "rating": review.rating,
        "content": review.content,
        "tags": review.tags or [],
        "images": review.images or [],
        "anonymous": review.anonymous,
        "reply": review.reply,
        "reply_at": review.reply_at.isoformat() if review.reply_at else None,
        "created_at": review.created_at.isoformat() if review.created_at else "",
        "order": order_info,
    }
