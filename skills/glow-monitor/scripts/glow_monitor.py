#!/usr/bin/env python3
"""
通用霞光监测脚本（晚霞 / 次日早霞）
支持自动IP定位或手动指定城市，评估霞光出现概率并推送通知。

用法:
  python glow_monitor.py                          # 自动定位，看今晚晚霞
  python glow_monitor.py --city 杭州              # 指定城市，看今晚晚霞
  python glow_monitor.py --city 上海 --mode dawn  # 指定城市，看明日早霞
  python glow_monitor.py --lat 30.27 --lon 120.15 # 用坐标
"""

import requests
import json
import subprocess
import argparse
import sys
import os
from datetime import datetime, timezone, timedelta

# ============================================================
# 常用城市坐标表（中文名 → lat, lon）
# ============================================================
CITY_DB = {
    "杭州": (30.2741, 120.1551),
    "上海": (31.2304, 121.4737),
    "北京": (39.9042, 116.4074),
    "广州": (23.1291, 113.2644),
    "深圳": (22.5431, 114.0579),
    "南京": (32.0603, 118.7969),
    "苏州": (31.2989, 120.5853),
    "成都": (30.5728, 104.0668),
    "重庆": (29.5630, 106.5516),
    "武汉": (30.5928, 114.3055),
    "西安": (34.3416, 108.9398),
    "郑州": (34.7466, 113.6253),
    "长沙": (28.2282, 112.9388),
    "青岛": (36.0671, 120.3826),
    "大连": (38.9140, 121.6147),
    "厦门": (24.4798, 118.0894),
    "昆明": (25.0389, 102.7183),
    "三亚": (18.2528, 109.5119),
    "拉萨": (29.6500, 91.1000),
    "哈尔滨": (45.8038, 126.5350),
    "乌鲁木齐": (43.8256, 87.6168),
    "香港": (22.3193, 114.1694),
    "台北": (25.0330, 121.5654),
    "东京": (35.6762, 139.6503),
    "首尔": (37.5665, 126.9780),
    "新加坡": (1.3521, 103.8198),
    "纽约": (40.7128, -74.0060),
    "伦敦": (51.5074, -0.1278),
    "巴黎": (48.8566, 2.3522),
}


# ============================================================
# 定位模块
# ============================================================
def ip_locate():
    """通过IP自动定位（使用 ip-api.com 免费服务）"""
    try:
        r = requests.get("http://ip-api.com/json/?lang=zh-CN", timeout=5)
        r.raise_for_status()
        d = r.json()
        if d.get("status") == "success":
            return d["lat"], d["lon"], d.get("city", "") or d.get("query", "")
    except Exception:
        pass
    # 备用：ipinfo.io
    try:
        r = requests.get("https://ipinfo.io/json", timeout=5)
        r.raise_for_status()
        d = r.json()
        loc = d.get("loc", "").split(",")
        if len(loc) == 2:
            return float(loc[0]), float(loc[1]), d.get("city", "")
    except Exception:
        pass
    return None, None, None


def resolve_city(name):
    """中文城市名 → 坐标"""
    name = name.strip()
    if name in CITY_DB:
        lat, lon = CITY_DB[name]
        return lat, lon, name
    print(f"⚠️  城市 '{name}' 不在预设表中，请用 --lat/--lon 指定坐标，"
          f"或从以下城市中选择：{', '.join(CITY_DB.keys())}")
    sys.exit(1)


# ============================================================
# 数据获取
# ============================================================
def get_weather(lat, lon, days=2):
    """Open-Meteo 小时级预报"""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ["cloud_cover", "visibility", "cloud_cover_low",
                   "cloud_cover_mid", "cloud_cover_high",
                   "precipitation_probability", "wind_speed_10m"],
        "timezone": "auto",
        "forecast_days": days,
    }
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    return r.json()


def get_sun_times(lat, lon, target_date=None):
    """获取日出日落时间。target_date: 'YYYY-MM-DD' 或 None(今天)"""
    url = "https://api.sunrise-sunset.org/json"
    params = {"lat": lat, "lng": lon, "formatted": 0}
    if target_date:
        params["date"] = target_date
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    return r.json()["results"]


def get_aqi(lat, lon):
    """基于坐标查 AQI（WAQI demo token）"""
    url = f"https://api.waqi.info/feed/geo:{lat};{lon}/?token=demo"
    try:
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        d = r.json()
        if d.get("status") == "ok":
            return d["data"]["aqi"], d["data"].get("city", {}).get("name", "")
    except Exception:
        pass
    return None, None


