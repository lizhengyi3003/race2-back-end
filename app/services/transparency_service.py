"""评估解释快照：配置来源、有效覆盖率及可定位风险原因。

来源指配置声明的采集渠道，不声称本次输入已经外部核验。
有效覆盖率只衡量输入对当前指标体系的覆盖，不代表模型准确率。
"""

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.ml.expert_engine import _check_veto, describe_scoring, score_indicator
from app.models.indicator import IndicatorConfig


def expected_indicators(db: Session, payload: dict) -> list[IndicatorConfig]:
    categories = set(payload.get("selectedCategories") or [])
    business_type = payload.get("businessType") or ""
    if business_type and business_type != "MIXED":
        categories.add(business_type)
    if business_type == "MIXED":
        categories.update(code for code, ratio in (payload.get("mixedBusiness") or {}).items() if ratio > 0)
    paths = set()
    for code in categories:
        small = code.split("_")[0]
        paths.update((code, small, small[:3], small[:2]))
    return (
        db.query(IndicatorConfig)
        .filter(or_(IndicatorConfig.level == "基本项", IndicatorConfig.category_code.in_(paths)))
        .order_by(IndicatorConfig.display_order, IndicatorConfig.code)
        .all()
    )


def enrich_result(db: Session, payload: dict, result: dict) -> dict:
    """在落库之前补齐解释，使即时结果和历史记录使用同一快照。"""
    values = payload.get("indicators") or {}
    expected = expected_indicators(db, payload)
    expected_codes = {c.code for c in expected}
    # 已提交的额外配置也展示来源，但不增加期望集/覆盖率分子。
    extras = (
        db.query(IndicatorConfig)
        .filter(IndicatorConfig.code.in_(set(values) - expected_codes))
        .order_by(IndicatorConfig.display_order, IndicatorConfig.code)
        .all()
    )
    contributions: dict[str, list[dict]] = {}
    for contribution in result.get("contributions") or []:
        code = contribution.get("code")
        if code:
            contributions.setdefault(code, []).append(contribution)

    rows = []
    missing = []
    alerts = []
    provided_count = valid_count = eligible_count = scored_count = 0
    for config in expected + extras:
        raw = values.get(config.code)
        value = str(raw).strip() if raw is not None else ""
        present = bool(value)
        eligible = config.indicator_type != "文本"
        evaluated_score = score_indicator(value, config) if present else None
        valid = present and (not eligible or evaluated_score is not None)
        hit_veto = config.is_veto and _check_veto({config.code: value}, {config.code: config}) is not None
        items = contributions.get(config.code) or []
        weight = sum(c["weight"] for c in items) if items else None
        score = round(sum(c["score"] * c["weight"] for c in items) / weight, 1) if items and weight else None
        if config.code in expected_codes:
            provided_count += int(present)
            eligible_count += int(eligible)
            valid_count += int(eligible and valid)
            scored_count += int(bool(items))
            if not present:
                missing.append(config.code)
        status = "missing" if not present else "invalid" if not valid else "provided" if items else "unscored"
        rows.append(
            {
                "code": config.code,
                "name": config.name,
                "level": config.level,
                "unit": config.unit,
                "value": value if present else None,
                "dataSource": config.data_source or "未配置采集来源",
                "riskMeaning": config.risk_meaning or "未配置评分用途",
                "scoringRule": describe_scoring(config),
                "score": score,
                "weight": round(weight, 4) if weight is not None else None,
                "status": status,
            }
        )
        if hit_veto:
            alerts.append(
                {
                    "code": config.code,
                    "factor": config.name,
                    "severity": "veto",
                    "reason": f"命中一票否决：{config.risk_meaning or config.name}。不予授信，需核验并处理后重新评估。",
                    "score": None,
                }
            )
        elif score is not None and score < 40:
            alerts.append(
                {
                    "code": config.code,
                    "factor": config.name,
                    "severity": "high",
                    "reason": (
                        f"该项得分 {score:g}/100，低于高风险提示阈值 40。"
                        f"{config.risk_meaning or '需人工复核该项经营风险'}。"
                    ),
                    "score": score,
                }
            )
    if not alerts and result.get("level") == "高风险":
        alerts.append({"code": "", "factor": "综合评估", "severity": "high", "reason": result["advice"], "score": None})
    completeness = round(provided_count / len(expected), 4) if expected else 0.0
    confidence = round(valid_count / eligible_count, 4) if eligible_count else 0.0
    result["completeness"] = completeness
    result["riskAlerts"] = alerts
    result["transparency"] = {
        "expectedCount": len(expected),
        "providedCount": provided_count,
        "scoredCount": scored_count,
        "missingCodes": missing,
        "confidence": confidence,
        "confidenceLabel": "覆盖充分" if confidence >= 0.8 else "覆盖一般" if confidence >= 0.5 else "覆盖不足",
        "confidenceExplanation": (
            f"本次可评估指标 {eligible_count} 项，有效输入 {valid_count} 项（含否决核验）；"
            "有效数据覆盖率反映评估依据的充分程度，不代表预测准确率。"
            "来源为配置的采集渠道，本次数据仍需核验；补充有效数据可提高覆盖率。"
        ),
        "indicators": rows,
    }
    return result
