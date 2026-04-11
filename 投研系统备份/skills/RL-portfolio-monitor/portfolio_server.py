#!/usr/bin/env python3
"""
持仓监控 — 本地 HTTP 服务器

提供交互式 HTML 报告 + API 端点：
- GET  /                          → 交互版 HTML 报告
- GET  /api/refresh_price/<code>  → 刷新单只股票行情
- GET  /api/refresh_prices        → 刷新所有持仓行情
- GET  /api/refresh_alert/<code>  → 刷新单只股票全量告警
- GET  /api/refresh_all           → 刷新所有持仓全量告警
"""

import json
import os
import sys
import time
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor, as_completed
import socketserver

class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

sys.path.insert(0, os.path.dirname(__file__))

from portfolio_loader import load_portfolio_config
from alert_history import insert_alert, was_alerted_today
from feishu_formatter import format_single_alert

# 导入主脚本的函数
import importlib.util
_main_path = os.path.join(os.path.dirname(__file__), "portfolio_monitor.py")
_spec = importlib.util.spec_from_file_location("monitor", _main_path)
_monitor = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_monitor)

fetch_performance = _monitor.fetch_performance
scan_single_holding = _monitor.scan_single_holding
scan_all_announcements = _monitor.scan_all_announcements
get_announcement_badge = _monitor.get_announcement_badge
generate_html_report = _monitor.generate_html_report
generate_interactive_html = _monitor.generate_interactive_html

# 全局状态
_all_perf_data = []
_triggered_alerts = []
_holdings = []
_last_refresh_time = ""
_ann_data = {}  # {code: {tag, title, badge_html}, ...}


def _load_holdings():
    global _holdings, _all_perf_data, _last_refresh_time
    try:
        _holdings = load_portfolio_config()
        _all_perf_data = []
        _last_refresh_time = time.strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        print(f"加载持仓失败：{e}")


def _refresh_all_prices():
    """刷新所有持仓价格（不做告警判断）"""
    global _all_perf_data
    results = []
    for h in _holdings:
        perf = fetch_performance(h["code"], h["name"])
        has_data = bool(perf.get("price", 0))
        ann = _ann_data.get(h["code"])
        results.append({
            "code": h["code"],
            "name": h["name"],
            "position_pct": h["position_pct"],
            "change_pct": perf.get("change_pct", 0),
            "price": perf.get("price", 0),
            "has_data": has_data,
            "ann_badge": ann["badge_html"] if ann else '<span class="badge-ann-neutral">无新公告</span>',
        })
        time.sleep(0.3)
    _all_perf_data = results
    return results


def _refresh_all_alerts():
    """刷新所有持仓全量告警"""
    global _triggered_alerts, _all_perf_data
    alerts = []
    perf_data = []
    for h in _holdings:
        a, perf = scan_single_holding(h)
        has_data = bool(perf.get("price", 0))
        perf_data.append({
            "code": h["code"],
            "name": h["name"],
            "position_pct": h["position_pct"],
            "change_pct": perf.get("change_pct", 0),
            "price": perf.get("price", 0),
            "has_data": has_data,
        })
        for alert in a:
            alert_id = insert_alert(
                code=h["code"],
                name=h["name"],
                alert_type=alert["type"],
                trigger_value=alert["trigger_value"],
                threshold_value=alert["threshold_value"],
                headline=alert.get("headline", ""),
            )
            alert["id"] = alert_id
            alert["code"] = h["code"]
            alert["name"] = h["name"]
            alerts.append(alert)
        time.sleep(0.5)
    _triggered_alerts = alerts
    _all_perf_data = perf_data
    return alerts, perf_data


class PortfolioHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self._serve_index()
        elif path.startswith("/api/refresh_price/"):
            code = path.split("/")[-1]
            self._api_refresh_price(code)
        elif path == "/api/refresh_prices":
            self._api_refresh_prices()
        elif path.startswith("/api/refresh_alert/"):
            code = path.split("/")[-1]
            self._api_refresh_alert(code)
        elif path == "/api/refresh_all":
            self._api_refresh_all()
        elif path == "/api/status":
            self._api_status()
        elif path == "/api/refresh_announcements":
            self._api_refresh_announcements()
        else:
            self.send_error(404)

    def _serve_index(self):
        html = generate_interactive_html(_all_perf_data, _triggered_alerts, _last_refresh_time)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def _api_refresh_price(self, code):
        holding = next((h for h in _holdings if h["code"] == code or h["code"].startswith(code)), None)
        if not holding:
            self._json(404, {"error": "未找到持仓"})
            return
        perf = fetch_performance(holding["code"], holding["name"])
        has_data = bool(perf.get("price", 0))
        ann = _ann_data.get(holding["code"])
        result = {
            "code": holding["code"],
            "name": holding["name"],
            "position_pct": holding["position_pct"],
            "change_pct": perf.get("change_pct", 0),
            "price": perf.get("price", 0),
            "has_data": has_data,
            "ann_badge": ann["badge_html"] if ann else '<span class="badge-ann-neutral">无新公告</span>',
        }
        # 更新全局数据
        for i, d in enumerate(_all_perf_data):
            if d["code"] == holding["code"]:
                _all_perf_data[i] = result
                break
        self._json(200, result)

    def _api_refresh_prices(self):
        """批量刷新所有价格"""
        results = _refresh_all_prices()
        count = sum(1 for r in results if r["has_data"])
        self._json(200, {"count": len(results), "ok": count, "data": results})

    def _api_refresh_alert(self, code):
        holding = next((h for h in _holdings if h["code"] == code or h["code"].startswith(code)), None)
        if not holding:
            self._json(404, {"error": "未找到持仓"})
            return
        alerts, perf = scan_single_holding(holding)
        has_data = bool(perf.get("price", 0))
        perf_entry = {
            "code": holding["code"],
            "name": holding["name"],
            "position_pct": holding["position_pct"],
            "change_pct": perf.get("change_pct", 0),
            "price": perf.get("price", 0),
            "has_data": has_data,
        }
        for i, d in enumerate(_all_perf_data):
            if d["code"] == holding["code"]:
                _all_perf_data[i] = perf_entry
                break
        result_alerts = []
        for a in alerts:
            alert_id = insert_alert(
                code=holding["code"],
                name=holding["name"],
                alert_type=a["type"],
                trigger_value=a["trigger_value"],
                threshold_value=a["threshold_value"],
                headline=a.get("headline", ""),
            )
            a["id"] = alert_id
            a["code"] = holding["code"]
            a["name"] = holding["name"]
            result_alerts.append(a)
            _triggered_alerts.append(a)
        self._json(200, {"alerts": result_alerts, "perf": perf_entry})

    def _api_refresh_all(self):
        """全量刷新（后台线程执行，不阻塞 HTTP 响应）"""
        self._json(200, {"status": "started"})
        threading.Thread(target=_refresh_all_alerts, daemon=True).start()

    def _api_status(self):
        self._json(200, {
            "total": len(_all_perf_data),
            "with_data": sum(1 for d in _all_perf_data if d.get("has_data")),
            "alerts": len(_triggered_alerts),
            "last_refresh": _last_refresh_time,
            "holdings_count": len(_holdings),
        })

    def _api_refresh_announcements(self):
        """扫描所有持仓公告情感"""
        global _ann_data
        results = scan_all_announcements()
        # 按 code 分组，每只股票取最新一条
        ann_by_code = {}
        for a in results:
            code = a["code"]
            if code not in ann_by_code:
                badge_html = get_announcement_badge(a["tag"])
                ann_by_code[code] = {
                    "tag": a["tag"],
                    "title": a["title"][:30],
                    "sentiment": a["sentiment"],
                    "badge_html": f'<span title="{a["title"][:30]}">{badge_html} {a["title"][:30]}</span>',
                }
        _ann_data = ann_by_code
        self._json(200, {"data": ann_by_code, "count": len(ann_by_code)})

    def _json(self, code, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        # 静默日志
        pass


def run_server(host="0.0.0.0", port=8765):
    _load_holdings()
    server = ReusableTCPServer((host, port), PortfolioHandler)
    url = f"http://{host}:{port}"
    print(f"持仓监控服务已启动：{url}")
    print(f"共 {len(_holdings)} 只持仓")

    # 后台线程加载初始数据
    def _initial_load():
        global _last_refresh_time
        print("初始加载持仓价格数据...")
        _refresh_all_prices()
        _last_refresh_time = time.strftime("%Y-%m-%d %H:%M:%S")
        print("初始加载完成")

    threading.Thread(target=_initial_load, daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="持仓监控 HTTP 服务")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    run_server(args.host, args.port)
