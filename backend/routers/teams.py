"""
联袂问道路由
多人拼团、课题组队、竞赛组队功能
"""
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, Field
from utils.db import get_db
from models import Team, TeamMember, User
from dependencies import get_current_user
from utils.content_guard import guard_user_content
from services.level_service import get_level_info

router = APIRouter(prefix="/api/v1/teams", tags=["联袂问道"])


# ── 请求/响应模型 ────────────────────────────────────────

class TeamCreate(BaseModel):
    title: str = Field(..., max_length=50)
    description: str = Field(default="", max_length=1000)
    category: str = "mi_jing"
    max_members: int = Field(default=5, ge=2, le=50)
    target_date: Optional[str] = None
    deadline: Optional[str] = None
    tags: list[str] = Field(default_factory=list, max_length=10)


class TeamUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[list[str]] = None
    target_date: Optional[str] = None
    deadline: Optional[str] = None
    status: Optional[str] = None


# ── API 端点 ─────────────────────────────────────────────

@router.get("/categories")
def list_categories():
    """组队分类列表"""
    return {
        "categories": [
            # 联袂问道（通用组队）
            {"id": "mi_jing", "name": "🔬 课题/科研", "icon": "🔬", "desc": "科研项目、课题组队", "group": "问道"},
            {"id": "competition", "name": "🏆 竞赛组队", "icon": "🏆", "desc": "建模、编程、创业竞赛", "group": "问道"},
            {"id": "project", "name": "💡 项目合作", "icon": "💡", "desc": "创业项目、产品开发", "group": "问道"},
            {"id": "study", "name": "📚 学习小组", "icon": "📚", "desc": "考研、考证、期末冲刺", "group": "问道"},
            # 下山历练（就业相关）
            {"id": "internship", "name": "🏢 寻觅道场", "icon": "🏢", "desc": "寻找实习机会", "group": "历练"},
            {"id": "referral", "name": "🎯 求取推荐", "icon": "🎯", "desc": "寻求内推机会", "group": "历练"},
            {"id": "job", "name": "💼 问道职涯", "icon": "💼", "desc": "求职、就职机会", "group": "历练"},
            {"id": "job_resource", "name": "🌟 布施机缘", "icon": "🌟", "desc": "分享实习/内推/职位", "group": "历练"},
        ]
    }


@router.get("")
def list_teams(
    category: Optional[str] = Query(None),
    status: Optional[str] = Query("recruiting"),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """组队列表"""
    query = db.query(Team)

    # status 和 category 是独立的过滤条件，可以同时生效
    if status:
        query = query.filter(Team.status == status)
    if category:
        query = query.filter(Team.category == category)
    if search:
        query = query.filter(
            Team.title.contains(search) | Team.description.contains(search)
        )

    query = query.order_by(Team.created_at.desc())

    total = query.count()
    teams = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "teams": [_team_to_dict(t, db) for t in teams],
    }


@router.get("/my")
def get_my_teams(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """我的组队（创建的 + 加入的）"""
    # 我创建的
    created = db.query(Team).filter(Team.creator_openid == user.openid).all()
    # 我加入的
    memberships = db.query(TeamMember).filter(
        TeamMember.openid == user.openid,
        TeamMember.status == "joined"
    ).all()
    joined_ids = [m.team_id for m in memberships]
    joined = db.query(Team).filter(Team.id.in_(joined_ids)).all() if joined_ids else []

    return {
        "created": [_team_to_dict(t, db) for t in created],
        "joined": [_team_to_dict(t, db) for t in joined],
    }


@router.get("/{team_id}")
def get_team(team_id: str, db: Session = Depends(get_db)):
    """组队详情"""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="组队不存在")

    result = _team_to_dict(team, db)
    # 追加成员详情
    members = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.status == "joined"
    ).all()
    result["members"] = [_member_to_dict(m, db) for m in members]
    return result


