# -*- coding: utf-8 -*-
"""Кастомные виджеты Minecraft-стиля для Genspark Arkhivator.

Все виджеты рисуются на tk.Canvas (без внешних библиотек) и попиксельно
воспроизводят эталонный скриншот reference_screenshot.png:

  • MCButton    — объёмная кнопка (зелёная / деревянная) с верхним бликом,
                  тёмным торцом, чёрной обводкой и hover-эффектом.
  • MCFrame     — пергаментная панель в зелёной кирпичной рамке с заклёпками
                  по углам (4 «пиксельных блока» 4×4 px).
  • MCEntry     — утопленное поле ввода с внутренней тенью и заголовком.
  • MCStatusLight — квадратный пиксельный индикатор с галочкой/часами (idle/work/ok/err).
  • MCCheckbox  — зелёный пиксельный квадрат с галочкой.
  • MCTabs      — вкладки-язычки (активная зелёная, неактивные деревянные).

Виджеты самодостаточны: они не ломают логику ttk/Tk, а дополняют её,
давая визуал референса без замены работающего кода.
"""
import os
import tkinter as tk


# ─────────────────────────────────────────────────────────────────────────────
# Цветовые константы (pixel-art Minecraft-стиль)
# ─────────────────────────────────────────────────────────────────────────────
_BORDER_DARK = "#3c2d1d"   # чёрная обводка
_BORDER_MID  = "#5a4a30"   # дополнительная обводка
_GREEN_BASE  = "#417a22"   # основной зелёный (верх блика)
_GREEN_HI    = "#5e9c32"   # светлый верхний блик
_GREEN_LO    = "#2d5916"   # тёмный нижний торец
_WOOD_BASE   = "#bd9354"   # дерево
_WOOD_HI     = "#d6bf8f"
_WOOD_LO     = "#7a5f30"
_RIVET_HI    = "#a8966b"
_RIVET_MID   = "#756c5a"
_RIVET_LO    = "#3c2d1d"


# ─────────────────────────────────────────────────────────────────────────────
# Утилиты отрисовки
# ─────────────────────────────────────────────────────────────────────────────
def _pixel_rect(canvas, x, y, w, h, color, outline=None, width=1):
    return canvas.create_rectangle(x, y, x + w, y + h, fill=color,
                                    outline=outline or "", width=width)


def _draw_rivet(canvas, x, y, size=4, dark=False):
    """Заклёпка 4×4 px: верхний светлый, нижний тёмный — псевдо-3D."""
    light = _RIVET_HI if not dark else _RIVET_MID
    _pixel_rect(canvas, x,         y,         size,     size,     light)
    _pixel_rect(canvas, x + size,  y,         size,     size,     _RIVET_MID)
    _pixel_rect(canvas, x,         y + size,  size,     size,     _RIVET_MID)
    _pixel_rect(canvas, x + size,  y + size,  size,     size,     _RIVET_LO)


