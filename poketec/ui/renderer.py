"""Capa de dibujo.

La interfaz solo habla con `Renderer`. Hay dos implementaciones:
  * `TkRenderer`  - dibuja en un `tkinter.Canvas` (lo que ve el jugador).
  * `PilRenderer` - dibuja en una imagen PIL (pruebas automáticas y capturas).
Así casi toda la GUI se puede comprobar sin abrir una ventana.
"""
from typing import Dict, List, Optional, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont

from . import theme


class Renderer:
    width = theme.WIDTH
    height = theme.HEIGHT

    # ---- ciclo de dibujo
    def begin(self, color: str = theme.NIGHT) -> None: ...
    def end(self) -> None: ...
    # ---- primitivas
    def rect(self, x1, y1, x2, y2, fill=None, outline=None, width=1) -> None: ...
    def rrect(self, x1, y1, x2, y2, r=10, fill=None, outline=None, width=1) -> None: ...
    def oval(self, x1, y1, x2, y2, fill=None, outline=None, width=1) -> None: ...
    def line(self, points: Sequence[float], color: str, width: int = 1) -> None: ...
    def poly(self, points: Sequence[float], fill=None, outline=None, width=1) -> None: ...
    def text(self, x, y, s: str, size: int = 14, color: str = theme.INK, anchor: str = "nw",
             bold: bool = False) -> None: ...
    def text_width(self, s: str, size: int = 14, bold: bool = False) -> int: ...
    def image(self, img: Image.Image, x, y, anchor: str = "nw") -> None: ...
    def dim(self, x1, y1, x2, y2, alpha: float = 0.5) -> None: ...

    # ---- utilidades comunes
    def wrap(self, s: str, size: int, max_width: int, bold: bool = False) -> List[str]:
        """Parte un texto en líneas que caben en `max_width` píxeles."""
        lines: List[str] = []
        for paragraph in s.split("\n"):
            words, current = paragraph.split(" "), ""
            for word in words:
                trial = word if not current else current + " " + word
                if current and self.text_width(trial, size, bold) > max_width:
                    lines.append(current)
                    current = word
                else:
                    current = trial
            lines.append(current)
        return lines

    def paragraph(self, x, y, s, size=14, color=theme.INK, max_width=300, bold=False,
                  line_height: Optional[float] = None, max_lines: Optional[int] = None) -> int:
        """Dibuja texto con saltos de línea automáticos. Devuelve la altura usada."""
        lh = line_height or size * 1.35
        lines = self.wrap(s, size, max_width, bold)
        if max_lines:
            lines = lines[:max_lines]
        for i, line in enumerate(lines):
            self.text(x, y + i * lh, line, size, color, "nw", bold)
        return int(len(lines) * lh)


def anchor_offset(anchor: str, w: float, h: float) -> Tuple[float, float]:
    """Desplazamiento (dx, dy) para que (x, y) sea el punto de anclaje."""
    dx = 0.0
    dy = 0.0
    if anchor in ("n", "center", "s"):
        dx = -w / 2
    elif anchor in ("ne", "e", "se"):
        dx = -w
    if anchor in ("w", "center", "e"):
        dy = -h / 2
    elif anchor in ("sw", "s", "se"):
        dy = -h
    return dx, dy


