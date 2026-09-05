# -*- coding: utf-8 -*-
"""Извлечение повторяющихся паттернов из пользовательских промптов (n-gram mining).

Задача: если пользователь пишет «использовать всевозможных агентов, всевозможные
инструменты, всевозможные поиски» (3 раза, threshold=2) — программа сама это
замечает, выделяет как «паттерн», сохраняет и кладёт во вкладку «Паттерны моих
промптов», где можно одной кнопкой скопировать.

Алгоритм:
  1. Из всех сохранённых промптов собираются n-граммы 2..5 слов (словоформы
     приводятся к нижнему регистру, ё→е, выкидываются стоп-слова).
  2. Считается частота каждой n-граммы. Если ≥ THRESHOLD (по умолчанию 2) и
     сама n-грамма не входит В БОЛЕЕ ДЛИННУЮ тоже-частую — она получает статус
     паттерна.
  3. Результат — список (phrase, count, samples_id).
  4. Хранение: новая таблица `prompt_patterns` в SQLite (data/archive.db).
     Вкладка читает из неё; рядом — кнопки «Скопировать» и «Удалить».

Никакого ИИ, всё локально и бесплатно.
"""
import os
import re
import sqlite3
import threading
import time
from collections import Counter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "archive.db")

CONN = None
LOCK = threading.Lock()

STOP = set(
    "и в во не что он на я с со как а то все она так его но да ты к у же вы за "
    "бы по только ее мне было вот от меня еще нет о из ему теперь когда даже "
    "ну вдруг ли если уже или ни быть был него до вас уж это их при сам себе "
    "чем об этом этот свои обо между где самый " "the a an and or of to in is "
    "it for on with as by at from this that these those be been being was "
    "were are will would can could should may might not no yes".split()
)

NGRAM_RANGE = (2, 5)
THRESHOLD_DEFAULT = 2
WORD_RE = re.compile(r"[A-Za-zА-Яа-яЁё0-9]+")


def connect():
    global CONN
    with LOCK:
        if CONN is None:
            os.makedirs(DATA_DIR, exist_ok=True)
            CONN = sqlite3.connect(DB_PATH, check_same_thread=False)
            CONN.row_factory = sqlite3.Row
            CONN.execute(
                """CREATE TABLE IF NOT EXISTS prompt_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phrase TEXT NOT NULL,
                    ngram INTEGER NOT NULL,
                    count INTEGER NOT NULL,
                    first_seen TEXT DEFAULT '',
                    last_seen TEXT DEFAULT '',
                    UNIQUE(phrase)
                )"""
            )
            CONN.commit()
    return CONN


def _normalize_text(text):
    s = (text or "").lower().replace("ё", "е")
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _tokens(text):
    return [w for w in WORD_RE.findall(_normalize_text(text)) if w not in STOP]


def extract_ngrams(tokens, n):
    if len(tokens) < n:
        return []
    return [" ".join(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]


def mine_patterns(prompts, threshold=THRESHOLD_DEFAULT):
    """Возвращает список паттернов (phrase, count, ngram_size).

    prompts — список текстов.
    """
    if not prompts:
        return []
    counts = Counter()
    sizes = {}
    for txt in prompts:
        tokens = _tokens(txt)
        seen_here = set()
        for n in range(NGRAM_RANGE[0], NGRAM_RANGE[1] + 1):
            for g in extract_ngrams(tokens, n):
                if g in seen_here:
                    continue  # один и тот же паттерн внутри промпта считается 1×, не N×
                seen_here.add(g)
                counts[g] += 1
                sizes[g] = n
    # фильтр «паттерн не подстрока более длинного и тоже-частого»
    raw = [(g, c, sizes[g]) for g, c in counts.items() if c >= threshold]
    raw.sort(key=lambda x: (-x[1], -x[2], x[0]))
    kept = []
    for g, c, n in raw:
        if any(other != g and other.count(g) and c <= counts[other]
               for other, _, _ in kept):
            continue
        kept.append((g, c, n))
    return kept


def update_patterns(prompts, threshold=THRESHOLD_DEFAULT):
    """Пересчитывает таблицу паттернов из списка промптов."""
    c = connect()
    patterns = mine_patterns(prompts, threshold=threshold)
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    with LOCK:
        c.execute("DELETE FROM prompt_patterns")
        for phrase, cnt, n in patterns:
            c.execute(
                "INSERT OR IGNORE INTO prompt_patterns(phrase, ngram, count, first_seen, last_seen) VALUES(?,?,?,?,?)",
                (phrase, n, cnt, now, now),
            )
        c.commit()
    return patterns


def list_patterns(min_count=None):
    c = connect()
    if min_count:
        rows = c.execute(
            "SELECT * FROM prompt_patterns WHERE count >= ? ORDER BY count DESC, ngram DESC, phrase ASC",
            (min_count,)).fetchall()
    else:
        rows = c.execute(
            "SELECT * FROM prompt_patterns ORDER BY count DESC, ngram DESC, phrase ASC"
        ).fetchall()
    return [dict(r) for r in rows]


def delete_pattern(pid):
    c = connect()
    with LOCK:
        c.execute("DELETE FROM prompt_patterns WHERE id=?", (pid,))
        c.commit()


def increment_use(phrase):
    c = connect()
    with LOCK:
        c.execute(
            "UPDATE prompt_patterns SET count=count+1, last_seen=? WHERE phrase=?",
            (time.strftime("%Y-%m-%d %H:%M:%S"), phrase))
        c.commit()


# ───────────────────────── расширение prompts.py ─────────────────────────
def attach_prompt_source():
    """Чтобы не дублировать код чтения промптов: берёт их из уже существующего
    модуля prompts (таблица `prompts`). Возвращает список текстов."""
    import importlib
    prompts = importlib.import_module("prompts")
    return [p.get("text", "") for p in prompts.list_prompts()]


def recompute_all():
    """Пересчитывает паттерны по текущей таблице prompts."""
    src = attach_prompt_source()
    patterns = update_patterns(src)
    return patterns
