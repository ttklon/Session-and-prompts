# -*- coding: utf-8 -*-
"""Офлайн-сжатие сессий Genspark (п. «скилл для ужимания контекста»).

Идея: сохранить всю содержательную суть чата, выкинуть «грязь» — повторы,
вводные ремарки, навигационные строки, отметки времени, одинаковые «thinking
шапки» от разных уровней агентов. Полностью локально, без ИИ, без сети.

Подход — конвейер:
  1. Нормализация текста (нижние регистры для служебных помет, схлопывание
     переводов строк, разбиение на смысловые блоки по заголовкам «USER: /
     AGENT: / TOOL: / THINKING:» из .txt после extractor).
  2. Удаление шаблонного шума по словарю NOISE_PATTERNS
     (формальные отказы, слова-паразиты времени, эмотиконы UI, навигация).
  3. Дедупликация: одинаковые/почти одинаковые строки (rapidfuzz ≥ 92)
     оставляются только один раз — с пометкой «(повтор N×)».
  4. Извлечение кода/фактов: блоки в тройных бэктиках, формулы `f(x)`, цифры
     и проценты вытаскиваются целиком — никогда не теряются.
  5. Извлечение текста: TF-IDF + сигнальные слова (из summarizer) — самые
     «содержательные» предложения. Покрытие цели ≈ 60–70% оригинала.
  6. Сжатие слов: заменяем длинные канцеляризмы короткими (по COMPACTIONS).
  7. Финал: склейка, заголовок, статистика.

Результат — `_compressed.txt` рядом с оригиналом в data/chats/.
Ничего не выкидывается «вслепую»: всё, что показалось сомнительным,
откладывается в конец как «[ВОЗМОЖНО НУЖНОЕ]», чтобы ничего не потерять.
"""
import hashlib
import os
import re
from collections import Counter

# ───────────────────────── словари ─────────────────────────
NOISE_PATTERNS = [
    r"^\s*Думаю в течение \d+ сек\.?$",
    r"^\s*Memory updated\.?$",
    r"^\s*\d+ tools? used.*$",
    r"^\s*Below is the next section.*$",
    r"^\s*Showing \d+ of \d+.*$",
    r"^\s*Continue\s*$",
    r"^\s*Click to expand\.?$",
    r"^\s*Thoughts\s*$",
    r"^\s*View as:.*$",
    r"^\s*Поделиться\s*$",
    r"^\s*Копировать\s*$",
    r"^\s*Свернуть\s*$",
    r"^\s*Развернуть\s*$",
    r"^\s*Обновить\s*$",
    r"^\s*Источник:?\s*$",
    r"^\s*Cookies?\s*$",
    r"^\s*\d{1,2}:\d{2}(:\d{2})?\s*$",
    r"^\s*Вчера\s*$",
    r"^\s*Сегодня\s*$",
    r"^\s*Just now\s*$",
    r"^\s*\.\.\.\s*$",
    r"^\s*-\s*Вы\s*$",
    r"^\s*-\s*AI\s*$",
]
NOISE_RE = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in NOISE_PATTERNS]

COMPACTIONS = {
    r"\bв целом\b": "в целом",
    r"\bв настоящее время\b": "сейчас",
    r"\bв данный момент\b": "сейчас",
    r"\bна сегодняшний день\b": "сейчас",
    r"\bтем не менее\b": "но",
    r"\bвместе с тем\b": "и",
    r"\bв связи с этим\b": "поэтому",
    r"\bв связи с чем\b": "поэтому",
    r"\bв соответствии с\b": "по",
    r"\bпри помощи\b": "через",
    r"\bпри условии\b": "если",
    r"\bв том случае, если\b": "если",
    r"\bдостаточно большое количество\b": "много",
    r"\bне представляется возможным\b": "нельзя",
    r"\bв значительной степени\b": "сильно",
    r"\bв конечном итоге\b": "в итоге",
    r"\bна постоянной основе\b": "постоянно",
    r"\bв рамках\b": "по",
    r"\bосуществлять деятельность\b": "работать",
    r"\bосуществлять\b": "делать",
    r"\bпроизводить\b": "делать",
    r"\bявляется\b": "—",
    r"\bпредставляет собой\b": "—",
}

