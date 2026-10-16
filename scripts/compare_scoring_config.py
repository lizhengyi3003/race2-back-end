"""对比改造前（备份 dump）与改造后（当前库）的 scoring_config 分布

目的：确认重灌后评分配置链条与改造前一致（是否有遗漏的后置脚本）。

用法：
    python scripts/compare_scoring_config.py
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

import pymysql

ROOT = Path(__file__).resolve().parent.parent
BACKUP = ROOT / "data" / "race_national_backup.sql"

INSERT_RE = re.compile(r"\((\d+),'([^']+)',")  # (id,'code',...


def parse_cfg(raw: str):
    """SQL 字面量 → Python 对象。dump 中 JSON 含 \\" 转义；当前库返回 JSON 文本。"""
    s = raw.strip()
    if s.startswith("'"):
        s = s[1:-1]
    s = s.replace('\\"', '"').replace("\\'", "'").replace("\\\\", "\\")
    if s in ("", "NULL"):
        return None
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return {"__raw__": s}


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    text = BACKUP.read_text(encoding="utf-8", errors="ignore")

    # ---- 改造前：从 dump 提取每条指标的 scoring_config（第 19 列，倒数第二个字段）----
    old_cfg: dict[str, object] = {}
    for line in text.splitlines():
        if "INSERT INTO `indicator_config`" not in line:
            continue
        body = line.split("VALUES", 1)[1]
        for t in body.split("),("):
            t = t.strip().strip(";").strip("()")
            m = re.match(r"(\d+),'([^']+)',", t)
            if not m:
                continue
            code = m.group(2)
            # scoring_config = 倒数第二个字段，格式 ,'{...}',<display_order>
            # 注意 JSON 内部含逗号，必须用正则从右端定位（贪婪匹配到最后一个 '}')
            m2 = re.search(r",'(\{.*\})',(\d+)$", t)
            old_cfg[code] = parse_cfg(m2.group(1)) if m2 else None

    # ---- 改造后：查库 ----
    conn = pymysql.connect(
        host="127.0.0.1", port=3307, user="root", password="race123456", database="race", charset="utf8mb4"
    )
    with conn.cursor() as cur:
        cur.execute("SELECT code, IFNULL(scoring_config, 'NULL') FROM indicator_config")
        new_cfg = {c: parse_cfg(v) for c, v in cur.fetchall()}
    conn.close()

    def summarize(cfgs: dict[str, object], label: str) -> None:
        cnt: Counter = Counter()
        for v in cfgs.values():
            if v is None:
                cnt["空"] += 1
                continue
            cnt["非空"] += 1
            if isinstance(v, dict):
                if "max" in v:
                    cnt["max"] += 1
                if "map" in v:
                    cnt["map"] += 1
                if "lower_better" in v:
                    cnt["lower_better"] += 1
        print(f"\n[{label}] 总 {len(cfgs)} 条")
        for k in ("非空", "空", "max", "map", "lower_better"):
            print(f"   {k}: {cnt[k]}")

    summarize(old_cfg, "改造前（备份 dump）")
    summarize(new_cfg, "改造后（当前库）")

    # ---- 逐 code 差异（JSON 对象级比较）----
    both = set(old_cfg) & set(new_cfg)
    diff = [c for c in both if old_cfg[c] != new_cfg[c]]
    print(f"\n共同 code: {len(both)}，scoring_config 不同的: {len(diff)}")
    for c in sorted(diff)[:25]:
        print(
            f"   [{c}] old={json.dumps(old_cfg[c], ensure_ascii=False)}"
            f"  →  new={json.dumps(new_cfg[c], ensure_ascii=False)}"
        )
    if len(diff) > 25:
        print(f"   ... 共 {len(diff)} 条")


if __name__ == "__main__":
    main()
