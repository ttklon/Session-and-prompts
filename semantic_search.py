# -*- coding: utf-8 -*-
"""Семантический поиск офлайн (п.3): TF-IDF + косинус — понимает синонимы,
находит чаты даже если общих слов почти нет. Бесплатно, локально, без GPU."""
import math
import re
from collections import Counter
from typing import List, Tuple, Dict

_WORD = re.compile(r"[A-Za-zА-Яа-яЁё0-9]+")

# Лёгкий ручной словарь синонимов (можно расширить)
SYNONYMS = {
    "ошибк": ["баг", "краш", "сбой", "fail", "error", "exception"],
    "браузер": ["хром", "chrome", "edge", "selenium", "драйвер"],
    "выгрузить": ["скачать", "сохранить", "экспорт", "extract", "dump"],
    "описани": ["summary", "пересказ", "summary", "аннотац"],
    "поиск": ["search", "найти", "lookup", "искать"],
    "чат": ["диалог", "conversation", "агент"],
    "агент": ["помощник", "assistant", "агент"],
    "файл": ["документ", "txt", "file"],
    "памятк": ["заметк", "note", "запис"],
    "статус": ["status", "состоян", "лайт"],
    "кнопк": ["button", "клавиш"],
    "окно": ["window", "программ"],
    "цвет": ["color", "фон", "фон"],
    "тема": ["theme", "стиль", "оформлен"],
    "html": ["страниц", "разметк"],
    "selenium": ["браузер", "хром", "драйвер"],
    "rapidfuzz": ["поиск", "опечатки"],
    "размышл": ["мысли", "thinking", "агент"],
    "запрос": ["промпт", "prompt", "вопрос"],
    "промпт": ["запрос", "prompt", "вопрос"],
}


def _tokens(text: str) -> List[str]:
    return [t.lower() for t in _WORD.findall(text or "")]


def _expand(tokens: List[str]) -> List[str]:
    out = list(tokens)
    for t in tokens:
        for k, syns in SYNONYMS.items():
            if k in t or t in k:
                out.extend(syns)
    return out


def _cosine(a: Counter, b: Counter) -> float:
    num = sum(a[w] * b[w] for w in a.keys() & b.keys())
    den = (math.sqrt(sum(v * v for v in a.values())) *
           math.sqrt(sum(v * v for v in b.values())))
    return num / den if den > 0 else 0.0


class SemanticIndex:
    """TF-IDF по архиву. Строится один раз, запросы дешёвые."""
    def __init__(self, docs: Dict[str, str]):
        self.docs = docs
        self.ids = list(docs.keys())
        self.N = max(1, len(self.ids))
        self.tfs = {}
        self.df = Counter()
        for cid, text in docs.items():
            toks = _expand(_tokens(text))
            tf = Counter(toks)
            self.tfs[cid] = tf
            self.df.update(set(toks))
        # idf
        self.idf = {w: math.log((1 + self.N) / (1 + df_)) + 1 for w, df_ in self.df.items()}

    def query(self, q: str, min_score: float = 0.005) -> List[Tuple[str, float]]:
        qtok = _expand(_tokens(q))
        if not qtok:
            return []
        qtf = Counter(qtok)
        qvec = Counter({w: v * self.idf.get(w, 0) for w, v in qtf.items()})
        out = []
        for cid in self.ids:
            dvec = Counter({w: v * self.idf.get(w, 0) for w, v in self.tfs[cid].items()})
            s = _cosine(qvec, dvec)
            if s >= min_score:
                out.append((cid, s))
        out.sort(key=lambda x: -x[1])
        return out


def build_index(chats) -> SemanticIndex:
    """Строит индекс по чатам: title + описание + (первые 60к символов) текста TXT."""
    docs = {}
    import os
    for ch in chats:
        cid = ch["chat_id"]
        body = ""
        p = ch.get("txt_path") or ""
        try:
            if p and os.path.exists(p):
                with open(p, encoding="utf-8", errors="ignore") as f:
                    body = f.read(60000)
        except Exception:
            pass
        docs[cid] = " ".join([
            ch.get("title") or "",
            ch.get("desc_min") or "",
            ch.get("desc_med") or "",
            body,
        ])
    return SemanticIndex(docs)


def semantic_search(query, chats, top_k=15):
    """Семантический поисковик: возвращает (chat, score_normalized_0..100, snippet)."""
    idx = build_index(chats)
    raw = idx.query(query)
    if not raw:
        return []
    maxv = max(s for _, s in raw) or 1.0
    out = []
    import os
    for cid, s in raw:
        ch = next((c for c in chats if c["chat_id"] == cid), None)
        if not ch:
            continue
        # короткий сниппет из начала текста
        snippet = (ch.get("desc_min") or ch.get("title") or "")[:300]
        if not snippet and ch.get("txt_path") and os.path.exists(ch["txt_path"]):
            try:
                with open(ch["txt_path"], encoding="utf-8", errors="ignore") as f:
                    snippet = f.read(300)
            except Exception:
                pass
        out.append((ch, min(100, round(100 * s / maxv, 2)), snippet, "семантика"))
    return out[:top_k]
