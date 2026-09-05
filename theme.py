# -*- coding: utf-8 -*-
"""Темы оформления GUI. Сейчас встроены 3 рабочие темы (светлая, тёмная, «кубики»/Minecraft-like);
после выбора одного из 7 стилей по картинкам сюда добавится точная тема."""

THEMES = {
    "Светлая": {
        "bg": "#f3f3f3", "fg": "#1a1a1a", "panel": "#ffffff",
        "accent": "#2f6fdd", "entry_bg": "#ffffff", "entry_fg": "#1a1a1a",
        "tree_bg": "#ffffff", "tree_fg": "#1a1a1a", "select": "#bcd6f7",
        "font": ("Segoe UI", 10), "loading": "#fff2b3", "ready": "#e2f5e2",
    },
    "Тёмная": {
        "bg": "#1e1f24", "fg": "#e6e6e6", "panel": "#26272e",
        "accent": "#4da3ff", "entry_bg": "#2b2c33", "entry_fg": "#e6e6e6",
        "tree_bg": "#26272e", "tree_fg": "#e6e6e6", "select": "#34507a",
        "font": ("Segoe UI", 10), "loading": "#5a5426", "ready": "#274a2c",
    },
    "Кубики": {
        "bg": "#3a3a3a", "fg": "#f0f0f0", "panel": "#4a4a4a",
        "accent": "#5fbf44", "entry_bg": "#2b2b2b", "entry_fg": "#f0f0f0",
        "tree_bg": "#333333", "tree_fg": "#f0f0f0", "select": "#5fbf44",
        "font": ("Courier New", 10, "bold"), "loading": "#8a7a2a", "ready": "#2f6b2f",
    },
}


def list_themes():
    return list(THEMES.keys())


def apply_theme(root, name):
    t = THEMES.get(name) or THEMES["Светлая"]
    style = None
    try:
        from tkinter import ttk
        style = ttk.Style(root)
        try:
            style.theme_use("clam")  # clam позволяет красить виджеты
        except Exception:
            pass
        f = t["font"]
        style.configure(".", background=t["bg"], foreground=t["fg"], font=f)
        style.configure("TFrame", background=t["bg"])
        style.configure("TLabel", background=t["bg"], foreground=t["fg"])
        style.configure("TButton", background=t["panel"], foreground=t["fg"], padding=5)
        style.map("TButton", background=[("active", t["accent"])])
        style.configure("TEntry", fieldbackground=t["entry_bg"], foreground=t["entry_fg"])
        style.configure("TCombobox", fieldbackground=t["entry_bg"], foreground=t["entry_fg"])
        style.configure("Treeview", background=t["tree_bg"], foreground=t["tree_fg"],
                        fieldbackground=t["tree_bg"], rowheight=24)
        style.map("Treeview", background=[("selected", t["select"])],
                  foreground=[("selected", t["fg"])])
        style.configure("Treeview.Heading", background=t["panel"], foreground=t["fg"])
        style.configure("TRadiobutton", background=t["bg"], foreground=t["fg"])
        style.configure("TCheckbutton", background=t["bg"], foreground=t["fg"])
    except Exception:
        pass
    try:
        root.configure(bg=t["bg"])
    except Exception:
        pass
    return t