@router.post("")
def create_team(
    body: TeamCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建组队"""
    guard_user_content(user.openid, body.model_dump())
    team_id = f"TM{uuid.uuid4().hex[:10].upper()}"

    team = Team(
        id=team_id,
        creator_openid=user.openid,
        title=body.title,
        description=body.description,
        category=body.category,
        max_members=body.max_members,
        tags=body.tags,
        target_date=datetime.fromisoformat(body.target_date) if body.target_date else None,
        deadline=datetime.fromisoformat(body.deadline) if body.deadline else None,
        current_members=1,
        status="recruiting",
    )
    db.add(team)

    # 创建者自动加入
    member = TeamMember(
        id=f"TMMB{int(datetime.now().timestamp() * 1000) % 1000000:06d}",
        team_id=team_id,
        openid=user.openid,
        role="leader",
        status="joined",
    )
    db.add(member)
    db.commit()

    return {"id": team_id, "success": True}


@router.put("/{team_id}")
def update_team(
    team_id: str,
    body: TeamUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新组队（仅创建者可操作）"""
    guard_user_content(user.openid, body.model_dump(exclude_unset=True))
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="组队不存在")
    if team.creator_openid != user.openid:
        raise HTTPException(status_code=403, detail="仅创建者可修改")

    if body.title is not None:
        team.title = body.title
    if body.description is not None:
        team.description = body.description
    if body.tags is not None:
        team.tags = body.tags
    if body.target_date is not None:
        team.target_date = datetime.fromisoformat(body.target_date)
    if body.deadline is not None:
        team.deadline = datetime.fromisoformat(body.deadline)
    if body.status is not None:
        team.status = body.status

    db.commit()
    return {"success": True}


@router.post("/{team_id}/join")
def join_team(
    team_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """加入组队"""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="组队不存在")
    if team.status != "recruiting":
        raise HTTPException(status_code=400, detail="该组队不在招募中")
    if team.current_members >= team.max_members:
        raise HTTPException(status_code=400, detail="组队已满员")

    # 检查是否已加入
    existing = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.openid == user.openid,
        TeamMember.status == "joined"
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="您已加入该组队")

    # 添加成员
    member = TeamMember(
        id=f"TMMB{int(datetime.now().timestamp() * 1000) % 1000000:06d}",
        team_id=team_id,
        openid=user.openid,
        role="member",
        status="joined",
    )
    db.add(member)
    team.current_members += 1

    # 满员自动关闭招募
    if team.current_members >= team.max_members:
        team.status = "full"

    db.commit()
    return {"success": True, "current_members": team.current_members}


@router.post("/{team_id}/leave")
def leave_team(
    team_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """离开组队"""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="组队不存在")

    member = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.openid == user.openid,
        TeamMember.status == "joined"
    ).first()
    if not member:
        raise HTTPException(status_code=400, detail="您未加入该组队")

    # 创建者不能直接离开
    if team.creator_openid == user.openid:
        raise HTTPException(status_code=400, detail="创建者需先转让组长或解散组队")

    member.status = "left"
    member.left_at = datetime.now()
    team.current_members -= 1
    team.status = "recruiting"  # 重新开放招募

    db.commit()
    return {"success": True, "current_members": team.current_members}


@router.delete("/{team_id}")
def delete_team(
    team_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """解散组队（仅创建者可操作）"""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="组队不存在")
    if team.creator_openid != user.openid:
        raise HTTPException(status_code=403, detail="仅创建者可解散")

    team.status = "closed"
    db.commit()
    return {"success": True}


# ── 辅助函数 ─────────────────────────────────────────────

def _team_to_dict(team: Team, db: Session) -> dict:
    """Team 模型转字典"""
    creator = db.query(User).filter(User.openid == team.creator_openid).first()
    creator_info = {}
    if creator:
        level_info = get_level_info(creator.level)
        creator_info = {
            "openid": creator.openid,
            "nickname": creator.nickname,
            "avatar_url": creator.avatar_url,
            "school": creator.school,
            "level": creator.level,
            "level_name": level_info.get("name", ""),
            "level_icon": level_info.get("icon", ""),
        }

    return {
        "id": team.id,
        "title": team.title,
        "description": team.description,
        "category": team.category,
        "max_members": team.max_members,
        "current_members": team.current_members,
        "tags": team.tags or [],
        "status": team.status,
        "target_date": team.target_date.isoformat() if team.target_date else None,
        "deadline": team.deadline.isoformat() if team.deadline else None,
        "creator": creator_info,
        "created_at": team.created_at.isoformat() if team.created_at else "",
    }


def _member_to_dict(member: TeamMember, db: Session) -> dict:
    """TeamMember 模型转字典"""
    user = db.query(User).filter(User.openid == member.openid).first()
    level_info = get_level_info(user.level) if user else {}
    return {
        "openid": member.openid,
        "nickname": user.nickname if user else "未知",
        "avatar_url": user.avatar_url if user else "",
        "role": member.role,
        "joined_at": member.joined_at.isoformat() if member.joined_at else "",
        "level": user.level if user else 1,
        "level_name": level_info.get("name", ""),
        "level_icon": level_info.get("icon", ""),
        "school": user.school if user else "",
    }


# ==================== 组队增强接口 ====================

class TransferLeaderRequest(BaseModel):
    new_leader_openid: str


class TaskAssignRequest(BaseModel):
    member_openid: str
    task_title: str
    task_description: str = ""
    deadline: Optional[str] = None


