from pathlib import Path

from maintenancetool.core.config_loader import load_all_configs


TEMPLATE_DIR = Path("packaging/config_templates")


def test_packaged_templates_load_as_valid_default_profile() -> None:
    configs = load_all_configs(TEMPLATE_DIR)

    assert len(configs["fixedTargets"]) >= 4
    assert len(configs["denyRules"]) >= 4
    assert configs["discover"].defaultDepth == 1
    assert configs["discover"].maxDepth == 2
    assert configs["learning"].newItemPolicy.promoteNewPaths is True


def test_packaged_templates_keep_default_targets_in_cache_and_logs_scope() -> None:
    configs = load_all_configs(TEMPLATE_DIR)

    allowed_categories = {"temp", "browser-cache", "logs"}
    protected_keywords = {"desktop", "documents", "downloads", "pictures", "videos"}

    for target in configs["fixedTargets"]:
        assert target.category in allowed_categories
        normalized_path = target.path.lower()
        assert not any(keyword in normalized_path for keyword in protected_keywords)
        assert target.deleteMode == "contents"


def test_packaged_templates_keep_safety_policy_conservative() -> None:
    configs = load_all_configs(TEMPLATE_DIR)
    safety_policy = configs["learning"].safetyPolicy

    assert safety_policy.refuseSymlinks is True
    assert safety_policy.requireManualConfirmForLearnedTargets is True
    assert safety_policy.requireManualConfirmAboveBytes >= 512 * 1024 * 1024
    assert safety_policy.maxItemsPerRun <= 50
    assert safety_policy.maxBytesPerRun <= 2 * 1024 * 1024 * 1024
    assert len(safety_policy.allowedRoots) >= 1


def test_packaged_templates_keep_learning_thresholds_non_aggressive() -> None:
    configs = load_all_configs(TEMPLATE_DIR)
    learning = configs["learning"]

    assert learning.newItemPolicy.minBytes >= 1024 * 1024
    assert learning.changePolicy.sizeDeltaBytes >= 32 * 1024 * 1024
    assert learning.changePolicy.sizeDeltaRatio >= 0.5
    assert learning.stalePolicy.missingCountThreshold >= 3
