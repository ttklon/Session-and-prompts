# -*- coding: utf-8 -*-
"""Описания чата в 3 режимах.
1) БЕЗ ИИ (по умолчанию, бесплатно и офлайн): экстрактивное сжатие — программа ранжирует
   предложения чата по информативности (частотность слов + позиция + сигнальные слова)
   и собирает описание ровно нужной длины:
     минимальное  = 10-15 предложений (цель 12)
     среднее      = 40-50 предложений (цель 45)
     максимальное = 70+ предложений   (цель 75)
2) Опционально — бесплатный Gemini (нужен ключ с aistudio.google.com). Если ИИ недоступен,
   всегда откат на офлайн."""
import re
from collections import Counter

TARGETS = {"min": 12, "med": 45, "max": 75}
NAMES = {"min": "минимальное (10-15)", "med": "среднее (40-50)", "max": "максимальное (70+)"}

STOPWORDS = set((
    "и в во не что он на я с со как а то все она так его но да ты к у же вы за бы по только "
    "ее мне было вот от меня еще нет о из ему теперь когда даже ну вдруг ли если уже или ни "
    "быть был него до вас уж это их при сам себе чем об этом этот свои обо между где самый "
    "также потом чтобы для поэтому затем поскольку хотя более менее очень совсем почти около "
    "через кроме среди значит например однако равно же как образом впрочем наконец итоге "
    "результате связи целом частности основном прежде всего первую очередь другая другие "
    "the a an and or of to in is it for on with as by at from this that these those be been "
    "being was were are will would can could should may might not no yes so but if then than "
    "too very just also only even here there when where how what who whom which while during "
    "after before about above below over under again further once more most such some any all "
    "each few both neither nor own same other another".split()
))

SIGNAL = (
    "агент", "инструмент", "размышл", "промпт", "задач", "ответ", "результат", "итог",
    "вывод", "код", "файл", "данн", "бд", "gemini", "selenium", "браузер", "скрипт",
    "программ", "ошибк", "работа", "сделать", "использ", "функц", "алгоритм", "реализ",
    "провер", "проект", "python", "решение", "шаг", "этап", "план", "создан", "получ",
    "запрос", "диалог", "сообщен", "ссылка", "страниц", "чат",
)


def _words(s):
    return [w.lower() for w in re.findall(r"[A-Za-zА-Яа-яЁё0-9]+", s) if w.lower() not in STOPWORDS]


def split_sentences(text):
    text = re.sub(r"\s+", " ", (text or ""))
    parts = re.split(r"(?<=[.!?…])\s+(?=[А-ЯЁA-Z0-9«\"“(\[])",
                     text)
    return [p.strip() for p in parts if p.strip()]


def _score(sents):
    freq = Counter()
    for s in sents:
        for w in _words(s):
            freq[w] += 1
    maxf = max(freq.values()) if freq else 1
    total = max(1, len(sents))
    res = []
    for i, s in enumerate(sents):
        ws = _words(s)
        tf = (sum(freq.get(w, 0) for w in ws) / maxf) if ws else 0
        rel = i / total
        if rel <= 0.05:
            pos = 1.0
        elif rel <= 0.2:
            pos = 0.8
        elif rel <= 0.6:
            pos = 0.5
        else:
            pos = 0.3
        sig = sum(1 for w in ws if any(x in w for x in SIGNAL)) / max(1, len(ws))
        length = min(len(ws), 40) / 40.0
        score = 0.45 * tf + 0.20 * pos + 0.25 * sig + 0.10 * length
        res.append((score, s))
    return res


def select_sentences(sents, n):
    if not sents or n <= 0:
        return []
    scored = _score(sents)
    order = sorted(range(len(sents)), key=lambda i: -scored[i][0])
    chosen_idx = []
    chosen_words = set()
    for idx in order:
        ws = set(_words(sents[idx]))
        sim = len(ws & chosen_words) / max(1, len(ws | chosen_words))
        if sim > 0.55:
            continue
        chosen_idx.append(idx)
        chosen_words |= ws
        if len(chosen_idx) >= n:
            break
    if len(chosen_idx) < n:
        for idx in order:
            if idx in chosen_idx:
                continue
            chosen_idx.append(idx)
            if len(chosen_idx) >= n:
                break
    chosen_idx = sorted(chosen_idx[:n])
    return [sents[i] for i in chosen_idx]


def build_stats(text):
    low = (text or "").lower()
    n_agent = low.count("агент") + low.count("agent")
    n_tool = low.count("инструмент") + low.count("tool")
    n_think = low.count("размышл") + low.count("thinking")
    chars = len(text or "")
    sents = len(split_sentences(text or ""))
    return ("Статистика: символов ~%d, предложений ~%d, упоминаний агентов ~%d, "
            "инструментов ~%d, размышлений ~%d" % (chars, sents, n_agent, n_tool, n_think))


def _fix_count(text, n):
    s = split_sentences(text)
    if not s:
        return ""
    if len(s) > n:
        return " ".join(s[:n])
    return text.strip()


def _gemini(text, key, model, n):
    import requests
    url = "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent?key=%s" % (model, key)
    head = text[:200000]
    tail = text[-100000:] if len(text) > 200000 else ""
    chunk = head + ("\n...[пропущен средний фрагмент]...\n" if tail else "") + tail
    prompt = (
        "Ниже — полный текст чата с ИИ-агентами (промпты пользователя, ответы агентов, "
        "запущенные агенты, инструменты, размышления). Составь связное описание этого чата "
        "на русском языке РОВНО из %d предложений: о чём чат, что просил пользователь, "
        "что делали агенты, какие инструменты запускались, каков итог. "
        "В ответе — только сам текст описания, без заголовков и нумерации.\n\n%s" % (n, chunk)
    )
    try:
        r = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=240)
        r.raise_for_status()
        out = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        return _fix_count(out, n)
    except Exception:
        return ""


def _wrap(title, mode, engine, text, body):
    head = ["Описание чата: %s" % (re.sub(r"\s+", " ", title or "").strip()),
            "Режим: %s | Движок: %s" % (NAMES.get(mode, mode), engine),
            build_stats(text)]
    return "\n".join(head) + "\n\n" + body


def build_description(text, mode, title="", engine="offline",
                      gemini_key="", gemini_model="", ollama_url="", ollama_model=""):
    target = TARGETS.get(mode, 12)

    if engine == "gemini" and gemini_key:
        body = _gemini(text, gemini_key, gemini_model or "gemini-2.5-flash", target)
        if body:
            return _wrap(title, mode, "gemini (бесплатный тариф)", text, body)

    sents = split_sentences(text)
    n = min(target, len(sents))
    picked = select_sentences(sents, n) if sents else []
    if picked:
        if len(sents) < target:
            body = " ".join(picked) + "\n\n[В чате меньше предложений, чем нужно для этого режима — показаны все имеющиеся.]"
        else:
            body = " ".join(picked)
    else:
        body = "(Недостаточно текста для описания.)"
    return _wrap(title, mode, "офлайн (без ИИ)", text, body)


def make_all_descriptions(text, title="", engine="offline",
                          gemini_key="", gemini_model="", ollama_url="", ollama_model=""):
    return {m: build_description(text, m, title, engine, gemini_key, gemini_model,
                                 ollama_url, ollama_model) for m in TARGETS}
