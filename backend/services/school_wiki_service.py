"""
高校百科 AI 问答服务
《驯龙阁》宗门图志智能助手
"""
import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, text


# 高校基础数据


# ═══════════════════════════════════════════════════════════
# 高校基础数据
# ═══════════════════════════════════════════════════════════

# 高校信息模板（实际项目中可从数据库或外部 API 读取）
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


# ═══════════════════════════════════════════════════════════
# AI 问答服务
# ═══════════════════════════════════════════════════════════

class QAHistory:
    """问答历史数据结构（不使用 ORM）"""
    def __init__(self, id, user_openid, school_name, question, answer, sources, tokens_used, created_at):
        self.id = id
        self.user_openid = user_openid
        self.school_name = school_name
        self.question = question
        self.answer = answer
        self.sources = sources
        self.tokens_used = tokens_used
        self.created_at = created_at


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


def generate_qa_response(question: str, school_info: Optional[dict] = None,
                         resources: list = None) -> dict:
    """
    生成 AI 问答回答

    实际项目中应调用大模型 API（如文心一言、ChatGPT）
    此处为模拟实现
    """
    # 问题类型识别
    q_type = _classify_question(question)

    if not school_info:
        return {
            "answer": "抱歉，我暂时没有找到您询问的高校信息。请尝试提供更完整的高校名称，或联系平台添加该宗门信息。",
            "sources": [],
            "suggestions": [
                "搜索「复旦大学」了解更多信息",
                "搜索「上海交通大学」了解更多信息",
                "尝试发布「求万宗宝鉴」需求，让学长为你解答",
            ],
        }

    school = school_info["name"]
    info = {k: v for k, v in school_info.items() if k != "name"}

    # 根据问题类型生成回答
    if q_type == "admission":
        answer = _answer_admission(school, info)
    elif q_type == "major":
        answer = _answer_major(school, info, question)
    elif q_type == "life":
        answer = _answer_life(school, info)
    elif q_type == "spirit":
        answer = _answer_spirit(school, info)
    elif q_type == "general":
        answer = _generate_general_info(school, info)
    else:
        answer = _generate_general_info(school, info)

    return {
        "answer": answer,
        "sources": resources[:3] if resources else [],
        "school_info": {"name": school, **info},
    }


def _classify_question(question: str) -> str:
    """问题分类"""
    q = question.lower()

    if any(w in q for w in ["录取", "分数", "线", "志愿", "投档", "招生", "考多少"]):
        return "admission"
    elif any(w in q for w in ["专业", "院系", "优势", "学科", "转专业", "分流"]):
        return "major"
    elif any(w in q for w in ["生活", "宿舍", "食堂", "食堂", "校园", "环境", "氛围"]):
        return "life"
    elif any(w in q for w in ["校训", "精神", "理念", "文化"]):
        return "spirit"
    else:
        return "general"


def _answer_admission(school: str, info: dict) -> str:
    """回答招生相关问题"""
    return f"""关于 **{school}** 的招生信息：

📊 **院校层次**：{info.get('level', '未知')}
📍 **地理位置**：{info.get('location', '未知')}
🏛 **学校类型**：{info.get('type', '未知')}
🌐 **QS排名**：{info.get('qs_rank', '未知')}

💡 **温馨提示**：
- 具体录取分数线请参考各省市历年招生数据
- 不同专业组录取分数可能有较大差异
- 建议关注学校本科招生网获取最新信息

🎯 **更多问题**：
建议发布「求万宗宝鉴」需求，让目标院校的学长学姐为你详细解答志愿填报策略！"""


def _answer_major(school: str, info: dict, question: str) -> str:
    """回答专业相关问题"""
    majors = info.get("majors", [])
    major_str = "\n".join([f"  • {m}" for m in majors[:8]]) if majors else "暂无数据"

    return f"""关于 **{school}** 的专业信息：

⭐ **优势专业**：
{major_str}

🎓 **专业特色**：
• {info.get('features', ['暂无数据'])[0] if info.get('features') else '暂无数据'}

📚 **选专业建议**：
- 入学后通常有通识教育阶段，可深入了解后再选择
- 部分学校支持辅修或双学位
- 关注各学院的转专业政策

💬 **深入了解**：
发布「联袂问道」需求，找到目标专业的学长带你了解专业内幕！"""


