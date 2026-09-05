# -*- coding: utf-8 -*-
"""Хранилище архива: SQLite (список чатов, заметки, избранное, описания) + папка data/chats (.txt + .html).

Всё локально и бесплатно: никаких серверов, база и тексты лежат рядом с программой.
"""
import os
import re
import sqlite3
import threading
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CHATS_DIR = os.path.join(DATA_DIR, "chats")
DB_PATH = os.path.join(DATA_DIR, "archive.db")

_conn = None
_lock = threading.Lock()


def ensure_dirs():
    os.makedirs(CHATS_DIR, exist_ok=True)


def now_iso():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_conn():
    global _conn
    ensure_dirs()
    if _conn is None:
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
    return _conn


def init_db():
    with _lock:
        conn = get_conn()
        conn.execute(
            """CREATE TABLE IF NOT EXISTS chats (
                chat_id         TEXT PRIMARY KEY,
                url             TEXT NOT NULL,
                title           TEXT DEFAULT '',
                first_prompt_at TEXT DEFAULT '',
                last_opened_at  TEXT DEFAULT '',
                favorite        INTEGER DEFAULT 0,
                notes           TEXT DEFAULT '',
                txt_path        TEXT DEFAULT '',
                created_at      TEXT DEFAULT '',
                desc_min        TEXT DEFAULT '',
                desc_med        TEXT DEFAULT '',
                desc_max        TEXT DEFAULT '',
                desc_mode       TEXT DEFAULT 'offline'
            )"""
        )
        conn.commit()


def upsert_chat(chat_id, url, title, first_prompt_at, txt_path, descs=None, mode="offline"):
    """Вставляет чат либо обновляет его при повторной выгрузке.
    Заметки и избранное при обновлении НЕ теряются."""
    with _lock:
        conn = get_conn()
        now = now_iso()
        descs = descs or {}
        conn.execute(
            """INSERT INTO chats (chat_id, url, title, first_prompt_at, last_opened_at,
                                  favorite, notes, txt_path, created_at,
                                  desc_min, desc_med, desc_max, desc_mode)
               VALUES (?,?,?,?,?, 0, '', ?, ?, ?,?,?,?)
               ON CONFLICT(chat_id) DO UPDATE SET
                 url = excluded.url,
                 title = excluded.title,
                 last_opened_at = excluded.last_opened_at,
                 txt_path = excluded.txt_path,
                 desc_min = excluded.desc_min,
                 desc_med = excluded.desc_med,
                 desc_max = excluded.desc_max,
                 desc_mode = excluded.desc_mode,
                 first_prompt_at = CASE
                     WHEN chats.first_prompt_at IS NULL OR chats.first_prompt_at = ''
                     THEN excluded.first_prompt_at ELSE chats.first_prompt_at END
            """,
            (chat_id, url, title, first_prompt_at or "", now, txt_path or "",
             now, descs.get("min", ""), descs.get("med", ""), descs.get("max", ""), mode),
        )
        conn.commit()


def get_chat(chat_id):
    conn = get_conn()
    cur = conn.execute("SELECT * FROM chats WHERE chat_id=?", (chat_id,))
    row = cur.fetchone()
    return dict(row) if row else None


def list_chats(sort_by="session", only_fav=False):
    """sort_by: session (начало сессии) | opened (последнее открытие) | title (по названию)."""
    if sort_by == "title":
        order = "title COLLATE NOCASE ASC"
    elif sort_by == "opened":
        order = "COALESCE(NULLIF(last_opened_at,''), created_at) DESC"
    else:
        order = "COALESCE(NULLIF(first_prompt_at,''), created_at) DESC"
    where = " WHERE favorite=1" if only_fav else ""
    conn = get_conn()
    cur = conn.execute("SELECT * FROM chats" + where + " ORDER BY " + order)
    return [dict(r) for r in cur.fetchall()]


def update_notes(chat_id, notes):
    with _lock:
        conn = get_conn()
        conn.execute("UPDATE chats SET notes=? WHERE chat_id=?", (notes, chat_id))
        conn.commit()


def set_favorite(chat_id, fav):
    with _lock:
        conn = get_conn()
        conn.execute("UPDATE chats SET favorite=? WHERE chat_id=?", (1 if fav else 0, chat_id))
        conn.commit()


def update_descs(chat_id, descs, mode):
    with _lock:
        conn = get_conn()
        conn.execute(
            "UPDATE chats SET desc_min=?, desc_med=?, desc_max=?, desc_mode=? WHERE chat_id=?",
            (descs.get("min", ""), descs.get("med", ""), descs.get("max", ""), mode, chat_id),
        )
        conn.commit()


def delete_chat(chat_id):
    with _lock:
        conn = get_conn()
        row = conn.execute("SELECT * FROM chats WHERE chat_id=?", (chat_id,)).fetchone()
        conn.execute("DELETE FROM chats WHERE chat_id=?", (chat_id,))
        conn.commit()
    return dict(row) if row else None


def save_artifacts(chat_id, data):
    """Сохраняет .txt (полный текст чата) и .html (снимок страницы) в data/chats.
    Возвращает путь к .txt."""
    ensure_dirs()
    title = (data.get("title") or "chat").strip()
    safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", title).strip().strip("._")[:80] or "chat"
    day = datetime.now().strftime("%Y-%m-%d")
    base = f"{day}_{safe}_{chat_id[:8]}"
    txt_path = os.path.join(CHATS_DIR, base + ".txt")
    html_path = os.path.join(CHATS_DIR, base + ".html")

    header = (
        "НАЗВАНИЕ: %s\nССЫЛКА: %s\nID ЧАТА: %s\nНАЧАЛО СЕССИИ: %s\nВЫГРУЖЕНО: %s\n\n"
        % (data.get("title", ""), data.get("url", ""), chat_id,
           data.get("first_prompt_at") or "не найдено", now_iso())
    )
    body = (data.get("text") or "").strip()
    if not body:
        body = "(Текст страницы пуст: возможно, чат приватный/требует вход, или страница не открылась.)"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(header + "=" * 60 + "\nПОЛНЫЙ ТЕКСТ ЧАТА\n" + "=" * 60 + "\n\n" + body)

    html = data.get("html")
    if html:
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
    return txt_path
