"""
微信支付服务
支持 v3 API（JSAPI下单）
"""
import httpx
import time
import hashlib
import base64
from config import get_settings
from models import Order

settings = get_settings()


async def create_unified_order(
    order: Order,
    openid: str,
    description: str = "驯龙阁服务",
) -> dict:
    """
    发起微信支付统一下单
    返回支付参数供小程序调起支付
    """
    # 生产环境使用真实微信支付 API，这里为演示返回模拟参数
    # 真实实现需要：
    # 1. 调用微信支付 v3 API: POST /v3/pay/transactions/jsapi
    # 2. 使用商户证书签名
    # 3. 返回 { timeStamp, nonceStr, package, signType, paySign }

    pay_sign = hashlib.sha256(
        f"{settings.wechat_mchid}{order.id}{int(time.time())}".encode()
    ).hexdigest()[:32]

    return {
        "timeStamp": str(int(time.time())),
        "nonceStr": f"nonce{order.id[-8:]}",
        "package": f"prepay_id=wx{order.id}test",
        "signType": "RSA",
        "paySign": pay_sign,
    }


async def query_order_status(transaction_id: str) -> dict:
    """
    查询微信支付订单状态
    """
    # 真实实现调用: GET /v3/pay/transactions/id/{transaction_id}
    return {"trade_state": "SUCCESS"}


async def close_order(order_id: str) -> bool:
    """
    关闭订单（用户超时未支付）
    """
    # 真实实现调用: POST /v3/pay/transactions/out-trade-no/{order_id}/close
    return True
