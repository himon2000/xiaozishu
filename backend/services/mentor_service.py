"""
道友传承服务
《驯龙阁》企业导师+学术导师双轨永续机制核心
"""
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from models import Mentorship, User
from services.level_service import add_exp

MENTOR_BONUS_RATIO = 0.05  # 导师从被传承者订单中额外获得 5%


def check_existing_mentorship(
    db: Session,
    disciple_openid: str,
    provider_openid: str,
    mentor_type: str = "academic",
) -> Mentorship | None:
    """检查是否存在活跃的同道友传承关系"""
    return db.query(Mentorship).filter(
        Mentorship.disciple_openid == disciple_openid,
        Mentorship.mentor_openid == provider_openid,
        Mentorship.status == "active",
        Mentorship.mentor_type == mentor_type,
    ).first()


def count_active_mentorship_by_type(db: Session, disciple_openid: str, mentor_type: str) -> int:
    """统计散修当前持有的某类型导师数量（上限1名）"""
    return db.query(Mentorship).filter(
        Mentorship.disciple_openid == disciple_openid,
        Mentorship.mentor_type == mentor_type,
        Mentorship.status == "active",
    ).count()


def create_mentorship(
    db: Session,
    mentor: User,
    disciple: User,
    origin_order_id: str = "",
    mentor_type: str = "academic",
    mentor_direction: str = "academic",
    application_reason: str = "",
) -> Mentorship:
    """建立道友传承关系"""
    # 检查是否已有关系
    existing = check_existing_mentorship(db, disciple.openid, mentor.openid, mentor_type)
    if existing:
        return existing

    mentorship = Mentorship(
        id=f"MTR{uuid.uuid4().hex[:10].upper()}",
        mentor_openid=mentor.openid,
        disciple_openid=disciple.openid,
        mentor_type=mentor_type,
        mentor_direction=mentor_direction,
        application_reason=application_reason,
        status="active",
        origin_order_id=origin_order_id,
        lineage_depth=1,
    )
    db.add(mentorship)

    # 更新导师的活跃被传承者数
    mentor.active_disciples += 1
    db.commit()
    return mentorship


def dissolve_mentorship(db: Session, mentorship_id: str) -> bool:
    """解除道友传承关系（出师或主动退出）"""
    m = db.query(Mentorship).filter(Mentorship.id == mentorship_id).first()
    if not m or m.status != "active":
        return False
    m.status = "dissolved"

    # 更新导师计数
    mentor = db.query(User).filter(User.openid == m.mentor_openid).first()
    if mentor and mentor.active_disciples > 0:
        mentor.active_disciples -= 1
    db.commit()
    return True


def graduate_mentorship(
    db: Session,
    mentorship: Mentorship,
    event: str = "disciple_graduated",
    remark: str = "",
) -> dict:
    """
    被传承者达成里程碑，触发传承气运奖励
    event: disciple_graduated | exam_passed | offer_received | next_mentor_created
    """
    milestone_exp_map = {
        "disciple_graduated": 50,   # 升学成功
        "exam_passed": 20,           # 重要考试通过
        "offer_received": 30,         # 拿到Offer
        "next_mentor_created": 20,   # 被传承者也成为导师
    }
    exp_reward = milestone_exp_map.get(event, 10)

    mentor = db.query(User).filter(User.openid == mentorship.mentor_openid).first()
    if not mentor:
        return {"error": "导师不存在"}

    # 追加里程碑记录
    milestones = mentorship.milestones or []
    milestones.append({
        "event": event,
        "description": remark,
        "recorded_at": datetime.now().isoformat(),
        "exp_awarded_to_mentor": exp_reward,
    })
    mentorship.milestones = milestones

    # 给导师加修为
    result = add_exp(db, mentor, "earn_disciple_graduate",
                     related_id=mentorship.id,
                     remark=f"被传承者达成里程碑: {remark}")

    # 如果是出师，更新状态
    if event == "disciple_graduated":
        mentorship.status = "completed"
        mentorship.graduated_at = datetime.now()
        mentor.active_disciples = max(0, mentor.active_disciples - 1)
        mentor.total_disciples += 1

    db.commit()
    return {
        "milestone_added": True,
        "exp_reward": exp_reward,
        "mentor_new_level": result.get("level_after"),
        "mentorship_status": mentorship.status,
    }


def get_mentor_bonus(order_service_fee: int, has_mentorship: bool) -> int:
    """计算道友传承关系带来的额外奖金"""
    if not has_mentorship:
        return 0
    return int(order_service_fee * MENTOR_BONUS_RATIO)


def build_lineage_tree(db: Session, user_openid: str, depth: int = 3) -> dict:
    """
    构建传承树数据（用于前端可视化）
    向上追溯导师，向下追溯被传承者
    """
    result = {"mentors": [], "disciples": []}

    # 向上找导师
    mship = db.query(Mentorship).filter(
        Mentorship.disciple_openid == user_openid,
        Mentorship.status == "active"
    ).first()
    if mship:
        mentor = db.query(User).filter(User.openid == mship.mentor_openid).first()
        if mentor:
            node = _user_to_node(mentor)
            node["mentor_type"] = getattr(mship, "mentor_type", "academic")
            node["mentor_direction"] = getattr(mship, "mentor_direction", "academic")
            result["mentors"].append(node)

    # 向下找被传承者
    disciples = db.query(Mentorship).filter(
        Mentorship.mentor_openid == user_openid,
        Mentorship.status == "active"
    ).all()
    for d in disciples:
        disciple = db.query(User).filter(User.openid == d.disciple_openid).first()
        if disciple:
            node = _user_to_node(disciple)
            node["milestones"] = d.milestones or []
            node["started_at"] = d.started_at.isoformat() if d.started_at else ""
            node["mentor_type"] = getattr(d, "mentor_type", "academic")
            result["disciples"].append(node)

    return result


def _user_to_node(user: User) -> dict:
    from services.level_service import get_level_info
    info = get_level_info(user.level)
    return {
        "openid": user.openid,
        "nickname": user.nickname,
        "avatar_url": user.avatar_url,
        "level": user.level,
        "level_name": info["name"],
        "level_color": info["color"],
        "level_icon": info["icon"],
        "school": user.school,
        "specialties": user.specialties or [],
    }
