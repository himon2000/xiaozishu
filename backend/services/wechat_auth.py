"""
微信登录服务
"""
import httpx
import uuid
import random
import string
from config import get_settings

settings = get_settings()


def generate_referral_code(length: int = 6) -> str:
    """生成唯一飞花令牌（前4位随机 + 后2位校验）"""
    chars = string.ascii_uppercase + string.digits
    rand_part = ''.join(random.choices(chars, k=4))
    return f"XLG{rand_part}"


async def code2session(js_code: str) -> dict:
    """
    微信 code2session 接口
    小程序端通过 wx.login() 获取 code，传给后端换 openid
    """
    url = "https://api.weixin.qq.com/sns/jscode2session"
    params = {
        "appid": settings.wechat_appid,
        "secret": settings.wechat_secret,
        "js_code": js_code,
        "grant_type": "authorization_code",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)
        data = resp.json()
        if "errcode" in data and data["errcode"] != 0:
            raise Exception(f"微信登录失败: {data.get('errmsg', data)}")
        return data  # { openid, session_key, unionid? }


async def get_phone_number(access_token: str, code: str) -> str | None:
    """
    通过微信获取用户手机号
    需要用户主动点击按钮触发
    """
    url = "https://api.weixin.qq.com/wxa/business/getuserphonenumber"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            url,
            params={"access_token": access_token},
            json={"code": code},
        )
        data = resp.json()
        if data.get("errcode") == 0:
            phone_info = data.get("phone_info", {})
            return phone_info.get("phoneNumber")
    return None
