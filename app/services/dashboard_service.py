"""数据看板统计服务"""

import json
import re
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.api_log import ApiLog
from app.models.assessment import AssessmentRecord
from app.models.indicator import IndicatorCategory
from app.models.user import User
from app.schemas.dashboard import (
    AdminDashboardStats,
    AdminUserActivity,
    AdminUserBehavior,
    AssessmentApiRequests,
    DashboardStats,
    EngineCallDay,
    EngineUsageDay,
    EngineUsageStats,
    IndustryItem,
    ScoreDistItem,
    TrendItem,
)


def _response_code(preview: str | None) -> int | None:
    """从ApiLog响应预览读统一响应的顶层业务码，缺失或截断异常时返回未知。"""
    if not preview:
        return None
    try:
        body = json.loads(preview)
    except (json.JSONDecodeError, TypeError):
        # 响应预览可能被截断；统一响应把 code 放在 JSON 顶层首字段。
        match = re.match(r'^\s*\{\s*"code"\s*:\s*(\d+)', preview)
        return int(match.group(1)) if match else None
    code = body.get("code") if isinstance(body, dict) else None
    return code if isinstance(code, int) and not isinstance(code, bool) else None


def admin_stats(db: Session, days: int = 30) -> AdminDashboardStats:
    """管理端统计：评估快照 + 账号归属 + 动态评估接口请求日志。"""
    today = datetime.now().date()
    first_day = today - timedelta(days=days - 1)
    start = datetime.combine(first_day, datetime.min.time())

    rows = (
        db.query(
            AssessmentRecord.id,
            AssessmentRecord.user_id,
            AssessmentRecord.score,
            AssessmentRecord.level,
            AssessmentRecord.result_json,
            AssessmentRecord.created_at,
        )
        .filter(AssessmentRecord.created_at >= start)
        .all()
    )
    total = len(rows)
    scores = [int(row.score or 0) for row in rows]
    low = sum(1 for row in rows if row.level == "低风险")
    mid = sum(1 for row in rows if row.level == "中等风险")
    high = sum(1 for row in rows if row.level == "高风险")
    completeness_values: list[float] = []
    veto_count = override_count = 0
    trend_by_date: dict[str, list[int]] = {}
    usage_by_date: dict[str, list[int]] = {}
    expert_calls = data_layer_applications = tracked_assessments = untracked_assessments = 0
    for row in rows:
        rj = row.result_json if isinstance(row.result_json, dict) else {}
        completeness = rj.get("completeness")
        if isinstance(completeness, (int, float)):
            completeness_values.append(float(completeness))
        if rj.get("veto"):
            veto_count += 1
        overrides = rj.get("overrides")
        if isinstance(overrides, list):
            override_count += len(overrides)
        day = row.created_at.strftime("%Y-%m-%d")
        bucket = trend_by_date.setdefault(day, [])
        bucket.append(int(row.score or 0))
        usage = rj.get("engineUsage")
        calls = usage.get("expertCalls") if isinstance(usage, dict) else None
        applications = usage.get("dataLayerApplications") if isinstance(usage, dict) else None
        if (
            isinstance(calls, int)
            and not isinstance(calls, bool)
            and calls >= 0
            and isinstance(applications, int)
            and not isinstance(applications, bool)
            and applications >= 0
        ):
            tracked_assessments += 1
            expert_calls += calls
            data_layer_applications += applications
            daily_usage = usage_by_date.setdefault(day, [0, 0])
            daily_usage[0] += calls
            daily_usage[1] += applications
        else:
            untracked_assessments += 1

    # 用户行为只统计落库评估；匿名记录单独展示，不把请求流量猜成用户数。
    user_rows = (
        db.query(
            AssessmentRecord.user_id,
            func.max(User.username),
            func.max(AssessmentRecord.assessor_name),
            func.count(AssessmentRecord.id),
        )
        .outerjoin(User, User.id == AssessmentRecord.user_id)
        .filter(AssessmentRecord.created_at >= start, AssessmentRecord.user_id.isnot(None))
        .group_by(AssessmentRecord.user_id)
        .order_by(func.count(AssessmentRecord.id).desc())
        .limit(10)
        .all()
    )
    distinct_users = (
        db.query(func.count(func.distinct(AssessmentRecord.user_id)))
        .filter(AssessmentRecord.created_at >= start, AssessmentRecord.user_id.isnot(None))
        .scalar()
        or 0
    )
    # topUsers 为前十用户，registeredAssessments/anonymousAssessments 使用全量行计数。
    registered_assessments = sum(1 for row in rows if row.user_id is not None)
    anonymous_assessments = total - registered_assessments
    top_users = [
        AdminUserActivity(
            userId=int(user_id),
            username=username or assessor_name or f"用户 {user_id}",
            assessmentCount=int(count),
        )
        for user_id, username, assessor_name, count in user_rows
        if user_id is not None
    ]

    # 该应用的风险评估由专家引擎处理；按日志统计 assess-dynamic 接口请求，
    # 仅作接口请求流量；成功/失败使用HTTP状态码和统一响应业务码，缺少响应码归为未知。
    call_rows = (
        db.query(
            ApiLog.created_at,
            ApiLog.status_code,
            ApiLog.resp_preview,
        )
        .filter(
            ApiLog.created_at >= start,
            ApiLog.method == "POST",
            ApiLog.path.like("%/risk/assess-dynamic"),
        )
        .all()
    )
    calls_by_date: dict[str, list[int]] = {}
    for created_at, status_code, preview in call_rows:
        counts = calls_by_date.setdefault(created_at.strftime("%Y-%m-%d"), [0, 0, 0, 0])
        counts[0] += 1
        if not 200 <= int(status_code or 0) < 300:
            counts[2] += 1
            continue
        response_code = _response_code(preview)
        if response_code is None:
            counts[3] += 1
        elif response_code == 200:
            counts[1] += 1
        else:
            counts[2] += 1
    call_daily: list[EngineCallDay] = []
    for offset in range(days):
        day = (first_day + timedelta(days=offset)).strftime("%Y-%m-%d")
        count, succeeded, failed, unknown = calls_by_date.get(day, [0, 0, 0, 0])
        call_daily.append(
            EngineCallDay(date=day, count=count, succeeded=succeeded, failed=failed, unknown=unknown)
        )
    call_total = sum(item.count for item in call_daily)
    call_success = sum(item.succeeded for item in call_daily)
    call_failed = sum(item.failed for item in call_daily)
    call_unknown = sum(item.unknown for item in call_daily)

    assessment_trend = []
    engine_usage_daily = []
    for offset in range(days):
        day = (first_day + timedelta(days=offset)).strftime("%Y-%m-%d")
        values = trend_by_date.get(day, [])
        assessment_trend.append(
            TrendItem(date=day, count=len(values), avgScore=round(sum(values) / len(values), 1) if values else 0)
        )
        calls, applications = usage_by_date.get(day, [0, 0])
        engine_usage_daily.append(EngineUsageDay(date=day, expertCalls=calls, dataLayerApplications=applications))

    return AdminDashboardStats(
        windowDays=days,
        assessmentTotal=total,
        averageScore=round(sum(scores) / total, 1) if total else 0,
        lowRiskCount=low,
        midRiskCount=mid,
        highRiskCount=high,
        averageCompleteness=round(sum(completeness_values) / len(completeness_values), 4)
        if completeness_values
        else None,
        vetoCount=veto_count,
        overrideCount=override_count,
        userBehavior=AdminUserBehavior(
            registeredAssessments=registered_assessments,
            anonymousAssessments=anonymous_assessments,
            activeUsers=int(distinct_users),
            topUsers=top_users,
        ),
        engineUsage=EngineUsageStats(
            expertCalls=expert_calls,
            dataLayerApplications=data_layer_applications,
            trackedAssessments=tracked_assessments,
            untrackedAssessments=untracked_assessments,
            daily=engine_usage_daily,
        ),
        assessmentApiRequests=AssessmentApiRequests(
            endpoint="POST /risk/assess-dynamic",
            metric="API 请求日志：HTTP 2xx 且业务码 200 为成功；非 2xx 或非 200 业务码为失败；缺失业务码为未知",
            windowDays=days,
            total=call_total,
            succeeded=call_success,
            failed=call_failed,
            unknown=call_unknown,
            daily=call_daily,
        ),
        assessmentTrend=assessment_trend,
    )


