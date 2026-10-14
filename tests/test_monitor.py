"""系统监控与管理平台接口测试"""


def test_monitor_health(client, auth_headers):
    r = client.get("/api/v1/monitor/health", headers=auth_headers)
    body = r.json()
    assert body["code"] == 200
    data = body["data"]
    assert data["service"] == "ok"
    assert data["database"] == "ok"
    assert data["modelExists"] is True


def test_monitor_server(client, auth_headers):
    r = client.get("/api/v1/monitor/server", headers=auth_headers)
    body = r.json()
    assert body["code"] == 200
    data = body["data"]
    assert "cpu" in data and "memory" in data and "disk" in data
    assert 0 <= data["cpu"]["percent"] <= 100


def test_monitor_database(client, auth_headers):
    r = client.get("/api/v1/monitor/database", headers=auth_headers)
    body = r.json()
    assert body["code"] == 200
    data = body["data"]
    assert data["connected"] is True
    assert len(data["tables"]) >= 4  # user/record/model/config/api_log


def test_admin_stats(client, auth_headers):
    r = client.get("/api/v1/admin/stats", headers=auth_headers)
    body = r.json()
    assert body["code"] == 200
    assert body["data"]["users"] >= 1


def test_admin_dashboard_is_private_and_uses_persisted_activity(client, auth_headers):
    from tests.conftest import SAMPLE_INPUT

    assert client.get("/api/v1/admin/dashboard").json()["code"] == 401
    created = client.post(
        "/api/v1/admin/users",
        json={"username": "dashboard_analyst", "password": "test123", "role": "analyst"},
        headers=auth_headers,
    )
    assert created.json()["code"] == 200
    analyst_login = client.post("/api/v1/auth/login", json={"username": "dashboard_analyst", "password": "test123"})
    analyst_headers = {"Authorization": f"Bearer {analyst_login.json()['data']['token']}"}
    assert client.get("/api/v1/admin/dashboard", headers=analyst_headers).json()["code"] == 403

    payload = {**SAMPLE_INPUT, "enterpriseName": "看板契约记录"}
    assessed = client.post("/api/v1/risk/assess-dynamic", json=payload, headers=auth_headers)
    assert assessed.json()["code"] == 200
    result = assessed.json()["data"]
    assert isinstance(result.get("contributions"), list)
    assert isinstance(result.get("deductions"), list)
    assert isinstance(result.get("overrides"), list)
    assert "veto" in result and "completeness" in result
    assert "riskAlerts" in result and "transparency" in result

    record_list = client.get(
        "/api/v1/risk/records",
        params={"keyword": "看板契约记录", "page": 1, "size": 10},
        headers=auth_headers,
    ).json()["data"]
    record = next(item for item in record_list["items"] if item["enterpriseName"] == "看板契约记录")
    detail = client.get(f"/api/v1/risk/records/{record['id']}", headers=auth_headers).json()["data"]
    for field in ("contributions", "deductions", "overrides", "riskAlerts", "transparency", "engineUsage"):
        assert detail[field] == result[field]
    assert detail["completeness"] == result["completeness"]

    before = client.get("/api/v1/admin/dashboard", headers=auth_headers).json()["data"]
    invalid = client.post("/api/v1/risk/assess-dynamic", json={"businessType": "invalid"}, headers=auth_headers)
    assert invalid.status_code == 200 and invalid.json()["code"] == 422
    after = client.get("/api/v1/admin/dashboard", headers=auth_headers).json()["data"]
    assert after["assessmentApiRequests"]["failed"] == before["assessmentApiRequests"]["failed"] + 1
    assert after["assessmentApiRequests"]["succeeded"] == before["assessmentApiRequests"]["succeeded"]
    assert after["engineUsage"]["expertCalls"] == before["engineUsage"]["expertCalls"]

    dashboard = client.get("/api/v1/admin/dashboard", headers=auth_headers, params={"days": 14})
    assert dashboard.json()["code"] == 200
    stats = dashboard.json()["data"]
    assert stats["assessmentTotal"] >= 1
    assert stats["userBehavior"]["registeredAssessments"] >= 1
    assert stats["userBehavior"]["activeUsers"] >= 1
    assert stats["engineUsage"]["expertCalls"] >= 1
    assert stats["engineUsage"]["trackedAssessments"] >= 1
    assert stats["engineUsage"]["untrackedAssessments"] >= 0
    assert len(stats["engineUsage"]["daily"]) == 14
    assert stats["assessmentApiRequests"]["total"] >= 1
    assert stats["assessmentApiRequests"]["succeeded"] >= 1
    assert stats["assessmentApiRequests"]["failed"] >= 0
    assert stats["assessmentApiRequests"]["endpoint"] == "POST /risk/assess-dynamic"
    assert len(stats["assessmentTrend"]) == 14


def test_admin_users_crud(client, auth_headers):
    # 创建
    r = client.post(
        "/api/v1/admin/users",
        json={"username": "testuser", "password": "test123", "realName": "测试用户", "role": "analyst"},
        headers=auth_headers,
    )
    assert r.json()["code"] == 200
    uid = r.json()["data"]["id"]

    # 列表
    r = client.get("/api/v1/admin/users", headers=auth_headers, params={"keyword": "testuser"})
    assert r.json()["data"]["total"] >= 1

    # 更新
    r = client.put(f"/api/v1/admin/users/{uid}", json={"status": 0}, headers=auth_headers)
    assert r.json()["data"]["status"] == 0

    # 重置密码
    r = client.post(f"/api/v1/admin/users/{uid}/reset-password", json={"newPassword": "newpass"}, headers=auth_headers)
    assert r.json()["code"] == 200

    # 删除
    r = client.delete(f"/api/v1/admin/users/{uid}", headers=auth_headers)
    assert r.json()["code"] == 200


def test_api_spec(client, auth_headers):
    r = client.get("/api/v1/admin/api-spec", headers=auth_headers)
    body = r.json()
    assert body["code"] == 200
    assert len(body["data"]) >= 20


def test_api_logs(client, auth_headers):
    from tests.conftest import SAMPLE_INPUT

    client.post("/api/v1/risk/assess-dynamic", json=SAMPLE_INPUT)
    r = client.get("/api/v1/admin/api-logs", headers=auth_headers, params={"page": 1, "size": 5})
    body = r.json()
    assert body["code"] == 200
    assert body["data"]["total"] >= 1
