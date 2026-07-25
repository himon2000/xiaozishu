"""
修为与境界路由
"""
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from utils.db import get_db
from models import User
from dependencies import get_current_user
from services.level_service import (
    get_user_cultivation_summary,
    get_ranking,
    get_level_info,
    LEVEL_CONFIG,
)
from services.dividend_service import (
    get_user_dividend,
    claim_dividend,
    get_dividend_history,
    get_pool_summary,
    get_eligible_users,
    calculate_dividend_share,
    generate_dividend_records,
)

router = APIRouter(prefix="/api/v1/level", tags=["修为境界"])


@router.get("/mine")
def my_cultivation(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """我的修为总览"""
    return get_user_cultivation_summary(db, user)


@router.get("/ranking")
def ranking(
    period: str = Query("total"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """修为排行榜"""
    return {"period": period, "ranking": get_ranking(db, period, limit)}


@router.get("/config")
def level_config():
    """境界配置（供前端渲染）"""
    return {"levels": LEVEL_CONFIG}


# ═══════════════════════════════════════════════════════════
# 分红池 API
# ═══════════════════════════════════════════════════════════

@router.get("/dividend-pool")
def dividend_pool(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    year: int = Query(None, description="查询年份，默认今年"),
):
    """
    宗门宝库公示
    年度分红：化神期(Lv5)大虾按修为比例分配20%佣金池
    """
    target_year = year or datetime.now().year

    # 获取用户分红信息
    user_dividend = get_user_dividend(db, user.openid, target_year)

    # 获取符合分红资格的大虾
    eligible = get_eligible_users(db)
    total_exp = sum(u.exp_points for u in eligible) or 1

    # 模拟年度分红池金额（实际从平台佣金池读取）
    pool_total = 10000000  # 模拟：10万元年度分红池（分）

    # 生成分红记录（如果不存在）
    generate_dividend_records(db, target_year, pool_total)

    # 获取用户预估份额
    share_info = calculate_dividend_share(user, eligible, pool_total) if user in eligible else {
        "user_share": 0,
        "user_exp_ratio": 0,
        "eligible_count": len(eligible),
        "total_exp": total_exp,
    }

    eligible_list = []
    for u in eligible[:20]:  # 只返回前20名
        level_info = get_level_info(u.level)
        u_share = int(pool_total * u.exp_points / total_exp)
        eligible_list.append({
            "openid": u.openid,
            "nickname": u.nickname,
            "avatar_url": u.avatar_url,
            "level": u.level,
            "level_name": level_info["name"],
            "level_icon": level_info["icon"],
            "exp_points": u.exp_points,
            "exp_ratio": round(u.exp_points / total_exp, 4),
            "total_orders_done": u.total_orders_done,
            "estimated_share": u_share,
        })

    return {
        "year": target_year,
        "pool_total": pool_total,
        "pool_total_yuan": pool_total / 100,
        "eligible_count": len(eligible),
        "eligible_list": eligible_list,
        "your_info": {
            "eligible": user.level >= 5 and user.total_orders_done > 0,
            "level": user.level,
            "level_name": get_level_info(user.level)["name"],
            "level_icon": get_level_info(user.level)["icon"],
            "exp_points": user.exp_points,
            "exp_ratio": share_info["user_exp_ratio"],
            "estimated_share": share_info["user_share"],
            "estimated_share_yuan": share_info["user_share"] / 100,
        },
        **user_dividend,
    }


@router.post("/dividend-pool/claim")
def claim_dividend_api(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    year: int = Query(None, description="领取年份，默认今年"),
):
    """
    领取年度分红
    """
    target_year = year or datetime.now().year

    if user.level < 5:
        return {"success": False, "message": "仅化神期(Lv5)及以上可领取分红"}

    result = claim_dividend(db, user.openid, target_year)
    return result


@router.get("/dividend-pool/history")
def dividend_history(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=50),
):
    """
    获取用户分红历史
    """
    records = get_dividend_history(db, user.openid, limit)
    return {"records": records}


@router.get("/dividend-pool/summary")
def dividend_summary(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    year: int = Query(None, description="查询年份，默认今年"),
):
    """
    获取分红池汇总信息（管理端用）
    """
    target_year = year or datetime.now().year
    summary = get_pool_summary(db, target_year)

    # 补充用户自己的状态
    user_dividend = get_user_dividend(db, user.openid, target_year)
    summary["your_status"] = user_dividend.get("status", "none")
    summary["your_share"] = user_dividend.get("user_share", 0)

    return summary
