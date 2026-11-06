"""Componentes de interfaz reutilizables (todos dibujan con `Renderer`)."""
from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence, Tuple

from ..engine.elements import TYPE_NAMES_ES
from ..engine.pokemon import STATUS_LABELS, Pokemon
from . import theme
from .renderer import Renderer

BACK = -1


def inside(x, y, rect) -> bool:
    return rect[0] <= x <= rect[2] and rect[1] <= y <= rect[3]


# ----------------------------------------------------------------------------- paneles y texto
def panel(r: Renderer, x, y, w, h, fill=theme.PANEL, border=theme.BORDER, radius=12, shadow=True,
          width=3) -> None:
    if shadow:
        r.rrect(x + 4, y + 5, x + w + 4, y + h + 5, radius, fill="#00000040")
    r.rrect(x, y, x + w, y + h, radius, fill=fill, outline=border, width=width)


def title_bar(r: Renderer, text: str, subtitle: str = "") -> None:
    r.rect(0, 0, theme.WIDTH, 64, fill=theme.NIGHT_2)
    r.rect(0, 62, theme.WIDTH, 66, fill=theme.ACCENT)
    r.text(28, 32, text, 28, theme.WHITE, "w", bold=True)
    if subtitle:
        r.text(theme.WIDTH - 28, 32, subtitle, 16, "#c8d0e8", "e")


