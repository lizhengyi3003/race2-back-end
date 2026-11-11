"""Initialize a fresh database without overwriting an existing indicator catalogue."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.import_indicators import build, parse_rows

from app.db.init_db import full_init
from app.db.session import SessionLocal
from app.models.indicator import IndicatorCategory, IndicatorConfig


def main():
    full_init()
    with SessionLocal() as db:
        if db.query(IndicatorConfig).count():
            print("Existing indicators preserved; bootstrap skipped.")
            return
        categories, indicators = build(parse_rows(Path("deploy/indicators.xlsx")))
        db.add_all(IndicatorCategory(**row) for row in categories)
        db.add_all(IndicatorConfig(**row) for row in indicators)
        db.commit()
        print(f"Initialized {len(categories)} categories and {len(indicators)} indicators.")
    full_init()


if __name__ == "__main__":
    main()
