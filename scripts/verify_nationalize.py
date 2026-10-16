"""全国化重灌验证

检查项：
1. 改造前（备份 dump）与改造后（当前库）的指标 code 集合是否一致（行序稳定 → code 稳定）
2. 名称变化清单（应仅限全国化改写的 5 条指标名）
3. region 分布（应全部为"全国"）
4. indicator_value 历史记录能否全部关联到现有指标（code 稳定性的直接证据）
5. 抽查代表性指标（补贴类 / 名称改写类 / 特色保留类）

用法：
    python scripts/verify_nationalize.py
    python scripts/verify_nationalize.py --backup data/race_national_backup.sql
"""

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

import pymysql

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BACKUP = ROOT / "data" / "race_national_backup.sql"

INSERT_RE = re.compile(r"\((\d+),'([^']+)',")  # 元组 (id,'code',...


def read_backup_codes(path: Path) -> set[str]:
    """从备份 SQL 提取改造前全部 code（mysqldump 默认 extended-insert：多条记录同一行）"""
    codes: set[str] = set()
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "INSERT INTO `indicator_config`" not in line:
            continue
        for m in INSERT_RE.finditer(line):
            codes.add(m.group(2))
    return codes


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    ap = argparse.ArgumentParser()
    ap.add_argument("--backup", default=str(DEFAULT_BACKUP))
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=3307)
    ap.add_argument("--user", default="root")
    ap.add_argument("--password", default="race123456")
    ap.add_argument("--db", default="race")
    args = ap.parse_args()

    old_set = read_backup_codes(Path(args.backup))
    conn = pymysql.connect(
        host=args.host, port=args.port, user=args.user, password=args.password, database=args.db, charset="utf8mb4"
    )
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT code, name, region, is_feature FROM indicator_config")
            rows = cur.fetchall()
    finally:
        conn.close()

    new_codes = {r[0] for r in rows}

    print(f"改造前 code 数: {len(old_set)}")
    print(f"改造后 code 数: {len(new_codes)}")
    missing = old_set - new_codes
    added = new_codes - old_set
    print(f"消失的 code: {len(missing)} {sorted(missing)[:5] if missing else ''}")
    print(f"新增的 code: {len(added)} {sorted(added)[:5] if added else ''}")

    regions = Counter(r[2] for r in rows)
    print(f"\nregion 分布: {dict(regions)}")
    non_national = [(r[0], r[1], r[2]) for r in rows if r[2] != "全国"]
    if non_national:
        print(f"[warn] 非'全国'的指标 {len(non_national)} 条，样例: {non_national[:5]}")
    else:
        print("region 全部为'全国' ✓")

    feat = sum(1 for r in rows if r[3])
    print(f"特色指标: {feat}")

    # 历史评估记录关联（code 稳定性证据）
    conn = pymysql.connect(
        host=args.host, port=args.port, user=args.user, password=args.password, database=args.db, charset="utf8mb4"
    )
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM indicator_value")
            total = cur.fetchone()[0]
            cur.execute(
                "SELECT COUNT(*) FROM indicator_value v "
                "LEFT JOIN indicator_config c ON v.indicator_code = c.code "
                "WHERE c.code IS NULL"
            )
            orphan = cur.fetchone()[0]
            cur.execute(
                "SELECT code, name, region, value_range, risk_meaning FROM indicator_config "
                "WHERE code IN ('BASIC_007','BASIC_025','0111_04','0112_03','0113_0133_01')"
            )
            samples = cur.fetchall()
    finally:
        conn.close()
    print(f"\nindicator_value 总数: {total}，无法关联的: {orphan} {'✓' if orphan == 0 else '[err]'}")

    print("\n== 抽查 ==")
    for code, name, region, vr, rm in samples:
        print(f"  [{code}] {name} | {region}")
        print(f"      取值说明: {vr}")
        if rm:
            print(f"      风险含义: {rm}")

    print("\n== 名称改写指标核查 ==")
    renamed_keywords = [
        "民俗工艺品产量",
        "农业务工劳务服务规模",
        "人居环境整治覆盖村数",
        "品牌广告服务额",
        "农垦/森工体系内主体",
    ]
    renamed = [(r[0], r[1]) for r in rows if any(s in r[1] for s in renamed_keywords)]
    for code, name in renamed:
        print(f"  [{code}] {name}")


if __name__ == "__main__":
    main()
