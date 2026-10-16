#!/usr/bin/env bash
# Update an existing personal VPS installation to a reviewed full commit SHA.
set -Eeuo pipefail
umask 077
[[ $EUID -eq 0 ]] || { echo 'Run as root on the VPS.'; exit 1; }
[[ $# -eq 1 && $1 =~ ^[0-9a-f]{40}$ ]] || {
  echo 'Usage: bash update-personal-vps.sh FULL_REVIEWED_COMMIT_SHA'; exit 1;
}
revision=$1
repo=/home/quant/quant-brain-mcp
state=/home/quant/.local/share/quant-brain
exec 9>/run/lock/quant-brain-update.lock
flock -n 9 || { echo 'Another update is running.'; exit 1; }
quant() { runuser -u quant -- env -i HOME=/home/quant PATH=/usr/local/bin:/usr/bin:/bin "$@"; }
qgit() { quant git -C "$repo" "$@"; }
[[ -d $repo && ! -L $repo ]] || { echo 'Expected installer checkout not found.'; exit 1; }
[[ $(stat -c %U "$repo") == quant ]] || { echo 'Checkout must be owned by quant.'; exit 1; }
[[ $(qgit remote get-url origin) == https://github.com/paarths-collab/quant-brain-mcp.git ]] || {
  echo 'Unexpected origin; inspect manually.'; exit 1;
}
[[ $(qgit branch --show-current) == main ]] || { echo 'Expected main branch.'; exit 1; }
[[ -z $(qgit status --porcelain --untracked-files=normal) ]] || {
  echo 'Checkout has local changes; preserve them before updating.'; exit 1;
}
[[ -x $repo/.venv/bin/python ]] || { echo 'Existing virtual environment missing.'; exit 1; }
for unit in quant-brain-internal quant-brain; do
  systemctl is-active --quiet "$unit" || { echo "$unit must be running before this update."; exit 1; }
done
old_revision=$(qgit rev-parse HEAD)
qgit fetch --no-tags origin main
[[ $(qgit rev-parse "$revision^{commit}") == "$revision" ]] || exit 1
qgit merge-base --is-ancestor "$old_revision" "$revision" || {
  echo 'Target is not a fast-forward update.'; exit 1;
}
qgit merge-base --is-ancestor "$revision" origin/main || {
  echo 'Target is not on origin/main.'; exit 1;
}
quant mkdir -p "$state/releases" "$state/venvs"
release=$(quant mktemp -d "$state/releases/update-XXXXXXXX")
venv=$(quant mktemp -d "$state/venvs/$revision-XXXXXXXX")
quant mkdir "$release/source"
qgit archive "$revision" | quant tar -x -C "$release/source"
printf '%s\n' "$old_revision" > "$release/previous-commit"
printf '%s\n' "$revision" > "$release/target-commit"
printf '%s\n' "$venv" > "$release/target-venv"
# Never move the new venv after installation: entry-point shebangs use its path.
quant python3.12 -m venv "$venv"
quant "$venv/bin/python" -m pip install -r "$release/source/requirements_research.txt" pytest==9.1.1
quant "$venv/bin/python" -m pip check
quant bash -c 'cd "$1"; exec "$2/bin/python" -m pytest -q' _ "$release/source" "$venv"
# Check again after preparation: do not replace edits made while pip/tests ran.
[[ $(qgit rev-parse HEAD) == "$old_revision" && -z $(qgit status --porcelain --untracked-files=normal) ]] || {
  echo 'Checkout changed during preparation; services untouched.'; exit 1;
}

stopped=0
venv_moved=0
rollback() {
  result=${1:-$?}
  trap - ERR INT TERM
  set +e
  if [[ $stopped == 1 ]]; then
    echo 'Update failed. Attempting to restore the previous code and environment.'
    systemctl stop quant-brain
    systemctl stop quant-brain-internal
    # --keep plus cleanliness checks never discard intervening tracked edits.
    if [[ -z $(qgit status --porcelain --untracked-files=normal) ]] && qgit reset --keep "$old_revision"; then
      if [[ $venv_moved == 1 ]]; then
        if [[ -L $repo/.venv && $(readlink "$repo/.venv") == "$venv" ]]; then
          quant rm "$repo/.venv"
        fi
        if [[ ! -e $repo/.venv && ! -L $repo/.venv ]]; then
          quant mv "$release/previous-venv" "$repo/.venv"
        else
          echo 'Environment changed unexpectedly; inspect before restarting.'
          echo "Recovery records: $release"
          exit "$result"
        fi
      fi
      systemctl start quant-brain-internal && systemctl start quant-brain
      echo 'Previous code/environment restored; check service health before use.'
    else
      echo 'Checkout changed; automatic rollback stopped to preserve local edits.'
    fi
    echo "Recovery records: $release"
  fi
  exit "$result"
}
trap rollback ERR
trap 'rollback 130' INT
trap 'rollback 143' TERM
# Running research is interrupted by service restart. Wait for jobs beforehand.
stopped=1
systemctl stop quant-brain
systemctl stop quant-brain-internal
qgit merge --ff-only "$revision"
quant mv "$repo/.venv" "$release/previous-venv"
venv_moved=1
quant ln -s "$venv" "$repo/.venv"
systemctl start quant-brain-internal
systemctl start quant-brain
# Authenticated handshake and discovery test, without displaying credentials.
quant "$venv/bin/python" - <<'PY'
import asyncio
from pathlib import Path
import subprocess
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def check(url, token):
    async with streamablehttp_client(url, headers={"Authorization": "Bearer " + token}) as (read, write, _):
        async with ClientSession(read, write) as client:
            await client.initialize()
            result = await client.list_tools()
            if not result.tools:
                raise RuntimeError("No MCP tools discovered")
            return len(result.tools)

# Read only the internal token from the operator-owned shell configuration.
# stdout is captured in memory, never printed or written to the release folder.
result = subprocess.run(
    ["/bin/bash", "-c", 'source /home/quant/.config/quant-brain/runtime.env; printf %s "$QUANT_INTERNAL_TOKEN"'],
    check=True, capture_output=True, text=True,
)
internal = result.stdout
outer = Path("/home/quant/.config/quant-brain/client-token").read_text().strip()
if not internal or not outer:
    raise SystemExit("Required private tokens are missing.")
async def main():
    for attempt in range(10):
        try:
            async with asyncio.timeout(15):
                inside = await check("http://127.0.0.1:8001/mcp", internal)
                outside = await check("http://127.0.0.1:8000/mcp", outer)
            if (inside, outside) != (21, 29):
                raise RuntimeError("Unexpected MCP tool count")
            print(f"Authenticated MCP checks passed: internal={inside}, outer={outside} tools.")
            return
        except Exception:
            if attempt == 9:
                raise SystemExit("Post-update MCP check failed; no credentials printed.")
            await asyncio.sleep(2)
asyncio.run(main())
PY
systemctl is-active --quiet quant-brain-internal
systemctl is-active --quiet quant-brain
trap - ERR INT TERM
printf 'Updated successfully to %s\nRecovery records: %s\n' "$revision" "$release"
echo 'Private configuration, Codex sign-in, database, and reverse proxy were preserved.'
echo 'Now run a quick research job through Claude to verify live model/provider access.'
