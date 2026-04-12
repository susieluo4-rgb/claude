"""告警历史读写 — SQLite 持久化"""

import sqlite3
import os
from datetime import datetime, timedelta
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "alert_history.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库表"""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS alert_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            name TEXT NOT NULL,
            alert_type TEXT NOT NULL,
            trigger_value REAL,
            threshold_value REAL,
            headline TEXT,
            source TEXT DEFAULT 'ifind',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sent_to_feishu BOOLEAN DEFAULT FALSE
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_code ON alert_history(code)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_created ON alert_history(created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_alert_type ON alert_history(alert_type)")
    conn.commit()
    conn.close()


def insert_alert(
    code: str,
    name: str,
    alert_type: str,
    trigger_value: float,
    threshold_value: float,
    headline: str = "",
    source: str = "ifind",
) -> int:
    """写入一条告警记录，返回自增 ID"""
    conn = get_connection()
    cur = conn.execute(
        """
        INSERT INTO alert_history
        (code, name, alert_type, trigger_value, threshold_value, headline, source)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (code, name, alert_type, trigger_value, threshold_value, headline, source),
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return row_id


def was_alerted_today(code: str, alert_type: str) -> bool:
    """检查该标的该类型今日是否已告警（去重）"""
    conn = get_connection()
    today = datetime.now().strftime("%Y-%m-%d")
    row = conn.execute(
        """
        SELECT 1 FROM alert_history
        WHERE code = ? AND alert_type = ?
        AND date(created_at) = date(?)
        LIMIT 1
        """,
        (code, alert_type, today),
    ).fetchone()
    conn.close()
    return row is not None


def query_history(
    days: int = 7,
    code: Optional[str] = None,
    alert_type: Optional[str] = None,
) -> list[dict]:
    """查询告警历史"""
    conn = get_connection()
    query = "SELECT * FROM alert_history WHERE 1=1"
    params = []

    if code:
        query += " AND code = ?"
        params.append(code)

    if alert_type:
        query += " AND alert_type = ?"
        params.append(alert_type)

    query += f" AND created_at >= datetime('now', '-{days} days')"
    query += " ORDER BY created_at DESC"

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_alert_summary(days: int = 7) -> dict:
    """获取告警汇总：按标的分组统计各类告警次数"""
    conn = get_connection()
    rows = conn.execute(
        f"""
        SELECT code, name, alert_type, COUNT(*) as cnt
        FROM alert_history
        WHERE created_at >= datetime('now', '-{days} days')
        GROUP BY code, alert_type
        ORDER BY cnt DESC
        """,
    ).fetchall()
    conn.close()

    # 按股票聚合
    by_stock = {}
    for row in rows:
        code = row["code"]
        if code not in by_stock:
            by_stock[code] = {"name": row["name"], "alerts": []}
        by_stock[code]["alerts"].append({"type": row["alert_type"], "count": row["cnt"]})
    return by_stock


def mark_sent_to_feishu(alert_id: int):
    """标记某条告警已发送飞书"""
    conn = get_connection()
    conn.execute(
        "UPDATE alert_history SET sent_to_feishu = 1 WHERE id = ?",
        (alert_id,),
    )
    conn.commit()
    conn.close()


def get_unsent_alerts() -> list[dict]:
    """获取未发送飞书的告警"""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM alert_history WHERE sent_to_feishu = 0 ORDER BY created_at ASC"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


# 初始化数据库
init_db()
