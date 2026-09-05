# -*- coding: utf-8 -*-
"""Genspark Arkhivator — интерфейс (Windows 11), всё в одном окне.

Версия после шагов 5–7:
  • Интерфейс пересажен на кастомные пиксельные виджеты widgets.py
    (MCFrame / MCButton / MCEntry / MCStatusLight / MCCheckbox / MCTabs),
    компоновка 1:1 по reference_screenshot.png.
  • Горячая смена темы без перезапуска (полная перестройка UI).
  • Дефолтная тема — «Майнкрафт».

Функции (все сохранены):
  1. Вкладка «Мои промпты»: сохранение промптов, привязка к чату, двойной клик ищет похожие чаты.
  2. Подсветка совпадений в TXT + «◀ пред. / след. ▶».
  3. Семантический офлайн-поиск (TF-IDF + синонимы), кнопка «🧠 Семантика».
  6. Предпросмотр при наведении на строку + экспорт чата в Markdown.
  7. Автосохранение заметок каждые 1.5 с + Ctrl+S.
  8. «Дубликаты и похожие»: md5 + Jaccard-шинглы.
"""
import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import db
import extractor
import summarizer
import theme as thememod
import widgets
import prompts as promptsm
import duplicates

try:
    import search as searchmod
except Exception:
    searchmod = None

try:
    import semantic_search as semmod
except Exception:
    semmod = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
SETTINGS_PATH = os.path.join(DATA_DIR, "settings.json")

SORTS = {"Начало сессии": "session", "Последнее открытие": "opened", "По названию": "title"}


def load_settings():
    import json
    defaults = {"engine": "offline", "gemini_key": "", "gemini_model": "gemini-2.5-flash",
                "headless": True, "theme": thememod.default_theme()}
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        if os.path.exists(SETTINGS_PATH):
            with open(SETTINGS_PATH, encoding="utf-8") as f:
                d = json.load(f)
            if isinstance(d, dict):
                defaults.update(d)
    except Exception:
        pass
    if defaults.get("theme") not in thememod.list_themes():
        defaults["theme"] = thememod.default_theme()
    return defaults


def save_settings(s):
    import json
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ---------- экспорт в Markdown (п.6) ----------
def export_chat_to_markdown(chat_id):
    ch = db.get_chat(chat_id)
    if not ch:
        return ""
    txt_path = ch.get("txt_path") or ""
    body = ""
    if txt_path and os.path.exists(txt_path):
        with open(txt_path, encoding="utf-8", errors="ignore") as f:
            body = f.read()
    lines = [
        "# %s" % (ch.get("title") or "Без названия"),
        "",
        "- **Ссылка:** %s" % ch.get("url"),
        "- **ID чата:** `%s`" % chat_id,
        "- **Начало сессии:** %s" % (ch.get("first_prompt_at") or "—"),
        "- **Выгружено:** %s" % (ch.get("last_opened_at") or ""),
        "",
        "## Описание (минимум)",
        (ch.get("desc_min") or "").split("\n\n")[-1] if ch.get("desc_min") else "",
        "",
        "## Описание (среднее)",
        (ch.get("desc_med") or "").split("\n\n")[-1] if ch.get("desc_med") else "",
        "",
        "## Описание (максимум)",
        (ch.get("desc_max") or "").split("\n\n")[-1] if ch.get("desc_max") else "",
        "",
        "## Полный текст чата",
        "```text",
        body,
        "```",
        "",
        "## Мои заметки",
        ch.get("notes") or "(пусто)",
        "",
    ]
    return "\n".join(lines)


