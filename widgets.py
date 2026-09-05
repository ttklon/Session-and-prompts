# -*- coding: utf-8 -*-
"""Кастомные пиксельные виджеты Minecraft-стиля (только stdlib Tk, без PIL).

Виджеты:
  MCFrame       — зелёная «кирпичная» рамка + пергаментная панель, .body — внутренний контейнер.
  MCButton      — объёмная кнопка (kind='green'/'wood'), блик сверху, тень снизу, заклёпки.
  MCEntry       — утопленное поле ввода на пергаменте, .var/.entry доступны.
  MCStatusLight — пиксельный квадрат-лампочка (idle/work/ok/err) с глифом.
  MCCheckbox    — пиксельный квадрат с галочкой, поддерживает tk.BooleanVar.
  MCTabs        — вкладки-язычки (активная зелёная, неактивные деревянные), .tabs — dict страниц.

Вся палитра управляется set_theme(theme_dict, minecraft=True/False): для современных
тем (Светлая/Тёмная) рисуются плоские панели без блоков — тот же API.
"""
import tkinter as tk

# ──────────────────────────── палитра (дефолт = Майнкрафт) ────────────────────────────
_T = {
    "tile_hi": "#5c8a3d", "tile_mid": "#2f5e1e", "tile_lo": "#1f4a16", "tile_gap": "#162e0c",
    "panel": "#ebd3aa", "panel_dark": "#d6bf8f", "panel_light": "#f3e0b8",
    "border_dark": "#3c2d1d", "border_mid": "#756c5a", "border_light": "#a8966b",
    "accent": "#417a22", "accent_light": "#5e9c32", "accent_dark": "#2d5916",
    "wood": "#bd9354", "wood_light": "#d6bf8f", "wood_dark": "#7a5f30",
    "entry_bg": "#fdf6e0", "fg": "#1a1a1a",
    "ok": "#35b23a", "warn": "#e6b800", "err": "#d64545", "silver": "#9a9a9a",
    "font": ("Segoe UI", 10, "bold"),
}
_MC = True  # True → пиксельные блоки/заклёпки; False → плоский современный вид


def set_theme(t, minecraft=True):
    """Применить словарь темы из theme.py ко всем новым виджетам."""
    global _MC
    _MC = bool(minecraft)
    if minecraft:
        for k in ("tile_hi", "tile_mid", "tile_lo", "tile_gap"):
            _T[k] = {"tile_hi": t.get("bg_block_high", "#5c8a3d"),
                     "tile_mid": t.get("bg_block_mid", "#2f5e1e"),
                     "tile_lo": t.get("bg_block_dark", "#1f4a16"),
                     "tile_gap": t.get("bg_tile_gap", "#162e0c")}[k]
    else:
        flat = t.get("bg", "#f3f3f3")
        _T["tile_hi"] = _T["tile_mid"] = _T["tile_lo"] = _T["tile_gap"] = flat
    _T["panel"] = t.get("panel", "#ebd3aa")
    _T["panel_dark"] = t.get("panel_dark", "#d6bf8f")
    _T["panel_light"] = t.get("panel_light", "#f3e0b8")
    _T["border_dark"] = t.get("border_color", "#3c2d1d")
    _T["border_mid"] = t.get("border_mid", "#756c5a")
    _T["border_light"] = t.get("border_light", "#a8966b")
    _T["accent"] = t.get("accent", "#417a22")
    _T["accent_light"] = t.get("accent_light", "#5e9c32")
    _T["accent_dark"] = t.get("accent_dark", "#2d5916")
    _T["wood"] = t.get("wood", "#bd9354")
    _T["wood_light"] = t.get("wood_light", "#d6bf8f")
    _T["wood_dark"] = t.get("wood_dark", "#7a5f30")
    _T["entry_bg"] = t.get("entry_bg", "#fdf6e0")
    _T["fg"] = t.get("fg", "#1a1a1a")
    _T["ok"] = t.get("ok", "#35b23a")
    _T["warn"] = t.get("warn", "#e6b800")
    _T["err"] = t.get("err", "#d64545")
    _T["silver"] = t.get("silver", "#9a9a9a")
    _T["font"] = t.get("mc_font") if minecraft and t.get("mc_font") else t.get("font", ("Segoe UI", 10, "bold"))


def palette():
    return dict(_T)


