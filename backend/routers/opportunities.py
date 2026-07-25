"""
下山历练-就业资源路由
实习、内推、职位机会发布与申请
"""
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from pydantic import BaseModel
from utils.db import get_db
from models import Opportunity, OpportunityApplication, OpportunityFavorite, User
from models import OpportunityType, OpportunityStatus, ApplicationStatus
from dependencies import get_current_user, get_current_user_optional
from services.level_service import get_level_info

router = APIRouter(prefix="/api/v1/opportunities", tags=["下山历练"])


# ── 请求/响应模型 ────────────────────────────────────────

class OpportunityCreate(BaseModel):
    title: str
    opportunity_type: str  # internship|referral|job
    company_name: str = ""
    company_industry: str = ""
    company_size: str = ""
    position: str = ""
    position_type: str = ""
    work_location: str = ""
    work_mode: str = ""
    salary_range: str = ""
    salary_hidden: bool = False
    description: str = ""
    requirements: str = ""
    benefits: str = ""
    deadline: Optional[str] = None
    apply_url: str = ""
    contact_wx: str = ""
    tags: list[str] = []
    require_cert: bool = True
    require_school: bool = False
    require_level: int = 0


class OpportunityUpdate(BaseModel):
    title: Optional[str] = None
    company_name: Optional[str] = None
    company_industry: Optional[str] = None
    position: Optional[str] = None
    position_type: Optional[str] = None
    work_location: Optional[str] = None
    work_mode: Optional[str] = None
    salary_range: Optional[str] = None
    salary_hidden: Optional[bool] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    benefits: Optional[str] = None
    deadline: Optional[str] = None
    apply_url: Optional[str] = None
    contact_wx: Optional[str] = None
    tags: Optional[list[str]] = None
    status: Optional[str] = None


class ApplicationCreate(BaseModel):
    message: str = ""
    resume_url: str = ""


# ── 分类接口 ─────────────────────────────────────────────

@router.get("/categories")
def list_categories():
    """就业资源分类列表"""
    return {
        "categories": [
            {
                "id": "internship",
                "name": "🏢 寻觅道场",
                "icon": "🏢",
                "desc": "寻找实习机会",
                "sub": "实习",
                "type": "resource"  # 资源类型：resource=提供者发布，need=需求者寻找
            },
            {
                "id": "referral",
                "name": "🎯 求取推荐",
                "icon": "🎯",
                "desc": "寻求内推机会",
                "sub": "内推",
                "type": "need"
            },
            {
                "id": "job",
                "name": "💼 问道职涯",
                "icon": "💼",
                "desc": "求职、就职机会",
                "sub": "求职",
                "type": "need"
            },
            {
                "id": "job_resource",
                "name": "🌟 布施机缘",
                "icon": "🌟",
                "desc": "分享实习/内推/职位",
                "sub": "发布资源",
                "type": "resource"
            },
        ]
    }


# ── 资源列表 ─────────────────────────────────────────────

