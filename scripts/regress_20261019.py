"""
2026-10-19 缺陷修复回归（隔离 SQLite，不触碰 .env 与云环境）

覆盖：
A 侧  D01 搜索清除 / D02 枚举中文名 / D03 指标口径 / D04 组队人数 / D05 需求详情
B 侧  LD001 建单500 / LD002 完成后重开二次入账 / LD003 日志只存第1条
      LD004 时间线丢失 / LD005 结算部分提交 / BU01 我的服务
用法：python scripts/regress_20261019.py
"""
import os
import sys
import tempfile
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND = os.path.join(BASE, "backend")
sys.path.insert(0, BACKEND)
os.chdir(BACKEND)

TMP_DB = os.path.join(tempfile.gettempdir(), "xz_regress_20261019.db")
if os.path.exists(TMP_DB):
    os.remove(TMP_DB)

os.environ["DATABASE_URL"] = "sqlite:///" + TMP_DB.replace("\\", "/")
os.environ["JWT_SECRET"] = "regress-secret-20261019"
os.environ["ENVIRONMENT"] = "development"
# 回归需覆盖收费订单，测试进程内临时开启支付；不修改 .env 与云环境
os.environ["PAYMENT_ENABLED"] = "true"

from fastapi.testclient import TestClient  # noqa: E402
from models import init_db, User  # noqa: E402
from utils.db import SessionLocal  # noqa: E402
import main  # noqa: E402

init_db()
from utils.jwt_utils import create_access_token  # noqa: E402

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, ok, detail))
    print(("PASS " if ok else "FAIL ") + name + ("  | " + str(detail) if detail else ""))


def make_user(openid, nickname, role="provider", stones=10000):
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.openid == openid).first()
        if not u:
            import uuid as _uuid
            u = User(id=f"U{_uuid.uuid4().hex[:12]}", openid=openid, nickname=nickname, role=role,
                     spirit_stones=stones, exp_points=0, level=1,
                     total_orders_done=0, rating_count=0, status="active")
            db.add(u)
            db.flush()
            db.commit()
        return u
    finally:
        db.close()


client = TestClient(main.app)


def token_of(openid):
    return create_access_token(openid, "seeker")


def hdr(openid):
    return {"Authorization": "Bearer " + token_of(openid)}


A = "regress_A_seeker"
B = "regress_B_provider"
make_user(A, "回归求助者", "seeker", 10000)
make_user(B, "回归服务者", "provider", 0)

# ── B 侧：发布服务 ────────────────────────────────────────
svc_paid = client.post("/api/v1/services", headers=hdr(B), json={
    "dao_fa_type": "chuan_gong", "title": "回归测试·高数辅导一对一",
    "description": "这是回归测试用的服务说明，满足至少二十个字的要求，用于验证订单闭环逻辑是否正常。",
    "price": 1000, "pricing_mode": "per_session", "unit": "次",
    "min_sessions": 1, "service_type": "tutoring",
    "delivery_methods": ["online"], "subjects": ["math"],
}).json()
svc_free = client.post("/api/v1/services", headers=hdr(B), json={
    "dao_fa_type": "chuan_gong", "title": "回归测试·免费答疑服务",
    "description": "免费互助服务，用于验证零金额订单不会因为空值参与乘法而创建失败。",
    "price": 0, "pricing_mode": "free", "unit": "次",
    "min_sessions": 1, "service_type": "tutoring",
    "delivery_methods": ["online"], "subjects": ["math"],
}).json()
sid_paid = (svc_paid.get("service") or svc_paid).get("id") if isinstance(svc_paid, dict) else None
sid_free = (svc_free.get("service") or svc_free).get("id") if isinstance(svc_free, dict) else None
check("发布服务（收费/免费）", bool(sid_paid and sid_free), f"{sid_paid} / {sid_free}")

