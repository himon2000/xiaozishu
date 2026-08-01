"""
服务路由：六大道法服务 CRUD
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
from utils.db import get_db
from models import ContentReport, Service, User, Review, Order
from dependencies import get_current_user, require_provider, require_certified
from services.level_service import get_level_info
from sqlalchemy import func
from utils.content_guard import guard_user_content
from config import get_settings

router = APIRouter(prefix="/api/v1/services", tags=["服务"])


class ServiceCreate(BaseModel):
    dao_fa_type: str
    title: str = Field(..., max_length=50)
    description: str = Field(default="", max_length=2000)
    cover_image: str = ""
    tags: list[str] = Field(default_factory=list, max_length=10)
    target_audience: str = "all"
    subjects: list[str] = Field(default_factory=list, max_length=10)
    pricing_mode: str = "per_session"
    price: int = Field(default=0, ge=0, le=1000000)  # 灵石，最大10000元
    unit: str = "次"
    min_sessions: int = Field(default=1, ge=1, le=365)
    group_price: int = 0
    delivery_methods: list[str] = []
    location: str = ""
    max_group_size: int = Field(default=1, ge=1, le=100)
    provider_level_required: int = 0
    # 传功授法特有字段
    service_type: str = "tutoring"  # tutoring|competition|exam_prep|thesis
    achievements: list = []  # 战绩
    cases: list = []  # 案例
    expertise: list[str] = []  # 擅长领域
    teaching_style: str = ""  # 教学风格


@router.get("")
def list_services(
    dao_fa_type: Optional[str] = Query(None),
    subject: Optional[str] = Query(None),
    service_type: Optional[str] = Query(None),  # 传功授法服务类型
    school_level: Optional[str] = Query(None),
    min_level: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    sort: Optional[str] = Query("hot"),
    min_price: Optional[int] = Query(None),  # 最低价格（分）
    max_price: Optional[int] = Query(None),  # 最高价格（分）
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """
    服务广场列表
    支持：道法类型 / 科目 / 服务类型 / 学段 / 最低境界 / 关键词搜索 / 排序 / 价格区间
    """
    query = db.query(Service).filter(Service.status == "on_sale")

    if dao_fa_type:
        query = query.filter(Service.dao_fa_type == dao_fa_type)
    if subject:
        query = query.filter(Service.subjects.contains(subject))
    if service_type:
        query = query.filter(Service.service_type == service_type)
    if school_level:
        query = query.filter(Service.seeker_school_levels.contains(school_level))
    if min_level:
        query = query.filter(Service.provider_level_required <= min_level)
    if search:
        query = query.filter(
            Service.title.contains(search) |
            Service.description.contains(search) |
            Service.subjects.contains(search)
        )
    # 价格区间筛选
    if min_price is not None:
        query = query.filter(Service.price >= min_price)
    if max_price is not None:
        query = query.filter(Service.price <= max_price)

    # 排序
    if sort == "hot":
        query = query.order_by(Service.order_count.desc(), Service.rating.desc())
    elif sort == "sales":
        query = query.order_by(Service.order_count.desc())
    elif sort == "rating":
        query = query.order_by(Service.rating.desc())
    elif sort == "price_asc":
        query = query.order_by(Service.price.asc())
    elif sort == "price_desc":
        query = query.order_by(Service.price.desc())
    else:
        query = query.order_by(Service.created_at.desc())

    total = query.count()
    services = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "services": [_service_to_dict(s, db) for s in services],
    }


@router.get("/categories")
def list_categories():
    """六大道法分类列表 + 传功授法细分"""
    return {
        "categories": [
            {"id": "chuan_gong", "name": "传功授法", "sub": "学科辅导/竞赛指导",
             "desc": "学科辅导/竞赛陪练",
             "icon": "📚", "commission_rate": 0.10, "color": "#e74c3c"},
            {"id": "mi_jing",   "name": "联袂问道", "sub": "课题带教/科研组队",
             "desc": "课题带教/科研合作",
             "icon": "🔬", "commission_rate": 0.10, "color": "#9b59b6"},
            {"id": "zong_men",  "name": "万宗宝鉴", "sub": "志愿咨询/名校攻略",
             "desc": "志愿咨询/名校助升",
             "icon": "🏫", "commission_rate": 0.12, "color": "#3498db"},
            {"id": "xia_shan",  "name": "下山历练", "sub": "实习内推/名企就业",
             "desc": "实习内推/名企兼职",
             "icon": "💼", "commission_rate": 0.08, "color": "#2ecc71"},
            {"id": "zhi_fa",    "name": "天衡裁决", "sub": "纠纷仲裁/客服支持",
             "desc": "平台运维实习岗",
             "icon": "⚙️",  "commission_rate": 0.05, "color": "#f39c12"},
            {"id": "cang_jing", "name": "道藏天阁", "sub": "学习笔记/经验攻略",
             "desc": "题库/经验/攻略",
             "icon": "📖", "commission_rate": 0.15, "color": "#1abc9c"},
        ],
        # 传功授法细分
        "chuan_gong_subjects": [
            # 理工类
            {"id": "math", "name": "高等数学", "icon": "📐", "category": "理工"},
            {"id": "linear_algebra", "name": "线性代数", "icon": "📊", "category": "理工"},
            {"id": "probability", "name": "概率论/数理统计", "icon": "🎲", "category": "理工"},
            {"id": "physics", "name": "大学物理", "icon": "⚡", "category": "理工"},
            {"id": "chemistry", "name": "大学化学", "icon": "🧪", "category": "理工"},
            {"id": "programming", "name": "编程/Python/C++", "icon": "💻", "category": "理工"},
            {"id": "data_structure", "name": "数据结构与算法", "icon": "🔢", "category": "理工"},
            {"id": "circuit", "name": "电路/电子技术", "icon": "🔌", "category": "理工"},
            # 文科类
            {"id": "english", "name": "英语/四六级/考研英语", "icon": "🇬🇧", "category": "文科"},
            {"id": "chinese", "name": "大学语文/写作", "icon": "📝", "category": "文科"},
            {"id": "economics", "name": "经济学/金融学", "icon": "💹", "category": "文科"},
            {"id": "management", "name": "管理学/市场营销", "icon": "📋", "category": "文科"},
            {"id": "law", "name": "法学/法律", "icon": "⚖️", "category": "文科"},
            # 竞赛类
            {"id": "math建模", "name": "数学建模竞赛", "icon": "🏆", "category": "竞赛", "is_competition": True},
            {"id": "acm", "name": "ACM/ICPC编程竞赛", "icon": "🏆", "category": "竞赛", "is_competition": True},
            {"id": "challenge_cup", "name": "挑战杯/创青春", "icon": "🏆", "category": "竞赛", "is_competition": True},
            {"id": "innovation", "name": "大创/互联网+", "icon": "🏆", "category": "竞赛", "is_competition": True},
            {"id": "math_competition", "name": "全国/省级数学竞赛", "icon": "🏆", "category": "竞赛", "is_competition": True},
            {"id": "physics_competition", "name": "大学物理竞赛", "icon": "🏆", "category": "竞赛", "is_competition": True},
            # 考试冲刺
            {"id": "postgraduate", "name": "考研全套辅导", "icon": "🎓", "category": "考试"},
            {"id": "toefl_ielts", "name": "托福/雅思", "icon": "🌍", "category": "考试"},
            {"id": "gmat_gre", "name": "GMAT/GRE", "icon": "📚", "category": "考试"},
            {"id": "cfa_frm", "name": "CFA/FRM金融证书", "icon": "💰", "category": "考试"},
            {"id": "cpa", "name": "CPA/ACCA会计证书", "icon": "📊", "category": "考试"},
            # 其他
            {"id": "thesis", "name": "论文写作/发表", "icon": "📄", "category": "其他"},
            {"id": "exam_prep", "name": "考前冲刺/答疑", "icon": "✏️", "category": "其他"},
            {"id": "other", "name": "其他学科", "icon": "📦", "category": "其他"},
        ],
        "competition_levels": [
            {"id": "school", "name": "校级", "color": "#95a5a6"},
            {"id": "city", "name": "市级", "color": "#3498db"},
            {"id": "provincial", "name": "省级", "color": "#9b59b6"},
            {"id": "national", "name": "国家级", "color": "#e74c3c"},
            {"id": "world", "name": "国际级", "color": "#f39c12"},
        ],
    }


@router.get("/providers/top")
def top_providers(
    dao_fa_type: Optional[str] = Query(None),
    page_size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """优秀服务者推荐，供首页/传功授法入口使用"""
    query = db.query(User).filter(User.role.in_(["provider", "elder", "admin"]))
    if dao_fa_type:
        query = query.join(Service, Service.provider_openid == User.openid).filter(
            Service.dao_fa_type == dao_fa_type,
            Service.status == "on_sale",
        )

    users = query.order_by(
        User.rating.desc(),
        User.total_orders_done.desc(),
        User.exp_points.desc(),
    ).limit(page_size * 2).all()

    providers = []
    seen = set()
    for user in users:
        if user.openid in seen:
            continue
        seen.add(user.openid)
        providers.append(_provider_to_dict(user))
        if len(providers) >= page_size:
            break

    return {"providers": providers, "total": len(providers)}


@router.get("/{service_id}")
def get_service(service_id: str, db: Session = Depends(get_db)):
    """服务详情 + 大虾主页信息"""
    svc = db.query(Service).filter(Service.id == service_id).first()
    if not svc:
        raise HTTPException(status_code=404, detail="服务不存在")
    result = _service_to_dict(svc, db)
    # 追加大虾详细信息
    provider = db.query(User).filter(User.openid == svc.provider_openid).first()
    if provider:
        result["provider"] = _provider_to_dict(provider)
    return result


@router.post("")
def create_service(
    body: ServiceCreate,
    user: User = Depends(require_provider),
    db: Session = Depends(get_db),
):
    """大虾发布新服务"""
    guard_user_content(user.openid, body.model_dump())
    if not get_settings().payment_enabled and (body.pricing_mode != "free" or body.price != 0):
        raise HTTPException(status_code=403, detail="当前版本仅允许发布免费服务")
    # 检查境界是否满足要求
    from services.level_service import get_level_info as gli
    user_level_cfg = gli(user.level)
    max_price = user_level_cfg.get("max_price_yuan", 200) * 100
    if body.price > max_price:
        raise HTTPException(
            status_code=400,
            detail=f"您的境界（{user_level_cfg['name']}）最高定价 {max_price // 100} 元/次"
        )

    svc = Service(
        id=f"SVC{uuid.uuid4().hex[:10].upper()}",
        provider_openid=user.openid,
        dao_fa_type=body.dao_fa_type,
        title=body.title,
        description=body.description,
        cover_image=body.cover_image,
        tags=body.tags,
        target_audience=body.target_audience,
        subjects=body.subjects,
        pricing_mode=body.pricing_mode,
        price=body.price,
        unit=body.unit,
        min_sessions=body.min_sessions,
        group_price=body.group_price,
        delivery_methods=body.delivery_methods,
        location=body.location,
        max_group_size=body.max_group_size,
        provider_level_required=body.provider_level_required,
        # 传功授法特有字段
        service_type=body.service_type,
        achievements=body.achievements or [],
        cases=body.cases or [],
        expertise=body.expertise or [],
        teaching_style=body.teaching_style,
        status="on_sale",
    )
    db.add(svc)
    db.commit()
    db.refresh(svc)

    # ── 多角色体系：自动更新服务统计 + 检查是否解锁 provider ──
    try:
        from services import role_service
        # 更新 provider 角色的服务数
        enabled = user.enabled_roles or []
        if "provider" in enabled or "elder" in enabled:
            role_service.update_role_stats(db, user.openid, "provider", service_delta=1)
        # 检查是否可以解锁 provider 角色
        if "provider" not in enabled:
            can_unlock, _ = role_service.check_role_eligibility(db, user, "provider")
            if can_unlock:
                role_service.enable_role(db, user.openid, "provider")
                user.current_role = "provider"
                db.commit()
    except Exception:
        pass  # 不因角色更新失败影响服务发布

    return {"id": svc.id, "success": True}


class ServiceUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    cover_image: Optional[str] = None
    tags: Optional[list[str]] = None
    target_audience: Optional[str] = None
    subjects: Optional[list[str]] = None
    pricing_mode: Optional[str] = None
    price: Optional[int] = None
    unit: Optional[str] = None
    min_sessions: Optional[int] = None
    group_price: Optional[int] = None
    delivery_methods: Optional[list[str]] = None
    location: Optional[str] = None
    max_group_size: Optional[int] = None
    status: Optional[str] = None  # on_sale | off_sale
    # 传功授法特有字段
    service_type: Optional[str] = None
    achievements: Optional[list] = None
    cases: Optional[list] = None
    expertise: Optional[list[str]] = None
    teaching_style: Optional[str] = None


@router.put("/{service_id}")
def update_service(
    service_id: str,
    body: ServiceUpdate,
    user: User = Depends(require_provider),
    db: Session = Depends(get_db),
):
    """更新服务（仅服务所有者可操作）"""
    guard_user_content(user.openid, body.model_dump(exclude_unset=True))
    svc = db.query(Service).filter(Service.id == service_id).first()
    if not svc:
        raise HTTPException(status_code=404, detail="服务不存在")

    # 权限检查
    if svc.provider_openid != user.openid:
        raise HTTPException(status_code=403, detail="无权修改此服务")

    # 更新字段
    update_data = body.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(svc, field):
            setattr(svc, field, value)

    db.commit()
    return {"success": True, "id": service_id}


@router.delete("/{service_id}")
def delete_service(
    service_id: str,
    user: User = Depends(require_provider),
    db: Session = Depends(get_db),
):
    """删除服务（软删除，下架）"""
    svc = db.query(Service).filter(Service.id == service_id).first()
    if not svc:
        raise HTTPException(status_code=404, detail="服务不存在")

    # 权限检查
    if svc.provider_openid != user.openid:
        raise HTTPException(status_code=403, detail="无权删除此服务")

    # 软删除：下架服务
    svc.status = "off_sale"
    db.commit()
    return {"success": True, "message": "服务已下架"}


@router.post("/{service_id}/toggle-status")
def toggle_service_status(
    service_id: str,
    user: User = Depends(require_provider),
    db: Session = Depends(get_db),
):
    """上下架切换"""
    svc = db.query(Service).filter(Service.id == service_id).first()
    if not svc:
        raise HTTPException(status_code=404, detail="服务不存在")

    # 权限检查
    if svc.provider_openid != user.openid:
        raise HTTPException(status_code=403, detail="无权操作此服务")

    # 切换状态
    new_status = "off_sale" if svc.status == "on_sale" else "on_sale"
    svc.status = new_status
    db.commit()

    return {
        "success": True,
        "id": service_id,
        "status": new_status,
        "message": "上架成功" if new_status == "on_sale" else "已下架"
    }


@router.get("/mine")
def my_services(
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    user: User = Depends(require_provider),
    db: Session = Depends(get_db),
):
    """我的服务列表"""
    query = db.query(Service).filter(Service.provider_openid == user.openid)

    if status:
        query = query.filter(Service.status == status)

    total = query.count()
    services = query.order_by(Service.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "services": [_service_to_dict(s, db) for s in services],
    }


@router.get("/provider/{openid}")
def get_provider_profile(openid: str, db: Session = Depends(get_db)):
    """大虾主页（含服务列表+评价摘要+传承树）"""
    provider = db.query(User).filter(User.openid == openid).first()
    if not provider:
        raise HTTPException(status_code=404, detail="大虾不存在")

    services = db.query(Service).filter(
        Service.provider_openid == openid,
        Service.status == "on_sale"
    ).all()

    return {
        "provider": _provider_to_dict(provider),
        "services": [_service_to_dict(s, db) for s in services],
    }


def _service_to_dict(svc: Service, db: Session) -> dict:
    """将 Service 模型转为 API 响应字典"""
    provider = db.query(User).filter(User.openid == svc.provider_openid).first()
    level_info = get_level_info(provider.level) if provider else {}
    return {
        "id": svc.id,
        "dao_fa_type": svc.dao_fa_type,
        "title": svc.title,
        "description": svc.description,
        "cover_image": svc.cover_image,
        "tags": svc.tags or [],
        "target_audience": svc.target_audience,
        "subjects": svc.subjects or [],
        "pricing": {
            "mode": svc.pricing_mode,
            "price": svc.price,
            "unit": svc.unit,
            "min_sessions": svc.min_sessions,
            "group_price": svc.group_price,
        },
        # 兼容小程序现有卡片组件的扁平字段；新代码优先使用 pricing。
        "price": svc.price,
        "pricing_mode": svc.pricing_mode,
        "unit": svc.unit,
        "min_sessions": svc.min_sessions,
        "group_price": svc.group_price,
        "delivery_methods": svc.delivery_methods or [],
        "location": svc.location,
        "max_group_size": svc.max_group_size,
        # 传功授法特有
        "service_type": svc.service_type,
        "achievements": svc.achievements or [],
        "cases": svc.cases or [],
        "expertise": svc.expertise or [],
        "teaching_style": svc.teaching_style,
        "stats": {
            "rating": svc.rating,
            "review_count": svc.review_count,
            "order_count": svc.order_count,
        },
        # 兼容小程序现有列表组件；新代码优先使用 stats。
        "rating": svc.rating,
        "review_count": svc.review_count,
        "order_count": svc.order_count,
        "provider": _provider_to_dict(provider) if provider else None,
        "created_at": svc.created_at.isoformat() if svc.created_at else "",
        "cover": svc.cover_image,
    }


def _provider_to_dict(user: User) -> dict:
    """将 User 模型转为大虾信息字典"""
    level_info = get_level_info(user.level)
    return {
        "openid": user.openid,
        "nickname": user.nickname,
        "avatar_url": user.avatar_url,
        "avatar": user.avatar_url,
        "role": user.role,
        "school": user.school,
        "school_level": user.school_level,
        "major": user.major,
        "level": user.level,
        "level_name": level_info["name"],
        "level_color": level_info["color"],
        "level_icon": level_info["icon"],
        "exp_points": user.exp_points,
        "provider_tagline": user.provider_tagline,
        "specialties": user.specialties or [],
        "service_categories": user.service_categories or [],
        "hourly_rate": user.hourly_rate,
        "available": user.available,
        "cert_status": user.cert_status,
        "cert_badges": user.cert_badges or [],
        "rating": user.rating,
        "rating_count": user.rating_count,
        "total_orders_done": user.total_orders_done,
        "totalOrders": user.total_orders_done,
        "total_disciples": user.total_disciples,
        "active_disciples": user.active_disciples,
    }


# ==================== 服务增强接口 ====================

class ReportRequest(BaseModel):
    reason: str  # spam | fake | inappropriate | other
    description: str = ""


@router.post("/{service_id}/report")
def report_service(
    service_id: str,
    body: ReportRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    举报服务
    - reason: spam(垃圾信息) | fake(虚假宣传) | inappropriate(不适内容) | other(其他)
    """
    svc = db.query(Service).filter(Service.id == service_id).first()
    if not svc:
        raise HTTPException(status_code=404, detail="服务不存在")

    # 不能举报自己的服务
    if svc.provider_openid == user.openid:
        return {"success": False, "message": "不能举报自己的服务"}
    guard_user_content(user.openid, body.description)

    existing = db.query(ContentReport).filter(
        ContentReport.reporter_openid == user.openid,
        ContentReport.target_type == "service",
        ContentReport.target_id == service_id,
        ContentReport.status == "pending",
    ).first()
    if existing:
        return {"success": True, "message": "举报已提交", "report_id": existing.id}

    svc.report_count = (svc.report_count or 0) + 1
    report = ContentReport(
        id=f"RPT{uuid.uuid4().hex[:12].upper()}",
        reporter_openid=user.openid,
        target_type="service",
        target_id=service_id,
        reason=body.reason,
        description=body.description,
    )
    db.add(report)
    db.commit()
    return {
        "success": True,
        "message": "举报已提交，感谢您的反馈",
        "report_id": report.id,
    }


