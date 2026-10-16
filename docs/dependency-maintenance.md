# Runtime installation and release checks

Use Python 3.12. Both `requirements.txt` and the legacy
`requirements_mcp.txt` install the same complete pinned runtime lock.

```sh
python -m pip install -r requirements.txt
python -m pip check
python -m pip install pytest==9.1.1
python -m pytest -q
python smoke_test.py
```

The smoke test is offline and checks server startup, HTTP health, tool registration,
and actual PNG generation through the MCP chart conversion path. Any failure
returns a nonzero exit status. It requires installed Google Chrome or Chromium;
Kaleido 1 does not bundle a browser. On a new host, install Chrome/Chromium using
the operating system package manager, or run `kaleido_get_chrome` during the image
build. Set `BROWSER_PATH` to its executable if automatic discovery fails. Linux
containers must also include the browser's required shared libraries. Run the
smoke test inside the final deployment image before promotion. CI explicitly downloads Kaleido's tested Chrome build before the smoke test.

Direct dependencies live in `requirements.in`. Plotly 6.3.1 works with both
VectorBT 1.0.0 and Kaleido 1.5.0; unconstrained Plotly upgrades can break startup.
Regenerate the complete lock after intentional upgrades, then repeat all checks:

```sh
uv pip compile requirements.in --python-version 3.12 --output-file requirements.lock --no-annotate --no-header
```

CI performs the installation, dependency consistency check, unit suite, and PNG
smoke test. A passing offline suite does not prove live market data or PostgreSQL
availability; verify those integrations separately with deployment credentials.