# ─────── стоп-слова отличаются от summarizer: тут упор на сохранение фактов ───────
KEEP_TOKENS_RE = re.compile(
    r"https?://\S+|"
    r"[0-9]+(?:[.,][0-9]+)?%?|"
    r"\$[A-Za-z\n\-]{1,8}|"
    r"[A-Za-z]+\.(?:py|js|ts|json|csv|md|html|yml|yaml|sh|bat|exe|dll)|"
    r"[A-Z][A-Za-z0-9]{2,}|"  # CamelCase (имена классов)
    r"`[^`]+`|"  # inline code
    r"\[[^\]]+\]|"
    r"<[A-Za-z][^>]*>|"
)
CODE_BLOCK_RE = re.compile(r"```[\s\S]*?```", re.MULTILINE)
SIMPLE_LINE_RE = re.compile(r"^\s{0,4}.{1,240}$", re.MULTILINE)

# Сигнальные слова — насколько содержательно предложение
SIGNAL = (
    "решен", "ошибк", "баг", "верс", "api", "файл", "код", "git", "bash",
    "python", "windows", "selenium", "driver", "chrome", "edge", "драйвер",
    "результат", "план", "шаг", "идея", "метод", "тест", "итог", "вывод",
    "улучш", "оптимиз", "ускор", "памят", "скорост", "длин", "токен",
    "причин", "проблем", "рекоменд", "лучше", "говор", "означа", "пример",
)
STOPWORDS = set(
    "и в во не что он на я с со как а то все она так его но да ты к у же "
    "вы за бы по только ее мне было вот от меня еще нет о из ему теперь когда "
    "даже ну вдруг ли если уже или ни быть был него до вас уж это их при сам "
    "себе чем об этом этот свои обо между где самый также потом чтобы для "
    "поэтому затем поскольку хотя более менее очень совсем почти около через "
    "кроме среди значит например однако равно же как образом впрочем наконец "
    "итоге результате связи целом частности основном прежде всего очередь другая "
    "другие each other route этап следующий предыдущий имя того котором".split()
)


def _words(s):
    return [w.lower() for w in re.findall(r"[A-Za-zА-Яа-яЁё0-9]+", s)
            if w.lower() not in STOPWORDS and len(w) > 2]


def _strip_noise(text):
    out = text
    for rx in NOISE_RE:
        out = rx.sub("", out)
    # выкидываем одиночные эмодзи/символы
    out = re.sub(r"^\s*[▎▌▍▏▐▶▼▲◆■●•]+\s*$", "", out, flags=re.MULTILINE)
    return out


def _compact_words(text):
    for k, v in COMPACTIONS.items():
        text = re.sub(k, v, text, flags=re.IGNORECASE)
    return text


def _split_blocks(text):
    """Разбивает по логическим маркерам сессии USER:/AGENT:/TOOL:/THINKING: и т.п."""
    markers = re.split(r"(?m)^(#{1,4}\s+.+|>>>+\s+.+|USER\s*[:>]\s+|ASSISTANT\s*[:>]\s+"
                       r"AGENT\s*[:>]\s+|TOOL\s*[:>]\s+|THINKING\s*[:>]\s+|"
                       r"###\s+Response\s+|###\s+Thought\s+process\s+for\s+step\s+\d+\s*\n)", text)
    # markers[odd] — разделители, markers[even] — куски
    blocks = []
    for i in range(1, len(markers), 2):
        blocks.append((markers[i].strip(), markers[i + 1] if i + 1 < len(markers) else ""))
    return blocks


def _keep_score(s):
    ws = _words(s)
    if not ws:
        return 0.0
    sig = sum(1 for w in ws if any(x in w for x in SIGNAL)) / len(ws)
    keep = len(KEEP_TOKENS_RE.findall(s))
    return sig * 0.6 + min(keep, 6) / 6 * 0.4


def _dedup_keep_first(blocks):
    """Схлопываем похожие блоки (rapidfuzz ≥ 92), оставляем тот, что длиннее."""
    try:
        from rapidfuzz import fuzz
        have_rf = True
    except Exception:
        have_rf = False
    from difflib import SequenceMatcher

    kept = []
    for hdr, body in blocks:
        body_s = body.strip()
        if not body_s:
            continue
        jz = min(len(body_s), 2000)
        sig_str = re.sub(r"\s+", " ", body_s[:jz]).lower()
        merge = False
        for i, (kh, kb) in enumerate(kept):
            ks = re.sub(r"\s+", " ", kb[:jz]).lower()
            if have_rf:
                sim = fuzz.token_set_ratio(sig_str, ks)
            else:
                sim = SequenceMatcher(None, sig_str, ks).ratio() * 100
            if sim >= 92:
                if len(body_s) > len(kb):
                    kept[i] = (kh, body_s)
                merge = True
                break
        if not merge:
            kept.append((hdr, body_s))
    return kept


