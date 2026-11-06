"""Colores, tamaños y textos comunes para que todos los menús se vean iguales."""
from typing import Dict

WIDTH, HEIGHT = 960, 600
FPS = 30

# Paleta
INK = "#202838"
INK_SOFT = "#4a5468"
PAPER = "#f8f4e4"
PAPER_DARK = "#e6dfc4"
PANEL = "#fffdf4"
BORDER = "#303848"
ACCENT = "#e63946"
ACCENT_DARK = "#b02a35"
BLUE = "#3a6ea5"
GOLD = "#f4b942"
OK = "#3fae5a"
WARN = "#f0a030"
DANGER = "#d64545"
NIGHT = "#141a2e"
NIGHT_2 = "#232c4a"
WHITE = "#ffffff"
DISABLED = "#a8a8a0"

TYPE_COLORS: Dict[str, str] = {
    "normal": "#a8a878", "fire": "#f08030", "water": "#6890f0", "grass": "#78c850",
    "electric": "#f8d030", "fighting": "#c03028", "poison": "#a040a0", "ground": "#e0c068",
    "flying": "#a890f0", "psychic": "#f85888", "bug": "#a8b820", "rock": "#b8a038",
    "ghost": "#705898",
}
STATUS_COLORS = {"quemadura": "#f08030", "paralisis": "#e8c020", "veneno": "#a040a0", "sueno": "#7a8aa0"}

# Escenarios de combate / zonas: (cielo arriba, cielo abajo, suelo, suelo claro)
THEMES = {
    "town":    ("#8fd0f0", "#d8f0ff", "#8cc870", "#a6dc88"),
    "route":   ("#8fd0f0", "#d8f0ff", "#78c060", "#92d478"),
    "forest":  ("#5aa070", "#a8d8a0", "#4c9050", "#62a864"),
    "coast":   ("#78c8f0", "#e0f6ff", "#e8dca0", "#f4ecbc"),
    "volcano": ("#c05838", "#f0b080", "#8a6a58", "#a08068"),
    "classic": ("#7ab8f0", "#d8ecff", "#7cc468", "#98d880"),
}

# Letra: se pide una familia habitual; Tk usa la más parecida disponible
FONT_FAMILY = "Helvetica"
