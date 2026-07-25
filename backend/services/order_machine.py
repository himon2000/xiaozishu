"""
订单状态机
《小紫薯》订单全生命周期状态管理
"""
from datetime import datetime
from models import Order, OrderStatus
from utils.db import get_db
from config import get_settings
import random, string

settings = get_settings()

# 状态流转白名单
VALID_TRANSITIONS = {
    OrderStatus.PENDING_PAYMENT: [OrderStatus.PAID, OrderStatus.CANCELLED],
    OrderStatus.PAID: [OrderStatus.ASSIGNED, OrderStatus.IN_PROGRESS],
    OrderStatus.ASSIGNED: [OrderStatus.IN_PROGRESS, OrderStatus.DISPUTE],
    OrderStatus.IN_PROGRESS: [OrderStatus.PENDING_CONFIRM, OrderStatus.DISPUTE],
    OrderStatus.PENDING_CONFIRM: [OrderStatus.COMPLETED, OrderStatus.DISPUTE],
    OrderStatus.DISPUTE: [OrderStatus.ADMIN_RESOLVING],
    OrderStatus.ADMIN_RESOLVING: [OrderStatus.RESOLVED, OrderStatus.COMPLETED],
    OrderStatus.RESOLVED: [],
    OrderStatus.COMPLETED: [],
    OrderStatus.CANCELLED: [],
}


def generate_order_id() -> str:
    """生成订单号：DLG + yyyyMMdd + 6位随机"""
    date_str = datetime.now().strftime("%Y%m%d")
    rand = ''.join(random.choices(string.digits, k=6))
    return f"DLG{date_str}{rand}"


def can_transition(current: str, target: str) -> bool:
    """检查状态是否可流转"""
    return target in VALID_TRANSITIONS.get(current, [])


def add_timeline_entry(order: Order, status: str, remark: str = "", operator: str = "") -> None:
    """向订单timeline追加一条记录"""
    import json
    entry = {
        "status": status,
        "remark": remark,
        "operator": operator,
        "timestamp": datetime.now().isoformat(),
    }
    timeline = order.timeline or []
    timeline.append(entry)
    order.timeline = timeline


def get_default_commission_rate(dao_fa_type: str) -> float:
    """根据道法类型获取平台抽成比例"""
    rates = {
        "chuan_gong": 0.10,
        "mi_jing": 0.10,
        "zong_men": 0.12,
        "xia_shan": 0.08,
        "zhi_fa": 0.05,
        "cang_jing": 0.15,
    }
    return rates.get(dao_fa_type, 0.10)


def calculate_order_amounts(order: Order) -> dict:
    """
    计算订单各部分金额
    返回: { service_fee, platform_commission, provider_income, mentor_bonus, total_paid }
    """
    service_fee = order.service_fee
    commission_rate = get_default_commission_rate(order.dao_fa_type)
    commission = int(service_fee * commission_rate)
    mentor_bonus = 0  # 后续根据师徒关系计算
    provider_income = service_fee - commission - mentor_bonus
    return {
        "service_fee": service_fee,
        "platform_commission": commission,
        "provider_income": provider_income,
        "mentor_bonus": mentor_bonus,
        "total_paid": service_fee,
    }


def get_status_display_name(status: str) -> str:
    """获取状态的修仙风格中文显示名"""
    names = {
        "pending_payment": "待付灵契",
        "paid": "灵契已付",
        "assigned": "大虾接单",
        "in_progress": "修炼中",
        "pending_confirm": "待散修确认",
        "completed": "功法大成",
        "dispute": "纠纷仲裁中",
        "admin_resolving": "执事处理中",
        "resolved": "仲裁完结",
        "cancelled": "灵契解除",
    }
    return names.get(status, status)


def get_status_progress(status: str) -> int:
    """
    获取订单进度百分比（用于前端进度条）
    """
    progress_map = {
        "pending_payment": 10,
        "paid": 25,
        "assigned": 35,
        "in_progress": 60,
        "pending_confirm": 80,
        "completed": 100,
        "dispute": 50,
        "admin_resolving": 50,
        "resolved": 100,
        "cancelled": 0,
    }
    return progress_map.get(status, 0)
