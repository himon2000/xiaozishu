"""
人生阶段 API 路由
支持用户在不同人生阶段扮演不同角色
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from dependencies import get_db, get_current_user
from services import stage_service
from models import User, LifeStageType

router = APIRouter(prefix="/api/v1/stages", tags=["人生阶段"])


# ── Request/Response Models ──────────────────────────────

class StageCreateRequest(BaseModel):
    stage_type: str  # high_school|college|working
    stage_name: str = ""
    role: str = "seeker"
    # 高中信息
    high_school_name: str = ""
    high_school_city: str = ""
    grade: str = ""
    # 大学信息
    school: str = ""
    school_level: str = ""
    major: str = ""
    graduation_year: int = None
    # 就业信息
    company: str = ""
    position: str = ""
    industry: str = ""
    # 通用信息
    city: str = ""
    start_year: int = None
    end_year: int = None


class StageUpdateRequest(BaseModel):
    stage_name: str = None
    role: str = None
    # 高中信息
    high_school_name: str = None
    high_school_city: str = None
    grade: str = None
    # 大学信息
    school: str = None
    school_level: str = None
    major: str = None
    graduation_year: int = None
    # 就业信息
    company: str = None
    position: str = None
    industry: str = None
    # 通用信息
    city: str = None
    start_year: int = None
    end_year: int = None


# ── API Endpoints ────────────────────────────────────────

@router.get("", response_model=List[dict])
def list_my_stages(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取当前用户的所有人生阶段"""
    return stage_service.get_user_stages(db, current_user.openid)


@router.get("/current")
def get_current_stage(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取当前激活的人生阶段"""
    stage = stage_service.get_current_stage(db, current_user.openid)
    if not stage:
        raise HTTPException(status_code=404, detail="暂无激活的人生阶段")
    return stage


@router.get("/{stage_id}")
def get_stage(
    stage_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取指定阶段详情"""
    stage = stage_service.get_stage_by_id(db, stage_id, current_user.openid)
    if not stage:
        raise HTTPException(status_code=404, detail="阶段不存在")
    return stage


@router.post("")
def create_stage(
    req: StageCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建新的人生阶段"""
    # 验证阶段类型
    valid_types = [LifeStageType.HIGH_SCHOOL, LifeStageType.COLLEGE, LifeStageType.WORKING]
    if req.stage_type not in valid_types:
        raise HTTPException(status_code=400, detail="无效的阶段类型")

    return stage_service.create_stage(
        db=db,
        openid=current_user.openid,
        stage_type=req.stage_type,
        stage_name=req.stage_name,
        role=req.role,
        high_school_name=req.high_school_name,
        high_school_city=req.high_school_city,
        grade=req.grade,
        school=req.school,
        school_level=req.school_level,
        major=req.major,
        graduation_year=req.graduation_year,
        company=req.company,
        position=req.position,
        industry=req.industry,
        city=req.city,
        start_year=req.start_year,
        end_year=req.end_year,
    )


@router.put("/{stage_id}")
def update_stage(
    stage_id: str,
    req: StageUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新人生阶段"""
    updates = {k: v for k, v in req.dict().items() if v is not None}
    stage = stage_service.update_stage(db, stage_id, current_user.openid, **updates)
    if not stage:
        raise HTTPException(status_code=404, detail="阶段不存在")
    return stage


@router.post("/{stage_id}/switch")
def switch_stage(
    stage_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """切换到指定阶段（设为当前活跃阶段）"""
    stage = stage_service.switch_to_stage(db, stage_id, current_user.openid)
    if not stage:
        raise HTTPException(status_code=404, detail="阶段不存在或无权访问")
    return {"message": "切换成功", "stage": stage}


@router.post("/{stage_id}/archive")
def archive_stage(
    stage_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """归档人生阶段"""
    stage = stage_service.archive_stage(db, stage_id, current_user.openid)
    if not stage:
        raise HTTPException(status_code=404, detail="阶段不存在")
    return {"message": "归档成功", "stage": stage}


@router.delete("/{stage_id}")
def delete_stage(
    stage_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除人生阶段"""
    success = stage_service.delete_stage(db, stage_id, current_user.openid)
    if not success:
        raise HTTPException(status_code=404, detail="阶段不存在")
    return {"message": "删除成功"}


@router.post("/init")
def init_stages(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """初始化用户的人生阶段（首次登录时调用）"""
    return stage_service.init_user_stages(db, current_user.openid)
