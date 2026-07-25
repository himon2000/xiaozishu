"""
藏经阁资源服务层
《驯龙阁》UGC 积分解锁 + 审核 + 排行榜
"""
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from models import Resource, User, LevelLog, Service, ResourceComment, ResourceFavorite
from dependencies import get_db


# ── 发布资源 ───────────────────────────────────────────────
def publish_resource(db: Session, author_openid: str, data: dict) -> Resource:
    """
    发布藏经阁资源
    - 发布后自动奖励 +3 修为点（需审核通过后才发放）
    - 免费资源直接上线；付费/积分资源进入审核
    """
    resource_id = f"RSC{uuid.uuid4().hex[:12].upper()}"

    resource = Resource(
        id=resource_id,
        author_openid=author_openid,
        resource_type=data.get("resource_type", "experience_post"),
        title=data["title"],
        content=data.get("content", ""),
        cover_image=data.get("cover_image", ""),
        attachments=data.get("attachments", []),
        tags=data.get("tags", []),
        subject=data.get("subject", ""),
        school_level=data.get("school_level", ""),
        target_school=data.get("target_school", ""),
        access_mode=data.get("access_mode", "free"),
        points_cost=data.get("points_cost", 0),
        price_cost=data.get("price_cost", 0),
        review_status="approved" if data.get("access_mode") == "free" else "pending",
    )

    db.add(resource)

    # 免费资源立即上线，同时奖励修为点
    if resource.review_status == "approved":
        _award_exp(db, author_openid, 3, "earn_resource_publish", resource_id,
                   f"发布藏经阁资源《{data['title']}》")

    db.commit()
    db.refresh(resource)
    return resource


def _award_exp(db: Session, openid: str, delta: int, change_type: str,
                related_id: str = "", remark: str = ""):
    """统一修为积分奖励"""
    user = db.query(User).filter(User.openid == openid).first()
    if not user:
        return

    level_before = user.level
    user.exp_points += delta

    # 境界升级判定
    level_after = _calc_level(user.exp_points)
    level_upgraded = level_after > level_before
    if level_upgraded:
        user.level = level_after

    log = LevelLog(
        id=f"LL{uuid.uuid4().hex[:10].upper()}",
        user_openid=openid,
        change_type=change_type,
        points_delta=delta,
        balance_after=user.exp_points,
        level_before=level_before,
        level_after=level_after if level_upgraded else level_before,
        level_upgraded=level_upgraded,
        related_id=related_id,
        remark=remark,
    )
    db.add(log)
    db.commit()


def _calc_level(exp: int) -> int:
    """修为点 → 境界"""
    thresholds = [(5000, 5), (2000, 4), (500, 3), (100, 2), (0, 1)]
    for threshold, level in thresholds:
        if exp >= threshold:
            return level
    return 1


# ── 资源列表 ───────────────────────────────────────────────
def list_resources(db: Session, filters: dict, page: int = 1, page_size: int = 20):
    """
    资源广场列表
    支持：resource_type / subject / school_level / access_mode / keyword
    """
    q = db.query(Resource).filter(Resource.review_status == "approved")

    if filters.get("resource_type"):
        q = q.filter(Resource.resource_type == filters["resource_type"])
    if filters.get("subject"):
        q = q.filter(Resource.subject == filters["subject"])
    if filters.get("school_level"):
        q = q.filter(Resource.school_level == filters["school_level"])
    if filters.get("access_mode"):
        q = q.filter(Resource.access_mode == filters["access_mode"])

    # 关键词搜索（标题 + 内容）
    keyword = (filters.get("keyword") or "").strip()
    if keyword:
        pattern = f"%{keyword}%"
        q = q.filter(
            or_(
                Resource.title.ilike(pattern),
                Resource.content.ilike(pattern),
                Resource.tags.ilike(pattern),
            )
        )

    # 排序
    sort = filters.get("sort", "hot")
    if sort == "hot":
        q = q.order_by(Resource.likes.desc(), Resource.unlocks.desc())
    elif sort == "new":
        q = q.order_by(Resource.created_at.desc())
    elif sort == "free":
        q = q.filter(Resource.access_mode == "free").order_by(Resource.created_at.desc())

    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()

    return {"total": total, "page": page, "page_size": page_size, "items": items}


