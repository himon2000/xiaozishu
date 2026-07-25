"""

认证路由：登录、注册、认证申请

"""

import uuid

import random

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy.orm import Session

from pydantic import BaseModel, Field

from utils.db import get_db

from utils.jwt_utils import create_access_token

from models import User, Service, Order, Resource, Review, Team, TeamMember

from services import wechat_auth as wx_auth, stage_service, role_service

from dependencies import get_current_user



router = APIRouter(prefix="/api/v1/auth", tags=["认证"])



# 演示登录请求/响应模型

class DemoLoginRequest(BaseModel):

    role: str = Field(default="seeker", pattern="^(seeker|provider|elder)$")  # seeker, provider, elder



class DemoLoginResponse(BaseModel):

    access_token: str

    token_type: str = "bearer"

    user: dict
class LoginRequest(BaseModel):

    code: str  # wx.login() 获取的 code





class LoginResponse(BaseModel):

    access_token: str

    token_type: str = "bearer"

    user: dict





class CertRequest(BaseModel):

    cert_type: str = Field(..., pattern="^(xuexin|enterprise_email|invite_code)$")  # xuexin | enterprise_email | invite_code

    school: str = ""

    school_level: str = ""

    major: str = ""

    graduation_year: int = 0

    cert_doc_url: str = ""

    referrer_code: str = ""





class ProfileUpdateRequest(BaseModel):

    nickname: str = Field(default="", max_length=20)

    bio: str = Field(default="", max_length=200)  # 个人简介

    gender: str = ""  # male | female | secret

    birthday: str = ""  # YYYY-MM-DD





class UserStatsResponse(BaseModel):

    total_services: int  # 发布的服务数

    on_sale_services: int  # 在售服务数

    total_orders: int  # 总订单数

    completed_orders: int  # 完成的订单数

    total_spent: int  # 总消费

    total_earned: int  # 总收入

    resources_published: int  # 发布的资源数

    reviews_given: int  # 给出的评价数

    reviews_received: int  # 收到的评价数

    teams_joined: int  # 加入的组队数

    followers: int  # 粉丝数

    following: int  # 关注数





@router.post("/demo-login", response_model=DemoLoginResponse)

