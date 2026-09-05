# -*- coding: utf-8 -*-
"""Извлечение полного текста страницы чата через Selenium (Chrome/Edge).
Логин не нужен, Playwright не используется. Драйвер скачивает Selenium Manager сам."""
import json
import os
import re
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SELECTORS_PATH = os.path.join(BASE_DIR, "selectors.json")

DEFAULT_SELECTORS = {
    "expander_patterns": [
        "размышл", "мышлен", "thinking", "thought", "агент", "agent",
        "инструмент", "tool", "раскрыт", "expand", "показать", "show",
        "more", "ещё", "еще", "подробн", "detail", "свернут", "collaps",
    ],
    "wait_for_text": ["Genspark"],
    "scroll_pause": 1.2,
    "max_scrolls": 40,
    "max_expand_rounds": 8,
    "title_selectors": ["meta[property='og:title']", "meta[name='twitter:title']", "h1"],
}

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

_EXPAND_JS = """
() => {
  const patterns = ARGS_PATTERNS;
  const els = [];
  const seen = new Set();
  document.querySelectorAll(
    'summary, details, [aria-expanded], [role="button"], button, [class*="expand"], [class*="collaps"], [class*="show"], [class*="toggle"]'
  ).forEach(el => {
    if (el.offsetParent === null) return;
    const tag = el.tagName.toLowerCase();
    if (tag === 'button' && el.disabled) return;
    if (el.getAttribute && el.getAttribute('aria-expanded') === 'true') return;
    if (tag === 'summary' && el.parentElement && el.parentElement.tagName === 'DETAILS' && el.parentElement.open) return;
    const t = (el.textContent || '').trim();
    if (!t || t.length > 160) return;
    const low = t.toLowerCase();
    if (!patterns.some(p => low.indexOf(p) !== -1)) return;
    const key = tag + '|' + (el.className || '');
    if (seen.has(key)) return;
    seen.add(key);
    els.push(el);
  });
  let clicked = 0;
  els.forEach(el => { try { el.click(); clicked++; } catch (e) {} });
  return clicked;
}
"""

_DATE_JS = """
() => {
  try {
    const lds = document.querySelectorAll('script[type="application/ld+json"]');
    for (const s of lds) {
      const m = s.textContent.match(/"datePublished"\\s*:\\s*"([^"]+)"/);
      if (m) return m[1];
    }
  } catch (e) {}
  try {
    const meta = document.querySelector("meta[property='article:published_time']");
    if (meta) return meta.getAttribute("content") || "";
  } catch (e) {}
  return "";
}
"""


def load_selectors():
    cfg = dict(DEFAULT_SELECTORS)
    try:
        if os.path.exists(SELECTORS_PATH):
            with open(SELECTORS_PATH, encoding="utf-8") as f:
                user = json.load(f)
            if isinstance(user, dict):
                cfg.update(user)
    except Exception:
        pass
    return cfg


def chat_id_from(url):
    m = re.search(r"(?:[?&]id=)([0-9A-Za-z-]+)", url or "")
    if m:
        return m.group(1)
    return re.sub(r"[^0-9A-Za-z-_]", "_", url or "")[-40:]


def create_driver(headless=True, status=None):
    def say(msg):
        if status:
            status(msg)

    try:
        from selenium import webdriver
    except ImportError:
        raise RuntimeError(
            "Не установлена библиотека selenium. Запустите run.bat (он сам поставит) "
            "или выполните: python -m pip install -r requirements.txt"
        )

    common = [
        "--disable-blink-features=AutomationControlled",
        "--ignore-certificate-errors",
        "--lang=ru-RU",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        ("--window-size=1440,4000" if headless else "--start-maximized"),
    ]
    hflag = "--headless=new" if headless else None

    say("Запускаю Chrome (при первом запуске Selenium Manager сам скачает драйвер, это 10-40 сек)...")
    try:
        opts = webdriver.ChromeOptions()
        for a in common:
            opts.add_argument(a)
        if hflag:
            opts.add_argument(hflag)
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)
        opts.add_argument("--user-agent=" + USER_AGENT)
        return webdriver.Chrome(options=opts)
    except Exception as e1:
        say("Chrome не запустился, пробую Edge (" + str(e1)[:120] + ")...")
        try:
            from selenium.webdriver.edge.options import Options as EdgeOptions
            opts = EdgeOptions()
            for a in common:
                opts.add_argument(a)
            if hflag:
                opts.add_argument(hflag)
            opts.add_experimental_option("excludeSwitches", ["enable-automation"])
            opts.add_experimental_option("useAutomationExtension", False)
            opts.add_argument("--user-agent=" + USER_AGENT)
            return webdriver.Edge(options=opts)
        except Exception as e2:
            raise RuntimeError(
                "Не удалось запустить ни Chrome, ни Edge. Проверьте, что браузер установлен.\n"
                "Chrome: " + str(e1)[:160] + "\nEdge: " + str(e2)[:160]
            )


