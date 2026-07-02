#!/usr/bin/env python3
"""Generate Chinese Markdown ETF report from snapshot JSON."""

from __future__ import annotations

import argparse
import json
import pathlib
from typing import Any, Dict, List


def _get(d: Dict[str, Any], key: str, default: str = "N/A") -> Any:
    v = d.get(key)
    if v is None:
        return default
    return v


def _regime_label(metrics: Dict[str, Any]) -> str:
    score = 0
    if metrics.get("policy_rate_direction") in ("easing", "宽松"):
        score += 1
    if (metrics.get("liquidity_proxy") or -999) > 0:
        score += 1
    if (metrics.get("equity_momentum_3m") or -999) > 0:
        score += 1
    if (metrics.get("credit_spread_change_3m") or 999) < 0:
        score += 1

    if score >= 3:
        return "偏风险偏好（Risk-on）"
    if score == 2:
        return "过渡阶段（Neutral/Transition）"
    return "偏防御（Risk-off）"


def _format_board(rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return "- 暂无数据\n"
    out = "| 行业 | 代码 | 近1月动量% | 近3月动量% | 近3月波动% | 景气度分数 |\n"
    out += "|---|---:|---:|---:|---:|---:|\n"
    for r in rows:
        out += (
            f"| {r.get('行业','N/A')} | {r.get('代码','N/A')} | {r.get('近1月动量%','N/A')} | "
            f"{r.get('近3月动量%','N/A')} | {r.get('近3月波动%','N/A')} | {r.get('景气度分数','N/A')} |\n"
        )
    return out


def _etf_candidates(snapshot: Dict[str, Any]) -> List[Dict[str, str]]:
    top = snapshot.get("industry_prosperity_board", {}).get("top5", [])
    out = []
    for r in top[:3]:
        out.append(
            {
                "ticker": str(r.get("代码", "N/A")),
                "行业": str(r.get("行业", "N/A")),
                "理由": f"景气度分数 {r.get('景气度分数', 'N/A')}，3月动量 {r.get('近3月动量%', 'N/A')}%",
                "风险": "若信用环境恶化或波动显著上行，需减仓",
            }
        )
    return out


def _safe_num(v: Any, default: float = 0.0) -> float:
    try:
        if v is None:
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def _stance(score: float) -> str:
    if score >= 0.35:
        return "增配"
    if score <= -0.35:
        return "低配"
    return "中性"


def _horizon_view(score: float) -> Dict[str, str]:
    if score >= 0.45:
        return {"短期": "偏强", "中期": "偏强", "长期": "中性偏强"}
    if score >= 0.15:
        return {"短期": "中性偏强", "中期": "偏强", "长期": "中性"}
    if score <= -0.45:
        return {"短期": "偏弱", "中期": "偏弱", "长期": "中性偏弱"}
    if score <= -0.15:
        return {"短期": "中性偏弱", "中期": "偏弱", "长期": "中性"}
    return {"短期": "中性", "中期": "中性", "长期": "中性"}


def _marginal_change(score: float, equity: float, liquidity: float, earnings: float) -> str:
    delta = 0.0
    if equity > 0:
        delta += 0.15
    if liquidity > 0:
        delta += 0.15
    if earnings >= 60:
        delta += 0.2
    if score < 0:
        delta -= 0.1
    if delta >= 0.3:
        return "改善"
    if delta <= -0.2:
        return "走弱"
    return "平稳"


def _build_csi_logic(metrics: Dict[str, Any]) -> List[Dict[str, str]]:
    policy = str(metrics.get("policy_rate_direction", "中性"))
    liquidity = _safe_num(metrics.get("liquidity_proxy"))
    commodity = _safe_num(metrics.get("commodity_momentum_3m"))
    equity = _safe_num(metrics.get("equity_momentum_3m"))
    dxy = _safe_num(metrics.get("dxy_momentum_3m"))
    earnings = _safe_num(metrics.get("earnings_state_score"))
    rows: List[Dict[str, str]] = []

    def add(name: str, score: float, logic: str, watch: str, trigger: str) -> None:
        hv = _horizon_view(score)
        rows.append(
            {
                "行业": name,
                "建议": _stance(score),
                "短期": hv["短期"],
                "中期": hv["中期"],
                "长期": hv["长期"],
                "边际变化": _marginal_change(score, equity, liquidity, earnings),
                "当前投资逻辑": logic,
                "重点观察": watch,
                "触发条件": trigger,
            }
        )

    add(
        "能源",
        0.35 + (0.2 if commodity > 5 else -0.1),
        f"商品动量{commodity:.2f}%仍偏强，能源现金流弹性相对更高，适合作为周期对冲仓位。",
        "油价趋势、库存变化、地缘供给扰动",
        "若商品动量连续2期>5%且库存去化，可从中性上调至增配",
    )
    add(
        "原材料",
        0.15 + (0.15 if commodity > 5 else -0.1),
        f"在流动性{liquidity:.2f}%扩张背景下，原材料受补库与价格弹性支撑，但需防需求不及预期。",
        "工业品价格、地产链开工、库存周期",
        "若工业品价格与库存周期共振向上，提升到增配",
    )
    add(
        "工业",
        0.20 + (0.1 if equity > 0 else -0.1),
        f"权益动量{equity:.2f}%略偏正，工业板块受稳增长与设备更新预期支撑，建议择优配置。",
        "制造业PMI、订单/产能利用率、出口增速",
        "若PMI与新订单连续回升，短期由中性偏强转偏强",
    )
    add(
        "可选消费",
        -0.05 + (0.1 if earnings >= 60 else -0.1),
        f"盈利状态分数{earnings:.2f}尚可，但消费修复节奏分化，建议偏结构性而非全面进攻。",
        "社零同比、居民收入预期、线上线下景气差",
        "若社零与就业预期同步改善，可提高1档",
    )
    add(
        "主要消费",
        0.15 + (0.05 if policy in ("宽松", "中性") else -0.1),
        f"政策方向为{policy}，防御属性仍有配置价值，适合作为组合波动缓冲。",
        "必选消费龙头提价能力、渠道库存、成本端变化",
        "若成本下行且提价兑现，盈利弹性增强后提高评级",
    )
    add(
        "医药卫生",
        0.10 + (0.1 if policy in ("宽松", "中性") else -0.1),
        f"流动性环境偏友好，医药处于估值修复与业绩分化并行阶段，可中期布局。",
        "医保政策、创新药出海、院内外需求恢复",
        "若集采扰动减弱且创新药商业化加速，转偏强",
    )
    add(
        "金融地产",
        -0.15 + (0.1 if policy == "宽松" else 0.0),
        f"当前政策{policy}下，金融地产更多依赖稳增长与信用扩张确认，短期仍以低位博弈为主。",
        "社融增速、按揭/开发贷、不良与拨备趋势",
        "若社融与地产销售连续改善，可从中性偏弱上修",
    )
    add(
        "信息技术",
        0.20 + (0.1 if dxy < 0 else -0.05),
        f"美元动量{dxy:.2f}%偏弱对成长风格相对友好，科技板块以景气赛道与盈利兑现为主线。",
        "AI/算力资本开支、半导体周期、估值消化速度",
        "若订单增速与盈利预告同步上修，可提升至增配",
    )
    add(
        "电信业务",
        0.05 + (0.05 if equity >= 0 else 0.0),
        f"在风险偏好温和修复阶段，电信业务兼具现金流与低波动属性，适合底仓配置。",
        "运营商资本开支、云业务增速、分红政策",
        "若云业务增速超预期且分红提升，可由中性转偏强",
    )
    add(
        "公用事业",
        0.10 + (0.1 if equity < 2 else -0.05),
        f"权益动量并不极强，公用事业的防御+分红特征仍有吸引力，可作为组合稳定器。",
        "煤电气价格联动、负债成本、分红持续性",
        "若利率中枢下行且分红预期上修，可提升配置",
    )
    add(
        "通信服务",
        0.10 + (0.1 if earnings >= 60 else -0.05),
        f"盈利环境({earnings:.2f})对通信服务板块形成支撑，关注平台经济与内容生态修复弹性。",
        "广告景气、用户时长、监管边际变化",
        "若广告景气和监管环境双改善，建议上调",
    )

    return rows


def main() -> int:
    root = pathlib.Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Generate Chinese markdown report")
    parser.add_argument(
        "--input",
        default=str(root / "data" / "latest_market_snapshot.json"),
        help="Input snapshot JSON",
    )
    parser.add_argument(
        "--output",
        default=str(root / "data" / "latest_report_zh.md"),
        help="Output markdown path",
    )
    args = parser.parse_args()

    snapshot = json.loads(pathlib.Path(args.input).read_text(encoding="utf-8"))
    meta = snapshot.get("meta", {})
    metrics = snapshot.get("metrics", {})
    quality = snapshot.get("quality", {})
    industry = snapshot.get("industry_prosperity_board", {})
    earnings = snapshot.get("earnings_quality_board", {})
    supplement = snapshot.get("supplementary_signals", {})

    regime = _regime_label(metrics)
    cands = _etf_candidates(snapshot)
    csi_rows = _build_csi_logic(metrics)

    lines: List[str] = []
    lines.append("# ETF投研报告（中文）")
    lines.append("")
    lines.append(f"- 生成日期(UTC): {_get(meta, 'as_of_utc')}")
    aux = meta.get("辅助视角")
    if isinstance(aux, list):
        aux_str = "、".join(str(x) for x in aux)
    else:
        aux_str = str(aux) if aux is not None else "N/A"
    lines.append(f"- 主视角区域: {_get(meta, 'region_label', _get(meta, 'region'))}")
    lines.append(f"- 主视角: {_get(meta, '主视角')}")
    lines.append(f"- 辅助视角: {aux_str}")
    lines.append(f"- 数据覆盖率: {_get(quality, 'coverage')}")
    lines.append("")

    lines.append("## 执行摘要")
    lines.append(
        f"当前市场处于**{regime}**。流动性趋势({_get(metrics, 'liquidity_proxy')}%)与政策方向({_get(metrics, 'policy_rate_direction')})"
        f"对风险资产形成一定支撑，但权益3个月动量({_get(metrics, 'equity_momentum_3m')}%)提示短期分化。"
    )
    lines.append("")

    lines.append("## 宏观阶段")
    lines.append(f"- 增长代理(gdp_nowcast): {_get(metrics, 'gdp_nowcast')}%")
    lines.append(f"- 通胀趋势(inflation_trend): {_get(metrics, 'inflation_trend')}%")
    lines.append(f"- 利率方向(policy_rate_direction): {_get(metrics, 'policy_rate_direction')}")
    lines.append(f"- 3个月政策利率变化: {_get(metrics, 'policy_rate_change_3m')}")
    lines.append(f"- 流动性趋势(liquidity_proxy): {_get(metrics, 'liquidity_proxy')}%")
    lines.append("")
    lines.append("### 美国/全球辅助信号")
    lines.append(f"- 美国股市3个月动量: {_get(supplement, '美国股市3月动量%')}%")
    lines.append(f"- 全球股市3个月动量: {_get(supplement, '全球股市3月动量%')}%")
    lines.append("")

    lines.append("## 行业景气看板")
    lines.append(f"- 行业广度(近3月上涨占比): {_get(metrics, 'sector_breadth_positive_3m')}%")
    lines.append(f"- Top3景气平均分: {_get(metrics, 'sector_trend_score_top3_avg')}")
    lines.append("")
    lines.append("### 领先行业 Top5")
    lines.append(_format_board(industry.get("top5", [])))
    lines.append("### 偏弱行业 Bottom3")
    lines.append(_format_board(industry.get("bottom3", [])))
    lines.append("")
    lines.append("## 中证一级行业投资逻辑（11行业，多视角）")
    for r in csi_rows:
        lines.append(f"### {r['行业']}")
        lines.append(f"- 建议：{r['建议']}")
        lines.append(f"- 时间视角：短期 {r['短期']} / 中期 {r['中期']} / 长期 {r['长期']}")
        lines.append(f"- 边际变化：{r['边际变化']}")
        lines.append(f"- 当前投资逻辑：{r['当前投资逻辑']}")
        lines.append(f"- 重点观察：{r['重点观察']}")
        lines.append(f"- 触发条件：{r['触发条件']}")
        lines.append("")
    lines.append("")

    lines.append("## 盈利状态看板")
    lines.append(f"- 状态: {_get(earnings, '状态')}")
    lines.append(f"- 综合分数: {_get(earnings, '分数')}")
    for x in earnings.get("指标明细", []):
        lines.append(f"- {x.get('指标', 'N/A')}: {x.get('值', 'N/A')} ({x.get('方向', 'N/A')})")
    lines.append("")

    lines.append("## ETF候选清单")
    if cands:
        lines.append("| 代码 | 行业 | 核心理由 | 主要风险 |")
        lines.append("|---:|---|---|---|")
        for c in cands:
            lines.append(f"| {c['ticker']} | {c['行业']} | {c['理由']} | {c['风险']} |")
    else:
        lines.append("- 暂无候选")
    lines.append("")

    lines.append("## 行动计划")
    lines.append("1. 按 40%/30%/30% 分批建仓，避免单点择时。")
    lines.append("2. 若信用利差持续走扩或行业广度快速收缩，降低进攻仓位。")
    lines.append("3. 每月滚动更新一次快照并复核行业排名变化。")
    lines.append("")
    lines.append("> 免责声明：本报告仅用于研究与流程演示，不构成任何投资建议。")

    out_path = pathlib.Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote report: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