def stats(db: Session) -> DashboardStats:
    total = db.query(func.count(AssessmentRecord.id)).scalar() or 0
    if total == 0:
        return DashboardStats(
            totalAssess=0,
            avgScore=0,
            highRiskRate=0,
            passRate=0,
            lowCount=0,
            midCount=0,
            highCount=0,
        )
    avg_score = db.query(func.avg(AssessmentRecord.score)).scalar() or 0
    low = db.query(func.count(AssessmentRecord.id)).filter(AssessmentRecord.level == "低风险").scalar() or 0
    mid = db.query(func.count(AssessmentRecord.id)).filter(AssessmentRecord.level == "中等风险").scalar() or 0
    high = db.query(func.count(AssessmentRecord.id)).filter(AssessmentRecord.level == "高风险").scalar() or 0
    return DashboardStats(
        totalAssess=total,
        avgScore=round(float(avg_score), 1),
        highRiskRate=round(high / total * 100, 1),
        passRate=round((low + mid) / total * 100, 1),
        lowCount=low,
        midCount=mid,
        highCount=high,
    )


def industry_distribution(db: Session) -> list[IndustryItem]:
    # 大类编码 → 名称映射（来自指标类别树 level=大类；MIXED 为混合经营特殊处理）
    name_map = {
        c: n
        for c, n in db.query(IndicatorCategory.code, IndicatorCategory.name)
        .filter(IndicatorCategory.level == "大类")
        .all()
    }
    name_map["MIXED"] = "混合经营"
    rows = (
        db.query(
            AssessmentRecord.business_type,
            func.count(AssessmentRecord.id),
        )
        .group_by(AssessmentRecord.business_type)
        .all()
    )
    items = []
    for code, cnt in rows:
        label = name_map.get(code) or (code or "未填写")
        # 统计该行业各风险等级数，取占比最高者作为行业风险标签
        level_cnt = {
            lv: db.query(func.count(AssessmentRecord.id))
            .filter(AssessmentRecord.business_type == code, AssessmentRecord.level == lv)
            .scalar()
            or 0
            for lv in ("低风险", "中等风险", "高风险")
        }
        risk = max(level_cnt, key=level_cnt.get) if sum(level_cnt.values()) else "中"
        items.append(IndustryItem(name=label, value=int(cnt), risk=risk))
    return items