async def demo_login(body: DemoLoginRequest, db: Session = Depends(get_db)):

    """

    演示登录 - 用于测试

    自动创建指定角色的演示用户

    仅在 debug 模式或 ENABLE_DEMO=true 时可用

    """

    import time
    import os
    from config import get_settings

    settings = get_settings()

    # P1-8 修复：Demo 数据注入控制
    enable_demo = settings.debug or os.environ.get("ENABLE_DEMO") == "true"
    if not enable_demo:
        raise HTTPException(status_code=403, detail="演示登录仅在调试模式下可用")



    # 生成演示openid

    demo_openid = f"demo_{body.role}_{int(time.time())}"



    # 角色配置

    role_config = {

        "seeker": {"nickname": "🍀 散修小明", "level": 1, "school": "待认证", "cert_status": "none"},

        "provider": {"nickname": "🍠 大虾学姐", "level": 5, "school": "复旦大学", "cert_status": "verified"},

        "elder": {"nickname": "🏛️ 长老王老师", "level": 5, "school": "复旦附中", "cert_status": "verified"},

    }



    config = role_config.get(body.role, role_config["seeker"])



    # 查询或创建用户

    user = db.query(User).filter(User.openid == demo_openid).first()

    if not user:

        user = User(

            id=f"D{int(time.time() * 1000) % 100000:05d}",

            openid=demo_openid,

            nickname=config["nickname"],

            role=body.role,

            level=config["level"],

            school=config["school"],

            cert_status=config["cert_status"],

            referral_code=wx_auth.generate_referral_code(),

            exp_points=5000 if config["level"] == 5 else 100,

            total_orders_done=25 if config["level"] == 5 else 3,

            rating=4.9 if config["level"] == 5 else 4.5,

            rating_count=30 if config["level"] == 5 else 5,

        )

        db.add(user)

        db.commit()

        db.refresh(user)



        # provider角色登录时自动生成演示服务

        if body.role == "provider":

            _generate_demo_services_for_user(db, user)



        # 初始化人生阶段

        stages = stage_service.init_user_stages(db, user.openid)

        # 更新默认阶段的角色

        current_stage = stage_service.get_current_stage(db, user.openid)

        if current_stage and current_stage['role'] != body.role:

            stage_service.update_stage(db, current_stage['id'], user.openid, role=body.role)

        # 解锁演示角色

        if body.role in ["provider", "elder"]:

            role_service.enable_role(db, user.openid, body.role)

            user.current_role = body.role

            db.commit()





    # 初始化用户角色（多角色体系）

    role_service.init_user_roles(db, user.openid)



    # 解锁演示角色（provider/elder演示登录时自动解锁对应角色）

    if body.role in ["provider", "elder"]:

        role_service.enable_role(db, user.openid, body.role)

        user.current_role = body.role

        db.commit()



    # 生成 token

    token = create_access_token(user.openid, user.role)



    # 获取当前人生阶段

    current_stage = stage_service.get_current_stage(db, user.openid)

    all_stages = stage_service.get_user_stages(db, user.openid)

    # 获取用户所有角色

    all_roles = role_service.get_user_roles(db, user.openid)

    current_role_obj = next((r for r in all_roles if r["role"] == (user.current_role or "seeker")), all_roles[0] if all_roles else None)



    return DemoLoginResponse(

        access_token=token,

        user={

            "id": user.id,

            "openid": user.openid,

            "nickname": user.nickname,

            "avatar_url": user.avatar_url,

            "role": user.current_role or user.role,

            "cert_status": user.cert_status,

            "level": current_role_obj.get("level", 1) if current_role_obj else 1,

            "level_name": current_role_obj.get("level_name", "练气期") if current_role_obj else "练气期",

            "school": user.school,

            "referral_code": user.referral_code,

            "is_new_user": False,

            # 人生阶段信息

            "current_stage": current_stage,

            "all_stages": all_stages,

            # 多角色信息

            "roles": all_roles,

            "current_role_obj": current_role_obj,

            "enterprise_email_verified": user.enterprise_email_verified,

        }

    )





@router.post("/login", response_model=LoginResponse)

async def login(body: LoginRequest, db: Session = Depends(get_db)):

    """

    微信登录

    1. 通过 code2session 获取 openid

    2. 创建或更新用户记录

    3. 返回 JWT token

    """

    # 获取 openid（本地开发环境使用模拟openid）

    try:

        session_data = await wx_auth.code2session(body.code)

        openid = session_data["openid"]

    except Exception:

        # 本地开发/测试：使用 code 本身作为 openid

        openid = f"dev_{body.code[:20]}"



    # 查询或创建用户

    user = db.query(User).filter(User.openid == openid).first()

    is_new_user = False

    if not user:

        is_new_user = True

        user = User(

            id=f"U{uuid.uuid4().hex[:10].upper()}",

            openid=openid,

            nickname=f"散修{uuid.uuid4().hex[:4]}",

            role="seeker",

            referral_code=wx_auth.generate_referral_code(),

        )

        db.add(user)

        db.commit()

        db.refresh(user)



    # 初始化人生阶段

    stage_service.init_user_stages(db, user.openid)



    # 初始化用户角色（多角色体系）

    role_service.init_user_roles(db, user.openid)



    # 生成 token

    token = create_access_token(user.openid, user.role)



    # 获取当前人生阶段

    current_stage = stage_service.get_current_stage(db, user.openid)

    all_stages = stage_service.get_user_stages(db, user.openid)

    # 获取用户所有角色

    all_roles = role_service.get_user_roles(db, user.openid)

    current_role_obj = next((r for r in all_roles if r["role"] == (user.current_role or "seeker")), all_roles[0] if all_roles else None)



    return LoginResponse(

        access_token=token,

        user={

            "id": user.id,

            "openid": user.openid,

            "nickname": user.nickname,

            "avatar_url": user.avatar_url,

            "role": user.current_role or user.role,

            "cert_status": user.cert_status,

            "level": current_role_obj.get("level", 1) if current_role_obj else 1,

            "level_name": current_role_obj.get("level_name", "练气期") if current_role_obj else "练气期",

            "referral_code": user.referral_code,

            "is_new_user": is_new_user,

            # 人生阶段信息

            "current_stage": current_stage,

            "all_stages": all_stages,

            # 多角色信息

            "roles": all_roles,

            "current_role_obj": current_role_obj,

            "enterprise_email_verified": user.enterprise_email_verified,

        }

    )





