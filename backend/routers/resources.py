"""
藏经阁资源路由
GET  /api/v1/resources              资源列表
GET  /api/v1/resources/categories   资源分类
GET  /api/v1/resources/{id}         资源详情
POST /api/v1/resources              发布资源
POST /api/v1/resources/{id}/unlock  积分/付费解锁
POST /api/v1/resources/{id}/like    点赞
GET  /api/v1/resources/mine         我的发布
GET  /api/v1/resources/school-guides 高校百科
GET  /api/v1/resources/{id}/comments    评论列表
POST /api/v1/resources/{id}/comments   添加评论
POST /api/v1/resources/{id}/favorite   收藏/取消收藏
GET  /api/v1/resources/favorites    我的收藏
"""
from fastapi import APIRouter, Depends, Query, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from dependencies import get_db, get_current_user, get_current_user_optional
from services import resource_service
from utils.db import get_db as get_db_session
from models import Resource, ResourceFavorite, User
from sqlalchemy import func
from utils.content_guard import guard_user_content
from config import get_settings


# ═══════════════════════════════════════════════════════════
# 资源分类与标签
# ═══════════════════════════════════════════════════════════

RESOURCE_CATEGORIES = [
    {
        "id": "notes",
        "name": "学习笔记",
        "icon": "icon-note",
        "description": "课程笔记、考前复习、知识点总结",
    },
    {
        "id": "materials",
        "name": "复习资料",
        "icon": "icon-file",
        "description": "课件、习题集、往年试卷",
    },
    {
        "id": "experience",
        "name": "经验分享",
        "icon": "icon-star",
        "description": "考研、竞赛、实习经验贴",
    },
    {
        "id": "tools",
        "name": "工具资源",
        "icon": "icon-tool",
        "description": "效率工具、软件教程、学习资源",
    },
]

RESOURCE_SUBJECTS = [
    "高等数学", "线性代数", "概率论", "大学物理",
    "计算机基础", "数据结构", "算法设计", "机器学习",
    "英语", "政治", "专业课", "其他",
]

RESOURCE_TAGS = [
    "考研", "期末复习", "竞赛", "留学", "实习",
    "保研", "转专业", "奖学金", "社团", "就业",
]


router = APIRouter(prefix="/api/v1/resources", tags=["藏经阁"])