if sid_paid and sid_free:
    # LD001：建单不再 500
    r1 = client.post("/api/v1/orders", headers=hdr(A),
                     json={"service_id": sid_paid, "sessions": 2})
    check("LD001 收费订单创建（1000×2=2000）", r1.status_code == 200,
          f"{r1.status_code} {r1.text[:160]}")
    if r1.status_code == 200:
        body = r1.json()
        check("LD001 金额正确", body.get("service_fee") == 2000, body)

    r2 = client.post("/api/v1/orders", headers=hdr(A),
                     json={"service_id": sid_free, "sessions": 1})
    check("LD001 免费订单创建（0）", r2.status_code == 200,
          f"{r2.status_code} {r2.text[:160]}")

    if r1.status_code == 200:
        oid = r1.json()["id"]

        # 状态推进：paid -> assigned -> in_progress
        for st in ("paid", "assigned", "in_progress"):
            rr = client.patch(f"/api/v1/orders/{oid}/status", headers=hdr(B),
                              json={"status": st})
            check(f"状态推进 {st}", rr.status_code == 200, rr.text[:120])

        # LD003：两次课次日志都应落库
        l1 = client.post(f"/api/v1/orders/{oid}/session-log", headers=hdr(B),
                         json={"session_no": 1, "duration_min": 60, "summary": "第1课"})
        l2 = client.post(f"/api/v1/orders/{oid}/session-log", headers=hdr(B),
                         json={"session_no": 2, "duration_min": 60, "summary": "第2课"})
        check("LD003 两次课次提交", l1.status_code == 200 and l2.status_code == 200,
              f"{l1.status_code}/{l2.status_code}")

        db = SessionLocal()
        from models import Order
        o = db.query(Order).filter(Order.id == oid).first()
        logs = o.session_logs or []
        check("LD003 日志完整持久化（2条）", len(logs) == 2,
              f"logs={len(logs)} done={o.sessions_done} status={o.status}")
        check("LD003 全部交付后转待确认", o.status == "pending_confirm", o.status)
        db.close()

        # 重复编号不新增课次
        l3 = client.post(f"/api/v1/orders/{oid}/session-log", headers=hdr(B),
                         json={"session_no": 2, "duration_min": 90, "summary": "第2课重复"})
        db = SessionLocal()
        o = db.query(Order).filter(Order.id == oid).first()
        check("LD003 重复课次号不新增", len(o.session_logs or []) == 2 and l3.status_code == 200,
              f"logs={len(o.session_logs)} dup={l3.json().get('duplicated')}")
        db.close()

        # A 确认完成
        rc = client.patch(f"/api/v1/orders/{oid}/status", headers=hdr(A),
                          json={"status": "completed"})
        check("A 确认完成", rc.status_code == 200, rc.text[:160])

        db = SessionLocal()
        o = db.query(Order).filter(Order.id == oid).first()
        b = db.query(User).filter(User.openid == B).first()
        check("结算入账 1800", b.spirit_stones == 1800, f"stones={b.spirit_stones}")
        check("LD004 时间线完整（含 settled）",
              any(t.get("status") == "settled" for t in (o.timeline or [])),
              [t.get("status") for t in (o.timeline or [])])
        check("LD004 状态流转全部落库",
              all(any(t.get("status") == s for t in (o.timeline or []))
                  for s in ("paid", "assigned", "in_progress", "completed")),
              [t.get("status") for t in (o.timeline or [])])
        b_stones_after = b.spirit_stones
        db.close()

        # LD002：完成后补日志应被拒绝
        l4 = client.post(f"/api/v1/orders/{oid}/session-log", headers=hdr(B),
                         json={"session_no": 3, "duration_min": 30, "summary": "完成后补记"})
        check("LD002 完成后补日志被拒绝", l4.status_code == 400, f"{l4.status_code} {l4.text[:120]}")

        # LD002：直接重复确认应被拒绝
        rc2 = client.patch(f"/api/v1/orders/{oid}/status", headers=hdr(A),
                           json={"status": "completed"})
        check("LD002 重复确认被拒绝", rc2.status_code == 400, f"{rc2.status_code} {rc2.text[:120]}")

        db = SessionLocal()
        b = db.query(User).filter(User.openid == B).first()
        check("LD002 无二次入账", b.spirit_stones == b_stones_after,
              f"{b_stones_after} -> {b.spirit_stones}")
        db.close()

        # LD005：结算异常整体回滚
        r_new = client.post("/api/v1/orders", headers=hdr(A),
                            json={"service_id": sid_paid, "sessions": 1})
        oid2 = r_new.json()["id"]
        for st in ("paid", "assigned", "in_progress"):
            client.patch(f"/api/v1/orders/{oid2}/status", headers=hdr(B), json={"status": st})
        client.post(f"/api/v1/orders/{oid2}/session-log", headers=hdr(B),
                    json={"session_no": 1, "duration_min": 60, "summary": "唯一课次"})

        import services.level_service as ls
        original = ls.add_exp

        def boom(*a, **kw):
            raise RuntimeError("注入故障")

        ls.add_exp = boom
        import routers.orders as ro
        ro.add_exp = boom
        try:
            rfail = client.patch(f"/api/v1/orders/{oid2}/status", headers=hdr(A),
                                 json={"status": "completed"})
        finally:
            ls.add_exp = original
            ro.add_exp = original

        db = SessionLocal()
        o2 = db.query(Order).filter(Order.id == oid2).first()
        b = db.query(User).filter(User.openid == B).first()
        check("LD005 故障返回 5xx", rfail.status_code >= 500, rfail.status_code)
        check("LD005 订单状态回滚为待确认", o2.status == "pending_confirm", o2.status)
        check("LD005 余额未部分提交", b.spirit_stones == b_stones_after,
              f"{b_stones_after} -> {b.spirit_stones}")
        check("LD005 完成数未部分提交", b.total_orders_done == 1, b.total_orders_done)
        db.close()

