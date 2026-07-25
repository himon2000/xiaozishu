"""
《小紫薯》FastAPI 主入口
微信云托管 + 本地开发双支持
"""
import os
import logging
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import get_settings
from models import init_db
from routers import auth, services, orders, mentorships, levels, resources, school_wiki, teams, disputes, reviews, init_data, stages, roles, wallet, opportunities, demands

logger = logging.getLogger(__name__)
settings = get_settings()

# ── FastAPI 应用初始化 ──────────────────────────────────
app = FastAPI(
    title="小紫薯 API",
    description="《小紫薯》校园互助平台后端 API",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# ── CORS ────────────────────────────────────────────────
# 微信云托管内网调用无需 CORS；此处主要用于本地开发时前端直连。
# 生产环境请将 CORS_ORIGINS 环境变量设置为实际域名，例如：
#   CORS_ORIGINS=https://your-domain.com,https://api.your-domain.com
_raw_origins = os.environ.get("CORS_ORIGINS", "")
_allow_origins: list[str] = (
    [o.strip() for o in _raw_origins.split(",") if o.strip()]
    if _raw_origins
    else (["*"] if settings.environment == "development" else [])
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    # allow_credentials 与 allow_origins=["*"] 不能同时为 True（浏览器会拒绝）
    # 仅在明确指定了域名时才开启 credentials
    allow_credentials=bool(_allow_origins and _allow_origins != ["*"]),
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# ── 启动时初始化数据库 ───────────────────────────────────
@app.on_event("startup")
def startup():
    init_db()
    # P2-8: 生产环境校验微信支付参数
    if settings.environment != "development":
        if settings.wechat_mchid == "test_mchid":
            logger.warning("⚠️ 生产环境使用测试微信支付参数！请通过环境变量配置真实值。")
    logger.info(f"《小紫薯》API 启动成功 | 环境: {settings.environment} | 端口: {settings.port}")


# ── 全局异常处理 ────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc) if settings.debug else "服务器内部错误"},
    )


# ── 健康检查 ────────────────────────────────────────────
@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "小紫薯 API",
        "version": "1.0.0",
        "environment": settings.environment,
    }


@app.get("/")
def root():
    return {
        "service": "《小紫薯》",
        "version": "1.0.0",
        "environment": settings.environment,
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "auth": "/api/v1/auth",
            "services": "/api/v1/services",
            "orders": "/api/v1/orders",
            "disputes": "/api/v1/disputes",
            "reviews": "/api/v1/reviews",
            "mentorships": "/api/v1/mentorships",
            "levels": "/api/v1/level",
            "dividend": "/api/v1/level/dividend-pool",
            "resources": "/api/v1/resources",
            "schoolWiki": "/api/v1/school-wiki",
            "teams": "/api/v1/teams",
            "opportunities": "/api/v1/opportunities",
        }
    }


# ── 注册路由 ────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(wallet.router)  # 灵石充值
app.include_router(services.router)
app.include_router(orders.router)
app.include_router(mentorships.router)
app.include_router(levels.router)
app.include_router(resources.router)
app.include_router(school_wiki.router)
app.include_router(teams.router)
app.include_router(opportunities.router)  # 下山历练-就业资源
app.include_router(demands.router)
app.include_router(disputes.router)
app.include_router(reviews.router)
app.include_router(init_data.router)
app.include_router(stages.router)
app.include_router(roles.router)


def prioritize_static_routes() -> None:
    def route_score(route) -> tuple[int, int, int]:
        path = getattr(route, "path", "")
        segments = [seg for seg in path.split("/") if seg]
        dynamic_count = sum("{" in seg and "}" in seg for seg in segments)
        static_count = len(segments) - dynamic_count
        return dynamic_count, -static_count, -len(path)

    app.router.routes.sort(key=route_score)


prioritize_static_routes()


# ── 启动命令 ────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info",
    )
