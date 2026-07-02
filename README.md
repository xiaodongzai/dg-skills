# dg-skills

AI Agent Skills 合集仓库，兼容 `npx skills` / WorkBuddy 等 skill 管理工具。

## Skills 一览

| Skill | 说明 | 安装 |
|-------|------|------|
| **glow-monitor** | 霞光概率监测（晚霞/早霞），支持自动IP定位或指定城市，五维气象评分 + macOS通知推送 | `npx skills add xiaodongzai/dg-skills@glow-monitor` |
| **etf-macro-research** | ETF 宏观策略研究流水线（中国视角），生成市场快照 + 中文研报 | `npx skills add xiaodongzai/dg-skills@etf-macro-research` |

## Structure

```text
skills/
  glow-monitor/              # 霞光监测
    SKILL.md
    scripts/
      glow_monitor.py

  etf-macro-research/        # ETF 宏观研究
    SKILL.md
    config/
    references/
    scripts/
    examples/
    evals/
```

## glow-monitor — 霞光监测

基于云量、云层结构、能见度、AQI、降水概率五项气象指标，评估晚霞或次日早霞出现概率（0-100分）。

```bash
# 自动定位，看今晚晚霞
python3 skills/glow-monitor/scripts/glow_monitor.py

# 指定城市，看次日早霞
python3 skills/glow-monitor/scripts/glow_monitor.py --city 上海 --mode dawn
```

支持 30+ 城市（杭州/上海/北京/广州/深圳/郑州/西安/成都/…），也支持 `--lat`/`--lon` 自定义坐标。

## etf-macro-research — ETF 宏观研究

```bash
python3 skills/etf-macro-research/scripts/run_pipeline.py --region CN
python3 skills/etf-macro-research/scripts/generate_report.py
```

- 主视角：中国；辅助视角：美国、全球
- 输出：`latest_market_snapshot.json` + `latest_report_zh.md`

## Design principles

- Single version per skill (no v1/v2 split)
- Config-first extensibility
- Stable output contract
- Zero-API-key by default (所有 skill 默认使用免费 API)
