#!/usr/bin/env python3
"""
持仓监控 — 本地 HTTP 服务器（多组合版）

提供交互式 HTML 报告 + API 端点：
- GET  /                                 → 多组合 Tab HTML 报告
- GET  /api/refresh_price/<code>         → 刷新单只股票行情
- GET  /api/refresh_prices               → 刷新所有持仓行情
- GET  /api/refresh_alert/<code>         → 刷新单只股票全量告警
- GET  /api/refresh_all                  → 刷新所有持仓全量告警
- GET  /api/portfolio/<name>/refresh      → 刷新指定组合
"""

import json
import os
import sys
import time
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor, as_completed
import socketserver

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

sys.path.insert(0, os.path.dirname(__file__))

from portfolio_loader import load_portfolio_config, get_all_portfolios, get_portfolio_name
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
generate_interactive_multi_html = _monitor.generate_interactive_multi_html

# 全局状态：{portfolio_name: {"holdings": [...], "perf_data": [...], "alerts": [...]}}
_portfolios = {}
_last_refresh_time = ""
_ann_data = {}  # {code: {tag, title, badge_html}, ...}


def _load_all_portfolios():
    """加载所有组合持仓配置"""
    global _portfolios
    all_p = get_all_portfolios()
    _portfolios = {}
    for p in all_p:
        name = p["name"]
        path = p["path"]
        try:
            holdings = load_portfolio_config(path)
        except Exception as e:
            print(f"加载组合 {name} 失败：{e}")
            continue
        _portfolios[name] = {
            "holdings": holdings,
            "perf_data": [],
            "alerts": [],
        }
    return _portfolios


def _refresh_all_prices():
    """刷新所有组合所有持仓价格"""
    global _portfolios, _ann_data
    for name, state in _portfolios.items():
        results = []
        for h in state["holdings"]:
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
        _portfolios[name]["perf_data"] = results
    return _portfolios


