"""评估记录输出（camelCase，供管理平台/前端使用）"""

from datetime import datetime

from pydantic import BaseModel

from app.schemas.risk import DataTransparency, EngineUsage, RiskAlert


class IndicatorValueOut(BaseModel):
    """动态指标明细（评估记录详情）。"""

    code: str
    name: str = ""
    level: str = ""
    unit: str = ""
    value: str | None = None
    quality: str = "直接"


class AssessmentRecordOut(BaseModel):
    id: int
    enterpriseName: str
    businessType: str

    score: int
    probability: float
    level: str
    suggestedAmount: float
    suggestedRate: float
    assessorName: str | None = None
    createdAt: datetime | None = None

    # 真实回测（人工回填放款结果）
    outcome: str = "pending"  # pending/normal/overdue/rejected
    outcomeNote: str | None = None
    outcomeAt: datetime | None = None

    # 动态评估扩展
    mixedBusiness: dict | None = None
    completeness: float | None = None
    veto: str | None = None
    contributions: list[dict] | None = None
    deductions: list[dict] | None = None
    overrides: list[str] | None = None
    riskAlerts: list[RiskAlert] | None = None
    transparency: DataTransparency | None = None
    engineUsage: EngineUsage | None = None
    indicatorValues: list[IndicatorValueOut] | None = None

    # 完整快照（详情查看）
    input: dict | None = None
    result: dict | None = None

    @classmethod
    def from_model(cls, r, indicator_values: list[IndicatorValueOut] | None = None) -> "AssessmentRecordOut":
        input_json = r.input_json or {}
        result_json = r.result_json if isinstance(r.result_json, dict) else {}
        return cls(
            id=r.id,
            enterpriseName=r.enterprise_name,
            businessType=r.business_type,
            score=r.score,
            probability=r.probability,
            level=r.level,
            suggestedAmount=r.suggested_amount,
            suggestedRate=r.suggested_rate,
            assessorName=r.assessor_name,
            createdAt=r.created_at,
            outcome=r.outcome or "pending",
            outcomeNote=r.outcome_note,
            outcomeAt=r.outcome_at,
            mixedBusiness=input_json.get("mixedBusiness") if isinstance(input_json, dict) else None,
            completeness=result_json.get("completeness") if isinstance(result_json, dict) else None,
            veto=result_json.get("veto") if isinstance(result_json, dict) else None,
            contributions=result_json.get("contributions"),
            deductions=result_json.get("deductions"),
            overrides=result_json.get("overrides"),
            riskAlerts=result_json.get("riskAlerts"),
            transparency=result_json.get("transparency"),
            engineUsage=result_json.get("engineUsage"),
            indicatorValues=indicator_values,
            input=input_json,
            result=result_json,
        )