def score_distribution(db: Session) -> list[ScoreDistItem]:
    ranges = [
        (0, 300, "0-300"),
        (300, 500, "300-500"),
        (500, 600, "500-600"),
        (600, 700, "600-700"),
        (700, 800, "700-800"),
        (800, 901, "800-1000"),
    ]
    items = []
    for lo, hi, label in ranges:
        cnt = (
            db.query(func.count(AssessmentRecord.id))
            .filter(AssessmentRecord.score >= lo, AssessmentRecord.score < hi)
            .scalar()
            or 0
        )
        items.append(ScoreDistItem(range=label, count=cnt))
    return items


def trend(db: Session, days: int = 30) -> list[TrendItem]:
    start = datetime.now() - timedelta(days=days - 1)
    rows = (
        db.query(
            func.date(AssessmentRecord.created_at).label("d"),
            func.count(AssessmentRecord.id),
            func.avg(AssessmentRecord.score),
        )
        .filter(AssessmentRecord.created_at >= start)
        .group_by(func.date(AssessmentRecord.created_at))
        .all()
    )
    by_date = {str(d): (c, s) for d, c, s in rows}
    items = []
    for i in range(days):
        day = (start + timedelta(days=i)).strftime("%Y-%m-%d")
        cnt, avg = by_date.get(day, (0, 0))
        items.append(TrendItem(date=day, count=cnt, avgScore=round(float(avg or 0), 1)))
    return items
