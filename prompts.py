# -*- coding: utf-8 -*-
"""Хранение пользовательских промптов и поиск по ним (пункт из списка улучшений)."""
import os
import sqlite3
import threading
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "archive.db")

_CONN = None
_lock = threading.Lock()


def _get_conn():
    global _CONN
    if _CONN is None:
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("""CREATE TABLE IF NOT EXISTS prompts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            created_at TEXT DEFAULT '',
            chat_id TEXT DEFAULT '',
            tags TEXT DEFAULT '',
            use_count INTEGER DEFAULT 0
        )""")
        _conn.commit()
    return _conn


def ensure_table():
    with _lock:
        c = _get_conn()
        c.execute("""CREATE TABLE IF NOT EXISTS prompts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            created_at TEXT DEFAULT '',
            chat_id TEXT DEFAULT '',
            tags TEXT DEFAULT '',
            use_count INTEGER DEFAULT 0
        )""")
        c.commit()


def add_prompt(text, chat_id="", tags=""):
    ensure_table()
    with _lock:
        c = _get_conn()
        c.execute("INSERT INTO prompts(text, created_at, chat_id, tags) VALUES(?,?,?,?)",
                  (text.strip(), time.strftime("%Y-%m-%d %H:%M:%S"), chat_id, tags.strip()))
        c.commit()


def list_prompts():
    ensure_table()
    c = _get_conn()
    return [dict(r) for r in c.execute("SELECT * FROM prompts ORDER BY id DESC")]


def delete_prompt(pid):
    with _lock:
        c = _get_conn()
        c.execute("DELETE FROM prompts WHERE id=?", (pid,))
        c.commit()


def bump_use(pid):
    with _lock:
        c = _get_conn()
        c.execute("UPDATE prompts SET use_count=use_count+1 WHERE id=?", (pid,))
        c.commit()
