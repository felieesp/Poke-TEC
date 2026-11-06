"""Carga y generación de imágenes (sprites, personajes, mapas, fondos).

* Si existe `images/Pokemones/<Sprite>.png` se usa ese arte (escalado sin
  suavizar para conservar el pixel-art); si no, se dibuja una criatura genérica
  con los colores de su tipo, así que cualquier especie nueva funciona al instante.
* Los mapas del mundo se dibujan una sola vez por zona y se guardan en caché.
"""
import hashlib
from pathlib import Path
from typing import Dict, Optional, Tuple

from PIL import Image, ImageDraw

from ..engine.species import get_species
from ..engine.world import MAP_H, MAP_W, get_zone
from ..paths import IMAGES_DIR
from . import theme

TILE = 48
MAP_PX = (MAP_W * TILE, MAP_H * TILE)
SUPER = 4          # sobremuestreo para dibujar formas suaves


def _fit(img: Image.Image, box: Tuple[int, int]) -> Image.Image:
    """Escala la imagen para que quepa en `box` conservando la proporción."""
    scale = min(box[0] / img.width, box[1] / img.height)
    size = (max(1, round(img.width * scale)), max(1, round(img.height * scale)))
    method = Image.LANCZOS if scale < 0.75 else Image.NEAREST
    return img.resize(size, method)


