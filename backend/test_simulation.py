# 小紫薯功能测试脚本
# 测试场景覆盖：用户注册、服务浏览、下单、组队、藏经阁、评价等

import requests
import json
import time
import sys
from datetime import datetime

# 设置 UTF-8 输出
sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://127.0.0.1:18765/api/v1"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    # Windows CMD 不支持颜色，使用简单标记
    MARK_PASS = '[PASS]'
    MARK_FAIL = '[FAIL]'

def test(name, fn):
    """执行测试并打印结果"""
    print(f"\n>> Test: {name}")
    try:
        result = fn()
        print(f"[PASS]")
        return True, result
    except Exception as e:
        print(f"[FAIL] {e}")
        return False, None

def api_get(path, headers=None):
    """GET 请求"""
    url = f"{BASE_URL}{path}"
    resp = requests.get(url, headers=headers or {}, timeout=10)
    if resp.status_code >= 400:
        raise Exception(f"HTTP {resp.status_code}: {resp.text[:100]}")
    return resp.json()

def api_post(path, data=None, headers=None):
    """POST 请求"""
    url = f"{BASE_URL}{path}"
    resp = requests.post(url, json=data, headers=headers or {}, timeout=10)
    if resp.status_code >= 400:
        raise Exception(f"HTTP {resp.status_code}: {resp.text[:100]}")
    return resp.json()

def api_put(path, data=None, headers=None):
    """PUT 请求"""
    url = f"{BASE_URL}{path}"
    resp = requests.put(url, json=data, headers=headers or {}, timeout=10)
    if resp.status_code >= 400:
        raise Exception(f"HTTP {resp.status_code}: {resp.text[:100]}")
    return resp.json()

def api_delete(path, headers=None):
    """DELETE 请求"""
    url = f"{BASE_URL}{path}"
    resp = requests.delete(url, headers=headers or {}, timeout=10)
    if resp.status_code >= 400:
        raise Exception(f"HTTP {resp.status_code}: {resp.text[:100]}")
    return resp.json() if resp.content else {}

