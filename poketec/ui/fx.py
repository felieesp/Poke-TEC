"""Efectos visuales de combate: ataques por tipo, impactos y la Poké Ball.

Todas las funciones reciben el progreso `p` de 0 a 1 y dibujan un solo fotograma.
"""
import math
from typing import Tuple

from . import theme
from .renderer import Renderer

Point = Tuple[float, float]


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _color(type_id: str) -> str:
    return theme.TYPE_COLORS.get(type_id, "#ffffff")


def ease_out(t: float) -> float:
    return 1 - (1 - t) ** 3


def ease_in_out(t: float) -> float:
    return 3 * t * t - 2 * t * t * t


# ----------------------------------------------------------------------------- impacto
def impact(r: Renderer, x: float, y: float, p: float, color: str, size: float = 70) -> None:
    """Estallido radial al golpear."""
    if p <= 0 or p >= 1:
        return
    rad = size * ease_out(p)
    width = max(1, int(6 * (1 - p)))
    r.oval(x - rad, y - rad, x + rad, y + rad, outline=color, width=width)
    for k in range(8):
        ang = k * math.pi / 4 + 0.3
        r.line([x + math.cos(ang) * rad * 0.45, y + math.sin(ang) * rad * 0.45,
                x + math.cos(ang) * rad * 1.15, y + math.sin(ang) * rad * 1.15], "#ffffff", max(1, width - 1))
    r.oval(x - rad * 0.35, y - rad * 0.35, x + rad * 0.35, y + rad * 0.35, fill=color if p < 0.5 else None,
           outline="#ffffff", width=2)


# ----------------------------------------------------------------------------- proyectiles por tipo
def projectile(r: Renderer, type_id: str, src: Point, dst: Point, p: float) -> None:
    t = ease_in_out(max(0.0, min(1.0, p)))
    x, y = _lerp(src[0], dst[0], t), _lerp(src[1], dst[1], t) - math.sin(t * math.pi) * 24
    base = _color(type_id)
    if type_id == "electric":
        pts = [src[0], src[1]]
        steps = 7
        for k in range(1, steps + 1):
            f = k / steps * t
            jx = math.sin(k * 7.3 + p * 40) * 18
            jy = math.cos(k * 5.1 + p * 33) * 18
            pts += [_lerp(src[0], dst[0], f) + jx, _lerp(src[1], dst[1], f) + jy]
        r.line(pts, "#fff7b0", 7)
        r.line(pts, "#f8d030", 3)
    elif type_id == "fire":
        flick = 1 + 0.15 * math.sin(p * 60)
        for rad, col in ((22, "#d83a18"), (16, "#f08030"), (9, "#ffe070")):
            r.oval(x - rad * flick, y - rad * flick, x + rad * flick, y + rad * flick, fill=col)
        for k in range(1, 4):
            tx, ty = _lerp(x, src[0], k * 0.07), _lerp(y, src[1], k * 0.07)
            r.oval(tx - 10 + k * 2, ty - 10 + k * 2, tx + 10 - k * 2, ty + 10 - k * 2, fill="#f08030")
    elif type_id == "water":
        for k in range(5):
            f = max(0.0, t - k * 0.06)
            dx, dy = _lerp(src[0], dst[0], f), _lerp(src[1], dst[1], f) - math.sin(f * math.pi) * 24
            rad = 11 - k * 1.5
            r.oval(dx - rad, dy - rad * 1.3, dx + rad, dy + rad, fill="#78a8ff", outline="#ffffff")
    elif type_id == "grass":
        for k in range(5):
            f = max(0.0, t - k * 0.05)
            dx = _lerp(src[0], dst[0], f)
            dy = _lerp(src[1], dst[1], f) + math.sin(f * 14 + k) * 14
            r.poly([dx, dy - 10, dx + 8, dy, dx, dy + 10, dx - 8, dy], fill="#58b848", outline="#2d7a3a")
    elif type_id in ("psychic", "ghost"):
        col = "#f85888" if type_id == "psychic" else "#6a4c98"
        for k in range(3):
            rad = 10 + k * 8 + 3 * math.sin(p * 25 + k)
            r.oval(x - rad, y - rad, x + rad, y + rad, outline=col, width=4 - k)
        r.oval(x - 7, y - 7, x + 7, y + 7, fill=col)
    elif type_id == "poison":
        for k in range(4):
            f = max(0.0, t - k * 0.07)
            dx, dy = _lerp(src[0], dst[0], f), _lerp(src[1], dst[1], f) - math.sin(f * math.pi) * 24 + k * 3
            r.oval(dx - 9 + k, dy - 9 + k, dx + 9 - k, dy + 9 - k, fill="#b858b8", outline="#6a2a6a")
    elif type_id in ("rock", "ground"):
        for k in range(4):
            f = max(0.0, t - k * 0.06)
            dx, dy = _lerp(src[0], dst[0], f), _lerp(src[1], dst[1], f) - math.sin(f * math.pi) * 24
            r.poly([dx - 9, dy - 6, dx + 3, dy - 11, dx + 10, dy + 2, dx - 2, dy + 10], fill="#a08850",
                   outline="#5a4a28")
    else:               # normal, fighting, flying, bug...
        r.oval(x - 14, y - 14, x + 14, y + 14, fill=base, outline="#ffffff", width=3)
        r.oval(x - 6, y - 6, x + 6, y + 6, fill="#ffffff")


