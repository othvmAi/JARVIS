#!/usr/bin/env python3
"""Lightweight SQLite REST server for JARVIS memory persistence.

Usage:
  pip install flask
  python sqlite-memory-server.py

This runs on http://localhost:8710 by default.
Set SQLITE_MEMORY_PATH env var to change the database file location.
Set SQLITE_MEMORY_PORT env var to change the port.
"""

import json
import os
import sqlite3
import sys
from datetime import datetime

from flask import Flask, g, jsonify, request

app = Flask(__name__)
DB_PATH = os.environ.get("SQLITE_MEMORY_PATH", os.path.join(os.path.dirname(__file__), "jarvis_memory.db"))


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        _init_db(g.db)
    return g.db


def _init_db(db):
    db.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            user_id TEXT,
            input TEXT,
            response TEXT,
            intent TEXT,
            timestamp INTEGER
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            category TEXT,
            key TEXT,
            value TEXT,
            updated_at INTEGER
        )
    """)
    db.execute("""
        CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)
    """)
    db.execute("""
        CREATE INDEX IF NOT EXISTS idx_facts_user ON facts(user_id)
    """)
    db.commit()


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "db_path": DB_PATH})


@app.route("/sessions", methods=["POST"])
def save_session():
    data = request.get_json(force=True)
    db = get_db()
    db.execute(
        "INSERT OR REPLACE INTO sessions (session_id, user_id, input, response, intent, timestamp) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            data.get("session_id", "default"),
            data.get("user_id", "default"),
            data.get("input", ""),
            data.get("response", ""),
            data.get("intent", ""),
            data.get("timestamp", int(datetime.utcnow().timestamp() * 1000)),
        ),
    )
    db.commit()
    return jsonify({"saved": True, "session_id": data.get("session_id")})


@app.route("/sessions/<session_id>", methods=["GET"])
def get_session(session_id):
    db = get_db()
    row = db.execute(
        "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
    ).fetchone()
    if row is None:
        return jsonify({"session": None})
    return jsonify({"session": dict(row)})


@app.route("/facts", methods=["POST"])
def save_facts():
    data = request.get_json(force=True)
    db = get_db()
    facts = data.get("facts", [])
    user_id = data.get("user_id", "default")
    count = 0
    for fact in facts:
        db.execute(
            "INSERT OR REPLACE INTO facts (user_id, category, key, value, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                user_id,
                fact.get("category", ""),
                fact.get("key", ""),
                fact.get("value", ""),
                int(datetime.utcnow().timestamp() * 1000),
            ),
        )
        count += 1
    db.commit()
    return jsonify({"factsSaved": count})


@app.route("/facts", methods=["GET"])
def get_facts():
    user_id = request.args.get("user_id")
    category = request.args.get("category")
    db = get_db()
    query = "SELECT * FROM facts WHERE 1=1"
    params = []
    if user_id:
        query += " AND user_id = ?"
        params.append(user_id)
    if category:
        query += " AND category = ?"
        params.append(category)
    query += " ORDER BY updated_at DESC"
    rows = db.execute(query, params).fetchall()
    return jsonify({"facts": [dict(r) for r in rows]})


if __name__ == "__main__":
    port = int(os.environ.get("SQLITE_MEMORY_PORT", 8710))
    print(f"JARVIS SQLite Memory Server starting on port {port}")
    print(f"Database path: {DB_PATH}")
    app.run(host="0.0.0.0", port=port, debug=False)
