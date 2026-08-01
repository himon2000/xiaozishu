"""
人生阶段服务 - 支持用户在不同人生阶段扮演不同角色
"""
import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from models import LifeStage, LifeStageType, LifeStageStatus, User


def generate_id():
    return f"stage_{uuid.uuid4().hex[:12]}"


def get_user_stages(db: Session, openid: str) -> List[dict]:
    """获取用户所有人生阶段"""
    stages = db.query(LifeStage).filter(
        LifeStage.user_openid == openid
    ).order_by(LifeStage.created_at.desc()).all()

    return [_stage_to_dict(s) for s in stages]


def get_current_stage(db: Session, openid: str) -> Optional[dict]:
    """获取当前激活的人生阶段"""
    stage = db.query(LifeStage).filter(
        LifeStage.user_openid == openid,
        LifeStage.is_current == True,
        LifeStage.status == LifeStageStatus.ACTIVE
    ).first()

    return _stage_to_dict(stage) if stage else None


def get_stage_by_id(db: Session, stage_id: str, openid: str) -> Optional[dict]:
    """根据ID获取阶段"""
    stage = db.query(LifeStage).filter(
        LifeStage.id == stage_id,
        LifeStage.user_openid == openid
    ).first()

    return _stage_to_dict(stage) if stage else None


def create_stage(
    db: Session,
    openid: str,
    stage_type: str,
    stage_name: str = "",
    role: str = "seeker",
    **kwargs
) -> dict:
    """创建新的人生阶段"""
    # 如果这是第一个阶段，自动设为当前
    existing_count = db.query(LifeStage).filter(
        LifeStage.user_openid == openid
    ).count()

    stage = LifeStage(
        id=generate_id(),
        user_openid=openid,
        stage_type=stage_type,
        stage_name=stage_name,
        role=role,
        is_current=(existing_count == 0),  # 第一个阶段自动当前
        **kwargs
    )

    db.add(stage)
    db.commit()
    db.refresh(stage)

    return _stage_to_dict(stage)


def update_stage(
    db: Session,
    stage_id: str,
    openid: str,
    **updates
) -> Optional[dict]:
    """更新人生阶段"""
    stage = db.query(LifeStage).filter(
        LifeStage.id == stage_id,
        LifeStage.user_openid == openid
    ).first()

    if not stage:
        return None

    # 允许更新的字段
    allowed_fields = [
        'stage_name', 'role', 'is_current', 'status',
        'high_school_name', 'high_school_city', 'grade',
        'school', 'school_level', 'major', 'graduation_year',
        'company', 'position', 'industry',
        'city', 'start_year', 'end_year'
    ]

    for key, value in updates.items():
        if key in allowed_fields and value is not None:
            setattr(stage, key, value)

    stage.updated_at = datetime.now()
    db.commit()
    db.refresh(stage)

    return _stage_to_dict(stage)


def switch_to_stage(db: Session, stage_id: str, openid: str) -> Optional[dict]:
    """切换到指定阶段（设为当前活跃阶段）"""
    # 验证阶段属于当前用户
    stage = db.query(LifeStage).filter(
        LifeStage.id == stage_id,
        LifeStage.user_openid == openid
    ).first()

    if not stage:
        return None

    # 先将所有阶段设为非当前
    db.query(LifeStage).filter(
        LifeStage.user_openid == openid
    ).update({'is_current': False})

    # 激活目标阶段
    stage.is_current = True
    stage.status = LifeStageStatus.ACTIVE
    stage.updated_at = datetime.now()

    db.commit()
    db.refresh(stage)

    return _stage_to_dict(stage)


def archive_stage(db: Session, stage_id: str, openid: str) -> Optional[dict]:
    """归档人生阶段"""
    stage = db.query(LifeStage).filter(
        LifeStage.id == stage_id,
        LifeStage.user_openid == openid
    ).first()

    if not stage:
        return None

    stage.is_current = False
    stage.status = LifeStageStatus.ARCHIVED
    stage.updated_at = datetime.now()

    db.commit()
    db.refresh(stage)

    return _stage_to_dict(stage)


