# -*- coding: utf-8 -*-
"""Темы оформления GUI для Genspark Arkhivator.

В текущей версии 4 темы:
  • Светлая / Тёмная / Кубики — прежние рабочие варианты;
  • Майнкрафт — точное воспроизведение референса:
        - зелёная кирпичная рамка окна,
        - пергаментные панели (#ebd3aa),
        - объёмные кнопки с бликом/тенью (#5e9c32 / #417a22 / #2d5916),
        - деревянные язычки вкладок (#bd9354),
        - пиксельный шрифт (Minecraft если установлен, иначе Courier New Bold).

Майнкрафт-тема сделана дефолтной: целиком совпадает с эталонным
скриншотом reference_screenshot.png.
"""
import os
import tkinter as _tk

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "data", "assets")
os.makedirs(ASSETS_DIR, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# Палитра Minecraft-стиля (по эталонному скриншоту)
# ─────────────────────────────────────────────────────────────────────────────
MC_PALETTE = {
    # Зелёная пиксельная рамка («трава / зелёный кирпич»)
    "bg_block_dark": "#1f4a16",
    "bg_block_mid":  "#2f5e1e",
    "bg_block_high": "#5c8a3d",
    "bg_tile_gap":   "#162e0c",

    # Пергамент
    "panel":         "#ebd3aa",
    "panel_dark":    "#d6bf8f",
    "panel_light":   "#f3e0b8",

    # Дерево / камень
    "border_dark":   "#3c2d1d",
    "border_mid":    "#756c5a",
    "border_light":  "#a8966b",

    # Акцентные зелёные (кнопка «ВЫГРУЗИТЬ ЧАТ»)
    "accent":        "#417a22",
    "accent_light":  "#5e9c32",
    "accent_dark":   "#2d5916",

    # Деревянные кнопки вторичные
    "wood":          "#bd9354",
    "wood_light":    "#d6bf8f",
    "wood_dark":     "#7a5f30",

    # Состояния
    "star":          "#e6b800",
    "ok":            "#35b23a",
    "warn":          "#e6b800",
    "err":           "#d64545",
    "silver":        "#9a9a9a",
    "idle":          "#9a9a9a",

    # Подсветка строк
    "select":        "#d1e7b9",
    "loading":       "#fff2b3",
    "ready":         "#e2f5e2",
}


THEMES = {
    "Светлая": {
        "bg": "#f3f3f3", "fg": "#1a1a1a", "panel": "#ffffff",
        "accent": "#2f6fdd", "entry_bg": "#ffffff", "entry_fg": "#1a1a1a",
        "tree_bg": "#ffffff", "tree_fg": "#1a1a1a", "select": "#bcd6f7",
        "font": ("Segoe UI", 10), "loading": "#fff2b3", "ready": "#e2f5e2",
        "border_color": "#c0c0c0", "border_mid": "#c0c0c0", "border_light": "#dadada",
        "panel_dark": "#eaeaea", "accent_light": "#5b95ee", "accent_dark": "#1b4f9e",
        "wood": "#e0e0e0", "wood_light": "#eeeeee", "wood_dark": "#a0a0a0",
        "ok": "#35b23a", "warn": "#e6b800", "err": "#d64545", "star": "#e6b800",
        "silver": "#9a9a9a", "style": "modern",
    },
    "Тёмная": {
        "bg": "#1e1f24", "fg": "#e6e6e6", "panel": "#26272e",
        "accent": "#4da3ff", "entry_bg": "#2b2c33", "entry_fg": "#e6e6e6",
        "tree_bg": "#26272e", "tree_fg": "#e6e6e6", "select": "#34507a",
        "font": ("Segoe UI", 10), "loading": "#5a5426", "ready": "#274a2c",
        "border_color": "#0f0f12", "border_mid": "#3a3a45", "border_light": "#4a4a55",
        "panel_dark": "#1c1d22", "accent_light": "#7ec2ff", "accent_dark": "#2b6fc5",
        "wood": "#3a3a45", "wood_light": "#4a4a55", "wood_dark": "#26272e",
        "ok": "#35b23a", "warn": "#e6b800", "err": "#d64545", "star": "#e6b800",
        "silver": "#9a9a9a", "style": "modern",
    },
    "Кубики": {
        "bg": "#3a3a3a", "fg": "#f0f0f0", "panel": "#4a4a4a",
        "accent": "#5fbf44", "entry_bg": "#2b2b2b", "entry_fg": "#f0f0f0",
        "tree_bg": "#333333", "tree_fg": "#f0f0f0", "select": "#5fbf44",
        "font": ("Courier New", 10, "bold"), "loading": "#8a7a2a", "ready": "#2f6b2f",
        "border_color": "#202020", "border_mid": "#555555", "border_light": "#777777",
        "panel_dark": "#3a3a3a", "accent_light": "#7fdf64", "accent_dark": "#3f8a29",
        "wood": "#5a5a5a", "wood_light": "#7a7a7a", "wood_dark": "#2a2a2a",
        "ok": "#5fbf44", "warn": "#e6b800", "err": "#d64545", "star": "#e6b800",
        "silver": "#9a9a9a", "style": "modern",
    },
    "Майнкрафт": {
        "bg": MC_PALETTE["bg_block_dark"],
        "fg": "#1a1a1a",
        "panel": MC_PALETTE["panel"],
        "panel_dark": MC_PALETTE["panel_dark"],
        "panel_light": MC_PALETTE["panel_light"],
        "accent": MC_PALETTE["accent"],
        "accent_light": MC_PALETTE["accent_light"],
        "accent_dark": MC_PALETTE["accent_dark"],
        "wood": MC_PALETTE["wood"],
        "wood_light": MC_PALETTE["wood_light"],
        "wood_dark": MC_PALETTE["wood_dark"],
        "border_color": MC_PALETTE["border_dark"],
        "border_mid": MC_PALETTE["border_mid"],
        "border_light": MC_PALETTE["border_light"],
        "entry_bg": "#fdf6e0",
        "entry_fg": "#1a1a1a",
        "tree_bg": MC_PALETTE["panel"],
        "tree_fg": "#1a1a1a",
        "select": MC_PALETTE["select"],
        "loading": MC_PALETTE["loading"],
        "ready": MC_PALETTE["ready"],
        "ok": MC_PALETTE["ok"],
        "warn": MC_PALETTE["warn"],
        "err": MC_PALETTE["err"],
        "silver": MC_PALETTE["silver"],
        "star": MC_PALETTE["star"],
        "font": ("Segoe UI", 10, "bold"),
        "mc_font": None,  # вычисляется лениво в get_theme()
        "style": "minecraft",
    },
}


def _try_mc_font():
    """Подбираем моноширинный пиксельный шрифт, если в системе он установлен.
    Ищем среди кандидатов по списку, иначе fallback на Segoe UI Bold."""
    try:
        from tkinter import font as tkfont
        try:
            available = set(tkfont.families())
        except Exception:
            available = set()
        # Предпочтения: Minecraft / Minecraftia / VT323 / PressStart / Fixedsys
        candidates = [
            ("Minecraft", 10, "bold"),
            ("Minecraftia", 10),
            ("VT323", 11),
            ("PressStart2P", 9),
            ("Press Start 2P", 9),
            ("Pixeled", 10),
            ("Fixedsys", 10),
        ]
        for cand in candidates:
            if cand[0] in available:
                return cand
    except Exception:
        pass
    return ("Segoe UI", 10, "bold")


def list_themes():
    return list(THEMES.keys())


def get_theme(name):
    t = THEMES.get(name) or THEMES["Майнкрафт"]
    if t.get("style") == "minecraft" and not t.get("mc_font"):
        t["mc_font"] = _try_mc_font()
    return t


def default_theme():
    return "Майнкрафт"


def mc_palette():
    return dict(MC_PALETTE)


def apply_theme(root, name):
    """Применяет тему к корневому окну Tk. Возвращает словарь с цветами
    и шрифтом — для виджетов, которые сами рисуют рамки/кнопки."""
    t = get_theme(name)
    is_mc = t.get("style") == "minecraft"

    try:
        from tkinter import ttk
        style = ttk.Style(root)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        f = t["font"]
        mc_f = t.get("mc_font") or f
        font_for = mc_f if is_mc else f

        # Базовая палитра
        style.configure(".", background=t["bg"], foreground=t["fg"], font=font_for)
        style.configure("TFrame", background=t["bg"])
        # Пергаментная (или белая) панель — НЕ рисует поверх наш canvas, но даёт фон tk-виджетам внутри
        style.configure("Panel.TFrame", background=t["panel"], relief="flat", borderwidth=0)

        # Кнопки ttk (используются как fallback, основные рисуются MCButton)
        style.configure(
            "TButton",
            background=t["accent"] if is_mc else t["panel"],
            foreground="#ffffff" if is_mc else t["fg"],
            font=font_for, padding=4, relief="flat", borderwidth=0,
        )
        style.map("TButton", background=[("active", t["accent_light"] if is_mc else t["accent"])])

        style.configure(
            "TEntry",
            fieldbackground=t["entry_bg"], foreground=t["entry_fg"],
            font=font_for, relief="sunken", borderwidth=2,
        )
        style.configure(
            "TCombobox",
            fieldbackground=t["entry_bg"], foreground=t["entry_fg"],
            font=font_for,
        )

        style.configure(
            "Treeview",
            background=t["tree_bg"], foreground=t["tree_fg"],
            fieldbackground=t["tree_bg"], rowheight=26,
            font=font_for, borderwidth=0,
        )
        style.map(
            "Treeview",
            background=[("selected", t["select"])],
            foreground=[("selected", t["fg"])],
        )
        style.configure(
            "Treeview.Heading",
            background=t["panel_dark"] if is_mc else t["panel"],
            foreground=t["fg"], font=font_for,
            relief="ridge" if is_mc else "raised",
            borderwidth=1,
        )
        style.configure("TRadiobutton", background=t["bg"], foreground=t["fg"], font=font_for)
        style.configure("TCheckbutton", background=t["bg"], foreground=t["fg"], font=font_for)

        # Notebook (мы его переопределяем через MCTabs, но стиль на всякий)
        style.configure("TNotebook", background=t["bg"], borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            background=t["wood"] if is_mc else t["panel"],
            foreground=t["fg"], padding=[12, 5],
            font=font_for,
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", t["accent"] if is_mc else t["accent"])],
            foreground=[("selected", "#ffffff" if is_mc else t["fg"])],
        )

        # Scrollbar
        style.configure(
            "Vertical.TScrollbar",
            background=t["wood"] if is_mc else t["panel"],
            troughcolor=t["bg"],
            bordercolor=t.get("border_color", "#999"),
            arrowcolor=t["fg"],
        )
    except Exception:
        pass

    try:
        root.configure(bg=t["bg"])
    except Exception:
        pass
    return t
