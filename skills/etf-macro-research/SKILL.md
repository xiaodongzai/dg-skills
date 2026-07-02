---
name: etf-macro-research
description: Analyze ETF opportunities with China as the primary region and US/global as supplementary views, covering macro cycle, industry prosperity, and earnings state. Use this whenever users ask for ETF allocation, sector rotation, China-focused market regime analysis, or repeatable ETF research workflows.
---

# ETF Macro Research

Build ETF research from a repeatable pipeline instead of ad-hoc opinions.

## 默认视角

- 主视角：`中国`（CN）
- 辅助视角：`美国`、`全球`

## When triggered

Run this skill when user asks for:

- ETF investment analysis or allocation suggestions
- China-focused macro/industry/earnings analysis
- Global asset cycle interpretation (equity, bond, commodity, FX, credit)
- Industry prosperity comparison and ranking
- Repeatable/follow-up research process

## Core workflow

1. Clarify objective and scope: region, horizon, risk preference, benchmark.
2. Pull baseline data via `scripts/run_pipeline.py`.
3. Score each module with configurable weights.
4. Produce final ETF shortlist and risk notes.
5. Output markdown report and machine-readable JSON.

## Executable entry

From repo root, run:

```bash
python3 skills/etf-macro-research/scripts/run_pipeline.py --region CN
python3 skills/etf-macro-research/scripts/generate_report.py
```

Note:

- `--region` supports `CN` / `US` / `GLOBAL`
- default is `CN`

## 中文报告结构（优先）

1. `执行摘要`
2. `宏观阶段`
3. `行业景气看板`
4. `盈利状态看板`
5. `ETF候选清单`
6. `行动计划`

If data is missing:

- Explicitly mark missing fields.
- Avoid fabricating values.
- Lower confidence score and explain why.

## Extensibility rules

For extensions, follow these files:

- `config/modules.yaml`: module registry and weights
- `config/providers.yaml`: provider registry and region profile strategy
- `references/scoring-framework.md`: factor scoring logic
- `references/data-dictionary.md`: metric definitions and units
- `references/provider-integration.md`: provider extension playbook

Add new module/provider by editing config first, then update references.

## References

- Read `references/workflow.md` for end-to-end execution.
- Read `references/scoring-framework.md` when changing scoring logic.
- Read `references/data-dictionary.md` when adding metrics.
