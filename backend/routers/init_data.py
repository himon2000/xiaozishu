"""
初始化路由：生成演示数据
用于快速初始化数据库演示数据
⚠️ 仅 admin 角色可在非 debug 环境调用
"""
import uuid
import random
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from utils.db import get_db
from models import User, Service
from dependencies import require_role

router = APIRouter(prefix="/api/v1/init", tags=["初始化"])


class InitDemoDataRequest(BaseModel):
    generate_services: bool = True


# 演示服务模板
DEMO_SERVICES = {
    "chuan_gong": [
        {"title": "考研数学一对一全程辅导", "price": 20000, "desc": "复旦学长亲自授课，从基础到冲刺全程陪伴"},
        {"title": "四六级英语冲刺班", "price": 8000, "desc": "高频词汇+真题精讲+作文模板"},
        {"title": "全国大学生数学竞赛培训", "price": 30000, "desc": "获奖选手分享竞赛技巧"},
        {"title": "期末高数速成辅导", "price": 15000, "desc": "考前重点梳理，快速提分"},
        {"title": "Python编程入门到进阶", "price": 12000, "desc": "零基础系统学习编程"},
    ],
    "mi_jing": [
        {"title": "大创项目组队招募", "price": 5000, "desc": "招募队友共同完成省级大创"},
        {"title": "数学建模竞赛组队", "price": 8000, "desc": "美赛/国赛组队，有经验者优先"},
        {"title": "互联网+创业项目招募", "price": 3000, "desc": "招募技术/运营合伙人"},
        {"title": "科研论文写作指导", "price": 20000, "desc": "SCI发表经验导师指导"},
    ],
    "zong_men": [
        {"title": "考研院校专业一对一规划", "price": 15000, "desc": "根据个人情况制定最优考研方案"},
        {"title": "高考志愿填报咨询", "price": 10000, "desc": "十年经验志愿规划师"},
        {"title": "保研夏令营申请指导", "price": 18000, "desc": "材料准备+面试技巧"},
        {"title": "留学申请全程服务", "price": 50000, "desc": "TOP50名校申请"},
    ],
    "xia_shan": [
        {"title": "大厂实习内推机会", "price": 5000, "desc": "阿里/腾讯/字节等大厂内推"},
        {"title": "简历优化服务", "price": 3000, "desc": "HR视角优化简历"},
        {"title": "模拟面试实战训练", "price": 8000, "desc": "真实面试场景模拟"},
        {"title": "名企远程实习项目", "price": 15000, "desc": "远程可完成"},
    ],
    "zhi_fa": [
        {"title": "校园推广代理招募", "price": 2000, "desc": "轻松兼职，按单结算"},
        {"title": "内容审核兼职", "price": 5000, "desc": "远程兼职，时间灵活"},
        {"title": "校园大使招募", "price": 3000, "desc": "校园推广，用户增长"},
    ],
    "cang_jing": [
        {"title": "考研全套复习资料", "price": 500, "desc": "含真题、笔记、思维导图"},
        {"title": "大学各科期末复习资料包", "price": 200, "desc": "覆盖理工文史"},
        {"title": "Python学习路线图", "price": 100, "desc": "从入门到就业完整指南"},
        {"title": "英语四六级备考攻略", "price": 150, "desc": "高效备考方法"},
    ],
}

TAGS = {
    "chuan_gong": ["考研", "数学", "英语", "竞赛"],
    "mi_jing": ["科研", "组队", "竞赛", "项目"],
    "zong_men": ["志愿", "考研", "保研", "留学"],
    "xia_shan": ["实习", "简历", "面试", "职场"],
    "zhi_fa": ["推广", "运营", "兼职"],
    "cang_jing": ["资料", "笔记", "教程"],
}


def _ensure_demo_users(db: Session) -> User:
    """确保存在演示用户"""
    # 查找 provider 用户
    provider = db.query(User).filter(User.role == "provider").first()
    if not provider:
        import time
        provider = User(
            id=f"D{int(time.time() * 1000) % 100000:05d}",
            openid=f"demo_provider_{int(time.time())}",
            nickname="🍠 大虾学姐",
            role="provider",
            level=5,
            school="复旦大学",
            cert_status="verified",
            exp_points=5000,
            total_orders_done=25,
            rating=4.9,
            rating_count=30,
        )
        db.add(provider)
        db.commit()
        db.refresh(provider)
    return provider


def _generate_demo_services(db: Session, provider: User) -> int:
    """生成演示服务"""
    existing = db.query(Service).filter(
        Service.provider_openid == provider.openid
    ).count()
    if existing > 0:
        return existing

    count = 0
    for dao_fa_type, templates in DEMO_SERVICES.items():
        for idx, template in enumerate(templates):
            svc = Service(
                id=f"SVC{uuid.uuid4().hex[:8].upper()}",
                provider_openid=provider.openid,
                dao_fa_type=dao_fa_type,
                title=template["title"],
                description=template["desc"],
                tags=TAGS.get(dao_fa_type, [])[:2],
                subjects=[TAGS.get(dao_fa_type, [None])[0]] if dao_fa_type in TAGS else [],
                pricing_mode="per_session",
                price=template["price"],
                unit="次",
                min_sessions=1,
                delivery_methods=["线上"],
                location="上海市",
                status="on_sale",
                rating=round(random.uniform(4.5, 5.0), 1),
                review_count=random.randint(5, 50),
                order_count=random.randint(10, 200),
                created_at=datetime.now() - timedelta(days=random.randint(1, 30)),
            )
            db.add(svc)
            count += 1

    db.commit()
    return count


@router.post("/demo-data")
async def init_demo_data(
    body: InitDemoDataRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    """
    初始化演示数据
    生成演示用户和示例服务
    """
    result = {"users": {"provider": None}, "services": 0}

    # 确保演示用户存在
    provider = _ensure_demo_users(db)
    result["users"]["provider"] = {
        "openid": provider.openid,
        "nickname": provider.nickname,
        "role": provider.role,
    }

    # 生成演示服务
    if body.generate_services:
        service_count = _generate_demo_services(db, provider)
        result["services"] = service_count

    return {
        "code": 0,
        "message": "演示数据初始化成功",
        "data": result,
    }


@router.get("/categories")
async def get_categories():
    """获取六大道法分类"""
    return {
        "categories": [
            {"id": "chuan_gong", "name": "传功授法", "desc": "学科辅导/竞赛陪练", "icon": "📚", "color": "#e74c3c"},
            {"id": "mi_jing",    "name": "联袂问道", "desc": "课题带教/科研组队", "icon": "🔬", "color": "#9b59b6"},
            {"id": "zong_men",   "name": "万宗宝鉴", "desc": "志愿咨询/名校攻略", "icon": "🏫", "color": "#3498db"},
            {"id": "xia_shan",   "name": "下山历练", "desc": "实习内推/名企就业", "icon": "💼", "color": "#2ecc71"},
            {"id": "zhi_fa",     "name": "天衡裁决", "desc": "纠纷仲裁/客服支持", "icon": "⚙️",  "color": "#f39c12"},
            {"id": "cang_jing",  "name": "道藏天阁", "desc": "学习笔记/经验攻略", "icon": "📖", "color": "#1abc9c"},
        ]
    }