# ============================================================================= Tkinter
class TkRenderer(Renderer):
    def __init__(self, canvas):
        import tkinter.font as tkfont
        self._tkfont = tkfont
        self.canvas = canvas
        self._photos: Dict[int, tuple] = {}
        self._fonts: Dict[tuple, object] = {}

    def _font(self, size: int, bold: bool):
        key = (size, bold)
        if key not in self._fonts:
            self._fonts[key] = self._tkfont.Font(family=theme.FONT_FAMILY, size=-size,
                                                 weight="bold" if bold else "normal")
        return self._fonts[key]

    def begin(self, color: str = theme.NIGHT) -> None:
        self.canvas.delete("all")
        self.canvas.configure(bg=color)

    def end(self) -> None:
        pass

    def rect(self, x1, y1, x2, y2, fill=None, outline=None, width=1):
        self.canvas.create_rectangle(x1, y1, x2, y2, fill=fill or "", outline=outline or "", width=width)

    def rrect(self, x1, y1, x2, y2, r=10, fill=None, outline=None, width=1):
        r = max(0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
        pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2, x2 - r, y2,
               x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        self.canvas.create_polygon(pts, smooth=True, fill=fill or "", outline=outline or "", width=width)

    def oval(self, x1, y1, x2, y2, fill=None, outline=None, width=1):
        self.canvas.create_oval(x1, y1, x2, y2, fill=fill or "", outline=outline or "", width=width)

    def line(self, points, color, width=1):
        self.canvas.create_line(*points, fill=color, width=width, capstyle="round", joinstyle="round")

    def poly(self, points, fill=None, outline=None, width=1):
        self.canvas.create_polygon(*points, fill=fill or "", outline=outline or "", width=width)

    def text(self, x, y, s, size=14, color=theme.INK, anchor="nw", bold=False):
        self.canvas.create_text(x, y, text=s, fill=color, anchor=anchor, font=self._font(size, bold))

    def text_width(self, s, size=14, bold=False):
        return self._font(size, bold).measure(s)

    def image(self, img, x, y, anchor="nw"):
        from PIL import ImageTk
        entry = self._photos.get(id(img))
        if entry is None or entry[0] is not img:
            entry = (img, ImageTk.PhotoImage(img))
            self._photos[id(img)] = entry
        self.canvas.create_image(x, y, image=entry[1], anchor=anchor)

    def dim(self, x1, y1, x2, y2, alpha=0.5):
        self.canvas.create_rectangle(x1, y1, x2, y2, fill="black", outline="",
                                     stipple="gray50" if alpha >= 0.4 else "gray25")


# ============================================================================= PIL
_FONT_DIR = "/usr/share/fonts/truetype/dejavu/"


class PilRenderer(Renderer):
    """Dibuja en una imagen. Pensado para pruebas y capturas de pantalla."""

    def __init__(self):
        self.img = Image.new("RGBA", (self.width, self.height), theme.NIGHT)
        self.d = ImageDraw.Draw(self.img)
        self._fonts: Dict[tuple, ImageFont.FreeTypeFont] = {}
        self.calls = 0

    def _font(self, size: int, bold: bool):
        key = (size, bold)
        if key not in self._fonts:
            name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
            try:
                self._fonts[key] = ImageFont.truetype(_FONT_DIR + name, size)
            except OSError:
                self._fonts[key] = ImageFont.load_default()
        return self._fonts[key]

    def begin(self, color=theme.NIGHT):
        self.img = Image.new("RGBA", (self.width, self.height), color)
        self.d = ImageDraw.Draw(self.img)
        self.calls = 0

    def end(self):
        pass

    def rect(self, x1, y1, x2, y2, fill=None, outline=None, width=1):
        self.calls += 1
        self.d.rectangle([x1, y1, x2, y2], fill=fill, outline=outline, width=width if outline else 0)

    def rrect(self, x1, y1, x2, y2, r=10, fill=None, outline=None, width=1):
        self.calls += 1
        self.d.rounded_rectangle([x1, y1, x2, y2], radius=r, fill=fill, outline=outline,
                                 width=width if outline else 0)

    def oval(self, x1, y1, x2, y2, fill=None, outline=None, width=1):
        self.calls += 1
        self.d.ellipse([x1, y1, x2, y2], fill=fill, outline=outline, width=width if outline else 0)

    def line(self, points, color, width=1):
        self.calls += 1
        self.d.line(list(points), fill=color, width=width)

    def poly(self, points, fill=None, outline=None, width=1):
        self.calls += 1
        pts = list(zip(points[0::2], points[1::2]))
        self.d.polygon(pts, fill=fill, outline=outline)

    def text(self, x, y, s, size=14, color=theme.INK, anchor="nw", bold=False):
        self.calls += 1
        font = self._font(size, bold)
        w = self.text_width(s, size, bold)
        dx, dy = anchor_offset(anchor, w, size * 1.2)
        self.d.text((x + dx, y + dy), s, fill=color, font=font)

    def text_width(self, s, size=14, bold=False):
        return int(self._font(size, bold).getlength(s))

    def image(self, img, x, y, anchor="nw"):
        self.calls += 1
        dx, dy = anchor_offset(anchor, img.width, img.height)
        layer = Image.new("RGBA", self.img.size, (0, 0, 0, 0))
        layer.paste(img.convert("RGBA"), (int(x + dx), int(y + dy)))
        self.img = Image.alpha_composite(self.img, layer)
        self.d = ImageDraw.Draw(self.img)

    def dim(self, x1, y1, x2, y2, alpha=0.5):
        self.calls += 1
        layer = Image.new("RGBA", self.img.size, (0, 0, 0, 0))
        ImageDraw.Draw(layer).rectangle([x1, y1, x2, y2], fill=(0, 0, 0, int(255 * alpha)))
        self.img = Image.alpha_composite(self.img, layer)
        self.d = ImageDraw.Draw(self.img)

    def save(self, path) -> None:
        self.img.convert("RGB").save(path)
