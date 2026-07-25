"""
灵石充值相关 API
"""
import time
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from utils.db import get_db
from models import User
from dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/wallet", tags=["灵石钱包"])

# 充值套餐白名单：key=stones（实付灵石+赠品），value=最低应付元
RECHARGE_PACKAGES = {
    100:   1.0,
    510:   5.0,   # 500+10赠
    1030:  10.0,  # 1000+30赠
    2080:  20.0,  # 2000+80赠
    5200:  50.0,  # 5000+200赠
    10500: 100.0, # 10000+500赠
}

# 自定义充值：1元=100灵石，最低1元
CUSTOM_RATE = 100  # 灵石/元

# ── 防重入：记录已回调的订单ID ────────────────────────────
_processed_callbacks: set = set()
_pending_recharges: dict[str, tuple[str, int]] = {}


class RechargeRequest(BaseModel):
    price: float = Field(..., gt=0, description="充值金额（元）")
    stones: int = Field(..., ge=1, description="期望到账灵石数量")


class RechargeResponse(BaseModel):
    success: bool
    order_id: str
    message: str = ""


class RechargeCallbackRequest(BaseModel):
    order_id: str
    status: str


class BalanceResponse(BaseModel):
    spirit_stones: int
    spirit_stones_frozen: int = 0


@router.get("/balance", response_model=BalanceResponse)
def get_balance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取用户灵石余额"""
    return {
        "spirit_stones": current_user.spirit_stones or 0,
        "spirit_stones_frozen": current_user.spirit_stones_frozen or 0,
    }


@router.post("/recharge", response_model=RechargeResponse)
def create_recharge_order(
    req: RechargeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建充值订单（Mock 实现）：服务端校验套餐合法性"""
    if req.price <= 0:
        raise HTTPException(status_code=400, detail="充值金额不合法")

    # 校验套餐：前端传来的 stones 必须与套餐白名单一致
    expected_price = RECHARGE_PACKAGES.get(req.stones)
    if expected_price is not None:
        if abs(req.price - expected_price) > 0.01:
            raise HTTPException(status_code=400, detail="充值套餐与价格不匹配")
    else:
        # 自定义充值：服务端按汇率计算实际灵石
        expected_stones = int(req.price) * CUSTOM_RATE
        if req.price < 1 or req.price != int(req.price):
            raise HTTPException(status_code=400, detail="自定义充值金额需为正整数元")
        req = req.model_copy(update={"stones": expected_stones})

    order_id = f"RECHARGE_{current_user.openid[:8]}_{int(time.time())}"
    _pending_recharges[order_id] = (current_user.openid, req.stones)
    return {
        "success": True,
        "order_id": order_id,
        "message": f"充值订单已创建：{req.stones} 灵石",
    }


@router.post("/recharge/callback")
def recharge_callback(
    body: RechargeCallbackRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    充值回调（Mock：生产环境应由微信支付服务器直接回调，不经前端）

    安全加固：
    - P0-2 修复：移除前端可调用的 get_current_user 依赖
    - 优先从微信云托管 header (X-WX-OPENID) 获取 openid
    - 防重入：同一 order_id 只允许回调一次
    - 生产环境应替换为微信支付签名验证
    """
    order_id = body.order_id
    if body.status != "success":
        return {"success": False, "message": "支付未成功"}

    # ── 防重入检查 ─────────────────────────────────────
    if order_id in _processed_callbacks:
        logger.warning(f"重复充值回调被拒绝: {order_id}")
        raise HTTPException(status_code=400, detail="该订单已处理，请勿重复提交")

    # ── 获取 openid（仅信任微信云托管 header）────────────
    wx_openid = request.headers.get("X-WX-OPENID") or request.headers.get("x-wx-openid")
    if not wx_openid:
        # Mock 模式：允许非云托管环境通过（仅 development）
        from config import get_settings
        _settings = get_settings()
        if not _settings.debug:
            logger.warning(f"充值回调缺少 X-WX-OPENID header: {order_id}")
            raise HTTPException(status_code=403, detail="非法请求：缺少身份认证")
        # 开发环境降级：从 order_id 中提取 openid
        parts = order_id.split("_")
        if len(parts) >= 2:
            wx_openid = parts[1] + "_mock"

    if not wx_openid:
        raise HTTPException(status_code=400, detail="无法识别用户身份")

    pending = _pending_recharges.get(order_id)
    if not pending:
        raise HTTPException(status_code=400, detail="充值订单不存在或已失效")
    order_openid, actual_stones = pending
    if order_openid != wx_openid:
        raise HTTPException(status_code=403, detail="充值订单与当前用户不匹配")

    # ── 查找用户 ──────────────────────────────────────
    user = db.query(User).filter(User.openid == wx_openid).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # TODO（生产环境）：
    # from models import RechargeOrder
    # recharge_order = db.query(RechargeOrder).filter(RechargeOrder.id == order_id).first()
    # if not recharge_order or recharge_order.status != "pending":
    #     raise HTTPException(status_code=400, detail="订单不存在或已处理")
    # actual_stones = recharge_order.stones
    # recharge_order.status = "paid"

    # ── 入账 ──────────────────────────────────────────
    user.spirit_stones = (user.spirit_stones or 0) + actual_stones
    # 同步到兼容字段
    user.balance = user.spirit_stones

    # 标记为已处理
    _processed_callbacks.add(order_id)
    _pending_recharges.pop(order_id, None)

    db.commit()
    logger.info(f"充值成功: user={wx_openid}, order={order_id}, stones={actual_stones}")

    return {
        "success": True,
        "spirit_stones": user.spirit_stones,
        "credited_stones": actual_stones,
    }
