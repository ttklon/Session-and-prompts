# -*- coding: utf-8 -*-
"""Обнаружение дубликатов и похожих чатов (пункт 8): сравнение по хэшу,
по названию и по шинглам текста 5-словных окон."""
import hashlib
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


def find_duplicates(chats, threshold=0.55):
    """Возвращает список пар (chat_a, chat_b, similarity) дубликатов/похожих."""
    sigs = {}
    dups_by_sig = {}
    for ch in chats:
        s = chat_signature(ch.get("title"), "")
        sigs[ch["chat_id"]] = s
        dups_by_sig.setdefault(s, []).append(ch["chat_id"])
    pairs = set()
    out = []
    for sig, ids in dups_by_sig.items():
        if len(ids) > 1:
            for i, a in enumerate(ids):
                for b in ids[i + 1:]:
                    pairs.add((a, b))
                    out.append((db.get_chat(a), db.get_chat(b), 1.0))
    # шинглы текста
    sh = {ch["chat_id"]: _shingles(ch.get("title", "") + " " + (ch.get("desc_min") or "")) for ch in chats}
    keys = list(sh.keys())
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            if (a, b) in pairs:
                continue
            sim = jaccard(sh[a], sh[b])
            if sim >= threshold:
                out.append((db.get_chat(a), db.get_chat(b), round(sim, 2)))
    return out
