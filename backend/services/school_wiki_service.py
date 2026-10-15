"""高校百科资料查询服务。仅提供静态资料和已审核资源，不生成问答。"""
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc


SCHOOL_PROFILES = {
    "复旦大学": {
        "alias": ["复旦", "FDU", "复附"],
        "level": "985/211",
        "location": "上海",
        "type": "综合类",
        "qs_rank": "前50",
        "majors": ["新闻传播", "经济学", "管理学", "计算机", "医学"],
        "campus": ["邯郸校区", "枫林校区", "江湾校区", "张江校区"],
        "spirit": "博学而笃志，切问而近思",
        "features": ["通识教育", "书院制度", "第二学位"],
    },
    "上海交通大学": {
        "alias": ["上交", "上交大", "SJTU", "交大"],
        "level": "985/211",
        "location": "上海",
        "type": "理工类",
        "qs_rank": "前100",
        "majors": ["船舶与海洋工程", "机械工程", "电子信息", "材料科学", "计算机"],
        "campus": ["闵行校区", "徐汇校区", "法华校区", "七宝校区"],
        "spirit": "尚德、求实、求是、创新",
        "features": ["工科实力强", "创业氛围浓", "国际化程度高"],
    },
    "清华大学": {
        "alias": ["清华", "THU", "水木"],
        "level": "985/211",
        "location": "北京",
        "type": "综合类",
        "qs_rank": "前20",
        "majors": ["计算机", "电子工程", "自动化", "机械工程", "建筑学", "经济管理"],
        "campus": ["紫荆校区", "华北大学"],
        "spirit": "自强不息，厚德载物",
        "features": ["顶尖工科", "创业孵化", "全球视野"],
    },
    "北京大学": {
        "alias": ["北大", "PKU", "燕园"],
        "level": "985/211",
        "location": "北京",
        "type": "综合类",
        "qs_rank": "前20",
        "majors": ["中文", "历史", "哲学", "经济学", "法学", "数学", "物理"],
        "campus": ["燕园校区", "医学部"],
        "spirit": "爱国、进步、民主、科学",
        "features": ["文理基础学科", "元培学院", "双学位"],
    },
    "浙江大学": {
        "alias": ["浙大", "ZJU", "求是"],
        "level": "985/211",
        "location": "杭州",
        "type": "综合类",
        "qs_rank": "前100",
        "majors": ["计算机", "控制科学", "光学工程", "材料科学", "农学"],
        "campus": ["紫金港校区", "玉泉校区", "西溪校区", "华家池校区", "之江校区"],
        "spirit": "求是创新",
        "features": ["学科齐全", "创业率高", "海宁国际校区"],
    },
}


def search_school(keyword: str) -> Optional[dict]:
    """搜索高校信息"""
    keyword = keyword.strip()

    # 先匹配高校名称
    for school, info in SCHOOL_PROFILES.items():
        if school in keyword or keyword in school:
            return {"name": school, **info}
        # 匹配别名
        for alias in info.get("alias", []):
            if alias in keyword or keyword in alias:
                return {"name": school, **info}

    return None


def search_school_resources(db: Session, school_name: str, limit: int = 5) -> list:
    """搜索高校相关的宗门图志"""
    from models import Resource
    pattern = f"%{school_name}%"
    resources = db.query(Resource).filter(
        Resource.resource_type == "school_guide",
        Resource.review_status == "approved",
        or_(
            Resource.title.ilike(pattern),
            Resource.target_school.ilike(pattern),
            Resource.content.ilike(pattern),
        ),
    ).order_by(desc(Resource.likes), desc(Resource.views)).limit(limit).all()

    return [
        {
            "id": r.id,
            "title": r.title,
            "target_school": r.target_school,
            "content_preview": r.content[:200] if r.content else "",
            "views": r.views,
            "likes": r.likes,
            "author_nickname": _get_author_nickname(db, r.author_openid),
        }
        for r in resources
    ]


def _get_author_nickname(db: Session, openid: str) -> str:
    """获取作者昵称"""
    from models import User
    user = db.query(User).filter(User.openid == openid).first()
    return user.nickname if user else "匿名大虾"
