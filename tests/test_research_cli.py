"""CLI setup tests never touch authentication or run a model."""
from types import SimpleNamespace
import sys

import pytest

import research_cli
from core import research_runtime


def test_check_uses_explicit_profile_and_restores_environment(monkeypatch, capsys):
    monkeypatch.setenv("QUANT_CODEX_HOME", "/original-profile")
    seen = []

    class Runtime:
        async def readiness(self):
            seen.append(research_cli.os.environ["QUANT_CODEX_HOME"])
            return {"authenticated": True, "live_research_tested": False}

    monkeypatch.setattr(research_runtime, "CodexResearchRuntime", Runtime)
    assert research_cli.main(["check", "--codex-home", "/selected-profile"]) == 0
    assert seen == ["/selected-profile"]
    assert research_cli.os.environ["QUANT_CODEX_HOME"] == "/original-profile"
    output = capsys.readouterr().out
    assert '"live_research_tested": false' in output
    assert "real research job is still required" in output


def test_failed_check_restores_unset_profile(monkeypatch, capsys):
    monkeypatch.delenv("QUANT_CODEX_HOME", raising=False)

    class Runtime:
        async def readiness(self):
            raise research_runtime.ResearchRuntimeError("Sign in to the selected profile")

    monkeypatch.setattr(research_runtime, "CodexResearchRuntime", Runtime)
    assert research_cli.main(["check", "--codex-home", "/selected-profile"]) == 1
    assert "QUANT_CODEX_HOME" not in research_cli.os.environ
    assert "Sign in" in capsys.readouterr().out


def test_login_selects_profile_without_changing_parent_codex_home(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("CODEX_HOME", "/desktop-profile")
    monkeypatch.setitem(sys.modules, "codex_cli_bin", SimpleNamespace(bundled_codex_path=lambda: "/fake-codex"))
    seen = []

    def run(command, **kwargs):
        seen.append((command, kwargs))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(research_cli.subprocess, "run", run)
    profile = tmp_path / "profile"
    assert research_cli.main(["login", "--codex-home", str(profile), "--device-auth"]) == 0
    command, options = seen[0]
    assert command[-2:] == ["login", "--device-auth"]
    assert options["env"]["CODEX_HOME"] == str(profile)
    assert research_cli.os.environ["CODEX_HOME"] == "/desktop-profile"
    assert "can update that profile's existing sign-in" in capsys.readouterr().out


def test_check_rejects_login_only_option():
    with pytest.raises(SystemExit) as error:
        research_cli.main(["check", "--device-auth"])
    assert error.value.code == 2
