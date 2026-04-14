#!/usr/bin/env python3
"""
新浪财经实时行情查询

独立脚本，可 CLI 调用或作为模块导入。

用法：
    python3 fetch_price.py --code 300750.SZ
    python3 fetch_price.py --code 01801.HK
    python3 fetch_price.py --code 920438.BJ
"""

import argparse
import json
import re
import sys
from urllib.request import urlopen, Request


def _normalize_code(code: str) -> str:
    """港股代码去前导零"""
    if ".HK" in code.upper():
        parts = code.split(".")
        parts[0] = parts[0].lstrip("0") or "0"
        return ".".join(parts)
    return code


def fetch_price_sina(code: str) -> dict:
    """通过新浪财经免费 API 获取实时行情

    Args:
        code: 股票代码，如 "300750.SZ", "01801.HK", "920438.BJ"

    Returns:
        dict 包含 price, change_pct, yesterday_close, open, high, low, volume, turnover
        失败返回 {}
    """
    try:
        parts = code.split(".")
        num, market = parts[0], parts[1] if len(parts) > 1 else "SZ"

        if market == "SZ":
            sina_code = f"sz{num}"
        elif market == "SH":
            sina_code = f"sh{num}"
        elif market == "HK":
            sina_code = f"hk{num.zfill(5)}"
        elif market == "BJ":
            sina_code = f"bj{num}"
        else:
            sina_code = f"sz{num}"

        url = f"https://hq.sinajs.cn/list={sina_code}"
        req = Request(url, headers={"Referer": "https://finance.sina.com.cn"})
        data = urlopen(req, timeout=10).read().decode("gbk")

        match = re.search(r'="(.+?)"', data)
        if not match:
            return {}

        fields = match.group(1).split(",")

        if market in ("SZ", "SH"):
            # A股: 名称, 昨收, 开盘, 现价, 最高, 最低, 买一, 卖一, 成交量, 成交额
            price = float(fields[3])
            yesterday = float(fields[1])
            if price <= 0 or yesterday <= 0:
                return {}
            return {
                "name": fields[0],
                "price": price,
                "change_pct": round((price - yesterday) / yesterday * 100, 4),
                "yesterday_close": yesterday,
                "open": float(fields[2]),
                "high": float(fields[4]),
                "low": float(fields[5]),
                "volume": int(fields[8]),
                "turnover": float(fields[9]),
            }
        elif market == "BJ":
            # 北交所: 名称, 开盘, 昨收, 现价, 最高, 最低（与A股字段顺序不同！）
            price = float(fields[3])
            yesterday = float(fields[2])
            if price <= 0 or yesterday <= 0:
                return {}
            return {
                "name": fields[0],
                "price": price,
                "change_pct": round((price - yesterday) / yesterday * 100, 4),
                "yesterday_close": yesterday,
                "open": float(fields[1]),
                "high": float(fields[4]),
                "low": float(fields[5]),
                "volume": int(fields[8]),
                "turnover": float(fields[9]),
            }
        elif market == "HK":
            # 港股: 英文名, 中文名, 开盘, 昨收, 最高, 最低, 现价, 涨跌额, 涨跌幅(小数), 成交量, 成交额
            price = float(fields[6])
            yesterday = float(fields[3])
            if price <= 0 or yesterday <= 0:
                return {}
            return {
                "name": fields[1],
                "price": price,
                "change_pct": round((price - yesterday) / yesterday * 100, 4),
                "yesterday_close": yesterday,
                "open": float(fields[2]),
                "high": float(fields[4]),
                "low": float(fields[5]),
                "volume": int(float(fields[9])) if fields[9] else 0,
                "turnover": float(fields[10]) if fields[10] else 0,
            }
        return {}
    except Exception:
        return {}


def main():
    parser = argparse.ArgumentParser(description="新浪财经实时行情查询")
    parser.add_argument("--code", required=True, help="股票代码，如 300750.SZ, 01801.HK, 920438.BJ")
    parser.add_argument("--pretty", action="store_true", help="美化输出")
    args = parser.parse_args()

    result = fetch_price_sina(args.code)
    if result:
        indent = 2 if args.pretty else None
        print(json.dumps(result, ensure_ascii=False, indent=indent))
    else:
        print(json.dumps({"error": "未获取到数据"}, ensure_ascii=False, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
