"""
演示服务数据生成脚本
用于生成示例服务数据，方便测试

运行方式: python -m routers.demo_services
"""
import uuid
from datetime import datetime, timedelta
import random
from utils.db import get_db
from models import Service, User

# 六大道法分类
DAO_FA_TYPES = [
    ("chuan_gong", "传功授法", "📚", ["考研数学", "四六级辅导", "竞赛培训", "期末冲刺"]),
    ("mi_jing", "联袂问道", "🔬", ["科研带教", "课题组队", "竞赛组队", "项目合作"]),
    ("zong_men", "万宗宝鉴", "🏫", ["志愿填报", "自主招生", "考研规划", "留学咨询"]),
    ("xia_shan", "下山历练", "💼", ["实习内推", "名企兼职", "简历优化", "面试辅导"]),
    ("zhi_fa", "天衡裁决", "⚙️", ["平台运营", "内容审核", "客服实习", "推广代理"]),
    ("cang_jing", "道藏天阁", "📖", ["学习笔记", "考研资料", "技能教程", "经验分享"]),
]

# 演示服务模板
DEMO_SERVICES = {
    "chuan_gong": [
        {"title": "考研数学一对一全程辅导", "price": 20000, "desc": "复旦学长亲自授课，从基础到冲刺全程陪伴"},
        {"title": "四六级英语冲刺班", "price": 8000, "desc": "高频词汇+真题精讲+作文模板"},
        {"title": "全国大学生数学竞赛培训", "price": 30000, "desc": "获奖选手分享竞赛技巧，历年真题解析"},
        {"title": "期末高数/线代速成辅导", "price": 15000, "desc": "考前重点梳理，快速提分"},
        {"title": "Python编程入门到进阶", "price": 12000, "desc": "适合零基础，系统学习编程思维"},
    ],
    "mi_jing": [
        {"title": "大创项目组队招募", "price": 5000, "desc": "招募队友共同完成省级大创项目"},
        {"title": "数学建模竞赛组队", "price": 8000, "desc": "美赛/国赛组队，有经验者优先"},
        {"title": "互联网+创业项目招募", "price": 3000, "desc": "校园创业项目招募技术/运营合伙人"},
        {"title": "科研论文写作指导", "price": 20000, "desc": "SCI发表经验导师一对一指导"},
    ],
    "zong_men": [
        {"title": "考研院校专业一对一规划", "price": 15000, "desc": "根据个人情况制定最优考研方案"},
        {"title": "高考志愿填报咨询", "price": 10000, "desc": "十年经验志愿规划师，科学填报"},
        {"title": "保研夏令营申请指导", "price": 18000, "desc": "材料准备+面试技巧+导师推荐"},
        {"title": "留学申请全程服务", "price": 50000, "desc": "TOP50名校申请，DIY辅助"},
    ],
    "xia_shan": [
        {"title": "大厂实习内推机会", "price": 5000, "desc": "阿里/腾讯/字节等大厂内推码"},
        {"title": "简历优化服务", "price": 3000, "desc": "HR视角优化，突出核心竞争力"},
        {"title": "模拟面试实战训练", "price": 8000, "desc": "真实面试场景，实时反馈改进"},
        {"title": "名企远程实习项目", "price": 15000, "desc": "远程可完成，为简历加分"},
    ],
    "zhi_fa": [
        {"title": "校园推广代理招募", "price": 2000, "desc": "轻松兼职，按单结算"},
        {"title": "内容审核兼职", "price": 5000, "desc": "远程兼职，时间灵活"},
        {"title": "校园大使招募", "price": 3000, "desc": "校园推广，用户增长"},
    ],
    "cang_jing": [
        {"title": "考研全套复习资料", "price": 500, "desc": "含真题、笔记、思维导图"},
        {"title": "大学各科期末复习资料包", "price": 200, "desc": "覆盖理工文史，考点精编"},
        {"title": "Python学习路线图", "price": 100, "desc": "从入门到就业的完整学习指南"},
        {"title": "英语四六级备考攻略", "price": 150, "desc": "高效备考方法+资料推荐"},
    ],
}


def generate_demo_services():
    """生成演示服务数据"""
    db = next(get_db())

    # 获取演示用户（provider角色）
    provider = db.query(User).filter(User.role == "provider").first()
    if not provider:
        print("❌ 未找到演示用户，请先通过demo-login创建")
        return

    print(f"✅ 找到演示用户: {provider.nickname}")

    # 检查是否已有服务
    existing = db.query(Service).filter(Service.provider_openid == provider.openid).count()
    if existing > 0:
        print(f"⚠️ 已存在 {existing} 个服务，跳过生成")
        return

    # 生成服务
    service_count = 0
    for dao_fa_type, dao_name, icon, tags in DAO_FA_TYPES:
        services_templates = DEMO_SERVICES.get(dao_fa_type, [])
        for idx, template in enumerate(services_templates):
            svc = Service(
                id=f"SVC{uuid.uuid4().hex[:10].upper()}",
                provider_openid=provider.openid,
                dao_fa_type=dao_fa_type,
                title=template["title"],
                description=template["desc"],
                tags=tags[:2],
                subjects=[tags[0]] if tags else [],
                pricing_mode="per_session",
                price=template["price"],
                unit="次",
                min_sessions=1,
                delivery_methods=["线上", "线下"],
                location="上海市",
                status="on_sale",
                rating=round(random.uniform(4.5, 5.0), 1),
                review_count=random.randint(5, 50),
                order_count=random.randint(10, 200),
                created_at=datetime.now() - timedelta(days=random.randint(1, 30)),
            )
            db.add(svc)
            service_count += 1

    db.commit()
    print(f"🎉 成功生成 {service_count} 个演示服务！")


if __name__ == "__main__":
    print("📦 正在生成演示服务数据...")
    generate_demo_services()
    print("✨ 完成！")