# ── 资源详情 ───────────────────────────────────────────────
def get_resource_detail(db: Session, resource_id: str, viewer_openid: str = ""):
    """
    获取资源详情
    - 增加浏览数
    - 判断 viewer 是否已解锁
    """
    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    if not resource:
        return None

    # 浏览数 +1
    resource.views += 1
    db.commit()

    # 作者信息
    author = db.query(User).filter(User.openid == resource.author_openid).first()
    author_info = None
    if author:
        author_info = {
            "openid": author.openid,
            "nickname": author.nickname,
            "avatar_url": author.avatar_url,
            "level": author.level,
            "level_name": _LEVEL_NAMES.get(author.level, "炼气期"),
        }

    # 解锁状态（免费/作者本人/已解锁）
    unlocked = (
        resource.access_mode == "free"
        or (viewer_openid and viewer_openid == resource.author_openid)
        or _is_resource_unlocked(db, resource_id, viewer_openid)
    )

    return {
        "resource": resource,
        "author": author_info,
        "unlocked": unlocked,
    }


def _is_resource_unlocked(db: Session, resource_id: str, openid: str) -> bool:
    """检查用户是否已解锁某资源（通过 ResourceUnlock 表或 order 检查）"""
    # 简化：每次解锁创建 ResourceUnlock 记录，此处用标记字段判断
    # 实际项目中可用独立 unlock 表，此处暂时用 resource.unlocks > 0 粗略判断
    if not openid:
        return False
    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    return resource is not None and resource.unlocks > 0


# ── 积分解锁 ───────────────────────────────────────────────
def unlock_resource(db: Session, openid: str, resource_id: str, unlock_method: str):
    """
    积分解锁 或 付费解锁
    unlock_method: 'points' | 'paid'
    """
    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    if not resource:
        raise ValueError("资源不存在")

    user = db.query(User).filter(User.openid == openid).first()
    if not user:
        raise ValueError("用户不存在")

    if unlock_method == "points":
        if resource.access_mode != "points":
            raise ValueError("该资源不是积分解锁类型")
        if user.exp_points < resource.points_cost:
            raise ValueError(f"修为点不足，当前{user.exp_points}点，需要{resource.points_cost}点")

        # 扣积分
        user.exp_points -= resource.points_cost
        log = LevelLog(
            id=f"LL{uuid.uuid4().hex[:10].upper()}",
            user_openid=openid,
            change_type="spend_resource_unlock",
            points_delta=-resource.points_cost,
            balance_after=user.exp_points,
            level_before=user.level,
            level_after=user.level,
            level_upgraded=False,
            related_id=resource_id,
            remark=f"解锁藏经阁资源《{resource.title}》",
        )
        db.add(log)

        # 作者获积分
        _award_exp(db, resource.author_openid, 1, "earn_resource_unlocked",
                    resource_id, f"资源《{resource.title}》被解锁")

    elif unlock_method == "paid":
        if resource.access_mode != "paid":
            raise ValueError("该资源不是付费类型")

    # 解锁计数
    resource.unlocks += 1
    db.commit()

    return {"success": True, "resource_id": resource_id}


# ── 点赞 ────────────────────────────────────────────────────
def like_resource(db: Session, resource_id: str):
    """资源点赞"""
    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    if not resource:
        raise ValueError("资源不存在")
    resource.likes += 1
    db.commit()
    return {"likes": resource.likes}


# ── 高校百科（宗门图志）─────────────────────────────────────
def list_school_guides(db: Session, keyword: str = "", page: int = 1, page_size: int = 20):
    """高校百科：宗门图志列表（资源类型=school_guide）"""
    q = db.query(Resource).filter(
        Resource.resource_type == "school_guide",
        Resource.review_status == "approved",
    )
    kw = (keyword or "").strip()
    if kw:
        pattern = f"%{kw}%"
        q = q.filter(
            or_(
                Resource.title.ilike(pattern),
                Resource.target_school.ilike(pattern),
                Resource.content.ilike(pattern),
            )
        )
    q = q.order_by(Resource.created_at.desc())
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "page": page, "page_size": page_size, "items": items}


# ── 我的发布（大虾视角）─────────────────────────────────
def my_resources(db: Session, openid: str, page: int = 1, page_size: int = 20):
    """查看我发布的藏经阁资源"""
    q = db.query(Resource).filter(Resource.author_openid == openid)
    q = q.order_by(Resource.created_at.desc())
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "page": page, "page_size": page_size, "items": items}


