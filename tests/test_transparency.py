"""看板 #8/#15：解释快照、覆盖率、风险定位及补录数据往返。"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.db.base import Base
from app.models.indicator import IndicatorConfig
from app.schemas.risk import RiskResult
from app.services import record_service, risk_service


@pytest.fixture()
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all(
            [
                IndicatorConfig(
                    code="T_REVENUE",
                    name="营业收入",
                    level="基本项",
                    category_code="BASIC",
                    indicator_type="数值",
                    unit="万元",
                    value_range="0-100",
                    scoring_config={"max": 100},
                    data_source="财务报表",
                    risk_meaning="经营规模",
                    scoring_rule="越高越好",
                    weight_star=5,
                ),
                IndicatorConfig(
                    code="T_VETO",
                    name="失信红线",
                    level="基本项",
                    category_code="BASIC",
                    indicator_type="布尔",
                    value_range="是/否",
                    is_veto=True,
                    scoring_rule="命中即拒贷",
                ),
                IndicatorConfig(
                    code="T_NAME",
                    name="主体名称",
                    level="基本项",
                    category_code="BASIC",
                    indicator_type="文本",
                ),
                IndicatorConfig(
                    code="T_01",
                    name="灌溉覆盖",
                    level="大类",
                    category_code="01",
                    indicator_type="数值",
                    value_range="0-100",
                    scoring_config={"max": 100},
                    data_source="生产台账",
                ),
                IndicatorConfig(
                    code="T_02",
                    name="加工资质",
                    level="大类",
                    category_code="02",
                    indicator_type="枚举",
                    value_range="合格/不合格",
                    scoring_config={"map": {"合格": 100, "不合格": 10}},
                ),
                IndicatorConfig(
                    code="T_LEAF",
                    name="叶子指标",
                    level="具体营业类型",
                    category_code="0111_0101",
                    indicator_type="数值",
                    value_range="0-100",
                    scoring_config={"max": 100},
                ),
            ]
        )
        session.commit()
        yield session
    engine.dispose()


def payload(indicators, **kwargs):
    return {"enterpriseName": "解释验收样例", "businessType": "01", "indicators": indicators, **kwargs}


def test_snapshot_roundtrip_and_source_history(db):
    request = payload({"T_REVENUE": "100", "T_VETO": "否", "T_NAME": "农场", "T_01": "100"})
    result = risk_service.assess_dynamic_and_store(db, request, user_id=17)
    parsed = RiskResult.model_validate(result)
    assert parsed.riskAlerts == []
    assert parsed.engineUsage.expertCalls == 1
    assert parsed.completeness == 1
    assert parsed.transparency.confidence == 1
    assert parsed.transparency.scoredCount == 2
    assert parsed.score == 1000  # 未命中的否决项只核验，不能作为40分项拉低评分
    assert any(c.code == "T_REVENUE" for c in parsed.contributions)
    record = record_service.list_records(db, user_id=17).items[0]
    config = db.query(IndicatorConfig).filter_by(code="T_REVENUE").one()
    config.data_source = "修改后的采集渠道"
    db.commit()
    detail = record_service.get_record(db, record.id, user_id=17)
    assert detail.input == request  # 历史补录可还原经营类型及全部指标值
    assert detail.result == result
    assert (
        next(i for i in detail.result["transparency"]["indicators"] if i["code"] == "T_REVENUE")["dataSource"]
        == "财务报表"
    )


def test_redline_has_code_and_zero_credit_even_for_mixed(db):
    request = payload(
        {"T_REVENUE": "100", "T_VETO": "是", "T_01": "100", "T_02": "合格"},
        businessType="MIXED",
        mixedBusiness={"0111_0101": 0.9, "0211_0101": 0.1},
    )
    result = risk_service.assess_dynamic_and_store(db, request)
    assert result["veto"] == "失信红线"
    assert result["suggestedAmount"] == 0
    assert result["score"] == 200
    assert result["engineUsage"]["expertCalls"] == 2
    assert result["riskAlerts"][0]["severity"] == "veto"
    assert result["riskAlerts"][0]["code"] == "T_VETO"
    assert "不予授信" in result["riskAlerts"][0]["reason"]


def test_high_risk_explains_specific_indicator(db):
    result = risk_service.assess_dynamic_and_store(db, payload({"T_REVENUE": "10", "T_VETO": "否"}))
    alert = next(a for a in result["riskAlerts"] if a["code"] == "T_REVENUE")
    assert alert["severity"] == "high"
    assert alert["score"] == 10
    assert "经营规模" in alert["reason"]
    assert set(result["transparency"]["missingCodes"]) == {"T_NAME", "T_01"}
    assert result["completeness"] == 0.5


def test_valid_coverage_does_not_count_invalid_values_or_extra_fields(db):
    request = payload({"T_REVENUE": "nan", "T_VETO": "不清楚", "T_NAME": "名字", "T_02": "不存在的选项"})
    result = risk_service.assess_dynamic_and_store(db, request)
    meta = result["transparency"]
    assert result["completeness"] == 0.75  # 有值与有效值分别计量
    assert meta["confidence"] == 0
    assert meta["scoredCount"] == 0
    assert {i["code"] for i in meta["indicators"] if i["status"] == "invalid"} == {"T_REVENUE", "T_VETO", "T_02"}
    assert "不代表预测准确率" in meta["confidenceExplanation"]


def test_expected_set_covers_mixed_paths_and_zero_share_is_ignored(db):
    request = payload(
        {"T_REVENUE": "100", "T_VETO": "否", "T_01": "100", "T_02": "合格"},
        businessType="MIXED",
        mixedBusiness={"0111_0101": 1, "0211_0101": 0},
    )
    result = risk_service.assess_dynamic_and_store(db, request)
    assert result["transparency"]["expectedCount"] == 5
    assert result["engineUsage"]["expertCalls"] == 1
    assert result["completeness"] == 0.6  # 零占比类型的额外输入不能提高覆盖率
    assert "T_LEAF" in result["transparency"]["missingCodes"]


def test_combine_cannot_dilute_veto(db):
    veto = risk_service.assess_dynamic_and_store(db, payload({"T_VETO": "是"}))
    good = risk_service.assess_dynamic_and_store(db, payload({"T_REVENUE": "100"}))
    combined = risk_service._combine_mixed({"01": (0.01, veto), "02": (0.99, good)}, db)
    assert combined["suggestedAmount"] == 0
    assert combined["veto"] == veto["veto"]


def test_empty_input_has_zero_coverage_and_actionable_system_risk(db):
    result = risk_service.assess_dynamic_and_store(db, payload({}))
    assert result["completeness"] == 0
    assert result["transparency"]["confidence"] == 0
    assert result["riskAlerts"][0]["code"] == ""


def test_old_result_contract_is_compatible():
    result = RiskResult.model_validate(
        dict(
            score=800,
            probability=0.1,
            level="低风险",
            suggestedAmount=10,
            suggestedRate=4,
            contributions=[],
            deductions=[],
            advice="历史建议",
        )
    )
    assert result.transparency is None
    assert result.riskAlerts == []


def test_alerts_preserve_multiple_redlines(db):
    db.add(
        IndicatorConfig(
            code="T_VETO2",
            name="第二红线",
            level="基本项",
            category_code="BASIC",
            indicator_type="布尔",
            value_range="是/否",
            is_veto=True,
        )
    )
    db.commit()
    result = risk_service.assess_dynamic_and_store(db, payload({"T_VETO": "是", "T_VETO2": "是"}))
    assert {a["code"] for a in result["riskAlerts"]} == {"T_VETO", "T_VETO2"}
