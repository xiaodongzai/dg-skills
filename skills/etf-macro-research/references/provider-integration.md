# Provider Integration Playbook

## Goal

Keep provider integration simple and replaceable.

## Rules

1. Add provider metadata in `config/providers.yaml` first.
2. Map external field names into internal metric ids from `references/data-dictionary.md`.
3. Never overwrite old fields silently; add new fields and deprecate explicitly.
4. If provider fails, keep pipeline output with missing fields and error list.

## Built-in providers

- `fred_graph_csv`
- `yahoo_chart_api`

## Add a new provider

1. Register provider in `config/providers.yaml`.
2. Extend `scripts/run_pipeline.py` with a fetch function and mapping section.
3. Keep output contract unchanged (`meta`, `metrics`, `quality`, `raw_preview`).
4. Update `references/data-dictionary.md` when adding new metrics.
