"""
角色服务 - 多角色体系核心
支持用户同时拥有散修/大虾/长老角色，各角色独立等级
"""
import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from models import User, UserRole, Service, RoleStatus


def generate_id():
    return f"ur_{uuid.uuid4().hex[:12]}"


# ── 角色元数据 ──────────────────────────────────────────

ROLE_CONFIG = {
    "seeker": {
        "name": "散修",
        "icon": "🧭",
        "desc": "发布需求，寻仙问道",
        "color": "#52c41a",
        "default_enabled": True,
        "unlock_condition": None,  # 默认解锁
    },
    "provider": {
        "name": "宗门弟子",
        "icon": "🧑‍🎓",
        "desc": "发布服务，传功授法",
        "color": "#fa8c16",
        "default_enabled": False,
        "unlock_condition": {
            "type": "service_count",
            "threshold": 2,
            "desc": "发布 2 个服务后自动解锁",
        },
    },
    "elder": {
        "name": "大能",
        "icon": "🧙",
        "desc": "职场专家，引领后辈",
        "color": "#722ed1",
        "default_enabled": False,
        "unlock_condition": {
            "type": "enterprise_email",
            "desc": "认证企业邮箱后解锁",
        },
    },
}


# ── 核心服务 ────────────────────────────────────────────

def get_user_roles(db: Session, openid: str) -> List[dict]:
    """
    获取用户所有角色状态
    包括已解锁和未解锁的角色
    """
    user = db.query(User).filter(User.openid == openid).first()
    if not user:
        return []

    # 获取已解锁的角色
    unlocked = db.query(UserRole).filter(
        UserRole.user_openid == openid,
        UserRole.status == RoleStatus.ENABLED,
    ).all()

    unlocked_map = {r.role: r for r in unlocked}

    result = []
    for role_key, config in ROLE_CONFIG.items():
        ur = unlocked_map.get(role_key)
        if ur:
            # 已解锁角色
            result.append(_role_to_dict(ur, config, enabled=True))
        else:
            # 未解锁角色
            result.append({
                "role": role_key,
                "name": config["name"],
                "icon": config["icon"],
                "desc": config["desc"],
                "color": config["color"],
                "status": "locked",
                "enabled": False,
                "level": 0,
                "exp_points": 0,
                "exp_to_next": 0,
                "unlock_tips": _get_unlock_tips(role_key, db, user),
                "unlock_progress": _get_unlock_progress(role_key, db, user),
            })

    return result


def enable_role(db: Session, openid: str, role: str) -> Optional[dict]:
    """
    解锁角色
    自动判断升级条件是否满足
    """
    user = db.query(User).filter(User.openid == openid).first()
    if not user:
        return None

    config = ROLE_CONFIG.get(role)
    if not config:
        return None

    # 检查是否已解锁
    existing = db.query(UserRole).filter(
        UserRole.user_openid == openid,
        UserRole.role == role,
    ).first()
    if existing:
        return _role_to_dict(existing, config, enabled=True)

    # 检查解锁条件
    can_unlock, reason = check_role_eligibility(db, user, role)
    if not can_unlock:
        return None

    # 解锁角色
    ur = UserRole(
        id=generate_id(),
        user_openid=openid,
        role=role,
        status=RoleStatus.ENABLED,
        level=1,
        exp_points=0,
        verified=False,
        unlocked_at=datetime.now(),
        unlock_condition=reason,
    )
    db.add(ur)
    db.commit()
    db.refresh(ur)

    # 更新 User.enabled_roles
    enabled_list = user.enabled_roles or []
    if role not in enabled_list:
        user.enabled_roles = enabled_list + [role]
        db.commit()

    return _role_to_dict(ur, config, enabled=True)


def switch_role(db: Session, openid: str, role: str) -> Optional[dict]:
    """
    切换当前展示角色
    """
    user = db.query(User).filter(User.openid == openid).first()
    if not user:
        return None

    # 检查是否已解锁该角色
    ur = db.query(UserRole).filter(
        UserRole.user_openid == openid,
        UserRole.role == role,
        UserRole.status == RoleStatus.ENABLED,
    ).first()

    if not ur:
        return None

    user.current_role = role
    db.commit()

    config = ROLE_CONFIG.get(role, {})
    return _role_to_dict(ur, config, enabled=True)


