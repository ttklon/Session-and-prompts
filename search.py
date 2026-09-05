# -*- coding: utf-8 -*-
"""Умный поиск по архиву: понимает опечатки и ищет не только в названиях,
но и в описаниях и в ПОЛНОМ тексте каждого чата (.txt).

Бесплатно и офлайн. Основа — RapidFuzz (github.com/rapidfuzz/RapidFuzz, MIT);
если пакета нет — автоматический откат на встроенный difflib с пословным сравнением.
"""
import os
import re

try:
    from rapidfuzz import fuzz
    HAVE_RF = True
except Exception:  # rapidfuzz не установлен — работаем на difflib
    HAVE_RF = False
    from difflib import SequenceMatcher

_WORD_RE = re.compile(r"[A-Za-zА-Яа-яЁё0-9]+")


def _norm(s):
    s = (s or "").lower().replace("ё", "е")
    return re.sub(r"\s+", " ", s).strip()


def _sim(a, b):
    """Похожесть строк 0..100 с учётом опечаток."""
    if not a or not b:
        return 0.0
    if HAVE_RF:
        return float(max(fuzz.partial_ratio(a, b), fuzz.token_set_ratio(a, b)))
    return 100.0 * SequenceMatcher(None, a, b).ratio()


def _word_score(qword, words):
    """Лучшая похожесть слова запроса на любое слово текста (0..100)."""
    if not qword or not words:
        return 0.0
    best = 0.0
    for w in words:
        if qword in w or w in qword:
            return 100.0
        r = SequenceMatcher(None, qword, w).ratio() * 100.0
        if r > best:
            best = r
    return best


def _fuzzy_words(query, text):
    """Оценка совпадения запроса с текстом пословно (работает с опечатками)."""
    qwords = [w for w in _WORD_RE.findall(_norm(query))]
    words = _WORD_RE.findall(_norm(text))
    if not qwords or not words:
        return 0.0
    if HAVE_RF:
        # token_set_ratio устойчив к порядку слов и лишним словам
        return float(fuzz.token_set_ratio(_norm(query), _norm(text)))
    scores = [_word_score(q, words) for q in qwords]
    return sum(scores) / len(scores)


def _read_txt(path, limit=600_000):
    try:
        if path and os.path.exists(path):
            with open(path, encoding="utf-8", errors="ignore") as f:
                return f.read(limit)
    except Exception:
        pass
    return ""


def _best_chunk(query, text, size=420, step=300):
    """Лучший фрагмент текста под запрос: (оценка, сниппет)."""
    t = (text or "")
    tn = _norm(t)
    if not tn:
        return 0.0, ""
    best_score, best_pos = 0.0, 0
    for pos in range(0, max(1, len(tn) - size + 1), step):
        s = _fuzzy_words(query, tn[pos:pos + size])
        if s > best_score:
            best_score, best_pos = s, pos
    lo = max(0, best_pos - step)
    hi = min(max(0, len(tn) - size), best_pos + step)
    for pos in range(lo, hi + 1, 60):
        s = _fuzzy_words(query, tn[pos:pos + size])
        if s > best_score:
            best_score, best_pos = s, pos
    snippet = re.sub(r"\s+", " ", t[best_pos:best_pos + size]).strip()
    return best_score, snippet


def search_chats(query, chats, limit=15, min_score=30):
    """Список (chat_dict, score, snippet, где_нашлось) по убыванию релевантности.
    Ищет в названии, описаниях и полном тексте .txt — даже если слов запроса
    нет в названии и в запросе есть опечатки."""
    q = _norm(query)
    if not q:
        return []
    out = []
    for ch in chats:
        title_s = _fuzzy_words(q, ch.get("title") or "")
        desc_all = " ".join([ch.get("desc_min") or "", ch.get("desc_med") or ""])[:30000]
        desc_s = _fuzzy_words(q, desc_all) if desc_all else 0.0
        body = _read_txt(ch.get("txt_path"))
        body_s, snippet = _best_chunk(q, body) if body else (0.0, "")

        score = max(title_s * 1.05, desc_s * 0.92, body_s * 0.95)
        if title_s >= desc_s and title_s >= body_s:
            where = "в названии"
            snippet = snippet or (ch.get("title") or "")
        elif desc_s >= body_s:
            where = "в описании"
            snippet = snippet or (ch.get("desc_min") or "")[:300]
        else:
            where = "в тексте чата"

        if score >= 15:
            tag = where if score >= min_score else where + " (слабое совпадение)"
            out.append((ch, min(100, round(score)), snippet, tag))
    out.sort(key=lambda x: -x[1])
    return out[:limit]
