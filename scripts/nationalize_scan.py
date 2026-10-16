"""全国化改造扫描（只读，不写库不改文件）

目的：在"东北振兴版 → 全国版"改造前，产出**逐行待改清单**，供人工审核。

扫描对象：docs_archive_20260920/农业及相关产业动态指标搜集体系.xlsx（3,020 条、14 列历史源）
当前 15 列源文件使用适用范围与区域标签，本脚本仅用于旧版复现。

分类规则：
- REGION_FIX  ：「适用区域」列非"全国"（预计 ~3,020 行全部命中，含"东北全境"与细分值）
- TEXT_FIX     ：其他列命中**地区限定词**（东北/黑吉辽/蒙东/黑龙江/吉林/辽宁/内蒙古/
                 呼伦贝尔/北大荒/松嫩/三江平原/长白山），需通用化
- REVIEW       ：其他列命中**特色语义词**（黑土地/寒地/冰雪/人参/冷水鱼/粳稻/亚麻/梅花鹿等），
                 默认保留（地域特色模块），仅当出现在指标名称中时待人工复核
- KEEP         ：无命中

输出：
- 控制台摘要（计数 + 样例）
- data/nationalize_report.csv：逐行明细（Excel 行号 / 指标名 / 命中列 / 原值 / 建议）

用法：
    python scripts/nationalize_scan.py
"""

import argparse
import csv
import re
import sys
from collections import Counter
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parent.parent
XLSX = ROOT / "docs_archive_20260920" / "农业及相关产业动态指标搜集体系.xlsx"
OUT_CSV = ROOT / "data" / "nationalize_report.csv"

# 地区限定词：出现即需通用化（豁免：指标名称中的特殊主体名，报告中标 REVIEW 由人工定夺）
HARD = re.compile(r"东北|黑吉辽|蒙东|黑龙江|吉林|辽宁|内蒙古|呼伦贝尔|北大荒|松嫩|三江平原|长白山")
# 特色语义词：默认保留（地域特色指标），指标名称中出现时待复核
SOFT = re.compile(r"黑土地|黑土|寒地|冰雪|人参|冷水鱼|粳稻|亚麻|梅花鹿|冻土|雪乡|林下")

COLUMNS = [
    "层级",
    "所属类别",
    "指标名称",
    "指标类型",
    "单位",
    "取值说明",
    "数据来源",
    "是否特色指标",
    "风险含义",
    "建议权重",
    "适用区域",
    "是否一票否决",
    "采集周期",
    "评分规则",
]

# 需要做地区词扫描的文本列（适用区域单独处理）
TEXT_COLS = ["指标名称", "取值说明", "数据来源", "风险含义", "评分规则"]


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx", default=str(XLSX), help="待扫描的 xlsx 路径")
    ap.add_argument("--out", default=str(OUT_CSV), help="报告输出路径")
    args = ap.parse_args()

    xlsx_path = Path(args.xlsx)
    out_csv = Path(args.out)

    wb = load_workbook(xlsx_path, read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()

    header = [str(c or "").strip() for c in rows[0]]
    assert header == COLUMNS, f"表头不符: {header}"
    data = [r for r in rows[1:] if r and any(c is not None and str(c).strip() for c in r)]

    region_counter: Counter = Counter()
    report: list[dict] = []
    stat = Counter()

    for idx, r in enumerate(data):
        excel_row = idx + 2  # 数据行在 Excel 中的行号（表头占第 1 行）
        cells = {name: str(r[i] or "").strip() for i, name in enumerate(COLUMNS)}
        region = cells["适用区域"]
        is_feature = cells["是否特色指标"]
        region_counter[region] += 1

        hits: list[tuple[str, str, str]] = []  # (列, 类型, 命中词)
        for col in TEXT_COLS:
            val = cells[col]
            if not val:
                continue
            for m in set(HARD.findall(val)):
                hits.append((col, "HARD", m))
            for m in set(SOFT.findall(val)):
                hits.append((col, "SOFT", m))

        hard_hits = [(col, w) for col, k, w in hits if k == "HARD"]
        soft_hits = [(col, w) for col, k, w in hits if k == "SOFT"]
        region_fix = region != "全国"

        # action 优先级：文本地区词（必须改写）> 区域列 > 指标名中特色词（复核）> 其他特色词（保留）
        if hard_hits:
            action = "TEXT_FIX"
        elif region_fix:
            action = "REGION_FIX"
        elif any(col == "指标名称" for col, _ in soft_hits):
            action = "REVIEW"
        elif soft_hits:
            action = "KEEP_SOFT"
        else:
            action = "KEEP"

        stat[action] += 1
        if action == "KEEP":
            continue

        report.append(
            {
                "excel_row": excel_row,
                "action": action,
                "region_fix": "Y" if region_fix else "",
                "层级": cells["层级"],
                "类别": cells["所属类别"],
                "指标名称": cells["指标名称"],
                "特色": is_feature,
                "适用区域": region,
                "命中列": " / ".join(sorted({c for c, _, _ in hits})),
                "命中类型": " / ".join(sorted({k for _, k, _ in hits})),
                "命中词": " / ".join(sorted({w for _, _, w in hits})),
                "原文": " | ".join(
                    f"{c}={cells[c]}"
                    for c in TEXT_COLS
                    if cells[c] and (HARD.search(cells[c]) or SOFT.search(cells[c]))
                ),
            }
        )

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(report[0].keys()))
        w.writeheader()
        w.writerows(report)

    # ---------- 摘要 ----------
    print(f"扫描: {xlsx_path.name}  数据行: {len(data)}")
    print("\n== 适用区域分布 ==")
    for k, v in region_counter.most_common():
        print(f"  {k!r}: {v}")
    print("\n== 建议分类 ==")
    for k in ("TEXT_FIX", "REVIEW", "REGION_FIX", "KEEP_SOFT", "KEEP"):
        print(f"  {k}: {stat[k]}")
    print(f"\n明细已写入: {out_csv}")
    print("\n== TEXT_FIX 样例（最多 15 条）==")
    shown = 0
    for row in report:
        if row["action"] == "TEXT_FIX":
            print(f"  [{row['excel_row']}] {row['指标名称']} | {row['命中列']} -> {row['原文'][:110]}")
            shown += 1
            if shown >= 15:
                break
    print("\n== REVIEW 样例（最多 10 条）==")
    shown = 0
    for row in report:
        if row["action"] == "REVIEW":
            print(f"  [{row['excel_row']}] {row['指标名称']} | {row['命中词']}")
            shown += 1
            if shown >= 10:
                break


if __name__ == "__main__":
    main()
