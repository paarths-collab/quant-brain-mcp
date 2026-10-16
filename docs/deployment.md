# Deployment and release checks

This revision requires authenticated HTTP access. It does not change an existing hosted deployment until deployed. Use an MCP client that can set an `Authorization: Bearer ...` header. The server uses operator-provisioned API tokens; it does not implement an OAuth login or account signup flow.

## Configuration

- Python 3.12; install the tested `requirements.lock` and provision Chrome for Kaleido image export (see README).
- `MCP_API_KEYS`: JSON mapping stable, non-personal owner IDs to lowercase SHA-256 digests of random bearer tokens. Generate at least 32 random bytes per token with a secure secrets generator. Supply the raw token only to its intended client through a secret manager, and store its digest in the server configuration. Never commit either value. Rotate a token by replacing its digest while retaining the owner ID, then restart workers.
- `DATABASE_URL`: PostgreSQL connection URL, required for durable alerts. Use TLS for remote databases and a dedicated database role. The application creates its tables/indexes on first use; run the first connection under controlled deployment conditions. Existing alerts with no owner remain inaccessible; assign ownership only after an operator verifies it.
- `METRICS_TOKEN`: separate random credential for the metrics endpoint.
- `MCP_ALLOWED_ORIGINS`: optional comma-separated exact browser origins. Browser requests are rejected by default. Native clients without an Origin header are supported.
- `HOST`, `PORT`: bind configuration. Use TLS at the ingress; do not expose plaintext HTTP publicly.

Start with `uvicorn render_app:app --host 0.0.0.0 --port "$PORT"`. Running `python fastmcp_server.py` uses the same protected application. Missing API-key configuration returns HTTP 503 on `/mcp`; missing/invalid credentials return HTTP 401. `/health` is liveness only and remains public; it does not certify database or Yahoo availability.

Each worker permits 4 concurrent authenticated MCP requests and 60 requests per minute per owner. HTTP bodies are capped at 1 MiB with a 15-second read timeout. Analysis workers have a separate four-job limit retained even if a client disconnects. Workloads accept at most 25 tickers or indicators per call. These are per-process safeguards: configure shared rate limiting, request-size limits, and timeouts at your production ingress when running multiple workers. Blocking analysis runs in threads so health checks remain responsive. Upstream data availability and numerical job duration are not guaranteed.

## Verification

Run the unit/regression suite, the offline smoke test (including PNG export), and the opt-in database integration tests described in their test module. Run representative authenticated live quote, indicator, portfolio, and chart requests in staging. Verify that a second identity cannot list, delete, or trigger the first identity's alerts. Check missing/wrong-token behavior before enabling public ingress.

A successful test suite is not a load, penetration, or investment-model certification. Portfolio results are historical research estimates; inspect the returned holdout methodology and limitations. Real database durability, ingress controls, and alert-polling credentials must be configured and tested for each deployment.
