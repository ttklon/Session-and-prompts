# -*- coding: utf-8 -*-
"""Хранение пользовательских промптов и поиск по ним (пункт из списка улучшений).

Замечание: в исходной версии внутри _get_conn() создавалась локальная
переменная _conn вместо глобальной _CONN — соединение никогда не
сохранялось и первый же запрос падал. Исправлено: глобальная переменная
обновляется через global, плюс блокировка сделана reentrant-безопасной,
а таблица создаётся ровно один раз при первом обращении.
"""
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
    with _lock:
        if _CONN is None:
            os.makedirs(DATA_DIR, exist_ok=True)
            _CONN = sqlite3.connect(DB_PATH, check_same_thread=False)  # FIX: global, не локальная
            _CONN.row_factory = sqlite3.Row
            _CONN.execute(
                """CREATE TABLE IF NOT EXISTS prompts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT NOT NULL,
                    created_at TEXT DEFAULT '',
                    chat_id TEXT DEFAULT '',
                    tags TEXT DEFAULT '',
                    use_count INTEGER DEFAULT 0
                )"""
            )
            _CONN.commit()
    return _CONN


def ensure_table():
    """Создаёт таблицу, если её ещё нет. Безопасно звать много раз."""
    _get_conn()


def add_prompt(text, chat_id="", tags=""):
    if not text or not text.strip():
        return
    c = _get_conn()
    with _lock:
        c.execute(
            "INSERT INTO prompts(text, created_at, chat_id, tags) VALUES(?,?,?,?)",
            (text.strip(), time.strftime("%Y-%m-%d %H:%M:%S"), chat_id, tags.strip()),
        )
        c.commit()


def list_prompts():
    c = _get_conn()
    return [dict(r) for r in c.execute("SELECT * FROM prompts ORDER BY id DESC").fetchall()]


def delete_prompt(pid):
    c = _get_conn()
    with _lock:
        c.execute("DELETE FROM prompts WHERE id=?", (pid,))
        c.commit()


def bump_use(pid):
    c = _get_conn()
    with _lock:
        c.execute("UPDATE prompts SET use_count=use_count+1 WHERE id=?", (pid,))
        c.commit()


def get_prompt(pid):
    c = _get_conn()
    row = c.execute("SELECT * FROM prompts WHERE id=?", (pid,)).fetchone()
    return dict(row) if row else None
