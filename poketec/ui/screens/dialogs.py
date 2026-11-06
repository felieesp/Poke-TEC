"""Diálogos y elecciones emergentes, y un ejecutor de secuencias de pantallas."""
from typing import Callable, Iterable, List, Optional, Sequence

from .. import theme
from ..renderer import Renderer
from ..widgets import BACK, MessageBox, MenuItem, MenuList, panel
from .base import Screen


class Dialog(Screen):
    """Texto con efecto máquina de escribir. Enter avanza; al final llama a `on_done`."""
    overlay = True

    def __init__(self, app, lines: Iterable[str], on_done: Optional[Callable[[], None]] = None,
                 speaker: str = ""):
        super().__init__(app)
        self.lines: List[str] = [l for l in lines if l] or ["..."]
        self.on_done = on_done
        self.speaker = speaker
        self.index = 0
        self.box = MessageBox()
        self.box.say(self.lines[0])

    def update(self, dt: float) -> None:
        super().update(dt)
        self.box.update(dt)

    def draw(self, r: Renderer) -> None:
        y = theme.HEIGHT - 160
        if self.speaker:
            w = r.text_width(self.speaker, 18, True) + 36
            panel(r, 50, y - 34, w, 40, fill=theme.NIGHT_2, border=theme.GOLD, radius=10, shadow=False)
            r.text(50 + w / 2, y - 14, self.speaker, 18, theme.WHITE, "center", True)
        self.box.draw(r, 40, y, theme.WIDTH - 80, 130, 22, prompt=True, blink=self.clock)

    def on_key(self, action: str) -> None:
        if action not in ("confirm", "back"):
            return
        if not self.box.done:
            self.box.skip()
            return
        self.index += 1
        if self.index < len(self.lines):
            self.box.say(self.lines[self.index])
            return
        self.app.pop()
        if self.on_done:
            self.on_done()

    def on_click(self, x: int, y: int) -> None:
        self.on_key("confirm")


class Choice(Screen):
    """Pregunta con opciones. `on_pick(i)` recibe el índice o BACK."""
    overlay = True

    def __init__(self, app, prompt: str, options: Sequence, on_pick: Callable[[int], None],
                 cancel: bool = True, width: int = 420):
        super().__init__(app)
        self.prompt, self.on_pick, self.cancel, self.width = prompt, on_pick, cancel, width
        self.menu = MenuList(options, row_h=42, gap=8, text_size=19)

    def _finish(self, value: int) -> None:
        self.app.pop()
        self.on_pick(value)

    def draw(self, r: Renderer) -> None:
        lines = r.wrap(self.prompt, 19, self.width - 50, True) if self.prompt else []
        h = 30 + len(lines) * 26 + len(self.menu.items) * 50 + 14
        x = (theme.WIDTH - self.width) // 2
        y = max(30, (theme.HEIGHT - h) // 2)
        r.dim(0, 0, theme.WIDTH, theme.HEIGHT, 0.45)
        panel(r, x, y, self.width, h, fill=theme.PAPER)
        for i, line in enumerate(lines):
            r.text(x + 25, y + 18 + i * 26, line, 19, theme.INK, "nw", True)
        self.menu.draw(r, x + 20, y + 24 + len(lines) * 26, self.width - 40)

    def on_key(self, action: str) -> None:
        choice = self.menu.handle_key(action)
        if choice is None:
            return
        if choice == BACK:
            if self.cancel:
                self._finish(BACK)
            return
        self._finish(choice)

    def on_click(self, x: int, y: int) -> None:
        choice = self.menu.handle_click(x, y)
        if choice is not None:
            self._finish(choice)

    def on_motion(self, x: int, y: int) -> None:
        self.menu.handle_motion(x, y)


def confirm(app, prompt: str, on_yes: Callable[[], None], on_no: Optional[Callable[[], None]] = None) -> None:
    """Atajo: pregunta Sí/No."""
    def picked(i: int) -> None:
        if i == 0:
            on_yes()
        elif on_no:
            on_no()
    app.push(Choice(app, prompt, ["Sí", "No"], picked))


def run_sequence(steps: Sequence[Callable[[Callable[[], None]], None]],
                 final: Optional[Callable[[], None]] = None) -> None:
    """Ejecuta pasos en orden. Cada paso recibe `next_step` y debe llamarlo al terminar
    (normalmente como `on_done` de la pantalla que abre)."""
    queue = list(steps)

    def advance() -> None:
        if queue:
            queue.pop(0)(advance)
        elif final:
            final()

    advance()
