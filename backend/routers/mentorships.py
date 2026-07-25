"""
道友传承体系路由
企业导师（长老）+ 学术导师（大虾/金丹期+）双轨体系
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from utils.db import get_db
from models import User
from dependencies import get_current_user
from services import mentor_service
from services.level_service import add_exp

router = APIRouter(prefix="/api/v1/mentorships", tags=["道友传承"])


class MentorshipApply(BaseModel):
    mentor_openid: str
    message: str = ""
    mentor_type: str = "academic"     # enterprise=企业导师，academic=学术导师
    mentor_direction: str = "academic"  # employment=就业方向，academic=学术方向


class MilestoneRecord(BaseModel):
    event: str   # disciple_graduated | exam_passed | offer_received | next_mentor_created
    remark: str = ""


@router.get("/mentors")
def list_mentors(
    mentor_type: Optional[str] = Query(None, description="导师类型: enterprise=企业导师, academic=学术导师"),
    min_level: Optional[int] = Query(None),
    subject: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """
    寻访导师列表（支持按导师类型筛选）
    - enterprise（企业导师）：长老角色，职场方向传承
    - academic（学术导师）：金丹期+大虾，升学方向传承
    """
    query = db.query(User).filter(User.role.in_(["provider", "elder"]), User.available == True)

    # 企业导师：role=elder 优先；学术导师：role=provider 且 level>=3
    if mentor_type == "enterprise":
        query = query.filter(User.role == "elder")
    elif mentor_type == "academic":
        query = query.filter(User.role == "provider", User.level >= 3)

    if min_level:
        query = query.filter(User.level >= min_level)
    total = query.count()
    mentors = query.order_by(User.exp_points.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "mentor_type": mentor_type or "all",
        "mentors": [_mentor_to_dict(m, db, mentor_type) for m in mentors],
    }


@router.post("/apply")
def apply_mentorship(
    body: MentorshipApply,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    申请道友传承（散修视角）
    散修可同时持有 1 名企业导师 + 1 名学术导师
    """
    # 消耗5修为点（防刷）
    if user.exp_points < 5:
        raise HTTPException(status_code=400, detail="修为点不足5点，无法申请道友传承")
    add_exp(db, user, "spend_apply_mentor", remark=f"申请道友传承 {body.mentor_openid} ({body.mentor_type})")

    mentor = db.query(User).filter(User.openid == body.mentor_openid).first()
    if not mentor:
        raise HTTPException(status_code=404, detail="导师不存在")

    # 校验导师类型与角色匹配
    if body.mentor_type == "enterprise" and mentor.role != "elder":
        raise HTTPException(status_code=400, detail="该用户不是企业导师")
    if body.mentor_type == "academic" and mentor.role != "provider":
        raise HTTPException(status_code=400, detail="该用户不是学术导师")
    if body.mentor_type == "academic" and mentor.level < 3:
        raise HTTPException(status_code=400, detail="学术导师需达到金丹期（Lv.3）以上")

    # 检查是否已有与此导师的传承关系
    existing = mentor_service.check_existing_mentorship(db, user.openid, body.mentor_openid, body.mentor_type)
    if existing:
        return {"success": True, "mentorship_id": existing.id, "message": "您已有此导师的传承关系"}

    # 检查双轨上限：同一类型导师最多 1 名
    type_count = mentor_service.count_active_mentorship_by_type(db, user.openid, body.mentor_type)
    if type_count >= 1:
        type_label = "企业导师" if body.mentor_type == "enterprise" else "学术导师"
        raise HTTPException(status_code=400, detail=f"您已有 1 名{type_label}，同一类型导师最多持有 1 名")

    # 建立传承关系
    mentorship = mentor_service.create_mentorship(
        db, mentor, user,
        mentor_type=body.mentor_type,
        mentor_direction=body.mentor_direction,
        application_reason=body.message,
    )
    return {
        "success": True,
        "mentorship_id": mentorship.id,
        "mentor_type": body.mentor_type,
        "message": f"成功拜入{mentor.nickname}门下，开启{body.mentor_type}道友传承！",
    }


