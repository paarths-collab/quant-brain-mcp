"""Exercise updater switching/rollback with real Git and simulated host services.

The fixture substitutes privileged paths and the quant identity boundary only in
its private script copy. pip, pytest, and MCP network checks are deterministic
stand-ins: these tests verify deployment orchestration, not package provisioning.
"""
from pathlib import Path
import os
import shlex
import shutil
import subprocess

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/update-personal-vps.sh"


def run(*args, cwd=None, env=None):
    return subprocess.run(args, cwd=cwd, env=env, check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def deployment(tmp_path):
    if not shutil.which("bash") or not shutil.which("git"):
        pytest.skip("Bash and Git are required")
    env = dict(os.environ, GIT_AUTHOR_NAME="Anonymous", GIT_AUTHOR_EMAIL="anonymous@example.invalid",
               GIT_COMMITTER_NAME="Anonymous", GIT_COMMITTER_EMAIL="anonymous@example.invalid")
    remote = tmp_path / "upstream.git"
    repo = tmp_path / "quant" / "quant-brain-mcp"
    repo.parent.mkdir()
    run("git", "init", "--bare", str(remote), env=env)
    run("git", "init", "-b", "main", str(repo), env=env)
    (repo / ".gitignore").write_text(".venv\n")
    (repo / "requirements_research.txt").write_text("# Fixture dependencies\n")
    (repo / "version").write_text("old\n")
    run("git", "add", ".", cwd=repo, env=env)
    run("git", "-c", "commit.gpgsign=false", "commit", "-m", "Initial fixture", cwd=repo, env=env)
    previous = run("git", "rev-parse", "HEAD", cwd=repo, env=env)
    (repo / "version").write_text("new\n")
    run("git", "add", ".", cwd=repo, env=env)
    run("git", "-c", "commit.gpgsign=false", "commit", "-m", "Fixture update", cwd=repo, env=env)
    target = run("git", "rev-parse", "HEAD", cwd=repo, env=env)
    run("git", "remote", "add", "origin", str(remote), cwd=repo, env=env)
    run("git", "push", "origin", "main", cwd=repo, env=env)
    run("git", "reset", "--hard", previous, cwd=repo, env=env)
    state = tmp_path / "state"
    state.mkdir()
    private = repo.parent / ".config" / "quant-brain"
    private.mkdir(parents=True)
    profile = repo.parent / ".quant-brain" / "codex"
    profile.mkdir(parents=True)
    protected = [private / "runtime.env", private / "client-token",
                 profile / "auth.json", state / "research.sqlite3"]
    for path in protected:
        path.write_bytes(("untouched-fixture-" + path.name).encode())
    before = {p: p.read_bytes() for p in protected}
    old_venv = repo / ".venv"
    (old_venv / "bin").mkdir(parents=True)
    (old_venv / "marker").write_text("original environment")
    old_python = old_venv / "bin" / "python"
    old_python.write_text("#!/bin/sh\nexit 0\n")
    old_python.chmod(0o755)
    bins = tmp_path / "bin"
    bins.mkdir()
    events = tmp_path / "events"
    failure = tmp_path / "failure-mode"
    def executable(name, source):
        p = bins / name
        p.write_text("#!/bin/bash\nset -eu\n" + source)
        p.chmod(0o755)
    event_q, failure_q = shlex.quote(str(events)), shlex.quote(str(failure))
    executable("systemctl", f'echo "systemctl $*" >> {event_q}\n')
    executable("flock", "exit 0\n")
    # Stable venv Python stands in for dependency installation/test/MCP calls.
    python_stub = tmp_path / "venv-python"
    python_stub.write_text(f'''#!/bin/bash
set -eu
echo "python $*" >> {event_q}
if [[ "${{1:-}}" == - ]]; then
  cat >/dev/null
  mode=$(cat {failure_q} 2>/dev/null || true)
  if [[ "$mode" == health ]]; then exit 1; fi
  if [[ "$mode" == signal ]]; then kill -TERM "$PPID"; sleep 0.05; exit 1; fi
fi
if [[ "${{1:-}} ${{2:-}}" == '-m pytest' ]] && [[ $(cat {failure_q} 2>/dev/null || true) == preflight ]]; then exit 1; fi
exit 0
''')
    python_stub.chmod(0o755)
    executable("python3.12", f'''[[ "$1 $2" == '-m venv' ]]
mkdir -p "$3/bin"
cp {shlex.quote(str(python_stub))} "$3/bin/python"
''')
    source = SCRIPT.read_text()
    original_root = "[[ $EUID -eq 0 ]] || { echo 'Run as root on the VPS.'; exit 1; }"
    original_quant = 'quant() { runuser -u quant -- env -i HOME=/home/quant PATH=/usr/local/bin:/usr/bin:/bin "$@"; }'
    original_owner = '[[ $(stat -c %U "$repo") == quant ]] || { echo \'Checkout must be owned by quant.\'; exit 1; }'
    assert all(text in source for text in (original_root, original_quant, original_owner))
    source = source.replace(original_root, ": # fixture root boundary")
    source = source.replace(original_quant, 'quant() { "$@"; }')
    source = source.replace(original_owner, ": # fixture owner boundary")
    source = source.replace("/home/quant/quant-brain-mcp", str(repo))
    source = source.replace("/home/quant/.local/share/quant-brain", str(state))
    source = source.replace("/home/quant", str(repo.parent))
    source = source.replace("/run/lock/quant-brain-update.lock", str(tmp_path / "update.lock"))
    source = source.replace("https://github.com/paarths-collab/quant-brain-mcp.git", str(remote))
    updater = tmp_path / "updater.sh"
    updater.write_text(source)
    env["PATH"] = str(bins) + os.pathsep + env["PATH"]
    return dict(repo=repo, previous=previous, target=target, env=env, updater=updater,
                events=events, failure=failure, before=before, state=state)


@pytest.mark.parametrize("mode", ["success", "health", "signal", "preflight"])
def test_update_lifecycle_and_preservation(deployment, mode):
    d = deployment
    d["failure"].write_text(mode)
    result = subprocess.run(["bash", str(d["updater"]), d["target"]],
                            env=d["env"], capture_output=True, text=True, timeout=20)
    events = d["events"].read_text().splitlines()
    current = run("git", "rev-parse", "HEAD", cwd=d["repo"], env=d["env"])
    if mode == "success":
        assert result.returncode == 0, result.stdout + result.stderr
        assert current == d["target"]
        assert (d["repo"] / ".venv").is_symlink()
        assert (d["repo"] / ".venv" / "bin" / "python").exists()
        assert events.index("python -m pytest -q") < events.index("systemctl stop quant-brain")
        assert events.index("systemctl stop quant-brain") < events.index("systemctl stop quant-brain-internal")
        assert events.index("systemctl start quant-brain-internal") < events.index("systemctl start quant-brain")
    else:
        assert result.returncode != 0
        assert current == d["previous"], result.stdout + result.stderr
        assert not (d["repo"] / ".venv").is_symlink()
        assert (d["repo"] / ".venv" / "marker").read_text() == "original environment"
        if mode == "preflight":
            assert not any("systemctl stop" in line for line in events)
        else:
            assert events.count("systemctl start quant-brain") == 2
            assert "Previous code/environment restored" in result.stdout
    assert all(path.read_bytes() == content for path, content in d["before"].items())
    assert run("git", "status", "--porcelain", cwd=d["repo"], env=d["env"]) == ""


def test_update_failure_restores_existing_venv_symlink(deployment):
    d = deployment
    old_link = d["repo"] / ".venv"
    original = d["state"] / "existing-stable-venv"
    old_link.rename(original)
    old_link.symlink_to(original)
    d["failure"].write_text("health")
    result = subprocess.run(["bash", str(d["updater"]), d["target"]],
                            env=d["env"], capture_output=True, text=True, timeout=20)
    assert result.returncode != 0
    assert old_link.is_symlink()
    assert old_link.resolve() == original
    assert (old_link / "marker").read_text() == "original environment"
    assert run("git", "rev-parse", "HEAD", cwd=d["repo"], env=d["env"]) == d["previous"]


def test_dirty_checkout_is_rejected_without_stopping_services(deployment):
    d = deployment
    (d["repo"] / "version").write_text("operator change\n")
    result = subprocess.run(["bash", str(d["updater"]), d["target"]],
                            env=d["env"], capture_output=True, text=True, timeout=20)
    assert result.returncode != 0
    assert "local changes" in result.stdout
    assert not d["events"].exists()
    assert (d["repo"] / "version").read_text() == "operator change\n"