def delete_stage(db: Session, stage_id: str, openid: str) -> bool:
    """删除人生阶段"""
    stage = db.query(LifeStage).filter(
        LifeStage.id == stage_id,
        LifeStage.user_openid == openid
    ).first()

    if not stage:
        return False

    was_current = stage.is_current

    db.delete(stage)
    db.commit()

    # 如果删除的是当前阶段，自动激活另一个
    if was_current:
        next_stage = db.query(LifeStage).filter(
            LifeStage.user_openid == openid,
            LifeStage.status == LifeStageStatus.ACTIVE
        ).first()

        if next_stage:
            next_stage.is_current = True
            db.commit()

    return True


def init_user_stages(db: Session, openid: str) -> List[dict]:
    """为新用户初始化默认人生阶段"""
    # 检查是否已有阶段
    existing = db.query(LifeStage).filter(
        LifeStage.user_openid == openid
    ).count()

    if existing > 0:
        return get_user_stages(db, openid)

    # 创建默认阶段（散修身份）
    default_stage = create_stage(
        db=db,
        openid=openid,
        stage_type=LifeStageType.COLLEGE,
        stage_name="我的修仙之路",
        role="seeker"
    )

    return [default_stage]


def _stage_to_dict(stage: LifeStage) -> dict:
    """将 LifeStage 模型转换为字典"""
    return {
        "id": stage.id,
        "user_openid": stage.user_openid,
        "stage_type": stage.stage_type,
        "stage_name": stage.stage_name,
        "role": stage.role,
        "is_current": stage.is_current,
        "status": stage.status,
        # 高中信息
        "high_school_name": stage.high_school_name or "",
        "high_school_city": stage.high_school_city or "",
        "grade": stage.grade or "",
        # 大学信息
        "school": stage.school or "",
        "school_level": stage.school_level or "",
        "major": stage.major or "",
        "graduation_year": stage.graduation_year,
        # 就业信息
        "company": stage.company or "",
        "position": stage.position or "",
        "industry": stage.industry or "",
        # 通用信息
        "city": stage.city or "",
        "start_year": stage.start_year,
        "end_year": stage.end_year,
        # 统计数据
        "orders_count": stage.orders_count,
        "services_count": stage.services_count,
        "total_earned": stage.total_earned,
        # 展示信息
        "display_title": _get_display_title(stage),
        "display_subtitle": _get_display_subtitle(stage),
        "role_label": _get_role_label(stage.role),
        "stage_type_label": _get_stage_type_label(stage.stage_type),
        "created_at": stage.created_at.isoformat() if stage.created_at else None,
        "updated_at": stage.updated_at.isoformat() if stage.updated_at else None,
    }


def _get_display_title(stage: LifeStage) -> str:
    """获取阶段展示标题"""
    if stage.stage_name:
        return stage.stage_name

    type_labels = {
        LifeStageType.HIGH_SCHOOL: "高中时光",
        LifeStageType.COLLEGE: "大学岁月",
        LifeStageType.WORKING: "职场之路",
    }
    return type_labels.get(stage.stage_type, "人生阶段")


def _get_display_subtitle(stage: LifeStage) -> str:
    """获取阶段展示副标题"""
    if stage.stage_type == LifeStageType.HIGH_SCHOOL:
        parts = [stage.high_school_name] if stage.high_school_name else []
        if stage.grade:
            parts.append(stage.grade)
        return " · ".join(parts) if parts else "高中阶段"
    elif stage.stage_type == LifeStageType.COLLEGE:
        parts = [stage.school] if stage.school else []
        if stage.school_level:
            parts.append(stage.school_level)
        return " · ".join(parts) if parts else "大学阶段"
    elif stage.stage_type == LifeStageType.WORKING:
        parts = [stage.position] if stage.position else []
        if stage.company:
            parts.append(f"@{stage.company}")
        return " · ".join(parts) if parts else "职场阶段"
    return ""


def _get_role_label(role: str) -> str:
    """获取角色标签"""
    labels = {
        "seeker": "散修",
        "provider": "宗门弟子",
        "elder": "大能",
        "admin": "执事",
    }
    return labels.get(role, "散修")


def _get_stage_type_label(stage_type: str) -> str:
    """获取阶段类型标签"""
    labels = {
        LifeStageType.HIGH_SCHOOL: "高中",
        LifeStageType.COLLEGE: "大学",
        LifeStageType.WORKING: "职场",
    }
    return labels.get(stage_type, "未知")
