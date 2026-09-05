# -*- coding: utf-8 -*-
"""Обнаружение дубликатов и похожих чатов (пункт 8): сравнение по хэшу,
по названию и по шинглам текста 5-словных окон.

Замечание: в исходной версии функция дергала db.get_chat() без импорта —
падало при первом вызове. Теперь модуль самодостаточный: возвращает
уже переданные dict-чат без обращения к БД, а для надёжности шинглов
читает первые ~600 символов TXT-файла чата, если путь существует.
"""
import hashlib
import os
import re

_WORD = re.compile(r"[A-Za-zА-Яа-яЁё0-9]+")


def _shingles(text, k=5):
    words = _WORD.findall((text or "").lower())
    return {" ".join(words[i:i + k]) for i in range(max(0, len(words) - k + 1))}


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / max(1, len(a | b))


def chat_signature(title, text):
    """Хэш title+первых 500 символов текста — точные дубли."""
    h = hashlib.md5()
    h.update((title or "").strip().lower().encode("utf-8"))
    h.update((text or "")[:500].encode("utf-8", errors="ignore"))
    return h.hexdigest()


def _first_chunks(chat):
    """Склейка: заголовок + минимальное описание + первые 600 символов TXT."""
    parts = [chat.get("title") or "", chat.get("desc_min") or ""]
    txt = chat.get("txt_path") or ""
    if txt and os.path.exists(txt):
        try:
            with open(txt, encoding="utf-8", errors="ignore") as f:
                parts.append(f.read(600))
        except Exception:
            pass
    return " ".join(parts)


def find_duplicates(chats, threshold=0.55):
    """Список пар (chat_a, chat_b, similarity) дубликатов/похожих.

    Использует ТОЛЬКО переданные словари, не обращается к БД.
    Возвращает копии чатов (dict), отсортированные по убыванию похожести.
    """
    if not chats:
        return []

    by_id = {ch.get("chat_id"): ch for ch in chats}

    # 1) Точные дубли по title+signature
    dups_by_sig = {}
    for ch in chats:
        sig = chat_signature(ch.get("title") or "", _first_chunks(ch))
        dups_by_sig.setdefault(sig, []).append(ch["chat_id"])

    pairs = set()
    out = []
    for sig, ids in dups_by_sig.items():
        if len(ids) > 1 and sig.strip("0"):  # не нулевой хэш при пустых полях
            for i, a in enumerate(ids):
                for b in ids[i + 1:]:
                    pk = tuple(sorted((a, b)))
                    if pk in pairs:
                        continue
                    pairs.add(pk)
                    out.append((by_id[a], by_id[b], 1.0))

    # 2) Похожие по шинглам 5-словных окон
    sh = {ch["chat_id"]: _shingles(_first_chunks(ch)) for ch in chats}
    keys = list(sh.keys())
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            pk = tuple(sorted((a, b)))
            if pk in pairs:
                continue
            sim = jaccard(sh[a], sh[b])
            if sim >= threshold:
                pairs.add(pk)
                out.append((by_id[a], by_id[b], round(sim, 2)))

    out.sort(key=lambda x: -x[2])
    return out
