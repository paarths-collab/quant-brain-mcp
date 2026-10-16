#!/usr/bin/env bash
# First installation on Ubuntu 24.04. Does not configure public ingress.
set -euo pipefail
umask 077

[[ $EUID -eq 0 ]] || { echo 'Run as root on the VPS.'; exit 1; }
source /etc/os-release
[[ ${ID:-} == ubuntu && ${VERSION_ID:-} == 24.04 ]] || {
  echo 'This installer targets Ubuntu 24.04 only.'; exit 1;
}
if id quant >/dev/null 2>&1 || [[ -e /home/quant || -L /home/quant ]]; then
  echo 'An existing quant user or home was found. Stop and inspect; nothing overwritten.'
  exit 1
fi
for unit in quant-brain-internal.service quant-brain.service; do
  if systemctl cat "$unit" >/dev/null 2>&1; then
    echo "Existing service found: $unit. Stop and inspect."
    exit 1
  fi
done
if ss -H -ltn 'sport = :8000 or sport = :8001' | grep -q .; then
  echo 'Port 8000 or 8001 is occupied. Stop and choose other ports.'
  exit 1
fi

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  git ca-certificates python3.12 python3.12-venv libgomp1
useradd --create-home --shell /bin/bash quant
chmod 700 /home/quant
runuser -u quant -- env HOME=/home/quant bash <<'APP'
set -euo pipefail
umask 077
cd /home/quant
git clone https://github.com/paarths-collab/quant-brain-mcp.git
cd quant-brain-mcp
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements_research.txt
.venv/bin/python -m pip check
mkdir -p /home/quant/.config/quant-brain /home/quant/.quant-brain/codex /home/quant/.local/share/quant-brain
chmod 700 /home/quant/.config/quant-brain /home/quant/.quant-brain /home/quant/.quant-brain/codex /home/quant/.local/share/quant-brain
.venv/bin/python - <<'CONFIG'
import hashlib, json, os, secrets, shlex
from pathlib import Path
base = Path('/home/quant/.config/quant-brain')
client = secrets.token_urlsafe(32)
values = {
    'MCP_API_KEYS': json.dumps({'personal-research': hashlib.sha256(client.encode()).hexdigest()}),
    'QUANT_INTERNAL_TOKEN': secrets.token_urlsafe(32),
    'QUANT_RESEARCH_ENABLED': 'true',
    'QUANT_INTERNAL_MCP_URL': 'http://127.0.0.1:8001/mcp',
    'QUANT_CODEX_HOME': '/home/quant/.quant-brain/codex',
    'QUANT_RESEARCH_DB': '/home/quant/.local/share/quant-brain/research.sqlite3',
    'QUANT_CODEX_MODEL': '',
    'QUANT_CODEX_ROLE_TIMEOUT': '120',
    'HOST': '127.0.0.1',
    'PORT': '8000',
    'MCP_ALLOWED_ORIGINS': '',
    'METRICS_TOKEN': secrets.token_urlsafe(32),
    'DATABASE_URL': '',
}
for name, content in {
    'runtime.env': ''.join(f'export {key}={shlex.quote(value)}\n' for key,value in values.items()),
    'client-token': client + '\n',
    'client.env': f'export QUANT_CLIENT_TOKEN={shlex.quote(client)}\n',
}.items():
    fd = os.open(base / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        stream.write(content)
print('Private configuration generated. No secrets printed.')
CONFIG
APP

for component in internal outer; do
  if [[ $component == internal ]]; then
    unit=quant-brain-internal
    application=internal_app:app
    port=8001
    after='network-online.target'
    wants='network-online.target'
  else
    unit=quant-brain
    application=render_app:app
    port=8000
    after='network-online.target quant-brain-internal.service'
    wants='network-online.target quant-brain-internal.service'
  fi
  cat > "/etc/systemd/system/$unit.service" <<UNIT
[Unit]
Description=Quant Brain $component MCP
After=$after
Wants=$wants

[Service]
Type=simple
User=quant
Group=quant
Environment=HOME=/home/quant
WorkingDirectory=/home/quant/quant-brain-mcp
ExecStart=/bin/bash -c 'source /home/quant/.config/quant-brain/runtime.env; exec /home/quant/quant-brain-mcp/.venv/bin/python -m uvicorn $application --host 127.0.0.1 --port $port --workers 1'
Restart=on-failure
RestartSec=5
UMask=0077
KillMode=control-group
TimeoutStopSec=90

[Install]
WantedBy=multi-user.target
UNIT
  chmod 644 "/etc/systemd/system/$unit.service"
done
systemctl daemon-reload
echo 'Installation finished. Services are not started yet.'
echo 'Next: sign in as quant using research_cli.py login --device-auth, then check authentication and enable both services.'
echo 'Traefik, DNS, firewall rules and existing application configuration were not changed.'
echo 'Chrome/chart export and PostgreSQL/alerts require separate setup.'