@router.post("/{team_id}/transfer-leader")
def transfer_leader(
    team_id: str,
    body: TransferLeaderRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    转让组长
    - 仅当前组长可操作
    - 新组长必须是已有成员
    """
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="组队不存在")

    if team.creator_openid != user.openid:
        raise HTTPException(status_code=403, detail="仅组长可转让")

    # 检查新组长是否是成员
    new_leader = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.openid == body.new_leader_openid,
        TeamMember.status == "joined"
    ).first()
    if not new_leader:
        raise HTTPException(status_code=400, detail="新组长必须是组队成员")

    # 转让
    team.creator_openid = body.new_leader_openid
    new_leader.role = "leader"

    # 原组长变为普通成员
    old_leader = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.openid == user.openid
    ).first()
    if old_leader:
        old_leader.role = "member"

    db.commit()
    return {"success": True, "message": "组长已转让"}


@router.post("/{team_id}/invite")
def invite_member(
    team_id: str,
    invitee_openid: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    邀请成员
    - 仅组长可操作
    - TODO: 发送通知
    """
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="组队不存在")

    if team.creator_openid != user.openid:
        raise HTTPException(status_code=403, detail="仅组长可邀请")

    if team.current_members >= team.max_members:
        raise HTTPException(status_code=400, detail="组队已满员")

    # 检查是否已是成员
    existing = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.openid == invitee_openid
    ).first()
    if existing and existing.status == "joined":
        raise HTTPException(status_code=400, detail="该用户已是成员")

    # TODO: 创建邀请记录
    return {
        "success": True,
        "message": "邀请已发送",
        "invitee_openid": invitee_openid
    }


@router.get("/{team_id}/tasks")
def get_team_tasks(
    team_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取组队任务列表
    """
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="组队不存在")

    # 检查权限
    is_member = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.openid == user.openid,
        TeamMember.status == "joined"
    ).first()
    if not is_member and team.creator_openid != user.openid:
        raise HTTPException(status_code=403, detail="只有组队成员可查看任务")

    # TODO: 从任务表获取任务（当前返回空）
    tasks = team.team_tasks or []

    return {
        "team_id": team_id,
        "tasks": tasks,
        "my_tasks": [t for t in tasks if t.get("assignee") == user.openid]
    }


@router.post("/{team_id}/tasks")
def assign_task(
    team_id: str,
    body: TaskAssignRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    分配任务
    - 仅组长可操作
    """
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="组队不存在")

    if team.creator_openid != user.openid:
        raise HTTPException(status_code=403, detail="仅组长可分配任务")

    # 检查被分配人是否是成员
    assignee = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.openid == body.member_openid,
        TeamMember.status == "joined"
    ).first()
    if not assignee:
        raise HTTPException(status_code=400, detail="被分配人必须是组队成员")

    # TODO: 创建任务记录
    task = {
        "id": f"TASK{int(datetime.now().timestamp() * 1000) % 100000:05d}",
        "title": body.task_title,
        "description": body.task_description,
        "assignee": body.member_openid,
        "assigner": user.openid,
        "status": "pending",
        "deadline": body.deadline,
        "created_at": datetime.now().isoformat(),
    }

    # 存储到组队记录（临时方案）
    if not team.team_tasks:
        team.team_tasks = []
    team.team_tasks.append(task)

    db.commit()
    return {"success": True, "task": task}


@router.get("/hot")
def get_hot_teams(
    category: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """
    获取热门组队推荐
    """
    query = db.query(Team).filter(Team.status == "recruiting")

    if category:
        query = query.filter(Team.category == category)

    teams = query.order_by(
        Team.current_members.desc(),
        Team.created_at.desc()
    ).limit(limit).all()

    return {
        "category": category or "all",
        "teams": [_team_to_dict(t, db) for t in teams]
    }


@router.get("/stats/overview")
def get_teams_overview(
    db: Session = Depends(get_db),
):
    """
    获取组队总览统计
    """
    from sqlalchemy import func

    total_teams = db.query(Team).count()
    recruiting = db.query(Team).filter(Team.status == "recruiting").count()
    total_members = db.query(func.sum(Team.current_members)).scalar() or 0

    # 各分类统计
    categories = ["mi_jing", "competition", "project", "study"]
    category_stats = {}

    for cat in categories:
        count = db.query(Team).filter(Team.category == cat).count()
        members = db.query(func.sum(Team.current_members)).filter(
            Team.category == cat
        ).scalar() or 0
        category_stats[cat] = {
            "team_count": count,
            "member_count": int(members),
        }

    return {
        "total_teams": total_teams,
        "recruiting_teams": recruiting,
        "total_members": int(total_members),
        "category_stats": category_stats,
    }
