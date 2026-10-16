# Validation results — 16 October 2026

## Automated checks

The local suite passed **306 tests**, including the PostgreSQL integration tests
and 22 additional calculation/data-quality regressions. The previous published
GitHub CI run passed 284 tests. These counts cover different revisions; CI must
run again after the latest fixes are published.

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
