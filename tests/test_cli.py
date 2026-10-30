from pathlib import Path

import pytest

from japyd.cli import main, skill_source, skill_target


def test_skill_source():
    assert skill_source().startswith("---\nname: japyd\n")


def test_skill_target(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    assert skill_target() == tmp_path / ".claude/skills/japyd/SKILL.md"
    assert skill_target(user=True) == tmp_path / "home/.claude/skills/japyd/SKILL.md"
    assert skill_target(directory=Path("other")) == Path("other/japyd/SKILL.md")


def test_install(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    target = tmp_path / ".claude/skills/japyd/SKILL.md"

    assert main(["install"]) == 0
    assert target.read_text() == skill_source()
    assert "installed" in capsys.readouterr().out

    assert main(["install"]) == 0
    assert "up to date" in capsys.readouterr().out


def test_install_dir(tmp_path):
    assert main(["install", "--dir", str(tmp_path / ".agents/skills")]) == 0
    assert (tmp_path / ".agents/skills/japyd/SKILL.md").read_text() == skill_source()


def test_install_modified(tmp_path, capsys):
    target = tmp_path / "japyd/SKILL.md"
    target.parent.mkdir()
    target.write_text("modified")

    assert main(["install", "--dir", str(tmp_path)]) == 1
    assert "--force" in capsys.readouterr().err
    assert target.read_text() == "modified"

    assert main(["install", "--dir", str(tmp_path), "--force"]) == 0
    assert target.read_text() == skill_source()


def test_show(capsys):
    assert main(["show"]) == 0
    assert capsys.readouterr().out == skill_source()


def test_user_and_dir_exclusive():
    with pytest.raises(SystemExit):
        main(["install", "--user", "--dir", "x"])
