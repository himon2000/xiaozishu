"""
《小紫薯》SQLAlchemy 数据模型
"""
from datetime import datetime
from sqlalchemy import (
    Column, String as SAString, Integer, Float, Boolean, DateTime, Text,
    ForeignKey, JSON, Enum as SAEnum, create_engine
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.sql import func
from config import get_settings


class String(SAString):
    """跨数据库字符串类型；MySQL 的 VARCHAR 必须显式指定长度。"""

    def __init__(self, length=255, **kwargs):
        super().__init__(length=length, **kwargs)


Base = declarative_base()

# ── 枚举定义 ────────────────────────────────────────────
class UserRoleType(str):
    """用户角色类型常量"""
    SEEKER = "seeker"       # 散修（高中生/普通人）
    PROVIDER = "provider"   # 大虾（大学生/服务者）
    ELDER = "elder"         # 长老（职场人/专家）
    ADMIN = "admin"         # 执事（平台管理）


class LifeStageType(str):
    """人生阶段类型"""
    HIGH_SCHOOL = "high_school"   # 高中
    COLLEGE = "college"           # 大学
    WORKING = "working"           # 就业


class LifeStageStatus(str):
    """阶段状态"""
    ACTIVE = "active"             # 激活
    INACTIVE = "inactive"         # 暂停
    ARCHIVED = "archived"         # 归档（过往阶段）


class RoleStatus(str):
    """角色状态"""
    LOCKED = "locked"      # 未解锁
    ENABLED = "enabled"    # 已启用
    PENDING = "pending"    # 审核中

class DaoFaType(str):
    CHUAN_GONG = "chuan_gong"   # 传功授法
    MI_JING = "mi_jing"         # 联袂问道
    ZONG_MEN = "zong_men"       # 万宗宝鉴
    XIA_SHAN = "xia_shan"       # 下山历练
    ZHI_FA = "zhi_fa"           # 天衡裁决
    CANG_JING = "cang_jing"     # 道藏天阁


class OpportunityType(str):
    """下山历练-就业资源类型"""
    INTERNSHIP = "internship"   # 寻觅道场（实习机会）
    REFERRAL = "referral"       # 求取推荐（内推资源）
    JOB = "job"                 # 问道职涯（求职/就职）
    JOB_RESOURCE = "job_resource"  # 布施机缘（提供就业资源）


class OpportunityStatus(str):
    """就业资源状态"""
    ACTIVE = "active"          # 进行中
    CLOSED = "closed"          # 已关闭
    EXPIRED = "expired"        # 已过期


class ApplicationStatus(str):
    """申请状态"""
    PENDING = "pending"        # 待处理
    ACCEPTED = "accepted"      # 已通过
    REJECTED = "rejected"      # 已拒绝
    WITHDRAWN = "withdrawn"    # 已撤回

class OrderStatus(str):
    PENDING_PAYMENT = "pending_payment"
    PAID = "paid"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    PENDING_CONFIRM = "pending_confirm"
    COMPLETED = "completed"
    DISPUTE = "dispute"
    ADMIN_RESOLVING = "admin_resolving"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"

class CertStatus(str):
    NONE = "none"
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


# ── 需求模型 ────────────────────────────────────────────
class Demand(Base):
    """用户发布的求助/咨询/组队需求"""
    __tablename__ = "demands"

    id = Column(String, primary_key=True)
    openid = Column(String, ForeignKey("users.openid"), nullable=True, index=True)
    demand_type = Column(String, default="tutor", index=True)
    dao_fa_type = Column(String, default="")
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    budget = Column(Integer, default=0)
    contact = Column(String, default="")
    target_tier = Column(String, default="")
    tags = Column(JSON, default=list)
    status = Column(String, default="open", index=True)
    view_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", foreign_keys=[openid])


# ── 用户模型 ────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    openid = Column(String, unique=True, nullable=False, index=True)
    unionid = Column(String, nullable=True)
    nickname = Column(String, nullable=False, default="散修")
    avatar_url = Column(String, default="")
    phone = Column(String, nullable=True)
    bio = Column(String, default="")  # 个人简介
    gender = Column(String, default="")  # male|female|secret
    birthday = Column(String, default="")  # YYYY-MM-DD

    role = Column(String, default="seeker")  # [兼容] 与 UserRole 表同步
    status = Column(String, default="active")

    # 身份认证 - [兼容] 与 LifeStage 表同步
    cert_type = Column(String, default="none")
    cert_status = Column(String, default="none")
    school = Column(String, default="")  # [兼容] 与 LifeStage 表同步
    school_level = Column(String, default="")  # [兼容] 与 LifeStage 表同步
    major = Column(String, default="")  # [兼容] 与 LifeStage 表同步
    graduation_year = Column(Integer, nullable=True)  # [兼容] 与 LifeStage 表同步
    cert_doc_url = Column(String, default="")
    referrer_openid = Column(String, nullable=True)

    # 修为体系 - [兼容] 与 UserRole 表同步
    level = Column(Integer, default=1)  # [兼容] 与 UserRole 表同步
    exp_points = Column(Integer, default=0)  # [兼容] 与 UserRole 表同步
    total_orders_done = Column(Integer, default=0)  # [兼容] 与 UserRole 表同步
    total_disciples = Column(Integer, default=0)
    active_disciples = Column(Integer, default=0)
    graduated_from_mentor = Column(Boolean, default=False)  # 是否已出师
    rating = Column(Float, default=5.0)  # [兼容] 与 UserRole 表同步
    rating_count = Column(Integer, default=0)  # [兼容] 与 UserRole 表同步

    # 大虾档案 - [兼容] 与 LifeStage 表同步
    provider_tagline = Column(String, default="")
    specialties = Column(JSON, default=list)
    service_categories = Column(JSON, default=list)
    hourly_rate = Column(Integer, default=0)
    available = Column(Boolean, default=True)
    intro_video_url = Column(String, default="")
    cert_badges = Column(JSON, default=list)

    # 长老档案 - [兼容] 与 LifeStage 表同步
    company = Column(String, default="")
    position = Column(String, default="")
    can_provide_internship = Column(Boolean, default=False)

    # ── 钱包（灵石体系）────────────────────────────────
    # 统一货币单位：灵石（1元 = 100灵石）
    spirit_stones = Column(Integer, default=0)       # 灵石总余额（主钱包）
    spirit_stones_frozen = Column(Integer, default=0) # 冻结灵石
    spirit_stones_earned = Column(Integer, default=0) # 累计灵石收入
    spirit_stones_dividend = Column(Integer, default=0)  # 累计灵石分红
    # [兼容] balance 保留用于与旧代码兼容，实际等同于 spirit_stones
    balance = Column(Integer, default=0)     # 分（已废弃，请使用 spirit_stones）
    frozen = Column(Integer, default=0)      # [兼容] 已废弃，请使用 spirit_stones_frozen
    total_earned = Column(Integer, default=0)  # [兼容] 已废弃，请使用 spirit_stones_earned
    total_dividend = Column(Integer, default=0)  # [兼容] 已废弃，请使用 spirit_stones_dividend

    # 推荐
    referral_code = Column(String, unique=True, nullable=True)
    total_invited = Column(Integer, default=0)  # 邀请人数
    invite_tree_depth = Column(Integer, default=0)

    # 时间
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_active_at = Column(DateTime, server_default=func.now())

    # 关系
    orders_as_seeker = relationship("Order", back_populates="seeker",
                                    foreign_keys="Order.seeker_openid")
    orders_as_provider = relationship("Order", back_populates="provider",
                                      foreign_keys="Order.provider_openid")
    services = relationship("Service", back_populates="provider")
    reviews_given = relationship("Review", back_populates="reviewer",
                                 foreign_keys="Review.reviewer_openid")
    reviews_received = relationship("Review", back_populates="reviewee",
                                    foreign_keys="Review.reviewee_openid")
    life_stages = relationship("LifeStage", back_populates="user", cascade="all, delete-orphan")
    user_roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")

    # ── 多角色支持 ─────────────────────────────
    # enabled_roles: 已解锁的角色列表 ["seeker", "provider", "elder"]
    enabled_roles = Column(JSON, default=list)   # JSON list of role names
    # current_role: 当前展示的角色
    current_role = Column(String, default="seeker")
    # 企业邮箱认证
    enterprise_email_verified = Column(Boolean, default=False)
    enterprise_email = Column(String, default="")
    enterprise_email_verified_at = Column(DateTime, nullable=True)


# ── 服务模型（六大道法）─────────────────────────────────
class Service(Base):
    __tablename__ = "services"

    id = Column(String, primary_key=True)
    provider_openid = Column(String, ForeignKey("users.openid"), nullable=False)
    dao_fa_type = Column(String, nullable=False, index=True)  # chuan_gong|mi_jing|...

    title = Column(String, nullable=False)
    description = Column(Text, default="")
    cover_image = Column(String, default="")
    tags = Column(JSON, default=list)

    target_audience = Column(String, default="all")
    subjects = Column(JSON, default=list)  # 科目/竞赛类型

    # 定价
    pricing_mode = Column(String, default="per_session")  # per_session|per_hour|per_project|free
    price = Column(Integer, default=0)  # 分
    unit = Column(String, default="次")
    min_sessions = Column(Integer, default=1)
    group_price = Column(Integer, default=0)

    # 交付
    delivery_methods = Column(JSON, default=list)
    location = Column(String, default="")
    max_group_size = Column(Integer, default=1)

    # 门槛
    provider_level_required = Column(Integer, default=0)
    seeker_school_levels = Column(JSON, default=list)

    # ── 传功授法特有字段 ──────────────────────────────
    # 服务类型：tutoring(学科辅导)|competition(竞赛陪练)|exam_prep(考前冲刺)|thesis(论文指导)
    service_type = Column(String, default="tutoring")

    # 战绩信息（竞赛服务必填）
    achievements = Column(JSON, default=list)  # [{type, level, name, year}]
    # 辅导案例
    cases = Column(JSON, default=list)  # [{title, description, result}]
    # 擅长领域
    expertise = Column(JSON, default=list)  # 擅长的具体方向
    # 教学风格
    teaching_style = Column(String, default="")  # 幽默风趣/严谨认真/耐心细致

    # ── 统计 ──────────────────────────────────────────
    rating = Column(Float, default=5.0)
    review_count = Column(Integer, default=0)
    order_count = Column(Integer, default=0)
    disciple_converted = Column(Integer, default=0)
    view_count = Column(Integer, default=0)  # 浏览数
    favorite_count = Column(Integer, default=0)  # 收藏数
    report_count = Column(Integer, default=0)  # 举报数

    status = Column(String, default="on_sale", index=True)  # on_sale|off_sale|reviewing|rejected
    reject_reason = Column(String, default="")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    provider = relationship("User", back_populates="services")


# ── 订单模型 ────────────────────────────────────────────
class Order(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True)
    dao_fa_type = Column(String, default="chuan_gong")
    order_type = Column(String, default="single")
    seeker_openid = Column(String, ForeignKey("users.openid"), nullable=False, index=True)
    provider_openid = Column(String, ForeignKey("users.openid"), nullable=False, index=True)
    group_members = Column(JSON, default=list)
    service_id = Column(String, ForeignKey("services.id"), nullable=False)

    # 服务快照
    service_title = Column(String, default="")
    service_dao_fa = Column(String, default="")
    service_cover = Column(String, default="")
    service_price = Column(Integer, default=0)
    service_unit = Column(String, default="")

    status = Column(String, default=OrderStatus.PENDING_PAYMENT, index=True)

    # 金额（单位：灵石）
    service_fee = Column(Integer, default=0)
    platform_commission = Column(Integer, default=0)
    provider_income = Column(Integer, default=0)
    mentor_bonus = Column(Integer, default=0)
    total_paid = Column(Integer, default=0)

    # 支付
    transaction_id = Column(String, default="")
    paid_at = Column(DateTime, nullable=True)
    refund_id = Column(String, default="")
    refunded_at = Column(DateTime, nullable=True)
    refund_amount = Column(Integer, default=0)
    refund_status = Column(String, default="none")

    # 退款详情
    refund_reason = Column(String, default="")
    refund_description = Column(Text, default="")
    refund_apply_at = Column(DateTime, nullable=True)
    # 取消详情
    cancelled_by = Column(String, default="")
    cancelled_reason = Column(String, default="")
    cancelled_at = Column(DateTime, nullable=True)

    # 退款详情
    refund_reason = Column(String, default="")
    refund_description = Column(Text, default="")
    refund_apply_at = Column(DateTime, nullable=True)
    # 取消详情
    cancelled_by = Column(String, default="")
    cancelled_reason = Column(String, default="")
    cancelled_at = Column(DateTime, nullable=True)

    # 课次
    sessions_total = Column(Integer, default=1)
    sessions_done = Column(Integer, default=0)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    expected_duration_hours = Column(Integer, default=24)  # 期望交付时长（小时）
    session_logs = Column(JSON, default=list)

    # 交付物
    deliverable_type = Column(String, default="")
    deliverable_urls = Column(JSON, default=list)

    timeline = Column(JSON, default=list)

    review_id = Column(String, default="")
    mentor_relationship_created = Column(Boolean, default=False)

    dispute = Column(JSON, default=dict)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    seeker = relationship("User", back_populates="orders_as_seeker",
                          foreign_keys=[seeker_openid])
    provider = relationship("User", back_populates="orders_as_provider",
                             foreign_keys=[provider_openid])


# ── 道友传承关系模型 ────────────────────────────────────
class Mentorship(Base):
    __tablename__ = "mentorships"

    id = Column(String, primary_key=True)
    mentor_openid = Column(String, ForeignKey("users.openid"), nullable=False)
    disciple_openid = Column(String, ForeignKey("users.openid"), nullable=False)

    # 导师类型：enterprise=企业导师（长老），academic=学术导师（大虾/金丹期+）
    mentor_type = Column(String, default="academic")
    # 传承方向：employment=就业方向，academic=学术方向
    mentor_direction = Column(String, default="academic")
    # 散修申请时填写的申请理由
    application_reason = Column(Text, default="")

    status = Column(String, default="active")
    origin_order_id = Column(String, nullable=True)
    started_at = Column(DateTime, server_default=func.now())
    graduated_at = Column(DateTime, nullable=True)

    milestones = Column(JSON, default=list)
    mentor_income_from_lineage = Column(Integer, default=0)
    lineage_depth = Column(Integer, default=1)

    created_at = Column(DateTime, server_default=func.now())


# ── 藏经阁资源 ──────────────────────────────────────────
class Resource(Base):
    __tablename__ = "resources"

    id = Column(String, primary_key=True)
    author_openid = Column(String, ForeignKey("users.openid"), nullable=False)
    resource_type = Column(String, default="question_set", index=True)
    title = Column(String, nullable=False)
    content = Column(Text, default="")
    cover_image = Column(String, default="")
    attachments = Column(JSON, default=list)

    tags = Column(JSON, default=list)
    subject = Column(String, default="")
    school_level = Column(String, default="")
    target_school = Column(String, default="")

    access_mode = Column(String, default="free")
    points_cost = Column(Integer, default=0)
    price_cost = Column(Integer, default=0)

    views = Column(Integer, default=0)
    unlocks = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    author_earned_points = Column(Integer, default=0)

    review_status = Column(String, default="pending")
    is_featured = Column(Boolean, default=False)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系
    comment_list = relationship("ResourceComment", back_populates="resource", cascade="all, delete-orphan")
    favorite_list = relationship("ResourceFavorite", back_populates="resource", cascade="all, delete-orphan")


class ResourceComment(Base):
    """藏经阁资源评论"""
    __tablename__ = "resource_comments"

    id = Column(String, primary_key=True)
    resource_id = Column(String, ForeignKey("resources.id"), nullable=False)
    author_openid = Column(String, ForeignKey("users.openid"), nullable=False)
    content = Column(Text, nullable=False)
    parent_id = Column(String, nullable=True)  # 回复评论的ID

    likes = Column(Integer, default=0)
    status = Column(String, default="active")  # active|deleted

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    resource = relationship("Resource", back_populates="comment_list")
    author = relationship("User")


class ResourceFavorite(Base):
    """藏经阁资源收藏"""
    __tablename__ = "resource_favorites"

    id = Column(String, primary_key=True)
    resource_id = Column(String, ForeignKey("resources.id"), nullable=False)
    user_openid = Column(String, ForeignKey("users.openid"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    resource = relationship("Resource", back_populates="favorite_list")
    user = relationship("User")


# ── 评价 ────────────────────────────────────────────────
class Review(Base):
    __tablename__ = "reviews"

    id = Column(String, primary_key=True)
    order_id = Column(String, ForeignKey("orders.id"), nullable=False, index=True)
    reviewer_openid = Column(String, ForeignKey("users.openid"), nullable=False)
    reviewee_openid = Column(String, ForeignKey("users.openid"), nullable=False)
    rating = Column(Integer, nullable=False)
    content = Column(Text, default="")
    tags = Column(JSON, default=list)  # 评价标签
    images = Column(JSON, default=list)  # 评价图片
    anonymous = Column(Boolean, default=False)  # 匿名评价

    # 服务者回复
    reply = Column(Text, default="")  # 回复内容
    reply_at = Column(DateTime, nullable=True)  # 回复时间

    # 点赞
    likes = Column(Integer, default=0)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    reviewer = relationship("User", back_populates="reviews_given",
                             foreign_keys=[reviewer_openid])
    reviewee = relationship("User", back_populates="reviews_received",
                             foreign_keys=[reviewee_openid])


# ── 分红记录模型 ────────────────────────────────────────
class DividendRecord(Base):
    __tablename__ = "dividend_records"

    id = Column(String, primary_key=True)
    user_openid = Column(String, ForeignKey("users.openid"), nullable=False)
    year = Column(Integer, nullable=False)
    pool_total = Column(Integer, nullable=False)
    user_share = Column(Integer, nullable=False)
    user_exp_ratio = Column(Float, nullable=False)
    eligible_exp_total = Column(Integer, nullable=False)
    status = Column(String, default="pending")
    claimed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", foreign_keys=[user_openid])


# ── 修为日志 ────────────────────────────────────────────
class LevelLog(Base):
    __tablename__ = "level_logs"

    id = Column(String, primary_key=True)
    user_openid = Column(String, ForeignKey("users.openid"), nullable=False)
    change_type = Column(String, nullable=False)
    points_delta = Column(Integer, nullable=False)
    balance_after = Column(Integer, nullable=False)
    level_before = Column(Integer, default=1)
    level_after = Column(Integer, default=1)
    level_upgraded = Column(Boolean, default=False)
    related_id = Column(String, default="")
    remark = Column(String, default="")

    created_at = Column(DateTime, server_default=func.now())




# ── 秘境组队模型 ────────────────────────────────────────
class Team(Base):
    """秘境组队"""
    __tablename__ = "teams"

    id = Column(String, primary_key=True)
    creator_openid = Column(String, ForeignKey("users.openid"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    category = Column(String, default="mi_jing")  # mi_jing|competition|project|study

    # 组队信息
    max_members = Column(Integer, default=5)
    current_members = Column(Integer, default=1)
    target_date = Column(DateTime, nullable=True)  # 目标日期
    deadline = Column(DateTime, nullable=True)  # 招募截止日期

    # 标签
    tags = Column(JSON, default=list)

    # 状态
    status = Column(String, default="recruiting")  # recruiting|full|closed|in_progress|completed

    # 任务列表
    team_tasks = Column(JSON, default=list)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    creator = relationship("User", foreign_keys=[creator_openid])
    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")


class TeamMember(Base):
    """组队成员"""
    __tablename__ = "team_members"

    id = Column(String, primary_key=True)
    team_id = Column(String, ForeignKey("teams.id"), nullable=False)
    openid = Column(String, ForeignKey("users.openid"), nullable=False)
    role = Column(String, default="member")  # leader|member
    status = Column(String, default="joined")  # joined|left|kicked
    joined_at = Column(DateTime, server_default=func.now())
    left_at = Column(DateTime, nullable=True)

    team = relationship("Team", back_populates="members")
    user = relationship("User")


# ── 下山历练-就业资源 ──────────────────────────────────
class Opportunity(Base):
    """
    下山历练-就业资源（实习/内推/职位）
    用于服务者（道修/长老）发布就业机会
    """
    __tablename__ = "opportunities"

    id = Column(String, primary_key=True)
    # 基础信息
    openid = Column(String, ForeignKey("users.openid"), nullable=False)
    title = Column(String, nullable=False)  # 资源标题
    opportunity_type = Column(String, nullable=False)  # internship|referral|job

    # 企业/机构信息
    company_name = Column(String, default="")  # 公司/机构名称
    company_industry = Column(String, default="")  # 行业
    company_size = Column(String, default="")  # 公司规模
    company_logo = Column(String, default="")  # 公司Logo

    # 职位信息
    position = Column(String, default="")  # 职位名称
    position_type = Column(String, default="")  # 职位类型（全职/兼职/实习）
    work_location = Column(String, default="")  # 工作地点
    work_mode = Column(String, default="")  # 工作模式（onsite/remote/hybrid）

    # 薪资待遇
    salary_range = Column(String, default="")  # 薪资范围（如"150-300/天"、"20-35K/月"）
    salary_hidden = Column(Boolean, default=False)  # 是否隐藏薪资

    # 详细信息
    description = Column(Text, default="")  # 职位描述
    requirements = Column(Text, default="")  # 任职要求
    benefits = Column(Text, default="")  # 福利待遇

    # 申请信息
    deadline = Column(DateTime, nullable=True)  # 截止日期
    apply_url = Column(String, default="")  # 外部申请链接（如牛客、Boss直聘）
    contact_wx = Column(String, default="")  # 联系方式（微信）

    # 标签
    tags = Column(JSON, default=list)  # 如["互联网","产品","实习"]

    # 统计
    view_count = Column(Integer, default=0)
    favorite_count = Column(Integer, default=0)
    apply_count = Column(Integer, default=0)

    # 信任认证要求
    require_cert = Column(Boolean, default=True)  # 是否需要实名认证
    require_school = Column(Boolean, default=False)  # 是否需要校园认证
    require_level = Column(Integer, default=0)  # 最低等级要求

    # 状态
    status = Column(String, default="active")  # active|closed|expired
    review_status = Column(String, default="approved")  # approved|pending|rejected
    reject_reason = Column(String, default="")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", foreign_keys=[openid])
    applications = relationship("OpportunityApplication", back_populates="opportunity", cascade="all, delete-orphan")
    favorites = relationship("OpportunityFavorite", back_populates="opportunity", cascade="all, delete-orphan")


class OpportunityApplication(Base):
    """
    就业资源申请记录
    用于需求者申请就业机会
    """
    __tablename__ = "opportunity_applications"

    id = Column(String, primary_key=True)
    opportunity_id = Column(String, ForeignKey("opportunities.id"), nullable=False)
    applicant_openid = Column(String, ForeignKey("users.openid"), nullable=False)

    # 申请信息
    message = Column(Text, default="")  # 申请留言/自我介绍
    resume_url = Column(String, default="")  # 简历URL

    # 状态
    status = Column(String, default="pending")  # pending|accepted|rejected|withdrawn
    result_message = Column(String, default="")  # 结果说明

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    opportunity = relationship("Opportunity", back_populates="applications")
    applicant = relationship("User", foreign_keys=[applicant_openid])


class OpportunityFavorite(Base):
    """
    就业资源收藏
    """
    __tablename__ = "opportunity_favorites"

    id = Column(String, primary_key=True)
    opportunity_id = Column(String, ForeignKey("opportunities.id"), nullable=False)
    user_openid = Column(String, ForeignKey("users.openid"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    opportunity = relationship("Opportunity", back_populates="favorites")
    user = relationship("User")


# ── 仲裁/纠纷 ──────────────────────────────────────────
class Dispute(Base):
    """仲裁/纠纷"""
    __tablename__ = "disputes"

    id = Column(String, primary_key=True)
    order_id = Column(String, ForeignKey("orders.id"), nullable=False)

    # 申请人信息
    applicant_openid = Column(String, ForeignKey("users.openid"), nullable=False)
    applicant_role = Column(String, default="seeker")  # seeker|provider

    # 纠纷详情
    dispute_type = Column(String, nullable=False)  # not_on_time|quality_issue|attendance_issue|refund_request|other
    description = Column(Text, nullable=False)
    evidence_images = Column(JSON, default=list)  # 证据图片URL列表
    expected_action = Column(String, nullable=False)  # full_refund|partial_refund|other

    # 状态
    status = Column(String, default="pending")  # pending|reviewing|resolved|cancelled
    resolution = Column(String, nullable=True)  # 仲裁结果
    admin_remark = Column(Text, nullable=True)  # 管理员备注

    # 补充证据
    evidence_extra = Column(JSON, default=list)  # 后续补充的证据

    # 时间
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    resolved_at = Column(DateTime, nullable=True)

    # 关系
    order = relationship("Order")
    applicant = relationship("User", foreign_keys=[applicant_openid])


# ── 人生阶段模型 ───────────────────────────────────────
class LifeStage(Base):
    """用户的人生阶段 - 支持用户在不同人生阶段扮演不同角色"""
    __tablename__ = "life_stages"

    id = Column(String, primary_key=True)
    user_openid = Column(String, ForeignKey("users.openid"), nullable=False, index=True)

    # 阶段类型
    stage_type = Column(String, nullable=False)  # high_school|college|working
    stage_name = Column(String, default="")     # 如"高中三年"、"大一新生"、"职场新人"

    # 该阶段的角色（散修/大虾/长老）
    role = Column(String, default="seeker")

    # 状态
    is_current = Column(Boolean, default=True)  # 是否为当前活跃阶段
    status = Column(String, default="active")   # active|inactive|archived

    # ── 高中信息 ────────────────────────────────
    high_school_name = Column(String, default="")
    high_school_city = Column(String, default="")
    grade = Column(String, default="")  # 高一/高二/高三

    # ── 大学信息 ────────────────────────────────
    school = Column(String, default="")
    school_level = Column(String, default="")   # 本科/硕士/博士
    major = Column(String, default="")
    graduation_year = Column(Integer, nullable=True)

    # ── 就业信息 ────────────────────────────────
    company = Column(String, default="")
    position = Column(String, default="")
    industry = Column(String, default="")

    # ── 通用信息 ────────────────────────────────
    city = Column(String, default="")          # 所在城市
    start_year = Column(Integer, nullable=True)
    end_year = Column(Integer, nullable=True)

    # ── 该阶段的统计数据 ─────────────────────────
    orders_count = Column(Integer, default=0)
    services_count = Column(Integer, default=0)
    total_earned = Column(Integer, default=0)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="life_stages", foreign_keys=[user_openid])


# ── 用户角色模型 ──────────────────────────────────────────
class UserRole(Base):
    """
    用户角色表 - 支持多角色共存，每个角色独立等级/经验值
    散修(seeker) 默认解锁，其他角色按条件解锁
    """
    __tablename__ = "user_roles"

    id = Column(String, primary_key=True)
    user_openid = Column(String, ForeignKey("users.openid"), nullable=False, index=True)
    role = Column(String, nullable=False)  # seeker|provider|elder

    # 状态
    status = Column(String, default=RoleStatus.ENABLED)  # locked|enabled|pending

    # 该角色的修为（独立于其他角色）
    level = Column(Integer, default=1)
    exp_points = Column(Integer, default=0)

    # 角色特定数据
    verified = Column(Boolean, default=False)           # 是否已认证
    verified_at = Column(DateTime, nullable=True)
    total_orders_done = Column(Integer, default=0)      # 该角色完成的订单数
    total_services_published = Column(Integer, default=0) # 该角色发布的服务数
    rating = Column(Float, default=5.0)
    rating_count = Column(Integer, default=0)

    # 解锁条件记录
    unlock_condition = Column(String, default="")        # 触发解锁的条件描述
    unlocked_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="user_roles")


class ContentReport(Base):
    """用户举报记录，覆盖服务、资源、评价和评论。"""
    __tablename__ = "content_reports"

    id = Column(String, primary_key=True)
    reporter_openid = Column(String, ForeignKey("users.openid"), nullable=False, index=True)
    target_type = Column(String, nullable=False, index=True)
    target_id = Column(String, nullable=False, index=True)
    reason = Column(String, nullable=False)
    description = Column(Text, default="")
    status = Column(String, default="pending", index=True)
    handled_by = Column(String, default="")
    handled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


# ── 数据库初始化 ────────────────────────────────────────
def init_db():
    settings = get_settings()
    database_url = settings.database_url.replace(
        "postgresql+asyncpg://",
        "postgresql://",
    )
    engine_options = {
        "echo": settings.debug,
        "pool_pre_ping": True,
    }
    if database_url.startswith("mysql"):
        engine_options["pool_recycle"] = 280

    engine = create_engine(
        database_url,
        **engine_options,
    )
    Base.metadata.create_all(engine)
    return engine
