from __future__ import annotations

from pathlib import Path


TEST_ROOT = Path("tests")
ALLOWED_TEST_LAYERS = {"core", "cli", "matrix", "integration", "release"}
ALLOWED_TOP_LEVEL = {"__init__.py", "conftest.py"}


def test_all_top_level_test_files_are_framework_files_only() -> None:
    files = {
        path.name
        for path in TEST_ROOT.iterdir()
        if path.is_file()
    }

    assert files == ALLOWED_TOP_LEVEL


def test_all_test_modules_live_under_known_layers() -> None:
    for path in TEST_ROOT.rglob("test_*.py"):
        relative = path.relative_to(TEST_ROOT)
        assert relative.parts[0] in ALLOWED_TEST_LAYERS


def test_support_compat_layer_is_removed() -> None:
    assert not (TEST_ROOT / "support.py").exists()


def test_no_test_imports_removed_support_layer() -> None:
    current_file = Path(__file__).resolve()
    for path in TEST_ROOT.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        if path.resolve() == current_file:
            continue
        text = path.read_text(encoding="utf-8")
        assert "tests.support" not in text
