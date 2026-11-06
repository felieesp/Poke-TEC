"""Aplicación: pila de pantallas, entrada y bucle de dibujo (independiente de tkinter)."""
import random
import traceback
from pathlib import Path
from typing import List, Optional

from ..engine.adventure import Adventure
from ..engine.save import SaveError, has_save, load_player
from ..paths import ADVENTURE_SAVE, BASE_DIR
from . import theme
from .assets import Assets, get_assets
from .renderer import Renderer
from .screens.base import Screen

ERROR_LOG = BASE_DIR / "poketec_error.log"


class App:
    def __init__(self, renderer: Renderer, assets: Optional[Assets] = None,
                 rng: Optional[random.Random] = None, save_path: Path = ADVENTURE_SAVE,
                 strict: bool = False):
        self.r = renderer
        self.assets = assets or get_assets()
        self.rng = rng or random.Random()
        self.save_path = Path(save_path)
        self.strict = strict                # True: las excepciones se propagan (pruebas)
        self.stack: List[Screen] = []
        self.adventure: Optional[Adventure] = None
        self.running = True
        self.time = 0.0

    # ---- pila de pantallas ------------------------------------------------------------------
    @property
    def top(self) -> Optional[Screen]:
        return self.stack[-1] if self.stack else None

    def push(self, screen: Screen) -> Screen:
        self.stack.append(screen)
        self._safe(screen.on_enter)
        return screen

    def pop(self, result=None) -> None:
        if self.stack:
            self.stack.pop()
        if self.top:
            self._safe(self.top.on_resume, result)

    def replace(self, screen: Screen) -> Screen:
        if self.stack:
            self.stack.pop()
        return self.push(screen)

    def reset_to(self, screen: Screen) -> None:
        self.stack.clear()
        self.push(screen)

    def quit(self) -> None:
        self.running = False

    # ---- partida ----------------------------------------------------------------------------
    def has_save(self) -> bool:
        return has_save(self.save_path)

    def load_adventure(self) -> Adventure:
        player = load_player(self.save_path)
        self.adventure = Adventure(player, self.rng)
        return self.adventure

    def save_adventure(self) -> None:
        from ..engine.save import save_player
        if self.adventure:
            save_player(self.adventure.player, self.save_path)

    # ---- bucle ------------------------------------------------------------------------------
    def update(self, dt: float) -> None:
        self.time += dt
        if self.top:
            self._safe(self.top.update, dt)

    def draw(self) -> None:
        r = self.r
        start = len(self.stack) - 1
        while start > 0 and self.stack[start].overlay:
            start -= 1
        r.begin(self.stack[start].background if self.stack else theme.NIGHT)
        for screen in self.stack[max(start, 0):]:
            if not self._safe(screen.draw, r):
                break
        r.end()

    # ---- entrada ----------------------------------------------------------------------------
    def key(self, action: str) -> None:
        if self.top:
            self._safe(self.top.on_key, action)

    def text(self, char: str) -> None:
        if self.top:
            self._safe(self.top.on_text, char)

    def click(self, x: int, y: int) -> None:
        if self.top:
            self._safe(self.top.on_click, x, y)

    def motion(self, x: int, y: int) -> None:
        if self.top:
            self._safe(self.top.on_motion, x, y)

    # ---- errores ----------------------------------------------------------------------------
    def _safe(self, fn, *args) -> bool:
        """Ejecuta `fn`; ante un error lo registra y muestra una pantalla de aviso."""
        if self.strict:
            fn(*args)
            return True
        try:
            fn(*args)
            return True
        except Exception:                                   # noqa: BLE001 - red de seguridad de la GUI
            detail = traceback.format_exc()
            try:
                with open(ERROR_LOG, "a", encoding="utf-8") as fh:
                    fh.write(detail + "\n")
            except OSError:
                pass
            from .screens.errors import ErrorScreen
            if not isinstance(self.top, ErrorScreen):
                self.stack.append(ErrorScreen(self, detail.strip().splitlines()[-1]))
            return False
