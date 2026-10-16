# Validation results — 16 October 2026

## Reliability update validation

The revised local suite passed **379 tests**, including real PostgreSQL owner isolation/concurrent alert checks, internal MCP admission, indicator settings, financial units, PDF extraction, source-fetch restrictions, publication metadata and VPS update/rollback orchestration. Dependency compatibility passed for the installed 121-package test environment. HTTP application startup, registration of all 29 tools and real PNG export also passed. Two upstream library warnings remain (Starlette's test-client deprecation and a settings forward-reference warning).

A new authenticated quick research job completed through both HTTP MCP servers and the actual Codex runtime in approximately three minutes. All four roles ran; SDK trace recorded six successful MCP calls and five web-search events, with no observed MCP failures. The report correctly returned **insufficient evidence / low confidence** because official-source retrieval was blocked and the auditor requested correction. This demonstrates working execution and honest evidence gaps, not investment accuracy.

Live profile and six-group checks returned explicit metadata. Thirty-seven indicators had finite values; ZigZag explicitly reported no recent finite pivots. Both tested official TCS HTML/PDF URLs returned HTTP 403 from the test environment; the retrieval layer recorded these failures. Generated PDF fixtures verified actual extraction separately. Sites that deny retrieval remain unavailable; there is no claim that every filing is now accessible.

The VPS updater was exercised with real temporary Git repositories and simulated service/package/MCP commands: success, preparation failure, activation rollback for directory and symlink environments, SIGTERM recovery and dirty-checkout refusal all passed. Private configuration, sign-in and database fixtures remained byte-identical. These lifecycle tests do not constitute deployment on a real VPS. After updating, repeat public HTTPS and a real Claude research request.

Only release source/docs are published; test credentials, local research reports and runtime files remain outside version control. Check GitHub CI for the published revision's Linux results.

## Previous release automated checks

The local suite passed **306 tests**, including the PostgreSQL integration tests
and 22 additional calculation/data-quality regressions.
[GitHub CI for revision a8c0df1](https://github.com/paarths-collab/quant-brain-mcp/actions/runs/38928497618)
also passed all 306 tests, dependency checks, registration of all 29 tools, HTTP
startup, and real PNG export. This is a record of that tested revision; consult the
repository CI badge for subsequent changes.

## Authenticated research smoke test

One deep research job completed through the authenticated outer HTTP MCP,
background worker, Codex SDK, and restricted internal HTTP MCP in approximately
5 minutes 30 seconds. It used the existing authorized Codex sign-in without
copying credentials. Test tokens, reports, logs, and databases stayed outside the
repository; both test servers were stopped afterward.

The request was deliberately narrow: find a recent official TCS disclosure and
retrieve a quote, with dates and limitations, without recommending a trade.

- All six roles ran; two correction rounds exercised the ten-invocation limit.
- SDK events recorded 10 web-search events and 9 successful `get_quote` calls.
- The auditor preserved original claim IDs, requested corrections, and excluded
  historical quote timestamps it could not independently authenticate.
- The synthesizer retained only the audited disclosure claim. Its final result
  was **mixed**, with **moderate** confidence; rejected claims and disagreements
  remained visible.
- An independent review opened the [official TCS disclosure](https://www.tcs.com/who-we-are/newsroom/press-release/tcs-financial-results-q2-fy-2027)
  and confirmed its 8 October 2026 dateline and quarter ended 30 September 2026.

This is an integration pass for the tested workflow, **not an investment-accuracy
pass**. No return, valuation, backtest, portfolio, or trading recommendation was
evaluated by this live model job.

## Remaining limitations

Some analyst prose described successful web retrieval without a corresponding
web-search event in that role's recorded trace. Prior evidence may have been
reused; the prose alone does not establish fresh retrieval. Runtime events prove
that calls occurred, not the truth or provenance of each claim. Model-generated
excerpts are not signed records of tool results.

The auditor correctly refused to authenticate previous quote timestamps from
fresh quotes. Repeating this issue consumed both correction rounds, showing a
latency and evidence-provenance limitation. Reports retain review history, which
can contain superseded warnings alongside corrections. Yahoo retrieval time
does not establish the market observation time or guarantee quote freshness.

Broader repeatability and investment-quality benchmarking remain necessary.
The authenticated MCP transport was tested directly; this run did not test an
actual Claude client connection.
