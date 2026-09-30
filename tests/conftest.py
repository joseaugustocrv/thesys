from pathlib import Path
import pytest


@pytest.fixture
def tmp_path(tmp_path_factory):
    root = tmp_path_factory.mktemp("thesys-test")
    workspace = root / "Thesys Projects"
    workspace.mkdir()
    project = workspace / "test-project"
    project.mkdir()
    return project
