"""
需求路由：求辅导、求组队、求实习、志愿咨询。
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from dependencies import get_current_user, get_current_user_optional
from models import Demand, Resource, Service, User
from utils.db import get_db
from utils.content_guard import guard_user_content

router = APIRouter(prefix="/api/v1", tags=["需求"])


class DemandCreate(BaseModel):
    type: str = Field(default="tutor")
    dao_fa_type: str = ""
    request_type: str = ""
    target_tier: str = ""
    title: str = Field(..., max_length=80)
    description: str = Field(default="", max_length=2000)
    budget: int = Field(default=0, ge=0, le=1000000)
    contact: str = Field(default="", max_length=100)
    tags: list[str] = Field(default_factory=list)


@router.get("/feed")
def list_feed(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """首页信息流：当前以审核通过的藏经阁内容为真实数据源。"""
    query = db.query(Resource).filter(Resource.review_status == "approved")
    total = query.count()
    rows = (
        query.order_by(Resource.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = []
    for resource in rows:
        author = db.query(User).filter(User.openid == resource.author_openid).first()
        items.append({
            "id": resource.id,
            "type": "note",
            "title": resource.title,
            "cover": resource.cover_image,
            "tags": resource.tags or [],
            "author_name": author.nickname if author else "匿名",
            "author_avatar": author.avatar_url if author else "",
            "likes": resource.likes or 0,
            "comments": resource.comments or 0,
        })
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/search")
def global_search(
    keyword: str = Query(..., min_length=1),
    type: str = Query("service", pattern="^(service|user|demand)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """全局搜索，统一替代不存在的微信云函数 search。"""
    services = []
    users = []
    demands = []
    total = 0
    offset = (page - 1) * page_size

    if type == "service":
        query = db.query(Service).filter(
            Service.status == "on_sale",
            or_(Service.title.contains(keyword), Service.description.contains(keyword)),
        )
        total = query.count()
        rows = query.order_by(Service.created_at.desc()).offset(offset).limit(page_size).all()
        services = [{
            "id": item.id,
            "title": item.title,
            "description": item.description,
            "cover_image": item.cover_image,
            "price": round((item.price or 0) / 100, 2),
            "sales": item.order_count or 0,
        } for item in rows]
    elif type == "user":
        query = db.query(User).filter(
            User.status == "active",
            or_(User.nickname.contains(keyword), User.bio.contains(keyword)),
        )
        total = query.count()
        rows = query.order_by(User.created_at.desc()).offset(offset).limit(page_size).all()
        users = [{
            "openid": item.openid,
            "nickname": item.nickname,
            "avatar_url": item.avatar_url,
            "bio": item.bio,
            "service_count": db.query(Service).filter(
                Service.provider_openid == item.openid,
                Service.status == "on_sale",
            ).count(),
            "order_count": item.total_orders_done or 0,
        } for item in rows]
    else:
        query = db.query(Demand).filter(
            Demand.status == "open",
            or_(Demand.title.contains(keyword), Demand.description.contains(keyword)),
        )
        total = query.count()
        rows = query.order_by(Demand.created_at.desc()).offset(offset).limit(page_size).all()
        demands = [{
            **_demand_to_dict(item, db),
            "budget_min": item.budget or 0,
            "budget_max": item.budget or 0,
            "views": item.view_count or 0,
        } for item in rows]

    return {
        "services": services,
        "users": users,
        "demands": demands,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/demands")
def list_demands(
    type: Optional[str] = Query(None),
    dao_fa_type: Optional[str] = Query(None),
    sort: str = Query("new"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """需求广场列表"""
    query = db.query(Demand).filter(Demand.status == "open")
    if type:
        query = query.filter(Demand.demand_type == type)
    if dao_fa_type:
        query = query.filter(Demand.dao_fa_type == dao_fa_type)

    if sort == "hot":
        query = query.order_by(Demand.view_count.desc(), Demand.created_at.desc())
    else:
        query = query.order_by(Demand.created_at.desc())

    total = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "demands": [_demand_to_dict(row, db) for row in rows],
    }


@router.post("/demands")
def create_demand(
    body: DemandCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """发布通用需求"""
    demand = _create_demand(body, user, db)
    return {"success": True, "id": demand.id}


@router.post("/demand-requests")
def create_demand_request(
    body: DemandCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """兼容旧前端的咨询需求发布入口"""
    demand = _create_demand(body, user, db)
    return {"success": True, "id": demand.id}


@router.get("/demands/{demand_id}")
def get_demand(
    demand_id: str,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """需求详情"""
    demand = db.query(Demand).filter(Demand.id == demand_id).first()
    if not demand:
        return {"success": False, "message": "需求不存在"}
    demand.view_count = (demand.view_count or 0) + 1
    db.commit()
    return _demand_to_dict(demand, db)


def _create_demand(body: DemandCreate, user: User, db: Session) -> Demand:
    guard_user_content(user.openid, body.model_dump())
    demand_type = body.request_type or body.type
    demand = Demand(
        id=f"DM{uuid.uuid4().hex[:10].upper()}",
        openid=user.openid,
        demand_type=demand_type,
        dao_fa_type=body.dao_fa_type,
        title=body.title,
        description=body.description,
        budget=body.budget,
        contact=body.contact,
        target_tier=body.target_tier,
        tags=body.tags or [],
    )
    db.add(demand)
    db.commit()
    db.refresh(demand)
    return demand


def _demand_to_dict(demand: Demand, db: Session) -> dict:
    user = db.query(User).filter(User.openid == demand.openid).first() if demand.openid else None
    return {
        "id": demand.id,
        "type": demand.demand_type,
        "demand_type": demand.demand_type,
        "dao_fa_type": demand.dao_fa_type,
        "title": demand.title,
        "description": demand.description,
        "budget": demand.budget,
        "contact": demand.contact,
        "target_tier": demand.target_tier,
        "tags": demand.tags or [],
        "status": demand.status,
        "view_count": demand.view_count,
        "author": {
            "openid": user.openid,
            "nickname": user.nickname,
            "avatar_url": user.avatar_url,
            "school": user.school,
        } if user else None,
        "created_at": demand.created_at.isoformat() if demand.created_at else "",
    }
