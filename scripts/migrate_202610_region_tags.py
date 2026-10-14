"""为既有 indicator_config 增加区域标签并迁移旧东北适用范围。

用法：python scripts/migrate_202610_region_tags.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import inspect, text  # noqa: E402

from app.db.session import SessionLocal, engine  # noqa: E402
from app.models.indicator import IndicatorConfig  # noqa: E402
from app.services.indicator_regions import normalize_region, normalize_tag_values  # noqa: E402


def main() -> None:
    columns = {column["name"] for column in inspect(engine).get_columns("indicator_config")}
    if "region_tags" not in columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE indicator_config ADD COLUMN region_tags JSON"))
        print("已添加 indicator_config.region_tags JSON 列")
    else:
        print("indicator_config.region_tags 已存在")

    updated = 0
    with SessionLocal() as db:
        rows = db.query(IndicatorConfig).all()
        for row in rows:
            scope, inferred_tags = normalize_region(row.region, row.is_feature)
            tags = normalize_tag_values(row.region_tags or inferred_tags)
            if row.region != scope or row.region_tags != tags:
                row.region = scope
                row.region_tags = tags
                updated += 1
        db.commit()
    print(f"区域范围已标准化，更新 {updated} 条指标")


if __name__ == "__main__":
    main()
