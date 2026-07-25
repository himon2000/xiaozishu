"""
《小紫薯》配置管理
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    # 微信小程序凭证（必须通过环境变量注入，禁止硬编码）
    # 本地开发请在 backend/.env 文件中配置，参考 .env.example
    wechat_appid: str
    wechat_secret: str
    wechat_mchid: str = "test_mchid"  # ⚠️ 生产环境必须通过 .env 配置真实值
    wechat_mchserialno: str = "test_serial"  # ⚠️ 生产环境必须通过 .env 配置真实值
    wechat_mchapiv3key: str = "test_apiv3key"  # ⚠️ 生产环境必须通过 .env 配置真实值
    wechat_mchprivatekey: str = str(BASE_DIR / "certs/apiclient_key.pem")

    # 微信公众号
    official_account_appid: str = ""
    official_account_appsecret: str = ""
    official_account_original_id: str = ""

    # 云开发
    tcb_secret_id: str = ""
    tcb_secret_key: str = ""
    tcb_env_id: str = ""

    # JWT Secret（必须通过环境变量注入，禁止使用弱默认值）
    # 本地开发请在 backend/.env 文件中配置，参考 .env.example
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080  # 7天

    # 数据库
    # 必须显式配置，生产环境使用云托管内网 MySQL。
    database_url: str

    # 服务
    host: str = "0.0.0.0"
    port: int = 80
    debug: bool = False
    environment: str = "development"

    class Config:
        env_file = BASE_DIR / ".env"
        env_file_encoding = "utf-8"
        # .env 同时供 Docker Compose 读取 MYSQL_* 变量；
        # 应用配置只消费自身声明的字段。
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
