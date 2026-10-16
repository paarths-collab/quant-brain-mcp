# Tool Reference

The public MCP exposes **29 tools**: 25 analysis/alert/chart tools and four research job tools. The internal Codex agents receive only 21 read-only analysis tools; they cannot start research jobs recursively or manage alerts. Parameters marked **required** must be supplied.

See [Architecture](architecture.md) for the system boundaries and [Research runtime](research-runtime.md) for setup and the Claude connection. HTTP calls require a configured bearer token. Research and alert records are scoped to the authenticated owner; there is no owner parameter to spoof.

Common parameter: `period` — history window. One of `1d` `5d` `1mo` `3mo` `6mo` `1y` `2y` `5y` `10y` `ytd` `max`. Default `2y` unless noted.


## Research jobs

These optional tools require `QUANT_RESEARCH_ENABLED=1`, the research dependencies, a signed-in Codex runtime, and the internal calculation server. They consume the selected Codex account's allowance. Start once, poll status, then fetch the finished report; an HTTP request does not stay open for the entire investigation.

### `start_research`

| Param | Type | Notes |
|---|---|---|
| `question` | `string` **required** | Nonblank, at most 12,000 characters |
| `tickers` | `string[]` **required** | 1–5 NSE stock symbols; trimmed, uppercased, deduplicated, with `.NS` appended if absent |
| `depth` | `"quick"` \| `"standard"` \| `"deep"` | Default `standard` |

Symbols such as `TCS` and `RELIANCE.NS` are accepted. Other exchange suffixes are rejected. Bare symbols are interpreted as NSE symbols, so confirm the company identity in the findings.

| Depth | Workflow | Maximum role invocations |
|---|---|---|
| `quick` | Company + quant in parallel → auditor → synthesizer | 4 |
| `standard` | Lead → company + quant in parallel → skeptic → auditor → up to one correction/re-audit → synthesizer | 8 |
| `deep` | Standard with up to two correction/re-audit rounds | 10 |

Returns the status object described below, including `id`. A fast worker may already have changed the initial `queued` status to `running` when this response arrives.

### `get_research_status`

| Param | Type | Notes |
|---|---|---|
| `job_id` | `string` **required** | The `id` returned by `start_research` |

Returns `id`, `status`, `stage`, `created`, `updated`, `tickers`, `depth`, and nullable `error`. Status is `queued`, `running`, `completed`, `failed`, or `cancelled`. `stage` identifies the latest workflow activity (for example `quant`, `auditor`, or `correction_1`); it is not a percentage, and parallel roles can overlap.

### `get_research_report`

| Param | Type | Notes |
|---|---|---|
| `job_id` | `string` **required** | The `id` returned by `start_research` |

A completed response contains `id`, `status: "completed"`, `report`, and chronological `events`. Other known jobs return `status`, `stage`, `error`, and `report: null`.

The report contains:

- Request context: `question`, `tickers`, `market: "NSE"`, `currency: "INR"`, `market_timezone: "Asia/Kolkata"`, `created_at`, and `depth`.
- Conclusions: `summary`, `outcome` (`supported`, `mixed`, or `insufficient_evidence`), `confidence` (`low`, `moderate`, or `high`), `assumptions`, `warnings`, and `disagreements`.
- Traceable findings: `claims` with evidence IDs, claim kind, assumptions, and a calculation method where applicable; `evidence` with URL/tool URI, title, publication date when known, retrieval date, source type, and excerpt.
- Review details: `verified_claim_ids`, `verification_basis: "model_review"`, `agent_findings`, `invocation_count`, and `execution_trace`.

`execution_trace` records SDK-observed web searches and allowed MCP tool-call names/statuses, without raw tool arguments, results, or URLs. It does **not** prove that each cited source supports its claim or that a calculation is correct. A `urn:tool:quant_internal:<tool_name>` citation identifies a tool; it is not itself execution proof. Check the claims, sources, warnings, and actual observation dates before relying on the summary. A completed job can correctly return `insufficient_evidence`.

### `cancel_research`

| Param | Type | Notes |
|---|---|---|
| `job_id` | `string` **required** | The `id` returned by `start_research` |

Requests cancellation of queued or running work and returns the status object. Completed, failed, and cancelled jobs remain terminal; cancellation does not delete a report or restart a job.

### Limits and errors

The queue accepts at most four active jobs globally and two per authenticated owner, counting both queued and running jobs. One job runs at a time; its company and quant roles run in parallel. The current job execution budget is 900 seconds after a worker starts it, excluding queue time. Each role defaults to 120 seconds, configurable with `QUANT_CODEX_ROLE_TIMEOUT` from 1–600 seconds. These are wall-clock and invocation limits, not a fixed token or cost budget.

