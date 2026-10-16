"""Explicit setup helpers for the private Codex research runtime."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import tempfile
from pathlib import Path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("login", "check"))
    parser.add_argument("--device-auth", action="store_true", help="Use Codex device login instead of browser login")
    parser.add_argument("--codex-home", help="Codex profile directory (overrides QUANT_CODEX_HOME for this command only)")
    args = parser.parse_args(argv)
    if args.device_auth and args.command != "login":
        parser.error("--device-auth is only valid with login")
    previous_home = os.environ.get("QUANT_CODEX_HOME")
    if args.codex_home:
        os.environ["QUANT_CODEX_HOME"] = args.codex_home
    try:
        return _run(args, parser)
    finally:
        if args.codex_home:
            if previous_home is None:
                os.environ.pop("QUANT_CODEX_HOME", None)
            else:
                os.environ["QUANT_CODEX_HOME"] = previous_home


def _run(args, parser) -> int:
    if args.command == "login":
        try:
            from codex_cli_bin import bundled_codex_path
        except ImportError:
            parser.exit(1, "Install requirements_research.txt first.\n")
        home = Path(os.environ.get("QUANT_CODEX_HOME", "~/.quant-brain/codex")).expanduser().resolve()
        home.mkdir(parents=True, exist_ok=True, mode=0o700)
        print("Signing into the selected Codex profile. Login can update that profile's existing sign-in.")
        command = [str(bundled_codex_path()), "-c", 'cli_auth_credentials_store="file"', "login"]
        if args.device_auth:
            command.append("--device-auth")
        with tempfile.TemporaryDirectory(prefix="quant-login-") as cwd:
            return subprocess.run(command, env={**os.environ, "CODEX_HOME": str(home)}, cwd=cwd, check=False).returncode
    from core.research_runtime import CodexResearchRuntime, ResearchRuntimeError
    try:
        result = asyncio.run(CodexResearchRuntime().readiness())
    except (ResearchRuntimeError, ValueError) as exc:
        print(str(exc))
        return 1
    print(json.dumps(result, indent=2))
    print("Login verified. A real research job is still required to verify model access, live search and MCP connectivity.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