def _mix(color: str, other: str, t: float) -> str:
    a = tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))
    b = tuple(int(other[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _noise(*key) -> int:
    """Número pseudoaleatorio estable a partir de una clave (para decorar mapas)."""
    return int(hashlib.md5(repr(key).encode()).hexdigest()[:8], 16)


class Assets:
    def __init__(self, images_dir: Path = IMAGES_DIR):
        self.dir = Path(images_dir)
        self._cache: Dict[tuple, Image.Image] = {}

    def _cached(self, key: tuple, build):
        if key not in self._cache:
            self._cache[key] = build()
        return self._cache[key]

    # ------------------------------------------------------------------ Pokémon
    def pokemon(self, species_id: str, box: Tuple[int, int] = (220, 220)) -> Image.Image:
        return self._cached(("mon", species_id, box), lambda: self._build_pokemon(species_id, box))

    def has_art(self, species_id: str) -> bool:
        return (self.dir / "Pokemones" / f"{get_species(species_id).sprite}.png").exists()

    def _build_pokemon(self, species_id: str, box) -> Image.Image:
        species = get_species(species_id)
        path = self.dir / "Pokemones" / f"{species.sprite}.png"
        if path.exists():
            try:
                img = Image.open(path).convert("RGBA")
                bbox = img.getbbox()
                if bbox:
                    img = img.crop(bbox)
                return _fit(img, box)
            except (OSError, ValueError):
                pass
        return self._generic_creature(species, box)

    def _generic_creature(self, species, box) -> Image.Image:
        """Criatura de respaldo: forma y colores dependen del tipo y del nombre."""
        n = SUPER
        w, h = box[0] * n, box[1] * n
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        main = theme.TYPE_COLORS.get(species.types[0], "#a8a878")
        second = theme.TYPE_COLORS.get(species.types[-1], main)
        light = _mix(main, "#ffffff", 0.45)
        dark = _mix(main, "#000000", 0.35)
        seed = _noise(species.id)
        shape = seed % 4
        cx, cy = w // 2, int(h * 0.58)
        bw, bh = int(w * 0.30), int(h * 0.30)
        # cola / adornos según la forma
        if shape == 0:      # orejas puntiagudas
            for sx in (-1, 1):
                d.polygon([(cx + sx * bw * 0.35, cy - bh * 0.7), (cx + sx * bw * 0.95, cy - bh * 1.75),
                           (cx + sx * bw * 0.85, cy - bh * 0.45)], fill=main, outline=dark)
        elif shape == 1:    # cuerno
            d.polygon([(cx - bw * 0.12, cy - bh * 0.85), (cx, cy - bh * 1.8), (cx + bw * 0.12, cy - bh * 0.85)],
                      fill=second, outline=dark)
        elif shape == 2:    # orejas redondas
            for sx in (-1, 1):
                d.ellipse([cx + sx * bw * 0.7 - bw * 0.25, cy - bh * 1.35, cx + sx * bw * 0.7 + bw * 0.25,
                           cy - bh * 0.75], fill=main, outline=dark)
        else:               # cresta
            for k in range(3):
                x = cx + (k - 1) * bw * 0.3
                d.polygon([(x - bw * 0.12, cy - bh * 0.8), (x, cy - bh * 1.45), (x + bw * 0.12, cy - bh * 0.8)],
                          fill=second, outline=dark)
        d.ellipse([cx + bw * 0.55, cy - bh * 0.2, cx + bw * 1.5, cy + bh * 0.4], fill=second, outline=dark)  # cola
        d.ellipse([cx - bw, cy - bh, cx + bw, cy + bh], fill=main, outline=dark, width=n * 2)               # cuerpo
        d.ellipse([cx - bw * 0.6, cy - bh * 0.1, cx + bw * 0.6, cy + bh * 0.9], fill=light)                  # barriga
        for sx in (-1, 1):                                                                                   # patas
            d.ellipse([cx + sx * bw * 0.55 - bw * 0.28, cy + bh * 0.7, cx + sx * bw * 0.55 + bw * 0.28,
                       cy + bh * 1.2], fill=dark)
        for sx in (-1, 1):                                                                                   # ojos
            ex, ey = cx + sx * bw * 0.38, cy - bh * 0.35
            d.ellipse([ex - bw * 0.16, ey - bw * 0.16, ex + bw * 0.16, ey + bw * 0.16], fill="white", outline=dark)
            d.ellipse([ex - bw * 0.07, ey - bw * 0.05, ex + bw * 0.07, ey + bw * 0.09], fill=theme.INK)
        d.arc([cx - bw * 0.25, cy - bh * 0.15, cx + bw * 0.25, cy + bh * 0.2], 20, 160, fill=dark, width=n)
        img = img.resize(box, Image.LANCZOS)
        bbox = img.getbbox()
        return img.crop(bbox) if bbox else img

    # ------------------------------------------------------------------ personajes
    def trainer(self, avatar: str, box: Tuple[int, int] = (160, 200)) -> Image.Image:
        return self._cached(("trainer", avatar, box), lambda: self._build_trainer(avatar, box))

    def _build_trainer(self, avatar: str, box) -> Image.Image:
        path = self.dir / "Entrenadores" / f"{avatar}.png"
        if path.exists():
            try:
                img = Image.open(path).convert("RGBA")
                bbox = img.getbbox()
                return _fit(img.crop(bbox) if bbox else img, box)
            except (OSError, ValueError):
                pass
        return self.character("#e63946", "down", box[1])

    def character(self, color: str, facing: str = "down", size: int = TILE,
                  skin: str = "#f2c9a0") -> Image.Image:
        """Personaje dibujado (para NPC y entrenadores). `color` es su ropa."""
        return self._cached(("char", color, facing, size, skin),
                            lambda: self._draw_character(color, facing, size, skin))

    @staticmethod
    def _draw_character(color: str, facing: str, size: int, skin: str) -> Image.Image:
        n = SUPER
        s = size * n
        img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        dark = _mix(color, "#000000", 0.35)
        d.ellipse([s * 0.22, s * 0.84, s * 0.78, s * 0.97], fill=(0, 0, 0, 70))               # sombra
        d.rounded_rectangle([s * 0.28, s * 0.50, s * 0.72, s * 0.88], s * 0.10, fill=color, outline=dark, width=n)
        d.rectangle([s * 0.34, s * 0.82, s * 0.46, s * 0.92], fill=dark)                          # pies
        d.rectangle([s * 0.54, s * 0.82, s * 0.66, s * 0.92], fill=dark)
        d.ellipse([s * 0.25, s * 0.12, s * 0.75, s * 0.62], fill=skin, outline=_mix(skin, "#000000", 0.4), width=n)
        hair = _mix(color, "#000000", 0.5)
        if facing == "up":
            d.pieslice([s * 0.23, s * 0.10, s * 0.77, s * 0.64], 0, 360, fill=hair)
        else:
            d.pieslice([s * 0.23, s * 0.10, s * 0.77, s * 0.64], 180, 360, fill=hair)
            d.rectangle([s * 0.23, s * 0.30, s * 0.77, s * 0.36], fill=hair)
        eye = theme.INK
        if facing == "down":
            for x in (0.40, 0.60):
                d.ellipse([s * (x - 0.04), s * 0.42, s * (x + 0.04), s * 0.52], fill=eye)
        elif facing in ("left", "right"):
            x = 0.36 if facing == "left" else 0.64
            d.ellipse([s * (x - 0.04), s * 0.42, s * (x + 0.04), s * 0.52], fill=eye)
        return img.resize((size, size), Image.LANCZOS)

    # ------------------------------------------------------------------ mapas
    def zone_map(self, zone_id: str) -> Image.Image:
        return self._cached(("zone", zone_id), lambda: self._draw_zone(zone_id))

    def _draw_zone(self, zone_id: str) -> Image.Image:
        zone = get_zone(zone_id)
        sky_top, sky_bottom, ground, ground_light = theme.THEMES.get(zone.theme, theme.THEMES["route"])
        img = Image.new("RGBA", MAP_PX, ground)
        d = ImageDraw.Draw(img)
        blocks = self._building_blocks(zone.grid)
        for y, row in enumerate(zone.grid):
            for x, ch in enumerate(row):
                self._draw_tile(d, zone, x, y, ch, ground, ground_light, blocks)
        return img

    @staticmethod
    def _building_blocks(grid):
        """Agrupa casillas de edificio contiguas y averigua su puerta (C, M, G, L)."""
        seen, blocks = set(), {}
        cells = set("hCMGL")
        for y, row in enumerate(grid):
            for x, ch in enumerate(row):
                if ch not in cells or (x, y) in seen:
                    continue
                stack, members = [(x, y)], []
                seen.add((x, y))
                while stack:
                    cx, cy = stack.pop()
                    members.append((cx, cy))
                    for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                        if 0 <= ny < len(grid) and 0 <= nx < len(grid[ny]) and (nx, ny) not in seen \
                                and grid[ny][nx] in cells:
                            seen.add((nx, ny))
                            stack.append((nx, ny))
                door = next((grid[cy][cx] for cx, cy in members if grid[cy][cx] in "CMGL"), "h")
                top = min(cy for _, cy in members)
                for cx, cy in members:
                    blocks[(cx, cy)] = (door, top)
        return blocks

    def _draw_tile(self, d, zone, x, y, ch, ground, ground_light, blocks):
        t = TILE
        x0, y0 = x * t, y * t
        box = [x0, y0, x0 + t - 1, y0 + t - 1]
        r = _noise(zone.id, x, y)
        base = ground_light if (x + y) % 2 == 0 else ground
        if ch in "#fg,":
            d.rectangle(box, fill=base)
        if ch == ",":
            for k in range(3):
                px, py = x0 + 6 + (r >> (k * 5)) % (t - 12), y0 + 6 + (r >> (k * 5 + 2)) % (t - 12)
                d.line([px, py, px + 2, py - 5], fill=_mix(ground, "#000000", 0.2), width=2)
        elif ch == "g":
            dark = _mix(ground, "#1c5a2a", 0.55)
            d.rectangle(box, fill=_mix(ground, "#2e8a3e", 0.5))
            for k in range(7):
                px, py = x0 + 4 + (r >> k) % (t - 8), y0 + 14 + (r >> (k + 3)) % (t - 18)
                d.line([px, py, px - 3, py - 11], fill=dark, width=3)
                d.line([px, py, px + 3, py - 11], fill=_mix(dark, "#9be08a", 0.35), width=3)
        elif ch == "f":
            for k in range(4):
                px, py = x0 + 8 + (r >> (k * 4)) % (t - 16), y0 + 8 + (r >> (k * 4 + 2)) % (t - 16)
                col = ("#ff6b9d", "#ffd166", "#ffffff", "#b388ff")[(r >> k) % 4]
                d.ellipse([px - 4, py - 4, px + 4, py + 4], fill=col, outline="#00000030")
                d.ellipse([px - 1, py - 1, px + 1, py + 1], fill="#f9a825")
        elif ch == "#":
            d.rectangle([x0 + 20, y0 + 28, x0 + 28, y0 + 44], fill="#6b4a2f")
            d.ellipse([x0 + 3, y0 + 2, x0 + t - 3, y0 + 36], fill="#2d7a3a", outline="#1b4d25", width=2)
            d.ellipse([x0 + 10, y0 + 7, x0 + 26, y0 + 20], fill="#4aa04e")
        elif ch == "w":
            d.rectangle(box, fill="#3f86d8" if (x + y) % 2 else "#4a92e4")
            for k in range(2):
                wy = y0 + 12 + k * 18
                d.arc([x0 + 4, wy, x0 + 22, wy + 8], 200, 340, fill="#bfe0ff", width=2)
                d.arc([x0 + 24, wy + 4, x0 + 42, wy + 12], 200, 340, fill="#bfe0ff", width=2)
        elif ch == "r":
            d.rectangle(box, fill=base)
            d.polygon([(x0 + 4, y0 + 42), (x0 + 12, y0 + 12), (x0 + 28, y0 + 6), (x0 + 44, y0 + 22),
                       (x0 + 42, y0 + 42)], fill="#8a8f98", outline="#55595f")
            d.polygon([(x0 + 12, y0 + 12), (x0 + 28, y0 + 6), (x0 + 30, y0 + 20), (x0 + 16, y0 + 26)],
                      fill="#aab0ba")
        elif ch == "." or ch.isdigit():
            d.rectangle(box, fill="#dcc896" if (x + y) % 2 == 0 else "#d4bf8a")
            for k in range(3):
                px, py = x0 + 6 + (r >> (k * 6)) % (t - 12), y0 + 6 + (r >> (k * 6 + 3)) % (t - 12)
                d.ellipse([px - 1, py - 1, px + 2, py + 2], fill="#b8a26e")
            if ch.isdigit():
                self._draw_exit_arrow(d, zone, x, y)
        elif ch in "hCMGL":
            self._draw_building_tile(d, x, y, ch, blocks[(x, y)])

    @staticmethod
    def _draw_exit_arrow(d, zone, x, y):
        t = TILE
        cx, cy = x * t + t // 2, y * t + t // 2
        if x == 0:
            pts = [(cx + 8, cy - 12), (cx - 8, cy), (cx + 8, cy + 12)]
        elif x == MAP_W - 1:
            pts = [(cx - 8, cy - 12), (cx + 8, cy), (cx - 8, cy + 12)]
        elif y == 0:
            pts = [(cx - 12, cy + 8), (cx, cy - 8), (cx + 12, cy + 8)]
        else:
            pts = [(cx - 12, cy - 8), (cx, cy + 8), (cx + 12, cy - 8)]
        d.line(pts, fill="#8b6f3a", width=5, joint="curve")

    @staticmethod
    def _draw_building_tile(d, x, y, ch, block):
        t = TILE
        x0, y0 = x * t, y * t
        door, top = block
        roof = {"C": "#e63946", "M": "#3a6ea5", "G": "#6c757d", "L": "#7b4fb0", "h": "#a0522d"}[door]
        wall = {"C": "#fdf0e6", "M": "#e8f0fa", "G": "#d9d9d9", "L": "#ece0f8", "h": "#f0e0c8"}[door]
        if y == top:
            d.rectangle([x0, y0, x0 + t - 1, y0 + t - 1], fill=roof)
            for k in range(0, t, 12):
                d.line([x0 + k, y0, x0 + k, y0 + t], fill=_mix(roof, "#000000", 0.18), width=2)
            d.rectangle([x0, y0 + t - 6, x0 + t - 1, y0 + t - 1], fill=_mix(roof, "#000000", 0.3))
        else:
            d.rectangle([x0, y0, x0 + t - 1, y0 + t - 1], fill=wall, outline=_mix(wall, "#000000", 0.25))
            if ch == "h":
                d.rectangle([x0 + 12, y0 + 10, x0 + 36, y0 + 34], fill="#8ecae6", outline="#4a6a7a", width=2)
                d.line([x0 + 24, y0 + 10, x0 + 24, y0 + 34], fill="#4a6a7a", width=2)
        if ch in "CMGL":
            d.rectangle([x0 + 8, y0 + 4, x0 + t - 9, y0 + t - 1], fill="#5b3a29", outline="#2b1a10", width=2)
            d.ellipse([x0 + t - 18, y0 + 26, x0 + t - 13, y0 + 31], fill="#f4b942")
            sx, sy = x0 + t // 2, y0 - 2
            d.rounded_rectangle([sx - 12, sy - 16, sx + 12, sy + 2], 4, fill="#fffdf4", outline="#303848", width=2)
            if ch == "C":
                d.rectangle([sx - 3, sy - 13, sx + 3, sy - 1], fill="#e63946")
                d.rectangle([sx - 7, sy - 9, sx + 7, sy - 5], fill="#e63946")
            elif ch == "M":
                d.polygon([(sx - 7, sy - 13), (sx, sy - 3), (sx + 7, sy - 13)], fill="#3a6ea5")
            elif ch == "G":
                d.ellipse([sx - 7, sy - 14, sx + 7, sy], fill="#f4b942", outline="#303848")
            else:
                d.polygon([(sx, sy - 15), (sx + 4, sy - 8), (sx + 9, sy - 8), (sx + 5, sy - 4), (sx + 6, sy + 1),
                           (sx, sy - 3), (sx - 6, sy + 1), (sx - 5, sy - 4), (sx - 9, sy - 8), (sx - 4, sy - 8)],
                          fill="#f4b942", outline="#303848")

    # ------------------------------------------------------------------ fondos
    def battle_backdrop(self, theme_id: str = "route", size: Tuple[int, int] = (theme.WIDTH, 420)) -> Image.Image:
        return self._cached(("bg", theme_id, size), lambda: self._draw_backdrop(theme_id, size))

    @staticmethod
    def _draw_backdrop(theme_id, size) -> Image.Image:
        sky_top, sky_bottom, ground, ground_light = theme.THEMES.get(theme_id, theme.THEMES["route"])
        w, h = size
        img = Image.new("RGBA", size, sky_top)
        d = ImageDraw.Draw(img)
        horizon = int(h * 0.55)
        for y in range(horizon):
            t = y / horizon
            d.line([0, y, w, y], fill=_mix(sky_top, sky_bottom, t))
        for y in range(horizon, h):
            t = (y - horizon) / max(1, h - horizon)
            d.line([0, y, w, y], fill=_mix(ground_light, ground, t))
        # colinas lejanas
        d.ellipse([-120, horizon - 50, 360, horizon + 70], fill=_mix(ground, "#ffffff", 0.2))
        d.ellipse([480, horizon - 70, 1100, horizon + 80], fill=_mix(ground, "#ffffff", 0.12))
        # plataformas
        for cx, cy, rx, ry in ((int(w * 0.72), int(h * 0.55), 150, 38), (int(w * 0.24), int(h * 0.90), 190, 46)):
            d.ellipse([cx - rx - 4, cy - ry + 6, cx + rx + 4, cy + ry + 10], fill=_mix(ground, "#000000", 0.35))
            d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=_mix(ground_light, "#ffffff", 0.15),
                      outline=_mix(ground, "#000000", 0.3), width=3)
        return img

    def menu_backdrop(self) -> Image.Image:
        return self._cached(("menu_bg",), self._draw_menu_backdrop)

    @staticmethod
    def _draw_menu_backdrop() -> Image.Image:
        w, h = theme.WIDTH, theme.HEIGHT
        img = Image.new("RGBA", (w, h), theme.NIGHT)
        d = ImageDraw.Draw(img)
        for y in range(h):
            d.line([0, y, w, y], fill=_mix(theme.NIGHT, "#3a2a5a", y / h))
        for i in range(70):                                  # estrellas
            r = _noise("star", i)
            x, y, s = r % w, (r >> 10) % int(h * 0.7), 1 + (r >> 20) % 2
            d.ellipse([x, y, x + s, y + s], fill=_mix("#ffffff", theme.NIGHT, (r >> 24) % 60 / 100))
        d.ellipse([w * 0.62, h * 0.12, w * 0.62 + 120, h * 0.12 + 120], fill="#f6efc8")
        d.ellipse([w * 0.62 + 24, h * 0.12 + 14, w * 0.62 + 120, h * 0.12 + 120], fill="#3a2a5a")
        d.ellipse([-200, int(h * 0.82), w + 200, h + 300], fill="#1b2a3a")
        d.ellipse([-100, int(h * 0.88), w * 0.6, h + 200], fill="#223648")
        return img

    # ------------------------------------------------------------------ iconos
    def icon(self, species_id: str, px: int = 56) -> Image.Image:
        return self.pokemon(species_id, (px, px))


_default: Optional[Assets] = None


def get_assets() -> Assets:
    global _default
    if _default is None:
        _default = Assets()
    return _default