def run_tests():
    """执行所有测试"""
    print(f"\n{'='*60}")
    print(f"  小紫薯功能模拟测试 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    results = {}

    # ===== 1. 基础健康检查 =====
    print(f"\n{'='*20} 1. 基础健康检查 {'='*20}")

    def test_health():
        data = api_get("/health")
        assert data.get("status") == "ok"
        return data

    results["健康检查"] = test("健康检查", test_health)

    # ===== 2. 认证测试 =====
    print(f"\n{'='*20} 2. 认证与用户测试 {'='*20}")

    # 创建测试用户1 (求助者)
    test_user1 = {
        "code": "test_user1_code_001",
        "nickname": "测试小王",
        "avatar": "https://example.com/avatar1.png",
        "role": "seeker"
    }

    def test_register_user1():
        data = api_post("/auth/login", test_user1)
        assert "openid" in data
        return data

    ok, result = test("注册用户1 (求助者)", test_register_user1)
    if ok:
        user1_token = result.get("token", "")
        user1_openid = result.get("openid", "")
        results["用户1_token"] = (True, user1_token)
    else:
        user1_token = ""
        user1_openid = ""

    # 创建测试用户2 (服务者)
    test_user2 = {
        "code": "test_user2_code_002",
        "nickname": "测试学长小李",
        "avatar": "https://example.com/avatar2.png",
        "role": "provider"
    }

    def test_register_user2():
        data = api_post("/auth/login", test_user2)
        assert "openid" in data
        return data

    ok, result = test("注册用户2 (服务者)", test_register_user2)
    if ok:
        user2_token = result.get("token", "")
        user2_openid = result.get("openid", "")
        results["用户2_token"] = (True, user2_token)
    else:
        user2_token = ""
        user2_openid = ""

    headers_user1 = {"Authorization": f"Bearer {user1_token}"} if user1_token else {}
    headers_user2 = {"Authorization": f"Bearer {user2_token}"} if user2_token else {}

    # ===== 3. 服务相关测试 =====
    print(f"\n{'='*20} 3. 服务广场测试 {'='*20}")

    def test_service_categories():
        data = api_get("/services/categories")
        assert "categories" in data
        return data

    results["服务分类"] = test("获取服务分类", test_service_categories)

    def test_service_list():
        data = api_get("/services")
        assert "services" in data or isinstance(data, list)
        return data

    results["服务列表"] = test("获取服务列表", test_service_list)

    def test_service_search():
        data = api_get("/services?q=高数")
        return data

    results["服务搜索"] = test("搜索服务 (高数)", test_service_search)

    def test_service_filter():
        data = api_get("/services?category=传功授法&min_price=50&max_price=200")
        return data

    results["服务筛选"] = test("筛选服务 (分类+价格)", test_service_filter)

    # ===== 4. 组队功能测试 =====
    print(f"\n{'='*20} 4. 组队功能测试 {'='*20}")

    def test_team_categories():
        data = api_get("/teams/categories")
        assert "categories" in data
        return data

    results["组队分类"] = test("获取组队分类", test_team_categories)

    # 创建组队
    def test_create_team():
        if not user1_token:
            raise Exception("需要登录用户")
        data = api_post("/teams", {
            "title": "【测试】数学建模竞赛组队",
            "description": "寻找数学建模队友，需要建模、编程、论文写作能力",
            "category": "竞赛组队",
            "max_members": 3,
            "target_date": "2026-05-01",
            "deadline": "2026-04-30",
            "tags": ["数学建模", "竞赛", "团队"]
        }, headers_user1)
        assert "id" in data
        return data

    ok, result = test("创建组队", test_create_team)
    team_id = result.get("id") if ok else ""

    def test_team_list():
        data = api_get("/teams")
        assert "teams" in data or isinstance(data, list)
        return data

    results["组队列表"] = test("获取组队列表", test_team_list)

    def test_team_detail():
        if not team_id:
            raise Exception("需要先创建组队")
        data = api_get(f"/teams/{team_id}")
        assert "id" in data
        return data

    results["组队详情"] = test("获取组队详情", test_team_detail)

    # 用户2加入组队
    def test_join_team():
        if not user2_token or not team_id:
            raise Exception("需要登录用户和组队ID")
        data = api_post(f"/teams/{team_id}/join", {}, headers_user2)
        return data

    results["加入组队"] = test("用户2加入组队", test_join_team)

    def test_my_teams():
        if not user1_token:
            raise Exception("需要登录用户")
        data = api_get("/teams/my", headers_user1)
        return data

    results["我的组队"] = test("获取我的组队", test_my_teams)

    # ===== 5. 藏经阁功能测试 =====
    print(f"\n{'='*20} 5. 藏经阁测试 {'='*20}")

    def test_resource_categories():
        data = api_get("/resources/categories")
        assert "categories" in data
        return data

    results["资源分类"] = test("获取资源分类", test_resource_categories)

    # 发布资源
    def test_create_resource():
        if not user2_token:
            raise Exception("需要登录用户")
        data = api_post("/resources", {
            "title": "【免费】复旦431金融专硕考研资料分享",
            "content": "包含近10年真题、专业课笔记、教材重点整理...",
            "category": "考研资料",
            "tags": ["考研", "金融", "复旦", "资料"]
        }, headers_user2)
        return data

    ok, result = test("发布资源", test_create_resource)
    resource_id = result.get("id") if ok else ""

    def test_resource_list():
        data = api_get("/resources")
        return data

    results["资源列表"] = test("获取资源列表", test_resource_list)

    def test_resource_detail():
        if not resource_id:
            # 尝试获取第一个资源
            res = api_get("/resources")
            items = res.get("resources", res) if isinstance(res, dict) else res
            if items:
                resource_id = items[0].get("id", "")
        if not resource_id:
            raise Exception("无资源可查看")
        data = api_get(f"/resources/{resource_id}")
        return data

    results["资源详情"] = test("获取资源详情", test_resource_detail)

    # ===== 6. 评价体系测试 =====
    print(f"\n{'='*20} 6. 评价体系测试 {'='*20}")

    def test_review_tags():
        data = api_get("/reviews/tags")
        assert "tags" in data
        return data

    results["评价标签"] = test("获取评价标签", test_review_tags)

    # ===== 7. 分红池测试 =====
    print(f"\n{'='*20} 7. 分红池测试 {'='*20}")

    def test_dividend_info():
        data = api_get("/levels/dividend")
        return data

    results["分红池信息"] = test("获取分红池信息", test_dividend_info)

    def test_dividend_history():
        if not user1_token:
            raise Exception("需要登录用户")
        data = api_get("/levels/dividend/history", headers_user1)
        return data

    results["领取历史"] = test("获取领取历史", test_dividend_history)

    # ===== 8. 师徒体系测试 =====
    print(f"\n{'='*20} 8. 师徒体系测试 {'='*20}")

    def test_mentor_list():
        data = api_get("/mentorships/mentors")
        return data

    results["师傅列表"] = test("获取师傅列表", test_mentor_list)

    def test_apply_mentor():
        if not user1_token:
            raise Exception("需要登录用户")
        data = api_post("/mentorships/apply", {
            "mentor_openid": user2_openid,
            "message": "希望拜师学习！"
        }, headers_user1)
        return data

    results["拜师申请"] = test("用户1申请拜师", test_apply_mentor)

    def test_my_mentor():
        if not user1_token:
            raise Exception("需要登录用户")
        data = api_get("/mentorships/my", headers_user1)
        return data

    results["我的师徒"] = test("获取我的师徒关系", test_my_mentor)

    # ===== 9. 等级系统测试 =====
    print(f"\n{'='*20} 9. 等级系统测试 {'='*20}")

    def test_levels():
        data = api_get("/levels")
        return data

    results["等级列表"] = test("获取等级列表", test_levels)

    def test_user_level():
        if not user1_token:
            raise Exception("需要登录用户")
        data = api_get("/levels/me", headers_user1)
        return data

    results["用户等级"] = test("获取用户等级", test_user_level)

    # ===== 10. 聊聊功能测试 =====
    print(f"\n{'='*20} 10. 聊聊功能测试 {'='*20}")

    def test_conversations():
        if not user1_token:
            raise Exception("需要登录用户")
        data = api_get("/conversations", headers_user1)
        return data

    results["会话列表"] = test("获取会话列表", test_conversations)

    # ===== 11. 订单系统测试 =====
    print(f"\n{'='*20} 11. 订单系统测试 {'='*20}")

    # 获取一个服务来下单
    def test_get_service_for_order():
        data = api_get("/services")
        services = data.get("services", data) if isinstance(data, dict) else data
        if services and len(services) > 0:
            return services[0]
        return None

    svc = test_get_service_for_order()

    def test_create_order():
        if not svc:
            raise Exception("无服务可下单")
        if not user1_token:
            raise Exception("需要登录用户")
        data = api_post("/orders", {
            "service_id": svc.get("id"),
            "quantity": 1,
            "message": "测试下单，请尽快联系"
        }, headers_user1)
        assert "id" in data
        return data

    ok, result = test("创建订单", test_create_order)
    order_id = result.get("id") if ok else ""

    def test_order_list():
        if not user1_token:
            raise Exception("需要登录用户")
        data = api_get("/orders", headers_user1)
        return data

    results["订单列表"] = test("获取订单列表", test_order_list)

    def test_order_detail():
        if not order_id:
            raise Exception("需要订单ID")
        data = api_get(f"/orders/{order_id}")
        return data

    results["订单详情"] = test("获取订单详情", test_order_detail)

    # ===== 12. 仲裁系统测试 =====
    print(f"\n{'='*20} 12. 仲裁系统测试 {'='*20}")

    def test_dispute_types():
        data = api_get("/disputes/types")
        return data

    results["仲裁类型"] = test("获取仲裁类型", test_dispute_types)

    # ===== 13. 高校百科测试 =====
    print(f"\n{'='*20} 13. 高校百科测试 {'='*20}")

    def test_school_list():
        data = api_get("/school-wiki/schools")
        return data

    results["学校列表"] = test("获取学校列表", test_school_list)

    def test_school_search():
        data = api_get("/school-wiki/search?q=复旦")
        return data

    results["学校搜索"] = test("搜索学校 (复旦)", test_school_search)

    # ===== 测试总结 =====
    print(f"\n{'='*60}")
    print(f"  测试结果汇总")
    print(f"{'='*60}")

    passed = 0
    failed = 0

    for name, result in results.items():
        if isinstance(result, tuple):
            ok, _ = result
            status = "[PASS]" if ok else "[FAIL]"
            print(f"  {name}: {status}")
            if ok:
                passed += 1
            else:
                failed += 1
        else:
            passed += 1
            print(f"  {name}: [PASS]")

    print(f"\n{'='*60}")
    print(f"  总计: {passed} 通过, {failed} 失败")
    print(f"{'='*60}")

    return passed, failed

if __name__ == "__main__":
    run_tests()