def _refresh_all_alerts():
    """刷新所有组合全量告警"""
    global _portfolios
    for name, state in _portfolios.items():
        alerts = []
        perf_data = []
        for h in state["holdings"]:
            a, perf = scan_single_holding(h)
            has_data = bool(perf.get("price", 0))
            perf_data.append({
                "code": h["code"], "name": h["name"],
                "position_pct": h["position_pct"],
                "change_pct": perf.get("change_pct", 0),
                "price": perf.get("price", 0), "has_data": has_data,
            })
            for alert in a:
                alert_id = insert_alert(
                    code=h["code"], name=h["name"], alert_type=alert["type"],
                    trigger_value=alert["trigger_value"], threshold_value=alert["threshold_value"],
                    headline=alert.get("headline", ""),
                )
                alert["id"] = alert_id
                alert["code"] = h["code"]
                alert["name"] = h["name"]
                alert["portfolio"] = name
                alerts.append(alert)
            time.sleep(0.5)
        _portfolios[name]["alerts"] = alerts
        _portfolios[name]["perf_data"] = perf_data
    return _portfolios


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
        elif path.startswith("/api/portfolio/"):
            # /api/portfolio/<name>/refresh
            parts = path.split("/")
            if len(parts) >= 4:
                name = parts[2]
                self._api_refresh_portfolio(name)
            else:
                self.send_error(404)
        else:
            self.send_error(404)

    def _serve_index(self):
        # 收集所有组合数据用于 HTML 生成
        portfolio_results = {}
        for name, state in _portfolios.items():
            portfolio_results[name] = {
                "alerts": state.get("alerts", []),
                "perf_data": state.get("perf_data", []),
            }
        if not portfolio_results:
            self._json(500, {"error": "未加载任何组合"})
            return
        # 构建 holdings_map 用于 API 刷新
        holdings_map = {}
        for name, state in _portfolios.items():
            holdings_map[name] = [
                {"code": h["code"], "name": h["name"], "position_pct": h["position_pct"]}
                for h in state["holdings"]
            ]
        # 使用交互式多组合 HTML（带刷新按钮）
        from datetime import date
        today = date.today().isoformat()
        html_path = os.path.expanduser(
            f"~/.claude/skills/rl-portfolio-monitor/reports/_server_{today}.html"
        )
        os.makedirs(os.path.dirname(html_path), exist_ok=True)
        path_used = generate_interactive_multi_html(
            portfolio_results, holdings_map, html_path
        )
        with open(path_used, "r", encoding="utf-8") as f:
            html = f.read()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def _find_holding(self, code):
        """在所有组合中查找持仓"""
        for name, state in _portfolios.items():
            for h in state["holdings"]:
                if h["code"] == code or h["code"].startswith(code):
                    return name, h
        return None, None

    def _api_refresh_price(self, code):
        name, holding = self._find_holding(code)
        if not holding:
            self._json(404, {"error": "未找到持仓"})
            return
        perf = fetch_performance(holding["code"], holding["name"])
        has_data = bool(perf.get("price", 0))
        ann = _ann_data.get(holding["code"])
        result = {
            "code": holding["code"], "name": holding["name"],
            "position_pct": holding["position_pct"],
            "change_pct": perf.get("change_pct", 0),
            "price": perf.get("price", 0), "has_data": has_data,
            "ann_badge": ann["badge_html"] if ann else '<span class="badge-ann-neutral">无新公告</span>',
        }
        # 更新全局数据
        for i, d in enumerate(_portfolios[name]["perf_data"]):
            if d["code"] == holding["code"]:
                _portfolios[name]["perf_data"][i] = result
                break
        self._json(200, result)

    def _api_refresh_prices(self):
        _refresh_all_prices()
        flat = []
        for name, state in _portfolios.items():
            flat.extend(state["perf_data"])
        count = sum(1 for r in flat if r["has_data"])
        self._json(200, {"count": len(flat), "ok": count, "data": flat})

    def _api_refresh_alert(self, code):
        name, holding = self._find_holding(code)
        if not holding:
            self._json(404, {"error": "未找到持仓"})
            return
        alerts, perf = scan_single_holding(holding)
        has_data = bool(perf.get("price", 0))
        perf_entry = {
            "code": holding["code"], "name": holding["name"],
            "position_pct": holding["position_pct"],
            "change_pct": perf.get("change_pct", 0),
            "price": perf.get("price", 0), "has_data": has_data,
        }
        # 更新 perf_data
        found = False
        for i, d in enumerate(_portfolios[name]["perf_data"]):
            if d["code"] == holding["code"]:
                _portfolios[name]["perf_data"][i] = perf_entry
                found = True
                break
        if not found:
            _portfolios[name]["perf_data"].append(perf_entry)
        result_alerts = []
        for a in alerts:
            alert_id = insert_alert(
                code=holding["code"], name=holding["name"], alert_type=a["type"],
                trigger_value=a["trigger_value"], threshold_value=a["threshold_value"],
                headline=a.get("headline", ""),
            )
            a["id"] = alert_id
            a["code"] = holding["code"]
            a["name"] = holding["name"]
            a["portfolio"] = name
            result_alerts.append(a)
            _portfolios[name]["alerts"].append(a)
        self._json(200, {"alerts": result_alerts, "perf": perf_entry})

    def _api_refresh_all(self):
        """全量刷新（后台线程执行）"""
        self._json(200, {"status": "started"})
        threading.Thread(target=_refresh_all_alerts, daemon=True).start()

    def _api_refresh_portfolio(self, name):
        """刷新指定组合"""
        if name not in _portfolios:
            self._json(404, {"error": f"未找到组合 {name}"})
            return
        state = _portfolios[name]
        alerts = []
        perf_data = []
        for h in state["holdings"]:
            a, perf = scan_single_holding(h)
            has_data = bool(perf.get("price", 0))
            perf_data.append({
                "code": h["code"], "name": h["name"],
                "position_pct": h["position_pct"],
                "change_pct": perf.get("change_pct", 0),
                "price": perf.get("price", 0), "has_data": has_data,
            })
            for alert in a:
                alert["portfolio"] = name
                alerts.append(alert)
            time.sleep(0.5)
        _portfolios[name]["alerts"] = alerts
        _portfolios[name]["perf_data"] = perf_data
        self._json(200, {"name": name, "alerts": alerts, "perf_data": perf_data})

    def _api_status(self):
        total = sum(len(s["perf_data"]) for s in _portfolios.values())
        with_data = sum(1 for s in _portfolios.values() for d in s["perf_data"] if d.get("has_data"))
        alerts = sum(len(s["alerts"]) for s in _portfolios.values())
        holdings_count = sum(len(s["holdings"]) for s in _portfolios.values())
        self._json(200, {
            "total": total, "with_data": with_data,
            "alerts": alerts, "last_refresh": _last_refresh_time,
            "holdings_count": holdings_count,
            "portfolios": list(_portfolios.keys()),
        })

    def _api_refresh_announcements(self):
        global _ann_data
        results = scan_all_announcements()
        ann_by_code = {}
        for a in results:
            code = a["code"]
            if code not in ann_by_code:
                badge_html = get_announcement_badge(a["tag"])
                ann_by_code[code] = {
                    "tag": a["tag"], "title": a["title"][:30],
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
        pass


def run_server(host="0.0.0.0", port=8765):
    _load_all_portfolios()
    total = sum(len(s["holdings"]) for s in _portfolios.values())
    print(f"持仓监控服务已启动：http://127.0.0.1:{port}")
    print(f"共 {len(_portfolios)} 个组合，{total} 只持仓")

    # 先启动服务器，后台异步加载初始数据
    server = ThreadedHTTPServer((host, port), PortfolioHandler)

    global _last_refresh_time
    print("后台加载持仓价格数据...")
    def _init_load():
        global _last_refresh_time
        _refresh_all_prices()
        _last_refresh_time = time.strftime("%Y-%m-%d %H:%M:%S")
        print("初始加载完成")
    threading.Thread(target=_init_load, daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="持仓监控 HTTP 服务（多组合版）")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    run_server(args.host, args.port)
