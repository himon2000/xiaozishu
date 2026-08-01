"""微信文本内容安全检查。生产环境默认启用，开发环境不访问微信接口。"""
from __future__ import annotations

import logging
import io
import threading
import time
from typing import Any

import httpx
from PIL import Image

from config import get_settings

logger = logging.getLogger(__name__)
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


def _get_access_token() -> str:
    global _access_token, _access_token_expires_at
    now = time.time()
    if _access_token and now < _access_token_expires_at:
        return _access_token

    with _token_lock:
        now = time.time()
        if _access_token and now < _access_token_expires_at:
            return _access_token
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
        return token


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
        token = _get_access_token()
        try:
            response = httpx.post(
                "https://api.weixin.qq.com/wxa/msg_sec_check",
                params={"access_token": token},
                json={"content": chunk, "version": 2, "scene": 2, "openid": openid},
                timeout=8,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            raise ContentCheckUnavailableError("内容安全服务暂时不可用") from exc

        if payload.get("errcode", 0) != 0:
            logger.error("微信文本安全检查失败: %s", payload.get("errcode"))
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

    token = _get_access_token()
    try:
        response = httpx.post(
            "https://api.weixin.qq.com/wxa/img_sec_check",
            params={"access_token": token},
            files={"media": ("upload.jpg", content, content_type)},
            timeout=12,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        raise ContentCheckUnavailableError("图片安全服务暂时不可用") from exc
    if payload.get("errcode", 0) != 0:
        if payload.get("errcode") in {87014}:
            raise ContentRejectedError("图片未通过安全检查")
        logger.error("微信图片安全检查失败: %s", payload.get("errcode"))
        raise ContentCheckUnavailableError("图片安全检查失败，请稍后重试")