def _draw_frame_border(canvas, x, y, w, h, thickness=2):
    """Зелёная «кирпичная» рамка по периметру (как блоки травы)."""
    # Внутренняя заливка — пергамент по умолчанию (или внешний bg)
    _pixel_rect(canvas, x, y, w, h, fill="", outline=_BORDER_DARK, width=1)

    # Верхний левый угол — рисуем «блоки» 4×4
    step = 4
    for bx in range(x, x + w, step * 2):
        for by in range(y, min(y + step * 2, y + thickness * 2), step):
            color = _GREEN_HI if (by // step) % 2 == 0 else _GREEN_BASE
            _pixel_rect(canvas, bx, by, step, step, color)


def _fill_bg_blocks(canvas, x, y, w, h, step=8):
    """Заливка фона пиксельными блоками (зелёная «трава/хвоя»)."""
    for bx in range(x, x + w, step):
        for by in range(y, y + h, step):
            # Делаем квадратики 1px зазора → эффект решётки
            c1 = _GREEN_HI if ((bx // step + by // step) % 4 == 0) else _GREEN_BASE
            c2 = _GREEN_LO if ((bx // step + by // step) % 4 == 1) else c1
            _pixel_rect(canvas, bx,           by,           step - 1, step - 1, c2)
            _pixel_rect(canvas, bx + step - 1, by,           1,         step - 1, _BORDER_DARK)
            _pixel_rect(canvas, bx,           by + step - 1, step,      1,        _BORDER_DARK)


# ─────────────────────────────────────────────────────────────────────────────
# MCButton — объёмная кнопка
# ─────────────────────────────────────────────────────────────────────────────
class MCButton(tk.Frame):
    """Объёмная кнопка Minecraft-стиля. Цвет: 'green' (по умолчанию) или 'wood'."""

    def __init__(self, parent, text="Button", command=None,
                 kind="green", width=None, height=32, font=None, **kwargs):
        # Цвета рамки у фрейма — оставляем прозрачной, всё рисуем в canvas
        super().__init__(parent, bd=0, highlightthickness=0, **kwargs)
        self.command = command
        self.kind = kind
        self._text = text
        self._disabled = False
        self.font = font or ("Segoe UI", 10, "bold")

        self.canvas = tk.Canvas(self, bd=0, highlightthickness=0, height=height, cursor="hand2")
        self.canvas.pack(fill="both", expand=True)

        # Подгоняем высоту по желаемому размеру
        if width:
            self.canvas.configure(width=width)
        # Привязка событий
        self.canvas.bind("<Configure>", self._on_resize)
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<Enter>", self._on_hover)
        self.canvas.bind("<Leave>", self._on_leave)
        # Прокидываем привязки на сам фрейм (на случай клика по фрейм-контейнеру)
        self.bind("<Enter>", self._on_hover)
        self.bind("<Leave>", self._on_leave)

    # ── публичные API ──
    def configure(self, cnf=None, **kw):
        if "text" in kw:
            self._text = kw.pop("text")
            self._redraw()
        if "command" in kw:
            self.command = kw.pop("command")
        if "state" in kw:
            self._disabled = (kw.pop("state") == "disabled")
            self._redraw()
        super().configure(cnf, **kw)

    def config(self, cnf=None, **kw):  # alias
        return self.configure(cnf, **kw)

    # ── внутренние ──
    def _on_resize(self, _e=None):
        self._redraw()

    def _redraw(self):
        c = self.canvas
        c.delete("all")
        w = max(1, c.winfo_width() or 1)
        h = max(1, c.winfo_height() or 1)
        if w < 4 or h < 4:
            return

        # Цветовая схема
        if self.kind == "wood":
            hi, base, lo, txt = _WOOD_HI, _WOOD_BASE, _WOOD_LO, "#1a1a1a"
        else:
            hi, base, lo, txt = _GREEN_HI, _GREEN_BASE, _GREEN_LO, "#ffffff"

        if self._disabled:
            base = "#6e6e6e"
            hi = "#8a8a8a"
            lo = "#3a3a3a"

        # Объёмные грани: верхний светлый блик, основной цвет, нижний тёмный торец
        hi_h = max(2, h // 4)
        lo_h = max(2, h // 4)

        # Светлый верх
        _pixel_rect(c, 0, 0, w, hi_h, hi)
        # Основное тело
        _pixel_rect(c, 0, hi_h, w, h - hi_h - lo_h, base)
        # Тёмный низ
        _pixel_rect(c, 0, h - lo_h, w, lo_h, lo)
        # Боковые тёмные торцы (по 1px)
        _pixel_rect(c, 0, 0, 1, h, _BORDER_DARK)
        _pixel_rect(c, w - 1, 0, 1, h, _BORDER_DARK)
        # Чёрная обводка
        _pixel_rect(c, 0, 0, w, h, outline=_BORDER_DARK, width=1)

        # Заклёпки по углам (2×2 px)
        rivet = 2
        for (rx, ry) in [(2, 2), (w - 6, 2), (2, h - 6), (w - 6, h - 6)]:
            _draw_rivet(c, rx, ry, size=rivet)

        # Текст
        font = tuple(self.font)
        c.create_text(w // 2, h // 2, text=self._text, fill=txt, font=font)

    def _on_click(self, _e=None):
        if self._disabled:
            return
        if self.command:
            try:
                self.command()
            except Exception:
                pass

    def _on_hover(self, _e=None):
        if self._disabled:
            return
        self.canvas.configure(cursor="hand2")
        # Лёгкая подсветка — рисуем поверх прозрачный белый rect
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 4 or h < 4:
            return
        if not hasattr(self, "_hover"):
            self._hover = self.canvas.create_rectangle(
                0, 0, w, h, fill="#ffffff", stipple="gray25", outline=""
            )
        else:
            self.canvas.coords(self._hover, 0, 0, w, h)

    def _on_leave(self, _e=None):
        if hasattr(self, "_hover"):
            self.canvas.delete(self._hover)
            del self._hover


# ─────────────────────────────────────────────────────────────────────────────
# MCFrame — пергаментная панель в зелёной кирпичной рамке
# ─────────────────────────────────────────────────────────────────────────────
class MCFrame(tk.Frame):
    """Контейнер с двумя слоями:
        1) фон — пиксельные зелёные блоки («траву/кирпич»);
        2) внутренняя пергаментная панель с приподнятыми краями."""

    def __init__(self, parent, parchment=True, padding=4, **kwargs):
        # bg = цвет фона «кирпичной» рамки
        super().__init__(parent, bd=0, highlightthickness=0,
                         bg=_GREEN_BASE, **kwargs)

        self.parchment = parchment
        self.padding = padding
        self._canvas = tk.Canvas(self, bd=0, highlightthickness=0, bg=_GREEN_BASE)
        self._canvas.pack(fill="both", expand=True)
        self._inner = None
        self._last_size = (0, 0)
        self._canvas.bind("<Configure>", self._on_resize)

    def _on_resize(self, _e=None):
        c = self._canvas
        w = max(1, c.winfo_width())
        h = max(1, c.winfo_height())
        if (w, h) == self._last_size:
            return
        self._last_size = (w, h)
        c.delete("all")

        # 1) Заливка фона пиксельной «травой»
        _fill_bg_blocks(c, 0, 0, w, h, step=8)

        # 2) Заклёпки по углам внешней рамки (4×4 each)
        rivet = 4
        for (rx, ry) in [(4, 4), (w - 12, 4), (4, h - 12), (w - 12, h - 12)]:
            _draw_rivet(c, rx, ry, size=rivet)

        pad = self.padding
        if w < pad * 2 + 4 or h < pad * 2 + 4:
            return

        # 3) Внутренняя пергаментная панель — прямоугольник с двойной обводкой
        ix, iy, iw, ih = pad, pad, w - pad * 2, h - pad * 2
        if self.parchment:
            # Тень под пергаментом
            _pixel_rect(c, ix + 2, iy + 2, iw, ih, "#9c8455")
            # Сам пергамент
            _pixel_rect(c, ix, iy, iw, ih, "#ebd3aa")
            # Верх/низ блик
            bh1 = max(1, ih // 10)
            _pixel_rect(c, ix, iy,      iw, bh1, "#f3e0b8")
            bh2 = max(1, ih // 14)
            _pixel_rect(c, ix, iy + ih - bh2, iw, bh2, "#d6bf8f")
            # Чёрная рамка пергамента
            _pixel_rect(c, ix, iy, iw, ih, outline=_BORDER_DARK, width=2)
            # Внутренняя тонкая (золотая) окантовка
            _pixel_rect(c, ix + 3, iy + 3, iw - 6, ih - 6, outline=_RIVET_HI, width=1)
        else:
            _pixel_rect(c, ix, iy, iw, ih, _GREEN_BASE)
            _pixel_rect(c, ix, iy, iw, ih, outline=_BORDER_DARK, width=1)

        # 4) Сам «внутренний» фрейм — в нём размещают реальные виджеты
        if self._inner is None:
            self._inner = tk.Frame(self._canvas, bg="#ebd3aa" if self.parchment else _GREEN_BASE,
                                   bd=0, highlightthickness=0)
            self._win_id = self._canvas.create_window(
                ix + 4, iy + 4, window=self._inner,
                width=max(1, iw - 8), height=max(1, ih - 8),
                anchor="nw"
            )
        else:
            self._canvas.coords(self._win_id, ix + 4, iy + 4)
            self._canvas.itemconfigure(self._win_id, width=max(1, iw - 8),
                                       height=max(1, ih - 8))

    # Проксируем add/add_child на внутренний фрейм
    def add(self, widget, **kw):
        if self._inner is None:
            self._on_resize()
        self._inner.pack(**kw)

    # tk.Frame-like API: пара прокси-методов
    def winfo_children(self):
        if self._inner:
            return self._inner.winfo_children()
        return []


# ─────────────────────────────────────────────────────────────────────────────
# MCEntry — поле ввода (утопленное) с лейблом-слева (опционально)
# ─────────────────────────────────────────────────────────────────────────────
class MCEntry(tk.Frame):
    """Поле ввода в Minecraft-стиле: пергаментная подложка, чёрная
    обводка, внутренняя тонкая золотая окантовка."""

    def __init__(self, parent, label=None, show=None, **kwargs):
        super().__init__(parent, bd=0, highlightthickness=0, bg=_GREEN_BASE, **kwargs)
        self._label_text = label
        self._show = show

        self._canvas = tk.Canvas(self, bd=0, highlightthickness=0,
                                 bg=_GREEN_BASE, height=28)
        self._canvas.pack(fill="x", expand=False)
        self._canvas.bind("<Configure>", self._redraw)

        # Сам Entry — tk.Entry, встраиваем в канвас
        self._var = tk.StringVar()
        self._entry = tk.Entry(self._canvas, textvariable=self._var,
                               bg="#fdf6e0", fg="#1a1a1a",
                               relief="flat", bd=0,
                               highlightthickness=0,
                               font=("Segoe UI", 10, "bold"),
                               insertbackground="#1a1a1a")
        if show:
            self._entry.config(show=show)

    def _redraw(self, _e=None):
        c = self._canvas
        c.delete("all")
        w = max(2, c.winfo_width())
        h = max(2, c.winfo_height())

        # Зелёная подложка-«земля»
        _pixel_rect(c, 0, 0, w, h, _GREEN_BASE)
        # Утопленный пергамент
        ix, iy, iw, ih = 2, 2, w - 4, h - 4
        _pixel_rect(c, ix + 1, iy + 1, iw, ih, _BORDER_DARK)   # тень
        _pixel_rect(c, ix, iy, iw, ih, "#fdf6e0")               # пергамент
        _pixel_rect(c, ix, iy, iw, ih, outline=_BORDER_DARK, width=1)

        # Размещаем виджет Entry
        if not hasattr(self, "_win_id"):
            self._win_id = c.create_window(
                ix + 4, iy + 2, window=self._entry,
                width=max(1, iw - 8), height=max(1, ih - 4),
                anchor="nw"
            )
        else:
            c.coords(self._win_id, ix + 4, iy + 2)
            c.itemconfigure(self._win_id, width=max(1, iw - 8),
                            height=max(1, ih - 4))

    # Проксируем StringVar-методы
    def get(self):
        return self._var.get()

    def set(self, v):
        self._var.set(v)

    def delete(self, first, last=None):
        self._entry.delete(first, last)

    def insert(self, index, s):
        self._entry.insert(index, s)

    def focus_set(self):
        self._entry.focus_set()

    def focus_force(self):
        self._entry.focus_force()


# ─────────────────────────────────────────────────────────────────────────────
# MCStatusLight — пиксельный индикатор статуса
# ─────────────────────────────────────────────────────────────────────────────
class MCStatusLight(tk.Frame):
    """Квадратный пиксельный индикатор 16×16 с галочкой / часами / крестиком.

    Состояния:
        idle  — серый, вертикальные линии
        work  — жёлтый, «часы» (две стрелки)
        ok    — зелёный, галочка ✓
        err   — красный, крестик ✗"""

    _COLORS = {
        "idle": ("#9a9a9a", "#5a5a5a", "#3a3a3a"),
        "work": ("#e6b800", "#a8800f", "#5e4a05"),
        "ok":   ("#35b23a", "#1d7a22", "#0e4a12"),
        "err":  ("#d64545", "#8a2424", "#4a0c0c"),
    }

    def __init__(self, parent, size=20, **kwargs):
        super().__init__(parent, bd=0, highlightthickness=0, bg=_GREEN_BASE, **kwargs)
        self.size = size
        self.state_val = "idle"
        self.canvas = tk.Canvas(self, width=size, height=size, bd=0,
                                highlightthickness=0, bg=_GREEN_BASE)
        self.canvas.pack()
        self.canvas.bind("<Configure>", self._redraw)

    def set_state(self, s):
        self.state_val = s
        self._redraw()

    def _redraw(self, _e=None):
        c = self.canvas
        c.delete("all")
        s = self.size
        hi, mid, lo = self._COLORS.get(self.state_val, self._COLORS["idle"])

        # 1px зазор по краям для «рамки»
        margin = 1
        _pixel_rect(c, margin, margin, s - margin * 2, s - margin * 2, mid)
        # Верхний блик
        bh = max(1, (s - margin * 2) // 3)
        _pixel_rect(c, margin, margin, s - margin * 2, bh, hi)
        # Нижняя тень
        _pixel_rect(c, margin, s - margin - bh, s - margin * 2, bh, lo)
        # Контур
        _pixel_rect(c, margin, margin, s - margin * 2, s - margin * 2,
                    outline=_BORDER_DARK, width=1)

        # Иконка внутри
        if s >= 12 and self.state_val == "ok":
            c.create_line(s * 0.30, s * 0.55, s * 0.45, s * 0.70,
                          fill="#ffffff", width=2)
            c.create_line(s * 0.45, s * 0.70, s * 0.72, s * 0.35,
                          fill="#ffffff", width=2)
        elif s >= 12 and self.state_val == "work":
            c.create_line(s * 0.5, s * 0.5, s * 0.5, s * 0.25, fill="#ffffff", width=2)
            c.create_line(s * 0.5, s * 0.5, s * 0.75, s * 0.5, fill="#ffffff", width=2)
        elif s >= 12 and self.state_val == "err":
            c.create_line(s * 0.30, s * 0.30, s * 0.70, s * 0.70,
                          fill="#ffffff", width=2)
            c.create_line(s * 0.70, s * 0.30, s * 0.30, s * 0.70,
                          fill="#ffffff", width=2)


# ─────────────────────────────────────────────────────────────────────────────
# MCCheckbox — пиксельный квадрат с галочкой
# ─────────────────────────────────────────────────────────────────────────────
class MCCheckbox(tk.Frame):
    def __init__(self, parent, text="", value=False, command=None, **kwargs):
        super().__init__(parent, bd=0, highlightthickness=0, bg=_GREEN_BASE, **kwargs)
        self._text = text
        self._val = bool(value)
        self._cmd = command
        self.canvas = tk.Canvas(self, height=22, bd=0, highlightthickness=0, bg=_GREEN_BASE)
        self.canvas.pack(side="left", fill="y")
        self.canvas.bind("<Configure>", self._redraw)
        self.canvas.bind("<Button-1>", self._on_click)
        self.bind("<Button-1>", self._on_click)
        self.canvas.configure(cursor="hand2")
        self._label_text = text

    def _redraw(self, _e=None):
        c = self.canvas
        c.delete("all")
        w = max(40, c.winfo_height() * 4)
        c.configure(width=w)
        h = c.winfo_height() or 22
        # Квадрат
        box = h - 4
        bx, by = 2, 2
        if self._val:
            _pixel_rect(c, bx, by, box, box, _GREEN_HI)
            _pixel_rect(c, bx + 1, by + box - 2, box - 2, 2, _GREEN_LO)
            # Галочка
            c.create_line(bx + box * 0.20, by + box * 0.55,
                          bx + box * 0.40, by + box * 0.72,
                          fill="#ffffff", width=2)
            c.create_line(bx + box * 0.40, by + box * 0.72,
                          bx + box * 0.78, by + box * 0.30,
                          fill="#ffffff", width=2)
        else:
            _pixel_rect(c, bx, by, box, box, "#cccccc")
            _pixel_rect(c, bx + 1, by + box - 2, box - 2, 2, "#888888")
        _pixel_rect(c, bx, by, box, box, outline=_BORDER_DARK, width=1)
        # Текст
        c.create_text(bx + box + 8, h / 2, text=self._text, anchor="w",
                      font=("Segoe UI", 10, "bold"), fill="#ffffff")

    def _on_click(self, _e=None):
        self._val = not self._val
        self._redraw()
        if self._cmd:
            try:
                self._cmd(self._val)
            except Exception:
                pass

    def get(self):
        return self._val

    def set(self, v):
        self._val = bool(v)
        self._redraw()


# ─────────────────────────────────────────────────────────────────────────────
# MCTabs — вкладки в Minecraft-стиле (язычки сверху)
# ─────────────────────────────────────────────────────────────────────────────
class MCTabs(tk.Frame):
    """Горизонтальный ряд закладок-язычков сверху + контейнер страниц.
    Каждая страница — обычный tk.Frame, доступ по tabs[title].
    """

    def __init__(self, parent, tabs=None, **kwargs):
        super().__init__(parent, bd=0, highlightthickness=0, bg=_GREEN_BASE, **kwargs)
        self.tabs_order = list(tabs or [])
        self.tabs_frames = {t: tk.Frame(self, bg="#ebd3aa", bd=1,
                                        highlightthickness=1,
                                        highlightbackground=_BORDER_DARK)
                            for t in self.tabs_order}
        self._active = self.tabs_order[0] if self.tabs_order else None

        # Рисуем панель язычков сверху
        self._bar_canvas = tk.Canvas(self, height=30, bd=0, highlightthickness=0,
                                     bg=_GREEN_BASE)
        self._bar_canvas.pack(side="top", fill="x")
        self._bar_canvas.bind("<Configure>", self._redraw_bar)

        # Pack остальных страниц стопкой (виден только активный)
        for t, frm in self.tabs_frames.items():
            frm.pack(fill="both", expand=True)
        self._show_active()

    def add_tab(self, title):
        if title in self.tabs_frames:
            return self.tabs_frames[title]
        frm = tk.Frame(self, bg="#ebd3aa", bd=1, highlightthickness=1,
                       highlightbackground=_BORDER_DARK)
        self.tabs_frames[title] = frm
        self.tabs_order.append(title)
        frm.pack(fill="both", expand=True)
        self._redraw_bar()
        self._show_active()
        return frm

    def select(self, title):
        if title not in self.tabs_frames:
            return
        self._active = title
        self._redraw_bar()
        self._show_active()

    def current(self):
        return self._active

    def _show_active(self):
        for t, frm in self.tabs_frames.items():
            frm.pack_forget()
        if self._active and self._active in self.tabs_frames:
            self.tabs_frames[self._active].pack(fill="both", expand=True)

    def _redraw_bar(self, _e=None):
        c = self._bar_canvas
        c.delete("all")
        w = max(2, c.winfo_width())
        h = max(2, c.winfo_height())
        _fill_bg_blocks(c, 0, 0, w, h, step=8)

        # Распределяем вкладки равномерно
        pad = 6
        cursor = 4
        for tab in self.tabs_order:
            # Ширина по тексту — пропорционально длине
            tw = max(80, 12 * len(tab) + 24)
            tw = min(tw, w // max(1, len(self.tabs_order)))
            active = (tab == self._active)
            color_base = _GREEN_BASE if active else _WOOD_BASE
            color_hi = _GREEN_HI if active else _WOOD_HI
            color_lo = _GREEN_LO if active else _WOOD_LO
            txt_col = "#ffffff" if active else "#1a1a1a"
            # Рисуем «язычок»
            _pixel_rect(c, cursor, 8, tw, h - 8, color_base)
            _pixel_rect(c, cursor, 8, tw, 4, color_hi)
            _pixel_rect(c, cursor, h - 12, tw, 4, color_lo)
            _pixel_rect(c, cursor, 8, tw, h - 8, outline=_BORDER_DARK, width=1)
            c.create_text(cursor + tw // 2, h // 2 + 2, text=tab,
                          fill=txt_col, font=("Segoe UI", 9, "bold"))
            cursor += tw

        # Нижняя линия пергамента под язычками
        _pixel_rect(c, 0, h - 2, w, 2, _BORDER_DARK)

        # Привязываем клики по язычкам
        # (перепривязываем на каждом ресайзе, отвязав старые теги-привязки)
        c.unbind("<Button-1>")
        cursor = 4
        for tab in self.tabs_order:
            tw = max(80, 12 * len(tab) + 24)
            tw = min(tw, w // max(1, len(self.tabs_order)))
            x1, y1, x2, y2 = cursor, 8, cursor + tw, h
            tag = "tab_" + tab
            if c.find_withtag(tag):
                c.delete(tag)
            # Делаем прозрачный rect, чтобы перехватить клик
            r = c.create_rectangle(x1, y1, x2, y2, fill="", outline="", tags=(tag,))
            c.tag_bind(tag, "<Button-1>", lambda _e, t=tab: self.select(t))
            c.tag_bind(tag, "<Enter>", lambda _e, r=r: c.itemconfigure(r, fill="#ffffff", stipple="gray12"))
            c.tag_bind(tag, "<Leave>", lambda _e, r=r: c.itemconfigure(r, fill=""))
            cursor += tw

    def winfo_children(self):
        # Возвращаем дочерние виджеты активной страницы — чтобы .pack() работал на MCTabs
        if self._active and self._active in self.tabs_frames:
            return self.tabs_frames[self._active].winfo_children()
        return []
