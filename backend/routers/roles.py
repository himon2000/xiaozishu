"""
角色 API 路由 - 多角色管理
支持角色列表、升级条件检查、角色切换、企业邮箱认证
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from utils.db import get_db
from models import User, Service
from dependencies import get_current_user
from services import role_service

router = APIRouter(prefix="/api/v1/roles", tags=["多角色"])


# ── Request/Response Models ──────────────────────────────

class RoleSwitchRequest(BaseModel):
    role: str  # seeker|provider|elder


class EnterpriseEmailVerifyRequest(BaseModel):
    email: str  # 企业邮箱地址


class RoleUpgradeResponse(BaseModel):
    role: str
    name: str
    icon: str
    can_unlock: bool
    reason: str
    progress: dict


# ── API Endpoints ────────────────────────────────────────

@router.get("", response_model=List[dict])
def list_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取用户所有角色状态（已解锁+未解锁）"""
    return role_service.get_user_roles(db, current_user.openid)


@router.get("/current")
def get_current_role(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前激活的角色"""
    roles = role_service.get_user_roles(db, current_user.openid)
    current = current_user.current_role or "seeker"
    for r in roles:
        if r["role"] == current and r.get("enabled"):
            return r
    # 如果当前角色未解锁，返回散修
    for r in roles:
        if r["role"] == "seeker":
            return r
    return roles[0] if roles else None


@router.post("/switch")
def switch_role(
    req: RoleSwitchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """切换当前展示角色"""
    result = role_service.switch_role(db, current_user.openid, req.role)
    if not result:
        raise HTTPException(status_code=400, detail="角色未解锁或不存在")
    return {"success": True, "role": result}


@router.get("/eligibility", response_model=List[RoleUpgradeResponse])
def check_all_eligibility(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """检查所有角色的升级条件"""
    result = []
    for role_key in ["seeker", "provider", "elder"]:
        can_unlock, reason = role_service.check_role_eligibility(db, current_user, role_key)
        progress = role_service._get_unlock_progress(role_key, db, current_user)
        config = role_service.ROLE_CONFIG.get(role_key, {})
        result.append({
            "role": role_key,
            "name": config.get("name", role_key),
            "icon": config.get("icon", "❓"),
            "can_unlock": can_unlock,
            "reason": reason,
            "progress": progress,
        })
    return result


@router.get("/eligibility/{role}")
def check_role_eligibility(
    role: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """检查指定角色的升级条件"""
    can_unlock, reason = role_service.check_role_eligibility(db, current_user, role)
    progress = role_service._get_unlock_progress(role, db, current_user)
    config = role_service.ROLE_CONFIG.get(role, {})
    return {
        "role": role,
        "name": config.get("name", role),
        "icon": config.get("icon", "❓"),
        "can_unlock": can_unlock,
        "reason": reason,
        "progress": progress,
    }


@router.post("/enable/{role}")
def enable_role(
    role: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """解锁角色（满足条件后调用）"""
    result = role_service.enable_role(db, current_user.openid, role)
    if not result:
        raise HTTPException(status_code=400, detail="条件不满足，无法解锁该角色")
    return {"success": True, "role": result}


@router.post("/enterprise-email/verify")
def verify_enterprise_email(
    req: EnterpriseEmailVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    企业邮箱认证
    目前为简化版：验证邮箱格式 + .com/.cn/.edu 等域名后缀
    实际生产环境应发送验证码邮件
    """
    import re
    email = req.email.lower().strip()

    # 基础格式验证
    if not re.match(r'^[\w.-]+@[\w.-]+\.\w+$', email):
        raise HTTPException(status_code=400, detail="邮箱格式不正确")

    # 企业邮箱域名白名单（可扩展）
    public_domains = ['gmail.com', 'qq.com', '163.com', '126.com', 'hotmail.com', 'outlook.com']
    if email.split('@')[1] in public_domains:
        raise HTTPException(status_code=400, detail="请使用企业/机构邮箱（非个人邮箱）")

    # 更新用户信息
    current_user.enterprise_email = email
    current_user.enterprise_email_verified = True

    # 自动解锁长老角色
    from datetime import datetime
    ur = role_service.get_role_by_user(db, current_user.openid, "elder")
    if not ur:
        from models import UserRole, RoleStatus
        ur = UserRole(
            id=role_service.generate_id(),
            user_openid=current_user.openid,
            role="elder",
            status=RoleStatus.ENABLED,
            level=1,
            exp_points=0,
            verified=True,
            verified_at=datetime.now(),
            unlocked_at=datetime.now(),
            unlock_condition="企业邮箱认证",
        )
        db.add(ur)
        current_user.enabled_roles = current_user.enabled_roles or []
        if "elder" not in current_user.enabled_roles:
            current_user.enabled_roles = current_user.enabled_roles + ["elder"]

    db.commit()

    return {
        "success": True,
        "message": "企业邮箱认证成功，长老角色已解锁！",
        "email": email,
    }


@router.get("/enterprise-email/status")
def get_enterprise_email_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取企业邮箱认证状态"""
    return {
        "verified": current_user.enterprise_email_verified,
        "email": current_user.enterprise_email or "",
    }