@router.post("/cert/apply")

def apply_cert(

    body: CertRequest,

    user: User = Depends(get_current_user),

    db: Session = Depends(get_db),

):

    """

    提交身份认证申请

    大虾必须通过学信网认证

    长老可通过企业邮箱或邀请码认证

    """

    user.cert_type = body.cert_type

    user.cert_status = "pending"

    user.school = body.school

    user.school_level = body.school_level

    user.major = body.major

    user.graduation_year = body.graduation_year

    user.cert_doc_url = body.cert_doc_url



    # 处理飞花令牌

    if body.referrer_code:

        referrer = db.query(User).filter(

            User.referral_code == body.referrer_code

        ).first()

        if referrer:

            user.referrer_openid = referrer.openid



    # 如果申请大虾认证，变更角色

    if body.cert_type == "xuexin" and body.school_level in ["undergrad", "postgrad", "phd"]:

        user.role = "provider"



    db.commit()

    return {"success": True, "message": "认证申请已提交，请等待审核"}





@router.get("/referral-code")

def get_my_referral_code(

    user: User = Depends(get_current_user),

):

    """获取我的飞花令牌"""

    return {
        "referral_code": user.referral_code,
        "total_invited": user.total_invited or 0,
        "invite_tree_depth": user.invite_tree_depth or 0,
    }





@router.get("/me")

def get_me(

    user: User = Depends(get_current_user),

    db: Session = Depends(get_db)

):

    """获取当前用户完整信息"""

    current_stage = stage_service.get_current_stage(db, user.openid)

    all_stages = stage_service.get_user_stages(db, user.openid)

    all_roles = role_service.get_user_roles(db, user.openid)

    current_role_obj = next((r for r in all_roles if r["role"] == (user.current_role or "seeker")), all_roles[0] if all_roles else None)



    return {

        "id": user.id,

        "openid": user.openid,

        "nickname": user.nickname,

        "avatar_url": user.avatar_url,

        "role": user.current_role or user.role,

        "status": user.status,

        "cert_type": user.cert_type,

        "cert_status": user.cert_status,

        "school": user.school,

        "school_level": user.school_level,

        "level": current_role_obj.get("level", 1) if current_role_obj else 1,

        "exp_points": current_role_obj.get("exp_points", 0) if current_role_obj else 0,

        "level_name": current_role_obj.get("level_name", "练气期") if current_role_obj else "练气期",

        "level_color": _get_level_color(current_role_obj.get("level", 1) if current_role_obj else 1),

        "total_orders_done": current_role_obj.get("total_orders_done", 0) if current_role_obj else 0,

        "rating": current_role_obj.get("rating", 5.0) if current_role_obj else 5.0,

        "rating_count": current_role_obj.get("rating_count", 0) if current_role_obj else 0,

        "referral_code": user.referral_code,

        "spirit_stones_balance": user.spirit_stones or 0,
        "spirit_stones": user.spirit_stones or 0,
        "spirit_stones_frozen": user.spirit_stones_frozen or 0,
        # 兼容现有个人中心/资产页面字段。
        "lingshi": user.spirit_stones or 0,
        "frozen_lingshi": user.spirit_stones_frozen or 0,
        "cultivation_level": current_role_obj.get("level", 1) if current_role_obj else 1,
        "cultivation_exp": current_role_obj.get("exp_points", 0) if current_role_obj else 0,

        "available": user.available,

        "created_at": user.created_at.isoformat() if user.created_at else "",

        "current_stage": current_stage,

        "all_stages": all_stages,

        "roles": all_roles,

        "current_role_obj": current_role_obj,

        "enterprise_email_verified": user.enterprise_email_verified,
        "bio": user.bio or "",
        "gender": user.gender or "",
        "birthday": user.birthday or "",

    }





