from app.services.indicator_regions import (
    CONFIGURABLE,
    NATIONAL,
    NORTHEAST_EXAMPLE,
    normalize_region,
    normalize_tag_values,
    parse_region_tags,
)


def test_legacy_northeast_scope_is_national_for_non_feature_indicators():
    assert normalize_region("东北全境", False) == (NATIONAL, [])


def test_legacy_national_scope_stays_national_including_feature_indicators():
    assert normalize_region("全国", False) == (NATIONAL, [])
    assert normalize_region("全国", True) == (NATIONAL, [])


def test_northeast_feature_is_retained_as_configurable_example():
    scope, tags = normalize_region("黑吉辽+蒙东", True)
    assert scope == NORTHEAST_EXAMPLE
    assert tags == ["东北农业区", "黑龙江", "吉林", "辽宁", "内蒙古东部"]


def test_province_specific_legacy_scope_is_configurable():
    scope, tags = normalize_region("仅辽宁鞍山", False)
    assert scope == CONFIGURABLE
    assert tags == ["辽宁", "鞍山市"]


def test_region_tags_accept_common_delimiters_and_drop_placeholder():
    assert normalize_tag_values("黄淮海农业区；河南,山东、河南；—") == [
        "黄淮海农业区",
        "河南",
        "山东",
    ]


def test_neutral_northeast_label_expands_to_province_and_region_tags():
    assert parse_region_tags("东北全境") == [
        "东北农业区",
        "黑龙江",
        "吉林",
        "辽宁",
        "内蒙古东部",
    ]
