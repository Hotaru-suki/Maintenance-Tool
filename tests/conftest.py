from __future__ import annotations

from pathlib import Path

import pytest

from tests.helpers.cli import TEST_SCOPE_NAME, runner as cli_runner
from tests.helpers.runtime_workspace import create_runtime_workspace
from tests.helpers.sandbox_factory import SandboxFactory


@pytest.fixture
def runner():
    return cli_runner


@pytest.fixture
def test_scope_name() -> str:
    return TEST_SCOPE_NAME


@pytest.fixture
def sandbox_factory(tmp_path):
    factory = SandboxFactory(tmp_path)
    yield factory
    factory.cleanup()


@pytest.fixture
def runtime_workspace(tmp_path):
    return create_runtime_workspace(tmp_path)


def pytest_collection_modifyitems(config, items) -> None:
    layer_markers = ("core", "cli", "matrix", "integration", "release")
    for item in items:
        path = Path(str(item.fspath))
        parts = path.parts
        for marker_name in layer_markers:
            if marker_name in parts:
                item.add_marker(getattr(pytest.mark, marker_name))
                break
