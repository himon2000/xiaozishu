"""
高校百科资料查询路由
GET  /api/v1/school-wiki              高校列表
GET  /api/v1/school-wiki/search        搜索高校
GET  /api/v1/school-wiki/schools       高校基础信息
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from dependencies import get_db
from services.school_wiki_service import (
    search_school,
    search_school_resources,
    SCHOOL_PROFILES,
)

router = APIRouter(prefix="/api/v1/school-wiki", tags=["高校百科"])


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
