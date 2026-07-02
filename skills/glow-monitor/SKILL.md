---
name: "glow-monitor"
description: "霞光概率监测与推送（通用版）。当用户询问是否有晚霞、早霞、日出朝霞、夕阳概率、霞光预报等场景时触发。支持自动IP定位或手动指定城市（杭州/上海/北京/广州等30+城市），基于云量、云层结构、能见度、AQI、降水概率五项气象指标评分（0-100），通过macOS通知推送结果。"
agent_created: true
---

# 霞光监测 Skill（通用版）

自动监测任意城市的晚霞或次日早霞出现概率，基于多维气象数据评分并通过系统通知推送。

## 功能概述

1. **智能定位** - 自动IP定位（ip-api.com），或手动指定城市名/坐标
2. **双模式** - 晚霞模式（当日傍晚）和早霞模式（次日清晨）
3. **多维评分** - 云量 + 云层结构 + 能见度 + AQI + 降水概率，五项指标
4. **通知推送** - macOS 系统通知 + 可选企业微信 Webhook

## 使用方法

### 基本用法

```bash
# 自动定位，看今晚晚霞（默认）
python scripts/glow_monitor.py

# 指定城市，看今晚晚霞
python scripts/glow_monitor.py --city 杭州

# 指定城市，看次日早霞
python scripts/glow_monitor.py --city 上海 --mode dawn

# 用经纬度指定位置
python scripts/glow_monitor.py --lat 30.27 --lon 120.15

# 自动定位 + 早霞模式
python scripts/glow_monitor.py --mode dawn
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--city` | 城市中文名（杭州、上海、北京等） | 自动定位 |
| `--lat` `--lon` | 经纬度坐标 | 自动定位 |
| `--mode` | `sunset`=今晚晚霞 / `dawn`=次日早霞 | sunset |

### 支持的城市

杭州、上海、北京、广州、深圳、南京、苏州、成都、重庆、武汉、西安、郑州、长沙、青岛、大连、厦门、昆明、三亚、拉萨、哈尔滨、乌鲁木齐、香港、台北、东京、首尔、新加坡、纽约、伦敦、巴黎。

未列出的城市可用 `--lat`/`--lon` 坐标指定。

### 配置企业微信推送（可选）

```bash
export WECOM_WEBHOOK="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY"
```

## 评分逻辑

| 指标 | 权重 | 评分标准 |
|------|------|---------|
| 云量 | 40分 | 30-70% 满分；20-30%/70-80% 28分；其他递减 |
| 云层结构 | 15分 | 中低云分层理想满分；过厚或缺失扣分 |
| 能见度 | 25分 | ≥15km 满分；10-15km 18分；递减 |
| AQI | 15分 | ≤50 满分；≤100 11分；递减 |
| 降水概率 | 5分 | <20% 满分；递减 |

**分级标准：**
- 70+ 分：🔥🔥🔥 极高
- 55-69 分：✅✅ 较高，值得一看
- 35-54 分：😐 一般，碰碰运气
- <35 分：😞 很低

## 依赖

```bash
pip install requests
```

## API 说明

| API | 用途 | 是否需要Key |
|-----|------|------------|
| Open-Meteo (`api.open-meteo.com`) | 小时级天气预报 | 免费无Key |
| Sunrise-Sunset (`api.sunrise-sunset.org`) | 日出日落时间 | 免费无Key |
| WAQI (`api.waqi.info`) | 空气质量指数 | demo token |
| ip-api (`ip-api.com`) | IP自动定位 | 免费无Key |

## 文件结构

```
glow-monitor/
├── SKILL.md
├── scripts/
│   └── glow_monitor.py   # 主执行脚本
└── references/
```