Use one outer server worker per research SQLite database. Interrupted work becomes `failed` with stage `interrupted` after recovery; jobs are not automatically resumed. Results survive restarts. There is currently no report-deletion MCP tool or automatic retention policy.

Tool-level failures return an `error` object for disabled research, invalid input, queue capacity, or an unknown/inaccessible job. Another owner's job returns the same `Research job not found` error as a nonexistent ID. Failures after job creation appear in job status with a safe error message; failed jobs have no report. A timeout suggests quick mode or fewer companies. Do not repeatedly resubmit a failed job without checking its error.

Transport failures are separate: missing/invalid bearer credentials return HTTP 401, missing server authentication configuration returns 503, and rate/concurrency limits return 429 with `Retry-After`. The HTTP middleware defaults to 60 requests per minute per owner and four concurrent requests per process; poll with a delay rather than a tight loop.

---

## Trader workflow

### `get_quote`

Price snapshot for one or many tickers in a single call.

| Param | Type | Notes |
|---|---|---|
| `tickers` | `string[]` **required** | e.g. `["AAPL", "RELIANCE.NS"]` |

Returns per ticker: `last_price`, `previous_close`, `day_change_pct`, `day_range`, `52w_range`, `pct_of_52w_range`, `volume`, `volume_vs_3mo_avg`, `currency`, `exchange`. Top level: `as_of` and `fetched_at` are retrieval timestamps, **not quote observation timestamps**. `market_timestamp` is currently null and `freshness_status` is `unknown`. `timestamp_note` explains this distinction. `data_delay_note` describes approximate provider delays (including roughly 15 minutes for NSE/BSE), not a verified freshness guarantee. Web search is not a real-time quote feed. One bad ticker is reported in its own batch slot.

### `get_news`

Recent headlines via Yahoo Finance's aggregated feed (not a scraper).

| Param | Type | Notes |
|---|---|---|
| `ticker` | `string` **required** | |
| `limit` | `int` | default 8, max 25 |

Returns `articles[]` with `title`, `publisher`, `url`, `published_at`, `summary`.

### `build_trade_plan`

The core tool: turns analysis into an actionable, sized plan.

| Param | Type | Notes |
|---|---|---|
| `ticker` | `string` **required** | |
| `equity` | `number` **required** | account size in the ticker's currency |
| `risk_pct` | `number` | % of equity risked if stopped out; default 1.0 |
| `direction` | `"long"` \| `"short"` | default long |
| `period` | period | default 1y |

Returns: `entry` (last close), `stop` (tighter of 10-bar swing level or 2×ATR, with a minimum distance of 0.75 ATR), `stop_basis`, `shares` (whole shares sized so the modeled entry-to-stop loss is at most the risk budget, capped by equity), `position_value`, `max_loss`, `targets` (1R/2R/3R), `liquidity` (your order as % of 20-day turnover, with a warning above ~1%), and a one-line `invalidation`. Despite its field name, `max_loss` is a modeled loss at the stated stop, not a guaranteed cap: gaps, slippage, fees, and execution failures can increase realized loss. No order is placed.

### `scan_watchlist`

The Sunday-evening tool: what did my list actually do?

| Param | Type | Notes |
|---|---|---|
| `tickers` | `string[]` **required** | your watchlist |
| `period` | period | default 1y |

Per name: `last_close`, `day_change_pct`, `gap_pct`, distance from 20/50/200-DMA and the 52-week high, `atr_pct`, `volume_vs_20d_avg`, and `rules_fired` from: `near_52w_high`, `volume_spike`, `crossed_above_200dma`, `crossed_below_200dma`, `at_20dma`, `gapped_over_1atr`. Sorted most-actionable first. Failed tickers land in `failed`, never break the scan.

### `price_alert`

Persistent, one-shot price alerts stored in Postgres. See [Price Alerts](price-alerts.md) for the full pattern.

| Param | Type | Notes |
|---|---|---|
| `action` | `"set"` \| `"list"` \| `"delete"` \| `"check"` **required** | |
| `ticker` | `string` | for `set` |
| `level` | `number` | for `set` |
| `direction` | `"above"` \| `"below"` | for `set` |
| `alert_id` | `int` | for `delete` |
| `note` | `string` | optional context, echoed back when the alert fires |

`check` fetches current prices for every active alert and returns `triggered[]` + `still_watching`. Fired alerts deactivate (one-shot) so they never spam.

---

## Indicators — 6 grouped tools, 38 indicators

Every tool takes `ticker` (**required**), optional `indicators` subset, and `period`. Each indicator returns its last 10 values. One failing indicator degrades to an error in its own slot; the rest still compute.

