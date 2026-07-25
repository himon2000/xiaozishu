"""
小紫薯 API - 启动管理脚本
腾讯云云托管要求使用 manage.py 作为入口
"""
import os
import sys

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn
from config import get_settings

settings = get_settings()

if __name__ == "__main__":
    # 端口从环境变量读取，默认 8080（云托管会在创建服务时指定端口）
    port = int(os.environ.get("PORT", 8080))

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,  # 生产环境不启用热重载
        log_level="info",
    )