def _answer_life(school: str, info: dict) -> str:
    """回答校园生活问题"""
    campuses = info.get("campus", [])
    campus_str = "\n".join([f"  • {c}" for c in campuses[:4]]) if campuses else "暂无数据"

    return f"""关于 **{school}** 的校园生活：

🏫 **校区分布**：
{campus_str}

✨ **校园特色**：
{info.get('features', ['暂无数据'])[0] if info.get('features') else '暂无数据'}

🚴 **校园体验**：
- 各校区之间通常有校车或公共交通
- 建议实地参加校园开放日
- 加入新生群了解学长学姐的真实体验

📸 **云游校园**：
发布「宗门云游」需求，让在校学长带你线上参观！"""


def _answer_spirit(school: str, info: dict) -> str:
    """回答校训精神问题"""
    spirit = info.get("spirit", "暂无校训信息")
    return f"""关于 **{school}** 的精神传承：

🏆 **校训**：{spirit}

🌟 **院校特色**：
{chr(10).join([f'• {f}' for f in info.get('features', ['暂无'])]) if info.get('features') else '暂无数据'}

📖 **精神解读**：
每一所高校都有独特的文化底蕴，这是几代人积淀的结果。
建议深入了解学校历史，参加校园宣讲，感受学校的精神气质。

💡 **行动建议**：
寻找该校的学长学姐，听听他们对学校精神的理解！"""


def _generate_general_info(school: str, info: dict) -> str:
    """生成通用信息回答"""
    features = "\n".join([f"  • {f}" for f in info.get("features", ["暂无"])]) if info.get("features") else "  • 暂无数据"

    return f"""**{school}** 宗门概览：

📊 **基本信息**：
  • 层次：{info.get('level', '未知')}
  • 类型：{info.get('type', '未知')}
  • 位置：{info.get('location', '未知')}
  • 排名：{info.get('qs_rank', '未知')}

🎯 **优势领域**：
{features}

🏛 **校区**：{', '.join(info.get('campus', ['暂无'])) if info.get('campus') else '暂无数据'}

📖 **校训**：{info.get('spirit', '暂无')}

---

💬 想了解更多？发布「万宗宝鉴」需求，让学长为你深入解答！"""


def save_qa_history(db: Session, user_openid: str, school_name: str,
                   question: str, answer: str, sources: list) -> dict:
    """保存问答历史"""
    import json
    record_id = f"QA{uuid.uuid4().hex[:12].upper()}"
    sources_json = json.dumps(sources) if sources else '[]'

    try:
        # 确保表存在
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS qa_history (
                id TEXT PRIMARY KEY,
                user_openid TEXT NOT NULL,
                school_name TEXT DEFAULT '',
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                sources TEXT DEFAULT '[]',
                tokens_used INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # 插入记录
        db.execute(
            text("""
                INSERT INTO qa_history (id, user_openid, school_name, question, answer, sources, created_at)
                VALUES (:id, :user_openid, :school_name, :question, :answer, :sources, datetime('now'))
            """),
            {
                "id": record_id,
                "user_openid": user_openid,
                "school_name": school_name,
                "question": question,
                "answer": answer,
                "sources": sources_json,
            }
        )
        db.commit()
    except Exception as e:
        db.rollback()
        return {"id": record_id, "school_name": school_name, "created_at": ""}

    return {
        "id": record_id,
        "school_name": school_name,
        "created_at": datetime.now().isoformat(),
    }

    record = QAHistory(
        id=f"QA{uuid.uuid4().hex[:12].upper()}",
        user_openid=user_openid,
        school_name=school_name,
        question=question,
        answer=answer,
        sources=sources,
        created_at=datetime.now(),
    )
    db.add(record)
    db.commit()

    return {
        "id": record.id,
        "school_name": school_name,
        "created_at": record.created_at.isoformat() if record.created_at else "",
    }


def get_qa_history(db: Session, user_openid: str, limit: int = 20) -> list:
    """获取问答历史"""
    try:
        from sqlalchemy import text
        result = db.execute(
            text("SELECT * FROM qa_history WHERE user_openid = :openid ORDER BY created_at DESC LIMIT :limit"),
            {"openid": user_openid, "limit": limit}
        )
        rows = result.fetchall()

        return [
            {
                "id": row[0],
                "school_name": row[2],
                "question": row[3],
                "answer_preview": (row[4][:100] + "..." if len(row[4]) > 100 else row[4]) if row[4] else "",
                "created_at": str(row[8]) if row[8] else "",
            }
            for row in rows
        ]
    except Exception:
        return []
