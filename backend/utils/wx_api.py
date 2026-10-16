"""微信开放接口 base URL 选择。

微信云托管容器内访问 api.weixin.qq.com 应走内网 HTTP：
- 免公网出网、无自签证书 TLS 问题（无需 verify=False）；
- 延迟更低、不计公网流量。

判定依据：云托管容器会注入 TCB_ENV 环境变量，
或在 /.tencentcloudbase/wx/ 下挂载云调用令牌文件。
非云托管环境（自建服务器 / 本地开发）回退 https。
"""
from __future__ import annotations

import os

CLOUDBASE_TOKEN_PATH = "/.tencentcloudbase/wx/cloudbase_access_token"

_HTTP_BASE = "http://api.weixin.qq.com"
_HTTPS_BASE = "https://api.weixin.qq.com"


def in_wx_cloudrun() -> bool:
    """当前是否运行在微信云托管容器内。"""
    if os.environ.get("TCB_ENV") or os.environ.get("CBR_ENV_ID"):
        return True
    try:
        return os.path.exists(os.path.dirname(CLOUDBASE_TOKEN_PATH))
    except Exception:
        return False


def wx_api_base() -> str:
    """返回微信开放接口 base URL（云托管走内网 http，其余走 https）。"""
    return _HTTP_BASE if in_wx_cloudrun() else _HTTPS_BASE
