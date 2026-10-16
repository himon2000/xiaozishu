"""HTTP 出站请求的 TLS 校验开关。

微信云托管的公网出口经平台网关转发，网关使用自签证书，
Python httpx 默认严格校验会直接抛
``[SSL: CERTIFICATE_VERIFY_FAILED] self-signed certificate``。

约定：环境变量 ``VERIFY_SSL`` 显式设为 true/1/yes 时恢复严格校验；
默认（云托管场景）跳过校验。
"""
from __future__ import annotations

import os


def ssl_verify() -> bool:
    """返回 httpx 客户端应使用的 verify 参数。"""
    return os.environ.get("VERIFY_SSL", "false").lower() in ("1", "true", "yes")
