"""标准化指标适用范围，并从旧区域描述保留可筛选标签。"""

from __future__ import annotations

import re

NATIONAL = "全国通用"
CONFIGURABLE = "区域可配置"
NORTHEAST_EXAMPLE = "示例：东北"
REGION_SCOPES = (NATIONAL, CONFIGURABLE, NORTHEAST_EXAMPLE)

_NORTHEAST_TAGS = ["东北农业区", "黑龙江", "吉林", "辽宁", "内蒙古东部"]


def parse_region_tags(value: str | None) -> list[str]:
    """把旧的加号区域写法转成稳定、省级或农业区标签列表。"""
    raw = str(value or "").strip()
    if not raw or raw in {"—", "全国", NATIONAL}:
        return []
    if raw in {"东北全境", "黑吉辽+蒙东", "东北农业区"}:
        return _NORTHEAST_TAGS.copy()

    normalized = raw.replace("＋", "+").replace("，", "+").replace("、", "+")
    normalized = re.sub(r"^仅", "", normalized)
    tags: list[str] = []
    if "黑龙江" in normalized or "黑" in normalized:
        tags.append("黑龙江")
    if "吉林" in normalized or "吉" in normalized:
        tags.append("吉林")
    if "辽宁" in normalized or "辽" in normalized:
        tags.append("辽宁")
    if "蒙东" in normalized or "内蒙古" in normalized:
        tags.append("内蒙古东部" if "蒙东" in normalized else "内蒙古")
    if "鞍山" in normalized:
        tags.append("鞍山市")
    if "盘锦" in normalized:
        tags.append("盘锦市")
    if any(term in normalized for term in ("农垦", "森工")):
        tags.append("农垦/森工体系")
    if "黑龙江" in tags and "吉林" in tags and ("辽宁" in tags or "内蒙古东部" in tags):
        tags.insert(0, "东北农业区")
    return list(dict.fromkeys(tags))


def normalize_region(value: str | None, is_feature: bool) -> tuple[str, list[str]]:
    """把历史区域值折叠到三个范围标签，同时保留适用省份/农业区。"""
    raw = str(value or "").strip()
    if raw in {"全国", NATIONAL}:
        return NATIONAL, []
    if raw == CONFIGURABLE:
        return CONFIGURABLE, []
    if raw == NORTHEAST_EXAMPLE:
        return NORTHEAST_EXAMPLE, _NORTHEAST_TAGS.copy()

    tags = parse_region_tags(raw)
    if is_feature:
        return NORTHEAST_EXAMPLE, tags or _NORTHEAST_TAGS.copy()
    if raw in {"", "东北全境"}:
        return NATIONAL, []
    return CONFIGURABLE, tags


def normalize_tag_values(value: str | list[str] | None) -> list[str]:
    """清理管理端或导入表中的标签，接受逗号、分号和顿号分隔。"""
    if isinstance(value, list):
        values = value
    else:
        values = re.split(r"[;,，；、\n]+", str(value or ""))
    cleaned = (tag.strip() for tag in values)
    return list(dict.fromkeys(tag for tag in cleaned if tag and tag not in {"—", "-"}))