| Tool | Indicators |
|---|---|
| `analyze_momentum` | rsi · macd · roc · cci · stoch · stochrsi · tsi · willr |
| `analyze_technical_levels` | sma · ema · hma · kama · ichimoku · supertrend · vwap · vwma |
| `analyze_trend` | adx · aroon · chop · psar · vortex · zigzag |
| `analyze_volatility` | atr · bbands · donchian · kc · stdev · ui |
| `analyze_volume` | obv · cmf · mfi · ad · pvt |
| `analyze_statistics` | log_return · zscore · skew · kurtosis · entropy |

Example call shape:

```json
{ "ticker": "RELIANCE.NS", "indicators": ["rsi", "macd"], "period": "5y" }
```

CCI uses the project's own implementation; see [Architecture](architecture.md).

---

## Portfolio

### `generate_optimized_verdict`

Optimize on a chronological training split → evaluate on the later holdout → risk-blend → verdict, in one call. The split is 70/30 with at least 126 training and 63 holdout observations; insufficient histories return an error. The historical verdict uses holdout performance. This is a historical validation split, not a forecast or a full walk-forward study.

| Param | Type | Notes |
|---|---|---|
| `tickers` | `string[]` **required** | mixed US + India supported |
| `amount` | `number` | notional for capital-at-risk figures; default 10 000 |
| `optimize_type` | enum | `mvo` (default) · `hrp` · `max_sharpe` · `min_volatility` · `black_litterman` · `cvar` · `semivariance` |
| `period` | period | default 2y |

Returns: `recommended_weights`, `backtest_metrics` (return / Sharpe / drawdown), `portfolio_intelligence` (per-ticker beta, VaR, alpha, regime — **blended by portfolio weight**, so the answer doesn't depend on the order you typed tickers), `risk_assessment` (95% 1-day VaR in % and currency, capital plan, risk flags), `final_verdict` (STRONG BUY / PROPER / ACCUMULATE / NEUTRAL / REDUCE / STAY AWAY), transparency fields (`requested_tickers` / `included_tickers` / `excluded_tickers` with per-ticker errors), and an `fx_note` disclosing that USD/INR currency risk is not modeled.

---

## Backtests

All take `ticker` (**required**) and `period` (default 2y). Fees of 0.1% per trade are applied. Returns include total return, Sharpe (252-day annualized), win rate, max drawdown, and trade count.

| Tool | Strategy | Extra params |
|---|---|---|
| `backtest_macd_momentum` | MACD crossover gated by EMA-200 trend filter | — |
| `backtest_macd_trend_follower` | MACD crossover | `fast=12` `slow=26` `signal=9` |
| `backtest_rsi_mean_reversion` | buy RSI < lower, sell RSI > upper | `length=14` `lower=30` `upper=70` |
| `backtest_mean_reversion_rsi_bb` | RSI + Bollinger Band confluence | `rsi_lower=30` `rsi_upper=70` |
| `backtest_sma_crossover` | fast/slow SMA cross | `fast=50` `slow=200` |
| `backtest_trend_crossover` | trend-filtered crossover | `fast=50` `slow=200` |
| `backtest_volatility_breakout` | Donchian-style breakout (bands shifted 1 bar — no lookahead) | `length=20` |

---

## Intelligence

### `analyze_sector_intelligence_tool`

| Param | Type | Notes |
|---|---|---|
| `market` | `"india"` \| `"us"` | default india |
| `timeframe` | `string` | default 1y |

Ranks sectors (8 Indian / 6 US) by a z-scored composite of risk-adjusted return, momentum, and drawdown. Includes a correlation matrix, per-sector `last_observed_date` / `is_stale` flags, and a `data_freshness_note` when index feeds lag.

### `find_sector_stock_pipeline_tool`

| Param | Type | Notes |
|---|---|---|
| `market` | `"india"` \| `"us"` | default india |
| `top_n_sectors` | `int` | default 3 |
| `top_n_stocks` | `int` | default 3 |

The full chain: rank sectors → score each sector's stocks (alpha, beta, Sharpe, regime) → recommend an entry strategy. Includes a `data_trace` of every fetch.

### `get_company_profile`

| Param | Type | Notes |
|---|---|---|
| `ticker` | `string` **required** | |

Business summary, sector/industry, valuation ratios, market cap (₹ Cr for Indian names), dividend yield, 52-week range.

---

## Charts

All three take `tickers` (`string[]`, **required**), `amount` (default `10000`), `market` (default `"us"`), `company_ticker` (default empty), and `timeframe` (default `"2y"`). Set `market: "india"` for Indian-market charts.

| Tool | Output |
|---|---|
| `generate_chart_pack` | full chart suite as Plotly JSON (for clients that render data) |
| `generate_charts` | summary + charts rendered as PNG images inline |
| `plot_charts` | alias of `generate_charts` for natural phrasing |
