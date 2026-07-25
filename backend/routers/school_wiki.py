"""
高校百科 AI 问答路由
GET  /api/v1/school-wiki              高校列表
GET  /api/v1/school-wiki/search        搜索高校
POST /api/v1/school-wiki/ask           AI 问答
GET  /api/v1/school-wiki/history       问答历史
GET  /api/v1/school-wiki/schools       高校基础信息
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from dependencies import get_db, get_current_user, get_current_user_optional
from models import User
from services.school_wiki_service import (
    search_school,
    search_school_resources,
    generate_qa_response,
    save_qa_history,
    get_qa_history,
    SCHOOL_PROFILES,
)

router = APIRouter(prefix="/api/v1/school-wiki", tags=["高校百科"])


class AskRequest(BaseModel):
    """问答请求"""
    question: str
    school_name: str = ""


@router.get("/schools")
def school_list():
    """获取支持的高校列表"""
    schools = []
    for name, info in SCHOOL_PROFILES.items():
        schools.append({
            "name": name,
            "alias": info.get("alias", []),
            "level": info.get("level", ""),
            "location": info.get("location", ""),
            "type": info.get("type", ""),
        })
    return {"code": 0, "data": {"schools": schools, "total": len(schools)}}


@router.get("")
def school_wiki_index():
    """高校百科首页列表，兼容前端直接访问 /school-wiki"""
    return school_list()


@router.get("/search")
def search_school_api(
    keyword: str = Query(..., description="搜索关键词"),
    db: Session = Depends(get_db),
):
    """搜索高校"""
    result = search_school(keyword)

    if not result:
        return {"code": 0, "data": {"found": False, "suggestions": list(SCHOOL_PROFILES.keys())[:5]}}

    # 获取相关资源
    resources = search_school_resources(db, result["name"])

    return {
        "code": 0,
        "data": {
            "found": True,
            "school": result,
            "resources": resources,
        },
    }


@router.post("/ask")
def ask_question(
    payload: AskRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    """
    AI 问答
    支持关于高校的各类问题咨询
    """
    user_openid = current_user.openid if current_user else ""

    # 搜索高校信息
    school_keyword = payload.school_name or payload.question
    school_info = search_school(school_keyword)

    # 搜索相关资源
    resources = []
    if school_info:
        resources = search_school_resources(db, school_info["name"])

    # 生成回答
    result = generate_qa_response(payload.question, school_info, resources)

    # 保存问答历史
    if user_openid:
        save_qa_history(
            db, user_openid,
            school_name=school_info["name"] if school_info else "",
            question=payload.question,
            answer=result["answer"],
            sources=result.get("sources", []),
        )

    return {
        "code": 0,
        "data": result,
    }


@router.get("/history")
def qa_history(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    limit: int = Query(20, ge=1, le=50),
):
    """获取我的问答历史"""
    records = get_qa_history(db, current_user.openid, limit)
    return {"code": 0, "data": {"records": records, "total": len(records)}}


@router.get("/detail/{school_name}")
def school_detail(
    school_name: str,
    db: Session = Depends(get_db),
):
    """获取高校详细信息"""
    info = search_school(school_name)

    if not info:
        return {"code": 404, "message": "未找到该高校信息"}

    # 获取相关资源
    resources = search_school_resources(db, info["name"])

    return {
        "code": 0,
        "data": {
            "school": info,
            "resources": resources,
            "wiki_count": len(resources),
        },
    }