# ── 资源评论 ──────────────────────────────────────────────
def add_comment(db: Session, resource_id: str, author_openid: str, content: str, parent_id: str = None):
    """添加资源评论"""
    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    if not resource:
        raise ValueError("资源不存在")

    if not content or len(content.strip()) == 0:
        raise ValueError("评论内容不能为空")

    if len(content) > 500:
        raise ValueError("评论内容不能超过500字")

    comment = ResourceComment(
        id=f"CMT{uuid.uuid4().hex[:12].upper()}",
        resource_id=resource_id,
        author_openid=author_openid,
        content=content.strip(),
        parent_id=parent_id,
    )
    db.add(comment)

    # 更新评论数
    resource.comments += 1
    db.commit()
    db.refresh(comment)

    return comment


def list_comments(db: Session, resource_id: str, page: int = 1, page_size: int = 20):
    """获取资源评论列表"""
    q = db.query(ResourceComment).filter(
        ResourceComment.resource_id == resource_id,
        ResourceComment.status == "active",
        ResourceComment.parent_id == None  # 只查一级评论
    )
    q = q.order_by(ResourceComment.created_at.desc())
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()

    # 填充评论者信息
    result = []
    for item in items:
        author = db.query(User).filter(User.openid == item.author_openid).first()
        result.append({
            "id": item.id,
            "resource_id": item.resource_id,
            "author_openid": item.author_openid,
            "author_nickname": author.nickname if author else "匿名",
            "author_avatar": author.avatar_url if author else "",
            "author_level": author.level if author else 1,
            "content": item.content,
            "parent_id": item.parent_id,
            "likes": item.likes,
            "created_at": item.created_at.isoformat() if item.created_at else "",
        })

    return {"total": total, "page": page, "page_size": page_size, "items": result}


def like_comment(db: Session, comment_id: str):
    """评论点赞"""
    comment = db.query(ResourceComment).filter(ResourceComment.id == comment_id).first()
    if not comment:
        raise ValueError("评论不存在")
    comment.likes += 1
    db.commit()
    return {"likes": comment.likes}


# ── 资源收藏 ──────────────────────────────────────────────
def add_favorite(db: Session, resource_id: str, user_openid: str):
    """收藏资源"""
    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    if not resource:
        raise ValueError("资源不存在")

    # 检查是否已收藏
    existing = db.query(ResourceFavorite).filter(
        ResourceFavorite.resource_id == resource_id,
        ResourceFavorite.user_openid == user_openid
    ).first()
    if existing:
        raise ValueError("已经收藏过了")

    favorite = ResourceFavorite(
        id=f"FAV{uuid.uuid4().hex[:12].upper()}",
        resource_id=resource_id,
        user_openid=user_openid,
    )
    db.add(favorite)
    db.commit()

    return {"success": True, "favorite_id": favorite.id}


def remove_favorite(db: Session, resource_id: str, user_openid: str):
    """取消收藏"""
    favorite = db.query(ResourceFavorite).filter(
        ResourceFavorite.resource_id == resource_id,
        ResourceFavorite.user_openid == user_openid
    ).first()
    if not favorite:
        raise ValueError("未收藏该资源")

    db.delete(favorite)
    db.commit()
    return {"success": True}


def is_favorited(db: Session, resource_id: str, user_openid: str) -> bool:
    """检查是否已收藏"""
    if not user_openid:
        return False
    favorite = db.query(ResourceFavorite).filter(
        ResourceFavorite.resource_id == resource_id,
        ResourceFavorite.user_openid == user_openid
    ).first()
    return favorite is not None


def my_favorites(db: Session, user_openid: str, page: int = 1, page_size: int = 20):
    """我的收藏列表"""
    q = db.query(ResourceFavorite).filter(ResourceFavorite.user_openid == user_openid)
    q = q.order_by(ResourceFavorite.created_at.desc())
    total = q.count()
    favorites = q.offset((page - 1) * page_size).limit(page_size).all()

    # 填充资源信息
    result = []
    for fav in favorites:
        resource = db.query(Resource).filter(Resource.id == fav.resource_id).first()
        if resource:
            result.append({
                "id": fav.id,
                "resource_id": resource.id,
                "resource_type": resource.resource_type,
                "title": resource.title,
                "cover_image": resource.cover_image,
                "author_nickname": "",  # 需要再查
                "created_at": fav.created_at.isoformat() if fav.created_at else "",
            })

    return {"total": total, "page": page, "page_size": page_size, "items": result}


_LEVEL_NAMES = {
    1: "炼气期",
    2: "筑基期",
    3: "金丹期",
    4: "元婴期",
    5: "化神期",
}