def attack(r: Renderer, move_type: str, category: str, p: float, src: Point, dst: Point) -> None:
    """Un fotograma del ataque (progreso `p` de 0 a 1)."""
    color = _color(move_type)
    if category == "estado":
        # aura que se expande alrededor de quien lo usa
        for k in range(3):
            q = (p + k * 0.25) % 1.0
            rad = 30 + 60 * q
            r.oval(src[0] - rad, src[1] - rad * 0.9, src[0] + rad, src[1] + rad * 0.9, outline=color,
                   width=max(1, int(5 * (1 - q))))
        return
    if category == "fisico" and move_type not in ("fire", "water", "electric", "grass", "psychic"):
        impact(r, dst[0], dst[1], max(0.0, (p - 0.35) / 0.65), color)
        return
    travel = 0.55
    if p < travel:
        projectile(r, move_type, src, dst, p / travel)
    else:
        impact(r, dst[0], dst[1], (p - travel) / (1 - travel), color, 80)


def lunge_offset(p: float, toward: Point) -> Point:
    """Desplazamiento del atacante en un ataque físico (embiste y vuelve)."""
    amount = math.sin(min(1.0, p / 0.5) * math.pi) if p < 0.5 else 0.0
    return toward[0] * amount * 60, toward[1] * amount * 60


# ----------------------------------------------------------------------------- estados y estadísticas
def stat_arrows(r: Renderer, x: float, y: float, p: float, up: bool) -> None:
    color = "#e84040" if not up else "#40c060"
    for k in range(3):
        q = (p + k * 0.3) % 1.0
        ax = x + (k - 1) * 34
        ay = y - 20 * q if up else y - 60 + 20 * q + 30
        off = -1 if up else 1
        r.poly([ax, ay - 14 * off, ax + 12, ay + 2 * off, ax + 5, ay + 2 * off, ax + 5, ay + 16 * off,
                ax - 5, ay + 16 * off, ax - 5, ay + 2 * off, ax - 12, ay + 2 * off], fill=color, outline="#ffffff")


def sparkles(r: Renderer, x: float, y: float, p: float, color: str = "#8ff0a8") -> None:
    for k in range(6):
        ang = k * math.pi / 3 + p * 2
        rad = 30 + 40 * p
        sx, sy = x + math.cos(ang) * rad, y + math.sin(ang) * rad * 0.8 - p * 20
        s = 7 * (1 - p) + 2
        r.poly([sx, sy - s * 1.6, sx + s * 0.5, sy - s * 0.5, sx + s * 1.6, sy, sx + s * 0.5, sy + s * 0.5,
                sx, sy + s * 1.6, sx - s * 0.5, sy + s * 0.5, sx - s * 1.6, sy, sx - s * 0.5, sy - s * 0.5],
               fill=color)


# ----------------------------------------------------------------------------- Poké Ball
BALL_COLORS = {"pokeball": "#e63946", "superball": "#3a6ea5", "ultraball": "#f4b942", "masterball": "#8e44ad"}


def ball(r: Renderer, x: float, y: float, ball_id: str = "pokeball", tilt: float = 0.0, size: float = 18) -> None:
    """Dibuja una Poké Ball centrada en (x, y); `tilt` en radianes la balancea."""
    top = BALL_COLORS.get(ball_id, "#e63946")
    c, s = math.cos(tilt), math.sin(tilt)

    def pt(px: float, py: float) -> Tuple[float, float]:
        return x + px * c - py * s, y + px * s + py * c

    steps = 14
    upper = [pt(math.cos(math.pi + math.pi * k / steps) * size, math.sin(math.pi + math.pi * k / steps) * size)
             for k in range(steps + 1)]
    lower = [pt(math.cos(math.pi * k / steps) * size, math.sin(math.pi * k / steps) * size) for k in range(steps + 1)]
    r.poly([v for point in upper for v in point], fill=top, outline="#202838", width=2)
    r.poly([v for point in lower for v in point], fill="#f8f8f8", outline="#202838", width=2)
    a, b = pt(-size, 0), pt(size, 0)
    r.line([a[0], a[1], b[0], b[1]], "#202838", 3)
    cx, cy = pt(0, 0)
    r.oval(cx - size * 0.32, cy - size * 0.32, cx + size * 0.32, cy + size * 0.32, fill="#f8f8f8",
           outline="#202838", width=3)