def _get_level_name(level: int) -> str:

    names = {1: "炼气期", 2: "筑基期", 3: "金丹期", 4: "元婴期", 5: "化神期"}

    return names.get(level, "炼气期")



def _get_level_color(level: int) -> str:

    colors = {1: "#999999", 2: "#00cc44", 3: "#4499ff", 4: "#cc44ff", 5: "#ffd700"}

    return colors.get(level, "#999999")





# 演示服务数据模板

DEMO_SERVICES_TEMPLATES = {

    "chuan_gong": [

        {"title": "考研数学一对一全程辅导", "price": 20000, "desc": "复旦学长亲自授课，从基础到冲刺全程陪伴"},

        {"title": "四六级英语冲刺班", "price": 8000, "desc": "高频词汇+真题精讲+作文模板"},

        {"title": "全国大学生数学竞赛培训", "price": 30000, "desc": "获奖选手分享竞赛技巧"},

    ],

    "mi_jing": [

        {"title": "大创项目组队招募", "price": 5000, "desc": "招募队友共同完成省级大创项目"},

        {"title": "数学建模竞赛组队", "price": 8000, "desc": "美赛/国赛组队，有经验者优先"},

    ],

    "zong_men": [

        {"title": "考研院校专业一对一规划", "price": 15000, "desc": "根据个人情况制定最优考研方案"},

        {"title": "高考志愿填报咨询", "price": 10000, "desc": "十年经验志愿规划师，科学填报"},

    ],

    "xia_shan": [

        {"title": "大厂实习内推机会", "price": 5000, "desc": "阿里/腾讯/字节等大厂内推码"},

        {"title": "简历优化服务", "price": 3000, "desc": "HR视角优化，突出核心竞争力"},

    ],

    "zhi_fa": [

        {"title": "校园推广代理招募", "price": 2000, "desc": "轻松兼职，按单结算"},

    ],

    "cang_jing": [

        {"title": "考研全套复习资料", "price": 500, "desc": "含真题、笔记、思维导图"},

        {"title": "Python学习路线图", "price": 100, "desc": "从入门到就业的完整学习指南"},

    ],

}





