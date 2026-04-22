from pathlib import Path


def test_readme_language_switch_links_exist() -> None:
    readme_en = Path("README.md").read_text(encoding="utf-8")
    readme_zh = Path("README.zh-CN.md").read_text(encoding="utf-8")

    assert "(README.zh-CN.md)" in readme_en
    assert "(README.md)" in readme_zh
    assert "## Advanced User Guide" in readme_en
    assert "## 高级用户操作指南" in readme_zh
