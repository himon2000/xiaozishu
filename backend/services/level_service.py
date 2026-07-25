"""
修为与境界服务
《驯龙阁》核心激励体系
"""
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from models import User, LevelLog
from utils.db import get_db

# 境界配置
LEVEL_CONFIG = [
    {"level": 1, "name": "炼气期", "exp_threshold": 0,    "color": "#999999", "max_price_yuan": 200,  "icon": "🌫"},
    {"level": 2, "name": "筑基期", "exp_threshold": 100,  "color": "#00cc44", "max_price_yuan": 500,  "icon": "🌿"},
    {"level": 3, "name": "金丹期", "exp_threshold": 500,  "color": "#4499ff", "max_price_yuan": 1000, "icon": "💙"},
    {"level": 4, "name": "元婴期", "exp_threshold": 2000, "color": "#cc44ff", "max_price_yuan": 3000, "icon": "💜"},
    {"level": 5, "name": "化神期", "exp_threshold": 5000, "color": "#ffd700", "max_price_yuan": 99999,"icon": "⭐"},
]

EXP_RULES = {
    "earn_order_done":        +10,  # 完成服务订单
    "earn_5star_review":      +5,   # 获得5星好评
    "earn_4star_review":      +3,   # 获得4星好评
    "earn_disciple_graduate": +50,  # 徒弟成功升学
    "earn_disciple_offer":    +30,  # 徒弟拿到Offer
    "earn_resource_publish":  +3,   # 发布藏经阁资源
    "earn_resource_unlock":   +1,  # 资源被他人解锁
    "earn_platform_duty":     +20,  # 宗门执事任务
    "earn_referral":          +15,  # 推荐新用户注册
    "spend_resource_unlock":  -5,   # 解锁藏经阁资源
    "spend_apply_mentor":     -5,   # 拜师申请消耗
}


def get_level_info(level: int) -> dict:
    """获取境界配置信息"""
    for cfg in LEVEL_CONFIG:
        if cfg["level"] == level:
            return cfg
    return LEVEL_CONFIG[0]


def get_level_by_exp(exp: int) -> int:
    """根据修为点计算境界等级"""
    current_level = 1
    for cfg in LEVEL_CONFIG:
        if exp >= cfg["exp_threshold"]:
            current_level = cfg["level"]
        else:
            break
    return current_level


def exp_to_next_level(exp: int, current_level: int) -> dict:
    """计算到下一境界的距离"""
    if current_level >= 5:
        return {"current": exp, "next_threshold": exp, "needed": 0, "progress": 100}
    next_cfg = next((c for c in LEVEL_CONFIG if c["level"] == current_level + 1), None)
    if not next_cfg:
        return {"current": exp, "next_threshold": exp, "needed": 0, "progress": 100}
    current_threshold = get_level_info(current_level)["exp_threshold"]
    needed = next_cfg["exp_threshold"] - exp
    total = next_cfg["exp_threshold"] - current_threshold
    progress = int((exp - current_threshold) / total * 100) if total > 0 else 100
    return {
        "current": exp,
        "next_threshold": next_cfg["exp_threshold"],
        "needed": max(0, needed),
        "progress": min(100, progress),
        "next_level": next_cfg["level"],
        "next_level_name": next_cfg["name"],
    }


def add_exp(db: Session, user: User, change_type: str, related_id: str = "",
            remark: str = "", auto_commit: bool = True) -> dict:
    """
    增加/消耗修为点，返回变更结果
    """
    delta = EXP_RULES.get(change_type, 0)
    if delta == 0 and not change_type.startswith("custom_"):
        raise ValueError(f"未知的修为变更类型: {change_type}")

    # 支持自定义增量
    if change_type.startswith("custom_"):
        delta = int(change_type.replace("custom_", ""))

    level_before = user.level
    user.exp_points += delta
    level_after = get_level_by_exp(user.exp_points)
    user.level = level_after

    # 写日志
    log = LevelLog(
        id=f"LGL{uuid.uuid4().hex[:12]}",
        user_openid=user.openid,
        change_type=change_type,
        points_delta=delta,
        balance_after=user.exp_points,
        level_before=level_before,
        level_after=level_after,
        level_upgraded=(level_after > level_before),
        related_id=related_id,
        remark=remark,
    )
    db.add(log)
    if auto_commit:
        db.commit()

    return {
        "delta": delta,
        "balance": user.exp_points,
        "level_before": level_before,
        "level_after": level_after,
        "level_upgraded": level_after > level_before,
        "level_info": get_level_info(level_after),
    }


def get_user_cultivation_summary(db: Session, user: User) -> dict:
    """获取用户修为总览"""
    logs = db.query(LevelLog).filter(
        LevelLog.user_openid == user.openid
    ).order_by(LevelLog.created_at.desc()).limit(20).all()

    return {
        "level": user.level,
        "exp_points": user.exp_points,
        "level_name": get_level_info(user.level)["name"],
        "level_color": get_level_info(user.level)["color"],
        "level_icon": get_level_info(user.level)["icon"],
        "max_price_yuan": get_level_info(user.level)["max_price_yuan"],
        "progress": exp_to_next_level(user.exp_points, user.level),
        "total_orders_done": user.total_orders_done,
        "total_disciples": user.total_disciples,
        "rating": user.rating,
        "recent_logs": [
            {
                "change_type": log.change_type,
                "points_delta": log.points_delta,
                "balance_after": log.balance_after,
                "remark": log.remark,
                "created_at": log.created_at.isoformat() if log.created_at else "",
            }
            for log in logs
        ],
    }


def get_ranking(db: Session, period: str = "total", limit: int = 50) -> list:
    """
    获取修为排行榜
    period: total | weekly | monthly
    """
    query = db.query(User).filter(User.role.in_(["provider", "elder"]))
    # 暂时用总修为排序（后续可按周/月过滤 level_logs）
    users = query.order_by(User.exp_points.desc()).limit(limit).all()
    return [
        {
            "rank": i + 1,
            "openid": u.openid,
            "nickname": u.nickname,
            "avatar_url": u.avatar_url,
            "level": u.level,
            "level_name": get_level_info(u.level)["name"],
            "level_icon": get_level_info(u.level)["icon"],
            "level_color": get_level_info(u.level)["color"],
            "exp_points": u.exp_points,
            "rating": u.rating,
        }
        for i, u in enumerate(users)
    ]
