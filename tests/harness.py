"""Ayudante para probar la interfaz sin ventana: dibuja en una imagen PIL."""
import random
from pathlib import Path

from poketec.ui.app import App
from poketec.ui.renderer import PilRenderer
from poketec.ui.screens.menu import MainMenu


class Harness:
    def __init__(self, tmp_path, seed: int = 1):
        self.renderer = PilRenderer()
        self.app = App(self.renderer, rng=random.Random(seed), save_path=Path(tmp_path) / "aventura.json",
                       strict=True)
        self.app.push(MainMenu(self.app))
        self.shots = 0

    @property
    def top(self):
        return self.app.top

    def tick(self, seconds: float = 0.1, step: float = 1 / 30) -> None:
        t = 0.0
        while t < seconds:
            self.app.update(step)
            self.app.draw()
            t += step

    def press(self, *actions: str, wait: float = 0.05) -> None:
        for action in actions:
            self.app.key(action)
            self.tick(wait)

    def type(self, text: str) -> None:
        for ch in text:
            self.app.text(ch)

    def shot(self, name: str, folder="/tmp/claude-0/shots") -> None:
        self.app.draw()
        Path(folder).mkdir(parents=True, exist_ok=True)
        self.renderer.save(Path(folder) / f"{name}.png")

    def screen_names(self):
        return [type(s).__name__ for s in self.app.stack]