# ============================================================
# 评分引擎
# ============================================================
def score_glow(hourly, idx, aqi, mode):
    """
    霞光概率评分（0-100）
    mode: 'sunset' 晚霞 | 'dawn' 早霞
    评分维度：云量(40) + 云层结构(15) + 能见度(25) + AQI(15) + 降水(5)
    """
    score = 0
    reasons = []

    cloud = hourly["cloud_cover"][idx]
    if cloud is None:
        cloud = 50

    # ---- 云量(40分)：中低空有云最佳 ----
    if 30 <= cloud <= 70:
        score += 40
        reasons.append(f"云量 {cloud}% - 理想范围")
    elif 20 <= cloud < 30 or 70 < cloud <= 80:
        score += 28
        reasons.append(f"云量 {cloud}% - 边缘可看")
    elif 10 <= cloud < 20:
        score += 15
        reasons.append(f"云量 {cloud}% - 偏少，霞光面积受限")
    elif cloud > 80:
        score += 5
        reasons.append(f"云量 {cloud}% - 太厚，霞光被遮挡")
    else:
        reasons.append(f"云量 {cloud}% - 太晴，无云可映")

    # ---- 云层结构(15分)：中低空有云、高空较透 ----
    cl = hourly.get("cloud_cover_low", [None])[idx] if "cloud_cover_low" in hourly else None
    cm = hourly.get("cloud_cover_mid", [None])[idx] if "cloud_cover_mid" in hourly else None
    ch = hourly.get("cloud_cover_high", [None])[idx] if "cloud_cover_high" in hourly else None
    if cl is not None and cm is not None:
        if 20 <= cl <= 80 and 20 <= cm <= 80:
            score += 15
            reasons.append(f"低云{cl}%/中云{cm}% - 分层理想")
        elif cl > 80 and cm > 80:
            reasons.append(f"低云{cl}%/中云{cm}% - 均过厚")
        else:
            score += 8
            reasons.append(f"低云{cl}%/中云{cm}% - 一般")
    else:
        score += 8  # 无数据时给中等分

    # ---- 能见度(25分) ----
    vis_m = hourly["visibility"][idx]
    vis_km = (vis_m / 1000) if vis_m else 0
    if vis_km >= 15:
        score += 25
        reasons.append(f"能见度 {vis_km:.0f}km - 极好")
    elif vis_km >= 10:
        score += 18
        reasons.append(f"能见度 {vis_km:.0f}km - 良好")
    elif vis_km >= 5:
        score += 10
        reasons.append(f"能见度 {vis_km:.0f}km - 一般")
    else:
        reasons.append(f"能见度 {vis_km:.0f}km - 较差")

    # ---- AQI(15分) ----
    if aqi is not None:
        if aqi <= 50:
            score += 15
            reasons.append(f"AQI {aqi} - 优")
        elif aqi <= 100:
            score += 11
            reasons.append(f"AQI {aqi} - 良")
        elif aqi <= 150:
            score += 4
            reasons.append(f"AQI {aqi} - 轻度污染")
        else:
            reasons.append(f"AQI {aqi} - 污染较重")
    else:
        score += 8

    # ---- 降水概率(5分) ----
    precip = hourly["precipitation_probability"][idx]
    if precip is not None:
        if precip < 20:
            score += 5
            reasons.append(f"降水概率 {precip}% - 无雨")
        elif precip < 50:
            score += 2
            reasons.append(f"降水概率 {precip}% - 可能有雨")
        else:
            reasons.append(f"降水概率 {precip}% - 大概率下雨")

    return score, reasons


def grade(score):
    """评分分级"""
    if score >= 70:
        return "🔥🔥🔥 极高", "🔥"
    elif score >= 55:
        return "✅✅ 较高，值得一看", "✅"
    elif score >= 35:
        return "😐 一般，碰碰运气", "😐"
    else:
        return "😞 很低", "😞"


# ============================================================
# 通知推送
# ============================================================
def notify_macos(title, msg):
    script = f'display notification "{msg}" with title "{title}"'
    try:
        subprocess.run(["osascript", "-e", script], timeout=5)
    except Exception:
        pass


def notify_wechat(msg):
    webhook = os.environ.get("WECOM_WEBHOOK")
    if not webhook:
        return False
    try:
        requests.post(webhook, json={"msgtype": "text", "text": {"content": msg}}, timeout=5)
        return True
    except Exception:
        return False


# ============================================================
# 主流程
# ============================================================
def find_hourly_index(times, target_dt, local_tz):
    """在小时数组中找到最接近 target_dt 的索引"""
    best_idx, best_diff = 0, float("inf")
    for i, t in enumerate(times):
        dt = datetime.fromisoformat(t).astimezone(local_tz)
        diff = abs((dt - target_dt).total_seconds())
        if diff < best_diff:
            best_diff = diff
            best_idx = i
    return best_idx