class App:
    def __init__(self, root):
        self.root = root
        self.settings = load_settings()
        self.q = queue.Queue()
        self.loading_ids = set()
        self.search_map = {}
        self.search_highlight = ""
        self.match_positions = []
        self.match_idx = 0
        self.in_search = False
        self._NOTE_DIRTY = False
        self._autosave_started = False
        self.preview = None

        self.root.title("Genspark Arkhivator — архив чатов в TXT")
        self.root.geometry("1240x820")
        self.root.minsize(1060, 660)

        self.colors = self._apply_theme(self.settings.get("theme"))
        self._build_ui()

        db.init_db()
        promptsm.ensure_table()
        self.refresh_list()
        self._refresh_prompts_list()
        if not self._autosave_started:
            self._autosave_started = True
            self._note_autosave()  # п.7
        self.root.after(200, self._drain_queue)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------------- темы ----------------
    def _apply_theme(self, name):
        t = thememod.apply_theme(self.root, name)
        widgets.set_theme(t, minecraft=(name == "Майнкрафт"))
        return t

    def _change_theme(self):
        self._save_settings()
        self.settings["theme"] = self.theme_var.get()
        save_settings(self.settings)
        self.colors = self._apply_theme(self.settings["theme"])
        # горячая перестройка UI без перезапуска
        if self.preview is not None:
            try:
                self.preview.destroy()
            except Exception:
                pass
            self.preview = None
        for child in list(self.root.winfo_children()):
            try:
                child.destroy()
            except Exception:
                pass
        self._build_ui()
        self.refresh_list()
        self._refresh_prompts_list()
        self._status("Тема «%s» применена без перезапуска." % self.settings["theme"], "ok")

    # ---------------- построение UI ----------------
    def _build_ui(self):
        self._build_top()
        self._build_search()
        self._build_main()
        self._build_bottom()

    def _build_top(self):
        t = self.colors
        fr = widgets.MCFrame(self.root)
        fr.pack(fill="x", padx=8, pady=(6, 2))
        f = fr.body
        tk.Label(f, text="Ссылка на чат Genspark:", bg=t["panel"], fg=t["fg"],
                 font=t["font"]).grid(row=0, column=0, sticky="w", padx=(4, 2), pady=2)
        self.url_var = tk.StringVar()
        self.url_entry = widgets.MCEntry(f, textvariable=self.url_var)
        self.url_entry.grid(row=0, column=1, sticky="ew", padx=4, pady=2)
        self.url_entry.bind("<Return>", lambda e: self.on_go())
        self.go_btn = widgets.MCButton(f, text="ВЫГРУЗИТЬ ЧАТ", command=self.on_go,
                                       kind="green", height=30)
        self.go_btn.grid(row=0, column=2, padx=(2, 6), pady=2)
        self.light = widgets.MCStatusLight(f, size=22)
        self.light.grid(row=0, column=3, padx=(0, 6), pady=2)
        self.status_var = tk.StringVar(value="Готово. Вставьте ссылку и нажмите «Выгрузить чат».")
        tk.Label(f, textvariable=self.status_var, bg=t["panel"], fg=t["fg"],
                 font=t["font"], anchor="w").grid(row=0, column=4, sticky="ew", padx=(0, 4))
        f.columnconfigure(1, weight=1)
        f.columnconfigure(4, weight=1)
        self.progress = ttk.Progressbar(self.root, mode="indeterminate")

    def _build_search(self):
        t = self.colors
        fr = widgets.MCFrame(self.root)
        fr.pack(fill="x", padx=8, pady=2)
        bar = fr.body
        tk.Label(bar, text="🔍 Поиск по архиву (понимает опечатки, ищет в тексте чатов):",
                 bg=t["panel"], fg=t["fg"], font=t["font"]).pack(side="left", padx=(4, 2))
        self.search_var = tk.StringVar()
        self.search_entry = widgets.MCEntry(bar, textvariable=self.search_var)
        self.search_entry.pack(side="left", fill="x", expand=True, padx=4, pady=2)
        self.search_entry.bind("<Return>", lambda e: self.on_search())
        widgets.MCButton(bar, text="Найти", command=self.on_search,
                         kind="green", height=26, width=90).pack(side="left", padx=2)
        widgets.MCButton(bar, text="Сброс", command=self.on_search_reset,
                         kind="wood", height=26, width=90).pack(side="left", padx=2)
        widgets.MCButton(bar, text="🧠 Семантика", command=self.on_semantic_search,
                         kind="wood", height=26, width=110).pack(side="left", padx=2)
        self.search_info = tk.StringVar(value="")
        tk.Label(bar, textvariable=self.search_info, bg=t["panel"], fg=t["fg"],
                 font=t["font"]).pack(side="left", padx=8)

    def _build_main(self):
        t = self.colors
        paned = ttk.Panedwindow(self.root, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=8, pady=4)

        # ---- левая часть: сортировка + таблица ----
        left_wrap = widgets.MCFrame(paned)
        paned.add(left_wrap, weight=3)
        left = left_wrap.body

        bar = tk.Frame(left, bg=t["panel"])
        bar.pack(fill="x", pady=(0, 2))
        tk.Label(bar, text="Сортировка:", bg=t["panel"], fg=t["fg"],
                 font=t["font"]).pack(side="left")
        self.sort_var = tk.StringVar(value="Начало сессии")
        self.sort_cb = ttk.Combobox(bar, textvariable=self.sort_var, state="readonly",
                                    width=17, values=list(SORTS.keys()))
        self.sort_cb.pack(side="left", padx=4)
        self.sort_cb.bind("<<ComboboxSelected>>", lambda e: self.refresh_list())
        self.fav_only_var = tk.BooleanVar(value=False)
        widgets.MCCheckbox(bar, text="Только ★", variable=self.fav_only_var,
                           command=self.refresh_list).pack(side="left", padx=6)

        cols = ("status", "title", "session", "size")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", selectmode="browse")
        self.tree.heading("status", text="Статус")
        self.tree.heading("title", text="Название")
        self.tree.heading("session", text="Дата сессии")
        self.tree.heading("size", text="Т")
        self.tree.column("status", width=90, anchor="center")
        self.tree.column("title", width=330, anchor="w")
        self.tree.column("session", width=150, anchor="w")
        self.tree.column("size", width=60, anchor="center")
        self._apply_row_tags()
        self.tree.bind("<Motion>", self._on_tree_hover)
        vsb = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", lambda e: self._show_txt_tab())
        self.tree.bind("<Button-3>", self._on_tree_menu)

        # preview bubble (п.6)
        self.preview = tk.Toplevel(self.root)
        self.preview.withdraw()
        self.preview.overrideredirect(True)
        self.prev_lbl = tk.Label(self.preview, justify="left", padx=8, pady=6,
                                 bg="#fffbd7", fg="#222", relief="solid", bd=1,
                                 font=("Segoe UI", 9), wraplength=520)
        self.prev_lbl.pack()

        # контекстное меню таблицы: редкие действия
        self.tree_menu = tk.Menu(self.root, tearoff=0)
        self.tree_menu.add_command(label="Экспорт чата в Markdown", command=self.export_md)
        self.tree_menu.add_command(label="Дубликаты и похожие", command=self.find_duplicates)

        # ---- правая часть: вкладки ----
        right_wrap = widgets.MCFrame(paned)
        paned.add(right_wrap, weight=3)
        right = right_wrap.body

        self.nb = widgets.MCTabs(right, tabs=["Текст чата (TXT)", "Мои заметки",
                                              "Описание", "Мои промпты"])
        self.nb.pack(fill="both", expand=True)

        # 1) Текст чата (TXT)
        tab_txt = self.nb.tabs["Текст чата (TXT)"]
        toolbar = tk.Frame(tab_txt, bg=t["panel"])
        toolbar.pack(fill="x")
        widgets.MCButton(toolbar, text="◀ пред.", command=self._prev_match,
                         kind="wood", height=24, width=80).pack(side="left", padx=2, pady=2)
        widgets.MCButton(toolbar, text="след. ▶", command=self._next_match,
                         kind="wood", height=24, width=80).pack(side="left", padx=2, pady=2)
        self.match_info = tk.StringVar(value="")
        tk.Label(toolbar, textvariable=self.match_info, bg=t["panel"],
                 fg=t["fg"], font=t["font"]).pack(side="left", padx=8)
        self.txt_view = tk.Text(tab_txt, wrap="word", font=("Consolas", 10),
                                bg=t["entry_bg"], fg=t["entry_fg"],
                                state="disabled", undo=False, relief="flat", bd=4)
        self.txt_view.tag_configure("hit", background="#fff17a", foreground="#000")
        txt_sb = ttk.Scrollbar(tab_txt, orient="vertical", command=self.txt_view.yview)
        self.txt_view.configure(yscrollcommand=txt_sb.set)
        txt_sb.pack(side="right", fill="y")
        self.txt_view.pack(fill="both", expand=True)

        # 2) Мои заметки
        tab_notes = self.nb.tabs["Мои заметки"]
        self.notes = tk.Text(tab_notes, wrap="word", undo=True, font=t["font"],
                             bg=t["entry_bg"], fg=t["entry_fg"], relief="flat", bd=4)
        self.notes.pack(fill="both", expand=True)
        widgets.MCButton(tab_notes, text="Сохранить заметки (Ctrl+S, авто каждые 1.5 с)",
                         command=self.save_notes, kind="green", height=26).pack(fill="x", pady=3)
        self.notes.bind("<Control-s>", lambda e: (self.save_notes(), "break"))
        self.root.bind("<Control-s>", lambda e: (self.save_notes(), "break"))
        self.notes.bind("<<Modified>>", self._on_notes_modified)

        # 3) Описание
        tab_desc = self.nb.tabs["Описание"]
        dbar = tk.Frame(tab_desc, bg=t["panel"])
        dbar.pack(fill="x")
        self.mode_var = tk.StringVar(value="min")
        for key, label in (("min", "Минимум (10-15)"),
                           ("med", "Среднее (40-50)"),
                           ("max", "Максимум (70+)")):
            tk.Radiobutton(dbar, text=label, value=key, variable=self.mode_var,
                           command=self._show_desc, bg=t["panel"], fg=t["fg"],
                           selectcolor=t["entry_bg"], font=t["font"]).pack(side="left", padx=6)
        widgets.MCButton(dbar, text="Копировать", command=self._copy_desc,
                         kind="wood", height=24, width=110).pack(side="right", padx=2)
        self.desc_view = tk.Text(tab_desc, wrap="word", font=t["font"],
                                 bg=t["entry_bg"], fg=t["entry_fg"],
                                 state="disabled", relief="flat", bd=4)
        self.desc_view.pack(fill="both", expand=True, pady=3)

        # 4) Мои промпты (п.1)
        tab_prom = self.nb.tabs["Мои промпты"]
        ptop = tk.Frame(tab_prom, bg=t["panel"])
        ptop.pack(fill="x")
        tk.Label(ptop, text="Промпт:", bg=t["panel"],
                 fg=t["fg"], font=t["font"]).pack(side="left")
        self.prompt_q = tk.StringVar()
        self.prompt_q_entry = widgets.MCEntry(ptop, textvariable=self.prompt_q)
        self.prompt_q_entry.pack(side="left", fill="x", expand=True, padx=6, pady=2)
        self.prompt_q_entry.bind("<Return>", lambda e: self._refresh_prompts_list())
        widgets.MCButton(ptop, text="Найти", command=self._refresh_prompts_list,
                         kind="green", height=26, width=80).pack(side="left", padx=2)
        widgets.MCButton(ptop, text="Сохранить", command=self._save_current_as_prompt,
                         kind="wood", height=26, width=100).pack(side="left", padx=2)
        pcols = ("when", "chat", "uses", "text")
        self.prom_tree = ttk.Treeview(tab_prom, columns=pcols, show="headings",
                                      selectmode="browse")
        self.prom_tree.heading("when", text="Когда")
        self.prom_tree.heading("chat", text="Чат")
        self.prom_tree.heading("uses", text="Запросов")
        self.prom_tree.heading("text", text="Текст промпта")
        self.prom_tree.column("when", width=140)
        self.prom_tree.column("chat", width=160)
        self.prom_tree.column("uses", width=70, anchor="center")
        self.prom_tree.column("text", width=480)
        psb = ttk.Scrollbar(tab_prom, orient="vertical", command=self.prom_tree.yview)
        self.prom_tree.configure(yscrollcommand=psb.set)
        psb.pack(side="right", fill="y")
        self.prom_tree.pack(fill="both", expand=True)
        self.prom_tree.bind("<Double-1>", self._use_prompt)
        pbot = tk.Frame(tab_prom, bg=t["panel"])
        pbot.pack(fill="x", pady=3)
        widgets.MCButton(pbot, text="Искать похожие чаты по промпту",
                         command=self._use_prompt, kind="green", height=26).pack(side="left", padx=2)
        widgets.MCButton(pbot, text="Удалить промпт", command=self._delete_prompt,
                         kind="wood", height=26, width=130).pack(side="left", padx=4)

    def _build_bottom(self):
        t = self.colors
        # ряд действий — 4 кнопки как на референсе
        fr = widgets.MCFrame(self.root)
        fr.pack(fill="x", padx=8, pady=(2, 0))
        bar = fr.body
        for text, cmd in (("★ Избранное", self.toggle_fav),
                          ("Открыть TXT в редакторе", self.open_txt),
                          ("Удалить из списка", self.on_delete),
                          ("Экспорт архива в ZIP", self.export_all)):
            widgets.MCButton(bar, text=text, command=cmd, kind="wood",
                             height=28).pack(side="left", padx=3, pady=2, fill="x", expand=True)

        # нижняя строка настроек — как на референсе
        fr2 = widgets.MCFrame(self.root)
        fr2.pack(fill="x", padx=8, pady=(2, 6))
        bar2 = fr2.body
        tk.Label(bar2, text="Тема:", bg=t["panel"], fg=t["fg"],
                 font=t["font"]).pack(side="left", padx=(4, 2))
        self.theme_var = tk.StringVar(value=self.settings.get("theme", thememod.default_theme()))
        self.theme_cb = ttk.Combobox(bar2, textvariable=self.theme_var, state="readonly",
                                     width=11, values=thememod.list_themes())
        self.theme_cb.pack(side="left", padx=2)
        self.theme_cb.bind("<<ComboboxSelected>>", lambda e: self._change_theme())
        tk.Label(bar2, text="Описание:", bg=t["panel"], fg=t["fg"],
                 font=t["font"]).pack(side="left", padx=(10, 2))
        self.engine_var = tk.StringVar(value=self.settings.get("engine", "offline"))
        self.engine_cb = ttk.Combobox(bar2, textvariable=self.engine_var, state="readonly",
                                      width=9, values=["offline", "gemini"])
        self.engine_cb.pack(side="left", padx=2)
        self.engine_cb.bind("<<ComboboxSelected>>", lambda e: self._save_settings())
        tk.Label(bar2, text="Gemini-ключ (бесплатно: aistudio.google.com):", bg=t["panel"],
                 fg=t["fg"], font=t["font"]).pack(side="left", padx=(10, 2))
        self.key_var = tk.StringVar(value=self.settings.get("gemini_key", ""))
        self.key_entry = widgets.MCEntry(bar2, textvariable=self.key_var, show="*", width=170)
        self.key_entry.pack(side="left", padx=2, fill="x", expand=True)
        self.headless_var = tk.BooleanVar(value=bool(self.settings.get("headless", True)))
        widgets.MCCheckbox(bar2, text="Фоновый браузер", variable=self.headless_var,
                           command=self._save_settings).pack(side="left", padx=6)
        widgets.MCButton(bar2, text="Сохранить", command=self._save_settings,
                         kind="green", height=28, width=110).pack(side="left", padx=4)
        tk.Label(bar2, text="Genspark", bg=t["panel"], fg=t.get("border_mid", "#756c5a"),
                 font=("Segoe UI", 8)).pack(side="right", padx=6)

    # ---------------- цвета строк ----------------
    def _apply_row_tags(self):
        t = self.colors
        self.tree.tag_configure("ready", background=t["ready"], foreground=t["fg"])
        self.tree.tag_configure("loading", background=t["loading"], foreground=t["fg"])

    def _row_tag(self, chat_id):
        return "loading" if chat_id in self.loading_ids else "ready"

    # ---------------- список ----------------
    def refresh_list(self, select_id=None):
        self.in_search = False
        self.search_map.clear()
        self.tree.delete(*self.tree.get_children())
        chats = db.list_chats(sort_by=SORTS.get(self.sort_var.get(), "session"),
                              only_fav=self.fav_only_var.get())
        for ch in chats:
            self._insert_row(ch)
            if select_id and ch["chat_id"] == select_id:
                self.tree.selection_set(ch["chat_id"])
                self.tree.see(ch["chat_id"])
        self._on_select()

    def _insert_row(self, ch, status_text=None):
        cid = ch["chat_id"]
        txt = ch.get("txt_path") or ""
        try:
            size = "%d КБ" % (os.path.getsize(txt) // 1024) if txt and os.path.exists(txt) else ""
        except Exception:
            size = ""
        if status_text is None:
            status_text = "⏳ догружает" if cid in self.loading_ids else "✔ готов"
        if ch.get("favorite"):
            status_text = status_text + " ★"
        vals = (status_text, ch.get("title") or "Без названия",
                ch.get("first_prompt_at") or "—", size)
        if self.tree.exists(cid):
            self.tree.item(cid, values=vals, tags=(self._row_tag(cid),))
        else:
            self.tree.insert("", "end", iid=cid, values=vals, tags=(self._row_tag(cid),))

    def _sel(self):
        sel = self.tree.selection()
        return sel[0] if sel else None

    def _on_select(self, event=None):
        cid = self._sel()
        self.notes.delete("1.0", "end")
        self._set_text(self.txt_view, "")
        self._set_text(self.desc_view, "")
        self.match_positions = []
        self.match_idx = 0
        if not cid:
            return
        ch = db.get_chat(cid)
        if not ch:
            return
        if ch.get("notes"):
            self.notes.insert("1.0", ch["notes"])
        snippet = ""
        if self.in_search and cid in self.search_map:
            snippet = self.search_map[cid][1]
        self._load_txt_view(ch, snippet)
        self._show_desc()

    # ---------------- п.6: предпросмотр при наведении ----------------
    def _on_tree_hover(self, event):
        if self.preview is None:
            return
        iid = self.tree.identify_row(event.y)
        if not iid:
            self.preview.withdraw()
            return
        ch = db.get_chat(iid)
        if not ch:
            self.preview.withdraw()
            return
        prev = (ch.get("title") or "")
        if ch.get("txt_path") and os.path.exists(ch["txt_path"]):
            try:
                with open(ch["txt_path"], encoding="utf-8", errors="ignore") as f:
                    prev = f.read(280).replace("\n", " ")
            except Exception:
                pass
        self.prev_lbl.configure(text=(prev[:340].strip() + "…") if len(prev) > 340 else prev)
        x = self.root.winfo_pointerx() + 14
        y = self.root.winfo_pointery() + 14
        self.preview.geometry("+%d+%d" % (x, y))
        self.preview.deiconify()

    def _on_tree_menu(self, event):
        iid = self.tree.identify_row(event.y)
        if iid:
            self.tree.selection_set(iid)
            try:
                self.tree_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.tree_menu.grab_release()

    def _set_text(self, widget, text):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    def _highlight_hits(self, query):
        """п.2: подсвечивает все вхождения слов запроса в txt_view."""
        self.txt_view.configure(state="normal")
        self.txt_view.tag_remove("hit", "1.0", "end")
        self.match_positions = []
        self.match_idx = 0
        if not query:
            self.match_info.set("")
            self.txt_view.configure(state="disabled")
            return
        start = "1.0"
        words = [w for w in query.lower().split() if len(w) >= 3]
        if not words:
            self.match_info.set("")
            self.txt_view.configure(state="disabled")
            return
        n = 0
        for w in words:
            pos = self.txt_view.search(w, start, stopindex="end", nocase=True)
            while pos:
                end = "%s+%dc" % (pos, len(w))
                self.txt_view.tag_add("hit", pos, end)
                self.match_positions.append(pos)
                n += 1
                pos = self.txt_view.search(w, end, stopindex="end", nocase=True)
        self.txt_view.configure(state="disabled")
        self.match_info.set("совпадений в TXT: %d (кнопки ◀ ▶ для навигации)" % n if n
                            else "совпадений в TXT нет")
        if n:
            self._show_match(0)

    def _show_match(self, idx):
        if not self.match_positions:
            return
        self.match_idx = idx % len(self.match_positions)
        pos = self.match_positions[self.match_idx]
        self.txt_view.see(pos)
        self.match_info.set("совпадение %d/%d" % (self.match_idx + 1, len(self.match_positions)))

    def _next_match(self):
        if self.match_positions:
            self._show_match(self.match_idx + 1)

    def _prev_match(self):
        if self.match_positions:
            self._show_match(self.match_idx - 1)

    def _load_txt_view(self, ch, snippet=""):
        p = ch.get("txt_path") or ""
        body = ""
        try:
            if p and os.path.exists(p):
                with open(p, encoding="utf-8", errors="ignore") as f:
                    body = f.read(1_500_000)
        except Exception as e:
            body = "(не удалось прочитать файл: %s)" % e
        if not body:
            body = "(TXT пока пуст — если статус «догружает», подождите окончания выгрузки.)"
        if snippet:
            body = "— НАЙДЕННЫЙ ФРАГМЕНТ —\n«…%s…»\n%s\n\n%s" % (snippet.strip(), "—" * 50, body)
        self._set_text(self.txt_view, body)
        self._highlight_hits(self.search_highlight)

    def _show_txt_tab(self):
        self.nb.select("Текст чата (TXT)")

    # ---------------- описания ----------------
    def _desc_of(self, ch, mode):
        section = ch.get("desc_" + mode) or "(Описание появится после выгрузки чата.)"
        parts = section.split("\n\n", 1)
        return parts[1] if len(parts) == 2 else section

    def _show_desc(self):
        cid = self._sel()
        if not cid:
            return
        ch = db.get_chat(cid)
        if ch:
            self._set_text(self.desc_view, self._desc_of(ch, self.mode_var.get()))

    def _copy_desc(self):
        cid = self._sel()
        if not cid:
            return
        ch = db.get_chat(cid)
        self.root.clipboard_clear()
        self.root.clipboard_append(self._desc_of(ch, self.mode_var.get()))
        self._status("Описание скопировано в буфер обмена.", "ok")

    # ---------------- заметки / избранное / удаление (п.7) ----------------
    def _on_notes_modified(self, _e=None):
        self._NOTE_DIRTY = True
        self.notes.edit_modified(False)

    def _note_autosave(self):
        if self._NOTE_DIRTY:
            cid = self._sel()
            if cid:
                db.update_notes(cid, self.notes.get("1.0", "end").strip())
            self._NOTE_DIRTY = False
        self.root.after(1500, self._note_autosave)

    def save_notes(self):
        cid = self._sel()
        if not cid:
            return "break"
        db.update_notes(cid, self.notes.get("1.0", "end").strip())
        self._NOTE_DIRTY = False
        ch = db.get_chat(cid)
        self._status("Заметки сохранены для «%s»." % (ch["title"] if ch else cid), "ok")
        return "break"

    def toggle_fav(self):
        cid = self._sel()
        if not cid:
            return
        ch = db.get_chat(cid)
        db.set_favorite(cid, not (ch and ch.get("favorite")))
        if self.in_search:
            self.on_search()
        else:
            self.refresh_list(select_id=cid)

    def on_delete(self):
        cid = self._sel()
        if not cid:
            return
        ch = db.get_chat(cid)
        if messagebox.askyesno("Удалить", "Убрать «%s» из списка?\nФайлы .txt и .html останутся в data/chats."
                               % (ch["title"] if ch else cid)):
            db.delete_chat(cid)
            self.refresh_list()

    def open_txt(self):
        cid = self._sel()
        if not cid:
            return
        ch = db.get_chat(cid)
        p = (ch.get("txt_path") or "") if ch else ""
        if p and os.path.exists(p):
            try:
                os.startfile(p)
            except Exception:
                self._show_txt_tab()
                self._status("TXT показан во вкладке «Текст чата».", "ok")
        else:
            messagebox.showwarning("Архиватор", "Файл TXT не найден.")

    def export_all(self):
        out = filedialog.asksaveasfilename(defaultextension=".zip",
                                           initialfile="genspark_archive.zip",
                                           filetypes=[("ZIP", "*.zip")])
        if not out:
            return
        import shutil
        try:
            base = out[:-4] if out.lower().endswith(".zip") else out
            shutil.make_archive(base, "zip", DATA_DIR)
            messagebox.showinfo("Экспорт", "Архив сохранён: %s" % (base + ".zip"))
        except Exception as e:
            messagebox.showerror("Экспорт", "Ошибка: %s" % e)

    # ---------------- п.6: Markdown ----------------
    def export_md(self):
        cid = self._sel()
        if not cid:
            messagebox.showinfo("Архиватор", "Выберите чат слева.")
            return
        ch = db.get_chat(cid)
        if not ch:
            return
        out = filedialog.asksaveasfilename(defaultextension=".md",
                                           initialfile=(ch.get("title") or "chat")[:60] + ".md",
                                           filetypes=[("Markdown", "*.md")])
        if not out:
            return
        try:
            data = export_chat_to_markdown(cid)
            with open(out, "w", encoding="utf-8") as f:
                f.write(data)
            messagebox.showinfo("Экспорт в Markdown", "Готово: %s" % out)
        except Exception as e:
            messagebox.showerror("Экспорт", "Ошибка: %s" % e)

    # ---------------- п.8: дубликаты ----------------
    def find_duplicates(self):
        chats = db.list_chats()
        if len(chats) < 2:
            messagebox.showinfo("Дубликаты", "В архиве меньше двух чатов.")
            return
        pairs = duplicates.find_duplicates(chats)
        win = tk.Toplevel(self.root)
        win.title("Дубликаты и похожие чаты")
        win.geometry("900x540")
        cols = ("a", "b", "sim")
        tv = ttk.Treeview(win, columns=cols, show="headings")
        tv.heading("a", text="Чат A")
        tv.heading("b", text="Чат B")
        tv.heading("sim", text="Сходство")
        for a, b, sim in pairs:
            tv.insert("", "end", values=(a.get("title") or "", b.get("title") or "", sim))
        tv.pack(fill="both", expand=True, padx=8, pady=8)
        msg = ("Найдено пар: %d" % len(pairs)) if pairs else \
            "Дубликатов и похожих чатов не найдено."
        tk.Label(win, text=msg).pack()

    # ---------------- поиск ----------------
    def on_search(self):
        q = self.search_var.get().strip()
        if not q:
            self.on_search_reset()
            return
        if searchmod is None:
            messagebox.showwarning("Поиск", "Модуль поиска недоступен.")
            return
        chats = db.list_chats(sort_by=SORTS.get(self.sort_var.get(), "session"))
        self._status("Ищу по %d чатам (названия, описания, полный текст)…" % len(chats), "work")
        results = searchmod.search_chats(q, chats)
        self.search_highlight = q
        self._render_search_results(results, "найдено (с опечатками): %d" % len(results))

    def on_semantic_search(self):
        q = self.search_var.get().strip()
        if not q:
            return
        if semmod is None:
            messagebox.showwarning("Поиск", "Семантический модуль недоступен.")
            return
        chats = db.list_chats()
        if not chats:
            return
        self._status("🧠 Семантический поиск по %d чатам…" % len(chats), "work")
        threading.Thread(target=self._semantic_worker, args=(q, chats), daemon=True).start()

    def _semantic_worker(self, q, chats):
        try:
            results = semmod.semantic_search(q, chats)
        except Exception as e:
            self.q.put(("status", ("Ошибка семантики: %s" % e, "err")))
            return
        as_common = [(ch, score, snippet, "семантика") for ch, score, snippet, _ in results]
        self.q.put(("semantic", (q, as_common)))

    def _render_search_results(self, results, info_text):
        self.in_search = True
        self.search_map.clear()
        self.tree.delete(*self.tree.get_children())
        for ch, score, snippet, where in results:
            self._insert_row(ch, status_text="%d%% • %s" % (score, where))
            self.search_map[ch["chat_id"]] = (ch, snippet)
        self.search_info.set(info_text)
        self._status(info_text + ". Кликните чат — найденное подсветится жёлтым.", "ok")
        if results:
            first = results[0][0]["chat_id"]
            self.tree.selection_set(first)
            self.tree.see(first)

    def on_search_reset(self):
        self.search_var.set("")
        self.search_info.set("")
        self.search_highlight = ""
        self.refresh_list()

    # ---------------- вкладка «Мои промпты» (п.1) ----------------
    def _refresh_prompts_list(self):
        q = self.prompt_q.get().strip().lower()
        items = promptsm.list_prompts()
        self.prom_tree.delete(*self.prom_tree.get_children())
        for p in items:
            text = p.get("text") or ""
            if q and q not in text.lower():
                continue
            chat_title = ""
            cid = p.get("chat_id") or ""
            if cid:
                chat = db.get_chat(cid)
                if chat:
                    chat_title = (chat.get("title") or "")[:24]
            vals = (p.get("created_at") or "", chat_title,
                    p.get("use_count") or 0, text[:240])
            self.prom_tree.insert("", "end", iid=str(p["id"]), values=vals)

    def _save_current_as_prompt(self):
        text = self.prompt_q.get().strip()
        if not text:
            messagebox.showinfo("Мои промпты", "Введите текст промпта в поле.")
            return
        cid = self._sel() or ""
        promptsm.add_prompt(text, chat_id=cid, tags="")
        self._refresh_prompts_list()
        self._status("Промпт сохранён.", "ok")

    def _use_prompt(self, _evt=None):
        sel = self.prom_tree.selection()
        if not sel:
            return
        items = promptsm.list_prompts()
        pid = int(sel[0])
        cur = next((x for x in items if x["id"] == pid), None)
        if not cur:
            return
        promptsm.bump_use(pid)
        text = cur.get("text") or ""
        self.url_var.set("")
        self.search_var.set(text)
        self.on_search()
        self._refresh_prompts_list()

    def _delete_prompt(self):
        sel = self.prom_tree.selection()
        if not sel:
            return
        promptsm.delete_prompt(int(sel[0]))
        self._refresh_prompts_list()

    # ---------------- выгрузка ----------------
    def on_go(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showinfo("Архиватор", "Вставьте ссылку на чат.")
            return
        if "genspark.ai" not in url.lower() and not messagebox.askyesno(
                "Архиватор", "Ссылка не похожа на Genspark. Всё равно попробовать?"):
            return
        self._save_settings()
        cid = extractor.chat_id_from(url)
        if cid in self.loading_ids:
            self._status("Эта ссылка уже выгружается…", "work")
            return
        self.loading_ids.add(cid)
        self._insert_row({"chat_id": cid, "title": "(выгружается…) " + url[:60],
                          "first_prompt_at": "", "txt_path": "", "favorite": 0})
        self.tree.see(cid)
        self._set_light("work")
        self.progress.pack(fill="x", padx=10, pady=(0, 4))
        self.progress.start(14)
        self.go_btn.configure(state="disabled")
        threading.Thread(target=self._work, args=(url, cid), daemon=True).start()

    def _work(self, url, cid):
        try:
            driver = None
            try:
                driver = extractor.create_driver(
                    headless=self.headless_var.get(),
                    status=lambda m: self.q.put(("status", (m, "work"))))
                data = extractor.extract_chat(
                    driver, url, status=lambda m: self.q.put(("status", (m, "work"))))
            finally:
                if driver:
                    try:
                        driver.quit()
                    except Exception:
                        pass
            self.q.put(("status", ("Сохраняю текст и строю описания…", "work")))
            txt_path = db.save_artifacts(cid, data)
            descs = summarizer.make_all_descriptions(
                data["text"], data["title"], self.engine_var.get(),
                self.key_var.get().strip(),
                self.settings.get("gemini_model", "gemini-2.5-flash"),
                ollama_url="", ollama_model="")
            db.upsert_chat(cid, data["url"], data["title"], data["first_prompt_at"],
                           txt_path, descs, self.engine_var.get())
            self.q.put(("ok", (cid, data["title"])))
        except Exception as e:
            self.q.put(("fail", (cid, str(e))))

    def _drain_queue(self):
        try:
            while True:
                kind, payload = self.q.get_nowait()
                if kind == "status":
                    msg, level = payload
                    self._status(msg, level)
                elif kind == "semantic":
                    q, results = payload
                    self.search_highlight = q
                    self._render_search_results(results, "🧠 найдено (по смыслу): %d" % len(results))
                elif kind == "ok":
                    cid, title = payload
                    self.loading_ids.discard(cid)
                    self.progress.stop()
                    self.progress.pack_forget()
                    self.go_btn.configure(state="normal")
                    self._set_light("ok")
                    self._status("Готово: «%s» — TXT лежит рядом, строка позеленела." % title, "ok")
                    if self.in_search:
                        self.on_search()
                    else:
                        self.refresh_list(select_id=cid)
                    self.url_entry.delete(0, "end")
                elif kind == "fail":
                    cid, err = payload
                    self.loading_ids.discard(cid)
                    self.progress.stop()
                    self.progress.pack_forget()
                    self.go_btn.configure(state="normal")
                    self._set_light("err")
                    self.refresh_list()
                    messagebox.showerror("Ошибка выгрузки", err)
        except queue.Empty:
            pass
        self.root.after(200, self._drain_queue)

    def _set_light(self, state):
        try:
            self.light.set_state(state)
        except Exception:
            pass

    def _status(self, msg, level="idle"):
        self.status_var.set(msg)
        if level == "work":
            self._set_light("work")
        elif level == "ok":
            self._set_light("ok")
        elif level == "err":
            self._set_light("err")

    def _save_settings(self):
        self.settings.update({
            "engine": self.engine_var.get(),
            "gemini_key": self.key_var.get().strip(),
            "headless": bool(self.headless_var.get()),
            "theme": self.theme_var.get(),
        })
        save_settings(self.settings)
        self._status("Настройки сохранены.", "ok")

    def _on_close(self):
        try:
            self.save_notes()
        except Exception:
            pass
        if self.preview is not None:
            try:
                self.preview.destroy()
            except Exception:
                pass
        self.root.destroy()


def seed_demo():
    import datetime
    samples = [
        ("demo-aaaa-1111", "Создание архиватора чатов",
         "Пользователь попросил программу для выгрузки чатов Genspark в txt. "
         "Агент предложил Selenium без логина и без Playwright. Инструмент раскрыл "
         "свёрнутые блоки с агентами и размышлениями. Результат: весь текст сохраняется "
         "в файл рядом с программой. Описания строятся офлайн без ИИ. "
         "Пользователь доволен и просит добавить избранное и заметки. " * 10),
        ("demo-bbbb-2222", "Разбор ошибок Python и драйвера Chrome",
         "В чате разбирали, почему ChromeDriver падал с ошибкой session not created. "
         "Агент объяснил про несовпадение версий браузера и драйвера. "
         "Инструменты: проверка версии, установка Selenium Manager. "
         "Размышления агента о совместимости. Итог: драйвер скачивается автоматически. " * 10),
        ("demo-cccc-3333", "Идеи интерфейса: кубики и зелёные статусы",
         "Пользователь хочет интерфейс с кубиками как в майнкрафте и цветными статусами. "
         "Агент предложил темы оформления и теги строк. Обсуждали поиск с опечатками "
         "по всему архиву на бесплатной библиотеке RapidFuzz с GitHub. " * 10),
    ]
    db.init_db()
    for i, (cid, title, text) in enumerate(samples):
        day = (datetime.datetime.now() - datetime.timedelta(days=i * 3)).strftime("%Y-%m-%d %H:%M:%S")
        data = {"title": title, "url": "https://www.genspark.ai/agents?id=" + cid,
                "first_prompt_at": day, "text": text, "html": ""}
        txt_path = db.save_artifacts(cid, data)
        descs = summarizer.make_all_descriptions(text, title)
        db.upsert_chat(cid, data["url"], title, day, txt_path, descs, "offline")
    db.set_favorite("demo-bbbb-2222", True)
    db.update_notes("demo-aaaa-1111", "ВАЖНО: это первый чат про архиватор.\nЗдесь обсуждали Selenium, статусы и офлайн-описания.")
    promptsm.add_prompt("Как выгрузить чаты Genspark в txt?", "demo-aaaa-1111", "")
    promptsm.add_prompt("Почему падает ChromeDriver session not created?", "demo-bbbb-2222", "")
    promptsm.add_prompt("Хочу интерфейс с кубиками и зелёными статусами", "demo-cccc-3333", "")


def main():
    if "--demo" in sys.argv:
        seed_demo()
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