@router.get("")
def list_resources(
    resource_type: str = Query(None, description="资源类型"),
    subject: str = Query(None),
    school_level: str = Query(None),
    access_mode: str = Query(None, description="free | points | paid"),
    keyword: str = Query(None),
    sort: str = Query("hot", description="hot | new | free"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    """藏经阁资源广场"""
    result = resource_service.list_resources(
        db,
        filters={
            "resource_type": resource_type,
            "subject": subject,
            "school_level": school_level,
            "access_mode": access_mode,
            "keyword": keyword,
            "sort": sort,
        },
        page=page,
        page_size=page_size,
    )
    viewer = current_user.openid if current_user else ""
    items = [_resource_summary(r, db, viewer) for r in result["items"]]
    return {"code": 0, "data": {**result, "items": items}}


@router.get("/school-guides")
def list_school_guides(
    keyword: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """高校百科 - 宗门图志"""
    result = resource_service.list_school_guides(db, keyword, page, page_size)
    items = [_resource_summary(r, db) for r in result["items"]]
    return {"code": 0, "data": {**result, "items": items}}


@router.get("/mine")
def my_resources(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """我的发布（大虾视角）"""
    result = resource_service.my_resources(db, current_user.openid, page, page_size)
    items = [_resource_summary(r, db, current_user.openid) for r in result["items"]]
    return {"code": 0, "data": {**result, "items": items}}


# 注意：/categories 必须放在 /{resource_id} 之前，否则会被资源ID匹配
@router.get("/categories")
def get_resource_categories():
    """获取藏经阁资源分类"""
    return {
        "code": 0,
        "data": {
            "categories": RESOURCE_CATEGORIES,
            "subjects": RESOURCE_SUBJECTS,
            "tags": RESOURCE_TAGS,
        }
    }


@router.post("")
def publish_resource(
    payload: dict,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    发布藏经阁资源
    - 免费资源直接上线，奖励 +3 修为点
    - 付费/积分资源需审核
    """
    if not payload.get("title"):
        return {"code": 400, "message": "标题不能为空"}
    guard_user_content(current_user.openid, payload)
    if not get_settings().payment_enabled and payload.get("access_mode", "free") != "free":
        return {"code": 403, "message": "当前版本仅允许发布免费内容"}

    try:
        resource = resource_service.publish_resource(
            db, current_user.openid, payload
        )
        return {
            "code": 0,
            "data": {
                "id": resource.id,
                "review_status": resource.review_status,
                "message": "发布成功"
                + ("，审核通过后奖励 +3 修为点"
                   if resource.review_status != "approved"
                   else "，已奖励 +3 修为点"),
            },
        }
    except Exception as e:
        return {"code": 500, "message": str(e)}


@router.post("/{resource_id}/unlock")
def unlock_resource(
    resource_id: str,
    unlock_method: str = Query(..., description="points | paid"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """积分解锁或付费解锁资源"""
    try:
        result = resource_service.unlock_resource(
            db, current_user.openid, resource_id, unlock_method
        )
        return {"code": 0, "data": result}
    except ValueError as e:
        return {"code": 400, "message": str(e)}
    except Exception as e:
        return {"code": 500, "message": str(e)}


@router.post("/{resource_id}/like")
def like_resource(
    resource_id: str,
    db: Session = Depends(get_db),
):
    """资源点赞"""
    try:
        result = resource_service.like_resource(db, resource_id)
        return {"code": 0, "data": result}
    except ValueError as e:
        return {"code": 400, "message": str(e)}


# ── 评论相关 ────────────────────────────────────────────────
class CommentPayload(BaseModel):
    content: str
    parent_id: str = None


@router.get("/{resource_id}/comments")
def list_resource_comments(
    resource_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """资源评论列表"""
    result = resource_service.list_comments(db, resource_id, page, page_size)
    return {"code": 0, "data": result}


@router.post("/{resource_id}/comments")
def add_resource_comment(
    resource_id: str,
    payload: CommentPayload,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """添加资源评论"""
    guard_user_content(current_user.openid, payload.content)
    try:
        comment = resource_service.add_comment(
            db, resource_id, current_user.openid, payload.content, payload.parent_id
        )
        return {
            "code": 0,
            "data": {
                "id": comment.id,
                "content": comment.content,
                "created_at": comment.created_at.isoformat() if comment.created_at else "",
            }
        }
    except ValueError as e:
        return {"code": 400, "message": str(e)}
    except Exception as e:
        return {"code": 500, "message": str(e)}


@router.post("/{resource_id}/comments/{comment_id}/like")
def like_comment(
    resource_id: str,
    comment_id: str,
    db: Session = Depends(get_db),
):
    """评论点赞"""
    try:
        result = resource_service.like_comment(db, comment_id)
        return {"code": 0, "data": result}
    except ValueError as e:
        return {"code": 400, "message": str(e)}


# ── 收藏相关 ────────────────────────────────────────────────
@router.post("/{resource_id}/favorite")
def toggle_favorite(
    resource_id: str,
    action: str = Query(..., description="add | remove"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """收藏或取消收藏资源"""
    try:
        if action == "add":
            result = resource_service.add_favorite(db, resource_id, current_user.openid)
        else:
            result = resource_service.remove_favorite(db, resource_id, current_user.openid)
        return {"code": 0, "data": result}
    except ValueError as e:
        return {"code": 400, "message": str(e)}
    except Exception as e:
        return {"code": 500, "message": str(e)}


@router.get("/{resource_id}/favorite/status")
def check_favorite_status(
    resource_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    """检查收藏状态"""
    is_favorited = resource_service.is_favorited(db, resource_id, current_user.openid if current_user else "")
    return {"code": 0, "data": {"is_favorited": is_favorited}}


@router.get("/favorites")
def my_favorite_resources(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """我的收藏列表"""
    result = resource_service.my_favorites(db, current_user.openid, page, page_size)
    items = []
    for favorite in result["items"]:
        resource = db.query(Resource).filter(Resource.id == favorite["resource_id"]).first()
        if resource:
            items.append(_resource_summary(resource, db, current_user.openid))
    return {"code": 0, "data": {**result, "items": items}}


# ── 内部辅助 ────────────────────────────────────────────────
def _resource_summary(r: Resource, db: Session, viewer_openid: str = "") -> dict:
    """资源摘要（列表用）"""
    author = db.query(User).filter(User.openid == r.author_openid).first()
    is_favorited = bool(viewer_openid) and db.query(ResourceFavorite).filter(
        ResourceFavorite.resource_id == r.id,
        ResourceFavorite.user_openid == viewer_openid,
    ).first() is not None
    return {
        "id": r.id,
        "resource_type": r.resource_type,
        "category": r.resource_type,
        "title": r.title,
        "description": r.content or "",
        "cover_image": r.cover_image,
        "tags": r.tags,
        "subject": r.subject,
        "school_level": r.school_level,
        "access_mode": r.access_mode,
        "points_cost": r.points_cost,
        "price_cost": r.price_cost,
        "views": r.views,
        "likes": r.likes,
        "unlocks": r.unlocks,
        "is_featured": r.is_featured,
        "review_status": r.review_status,
        "is_favorited": is_favorited,
        "author_openid": r.author_openid,
        "author": {
            "openid": author.openid if author else r.author_openid,
            "nickname": author.nickname if author else "匿名",
            "avatar_url": author.avatar_url if author else "",
        },
        "created_at": r.created_at.isoformat() if r.created_at else "",
    }


# ==================== 藏经阁增强接口 ====================

@router.get("/hot")
def get_hot_resources(
    resource_type: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    """
    获取热门资源推荐
    - 基于浏览量、点赞数、收藏数综合排序
    """
    query = db.query(Resource).filter(Resource.review_status == "approved")

    if resource_type:
        query = query.filter(Resource.resource_type == resource_type)

    resources = query.order_by(
        (Resource.views + Resource.likes * 3 + Resource.unlocks * 5).desc()
    ).limit(limit).all()

    return {
        "code": 0,
        "data": {
            "resource_type": resource_type or "all",
            "resources": [
                _resource_summary(r, db, current_user.openid if current_user else "")
                for r in resources
            ]
        }
    }


@router.get("/author/{openid}")
def get_author_resources(
    openid: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """
    获取作者的资源列表
    """
    query = db.query(Resource).filter(
        Resource.author_openid == openid,
        Resource.review_status == "approved"
    )

    total = query.count()
    resources = query.order_by(Resource.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    # 作者信息
    author = db.query(User).filter(User.openid == openid).first()
    author_info = {}
    if author:
        from services.level_service import get_level_info
        info = get_level_info(author.level)
        author_info = {
            "openid": author.openid,
            "nickname": author.nickname,
            "avatar_url": author.avatar_url,
            "level": author.level,
            "level_name": info["name"],
            "school": author.school,
        }

    return {
        "code": 0,
        "data": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "author": author_info,
            "resources": [_resource_summary(r, db) for r in resources]
        }
    }


@router.get("/stats/overview")
def get_resources_overview(
    db: Session = Depends(get_db),
):
    """
    获取藏经阁总览统计
    """
    total_resources = db.query(Resource).filter(Resource.review_status == "approved").count()

    # 各分类统计
    categories = ["notes", "materials", "experience", "tools"]
    category_stats = {}

    for cat in categories:
        count = db.query(Resource).filter(
            Resource.resource_type == cat,
            Resource.review_status == "approved"
        ).count()
        total_views = db.query(func.sum(Resource.views)).filter(
            Resource.resource_type == cat,
            Resource.review_status == "approved"
        ).scalar() or 0

        category_stats[cat] = {
            "count": count,
            "total_views": int(total_views),
        }

    # 总统计
    total_views = db.query(func.sum(Resource.views)).filter(
        Resource.review_status == "approved"
    ).scalar() or 0
    total_likes = db.query(func.sum(Resource.likes)).filter(
        Resource.review_status == "approved"
    ).scalar() or 0

    return {
        "code": 0,
        "data": {
            "total_resources": total_resources,
            "total_views": int(total_views),
            "total_likes": int(total_likes),
            "category_stats": category_stats,
        }
    }


@router.post("/{resource_id}/view")
def record_resource_view(
    resource_id: str,
    db: Session = Depends(get_db),
):
    """
    记录资源浏览
    """
    r = db.query(Resource).filter(Resource.id == resource_id).first()
    if not r:
        return {"code": 404, "message": "资源不存在"}

    r.views = (r.views or 0) + 1
    db.commit()

    return {"code": 0, "data": {"views": r.views}}


@router.get("/search/suggestions")
def get_search_suggestions(
    keyword: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """
    获取搜索建议（关键词补全）
    """
    resources = db.query(Resource).filter(
        Resource.review_status == "approved",
        Resource.title.contains(keyword)
    ).limit(limit).all()

    suggestions = [
        {"id": r.id, "title": r.title, "type": r.resource_type}
        for r in resources
    ]

    return {"code": 0, "data": {"suggestions": suggestions}}


# 通配详情路由必须放在所有固定 GET 路由之后，避免把 /favorites、/hot 等当作资源 ID。
@router.get("/{resource_id}")
def get_resource_detail(
    resource_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    """资源详情（含解锁与收藏状态）"""
    viewer = current_user.openid if current_user else ""
    result = resource_service.get_resource_detail(db, resource_id, viewer)
    if not result:
        return {"code": 404, "message": "资源不存在"}

    r = result["resource"]
    return {
        "code": 0,
        "data": {
            "id": r.id,
            "author_openid": r.author_openid,
            "author": result["author"],
            "resource_type": r.resource_type,
            "category": r.resource_type,
            "title": r.title,
            "description": r.content or "",
            "content": r.content if result["unlocked"] else "",
            "cover_image": r.cover_image,
            "attachments": r.attachments if result["unlocked"] else [],
            "tags": r.tags,
            "subject": r.subject,
            "school_level": r.school_level,
            "target_school": r.target_school,
            "access_mode": r.access_mode,
            "points_cost": r.points_cost,
            "price_cost": r.price_cost,
            "views": r.views,
            "likes": r.likes,
            "unlocks": r.unlocks,
            "unlocked": result["unlocked"],
            "is_featured": r.is_featured,
            "is_favorited": resource_service.is_favorited(db, r.id, viewer),
            "is_liked": False,
            "created_at": r.created_at.isoformat() if r.created_at else "",
        },
    }