def _generate_demo_services_for_user(db: Session, user: User):

    """为用户生成演示服务数据"""

    import time



    # 检查是否已有服务

    existing_count = db.query(Service).filter(Service.provider_openid == user.openid).count()

    if existing_count > 0:

        return  # 已有服务，跳过



    dao_fa_types = list(DEMO_SERVICES_TEMPLATES.keys())

    all_tags = {

        "chuan_gong": ["考研", "数学", "英语", "竞赛"],

        "mi_jing": ["科研", "组队", "竞赛", "项目"],

        "zong_men": ["志愿", "考研", "保研", "留学"],

        "xia_shan": ["实习", "简历", "面试", "职场"],

        "zhi_fa": ["推广", "运营", "兼职"],

        "cang_jing": ["资料", "笔记", "教程"],

    }



    # 为每个道法类型生成1-2个服务

    for dao_fa_type in dao_fa_types:

        templates = DEMO_SERVICES_TEMPLATES.get(dao_fa_type, [])

        for idx, template in enumerate(templates[:2]):  # 每个类型最多2个

            svc = Service(

                id=f"SVC{int(time.time() * 1000) % 1000000:06d}{idx}",

                provider_openid=user.openid,

                dao_fa_type=dao_fa_type,

                title=template["title"],

                description=template["desc"],

                tags=all_tags.get(dao_fa_type, [])[:2],

                subjects=[all_tags.get(dao_fa_type, [])[0]] if all_tags.get(dao_fa_type) else [],

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



    db.commit()





# ==================== 用户增强接口 ====================



from sqlalchemy import func





@router.put("/users/profile")

def update_profile(

    body: ProfileUpdateRequest,

    user: User = Depends(get_current_user),

    db: Session = Depends(get_db),

):

    """

    更新用户资料

    - 昵称（需审核）

    - 个人简介

    - 性别

    - 生日

    """

    if body.nickname:

        user.nickname = body.nickname

    if body.bio is not None:

        user.bio = body.bio

    if body.gender:

        user.gender = body.gender

    if body.birthday:

        user.birthday = body.birthday



    db.commit()

    return {"success": True, "message": "资料更新成功"}





@router.get("/users/profile/{openid}")

def get_user_profile(

    openid: str,

    db: Session = Depends(get_db),

):

    """

    获取他人公开资料

    - 不需要登录即可访问

    - 只返回公开信息

    """

    target_user = db.query(User).filter(User.openid == openid).first()

    if not target_user:

        raise HTTPException(status_code=404, detail="用户不存在")



    # 计算统计数据

    total_services = db.query(Service).filter(

        Service.provider_openid == openid,

        Service.status == "on_sale"

    ).count()



    completed_orders = db.query(Order).filter(

        ((Order.seeker_openid == openid) | (Order.provider_openid == openid)),

        Order.status == "completed"

    ).count()



    avg_rating = db.query(Service).filter(

        Service.provider_openid == openid

    ).with_entities(func.avg(Service.rating)).scalar() or 0



    return {

        "openid": target_user.openid,

        "nickname": target_user.nickname,

        "avatar_url": target_user.avatar_url,

        "role": target_user.role,

        "level": target_user.level,

        "level_name": _get_level_name(target_user.level),

        "school": target_user.school if target_user.cert_status == "verified" else "未认证",

        "cert_status": target_user.cert_status,

        "bio": target_user.bio or "",

        "rating": float(avg_rating),

        "total_services": total_services,

        "completed_orders": completed_orders,

        "member_since": target_user.created_at.strftime("%Y-%m") if target_user.created_at else "",

    }





@router.get("/users/stats")

def get_user_stats(

    user: User = Depends(get_current_user),

    db: Session = Depends(get_db),

):

    """

    获取用户统计信息

    """

    openid = user.openid



    # 服务统计

    total_services = db.query(Service).filter(Service.provider_openid == openid).count()

    on_sale_services = db.query(Service).filter(

        Service.provider_openid == openid,

        Service.status == "on_sale"

    ).count()



    # 订单统计（P1-2 修复：使用 count 聚合优化）
    from sqlalchemy import func

    orders_as_seeker_count = db.query(func.count(Order.id)).filter(
        Order.seeker_openid == openid
    ).scalar() or 0

    orders_as_provider_count = db.query(func.count(Order.id)).filter(
        Order.provider_openid == openid
    ).scalar() or 0

    completed_as_seeker = db.query(func.count(Order.id)).filter(
        Order.seeker_openid == openid,
        Order.status == "completed"
    ).scalar() or 0

    completed_as_provider = db.query(func.count(Order.id)).filter(
        Order.provider_openid == openid,
        Order.status == "completed"
    ).scalar() or 0

    total_spent = db.query(func.sum(Order.total_paid)).filter(
        Order.seeker_openid == openid,
        Order.status.in_(["completed", "confirmed"])
    ).scalar() or 0

    total_earned = db.query(func.sum(Order.total_paid)).filter(
        Order.provider_openid == openid,
        Order.status.in_(["completed", "confirmed"])
    ).scalar() or 0



    # 资源统计

    resources_published = db.query(Resource).filter(Resource.author_openid == openid).count()



    # 评价统计

    reviews_given = db.query(Review).filter(Review.reviewer_openid == openid).count()

    reviews_received = db.query(Review).filter(Review.provider_openid == openid).count()



    # 组队统计

    teams_joined = db.query(TeamMember).filter(TeamMember.openid == openid).count()



    return {

        "total_services": total_services,

        "on_sale_services": on_sale_services,

        "total_orders": orders_as_seeker_count,

        "completed_orders": completed_as_seeker + completed_as_provider,

        "total_spent": total_spent,

        "total_earned": total_earned,

        "resources_published": resources_published,

        "reviews_given": reviews_given,

        "reviews_received": reviews_received,

        "teams_joined": teams_joined,

        "followers": 0,

        "following": 0,

    }





class RedeemReferralRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=8, description="飞花令牌（XLG + 4位随机字符）")


