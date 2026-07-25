"""
年度分红池服务
《小紫薯》宗门宝库 - 化神期(Lv5)大虾按修为比例分配佣金池
"""
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc, text
from models import User, LevelLog, DividendRecord


# 分红配置
DIVIDEND_CONFIG = {
    "annual_pool_ratio": 0.20,  # 年度佣金池比例 20%
    "min_level": 5,              # 最低境界：化神期
    "min_orders": 1,             # 最少完成订单数
    "claim_expire_days": 30,     # 领取有效期 30 天
}


def ensure_dividend_table(db: Session):
    """确保分红记录表存在（用于 SQLite 手动建表）"""
    try:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS dividend_records (
                id TEXT PRIMARY KEY,
                user_openid TEXT NOT NULL,
                year INTEGER NOT NULL,
                pool_total INTEGER NOT NULL,
                user_share INTEGER NOT NULL,
                user_exp_ratio REAL NOT NULL,
                eligible_exp_total INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                claimed_at TIMESTAMP,
                created_at TIMESTAMP NOT NULL,
                FOREIGN KEY (user_openid) REFERENCES users(openid)
            )
        """))
        db.commit()
    except Exception:
        db.rollback()


def calculate_annual_pool(platform_commission: int, year: int = None) -> dict:
    """
    计算年度分红池金额
    返回：{ pool_total, eligible_count, distribution }
    """
    if year is None:
        year = datetime.now().year

    return {
        "year": year,
        "pool_total": platform_commission,
        "ratio": DIVIDEND_CONFIG["annual_pool_ratio"],
    }


def get_eligible_users(db: Session) -> list:
    """获取符合分红资格的大虾列表"""
    return db.query(User).filter(
        User.level >= DIVIDEND_CONFIG["min_level"],
        User.role.in_(["provider", "elder"]),
        User.total_orders_done >= DIVIDEND_CONFIG["min_orders"],
    ).all()


def calculate_dividend_share(user: User, eligible_users: list, pool_total: int) -> dict:
    """计算单个用户的分红份额"""
    total_exp = sum(u.exp_points for u in eligible_users) or 1
    share = int(pool_total * user.exp_points / total_exp)
    exp_ratio = user.exp_points / total_exp
    return {
        "user_share": share,
        "user_exp_ratio": round(exp_ratio, 4),
        "eligible_count": len(eligible_users),
        "total_exp": total_exp,
    }


def generate_dividend_records(db: Session, year: int, pool_total: int) -> list:
    """
    为所有符合资格的用户生成分红记录
    """
    eligible = get_eligible_users(db)
    if not eligible:
        return []

    records = []
    for user in eligible:
        # 检查是否已有该年分红记录
        existing = db.query(DividendRecord).filter(
            DividendRecord.user_openid == user.openid,
            DividendRecord.year == year,
        ).first()

        if existing:
            records.append(existing)
            continue

        share_info = calculate_dividend_share(user, eligible, pool_total)

        record = DividendRecord(
            id=f"DVR{uuid.uuid4().hex[:12].upper()}",
            user_openid=user.openid,
            year=year,
            pool_total=pool_total,
            user_share=share_info["user_share"],
            user_exp_ratio=share_info["user_exp_ratio"],
            eligible_exp_total=share_info["total_exp"],
            status="pending",
            created_at=datetime.now(),
        )
        db.add(record)
        records.append(record)

    db.commit()
    return records


def get_user_dividend(db: Session, user_openid: str, year: int = None) -> dict:
    """获取用户年度分红信息"""
    if year is None:
        year = datetime.now().year

    record = db.query(DividendRecord).filter(
        DividendRecord.user_openid == user_openid,
        DividendRecord.year == year,
    ).first()

    if not record:
        # 计算预期分红
        eligible = get_eligible_users(db)
        if not eligible:
            return {"eligible": False, "reason": "暂无分红资格"}

        user = db.query(User).filter(User.openid == user_openid).first()
        if not user or user.level < DIVIDEND_CONFIG["min_level"]:
            return {
                "eligible": False,
                "reason": f"需达到化神期(Lv{DIVIDEND_CONFIG['min_level']})方可参与分红",
                "current_level": user.level if user else 0,
            }

        if user.total_orders_done < DIVIDEND_CONFIG["min_orders"]:
            return {
                "eligible": False,
                "reason": f"需完成至少{DIVIDEND_CONFIG['min_orders']}个订单",
                "current_orders": user.total_orders_done,
            }

        return {
            "eligible": True,
            "status": "calculating",
            "estimated_share": 0,
            "message": "年度结算中，请耐心等待...",
        }

    return {
        "eligible": True,
        "record_id": record.id,
        "status": record.status,
        "pool_total": record.pool_total,
        "user_share": record.user_share,
        "user_exp_ratio": record.user_exp_ratio,
        "claimed_at": record.claimed_at.isoformat() if record.claimed_at else None,
        "created_at": record.created_at.isoformat() if record.created_at else "",
    }


def claim_dividend(db: Session, user_openid: str, year: int = None) -> dict:
    """用户领取分红"""
    if year is None:
        year = datetime.now().year

    record = db.query(DividendRecord).filter(
        DividendRecord.user_openid == user_openid,
        DividendRecord.year == year,
    ).first()

    if not record:
        return {"success": False, "message": "未找到分红记录"}

    if record.status == "claimed":
        return {"success": False, "message": "分红已领取，请勿重复操作"}

    if record.status == "expired":
        return {"success": False, "message": "分红已过期"}

    # 领取分红
    record.status = "claimed"
    record.claimed_at = datetime.now()

    # 增加用户余额
    user = db.query(User).filter(User.openid == user_openid).first()
    if user:
        user.balance += record.user_share
        user.total_dividend += record.user_share

        # 记录修为日志
        log = LevelLog(
            id=f"LL{uuid.uuid4().hex[:10].upper()}",
            user_openid=user_openid,
            change_type="earn_annual_dividend",
            points_delta=record.user_share,
            balance_after=user.balance,
            level_before=user.level,
            level_after=user.level,
            level_upgraded=False,
            related_id=record.id,
            remark=f"{year}年度宗门分红，修为占比{record.user_exp_ratio:.2%}",
        )
        db.add(log)

    db.commit()

    return {
        "success": True,
        "message": f"领取成功！获得 {record.user_share / 100:.2f} 元",
        "amount": record.user_share,
        "claimed_at": record.claimed_at.isoformat(),
    }


def get_dividend_history(db: Session, user_openid: str, limit: int = 10) -> list:
    """获取用户分红历史"""
    records = db.query(DividendRecord).filter(
        DividendRecord.user_openid == user_openid,
    ).order_by(desc(DividendRecord.year)).limit(limit).all()

    return [
        {
            "id": r.id,
            "year": r.year,
            "pool_total": r.pool_total,
            "user_share": r.user_share,
            "user_exp_ratio": r.user_exp_ratio,
            "eligible_exp_total": r.eligible_exp_total,
            "status": r.status,
            "claimed_at": r.claimed_at.isoformat() if r.claimed_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else "",
        }
        for r in records
    ]


def get_pool_summary(db: Session, year: int = None) -> dict:
    """获取分红池汇总信息"""
    if year is None:
        year = datetime.now().year

    eligible = get_eligible_users(db)
    total_exp = sum(u.exp_points for u in eligible) or 1

    # 统计已发放
    claimed = db.query(DividendRecord).filter(
        DividendRecord.year == year,
        DividendRecord.status == "claimed",
    ).all()

    pending = db.query(DividendRecord).filter(
        DividendRecord.year == year,
        DividendRecord.status == "pending",
    ).all()

    total_distributed = sum(r.user_share for r in claimed)
    total_pending = sum(r.user_share for r in pending)

    return {
        "year": year,
        "eligible_count": len(eligible),
        "total_exp": total_exp,
        "claimed_count": len(claimed),
        "pending_count": len(pending),
        "total_distributed": total_distributed,
        "total_pending": total_pending,
        "unclaimed_count": len(pending),
    }
