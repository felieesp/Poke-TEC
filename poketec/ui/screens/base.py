"""Clase base de todas las pantallas."""
from .. import theme
from ..renderer import Renderer


class Screen:
    """Una pantalla del juego. La `App` mantiene una pila de pantallas.

    Las pantallas con `overlay = True` se dibujan encima de la anterior
    (menús emergentes, diálogos...).
    """

    overlay = False
    wants_text = False          # True: recibe caracteres sueltos (campo de nombre)
    background = theme.NIGHT

    def __init__(self, app):
        self.app = app
        self.clock = 0.0
        self._toast_text = ""
        self._toast_left = 0.0

    # ciclo de vida
    def on_enter(self) -> None: ...
    def on_resume(self, result=None) -> None:
        """Se llama cuando la pantalla de encima se cierra con `pop(result)`."""

    def update(self, dt: float) -> None:
        self.clock += dt
        if self._toast_left > 0:
            self._toast_left -= dt

    def draw(self, r: Renderer) -> None: ...

    # avisos breves
    def notify(self, text: str, seconds: float = 2.0) -> None:
        self._toast_text, self._toast_left = text, seconds

    def draw_toast(self, r: Renderer) -> None:
        if self._toast_left > 0 and self._toast_text:
            from ..widgets import toast
            toast(r, self._toast_text)

    # entrada
    def on_key(self, action: str) -> None: ...
    def on_text(self, char: str) -> None: ...
    def on_click(self, x: int, y: int) -> None: ...
    def on_motion(self, x: int, y: int) -> None: ...