@router.get("")
def list_opportunities(
    category: Optional[str] = Query(None, description="分类筛选"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    location: Optional[str] = Query(None, description="工作地点筛选"),
    salary_range: Optional[str] = Query(None, description="薪资范围筛选"),
    sort: Optional[str] = Query("latest", description="排序：latest/newest/hottest"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """
    就业资源列表

    - category: 分类筛选（internship/referral/job/job_resource）
    - search: 搜索关键词
    - location: 工作地点筛选
    - salary_range: 薪资范围筛选
    - sort: 排序方式（latest/newest/hottest）
    """
    query = db.query(Opportunity).filter(Opportunity.status == OpportunityStatus.ACTIVE)

    # 分类筛选
    if category:
        if category == "job_resource":
            # 布施机缘：所有类型的资源
            pass
        else:
            query = query.filter(Opportunity.opportunity_type == category)

    # 关键词搜索
    if search:
        query = query.filter(
            or_(
                Opportunity.title.contains(search),
                Opportunity.company_name.contains(search),
                Opportunity.position.contains(search),
                Opportunity.description.contains(search)
            )
        )

    # 工作地点筛选
    if location:
        query = query.filter(Opportunity.work_location.contains(location))

    # 薪资筛选
    if salary_range:
        query = query.filter(Opportunity.salary_range == salary_range)

    # 排序
    if sort == "newest":
        query = query.order_by(Opportunity.created_at.desc())
    elif sort == "hottest":
        query = query.order_by(Opportunity.view_count.desc(), Opportunity.apply_count.desc())
    else:  # latest
        query = query.order_by(Opportunity.created_at.desc())

    total = query.count()
    opportunities = query.offset((page - 1) * page_size).limit(page_size).all()

    # 获取用户收藏状态
    favorite_ids = []
    if user:
        favorites = db.query(OpportunityFavorite).filter(
            OpportunityFavorite.user_openid == user.openid,
            OpportunityFavorite.opportunity_id.in_([o.id for o in opportunities])
        ).all()
        favorite_ids = [f.opportunity_id for f in favorites]

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "opportunities": [_opp_to_dict(o, db, is_favorited=o.id in favorite_ids) for o in opportunities],
    }


# ── 热门资源推荐 ─────────────────────────────────────────

@router.get("/hot")
def get_hot_opportunities(
    limit: int = Query(10, ge=1, le=50),
    user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """热门就业资源推荐"""
    query = db.query(Opportunity).filter(Opportunity.status == OpportunityStatus.ACTIVE)

    opportunities = query.order_by(
        Opportunity.view_count.desc(),
        Opportunity.apply_count.desc(),
        Opportunity.created_at.desc()
    ).limit(limit).all()

    # 获取用户收藏状态
    favorite_ids = []
    if user:
        favorites = db.query(OpportunityFavorite).filter(
            OpportunityFavorite.user_openid == user.openid,
            OpportunityFavorite.opportunity_id.in_([o.id for o in opportunities])
        ).all()
        favorite_ids = [f.opportunity_id for f in favorites]

    return {
        "opportunities": [_opp_to_dict(o, db, is_favorited=o.id in favorite_ids) for o in opportunities],
    }


# ── 我的资源（发布的） ────────────────────────────────────

@router.get("/mine")
def get_my_opportunities(
    status: Optional[str] = Query(None, description="状态筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """我发布的就业资源"""
    query = db.query(Opportunity).filter(Opportunity.openid == user.openid)

    if status:
        query = query.filter(Opportunity.status == status)

    query = query.order_by(Opportunity.created_at.desc())

    total = query.count()
    opportunities = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "opportunities": [_opp_to_dict(o, db) for o in opportunities],
    }


# ── 我的申请 ─────────────────────────────────────────────

@router.get("/applications/mine")
def get_my_applications(
    status: Optional[str] = Query(None, description="状态筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """我的申请记录"""
    query = db.query(OpportunityApplication).filter(
        OpportunityApplication.applicant_openid == user.openid
    )

    if status:
        query = query.filter(OpportunityApplication.status == status)

    query = query.order_by(OpportunityApplication.created_at.desc())

    total = query.count()
    applications = query.offset((page - 1) * page_size).limit(page_size).all()

    # 获取关联的资源信息
    result = []
    for app in applications:
        opp = db.query(Opportunity).filter(Opportunity.id == app.opportunity_id).first()
        if opp:
            result.append({
                "application": _application_to_dict(app, db),
                "opportunity": _opp_to_dict(opp, db),
            })

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "applications": result,
    }


# ── 收到的申请 ────────────────────────────────────────────

@router.get("/{opportunity_id}/applications")
def get_opportunity_applications(
    opportunity_id: str,
    status: Optional[str] = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取资源收到的申请列表（仅发布者可见）"""
    opp = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not opp:
        raise HTTPException(status_code=404, detail="资源不存在")

    if opp.openid != user.openid:
        raise HTTPException(status_code=403, detail="仅发布者可查看")

    query = db.query(OpportunityApplication).filter(
        OpportunityApplication.opportunity_id == opportunity_id
    )

    if status:
        query = query.filter(OpportunityApplication.status == status)

    query = query.order_by(OpportunityApplication.created_at.desc())
    applications = query.all()

    return {
        "opportunity_id": opportunity_id,
        "total": len(applications),
        "applications": [_application_to_dict(app, db, include_applicant_info=True) for app in applications],
    }


# ── 资源详情 ─────────────────────────────────────────────

@router.get("/{opportunity_id}")
def get_opportunity(
    opportunity_id: str,
    user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """就业资源详情"""
    opp = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not opp:
        raise HTTPException(status_code=404, detail="资源不存在")

    # 增加浏览数
    opp.view_count += 1
    db.commit()

    # 检查收藏状态
    is_favorited = False
    has_applied = False
    if user:
        favorite = db.query(OpportunityFavorite).filter(
            OpportunityFavorite.opportunity_id == opportunity_id,
            OpportunityFavorite.user_openid == user.openid
        ).first()
        is_favorited = favorite is not None

        application = db.query(OpportunityApplication).filter(
            OpportunityApplication.opportunity_id == opportunity_id,
            OpportunityApplication.applicant_openid == user.openid
        ).first()
        has_applied = application is not None

    return _opp_to_dict(
        opp,
        db,
        is_favorited=is_favorited,
        has_applied=has_applied,
        viewer_openid=user.openid if user else "",
    )


# ── 创建资源 ─────────────────────────────────────────────

@router.post("")
def create_opportunity(
    body: OpportunityCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """发布就业资源"""
    # 检查用户认证要求
    if body.require_cert and user.cert_status != "verified":
        raise HTTPException(status_code=400, detail="需要完成实名认证才能发布资源")

    if body.require_school and not user.school:
        raise HTTPException(status_code=400, detail="需要完成校园认证才能发布资源")

    if user.level < body.require_level:
        raise HTTPException(status_code=400, detail=f"需要达到{body.require_level}级才能发布资源")

    opportunity_id = f"OPP{uuid.uuid4().hex[:10].upper()}"

    opportunity = Opportunity(
        id=opportunity_id,
        openid=user.openid,
        title=body.title,
        opportunity_type=body.opportunity_type,
        company_name=body.company_name,
        company_industry=body.company_industry,
        company_size=body.company_size,
        position=body.position,
        position_type=body.position_type,
        work_location=body.work_location,
        work_mode=body.work_mode,
        salary_range=body.salary_range,
        salary_hidden=body.salary_hidden,
        description=body.description,
        requirements=body.requirements,
        benefits=body.benefits,
        deadline=datetime.fromisoformat(body.deadline) if body.deadline else None,
        apply_url=body.apply_url,
        contact_wx=body.contact_wx,
        tags=body.tags,
        require_cert=body.require_cert,
        require_school=body.require_school,
        require_level=body.require_level,
    )
    db.add(opportunity)
    db.commit()

    return {"id": opportunity_id, "success": True}


# ── 更新资源 ─────────────────────────────────────────────

@router.put("/{opportunity_id}")
def update_opportunity(
    opportunity_id: str,
    body: OpportunityUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新就业资源（仅发布者可操作）"""
    opp = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not opp:
        raise HTTPException(status_code=404, detail="资源不存在")

    if opp.openid != user.openid:
        raise HTTPException(status_code=403, detail="仅发布者可修改")

    if body.title is not None:
        opp.title = body.title
    if body.company_name is not None:
        opp.company_name = body.company_name
    if body.company_industry is not None:
        opp.company_industry = body.company_industry
    if body.position is not None:
        opp.position = body.position
    if body.position_type is not None:
        opp.position_type = body.position_type
    if body.work_location is not None:
        opp.work_location = body.work_location
    if body.work_mode is not None:
        opp.work_mode = body.work_mode
    if body.salary_range is not None:
        opp.salary_range = body.salary_range
    if body.salary_hidden is not None:
        opp.salary_hidden = body.salary_hidden
    if body.description is not None:
        opp.description = body.description
    if body.requirements is not None:
        opp.requirements = body.requirements
    if body.benefits is not None:
        opp.benefits = body.benefits
    if body.deadline is not None:
        opp.deadline = datetime.fromisoformat(body.deadline)
    if body.apply_url is not None:
        opp.apply_url = body.apply_url
    if body.contact_wx is not None:
        opp.contact_wx = body.contact_wx
    if body.tags is not None:
        opp.tags = body.tags
    if body.status is not None:
        opp.status = body.status

    db.commit()
    return {"success": True}


# ── 删除资源 ─────────────────────────────────────────────

@router.delete("/{opportunity_id}")
def delete_opportunity(
    opportunity_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除就业资源（仅发布者可操作）"""
    opp = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not opp:
        raise HTTPException(status_code=404, detail="资源不存在")

    if opp.openid != user.openid:
        raise HTTPException(status_code=403, detail="仅发布者可删除")

    db.delete(opp)
    db.commit()
    return {"success": True}


@router.post("/{opportunity_id}/delete")
def delete_opportunity_compat(
    opportunity_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """兼容小程序端用 POST 模拟 DELETE 的调用方式"""
    return delete_opportunity(opportunity_id, user, db)


# ── 收藏资源 ─────────────────────────────────────────────

@router.post("/{opportunity_id}/favorite")
def toggle_favorite(
    opportunity_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """收藏/取消收藏就业资源"""
    opp = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not opp:
        raise HTTPException(status_code=404, detail="资源不存在")

    existing = db.query(OpportunityFavorite).filter(
        OpportunityFavorite.opportunity_id == opportunity_id,
        OpportunityFavorite.user_openid == user.openid
    ).first()

    if existing:
        # 取消收藏
        db.delete(existing)
        opp.favorite_count = max(0, opp.favorite_count - 1)
        db.commit()
        return {"success": True, "action": "removed", "is_favorited": False}
    else:
        # 添加收藏
        favorite = OpportunityFavorite(
            id=f"OPPF{int(datetime.now().timestamp() * 1000) % 1000000:06d}",
            opportunity_id=opportunity_id,
            user_openid=user.openid,
        )
        db.add(favorite)
        opp.favorite_count += 1
        db.commit()
        return {"success": True, "action": "added", "is_favorited": True}


# ── 我的收藏 ─────────────────────────────────────────────

@router.get("/favorites/mine")
def get_my_favorites(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """我的收藏列表"""
    query = db.query(OpportunityFavorite).filter(
        OpportunityFavorite.user_openid == user.openid
    ).order_by(OpportunityFavorite.created_at.desc())

    total = query.count()
    favorites = query.offset((page - 1) * page_size).limit(page_size).all()

    opportunity_ids = [f.opportunity_id for f in favorites]
    opportunities = db.query(Opportunity).filter(
        Opportunity.id.in_(opportunity_ids)
    ).all() if opportunity_ids else []

    opp_dict = {o.id: o for o in opportunities}

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "favorites": [_opp_to_dict(opp_dict[f.opportunity_id], db, is_favorited=True) for f in favorites if f.opportunity_id in opp_dict],
    }


# ── 申请资源 ─────────────────────────────────────────────

@router.post("/{opportunity_id}/apply")
def apply_opportunity(
    opportunity_id: str,
    body: ApplicationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """申请就业资源"""
    opp = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not opp:
        raise HTTPException(status_code=404, detail="资源不存在")

    if opp.status != OpportunityStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="该资源已关闭")

    # 检查截止日期
    if opp.deadline and opp.deadline < datetime.now():
        raise HTTPException(status_code=400, detail="已过申请截止日期")

    # 检查是否已申请
    existing = db.query(OpportunityApplication).filter(
        OpportunityApplication.opportunity_id == opportunity_id,
        OpportunityApplication.applicant_openid == user.openid
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="您已申请过该资源")

    # 不能申请自己的资源
    if opp.openid == user.openid:
        raise HTTPException(status_code=400, detail="不能申请自己发布的资源")

    # 检查认证要求
    if opp.require_cert and user.cert_status != "verified":
        raise HTTPException(status_code=400, detail="该资源需要实名认证")

    if opp.require_school and not user.school:
        raise HTTPException(status_code=400, detail="该资源需要校园认证")

    if user.level < opp.require_level:
        raise HTTPException(status_code=400, detail=f"该资源需要达到{opp.require_level}级")

    application_id = f"APPL{int(datetime.now().timestamp() * 1000) % 1000000:06d}"

    application = OpportunityApplication(
        id=application_id,
        opportunity_id=opportunity_id,
        applicant_openid=user.openid,
        message=body.message,
        resume_url=body.resume_url,
    )
    db.add(application)

    # 增加申请数
    opp.apply_count += 1
    db.commit()

    return {"id": application_id, "success": True}


# ── 处理申请 ─────────────────────────────────────────────

@router.put("/{opportunity_id}/applications/{application_id}")
def handle_application(
    opportunity_id: str,
    application_id: str,
    status: str = Query(..., description="accepted/rejected"),
    result_message: str = Query(""),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """处理申请（通过/拒绝，仅发布者可操作）"""
    opp = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not opp:
        raise HTTPException(status_code=404, detail="资源不存在")

    if opp.openid != user.openid:
        raise HTTPException(status_code=403, detail="仅发布者可处理")

    application = db.query(OpportunityApplication).filter(
        OpportunityApplication.id == application_id,
        OpportunityApplication.opportunity_id == opportunity_id
    ).first()
    if not application:
        raise HTTPException(status_code=404, detail="申请不存在")

    if application.status != ApplicationStatus.PENDING:
        raise HTTPException(status_code=400, detail="该申请已被处理")

    application.status = status
    application.result_message = result_message
    db.commit()

    return {"success": True, "status": status}


# ── 撤回申请 ─────────────────────────────────────────────

@router.post("/applications/{application_id}/withdraw")
def withdraw_application(
    application_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """撤回申请"""
    application = db.query(OpportunityApplication).filter(
        OpportunityApplication.id == application_id
    ).first()
    if not application:
        raise HTTPException(status_code=404, detail="申请不存在")

    if application.applicant_openid != user.openid:
        raise HTTPException(status_code=403, detail="只能撤回自己的申请")

    if application.status != ApplicationStatus.PENDING:
        raise HTTPException(status_code=400, detail="只能撤回待处理的申请")

    application.status = ApplicationStatus.WITHDRAWN

    # 减少申请数
    opp = db.query(Opportunity).filter(Opportunity.id == application.opportunity_id).first()
    if opp:
        opp.apply_count = max(0, opp.apply_count - 1)

    db.commit()
    return {"success": True}


# ── 辅助函数 ─────────────────────────────────────────────

def _opp_to_dict(
    opp: Opportunity,
    db: Session,
    is_favorited: bool = False,
    has_applied: bool = False,
    viewer_openid: str = "",
) -> dict:
    """Opportunity 模型转字典"""
    user = db.query(User).filter(User.openid == opp.openid).first()
    level_info = get_level_info(user.level) if user else {}

    # 获取申请状态
    application_status = None
    if has_applied and viewer_openid:
        app = db.query(OpportunityApplication).filter(
            OpportunityApplication.opportunity_id == opp.id,
            OpportunityApplication.applicant_openid == viewer_openid
        ).first()
        application_status = app.status if app else None

    return {
        "id": opp.id,
        "title": opp.title,
        "opportunity_type": opp.opportunity_type,
        "opportunity_type_name": _get_type_name(opp.opportunity_type),

        # 企业信息
        "company_name": opp.company_name,
        "company_industry": opp.company_industry,
        "company_size": opp.company_size,
        "company_logo": opp.company_logo,

        # 职位信息
        "position": opp.position,
        "position_type": opp.position_type,
        "work_location": opp.work_location,
        "work_mode": opp.work_mode,
        "work_mode_name": _get_work_mode_name(opp.work_mode),

        # 薪资
        "salary_range": opp.salary_range if not opp.salary_hidden else "面议",
        "salary_hidden": opp.salary_hidden,

        # 详情
        "description": opp.description,
        "requirements": opp.requirements,
        "benefits": opp.benefits,
        "tags": opp.tags or [],

        # 截止日期
        "deadline": opp.deadline.isoformat() if opp.deadline else None,
        "is_expired": opp.deadline < datetime.now() if opp.deadline else False,

        # 申请信息
        "apply_url": opp.apply_url,
        "contact_wx": opp.contact_wx,

        # 统计
        "view_count": opp.view_count,
        "favorite_count": opp.favorite_count,
        "apply_count": opp.apply_count,

        # 认证要求
        "require_cert": opp.require_cert,
        "require_school": opp.require_school,
        "require_level": opp.require_level,

        # 状态
        "status": opp.status,

        # 发布者信息
        "publisher": {
            "openid": opp.openid,
            "nickname": user.nickname if user else "未知",
            "avatar_url": user.avatar_url if user else "",
            "school": user.school if user else "",
            "level": user.level if user else 1,
            "level_name": level_info.get("name", ""),
            "level_icon": level_info.get("icon", ""),
            "cert_status": user.cert_status if user else "none",
        } if user else None,

        # 当前用户状态
        "is_favorited": is_favorited,
        "has_applied": has_applied,
        "application_status": application_status,

        "created_at": opp.created_at.isoformat() if opp.created_at else "",
        "updated_at": opp.updated_at.isoformat() if opp.updated_at else "",
    }


def _application_to_dict(app: OpportunityApplication, db: Session, include_applicant_info: bool = False) -> dict:
    """Application 模型转字典"""
    result = {
        "id": app.id,
        "opportunity_id": app.opportunity_id,
        "applicant_openid": app.applicant_openid,
        "message": app.message,
        "resume_url": app.resume_url,
        "status": app.status,
        "status_name": _get_application_status_name(app.status),
        "result_message": app.result_message,
        "created_at": app.created_at.isoformat() if app.created_at else "",
        "updated_at": app.updated_at.isoformat() if app.updated_at else "",
    }

    if include_applicant_info:
        user = db.query(User).filter(User.openid == app.applicant_openid).first()
        level_info = get_level_info(user.level) if user else {}
        result["applicant"] = {
            "openid": app.applicant_openid,
            "nickname": user.nickname if user else "未知",
            "avatar_url": user.avatar_url if user else "",
            "school": user.school if user else "",
            "level": user.level if user else 1,
            "level_name": level_info.get("name", ""),
            "level_icon": level_info.get("icon", ""),
            "cert_status": user.cert_status if user else "none",
            "bio": user.bio if user else "",
        } if user else None

    return result


def _get_type_name(opp_type: str) -> str:
    """获取资源类型名称"""
    names = {
        "internship": "寻觅道场（实习）",
        "referral": "求取推荐（内推）",
        "job": "问道职涯（求职）",
        "job_resource": "布施机缘（资源）",
    }
    return names.get(opp_type, opp_type)


def _get_work_mode_name(mode: str) -> str:
    """获取工作模式名称"""
    names = {
        "onsite": "现场办公",
        "remote": "远程工作",
        "hybrid": "混合办公",
    }
    return names.get(mode, mode)


def _get_application_status_name(status: str) -> str:
    """获取申请状态名称"""
    names = {
        "pending": "待处理",
        "accepted": "已通过",
        "rejected": "已拒绝",
        "withdrawn": "已撤回",
    }
    return names.get(status, status)
