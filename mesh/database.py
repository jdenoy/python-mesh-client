from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import List

from .models import Message, NodeEntry

DB_PATH = Path(__file__).resolve().parent.parent / "mesh_client.db"


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


_local = threading.local()


def _conn() -> sqlite3.Connection:
    if not hasattr(_local, "conn"):
        _local.conn = _get_connection()
    return _local.conn


def init_db():
    conn = _conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS messages (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            text        TEXT NOT NULL,
            from_id     TEXT NOT NULL,
            to_id       TEXT NOT NULL,
            channel_index INTEGER DEFAULT 0,
            from_name   TEXT DEFAULT '',
            rx_time     REAL NOT NULL,
            rx_snr      REAL DEFAULT 0,
            packet_id   INTEGER DEFAULT 0,
            is_outgoing INTEGER DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_msg_channel ON messages(channel_index);
        CREATE INDEX IF NOT EXISTS idx_msg_time ON messages(rx_time);

        CREATE TABLE IF NOT EXISTS node_cache (
            node_id     TEXT PRIMARY KEY,
            node_num    INTEGER,
            long_name   TEXT DEFAULT '',
            short_name  TEXT DEFAULT '',
            hw_model    TEXT DEFAULT '',
            role        TEXT DEFAULT '',
            battery_level INTEGER,
            voltage     REAL,
            channel_util REAL,
            air_util_tx REAL,
            uptime_seconds INTEGER,
            snr         REAL,
            hops_away   INTEGER,
            last_heard  REAL,
            latitude    REAL,
            longitude   REAL,
            altitude    INTEGER
        );
    """)
    conn.commit()


def save_message(msg: Message) -> int:
    conn = _conn()
    cur = conn.execute(
        """INSERT INTO messages
           (text, from_id, to_id, channel_index, from_name, rx_time, rx_snr, packet_id, is_outgoing)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            msg.text,
            msg.from_id,
            msg.to_id,
            msg.channel_index,
            msg.from_name,
            msg.rx_time,
            msg.rx_snr,
            msg.packet_id,
            int(msg.is_outgoing),
        ),
    )
    conn.commit()
    return cur.lastrowid


def load_messages(channel_index: int, limit: int = 200) -> List[Message]:
    conn = _conn()
    rows = conn.execute(
        """SELECT * FROM messages WHERE channel_index = ?
           ORDER BY rx_time DESC LIMIT ?""",
        (channel_index, limit),
    ).fetchall()
    messages = []
    for r in reversed(rows):
        messages.append(
            Message(
                text=r["text"],
                from_id=r["from_id"],
                to_id=r["to_id"],
                channel_index=r["channel_index"],
                from_name=r["from_name"],
                rx_time=r["rx_time"],
                rx_snr=r["rx_snr"],
                packet_id=r["packet_id"],
                is_outgoing=bool(r["is_outgoing"]),
            )
        )
    return messages


def upsert_node(entry: NodeEntry):
    conn = _conn()
    conn.execute(
        """INSERT INTO node_cache
           (node_id, node_num, long_name, short_name, hw_model, role,
            battery_level, voltage, channel_util, air_util_tx, uptime_seconds,
            snr, hops_away, last_heard, latitude, longitude, altitude)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(node_id) DO UPDATE SET
            node_num=excluded.node_num,
            long_name=excluded.long_name,
            short_name=excluded.short_name,
            hw_model=excluded.hw_model,
            role=excluded.role,
            battery_level=excluded.battery_level,
            voltage=excluded.voltage,
            channel_util=excluded.channel_util,
            air_util_tx=excluded.air_util_tx,
            uptime_seconds=excluded.uptime_seconds,
            snr=excluded.snr,
            hops_away=excluded.hops_away,
            last_heard=excluded.last_heard,
            latitude=excluded.latitude,
            longitude=excluded.longitude,
            altitude=excluded.altitude""",
        (
            entry.node_id,
            entry.node_num,
            entry.long_name,
            entry.short_name,
            entry.hw_model,
            entry.role,
            entry.battery_level,
            entry.voltage,
            entry.channel_util,
            entry.air_util_tx,
            entry.uptime_seconds,
            entry.snr,
            entry.hops_away,
            entry.last_heard,
            entry.latitude,
            entry.longitude,
            entry.altitude,
        ),
    )
    conn.commit()


def load_nodes() -> List[NodeEntry]:
    conn = _conn()
    rows = conn.execute("SELECT * FROM node_cache ORDER BY last_heard DESC").fetchall()
    return [
        NodeEntry(
            node_id=r["node_id"],
            node_num=r["node_num"],
            long_name=r["long_name"],
            short_name=r["short_name"],
            hw_model=r["hw_model"],
            role=r["role"],
            battery_level=r["battery_level"],
            voltage=r["voltage"],
            channel_util=r["channel_util"],
            air_util_tx=r["air_util_tx"],
            uptime_seconds=r["uptime_seconds"],
            snr=r["snr"],
            hops_away=r["hops_away"],
            last_heard=r["last_heard"],
            latitude=r["latitude"],
            longitude=r["longitude"],
            altitude=r["altitude"],
        )
        for r in rows
    ]
