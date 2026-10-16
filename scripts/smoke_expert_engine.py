"""全国化重灌后的专家引擎冒烟回归（本地直连 race3 库，不经 HTTP）

复刻 scripts/test_20_scenarios.py 的代表性场景，与 2026-09-15 验证快照对比：
    01 优质 → 826 低风险 / 01 差 → 162 高风险 / 混合 01+02 → 497 / 一票否决 → 200 高风险
若评分一致，说明全国化数据改造未影响评分逻辑。

用法：
    python scripts/smoke_expert_engine.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DATABASE_URL", "mysql+pymysql://root:race123456@127.0.0.1:3307/race?charset=utf8mb4")

from app.db.session import SessionLocal  # noqa: E402
from app.ml.expert_engine import expert_assess  # noqa: E402

CASES = [
    (
        "01 农林牧渔业·优质   [期望 ≈826 低风险]",
        "01",
        {
            "BASIC_003": "25",
            "BASIC_004": "25",
            "BASIC_005": "80",
            "BASIC_008": "480",
            "BASIC_009": "20",
            "01_05": "2600",
            "0111_01": "2400",
        },
        None,
    ),
    (
        "01 农林牧渔业·中等",
        "01",
        {"BASIC_003": "8", "BASIC_004": "7", "BASIC_005": "15", "BASIC_008": "120", "BASIC_009": "55", "01_05": "600"},
        None,
    ),
    (
        "01 农林牧渔业·差     [期望 ≈162 高风险]",
        "01",
        {"BASIC_003": "1", "BASIC_004": "1", "BASIC_005": "2", "BASIC_008": "8", "BASIC_009": "88", "01_05": "30"},
        None,
    ),
    (
        "混合 01+02·产销一体   [期望 ≈497]",
        "MIXED",
        {"BASIC_003": "10", "BASIC_004": "10", "BASIC_005": "45", "BASIC_008": "380", "BASIC_009": "35"},
        {"01": 0.6, "02": 0.4},
    ),
    ("一票否决·失信被执行人 [期望 200 高风险]", "01", {"BASIC_003": "15", "BASIC_008": "400", "BASIC_013": "是"}, None),
    (
        "02 食用加工·优质",
        "02",
        {"BASIC_003": "18", "BASIC_004": "18", "BASIC_005": "90", "BASIC_008": "480", "BASIC_009": "25"},
        None,
    ),
]


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    db = SessionLocal()
    try:
        for title, bt, ind, mixed in CASES:
            r = expert_assess(db, bt, ind, mixed_business=mixed)
            veto = f" | veto={r['veto']}" if r.get("veto") else ""
            print(f"{title}")
            print(
                f"    score={r['score']}  level={r['level']}  prob={r['probability']:.3f}"
                f"  completeness={r['completeness']:.2f}{veto}"
            )
    finally:
        db.close()


if __name__ == "__main__":
    main()
