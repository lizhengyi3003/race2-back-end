"""核实"旧 SQL 775 条"（data/indicator_dump.sql）与当前 3,020 条体系的关系。

输出：
1. 旧 dump 指标数、层级分布
2. 775 个 code 在当前库中的匹配情况（完全一致 / 仅 code 同 / 不存在）
3. 当前库前 4 级（基本项+大类+中类+小类）数量，与旧 dump 对比

用法：
    python scripts/compare_legacy_dump.py
"""

import re
import sys
from collections import Counter
from pathlib import Path

import pymysql

ROOT = Path(__file__).resolve().parent.parent
LEGACY = ROOT / "data" / "indicator_dump.sql"

# 旧 dump 为逐条 INSERT：(id,'code','name','level','category_code',...
ROW_RE = re.compile(r"VALUES \((\d+),'([^']+)','([^']+)','([^']+)','([^']+)',")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    old: dict[str, tuple[str, str, str]] = {}  # code -> (name, level, category_code)
    for line in LEGACY.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "INSERT INTO `indicator_config`" not in line:
            continue
        m = ROW_RE.search(line)
        if m:
            _id, code, name, level, cat = m.groups()
            old[code] = (name, level, cat)

    print(f"旧 dump 指标数: {len(old)}")
    print(f"旧 dump 层级分布: {dict(Counter(v[1] for v in old.values()))}")

    conn = pymysql.connect(
        host="127.0.0.1", port=3307, user="root", password="race123456", database="race", charset="utf8mb4"
    )
    with conn.cursor() as cur:
        cur.execute("SELECT code, name, level FROM indicator_config")
        new = {c: (n, lv) for c, n, lv in cur.fetchall()}
    conn.close()

    print(f"\n当前库指标数: {len(new)}")
    print(f"当前库层级分布: {dict(Counter(v[1] for v in new.values()))}")

    exact = same_code_diff_name = missing = 0
    diff_names: list[tuple[str, str, str]] = []
    for code, (name, _level, _cat) in old.items():
        if code not in new:
            missing += 1
        elif new[code][0] == name:
            exact += 1
        else:
            same_code_diff_name += 1
            diff_names.append((code, name, new[code][0]))

    print("\n== 旧 775 条在当前库中的匹配 ==")
    print(f"  code+名称完全一致: {exact}")
    print(f"  code 存在但名称不同: {same_code_diff_name}")
    for code, o, n in diff_names[:15]:
        print(f"    [{code}] 旧='{o}'  新='{n}'")
    print(f"  code 不存在于当前库: {missing}")


if __name__ == "__main__":
    main()