def check_role_eligibility(db: Session, user: User, role: str) -> tuple:
    """
    检查用户是否符合角色升级条件
    返回 (can_unlock: bool, reason: str)
    """
    config = ROLE_CONFIG.get(role)
    if not config:
        return False, "无效角色"

    condition = config.get("unlock_condition")

    if role == "seeker":
        return True, "默认解锁"

    elif role == "provider":
        # 条件：发布 2 个以上的服务
        threshold = condition["threshold"] if condition else 2
        count = db.query(Service).filter(
            Service.provider_openid == user.openid,
            Service.status.in_(["on_sale", "off_sale"]),
        ).count()
        if count >= threshold:
            return True, f"已发布 {count} 个服务，满足条件"
        return False, f"需发布 {threshold} 个服务（当前 {count}/{threshold}）"

    elif role == "elder":
        # 条件1：企业邮箱认证
        if user.enterprise_email_verified:
            return True, "企业邮箱已认证"
        # 条件2：provider 角色 + 5 个服务
        ur = db.query(UserRole).filter(
            UserRole.user_openid == user.openid,
            UserRole.role == "provider",
            UserRole.status == RoleStatus.ENABLED,
        ).first()
        if ur and ur.total_services_published >= 5:
            return True, "宗门弟子服务数达标，自动解锁"
        if ur:
            return False, f"宗门弟子需发布 5 个服务（当前 {ur.total_services_published}/5）"
        return False, "请先成为宗门弟子，或认证企业邮箱"

    return False, "条件不满足"


def update_role_stats(db: Session, openid: str, role: str,
                       service_delta: int = 0, order_delta: int = 0,
                       exp_delta: int = 0, rating: float = None) -> None:
    """
    更新角色统计数据（服务数/订单数/经验值）
    角色发布服务后调用
    """
    ur = db.query(UserRole).filter(
        UserRole.user_openid == openid,
        UserRole.role == role,
        UserRole.status == RoleStatus.ENABLED,
    ).first()

    if not ur:
        return

    if service_delta != 0:
        ur.total_services_published = max(0, ur.total_services_published + service_delta)
    if order_delta != 0:
        ur.total_orders_done = max(0, ur.total_orders_done + order_delta)
    if exp_delta != 0:
        ur.exp_points += exp_delta
        _check_level_up(ur, exp_delta)
    if rating is not None:
        _update_rating(ur, rating)

    ur.updated_at = datetime.now()
    db.commit()


def get_role_by_user(db: Session, openid: str, role: str) -> Optional[UserRole]:
    """获取用户指定角色"""
    return db.query(UserRole).filter(
        UserRole.user_openid == openid,
        UserRole.role == role,
        UserRole.status == RoleStatus.ENABLED,
    ).first()


def init_user_roles(db: Session, openid: str) -> List[dict]:
    """
    初始化用户角色（新用户注册时调用）
    默认解锁散修角色
    """
    existing = db.query(UserRole).filter(
        UserRole.user_openid == openid
    ).count()
    if existing > 0:
        return get_user_roles(db, openid)

    # 解锁散修角色
    ur = UserRole(
        id=generate_id(),
        user_openid=openid,
        role="seeker",
        status=RoleStatus.ENABLED,
        level=1,
        exp_points=0,
        unlocked_at=datetime.now(),
        unlock_condition="默认解锁",
    )
    db.add(ur)
    db.commit()
    db.refresh(ur)

    # 更新 User.enabled_roles
    user = db.query(User).filter(User.openid == openid).first()
    if user:
        user.enabled_roles = ["seeker"]
        user.current_role = "seeker"
        db.commit()

    return get_user_roles(db, openid)


# ── 辅助函数 ─────────────────────────────────────────────

def _role_to_dict(ur: UserRole, config: dict, enabled: bool) -> dict:
    """将 UserRole 转换为字典"""
    level = ur.level or 1
    exp = ur.exp_points or 0
    exp_to_next = _exp_for_level(level + 1) - exp

    return {
        "role": ur.role,
        "name": config.get("name", ur.role),
        "icon": config.get("icon", "❓"),
        "desc": config.get("desc", ""),
        "color": config.get("color", "#999"),
        "status": ur.status,
        "enabled": enabled,
        "level": level,
        "exp_points": exp,
        "exp_to_next": max(0, exp_to_next),
        "exp_progress": _get_exp_progress(level, exp),
        "total_orders_done": ur.total_orders_done,
        "total_services_published": ur.total_services_published,
        "rating": ur.rating or 5.0,
        "rating_count": ur.rating_count or 0,
        "verified": ur.verified,
        "unlocked_at": ur.unlocked_at.isoformat() if ur.unlocked_at else None,
        "level_name": _get_level_name(level),
        "level_badge": _get_level_badge(level),
    }


