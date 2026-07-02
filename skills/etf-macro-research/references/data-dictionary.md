# Data Dictionary

## 宏观

- gdp_nowcast: 增长代理（工业生产同比）
- inflation_trend: 通胀同比趋势
- policy_rate_direction: 利率方向（tightening/easing/hold）
- liquidity_proxy: 流动性趋势（M2同比）

## 跨资产

- equity_momentum_3m
- bond_yield_change_3m
- credit_spread_change_3m
- commodity_momentum_3m
- dxy_momentum_3m

## 行业景气（代理）

- sector_trend_score_top3_avg: 行业景气Top3平均分
- sector_breadth_positive_3m: 近3个月上涨行业占比

## 盈利状态（代理）

- corporate_profits_yoy: 企业利润同比（FRED: CP）
- corporate_profits_qoq: 企业利润环比（FRED: CP）
- credit_spread_level: 信用利差水平（FRED: BAA10YM）
- unemployment_change_3m: 失业率3个月变化（FRED: UNRATE）
- earnings_state_score: 盈利状态综合分
