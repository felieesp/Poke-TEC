"""Ventana de tkinter: traduce teclado y ratón a acciones y ejecuta el bucle de juego."""
import time
from typing import Optional

from . import theme

# Tecla (keysym de Tk) -> acción lógica
KEY_ACTIONS = {
    "Up": "up", "Down": "down", "Left": "left", "Right": "right",
    "Return": "confirm", "KP_Enter": "confirm", "space": "confirm",
    "Escape": "back", "BackSpace": "backspace", "Tab": "menu",
}
LETTER_ACTIONS = {
    "w": "up", "s": "down", "a": "left", "d": "right",
    "z": "confirm", "x": "back", "m": "menu",
}


def translate_key(keysym: str, char: str, wants_text: bool) -> Optional[tuple]:
    """Devuelve ('action', nombre), ('text', carácter) o None.

    Mientras se escribe un nombre las letras son texto (si no, 'w/a/s/d' moverían el cursor).
    """
    if keysym in ("space",) and wants_text:
        return ("text", " ")
    if keysym in KEY_ACTIONS:
        action = KEY_ACTIONS[keysym]
        if wants_text and action == "menu":
            return None
        return ("action", action)
    if wants_text:
        if char and char.isprintable():
            return ("text", char)
        return None
    action = LETTER_ACTIONS.get(keysym.lower()) if len(keysym) == 1 else None
    return ("action", action) if action else None


def run() -> None:
    import tkinter as tk
    from .app import App
    from .renderer import TkRenderer
    from .screens.menu import MainMenu

    root = tk.Tk()
    root.title("Poke-TEC")
    root.resizable(False, False)
    canvas = tk.Canvas(root, width=theme.WIDTH, height=theme.HEIGHT, highlightthickness=0, bg=theme.NIGHT)
    canvas.pack()
    app = App(TkRenderer(canvas))
    app.push(MainMenu(app))

    def on_key(event) -> None:
        wants = bool(app.top and app.top.wants_text)
        translated = translate_key(event.keysym, event.char, wants)
        if not translated:
            return
        kind, value = translated
        (app.key if kind == "action" else app.text)(value)

    root.bind("<Key>", on_key)
    canvas.bind("<Button-1>", lambda e: app.click(e.x, e.y))
    canvas.bind("<Motion>", lambda e: app.motion(e.x, e.y))
    root.protocol("WM_DELETE_WINDOW", root.destroy)
    state = {"last": time.perf_counter()}

    def tick() -> None:
        if not app.running:
            root.destroy()
            return
        now = time.perf_counter()
        dt = min(0.1, now - state["last"])
        state["last"] = now
        app.update(dt)
        app.draw()
        root.after(max(1, int(1000 / theme.FPS)), tick)

    canvas.focus_set()
    tick()
    root.mainloop()