@router.post("/users/redeem-referral")

def redeem_referral_code(

    body: RedeemReferralRequest,

    user: User = Depends(get_current_user),

    db: Session = Depends(get_db),

):

    """

    兑换飞花令牌

    - 新用户首次使用飞花令牌可获得奖励

    - 推荐人也会获得奖励

    """

    if user.referrer_openid:

        return {"success": False, "message": "您已使用过飞花令牌"}



    referrer = db.query(User).filter(User.referral_code == body.code).first()

    if not referrer:

        raise HTTPException(status_code=404, detail="飞花令牌无效")



    if referrer.openid == user.openid:

        return {"success": False, "message": "不能使用自己的飞花令牌"}



    # 更新推荐关系

    user.referrer_openid = referrer.openid



    # 给新用户奖励（积分）

    user.exp_points += 500



    # 给推荐人奖励（积分 + 修为）

    referrer.exp_points += 200

    referrer.total_invited = (referrer.total_invited or 0) + 1

    # 按修为体系发放推荐修为奖励（+15 修为）

    from services import level_service

    level_service.add_exp(db, referrer, "earn_referral", remark="飞花令牌推荐奖励", auto_commit=False)



    db.commit()



    return {

        "success": True,

        "message": "飞花令牌兑换成功，获得500积分奖励",

        "reward": 500,
        "referrer_openid": referrer.openid,
    }





@router.get("/users/ranking")

def get_user_ranking(

    category: str = "rating",

    limit: int = 20,

    db: Session = Depends(get_db),

):

    """

    获取用户排行榜

    - rating: 评分排行

    - orders: 完成订单数排行

    - earnings: 收入排行

    """

    query = db.query(User)



    if category == "rating":

        users = query.filter(

            User.rating_count >= 5

        ).order_by(User.rating.desc()).limit(limit).all()

    elif category == "orders":

        users = query.order_by(User.total_orders_done.desc()).limit(limit).all()

    elif category == "earnings":

        users = query.filter(User.role == "provider").order_by(User.total_earnings.desc()).limit(limit).all()

    else:

        users = []



    return {

        "category": category,

        "ranking": [

            {

                "rank": idx + 1,

                "openid": u.openid,

                "nickname": u.nickname,

                "avatar_url": u.avatar_url,

                "level": u.level,

                "level_name": _get_level_name(u.level),

                "school": u.school if u.cert_status == "verified" else "未认证",

                "rating": u.rating,

                "rating_count": u.rating_count,

                "value": u.rating if category == "rating" else (

                    u.total_orders_done if category == "orders" else u.total_earnings

                ),

            }

            for idx, u in enumerate(users)

        ]

    }
