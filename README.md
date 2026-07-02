# dg-skills

`npx skills` compatible repository for ETF macro research.

## Strategy

- 主视角：`中国`
- 辅助视角：`美国`、`全球`

## Structure

```text
skills/
  etf-macro-research/
    SKILL.md
    config/
    references/
    scripts/
    examples/
    evals/
```

## Install

```bash
npx skills add <owner>/<repo>@etf-macro-research
```

## Run

```bash
python3 skills/etf-macro-research/scripts/run_pipeline.py --region CN
python3 skills/etf-macro-research/scripts/generate_report.py
```

Outputs:

- `skills/etf-macro-research/data/latest_market_snapshot.json`
- `skills/etf-macro-research/data/latest_report_zh.md`

## Design principles

- Single version only (no v1/v2 split)
- Config-first extensibility (`config/modules.yaml`, `config/providers.yaml`)
- Stable output contract (JSON snapshot + Chinese markdown report)
