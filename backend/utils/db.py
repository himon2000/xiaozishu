"""
数据库会话管理（SQLAlchemy）
支持 SQLite（开发）、MySQL（生产）和 PostgreSQL
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from config import get_settings

settings = get_settings()

# 将异步 PostgreSQL URL 转换为同步驱动 URL。
_db_url = settings.database_url
if "postgresql+asyncpg://" in _db_url:
    _db_url = _db_url.replace("postgresql+asyncpg", "postgresql")

_engine_options = {
    "echo": settings.debug,
    "pool_pre_ping": True,
}

# 云托管到 MySQL 的内网连接可能被服务端回收；在回收前主动更新连接，
# 避免实例空闲后第一次请求遇到失效连接。
if _db_url.startswith("mysql"):
    _engine_options["pool_recycle"] = 280

engine = create_engine(_db_url, **_engine_options)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """
    FastAPI 依赖注入：提供数据库会话
    用法：db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