from datetime import datetime


@router.get("/hot")
def get_hot_services(
    dao_fa_type: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """
    获取热门服务推荐
    - 基于订单量、评分、收藏数综合排序
    """
    query = db.query(Service).filter(Service.status == "on_sale")

    if dao_fa_type:
        query = query.filter(Service.dao_fa_type == dao_fa_type)

    # 综合热度计算：(订单数 × 3 + 评价数 × 5 + 评分 × 100)
    services = query.order_by(
        (Service.order_count * 3 + Service.review_count * 5 + Service.rating * 100).desc()
    ).limit(limit).all()

    return {
        "dao_fa_type": dao_fa_type or "all",
        "services": [_service_to_dict(s, db) for s in services],
    }


@router.get("/recommend")
def get_recommended_services(
    user_openid: Optional[str] = Query(None),
    dao_fa_type: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """
    个性化服务推荐
    - 如果登录：根据用户浏览历史和收藏偏好推荐
    - 未登录：返回热门服务
    """
    query = db.query(Service).filter(Service.status == "on_sale")

    if dao_fa_type:
        query = query.filter(Service.dao_fa_type == dao_fa_type)

    # 优先推荐高评分、订单多的服务
    services = query.order_by(
        Service.rating.desc(),
        Service.order_count.desc()
    ).limit(limit).all()

    return {
        "recommend_type": "personalized" if user_openid else "popular",
        "services": [_service_to_dict(s, db) for s in services],
    }


@router.get("/{service_id}/stats")
def get_service_stats(
    service_id: str,
    db: Session = Depends(get_db),
):
    """
    获取服务详细统计
    """
    svc = db.query(Service).filter(Service.id == service_id).first()
    if not svc:
        raise HTTPException(status_code=404, detail="服务不存在")

    # 获取服务者信息
    provider = db.query(User).filter(User.openid == svc.provider_openid).first()

    # 获取最近评价
    recent_reviews = db.query(Review).filter(
        Review.service_id == service_id
    ).order_by(Review.created_at.desc()).limit(5).all()

    # 计算评分分布
    all_reviews = db.query(Review).filter(Review.service_id == service_id).all()
    rating_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for r in all_reviews:
        if r.rating and 1 <= int(r.rating) <= 5:
            rating_distribution[int(r.rating)] += 1

    return {
        "service_id": service_id,
        "basic_stats": {
            "rating": svc.rating,
            "review_count": svc.review_count,
            "order_count": svc.order_count,
            "view_count": svc.view_count or 0,
            "favorite_count": svc.favorite_count or 0,
        },
        "rating_distribution": rating_distribution,
        "provider_stats": {
            "rating": provider.rating if provider else 0,
            "rating_count": provider.rating_count if provider else 0,
            "total_orders": provider.total_orders_done if provider else 0,
            "level": provider.level if provider else 1,
        },
        "recent_reviews": [
            {
                "id": r.id,
                "rating": r.rating,
                "content": r.content[:100] + "..." if r.content and len(r.content) > 100 else r.content,
                "tags": r.tags or [],
                "created_at": r.created_at.isoformat() if r.created_at else "",
            }
            for r in recent_reviews
        ],
    }


@router.post("/{service_id}/view")
def record_service_view(
    service_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    记录服务浏览
    """
    svc = db.query(Service).filter(Service.id == service_id).first()
    if not svc:
        raise HTTPException(status_code=404, detail="服务不存在")

    svc.view_count = (svc.view_count or 0) + 1
    db.commit()

    return {"success": True, "view_count": svc.view_count}


@router.get("/stats/overview")
def get_services_overview(
    db: Session = Depends(get_db),
):
    """
    获取服务广场总览统计
    """
    total_services = db.query(Service).filter(Service.status == "on_sale").count()

    # 各分类统计
    categories = ["chuan_gong", "mi_jing", "zong_men", "xia_shan", "zhi_fa", "cang_jing"]
    category_stats = {}

    for cat in categories:
        count = db.query(Service).filter(
            Service.dao_fa_type == cat,
            Service.status == "on_sale"
        ).count()
        avg_rating = db.query(func.avg(Service.rating)).filter(
            Service.dao_fa_type == cat,
            Service.status == "on_sale"
        ).scalar() or 0

        category_stats[cat] = {
            "count": count,
            "avg_rating": round(float(avg_rating), 1),
        }

    return {
        "total_services": total_services,
        "category_stats": category_stats,
    }
