"""Pantalla de aviso cuando algo falla de forma inesperada (el juego no se cierra)."""
from .. import theme
from ..renderer import Renderer
from ..widgets import panel
from .base import Screen


class ErrorScreen(Screen):
    background = theme.NIGHT

    def __init__(self, app, message: str):
        super().__init__(app)
        self.message = message

    def draw(self, r: Renderer) -> None:
        panel(r, 120, 150, 720, 300, fill=theme.PANEL, border=theme.DANGER)
        r.text(480, 200, "Algo salió mal", 32, theme.DANGER, "center", True)
        r.paragraph(160, 250, "El juego encontró un error inesperado, pero tu partida guardada está a salvo. "
                              "Se escribió un informe en poketec_error.log.", 18, theme.INK, 640)
        r.paragraph(160, 340, self.message[:150], 13, theme.INK_SOFT, 640)
        r.text(480, 410, "Pulsa Enter para volver al menú", 18, theme.ACCENT, "center", True)

    def on_key(self, action: str) -> None:
        if action in ("confirm", "back"):
            from .menu import MainMenu
            self.app.reset_to(MainMenu(self.app))

    def on_click(self, x: int, y: int) -> None:
        self.on_key("confirm")