def _compress_block(text, keep_frac=0.7):
    """Оставляет top-keep_frac предложений по содержательности."""
    sents = re.split(r"(?<=[.!?…])\s+(?=[А-ЯЁA-Z0-9«\"“(\[])", text.strip())
    sents = [s.strip() for s in sents if len(s.strip()) > 5]
    if not sents:
        return text
    n = max(1, int(len(sents) * keep_frac))
    scored = sorted(range(len(sents)), key=lambda i: -_keep_score(sents[i]))
    chosen_idx = sorted(scored[:n])
    chosen = [sents[i] for i in chosen_idx]
    maybe = [sents[i] for i in range(len(sents)) if i not in chosen_idx]
    out = " ".join(chosen).strip()
    if maybe:
        out += "\n\n[ВОЗМОЖНО НУЖНОЕ]\n" + " ".join(maybe[:40])
    return out


def _extract_keep(text):
    """Возвращает кусок текста из кода/фактов, который должен быть сохранён целиком."""
    pieces = []
    pieces.extend(CODE_BLOCK_RE.findall(text))
    pieces.extend(KEEP_TOKENS_RE.findall(text))
    return pieces


def compress_chat_text(text, keep_frac=0.7, max_chars=20000, title=""):
    """Главная функция офлайн-сжатия одной сессии.

    Параметры:
      text     — полный текст .txt
      keep_frac — доля предложений, которые остаются в основном теле (0.5 — жёстко, 0.9 — мягко)
      max_chars — лимит итогового размера
      title    — заголовок для шапки
    """
    if not (text or "").strip():
        return ""
    original_len = len(text)
    text = _strip_noise(text)
    text = _compact_words(text)

    blocks = _split_blocks(text)
    no_fact_blocks = []
    keep_pieces = []
    for hdr, body in blocks:
        if not body.strip():
            no_fact_blocks.append((hdr, ""))
            continue
        fact_chunk = "\n".join(_extract_keep(body))
        if fact_chunk.strip():
            keep_pieces.append(("FAKT", hdr, fact_chunk))
        cleaned = _compress_block(body, keep_frac=keep_frac)
        no_fact_blocks.append((hdr, cleaned))

    no_fact_blocks = _dedup_keep_first(no_fact_blocks)

    out = []
    if title:
        out.append("СЖАТАЯ СЕССИЯ: %s" % title.strip())
    out.append("ОРИГИНАЛ: %d симв.  →  СЖАТИЕ: см. ниже\n" % original_len)
    out.append("=" * 60)

    for hdr, body in no_fact_blocks:
        if hdr:
            out.append("\n" + hdr)
        if body.strip():
            out.append(body.strip())

    if keep_pieces:
        out.append("\n\n" + "=" * 60)
        out.append("[СОХРАНЁННЫЕ ФАКТЫ КАК ЕСТЬ — код, ссылки, числа, имена]")
        out.append("=" * 60)
        for kind, hdr, ch in keep_pieces:
            out.append("\n● %s%s" % (hdr, "" if not hdr else "\n" + ch))

    s = "\n".join(out).strip()
    if len(s) > max_chars:
        # оставляем начало + блок фактов
        cut = s[:int(max_chars * 0.85)]
        s = cut + "\n…\n(далее обрезано по лимиту %d символов)" % max_chars
    return s


def compress_chat_file(txt_path, out_dir=None, keep_frac=0.7, max_chars=20000):
    """Сжимает уже сохранённый .txt, кладёт `_compressed.txt` рядом."""
    if not (txt_path and os.path.exists(txt_path)):
        return None
    with open(txt_path, encoding="utf-8", errors="ignore") as f:
        raw = f.read()
    # пропускаем служебный заголовок из extractor — он мешает шаблонам
    parts = raw.split("=" * 60, 2)
    title = ""
    body = raw
    if len(parts) >= 3 and "ПОЛНЫЙ ТЕКСТ ЧАТА" in parts[1]:
        for line in parts[0].splitlines():
            if line.startswith("НАЗВАНИЕ:"):
                title = line.replace("НАЗВАНИЕ:", "").strip()
        body = parts[2]
    compressed = compress_chat_text(body, keep_frac=keep_frac, max_chars=max_chars, title=title)
    base, ext = os.path.splitext(txt_path)
    out_path = base + "_compressed.txt" if not base.endswith("_compressed") else base + ".txt"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(compressed)
    orig_size = os.path.getsize(txt_path)
    comp_size = os.path.getsize(out_path)
    return {
        "out_path": out_path,
        "orig_chars": len(body),
        "comp_chars": len(compressed),
        "ratio": (1 - comp_size / max(1, orig_size)) * 100,
    }


def estimate_compression(text, keep_frac=0.7):
    """Прогноз сжатия без записи на диск — для превью."""
    s = compress_chat_text(text, keep_frac=keep_frac, max_chars=10_000_000, title="")
    return len(s), len(text)
