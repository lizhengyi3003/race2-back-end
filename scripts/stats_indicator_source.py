"""统计指标库的「数据来源」构成，判断哪些指标可由调查数据（CFPS/CHFS/CMES）支撑。

用法：
    python scripts/stats_indicator_source.py
"""

import sys

import pymysql

CONN = dict(host="127.0.0.1", port=3307, user="root", password="race123456", database="race", charset="utf8mb4")

# 来源分类口径（按关键短语归并）
BUCKETS = [
    ("台账/报表/流水（经营记录）", ("台账", "报表", "流水", "记录", "单据", "凭证")),
    ("合同/订单（业务凭证）", ("合同", "订单", "协议")),
    ("主管部门/系统（外部数据）", ("部门", "系统", "网", "监管", "公示")),
    ("现场核查/走访（人工采集）", ("核查", "走访", "调查", "问卷", "观察", "评价")),
    ("征信/司法/税务（合规红线）", ("征信", "司法", "税务", "执行信息", "处罚")),
    ("保险/补贴（政策数据）", ("保险", "补贴", "补助", "财政")),
    ("质检/证书/资质", ("质检", "证书", "资质", "认证", "检疫", "检测")),
]


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    conn = pymysql.connect(**CONN)
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(DISTINCT data_source) FROM indicator_config")
        print(f"不同来源字符串种类: {cur.fetchone()[0]}")
        cur.execute("SELECT COUNT(*) FROM indicator_config")
        total = cur.fetchone()[0]
        print(f"指标总数: {total}\n")

        print("== 按来源归类 ==")
        for label, kws in BUCKETS:
            cond = " OR ".join(["data_source LIKE %s"] * len(kws))
            params = [f"%{k}%" for k in kws]
            cur.execute(f"SELECT COUNT(*) FROM indicator_config WHERE {cond}", params)
            n = cur.fetchone()[0]
            print(f"  {label:<24} {n:>5}  ({n / total:.1%})")

        print("\n== 含『调查/问卷』字样的来源（最具调查数据可支撑潜力）==")
        cur.execute(
            "SELECT data_source, COUNT(*) FROM indicator_config "
            "WHERE data_source LIKE %s OR data_source LIKE %s OR data_source LIKE %s "
            "GROUP BY data_source ORDER BY 2 DESC LIMIT 15",
            ("%调查%", "%问卷%", "%样本%"),
        )
        rows = cur.fetchall()
        if not rows:
            print("  （无）")
        for ds, n in rows:
            print(f"  {n:>4}  {ds}")
    conn.close()


if __name__ == "__main__":
    main()