def hint_bar(r: Renderer, text: str) -> None:
    r.rect(0, theme.HEIGHT - 30, theme.WIDTH, theme.HEIGHT, fill=theme.NIGHT_2)
    r.text(theme.WIDTH // 2, theme.HEIGHT - 15, text, 13, "#c8d0e8", "center")


def type_badge(r: Renderer, x, y, type_id: str, h=20) -> int:
    """Etiqueta de tipo. Devuelve su anchura."""
    label = TYPE_NAMES_ES.get(type_id, type_id).upper()
    w = r.text_width(label, 12, True) + 16
    r.rrect(x, y, x + w, y + h, h // 2, fill=theme.TYPE_COLORS.get(type_id, "#888888"), outline="#00000060")
    r.text(x + w / 2, y + h / 2, label, 12, theme.WHITE, "center", True)
    return int(w)


def status_badge(r: Renderer, x, y, status: Optional[str]) -> int:
    if not status:
        return 0
    label = STATUS_LABELS[status]
    r.rrect(x, y, x + 36, y + 18, 6, fill=theme.STATUS_COLORS[status], outline="#00000060")
    r.text(x + 18, y + 9, label, 11, theme.WHITE, "center", True)
    return 40


def hp_color(fraction: float) -> str:
    return theme.OK if fraction > 0.5 else theme.WARN if fraction > 0.2 else theme.DANGER


def bar(r: Renderer, x, y, w, h, fraction: float, color: str, back="#3a4254") -> None:
    fraction = max(0.0, min(1.0, fraction))
    r.rrect(x, y, x + w, y + h, h // 2, fill=back, outline="#1a2030", width=2)
    if fraction > 0:
        fill_w = max(4, int((w - 4) * fraction))
        r.rrect(x + 2, y + 2, x + 2 + fill_w, y + h - 2, max(2, h // 2 - 2), fill=color)


def hp_bar(r: Renderer, x, y, w, fraction: float, h=12) -> None:
    bar(r, x, y, w, h, fraction, hp_color(fraction))


# ----------------------------------------------------------------------------- menú de opciones
@dataclass
class MenuItem:
    label: str
    enabled: bool = True
    hint: str = ""
    badge: str = ""
    color: Optional[str] = None


class MenuList:
    """Lista de opciones navegable con teclado y ratón (1 o más columnas)."""

    def __init__(self, items: Sequence, cols: int = 1, row_h: int = 44, gap: int = 8, text_size: int = 20,
                 visible_rows: Optional[int] = None):
        self.cols, self.row_h, self.gap, self.text_size = cols, row_h, gap, text_size
        self.visible_rows = visible_rows          # None = se muestran todas
        self.items: List[MenuItem] = []
        self.index = 0
        self.top = 0                              # primera fila visible
        self._hits: List[Tuple[Tuple[int, int, int, int], int]] = []
        self.set_items(items)

    def set_items(self, items: Sequence, keep_index: bool = False) -> None:
        self.items = [i if isinstance(i, MenuItem) else MenuItem(str(i)) for i in items]
        self.index = min(self.index, max(0, len(self.items) - 1)) if keep_index else 0
        self.top = 0
        self._hits = []

    @property
    def current(self) -> Optional[MenuItem]:
        return self.items[self.index] if self.items else None

    # ---- entrada
    def move(self, action: str) -> bool:
        if not self.items:
            return False
        n, c = len(self.items), self.cols
        i = self.index
        if action == "up":
            i = i - c if i - c >= 0 else i
        elif action == "down":
            i = i + c if i + c < n else i
        elif action == "left" and c > 1:
            i = i - 1 if i % c > 0 else i
        elif action == "right" and c > 1:
            i = i + 1 if i % c < c - 1 and i + 1 < n else i
        elif action == "left" and c == 1:
            return False
        moved = i != self.index
        self.index = i
        return moved

    def handle_key(self, action: str) -> Optional[int]:
        """Devuelve el índice elegido, BACK, o None si solo se navegó."""
        if action in ("up", "down", "left", "right"):
            self.move(action)
            return None
        if action == "confirm" and self.items and self.items[self.index].enabled:
            return self.index
        if action in ("back", "backspace"):
            return BACK
        return None

    def hit(self, x, y) -> Optional[int]:
        for rect, i in self._hits:
            if inside(x, y, rect):
                return i
        return None

    def handle_click(self, x, y) -> Optional[int]:
        i = self.hit(x, y)
        if i is not None:
            self.index = i
            if self.items[i].enabled:
                return i
        return None

    def handle_motion(self, x, y) -> None:
        i = self.hit(x, y)
        if i is not None:
            self.index = i

    # ---- dibujo
    def _scroll_to_index(self) -> None:
        if self.visible_rows is None:
            self.top = 0
            return
        row = self.index // self.cols
        if row < self.top:
            self.top = row
        elif row >= self.top + self.visible_rows:
            self.top = row - self.visible_rows + 1

    def draw(self, r: Renderer, x, y, w) -> int:
        """Dibuja la lista; devuelve la altura ocupada."""
        cols = self.cols
        cell_w = (w - self.gap * (cols - 1)) // cols
        self._hits = []
        self._scroll_to_index()
        total_rows = (len(self.items) + cols - 1) // cols
        shown_rows = total_rows if self.visible_rows is None else min(self.visible_rows, total_rows)
        for i, item in enumerate(self.items):
            row = i // cols
            if not self.top <= row < self.top + shown_rows:
                continue
            cx = x + (i % cols) * (cell_w + self.gap)
            cy = y + (row - self.top) * (self.row_h + self.gap)
            self._hits.append(((cx, cy, cx + cell_w, cy + self.row_h), i))
            selected = i == self.index
            if selected:
                fill, border, ink = theme.ACCENT, theme.ACCENT_DARK, theme.WHITE
            else:
                fill, border, ink = theme.PANEL, theme.BORDER, theme.INK
            if not item.enabled:
                fill, border, ink = "#e4e0d0", "#a8a49a", theme.DISABLED
                if selected:
                    border = theme.INK_SOFT
            elif item.color and not selected:
                fill = item.color
                ink = theme.WHITE
            r.rrect(cx, cy, cx + cell_w, cy + self.row_h, 10, fill=fill, outline=border, width=3)
            if selected:
                r.poly([cx + 10, cy + self.row_h / 2 - 7, cx + 10, cy + self.row_h / 2 + 7,
                        cx + 20, cy + self.row_h / 2], fill=ink)
            r.text(cx + 30, cy + self.row_h / 2, item.label, self.text_size, ink, "w", True)
            if item.badge:
                r.text(cx + cell_w - 14, cy + self.row_h / 2, item.badge, self.text_size - 2, ink, "e", True)
        if self.visible_rows is not None and total_rows > shown_rows:       # indicadores de scroll
            mid = x + w - 12
            if self.top > 0:
                r.poly([mid - 8, y - 4, mid + 8, y - 4, mid, y - 14], fill=theme.INK_SOFT)
            if self.top + shown_rows < total_rows:
                bottom = y + shown_rows * (self.row_h + self.gap)
                r.poly([mid - 8, bottom, mid + 8, bottom, mid, bottom + 10], fill=theme.INK_SOFT)
        return shown_rows * (self.row_h + self.gap)


# ----------------------------------------------------------------------------- cuadro de mensajes
class MessageBox:
    """Cuadro de diálogo con efecto máquina de escribir."""

    SPEED = 70          # caracteres por segundo

    def __init__(self):
        self.text = ""
        self.shown = 0.0
        self.waiting = False

    def say(self, text: str) -> None:
        self.text, self.shown = text, 0.0

    @property
    def done(self) -> bool:
        return self.shown >= len(self.text)

    def skip(self) -> None:
        self.shown = float(len(self.text))

    def update(self, dt: float) -> None:
        if not self.done:
            self.shown = min(len(self.text), self.shown + dt * self.SPEED)

    def draw(self, r: Renderer, x, y, w, h, size=22, prompt=False, blink=0.0) -> None:
        panel(r, x, y, w, h, fill=theme.PANEL, border=theme.BORDER, radius=14)
        visible = self.text[:int(self.shown)]
        r.paragraph(x + 22, y + 16, visible, size, theme.INK, w - 60, True, size * 1.4)
        if prompt and self.done and int(blink * 2) % 2 == 0:
            r.poly([x + w - 34, y + h - 24, x + w - 18, y + h - 24, x + w - 26, y + h - 12], fill=theme.ACCENT)


# ----------------------------------------------------------------------------- tarjetas de Pokémon
def draw_mon_row(r: Renderer, assets, mon: Pokemon, x, y, w, h, selected=False, hint="") -> None:
    fill = "#fff4d6" if selected else theme.PANEL
    border = theme.ACCENT if selected else theme.BORDER
    if mon.is_fainted:
        fill = "#f0dcdc" if not selected else "#f8d0d0"
    r.rrect(x, y, x + w, y + h, 12, fill=fill, outline=border, width=4 if selected else 3)
    icon = assets.icon(mon.species_id, h - 14)
    r.image(icon, x + 8 + (h - 14) // 2, y + h // 2, "center")
    tx = x + h + 6
    r.text(tx, y + 8, mon.name, 20, theme.INK, "nw", True)
    r.text(tx + r.text_width(mon.name, 20, True) + 10, y + 12, f"Nv{mon.level}", 15, theme.INK_SOFT, "nw", True)
    status_badge(r, x + w - 52, y + 8, mon.status)
    if mon.is_fainted:
        r.text(x + w - 14, y + 14, "DEBILITADO", 13, theme.DANGER, "ne", True)
    bar_w = min(w - h - 130, 260)
    hp_bar(r, tx, y + h - 26, bar_w, mon.hp_fraction)
    r.text(tx + bar_w + 10, y + h - 20, f"{mon.hp}/{mon.max_hp}", 14, theme.INK, "w", True)
    if hint:
        r.text(x + w - 14, y + h - 18, hint, 13, theme.INK_SOFT, "e", True)


def draw_types(r: Renderer, x, y, types: Sequence[str], h=20) -> int:
    cx = x
    for t in types:
        cx += type_badge(r, cx, y, t, h) + 6
    return cx - x


def toast(r: Renderer, text: str, y: int = 530) -> None:
    w = r.text_width(text, 18, True) + 50
    x = (theme.WIDTH - w) // 2
    panel(r, x, y, w, 44, fill=theme.NIGHT_2, border=theme.GOLD, radius=22, shadow=True)
    r.text(theme.WIDTH // 2, y + 22, text, 18, theme.WHITE, "center", True)


class MonPicker:
    """Lista de Pokémon (equipo) seleccionable con teclado y ratón."""

    def __init__(self, team: Sequence[Pokemon], enabled: Optional[Callable[[int, Pokemon], bool]] = None,
                 hint: Optional[Callable[[int, Pokemon], str]] = None):
        self.team = list(team)
        self.enabled = enabled or (lambda i, m: True)
        self.hint = hint or (lambda i, m: "")
        self.index = self._first_enabled()
        self._rects: List[Tuple[int, int, int, int]] = []

    def _first_enabled(self) -> int:
        """El cursor empieza en el primer Pokémon elegible (no sobre uno debilitado o ya en combate)."""
        for i, mon in enumerate(self.team):
            if self.enabled(i, mon):
                return i
        return 0

    def set_team(self, team: Sequence[Pokemon]) -> None:
        self.team = list(team)
        self.index = min(self.index, max(0, len(self.team) - 1))

    def handle_key(self, action: str) -> Optional[int]:
        n = len(self.team)
        if action == "up" and self.index > 0:
            self.index -= 1
        elif action == "down" and self.index < n - 1:
            self.index += 1
        elif action == "confirm" and n and self.enabled(self.index, self.team[self.index]):
            return self.index
        elif action in ("back", "backspace"):
            return BACK
        return None

    def _hit(self, x, y) -> Optional[int]:
        for i, rect in enumerate(self._rects):
            if inside(x, y, rect):
                return i
        return None

    def handle_click(self, x, y) -> Optional[int]:
        i = self._hit(x, y)
        if i is not None:
            self.index = i
            if self.enabled(i, self.team[i]):
                return i
        return None

    def handle_motion(self, x, y) -> None:
        i = self._hit(x, y)
        if i is not None:
            self.index = i

    def draw(self, r: Renderer, assets, x, y, w, row_h=58, gap=6) -> None:
        self._rects = []
        for i, mon in enumerate(self.team):
            ry = y + i * (row_h + gap)
            self._rects.append((x, ry, x + w, ry + row_h))
            draw_mon_row(r, assets, mon, x, ry, w, row_h, selected=i == self.index, hint=self.hint(i, mon))
            if not self.enabled(i, mon):
                r.dim(x, ry, x + w, ry + row_h, 0.25)
