"""微信文本内容安全检查。

运行环境自适应：
1. 微信云托管环境 —— 优先使用「云调用」免鉴权令牌
   （容器内挂载文件 /.tencentcloudbase/wx/cloudbase_access_token），
   不需要 AppSecret、不受 IP 白名单限制、走微信内网专线。
2. 自建服务器 / 本地 —— 回退到 AppSecret 换取 access_token 的方式。
3. 开发环境（environment=development）或开关关闭时 —— 直接跳过检测。

云托管使用前必须在控制台完成一次配置：
  云托管控制台 → 云调用 → 云调用权限配置 → 添加接口路径（一行一个）：
    /wxa/msg_sec_check
    /wxa/img_sec_check
"""
from __future__ import annotations

import io
import logging
import os
import threading
import time
from typing import Any

import httpx
from PIL import Image

from config import get_settings
from utils.http_verify import ssl_verify

logger = logging.getLogger(__name__)

# 云托管容器内，微信后台周期性推送的免鉴权令牌挂载路径
CLOUDBASE_TOKEN_PATH = "/.tencentcloudbase/wx/cloudbase_access_token"

_token_lock = threading.Lock()
_access_token = ""
_access_token_expires_at = 0.0


class ContentRejectedError(ValueError):
    pass


class ContentCheckUnavailableError(RuntimeError):
    pass


def _flatten_text(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, dict):
        result: list[str] = []
        for item in value.values():
            result.extend(_flatten_text(item))
        return result
    if isinstance(value, (list, tuple, set)):
        result = []
        for item in value:
            result.extend(_flatten_text(item))
        return result
    return []


def _read_cloudbase_token() -> str:
    """读取云托管容器内的免鉴权令牌；非云托管环境返回空字符串。"""
    try:
        if os.path.exists(CLOUDBASE_TOKEN_PATH):
            with open(CLOUDBASE_TOKEN_PATH, "r", encoding="utf-8") as fp:
                return fp.read().strip()
    except Exception as exc:  # pragma: no cover - 读取失败按无令牌处理
        logger.warning("读取云调用令牌失败: %s", exc)
    return ""


def _get_token() -> tuple[str, str]:
    """返回 (令牌, 鉴权参数名)。

    云托管环境使用 cloudbase_access_token，其他环境使用 access_token。
    """
    global _access_token, _access_token_expires_at

    # 云调用免鉴权令牌由平台周期性推送，每次实时读取，不做长缓存。
    cloudbase_token = _read_cloudbase_token()
    if cloudbase_token:
        return cloudbase_token, "cloudbase_access_token"

    now = time.time()
    if _access_token and now < _access_token_expires_at:
        return _access_token, "access_token"

    with _token_lock:
        now = time.time()
        if _access_token and now < _access_token_expires_at:
            return _access_token, "access_token"

        settings = get_settings()
        try:
            response = httpx.get(
                "https://api.weixin.qq.com/cgi-bin/token",
                params={
                    "grant_type": "client_credential",
                    "appid": settings.wechat_appid,
                    "secret": settings.wechat_secret,
                },
                timeout=8,
                verify=ssl_verify(),
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            raise ContentCheckUnavailableError("内容安全服务暂时不可用") from exc

        token = payload.get("access_token")
        if not token:
            logger.error("微信 access_token 获取失败: %s", payload.get("errcode"))
            raise ContentCheckUnavailableError("内容安全服务配置异常")

        _access_token = token
        _access_token_expires_at = now + max(int(payload.get("expires_in", 7200)) - 300, 60)
        return _access_token, "access_token"


def ensure_safe_text(openid: str, *values: Any) -> None:
    settings = get_settings()
    if not settings.content_moderation_enabled or settings.environment == "development":
        return

    content = "\n".join(_flatten_text(values)).strip()
    if not content:
        return

    # 微信接口单次文本长度有限；表单内容分段检查，避免截断后半部分。
    for offset in range(0, len(content), 2000):
        chunk = content[offset:offset + 2000]
        token, token_param = _get_token()
        try:
            response = httpx.post(
                "https://api.weixin.qq.com/wxa/msg_sec_check",
                params={token_param: token},
                json={"content": chunk, "version": 2, "scene": 2, "openid": openid},
                timeout=8,
                verify=ssl_verify(),
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            raise ContentCheckUnavailableError("内容安全服务暂时不可用") from exc

        if payload.get("errcode", 0) != 0:
            logger.error("微信文本安全检查失败: %s", payload)
            raise ContentCheckUnavailableError("内容安全检查失败，请稍后重试")
        if payload.get("result", {}).get("suggest") != "pass":
            raise ContentRejectedError("内容未通过安全检查，请修改后重试")


def ensure_safe_image(content: bytes, content_type: str) -> None:
    settings = get_settings()
    if not settings.content_moderation_enabled or settings.environment == "development":
        return
    if not content or len(content) > 1024 * 1024:
        raise ContentRejectedError("图片大小不符合要求")
    try:
        image = Image.open(io.BytesIO(content))
        image.verify()
    except Exception as exc:
        raise ContentRejectedError("图片文件无效") from exc

    token, token_param = _get_token()
    try:
        response = httpx.post(
            "https://api.weixin.qq.com/wxa/img_sec_check",
            params={token_param: token},
            files={"media": ("upload.jpg", content, content_type)},
            timeout=12,
            verify=ssl_verify(),
        )
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        raise ContentCheckUnavailableError("图片安全服务暂时不可用") from exc
    if payload.get("errcode", 0) != 0:
        if payload.get("errcode") in {87014}:
            raise ContentRejectedError("图片未通过安全检查")
        logger.error("微信图片安全检查失败: %s", payload)
        raise ContentCheckUnavailableError("图片安全检查失败，请稍后重试")
