import contextlib

import pytest
from solution import safe_read


@pytest.fixture
def workspace(tmp_path):
    root = tmp_path / "docs"
    (root / "sub").mkdir(parents=True)
    (root / "readme.md").write_text("conteúdo público", encoding="utf-8")
    (root / "sub" / "nested.md").write_text("aninhado", encoding="utf-8")
    (tmp_path / "secret.env").write_text("API_KEY=nao-pode-vazar", encoding="utf-8")
    return root


def test_reads_file_inside_root(workspace):
    assert safe_read(workspace, "readme.md") == "conteúdo público"
    assert safe_read(workspace, "sub/nested.md") == "aninhado"


@pytest.mark.parametrize(
    "attack",
    ["../secret.env", "sub/../../secret.env", "./../secret.env", "sub/../../../etc/passwd"],
)
def test_path_traversal_is_refused(workspace, attack):
    with pytest.raises(PermissionError):
        safe_read(workspace, attack)


def test_absolute_path_is_refused(workspace, tmp_path):
    with pytest.raises(PermissionError):
        safe_read(workspace, str(tmp_path / "secret.env"))


def test_missing_file_inside_root(workspace):
    with pytest.raises(FileNotFoundError):
        safe_read(workspace, "nao-existe.md")


def test_secret_never_leaks(workspace, tmp_path):
    secret = (tmp_path / "secret.env").read_text(encoding="utf-8")
    for attack in ["../secret.env", str(tmp_path / "secret.env")]:
        with contextlib.suppress(PermissionError, FileNotFoundError):
            assert safe_read(workspace, attack) != secret