# ──────────────────────────── низкоуровневые примитивы ────────────────────────────
def _px(c, x, y, w, h, color, outline="", width=1):
    return c.create_rectangle(x, y, x + w, y + h, fill=color, outline=outline, width=width)


def _rivet(c, x, y, s=2):
    _px(c, x, y, s, s, _T["border_light"])
    _px(c, x + s, y, s, s, _T["border_mid"])
    _px(c, x, y + s, s, s, _T["border_mid"])
    _px(c, x + s, y + s, s, s, _T["border_dark"])


def _tiles(c, w, h, step=8):
    """Заливка зелёными пиксельными блоками с тёмными зазорами."""
    _px(c, 0, 0, w, h, _T["tile_gap"])
    for bx in range(0, w, step):
        for by in range(0, h, step):
            pick = (bx // step + by // step) % 4
            col = _T["tile_hi"] if pick == 0 else (_T["tile_lo"] if pick == 1 else _T["tile_mid"])
            _px(c, bx, by, step - 1, step - 1, col)


# ──────────────────────────── MCFrame ────────────────────────────
class MCFrame(tk.Frame):
    """Рамка с пиксельной «кирпичной» каймой и пергаментной панелью.
    Виджеты кладутся в .body."""

    def __init__(self, parent, parchment=True, pad=6, **kw):
        super().__init__(parent, bd=0, highlightthickness=0, bg=_T["tile_mid"], **kw)
        self.parchment = parchment
        self.pad = pad
        self.canvas = tk.Canvas(self, bd=0, highlightthickness=0, bg=_T["tile_mid"])
        self.canvas.pack(fill="both", expand=True)
        self.body = tk.Frame(self.canvas, bg=_T["panel"], bd=0, highlightthickness=0)
        self._win = self.canvas.create_window(0, 0, window=self.body, anchor="nw", width=1, height=1)
        self._size = (0, 0)
        self.canvas.bind("<Configure>", self._redraw)

    def _redraw(self, _e=None):
        c = self.canvas
        w = max(2, c.winfo_width())
        h = max(2, c.winfo_height())
        if (w, h) == self._size:
            return
        self._size = (w, h)
        c.delete("bg")
        if _MC:
            _tiles(c, w, h)
            for item in c.find_all():
                c.addtag_below("bg", item)
        else:
            r = _px(c, 0, 0, w, h, _T["tile_mid"])
            c.addtag_below("bg", r)
        pad = self.pad
        ix, iy, iw, ih = pad, pad, w - pad * 2, h - pad * 2
        if iw < 8 or ih < 8:
            return
        items = []
        if self.parchment:
            items.append(_px(c, ix + 2, iy + 2, iw, ih, "#9c8455"))            # тень
            items.append(_px(c, ix, iy, iw, ih, _T["panel"]))                  # пергамент
            bh1 = max(2, ih // 12)
            items.append(_px(c, ix, iy, iw, bh1, _T["panel_light"]))           # верхний блик
            items.append(_px(c, ix, iy + ih - bh1, iw, bh1, _T["panel_dark"])) # нижняя тень
            items.append(_px(c, ix, iy, iw, ih, "", _T["border_dark"], 2))     # чёрная рамка
            if _MC:
                items.append(_px(c, ix + 3, iy + 3, iw - 6, ih - 6, "", _T["border_light"], 1))
        for it in items:
            c.addtag_below("bg", it)
        if _MC:
            for (rx, ry) in [(2, 2), (max(2, w - 10), 2), (2, max(2, h - 10)), (max(2, w - 10), max(2, h - 10))]:
                for dx in (0, 2):
                    for dy in (0, 2):
                        pass
                _rivet(c, rx, ry, 2)
                for it in c.find_withtag("current"):
                    c.addtag_above("bg", it)
        # тело панели
        c.coords(self._win, ix + 3, iy + 3)
        c.itemconfigure(self._win, width=max(1, iw - 6), height=max(1, ih - 6))
        c.tag_raise(self._win)


# ──────────────────────────── MCButton ────────────────────────────
class MCButton(tk.Frame):
    def __init__(self, parent, text="Button", command=None, kind="green",
                 height=32, width=None, font=None, **kw):
        super().__init__(parent, bd=0, highlightthickness=0, bg=_T["panel"], **kw)
        self.command = command
        self.kind = kind
        self._text = text
        self._disabled = False
        self._hover_id = None
        self.font = font or _T["font"]
        self.canvas = tk.Canvas(self, bd=0, highlightthickness=0, height=height,
                                bg=_T["panel"], cursor="hand2")
        self.canvas.pack(fill="both", expand=True)
        if width:
            self.canvas.configure(width=width)
        self.canvas.bind("<Configure>", lambda e: self._redraw())
        self.canvas.bind("<ButtonRelease-1>", self._click)
        self.canvas.bind("<Enter>", self._hover_on)
        self.canvas.bind("<Leave>", self._hover_off)

    def configure(self, cnf=None, **kw):
        if "text" in kw:
            self._text = kw.pop("text")
            self._redraw()
        if "command" in kw:
            self.command = kw.pop("command")
        if "state" in kw:
            self._disabled = (kw.pop("state") == "disabled")
            self._redraw()
        return super().configure(cnf, **kw)

    config = configure

    def _colors(self):
        if self._disabled:
            return "#8a8a8a", "#6e6e6e", "#3a3a3a", "#dcdcdc"
        if self.kind == "wood":
            return _T["wood_light"], _T["wood"], _T["wood_dark"], "#1a1a1a"
        return _T["accent_light"], _T["accent"], _T["accent_dark"], "#ffffff"

    def _redraw(self):
        c = self.canvas
        c.delete("all")
        w = max(4, c.winfo_width())
        h = max(4, c.winfo_height())
        hi, base, lo, txt = self._colors()
        hi_h = max(2, h // 4)
        lo_h = max(2, h // 4)
        _px(c, 0, 0, w, hi_h, hi)
        _px(c, 0, hi_h, w, h - hi_h - lo_h, base)
        _px(c, 0, h - lo_h, w, lo_h, lo)
        _px(c, 0, 0, 1, h, _T["border_dark"])
        _px(c, w - 1, 0, 1, h, _T["border_dark"])
        _px(c, 0, 0, w, h, "", _T["border_dark"], 1)
        if _MC and w >= 24 and h >= 14:
            for (rx, ry) in [(3, 3), (w - 7, 3), (3, h - 7), (w - 7, h - 7)]:
                _rivet(c, rx, ry, 2)
        c.create_text(w // 2, h // 2, text=self._text, fill=txt, font=self.font)

    def _click(self, _e=None):
        if not self._disabled and self.command:
            self.command()

    def _hover_on(self, _e=None):
        if self._disabled:
            return
        w = max(4, self.canvas.winfo_width())
        h = max(4, self.canvas.winfo_height())
        if self._hover_id is None:
            self._hover_id = self.canvas.create_rectangle(0, 0, w, h, fill="#ffffff",
                                                          stipple="gray25", outline="")

    def _hover_off(self, _e=None):
        if self._hover_id is not None:
            self.canvas.delete(self._hover_id)
            self._hover_id = None


# ──────────────────────────── MCEntry ────────────────────────────
class MCEntry(tk.Frame):
    def __init__(self, parent, textvariable=None, show=None, width=None, height=30, **kw):
        super().__init__(parent, bd=0, highlightthickness=0, bg=_T["panel"], **kw)
        self.var = textvariable or tk.StringVar()
        self.canvas = tk.Canvas(self, bd=0, highlightthickness=0, height=height, bg=_T["panel"])
        self.canvas.pack(fill="both", expand=True)
        if width:
            self.canvas.configure(width=width)
        self.entry = tk.Entry(self.canvas, textvariable=self.var, bg=_T["entry_bg"],
                              fg=_T["fg"], insertbackground=_T["fg"], relief="flat",
                              bd=0, highlightthickness=0, font=_T["font"])
        if show:
            self.entry.config(show=show)
        self._win = self.canvas.create_window(0, 0, window=self.entry, anchor="nw",
                                              width=1, height=1)
        self.canvas.bind("<Configure>", self._redraw)

    def _redraw(self, _e=None):
        c = self.canvas
        c.delete("bg")
        w = max(4, c.winfo_width())
        h = max(4, c.winfo_height())
        items = []
        if _MC:
            items.append(_px(c, 0, 0, w, h, _T["accent_dark"]))
            items.append(_px(c, 3, 3, w - 4, h - 4, _T["border_dark"]))
            items.append(_px(c, 2, 2, w - 4, h - 4, _T["entry_bg"]))
        else:
            items.append(_px(c, 0, 0, w, h, _T["entry_bg"], _T["border_dark"], 1))
        for it in items:
            c.addtag_below("bg", it)
        m = 3 if _MC else 2
        c.coords(self._win, m + 3, m + 1)
        c.itemconfigure(self._win, width=max(1, w - (m + 3) * 2),
                        height=max(1, h - (m + 1) * 2 - 2))
        c.tag_raise(self._win)

    def get(self):
        return self.var.get()

    def set(self, v):
        self.var.set(v)

    def delete(self, first, last=None):
        self.entry.delete(first, last)

    def insert(self, index, s):
        self.entry.insert(index, s)

    def bind(self, seq=None, func=None, add=None):
        return self.entry.bind(seq, func, add)

    def focus_set(self):
        self.entry.focus_set()

    def focus_force(self):
        self.entry.focus_force()


# ──────────────────────────── MCStatusLight ────────────────────────────
class MCStatusLight(tk.Frame):
    _STATES = {"idle": "silver", "work": "warn", "ok": "ok", "err": "err"}

    def __init__(self, parent, size=22, **kw):
        super().__init__(parent, bd=0, highlightthickness=0, bg=_T["panel"], **kw)
        self.size = size
        self.state = "idle"
        self.canvas = tk.Canvas(self, width=size, height=size, bd=0,
                                highlightthickness=0, bg=_T["panel"])
        self.canvas.pack()
        self.canvas.bind("<Configure>", lambda e: self._redraw())
        self.after(80, self._redraw)

    def set_state(self, s):
        self.state = s
        self._redraw()

    def _redraw(self):
        c = self.canvas
        c.delete("all")
        s = self.size
        base = _T.get(self._STATES.get(self.state, "silver"), _T["silver"])
        _px(c, 1, 1, s - 2, s - 2, base)
        bh = max(2, s // 3)
        _px(c, 1, 1, s - 2, bh, "#ffffff")
        _px(c, 1, s - 1 - bh, s - 2, bh, "#000000")
        # уменьшаем контраст блика/тени стипплингом невозможно — красим полупрозрачно не умеем,
        # поэтому верх/низ перекрашиваем оттенками базового цвета
        def shade(col, f):
            col = col.lstrip("#")
            r, g, b = (int(col[i:i + 2], 16) for i in (0, 2, 4))
            r = max(0, min(255, int(r * f)))
            g = max(0, min(255, int(g * f)))
            b = max(0, min(255, int(b * f)))
            return "#%02x%02x%02x" % (r, g, b)
        _px(c, 1, 1, s - 2, bh, shade(base, 1.35))
        _px(c, 1, s - 1 - bh, s - 2, bh, shade(base, 0.55))
        _px(c, 0, 0, s, s, "", _T["border_dark"], 2)
        cx, cy = s / 2, s / 2
        if self.state == "ok":
            c.create_line(s * 0.25, cy, s * 0.43, s * 0.68, fill="#ffffff", width=2)
            c.create_line(s * 0.43, s * 0.68, s * 0.75, s * 0.30, fill="#ffffff", width=2)
        elif self.state == "work":
            c.create_line(cx, cy, cx, s * 0.28, fill="#ffffff", width=2)
            c.create_line(cx, cy, s * 0.72, cy, fill="#ffffff", width=2)
        elif self.state == "err":
            c.create_line(s * 0.3, s * 0.3, s * 0.7, s * 0.7, fill="#ffffff", width=2)
            c.create_line(s * 0.7, s * 0.3, s * 0.3, s * 0.7, fill="#ffffff", width=2)


# ──────────────────────────── MCCheckbox ────────────────────────────
class MCCheckbox(tk.Frame):
    def __init__(self, parent, text="", variable=None, command=None, **kw):
        super().__init__(parent, bd=0, highlightthickness=0, bg=_T["panel"], **kw)
        self._text = text
        self.var = variable or tk.BooleanVar(value=False)
        self._cmd = command
        self.canvas = tk.Canvas(self, height=26, bd=0, highlightthickness=0,
                                bg=_T["panel"], cursor="hand2")
        self.canvas.pack(fill="x", expand=True)
        self.canvas.bind("<Configure>", lambda e: self._redraw())
        self.canvas.bind("<ButtonRelease-1>", self._toggle)

    def _redraw(self):
        c = self.canvas
        c.delete("all")
        h = max(22, c.winfo_height())
        box = min(20, h - 6)
        bx, by = 3, (h - box) // 2
        val = bool(self.var.get())
        if val:
            _px(c, bx, by, box, box, _T["accent"])
            _px(c, bx, by, box, box // 3, _T["accent_light"])
            c.create_line(bx + box * 0.2, by + box * 0.55, bx + box * 0.4, by + box * 0.75,
                          fill="#ffffff", width=2)
            c.create_line(bx + box * 0.4, by + box * 0.75, bx + box * 0.8, by + box * 0.25,
                          fill="#ffffff", width=2)
        else:
            _px(c, bx, by, box, box, _T["entry_bg"])
            _px(c, bx, by + box - box // 4, box, box // 4, _T["panel_dark"])
        _px(c, bx, by, box, box, "", _T["border_dark"], 2)
        c.create_text(bx + box + 8, h / 2, text=self._text, anchor="w",
                      font=_T["font"], fill=_T["fg"])

    def _toggle(self, _e=None):
        self.var.set(not bool(self.var.get()))
        self._redraw()
        if self._cmd:
            self._cmd()

    def get(self):
        return bool(self.var.get())

    def set(self, v):
        self.var.set(bool(v))
        self._redraw()


# ──────────────────────────── MCTabs ────────────────────────────
class MCTabs(tk.Frame):
    """Язычки сверху (активная — зелёная, остальные — деревянные) + страницы.
    .tabs — dict title → tk.Frame контента; select(title) переключает."""

    def __init__(self, parent, tabs=None, **kw):
        super().__init__(parent, bd=0, highlightthickness=0, bg=_T["panel"], **kw)
        self.order = list(tabs or [])
        self.tabs = {}
        self._active = None
        self.bar = tk.Canvas(self, height=30, bd=0, highlightthickness=0, bg=_T["panel"])
        self.bar.pack(side="top", fill="x")
        self.bar.bind("<Configure>", lambda e: self._redraw_bar())
        self.bar.bind("<ButtonRelease-1>", self._click)
        self._page_holder = tk.Frame(self, bg=_T["panel"], bd=0, highlightthickness=0)
        self._page_holder.pack(fill="both", expand=True)
        for t in self.order:
            self.add_tab(t)

    def add_tab(self, title):
        if title not in self.tabs:
            self.tabs[title] = tk.Frame(self._page_holder, bg=_T["panel"], bd=0,
                                        highlightthickness=0)
        if title not in self.order:
            self.order.append(title)
        if self._active is None:
            self._active = title
        self._redraw_bar()
        self._show()
        return self.tabs[title]

    def select(self, title):
        if isinstance(title, int):
            title = self.order[title]
        if title in self.tabs:
            self._active = title
            self._redraw_bar()
            self._show()

    def current(self):
        return self._active

    def _show(self):
        for frm in self.tabs.values():
            frm.pack_forget()
        if self._active in self.tabs:
            self.tabs[self._active].pack(fill="both", expand=True)

    def _tab_rects(self):
        w = max(2, self.bar.winfo_width())
        n = max(1, len(self.order))
        tw = max(70, (w - 8) // n)
        rects = []
        x = 4
        for t in self.order:
            rects.append((t, x, x + tw))
            x += tw
        return rects

    def _redraw_bar(self):
        c = self.bar
        c.delete("all")
        w = max(2, c.winfo_width())
        h = max(2, c.winfo_height())
        _px(c, 0, 0, w, h, _T["panel"])
        _px(c, 0, h - 2, w, 2, _T["border_dark"])
        for (title, x1, x2) in self._tab_rects():
            active = (title == self._active)
            if active:
                hi, base, lo, fg = _T["accent_light"], _T["accent"], _T["accent_dark"], "#ffffff"
                y1, y2 = 2, h
            else:
                hi, base, lo, fg = _T["wood_light"], _T["wood"], _T["wood_dark"], _T["fg"]
                y1, y2 = 6, h - 2
            _px(c, x1, y1, x2 - x1, y2 - y1, base)
            _px(c, x1, y1, x2 - x1, 4, hi)
            _px(c, x1, y1, x2 - x1, y2 - y1, "", _T["border_dark"], 1)
            if active:
                _px(c, x1, y2 - 3, x2 - x1, 3, _T["panel"])  # активный язычок сливается с панелью
            c.create_text((x1 + x2) // 2, (y1 + y2) // 2, text=title, fill=fg,
                          font=("Segoe UI", 9, "bold"))

    def _click(self, e):
        for (title, x1, x2) in self._tab_rects():
            if x1 <= e.x <= x2:
                self.select(title)
                return
