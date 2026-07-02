#!/usr/bin/env python3
"""Fetch macro/cross-asset/industry/earnings proxy signals with region profiles.

Default region is CN (China-first), with US/global supplementary signals.
Dependencies: Python stdlib only.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import pathlib
import statistics
import urllib.parse
import urllib.request
from typing import Dict, List, Optional, Tuple


REGION_PROFILES = {
    "CN": {
        "label": "中国",
        "fred_series": {
            "inflation_cpi": "CHNCPIALLMINMEI",      # China CPI index
            "policy_rate": "IRSTCI01CNM156N",        # China short-term rate
            "liquidity_proxy": "CHXRSA",             # China reserves proxy
            "corporate_profits": "CP",              # fallback global proxy
            "credit_spread_baa10y": "BAA10YM",      # fallback global credit condition
            "unemployment": "UNRATE",               # fallback global labor condition
        },
        "symbols": {
            "equity": "ASHR",                       # China A-share ETF
            "growth_proxy_equity": "000300.SS",     # CSI 300 index
            "treasury_10y_yield": "^TNX",          # global rate reference
            "credit_hy": "HYG",
            "credit_ig": "IEF",
            "commodity": "DBC",
            "dollar_proxy": "UUP",
            "supplement_us_equity": "SPY",
            "supplement_global_equity": "ACWI",
        },
        "sector_etfs": {
            "A股宽基": "ASHR",
            "中国大盘": "FXI",
            "中国全市场": "MCHI",
            "中国互联网": "KWEB",
            "中国科技": "CQQQ",
            "中国消费": "CHIQ",
            "中国中概精选": "PGJ",
            "中国A股综合": "CNYA",
            "中国新经济": "CNXT",
            "中国ESG": "CXSE",
            "中国清洁能源": "KGRN",
        },
    },
    "US": {
        "label": "美国",
        "fred_series": {
            "gdp_nowcast_proxy": "INDPRO",
            "inflation_cpi": "CPIAUCSL",
            "policy_rate": "FEDFUNDS",
            "liquidity_proxy": "M2SL",
            "corporate_profits": "CP",
            "credit_spread_baa10y": "BAA10YM",
            "unemployment": "UNRATE",
        },
        "symbols": {
            "equity": "SPY",
            "growth_proxy_equity": "SPY",
            "treasury_10y_yield": "^TNX",
            "credit_hy": "HYG",
            "credit_ig": "IEF",
            "commodity": "DBC",
            "dollar_proxy": "UUP",
            "supplement_us_equity": "SPY",
            "supplement_global_equity": "ACWI",
        },
        "sector_etfs": {
            "信息技术": "XLK",
            "通信服务": "XLC",
            "可选消费": "XLY",
            "必须消费": "XLP",
            "医疗保健": "XLV",
            "金融": "XLF",
            "工业": "XLI",
            "能源": "XLE",
            "原材料": "XLB",
            "公用事业": "XLU",
            "房地产": "XLRE",
        },
    },
    "GLOBAL": {
        "label": "全球",
        "fred_series": {
            "inflation_cpi": "CPIAUCSL",             # fallback reference
            "policy_rate": "FEDFUNDS",
            "liquidity_proxy": "M2SL",
            "corporate_profits": "CP",
            "credit_spread_baa10y": "BAA10YM",
            "unemployment": "UNRATE",
        },
        "symbols": {
            "equity": "ACWI",
            "growth_proxy_equity": "ACWI",
            "treasury_10y_yield": "^TNX",
            "credit_hy": "HYG",
            "credit_ig": "IEF",
            "commodity": "DBC",
            "dollar_proxy": "UUP",
            "supplement_us_equity": "SPY",
            "supplement_global_equity": "ACWI",
        },
        "sector_etfs": {
            "全球宽基": "ACWI",
            "全球发达": "VEA",
            "新兴市场": "EEM",
            "全球科技": "IXN",
            "全球金融": "IXG",
            "全球能源": "IXC",
            "全球医疗": "IXJ",
            "全球消费": "IXP",
        },
    },
}


def _http_get_text(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


def _http_get_json(url: str, timeout: int = 20) -> dict:
    return json.loads(_http_get_text(url, timeout=timeout))


def fetch_fred_series(series_id: str) -> List[Tuple[str, float]]:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={urllib.parse.quote(series_id)}"
    text = _http_get_text(url)
    rows: List[Tuple[str, float]] = []
    reader = csv.DictReader(text.splitlines())
    for row in reader:
        if not row:
            continue
        date_key = next((k for k in row.keys() if k and "date" in k.lower()), None)
        date_s = row.get(date_key) if date_key else None
        value_s = row.get(series_id) or row.get("VALUE") or row.get("value")
        if not date_s or not value_s or value_s == ".":
            continue
        try:
            value = float(value_s)
        except ValueError:
            continue
        rows.append((date_s, value))
    return rows


def fetch_yahoo_close_series(symbol: str, range_: str = "1y", interval: str = "1d") -> List[Tuple[str, float]]:
    symbol_q = urllib.parse.quote(symbol, safe="")
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol_q}"
        f"?range={urllib.parse.quote(range_)}&interval={urllib.parse.quote(interval)}"
    )
    payload = _http_get_json(url)
    chart = payload.get("chart", {})
    if chart.get("error"):
        raise RuntimeError(f"Yahoo error for {symbol}: {chart['error']}")
    result = (chart.get("result") or [None])[0]
    if not result:
        raise RuntimeError(f"No Yahoo data for {symbol}")

    ts = result.get("timestamp") or []
    quote = ((result.get("indicators") or {}).get("quote") or [None])[0] or {}
    closes = quote.get("close") or []

    rows: List[Tuple[str, float]] = []
    for t, c in zip(ts, closes):
        if c is None or (isinstance(c, float) and math.isnan(c)):
            continue
        date_s = dt.datetime.fromtimestamp(int(t), dt.UTC).strftime("%Y-%m-%d")
        rows.append((date_s, float(c)))
    return rows


def pct_change(series: List[Tuple[str, float]], lookback: int) -> Optional[float]:
    if len(series) <= lookback:
        return None
    old = series[-lookback - 1][1]
    new = series[-1][1]
    if old == 0:
        return None
    return (new / old - 1.0) * 100.0


def abs_change(series: List[Tuple[str, float]], lookback: int) -> Optional[float]:
    if len(series) <= lookback:
        return None
    return series[-1][1] - series[-lookback - 1][1]


def yoy_change(series: List[Tuple[str, float]], periods: int) -> Optional[float]:
    return pct_change(series, periods)


def round_or_none(v: Optional[float], ndigits: int = 2) -> Optional[float]:
    return None if v is None else round(v, ndigits)


def _daily_returns(series: List[Tuple[str, float]]) -> List[float]:
    prices = [p for _, p in series]
    out: List[float] = []
    for i in range(1, len(prices)):
        prev = prices[i - 1]
        cur = prices[i]
        if prev > 0:
            out.append(cur / prev - 1.0)
    return out


def _volatility_3m(series: List[Tuple[str, float]], lookback_days: int = 63) -> Optional[float]:
    if len(series) < lookback_days + 1:
        return None
    rets = _daily_returns(series[-(lookback_days + 1):])
    if len(rets) < 2:
        return None
    return statistics.pstdev(rets) * math.sqrt(252) * 100.0


def _score_from_range(value: Optional[float], low: float, high: float, invert: bool = False) -> Optional[float]:
    if value is None or high == low:
        return None
    clipped = max(low, min(high, value))
    score = (clipped - low) / (high - low) * 100.0
    return 100.0 - score if invert else score


def _safe_avg(values: List[Optional[float]]) -> Optional[float]:
    clean = [v for v in values if v is not None]
    return None if not clean else sum(clean) / len(clean)


def _fetch_fred_map(series_map: Dict[str, str], errors: List[str]) -> Dict[str, List[Tuple[str, float]]]:
    out: Dict[str, List[Tuple[str, float]]] = {}
    for key, sid in series_map.items():
        try:
            out[key] = fetch_fred_series(sid)
        except Exception as exc:  # noqa: BLE001
            out[key] = []
            errors.append(f"FRED {sid}: {exc}")
    return out


def _fetch_yahoo_map(symbol_map: Dict[str, str], errors: List[str]) -> Dict[str, List[Tuple[str, float]]]:
    out: Dict[str, List[Tuple[str, float]]] = {}
    for key, sym in symbol_map.items():
        try:
            out[key] = fetch_yahoo_close_series(sym)
        except Exception as exc:  # noqa: BLE001
            out[key] = []
            errors.append(f"Yahoo {sym}: {exc}")
    return out


def build_snapshot(region: str = "CN") -> Dict[str, object]:
    region = region.upper()
    profile = REGION_PROFILES.get(region)
    if not profile:
        raise ValueError(f"Unsupported region: {region}")

    today = dt.datetime.now(dt.UTC).strftime("%Y-%m-%d")
    errors: List[str] = []

    fred_data = _fetch_fred_map(profile["fred_series"], errors)
    yahoo_data = _fetch_yahoo_map(profile["symbols"], errors)

    sector_data = {}
    for sector_name, symbol in profile["sector_etfs"].items():
        try:
            series = fetch_yahoo_close_series(symbol)
            if series:
                sector_data[sector_name] = series
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Yahoo {symbol}: {exc}")

    # Macro block (region-aware proxies)
    if region == "US":
        gdp_nowcast = yoy_change(fred_data.get("gdp_nowcast_proxy", []), 12)
    else:
        # For market-index proxy, use ~6m lookback to avoid sparse-history nulls.
        gdp_nowcast = pct_change(yahoo_data.get("growth_proxy_equity", []), 126)

    inflation_trend = yoy_change(fred_data.get("inflation_cpi", []), 12)
    policy_rate_change_3m = abs_change(fred_data.get("policy_rate", []), 3)
    liquidity_proxy = yoy_change(fred_data.get("liquidity_proxy", []), 12)

    if policy_rate_change_3m is None:
        policy_rate_direction = None
    elif policy_rate_change_3m > 0.10:
        policy_rate_direction = "收紧"
    elif policy_rate_change_3m < -0.10:
        policy_rate_direction = "宽松"
    else:
        policy_rate_direction = "中性"

    # Cross-asset block
    equity_momentum_3m = pct_change(yahoo_data.get("equity", []), 63)
    bond_yield_change_3m = abs_change(yahoo_data.get("treasury_10y_yield", []), 63)
    hyg_ret_3m = pct_change(yahoo_data.get("credit_hy", []), 63)
    ig_ret_3m = pct_change(yahoo_data.get("credit_ig", []), 63)
    credit_spread_change_3m = (hyg_ret_3m - ig_ret_3m) if (hyg_ret_3m is not None and ig_ret_3m is not None) else None
    commodity_momentum_3m = pct_change(yahoo_data.get("commodity", []), 63)
    dxy_momentum_3m = pct_change(yahoo_data.get("dollar_proxy", []), 63)

    # Supplementary US/Global block
    supplement_us_3m = pct_change(yahoo_data.get("supplement_us_equity", []), 63)
    supplement_global_3m = pct_change(yahoo_data.get("supplement_global_equity", []), 63)

    # Industry prosperity board
    sector_rows = []
    for sector_name, series in sector_data.items():
        mom_1m = pct_change(series, 21)
        mom_3m = pct_change(series, 63)
        vol_3m = _volatility_3m(series, 63)
        trend_score = _safe_avg([
            _score_from_range(mom_1m, -15, 15),
            _score_from_range(mom_3m, -30, 30),
            _score_from_range(vol_3m, 5, 45, invert=True),
        ])
        sector_rows.append(
            {
                "行业": sector_name,
                "代码": profile["sector_etfs"][sector_name],
                "近1月动量%": round_or_none(mom_1m),
                "近3月动量%": round_or_none(mom_3m),
                "近3月波动%": round_or_none(vol_3m),
                "景气度分数": round_or_none(trend_score),
            }
        )
    sector_rows_sorted = sorted(
        sector_rows,
        key=lambda x: (x["景气度分数"] is None, -(x["景气度分数"] or -9999)),
    )
    positive_3m = [r for r in sector_rows if (r["近3月动量%"] is not None and r["近3月动量%"] > 0)]
    sector_breadth_positive_3m = (len(positive_3m) / len(sector_rows) * 100.0) if sector_rows else None
    top3_avg = _safe_avg([r["景气度分数"] for r in sector_rows_sorted[:3]])

    # Earnings state board (proxy)
    corporate_profits_yoy = yoy_change(fred_data.get("corporate_profits", []), 4)
    corporate_profits_qoq = pct_change(fred_data.get("corporate_profits", []), 1)
    credit_spread_level_series = fred_data.get("credit_spread_baa10y", [])
    credit_spread_level = credit_spread_level_series[-1][1] if credit_spread_level_series else None
    unemployment_change_3m = abs_change(fred_data.get("unemployment", []), 3)

    earnings_rows = [
        {"指标": "企业利润同比", "值": round_or_none(corporate_profits_yoy), "方向": "正向" if (corporate_profits_yoy or -999) > 0 else "负向"},
        {"指标": "企业利润环比", "值": round_or_none(corporate_profits_qoq), "方向": "正向" if (corporate_profits_qoq or -999) > 0 else "负向"},
        {"指标": "信用利差水平(BAA-10Y)", "值": round_or_none(credit_spread_level), "方向": "正向" if (credit_spread_level is not None and credit_spread_level < 2.2) else "负向"},
        {"指标": "失业率3个月变化", "值": round_or_none(unemployment_change_3m, 3), "方向": "正向" if (unemployment_change_3m is not None and unemployment_change_3m <= 0) else "负向"},
    ]
    earnings_score = _safe_avg([
        _score_from_range(corporate_profits_yoy, -15, 20),
        _score_from_range(corporate_profits_qoq, -8, 8),
        _score_from_range(credit_spread_level, 0.8, 3.5, invert=True),
        _score_from_range(unemployment_change_3m, -0.5, 0.8, invert=True),
    ])
    if earnings_score is None:
        earnings_label = None
    elif earnings_score >= 65:
        earnings_label = "盈利扩张"
    elif earnings_score >= 45:
        earnings_label = "盈利平稳"
    else:
        earnings_label = "盈利承压"

    metrics = {
        "gdp_nowcast": round_or_none(gdp_nowcast),
        "inflation_trend": round_or_none(inflation_trend),
        "policy_rate_direction": policy_rate_direction,
        "policy_rate_change_3m": round_or_none(policy_rate_change_3m, 3),
        "liquidity_proxy": round_or_none(liquidity_proxy),
        "equity_momentum_3m": round_or_none(equity_momentum_3m),
        "bond_yield_change_3m": round_or_none(bond_yield_change_3m, 3),
        "credit_spread_change_3m": round_or_none(credit_spread_change_3m),
        "commodity_momentum_3m": round_or_none(commodity_momentum_3m),
        "dxy_momentum_3m": round_or_none(dxy_momentum_3m),
        "sector_trend_score_top3_avg": round_or_none(top3_avg),
        "sector_breadth_positive_3m": round_or_none(sector_breadth_positive_3m),
        "corporate_profits_yoy": round_or_none(corporate_profits_yoy),
        "corporate_profits_qoq": round_or_none(corporate_profits_qoq),
        "credit_spread_level": round_or_none(credit_spread_level),
        "unemployment_change_3m": round_or_none(unemployment_change_3m, 3),
        "earnings_state_score": round_or_none(earnings_score),
        "supplement_us_equity_momentum_3m": round_or_none(supplement_us_3m),
        "supplement_global_equity_momentum_3m": round_or_none(supplement_global_3m),
    }

    available_count = sum(1 for v in metrics.values() if v is not None)
    coverage = round(available_count / len(metrics), 3)

    return {
        "meta": {
            "as_of_utc": today,
            "region": region,
            "region_label": profile["label"],
            "主视角": "中国" if region == "CN" else profile["label"],
            "辅助视角": ["美国", "全球"],
            "providers": ["fred_graph_csv", "yahoo_chart_api"],
            "报告章节": ["执行摘要", "宏观阶段", "行业景气看板", "盈利状态看板", "ETF候选清单", "行动计划"],
        },
        "metrics": metrics,
        "industry_prosperity_board": {
            "top5": sector_rows_sorted[:5],
            "bottom3": list(reversed(sector_rows_sorted[-3:])),
        },
        "earnings_quality_board": {
            "状态": earnings_label,
            "分数": round_or_none(earnings_score),
            "指标明细": earnings_rows,
        },
        "supplementary_signals": {
            "美国股市3月动量%": round_or_none(supplement_us_3m),
            "全球股市3月动量%": round_or_none(supplement_global_3m),
        },
        "quality": {
            "coverage": coverage,
            "missing_metrics": [k for k, v in metrics.items() if v is None],
            "errors": errors,
        },
        "raw_preview": {
            "fred_last": {k: (v[-1] if v else None) for k, v in fred_data.items()},
            "yahoo_last": {k: (v[-1] if v else None) for k, v in yahoo_data.items()},
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run ETF macro data pipeline")
    parser.add_argument("--region", default="CN", choices=["CN", "US", "GLOBAL"], help="Primary region, default CN")
    parser.add_argument(
        "--output",
        default=str(pathlib.Path(__file__).resolve().parents[1] / "data" / "latest_market_snapshot.json"),
        help="Output JSON file path",
    )
    args = parser.parse_args()

    snapshot = build_snapshot(region=args.region)
    out_path = pathlib.Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Wrote snapshot: {out_path}")
    print(f"Region: {args.region}")
    print(f"Coverage: {snapshot['quality']['coverage']}")
    if snapshot["quality"]["errors"]:
        print("Warnings:")
        for err in snapshot["quality"]["errors"][:10]:
            print(f"- {err}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