@router.get("/mine")
def my_mentorships(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """我的道友传承关系（作为被传承者 / 作为导师）"""
    as_disciple = db.query(mentor_service.Mentorship).filter(
        mentor_service.Mentorship.disciple_openid == user.openid,
        mentor_service.Mentorship.status == "active"
    ).all()

    as_mentor = db.query(mentor_service.Mentorship).filter(
        mentor_service.Mentorship.mentor_openid == user.openid,
        mentor_service.Mentorship.status == "active"
    ).all()

    return {
        "as_disciple": [_mentorship_to_dict(m, db) for m in as_disciple],
        "as_mentor": [_mentorship_to_dict(m, db) for m in as_mentor],
    }


@router.get("/{mentorship_id}/lineage")
def get_lineage_tree(
    mentorship_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """传承树数据"""
    m = db.query(mentor_service.Mentorship).filter(
        mentor_service.Mentorship.id == mentorship_id
    ).first()
    if not m:
        raise HTTPException(status_code=404, detail="道友传承关系不存在")
    # 权限：只有导师或被传承者本人可见
    if user.openid not in [m.mentor_openid, m.disciple_openid]:
        raise HTTPException(status_code=403, detail="无权查看")

    return mentor_service.build_lineage_tree(db, user.openid)


@router.post("/{mentorship_id}/milestone")
def record_milestone(
    mentorship_id: str,
    body: MilestoneRecord,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """记录被传承者里程碑（导师操作）"""
    m = db.query(mentor_service.Mentorship).filter(
        mentor_service.Mentorship.id == mentorship_id
    ).first()
    if not m:
        raise HTTPException(status_code=404, detail="道友传承关系不存在")
    if user.openid != m.mentor_openid:
        raise HTTPException(status_code=403, detail="只有导师可以记录里程碑")

    result = mentor_service.graduate_mentorship(db, m, event=body.event, remark=body.remark)
    return result


@router.post("/{mentorship_id}/dissolve")
def dissolve(
    mentorship_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """解除道友传承关系"""
    m = db.query(mentor_service.Mentorship).filter(
        mentor_service.Mentorship.id == mentorship_id
    ).first()
    if not m:
        raise HTTPException(status_code=404, detail="道友传承关系不存在")
    if user.openid not in [m.mentor_openid, m.disciple_openid]:
        raise HTTPException(status_code=403, detail="无权操作")

    success = mentor_service.dissolve_mentorship(db, mentorship_id)
    return {"success": success}


def _mentor_to_dict(user: User, db, mentor_type: str = None) -> dict:
    from services.level_service import get_level_info
    info = get_level_info(user.level)
    # 根据导师类型决定展示方向标签
    if mentor_type == "enterprise":
        direction_label = "就业方向"
    elif mentor_type == "academic":
        direction_label = "学术方向"
    else:
        direction_label = "综合方向"
    return {
        "openid": user.openid,
        "nickname": user.nickname,
        "avatar_url": user.avatar_url,
        "level": user.level,
        "level_name": info["name"],
        "level_color": info["color"],
        "level_icon": info["icon"],
        "school": user.school,
        "major": user.major,
        "provider_tagline": user.provider_tagline,
        "specialties": user.specialties or [],
        "rating": user.rating,
        "rating_count": user.rating_count,
        "active_disciples": user.active_disciples,
        "total_disciples": user.total_disciples,
        "cert_status": user.cert_status,
        "cert_badges": user.cert_badges or [],
        # 道友传承新增字段
        "mentor_type": "enterprise" if user.role == "elder" else "academic",
        "mentor_direction": direction_label,
    }


def _mentorship_to_dict(m, db) -> dict:
    mentor = db.query(User).filter(User.openid == m.mentor_openid).first()
    disciple = db.query(User).filter(User.openid == m.disciple_openid).first()
    return {
        "id": m.id,
        "status": m.status,
        "started_at": m.started_at.isoformat() if m.started_at else "",
        "graduated_at": m.graduated_at.isoformat() if m.graduated_at else "",
        "milestones": m.milestones or [],
        "lineage_depth": m.lineage_depth,
        # 道友传承新增字段
        "mentor_type": getattr(m, "mentor_type", "academic"),
        "mentor_direction": getattr(m, "mentor_direction", "academic"),
        "application_reason": getattr(m, "application_reason", ""),
        "mentor": _mentor_to_dict(mentor, db) if mentor else None,
        "disciple": {
            "openid": disciple.openid if disciple else "",
            "nickname": disciple.nickname if disciple else "",
            "avatar_url": disciple.avatar_url if disciple else "",
            "level": disciple.level if disciple else 1,
        } if disciple else None,
    }


# ==================== 道友传承增强接口 ====================

from sqlalchemy import func


@router.get("/stats/mentor")
def get_mentor_stats(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取导师统计信息
    """
    Mentorship = mentor_service.Mentorship

    active_count = db.query(Mentorship).filter(
        Mentorship.mentor_openid == user.openid,
        Mentorship.status == "active"
    ).count()

    total_count = db.query(Mentorship).filter(
        Mentorship.mentor_openid == user.openid
    ).count()

    graduated_count = db.query(Mentorship).filter(
        Mentorship.mentor_openid == user.openid,
        Mentorship.status == "graduated"
    ).count()

    return {
        "active_disciples": active_count,
        "total_disciples": total_count,
        "graduated_disciples": graduated_count,
        "total_bonus_earned": 0,  # TODO: 从财务表计算
    }


@router.get("/stats/disciple")
def get_disciple_stats(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取被传承者统计信息
    """
    Mentorship = mentor_service.Mentorship

    active_mentorships = db.query(Mentorship).filter(
        Mentorship.disciple_openid == user.openid,
        Mentorship.status == "active"
    ).all()

    current_mentor = active_mentorships[0] if active_mentorships else None

    return {
        "current_mentors": len(active_mentorships),
        "graduated": user.graduated_from_mentor,
        "milestones_achieved": 0,  # TODO: 从里程碑表计算
    }


@router.get("/ranking")
def get_mentor_ranking(
    category: str = "disciples",  # disciples | rating | earnings
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """
    导师排行榜
    - disciples: 传承弟子数量排行
    - rating: 评分排行
    - earnings: 收入排行
    """
    query = db.query(User).filter(User.role.in_(["provider", "elder"]))

    if category == "disciples":
        users = query.order_by(User.active_disciples.desc()).limit(limit).all()
    elif category == "rating":
        users = query.filter(User.rating_count >= 5).order_by(User.rating.desc()).limit(limit).all()
    elif category == "earnings":
        users = query.order_by(User.total_earnings.desc()).limit(limit).all()
    else:
        users = []

    return {
        "category": category,
        "ranking": [
            {
                "rank": idx + 1,
                "openid": u.openid,
                "nickname": u.nickname,
                "avatar_url": u.avatar_url,
                "level": u.level,
                "school": u.school,
                "active_disciples": u.active_disciples,
                "rating": u.rating,
                "value": u.active_disciples if category == "disciples" else (
                    u.rating if category == "rating" else u.total_earnings
                ),
            }
            for idx, u in enumerate(users)
        ]
    }


@router.get("/recommend")
def get_recommended_mentors(
    limit: int = Query(6, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """
    推荐导师列表
    - 基于评分、传承弟子数、活跃度综合排序
    """
    query = db.query(User).filter(
        User.role.in_(["provider", "elder"]),
        User.available == True
    )

    mentors = query.order_by(
        (User.rating * 20 + User.active_disciples * 10 + User.level * 5).desc()
    ).limit(limit).all()

    return {
        "mentors": [_mentor_to_dict(m, db) for m in mentors]
    }