def _get_unlock_tips(role: str, db: Session, user: User) -> str:
    """获取解锁提示"""
    config = ROLE_CONFIG.get(role, {})
    condition = config.get("unlock_condition")

    if role == "provider":
        count = db.query(Service).filter(
            Service.provider_openid == user.openid,
            Service.status.in_(["on_sale", "off_sale"]),
        ).count()
        threshold = condition["threshold"] if condition else 2
        return f"再发布 {threshold - count} 个服务即可解锁" if count < threshold else "已满足条件！"
    elif role == "elder":
        if user.enterprise_email_verified:
            return "已认证企业邮箱！"
        ur = db.query(UserRole).filter(
            UserRole.user_openid == user.openid,
            UserRole.role == "provider",
            UserRole.status == RoleStatus.ENABLED,
        ).first()
        if ur:
            return f"宗门弟子服务数需达 5 个（当前 {ur.total_services_published}/5）或认证企业邮箱"
        return "需先成为宗门弟子（2 个服务）或认证企业邮箱"
    return ""


def _get_unlock_progress(role: str, db: Session, user: User) -> dict:
    """获取解锁进度"""
    if role == "provider":
        count = db.query(Service).filter(
            Service.provider_openid == user.openid,
            Service.status.in_(["on_sale", "off_sale"]),
        ).count()
        threshold = 2
        return {"current": count, "threshold": threshold, "percent": min(100, int(count / threshold * 100))}
    elif role == "elder":
        if user.enterprise_email_verified:
            return {"current": 100, "threshold": 100, "percent": 100}
        ur = db.query(UserRole).filter(
            UserRole.user_openid == user.openid,
            UserRole.role == "provider",
            UserRole.status == RoleStatus.ENABLED,
        ).first()
        if ur:
            return {"current": ur.total_services_published, "threshold": 5, "percent": min(100, int(ur.total_services_published / 5 * 100))}
        return {"current": 0, "threshold": 5, "percent": 0}
    return {"current": 0, "threshold": 0, "percent": 0}


def _exp_for_level(level: int) -> int:
    """计算指定等级需要的累计经验"""
    # 等级经验曲线：1→2需要100exp，2→3需要200exp...
    return sum(100 * i for i in range(1, level + 1))


def _get_exp_progress(level: int, exp: int) -> int:
    """获取当前等级经验进度百分比"""
    current_exp_for_level = _exp_for_level(level) - 100 * level
    exp_in_level = exp - current_exp_for_level
    exp_needed = 100 * level
    return min(100, int(exp_in_level / exp_needed * 100)) if exp_needed > 0 else 100


def _check_level_up(ur: UserRole, exp_delta: int) -> None:
    """检查是否升级"""
    # 简化版：每获得 100*level 点经验升一级
    while ur.exp_points >= _exp_for_level(ur.level + 1):
        ur.level += 1


def _update_rating(ur: UserRole, new_rating: float) -> None:
    """更新评分"""
    total = ur.rating * ur.rating_count + new_rating
    ur.rating_count += 1
    ur.rating = round(total / ur.rating_count, 1)


def _get_level_name(level: int) -> str:
    """获取修为境界名称"""
    names = {
        1: "练气期", 2: "筑基期", 3: "金丹期", 4: "元婴期", 5: "化神期",
        6: "炼虚期", 7: "合体期", 8: "大乘期", 9: "渡劫期", 10: "真仙境",
    }
    return names.get(level, f"第{level}境")


def _get_level_badge(level: int) -> str:
    """获取境界徽章"""
    badges = {
        1: "🌀", 2: "💎", 3: "⭐", 4: "🌟", 5: "✨",
        6: "💫", 7: "🔮", 8: "👑", 9: "🔥", 10: "🌈",
    }
    return badges.get(level, "🔰")
