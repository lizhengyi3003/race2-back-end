"""数据看板统计"""

from pydantic import BaseModel


class DashboardStats(BaseModel):
    totalAssess: int
    avgScore: float
    highRiskRate: float  # 高风险占比 %
    passRate: float  # 授信通过率（低+中风险占比）%
    lowCount: int
    midCount: int
    highCount: int


class IndustryItem(BaseModel):
    name: str
    value: int
    risk: str


class ScoreDistItem(BaseModel):
    range: str
    count: int


class TrendItem(BaseModel):
    date: str
    count: int
    avgScore: float


class AdminUserActivity(BaseModel):
    userId: int
    username: str
    assessmentCount: int


class AdminUserBehavior(BaseModel):
    registeredAssessments: int
    anonymousAssessments: int
    activeUsers: int
    topUsers: list[AdminUserActivity]


class EngineCallDay(BaseModel):
    date: str
    count: int
    succeeded: int
    failed: int
    unknown: int


class AssessmentApiRequests(BaseModel):
    endpoint: str
    metric: str
    windowDays: int
    total: int
    succeeded: int
    failed: int
    unknown: int
    daily: list[EngineCallDay]


class EngineUsageDay(BaseModel):
    date: str
    expertCalls: int
    dataLayerApplications: int


class EngineUsageStats(BaseModel):
    expertCalls: int
    dataLayerApplications: int
    trackedAssessments: int
    untrackedAssessments: int
    daily: list[EngineUsageDay]


class AdminDashboardStats(BaseModel):
    windowDays: int
    assessmentTotal: int
    averageScore: float
    lowRiskCount: int
    midRiskCount: int
    highRiskCount: int
    averageCompleteness: float | None
    vetoCount: int
    overrideCount: int
    userBehavior: AdminUserBehavior
    engineUsage: EngineUsageStats
    assessmentApiRequests: AssessmentApiRequests
    assessmentTrend: list[TrendItem]
