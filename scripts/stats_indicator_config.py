"""统计指标配置覆盖率（任务书用）：类型分布 / 数值 max 覆盖 / 枚举 map 覆盖。

用法：
    python scripts/stats_indicator_config.py
"""

import sys

import pymysql

CONN = dict(host="127.0.0.1", port=3307, user="root", password="race123456", database="race", charset="utf8mb4")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    conn = pymysql.connect(**CONN)
    with conn.cursor() as cur:
        print("== 指标类型分布 ==")
        cur.execute(
            "SELECT indicator_type, COUNT(*) FROM indicator_config GROUP BY indicator_type ORDER BY COUNT(*) DESC"
        )
        for t, n in cur.fetchall():
            print(f"   {t}: {n}")

        cur.execute("SELECT COUNT(*) FROM indicator_config")
        print(f"   合计: {cur.fetchone()[0]}")

        cur.execute("SELECT COUNT(*) FROM indicator_config WHERE indicator_type='数值'")
        total_num = cur.fetchone()[0]
        cur.execute(
            "SELECT COUNT(*) FROM indicator_config "
            "WHERE indicator_type='数值' AND JSON_EXTRACT(scoring_config,'$.max') IS NOT NULL"
        )
        has_max = cur.fetchone()[0]
        print("\n== 数值指标参考上限（max）覆盖 ==")
        print(f"   数值总数 {total_num} | 含 max {has_max} | 缺 max {total_num - has_max}")

        cur.execute("SELECT COUNT(*) FROM indicator_config WHERE indicator_type='枚举'")
        total_enum = cur.fetchone()[0]
        cur.execute(
            "SELECT COUNT(*) FROM indicator_config "
            "WHERE indicator_type='枚举' AND JSON_EXTRACT(scoring_config,'$.map') IS NOT NULL"
        )
        has_map = cur.fetchone()[0]
        print("\n== 枚举指标档位映射（map）覆盖 ==")
        print(f"   枚举总数 {total_enum} | 含 map {has_map} | 缺 map {total_enum - has_map}")

        cur.execute(
            "SELECT COUNT(*) FROM indicator_config WHERE JSON_EXTRACT(scoring_config,'$.lower_better') IS NOT NULL"
        )
        print(f"\n   含 lower_better 方向配置: {cur.fetchone()[0]}")
    conn.close()


if __name__ == "__main__":
    main()