def run(lat, lon, city_name, mode):
    local_tz = timezone(timedelta(hours=8))  # 简化：默认东八区
    # 尝试从天气API返回的时区做更精确的偏移
    now = datetime.now(local_tz)

    is_dawn = (mode == "dawn")
    glow_label = "早霞" if is_dawn else "晚霞"
    target_date_label = "明日" if is_dawn else "今日"

    print(f"\n{'='*55}")
    print(f"  {glow_label}监测  {now.strftime('%Y-%m-%d %H:%M')}")
    print(f"  地点: {city_name} ({lat:.4f}, {lon:.4f})")
    print(f"{'='*55}")

    # 1. 天气数据
    print(f"\n[1/4] 获取气象数据...")
    weather = get_weather(lat, lon, days=2)
    hourly = weather["hourly"]
    times = hourly["time"]

    # 获取实际时区偏移
    tz_str = weather.get("timezone_abbreviator", "GMT+8")
    utc_offset = weather.get("utc_offset_seconds", 28800)
    local_tz = timezone(timedelta(seconds=utc_offset))

    # 2. 日出/日落时间
    print(f"[2/4] 获取{'明日' if is_dawn else '今日'}日出/日落时间...")
    target_date_str = None
    if is_dawn:
        tomorrow = now + timedelta(days=1)
        target_date_str = tomorrow.strftime("%Y-%m-%d")
    try:
        sun = get_sun_times(lat, lon, target_date_str)
        if is_dawn:
            key_time = datetime.fromisoformat(sun["sunrise"]).astimezone(local_tz)
            print(f"   明日日出: {key_time.strftime('%H:%M')}")
        else:
            key_time = datetime.fromisoformat(sun["sunset"]).astimezone(local_tz)
            print(f"   今日日落: {key_time.strftime('%H:%M')}")
    except Exception as e:
        print(f"   ⚠️ 获取失败: {e}，使用默认时间")
        key_time = now.replace(hour=6 if is_dawn else 19, minute=0)

    # 3. AQI
    print(f"[3/4] 获取AQI...")
    aqi, aqi_city = get_aqi(lat, lon)
    if aqi:
        print(f"   AQI: {aqi}" + (f" ({aqi_city})" if aqi_city else ""))
    else:
        print("   AQI 获取失败，继续评分")

    # 4. 找到目标小时 + 日落前/日出前1小时
    print(f"\n[4/4] 评估{glow_label}概率...")
    best_idx = find_hourly_index(times, key_time, local_tz)
    eval_time = datetime.fromisoformat(times[best_idx]).astimezone(local_tz)

    # 提前1小时（霞光最早出现）
    pre_time = key_time - timedelta(hours=1)
    pre_idx = find_hourly_index(times, pre_time, local_tz)

    score, reasons = score_glow(hourly, best_idx, aqi, mode)

    # 比较"目标时刻"和"提前1小时"，取高分
    score_pre, reasons_pre = score_glow(hourly, pre_idx, aqi, mode)
    if score_pre > score:
        score, reasons = score_pre, reasons_pre
        eval_time = datetime.fromisoformat(times[pre_idx]).astimezone(local_tz)
        print(f"   （以{eval_time.strftime('%H:%M')}数据为准，霞光窗口更佳）")
    else:
        print(f"   评估时段: {eval_time.strftime('%H:%M')}")

    # 结果
    level, emoji = grade(score)
    print(f"\n{'='*55}")
    print(f"  {target_date_label}{glow_label}概率: {score}/100  {level}")
    print(f"\n  详细分析:")
    for r in reasons:
        print(f"    · {r}")

    key_str = key_time.strftime('%H:%M')
    print(f"\n  📍 最佳观测时间: {key_str} 前后30分钟")
    if is_dawn:
        print(f"  📍 建议: 面朝东方，找一个开阔无遮挡的地点")
    else:
        print(f"  📍 建议: 面朝西方，西湖/河边/高楼观景台均为佳选")

    # 通知
    title = f"{emoji} {city_name} {glow_label} {score}/100"
    msg = f"{key_str}{'日出' if is_dawn else '日落'} | " + reasons[0]
    print(f"\n{'='*55}")
    notify_macos(title, msg)
    print("  ✓ macOS 通知已发送")

    full_msg = f"{emoji} {city_name}{target_date_label}{glow_label}评分 {score}/100\n" \
               f"{'日出' if is_dawn else '日落'}时间 {key_str}\n" + "\n".join(reasons)
    if notify_wechat(full_msg):
        print("  ✓ 企业微信通知已发送")

    print(f"\n{'='*55}")

    return {"score": score, "level": level, "reasons": reasons,
            "key_time": key_str, "city": city_name, "mode": mode}


def main():
    parser = argparse.ArgumentParser(description="通用霞光监测（晚霞/早霞）")
    parser.add_argument("--city", type=str, default=None,
                        help="城市名（中文），如：杭州、上海")
    parser.add_argument("--lat", type=float, default=None, help="纬度")
    parser.add_argument("--lon", type=float, default=None, help="经度")
    parser.add_argument("--mode", type=str, default="sunset",
                        choices=["sunset", "dawn"],
                        help="sunset=今晚晚霞(默认) | dawn=次日早霞")
    args = parser.parse_args()

    # 定位优先级：--lat/--lon > --city > IP自动定位
    if args.lat is not None and args.lon is not None:
        lat, lon, name = args.lat, args.lon, f"({args.lat}, {args.lon})"
    elif args.city:
        lat, lon, name = resolve_city(args.city)
    else:
        print("📡 正在通过IP定位...")
        lat, lon, name = ip_locate()
        if lat is None:
            print("❌ 自动定位失败，请用 --city 或 --lat/--lon 指定位置")
            sys.exit(1)
        print(f"   定位到: {name} ({lat:.4f}, {lon:.4f})")

    run(lat, lon, name, args.mode)


if __name__ == "__main__":
    main()