def click_expanders(driver, patterns):
    js = _EXPAND_JS.replace("ARGS_PATTERNS", json.dumps(patterns, ensure_ascii=False))
    try:
        return int(driver.execute_script(js) or 0)
    except Exception:
        return 0


def _wait_for_text(driver, words, timeout=90, status=None):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            t = driver.execute_script("return document.body ? document.body.innerText : '';") or ""
            if len(t.strip()) > 80:
                return True
        except Exception:
            pass
        time.sleep(2)
    return False


def get_title(driver, cfg):
    title = ""
    for sel in cfg.get("title_selectors", []):
        try:
            js = ("(()=>{const el=document.querySelector(%s);"
                  "return el ? (el.getAttribute('content') || el.textContent || '') : ''})()"
                  % json.dumps(sel))
            v = (driver.execute_script(js) or "").strip()
            if v:
                title = v
                break
        except Exception:
            pass
    if not title:
        try:
            title = (driver.title or "").strip()
        except Exception:
            title = ""
    title = re.sub(r"\s*[|–—-]\s*(Genspark|AI)\s*.*$", "", title, flags=re.I).strip()
    return title or "Без названия"


def extract_chat(driver, url, cfg=None, status=None):
    def say(msg):
        if status:
            status(msg)

    cfg = cfg or load_selectors()
    patterns = cfg.get("expander_patterns", DEFAULT_SELECTORS["expander_patterns"])
    max_scrolls = int(cfg.get("max_scrolls", 40))
    pause = float(cfg.get("scroll_pause", 1.2))
    rounds = int(cfg.get("max_expand_rounds", 8))

    try:
        driver.set_page_load_timeout(90)
    except Exception:
        pass

    say("Открываю страницу...")
    driver.get(url)
    _wait_for_text(driver, cfg.get("wait_for_text", []), timeout=90, status=say)

    for i in range(max_scrolls + 1):
        say("Загрузка и раскрытие блоков... проход %d/%d" % (i + 1, max_scrolls + 1))
        for _ in range(rounds):
            c = click_expanders(driver, patterns)
            if not c:
                break
            time.sleep(0.5)
        try:
            prev = int(driver.execute_script(
                "return Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);") or 0)
            driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
        except Exception:
            break
        time.sleep(pause)
        try:
            now = int(driver.execute_script(
                "return Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);") or 0)
        except Exception:
            break
        if now <= prev:
            try:
                driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            except Exception:
                pass
            time.sleep(pause)
            break

    for _ in range(rounds):
        c = click_expanders(driver, patterns)
        if not c:
            break
        time.sleep(0.5)

    text, html = "", ""
    try:
        text = (driver.execute_script("return document.body ? document.body.innerText : '';") or "").strip()
    except Exception:
        pass
    try:
        html = driver.page_source
    except Exception:
        pass

    title = get_title(driver, cfg)

    first_prompt = ""
    try:
        first_prompt = (driver.execute_script(_DATE_JS) or "").strip()
    except Exception:
        pass
    if not first_prompt and text:
        m = re.search(r"([0-3]?\d)[./-]([01]?\d)[./-](20\d{2})[ T](\d{1,2}:\d{2})?", text)
        if m:
            first_prompt = m.group(0)

    return {"title": title, "text": text, "html": html, "first_prompt_at": first_prompt, "url": url}