# ── A / D 侧 ─────────────────────────────────────────────
r = client.get("/api/v1/services/" + sid_paid)
if r.status_code == 200:
    d = r.json()
    check("D02 服务类别返回中文名",
          d.get("dao_fa_type_name") == "传功授法", d.get("dao_fa_type_name"))
    p = d.get("provider") or {}
    check("D03 评价数/服务数分离",
          "rating_count" in p and p.get("service_count") == 2,
          f"rating_count={p.get('rating_count')} service_count={p.get('service_count')}")

# 组队
team = client.post("/api/v1/teams", headers=hdr(B), json={
    "title": "回归测试·图书馆搭子", "description": "回归测试组队",
    "category": "competition", "max_members": 2, "tags": [],
}).json()
tid = team.get("id") or (team.get("team") or {}).get("id")
r = client.get("/api/v1/teams", params={"category": "competition", "page_size": 10})
if r.status_code == 200:
    teams = r.json().get("teams", [])
    hit = next((t for t in teams if t.get("id") == tid), None)
    check("D04 列表返回 current_members/max_members",
          bool(hit) and "current_members" in hit and "max_members" in hit,
          hit and {k: hit.get(k) for k in ("current_members", "max_members")})
    check("D02 组队类别返回中文名",
          bool(hit) and hit.get("category_name") == "竞赛组队",
          hit and hit.get("category_name"))

# 需求创建 + 详情（D05 依赖）
r = client.post("/api/v1/demands", headers=hdr(A), json={
    "type": "tutor", "dao_fa_type": "chuan_gong",
    "title": "回归_20261019_高数极限求助",
    "description": "回归测试需求说明", "budget": 0, "contact": "", "tags": [],
})
did = r.json().get("id")
check("需求创建", bool(did), r.text[:160])
if did:
    rd = client.get(f"/api/v1/demands/{did}")
    check("D05 需求详情接口可用", rd.status_code == 200 and rd.json().get("id") == did,
          rd.status_code)

# BU01：我的服务
r = client.get("/api/v1/services", headers=hdr(B), params={"mine": True})
if r.status_code == 200:
    mine = r.json().get("services", [])
    check("BU01 mine 过滤只返回本人服务",
          all(s.get("dao_fa_type") == "chuan_gong" for s in mine) and len(mine) >= 2,
          f"count={len(mine)}")
else:
    check("BU01 mine 过滤", False, r.text[:160])

# 未登录访问 mine 应 401
r = client.get("/api/v1/services", params={"mine": True})
check("BU01 未登录访问 mine 返回 401", r.status_code == 401, r.status_code)

# ── 汇总 ────────────────────────────────────────────────
passed = sum(1 for _, ok, _ in RESULTS if ok)
print(f"\n合计 {len(RESULTS)} 项，通过 {passed}，失败 {len(RESULTS) - passed}")
sys.exit(0 if passed == len(RESULTS) else 1)
