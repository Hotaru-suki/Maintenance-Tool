from maintenancetool.ui import confirm


def test_prompt_yes_no_uses_explicit_uppercase_prompt(monkeypatch) -> None:
    prompts: list[str] = []

    def fake_prompt(message: str, **_: object) -> str:
        prompts.append(message)
        return "y"

    monkeypatch.setattr(confirm.typer, "prompt", fake_prompt)

    assert confirm.prompt_yes_no("Proceed?") is True
    assert prompts == ["Proceed? [Y/N]"]


def test_parse_yes_no_accepts_only_y_or_n() -> None:
    assert confirm.parse_yes_no("Y") is True
    assert confirm.parse_yes_no("y") is True
    assert confirm.parse_yes_no("N") is False
    assert confirm.parse_yes_no("n") is False
    assert confirm.parse_yes_no("") is None
    assert confirm.parse_yes_no("yes") is None
    assert confirm.parse_yes_no("no") is None
    assert confirm.parse_yes_no("1") is None
