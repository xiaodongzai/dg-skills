# Workflow

## 1) Input normalization

Required:

- investment region (CN/US/GLOBAL)
- holding horizon (short/medium/long)
- risk profile (conservative/balanced/aggressive)

Optional:

- benchmark (CSI300/SPY/ACWI etc.)
- banned sectors/assets

## 2) Collect baseline data (executable)

Run (China-first default):

```bash
python3 skills/etf-macro-research/scripts/run_pipeline.py --region CN
```

Alternative:

```bash
python3 skills/etf-macro-research/scripts/run_pipeline.py --region US
python3 skills/etf-macro-research/scripts/run_pipeline.py --region GLOBAL
```

Output file:

- `skills/etf-macro-research/data/latest_market_snapshot.json`

Current live providers:

- FRED public CSV (macro time series)
- Yahoo Chart API (cross-asset + sector ETF/index prices)

## 3) Generate Chinese report (executable)

Run:

```bash
python3 skills/etf-macro-research/scripts/generate_report.py
```

Output file:

- `skills/etf-macro-research/data/latest_report_zh.md`

## 4) Data blocks covered now

- Macro: growth proxy, inflation trend, policy direction, liquidity trend
- Cross-asset: equity momentum, yield change, credit spread proxy, commodity momentum, dollar momentum
- Industry prosperity board: sector/theme momentum-volatility ranking
- Earnings state board: profit/credit/labor proxy composite
- Supplementary signals: US/global equity momentum

## 5) Scoring

- normalize each metric to 0-100
- aggregate by module weights
- map total score to regime label

## 6) ETF mapping

Map top sectors/themes into tradable ETFs by region and liquidity preference.

## 7) Risk control

Include concentration risk, valuation risk, liquidity risk, and policy/event risk.
