# Tool Reference

All 25 tools, grouped the way you'd use them. Parameters marked **required**; everything else has a sensible default.

Common parameter: `period` — history window. One of `1d` `5d` `1mo` `3mo` `6mo` `1y` `2y` `5y` `10y` `ytd` `max`. Default `2y` unless noted.

---

## Trader workflow

### `get_quote`

Price snapshot for one or many tickers in a single call.

| Param | Type | Notes |
|---|---|---|
| `tickers` | `string[]` **required** | e.g. `["AAPL", "RELIANCE.NS"]` |

Returns per ticker: `last_price`, `previous_close`, `day_change_pct`, `day_range`, `52w_range`, `pct_of_52w_range`, `volume`, `volume_vs_3mo_avg`, `currency`, `exchange`. Top level: `as_of` timestamp + `data_delay_note` (US near-real-time, NSE ~15 min delayed). One bad ticker never breaks the batch.

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

Returns: `entry` (last close), `stop` (tighter of 10-bar swing level or 2×ATR, floored at 0.75 ATR so daily noise can't tag it), `stop_basis`, `shares` (sized so a stop-out loses exactly the risk budget, capped by equity — no implicit leverage), `position_value`, `max_loss`, `targets` (1R/2R/3R), `liquidity` (your order as % of 20-day turnover, with a warning above ~1%), and a one-line `invalidation`.

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

Note: CCI is computed in-house — the upstream pandas_ta implementation has a broken formula (see [Architecture](architecture.md)).

---

## Portfolio

### `generate_optimized_verdict`

Optimize → backtest → risk-blend → verdict, in one call.

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

All three take `tickers[]` (**required**), `amount`, `market`, `company_ticker`, `timeframe`.

| Tool | Output |
|---|---|
| `generate_chart_pack` | full chart suite as Plotly JSON (for clients that render data) |
| `generate_charts` | summary + charts rendered as PNG images inline |
| `plot_charts` | alias of `generate_charts` for natural phrasing |
