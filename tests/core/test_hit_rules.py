from maintenancetool.core.hit_rules import match_discovery_candidate


def test_match_discovery_candidate_matches_cache_name() -> None:
    result = match_discovery_candidate(
        logical_path=r"C:\Users\Alice\AppData\Local\Demo\Cache",
        root_category=None,
    )

    assert result.matched is True
    assert result.category == "browser-cache"
    assert result.rule_id == "name-browser-cache"


def test_match_discovery_candidate_uses_root_category_fallback() -> None:
    result = match_discovery_candidate(
        logical_path=r"C:\Users\Alice\AppData\Local\Temp\Vendor\Work",
        root_category="temp",
    )

    assert result.matched is True
    assert result.category == "temp"
    assert result.rule_id == "path-temp-local-temp"
