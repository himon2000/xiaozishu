"""
业务枚举 → 中文展示名

前端模板不再直接渲染内部枚举值（chuan_gong / competition / mi_jing 等），
后端在返回数据时一并给出 *_name 字段，保证各端口径一致。
前端可继续用这些字段做键值查询（如 tag-dao-chuan_gong 的样式类）。
"""

# 道法类型 → 中文名
DAO_FA_NAMES = {
    "chuan_gong": "传功授法",
    "mi_jing": "联袂问道",
    "zong_men": "万宗宝鉴",
    "xia_shan": "下山历练",
    "zhi_fa": "天衡裁决",
    "cang_jing": "道藏天阁",
}

# 组队分类 → 中文名
TEAM_CATEGORY_NAMES = {
    "mi_jing": "课题/科研",
    "competition": "竞赛组队",
    "project": "项目合作",
    "study": "学习小组",
    "internship": "寻觅道场",
    "referral": "求取推荐",
    "job": "问道职涯",
    "job_resource": "布施机缘",
}

# 服务类型 → 中文名
SERVICE_TYPE_NAMES = {
    "tutoring": "学科辅导",
    "competition": "竞赛陪练",
    "exam_prep": "考前冲刺",
    "thesis": "论文指导",
}

# 需求类型 → 中文名
DEMAND_TYPE_NAMES = {
    "tutor": "找辅导",
    "team": "找队友",
    "internship": "找实习",
    "consult": "志愿咨询",
    "mentor": "找导师",
}

# 订单状态 → 中文名
ODER_STATUS_NAMES = {
    "pending_payment": "待付灵契",
    "paid": "灵契已付",
    "assigned": "大虾接单",
    "in_progress": "修炼中",
    "pending_confirm": "待散修确认",
    "completed": "功法大成",
    "dispute": "纠纷仲裁中",
    "admin_resolving": "执事处理中",
    "resolved": "仲裁完结",
    "cancelled": "灵契解除",
}


def _name(mapping: dict, key, fallback: str = "") -> str:
    if not key:
        return fallback
    return mapping.get(key) or fallback or str(key)


def dao_fa_name(value) -> str:
    return _name(DAO_FA_NAMES, value, "综合服务")


def team_category_name(value) -> str:
    return _name(TEAM_CATEGORY_NAMES, value, "课题组队")


def service_type_name(value) -> str:
    return _name(SERVICE_TYPE_NAMES, value, "")


def demand_type_name(value) -> str:
    return _name(DEMAND_TYPE_NAMES, value, "通用需求")


def order_status_name(value) -> str:
    return _name(ODER_STATUS_NAMES, value, str(value or ""))
