"""Menú principal, nueva aventura y récords."""
import math
from typing import List

from ...engine.adventure import Adventure
from ...engine.save import SaveError
from ...engine.scores import load_scores
from ...engine.species import get_species
from ...engine.world import STARTERS
from .. import fx, theme
from ..renderer import Renderer
from ..widgets import BACK, MenuItem, MenuList, bar, draw_types, hint_bar, panel, title_bar
from .base import Screen
from .dialogs import Dialog, confirm

AVATARS = ("Ash", "Rival")
DIFFICULTIES = (
    ("easy", "Fácil", "Los rivales eligen ataques al azar. Ideal para empezar."),
    ("normal", "Normal", "Los rivales eligen buenos ataques y curan a sus Pokémon."),
    ("hard", "Difícil", "Los rivales aprovechan tus debilidades y cambian de Pokémon con astucia."),
)


class MainMenu(Screen):
    def __init__(self, app):
        super().__init__(app)
        self.menu = MenuList([], row_h=42, gap=6, text_size=20)
        self._build()

    def _build(self) -> None:
        has_save = self.app.has_save()
        self.menu.set_items([
            MenuItem("Continuar", enabled=has_save),
            MenuItem("Nueva aventura"),
            MenuItem("Duelo Clásico"),
            MenuItem("Récords"),
            MenuItem("Salir"),
        ])
        self.menu.index = 0 if has_save else 1

    def on_resume(self, result=None) -> None:
        self._build()

    def _pick(self, i: int) -> None:
        app = self.app
        if i == 0:
            try:
                app.load_adventure()
            except SaveError as err:
                app.push(Dialog(app, [f"No se pudo cargar la partida: {err}"]))
                return
            from .overworld import Overworld
            app.reset_to(Overworld(app))
        elif i == 1:
            if app.has_save():
                confirm(app, "Ya tienes una partida guardada. Empezar una nueva la reemplazará. ¿Continuar?",
                        lambda: app.push(NewGameScreen(app)))
            else:
                app.push(NewGameScreen(app))
        elif i == 2:
            from .classic import ClassicSetup
            app.push(ClassicSetup(app))
        elif i == 3:
            app.push(ScoresScreen(app))
        elif i == 4:
            app.quit()

    def on_key(self, action: str) -> None:
        choice = self.menu.handle_key(action)
        if choice is not None and choice != BACK:
            self._pick(choice)

    def on_click(self, x: int, y: int) -> None:
        choice = self.menu.handle_click(x, y)
        if choice is not None:
            self._pick(choice)

    def on_motion(self, x: int, y: int) -> None:
        self.menu.handle_motion(x, y)

    def draw(self, r: Renderer) -> None:
        assets = self.app.assets
        r.image(assets.menu_backdrop(), 0, 0)
        t = self.clock
        # Pokémon iniciales flotando
        for k, sid in enumerate(STARTERS):
            x = 170 + k * 310
            bob = math.sin(t * 2 + k * 1.7) * 8
            r.oval(x - 70, 292, x + 70, 312, fill="#00000050")
            r.image(assets.pokemon(sid, (130, 130)), x, 300 + bob, "s")
        # título
        for dx, dy, color in ((4, 5, "#000000"), (0, 0, theme.GOLD)):
            r.text(theme.WIDTH // 2 + dx, 82 + dy, "POKE-TEC", 78, color, "center", True)
        r.text(theme.WIDTH // 2, 138, "Tu aventura Pokémon", 22, "#e0e6ff", "center", True)
        for bx in (330, 630):
            fx.ball(r, bx, 138, "pokeball", math.sin(t * 2 + bx) * 0.35, 14)
        panel(r, 340, 326, 280, 5 * 48 + 20, fill=theme.PAPER)
        self.menu.draw(r, 354, 340, 252)
        r.text(theme.WIDTH - 12, theme.HEIGHT - 10, "Poke-TEC v2", 12, "#8090b0", "se")
        self.draw_toast(r)


class NewGameScreen(Screen):
    """Asistente: nombre -> personaje -> Pokémon inicial -> dificultad."""
    background = theme.NIGHT
    STEPS = ("Tu nombre", "Tu personaje", "Tu primer Pokémon", "Dificultad")

    def __init__(self, app):
        super().__init__(app)
        self.step = 0
        self.name = ""
        self.avatar = 0
        self.starter = 0
        self.difficulty = 1

    @property
    def wants_text(self) -> bool:          # type: ignore[override]
        return self.step == 0

    # ---- entrada
    def on_text(self, char: str) -> None:
        if self.step == 0 and char.isprintable() and len(self.name) < 12 and char not in "\r\n\t":
            self.name += char

    def on_key(self, action: str) -> None:
        if action == "back":
            if self.step == 0:
                self.app.pop()
            else:
                self.step -= 1
            return
        if self.step == 0:
            if action == "backspace":
                self.name = self.name[:-1]
            elif action == "confirm":
                self.name = self.name.strip() or "Entrenador"
                self.step = 1
            return
        horizontal = action in ("left", "right")
        delta = -1 if action in ("left", "up") else 1 if action in ("right", "down") else 0
        if self.step == 1 and horizontal:
            self.avatar = (self.avatar + delta) % len(AVATARS)
        elif self.step == 2 and horizontal:
            self.starter = (self.starter + delta) % len(STARTERS)
        elif self.step == 3 and action in ("up", "down"):
            self.difficulty = (self.difficulty + delta) % len(DIFFICULTIES)
        elif action == "confirm":
            if self.step < 3:
                self.step += 1
            else:
                self._create()

    def on_click(self, x: int, y: int) -> None:
        self.on_key("confirm")

    def _create(self) -> None:
        app = self.app
        adv = Adventure.new_game(self.name, AVATARS[self.avatar], STARTERS[self.starter],
                                 DIFFICULTIES[self.difficulty][0], rng=app.rng)
        app.adventure = adv
        from .flow import autosave
        from .overworld import Overworld
        autosave(app)
        app.reset_to(Overworld(app))
        starter = get_species(STARTERS[self.starter]).name
        app.push(Dialog(app, [f"¡Hola, {adv.player.name}! Soy el Profesor Robles.",
                              f"Has elegido a {starter}: ¡cuídalo mucho!",
                              "Tu rival te espera en el este del pueblo. ¡Buena suerte!"],
                        speaker="Profesor Robles"))

    # ---- dibujo
    def draw(self, r: Renderer) -> None:
        title_bar(r, "Nueva aventura", f"Paso {self.step + 1} de {len(self.STEPS)}: {self.STEPS[self.step]}")
        draw = (self._draw_name, self._draw_avatar, self._draw_starter, self._draw_difficulty)[self.step]
        draw(r)
        hint = ("Escribe tu nombre · Enter: continuar · Esc: volver" if self.step == 0 else
                "← → elegir · Enter: continuar · Esc: atrás" if self.step < 3 else
                "↑ ↓ elegir · Enter: ¡comenzar! · Esc: atrás")
        hint_bar(r, hint)

    def _draw_name(self, r: Renderer) -> None:
        panel(r, 180, 160, 600, 260, fill=theme.PANEL)
        r.text(480, 210, "¿Cómo te llamas, entrenador?", 28, theme.INK, "center", True)
        r.rrect(260, 260, 700, 330, 12, fill=theme.WHITE, outline=theme.BORDER, width=3)
        cursor = "▌" if int(self.clock * 2) % 2 == 0 else " "
        r.text(480, 295, self.name + cursor, 34, theme.INK, "center", True)
        r.text(480, 370, f"{len(self.name)}/12 letras", 14, theme.INK_SOFT, "center")

    def _draw_avatar(self, r: Renderer) -> None:
        for i, avatar in enumerate(AVATARS):
            x = 300 + i * 360
            chosen = i == self.avatar
            panel(r, x - 150, 110, 300, 400, fill="#fff4d6" if chosen else theme.PANEL,
                  border=theme.ACCENT if chosen else theme.BORDER)
            r.image(self.app.assets.trainer(avatar, (200, 280)), x, 400, "s")
            r.text(x, 450, avatar if avatar != "Rival" else "Rival", 24, theme.INK, "center", True)
            if chosen:
                r.text(x, 484, "◀  ▶", 20, theme.ACCENT, "center", True)

    def _draw_starter(self, r: Renderer) -> None:
        for i, sid in enumerate(STARTERS):
            sp = get_species(sid)
            x = 170 + i * 310
            chosen = i == self.starter
            panel(r, x - 140, 100, 280, 430, fill="#fff4d6" if chosen else theme.PANEL,
                  border=theme.ACCENT if chosen else theme.BORDER)
            bob = math.sin(self.clock * 3) * 6 if chosen else 0
            r.image(self.app.assets.pokemon(sid, (190, 190)), x, 300 + bob, "s")
            r.text(x, 320, sp.name, 26, theme.INK, "center", True)
            draw_types(r, x - sum(r.text_width(t.upper(), 12, True) + 22 for t in sp.types) // 2, 354,
                       sp.types, 22)
            for k, (key, label) in enumerate((("hp", "PS"), ("atk", "Ataque"), ("def", "Defensa"), ("spe", "Veloc."))):
                y = 400 + k * 28
                r.text(x - 118, y, label, 13, theme.INK_SOFT, "nw", True)
                bar(r, x - 40, y + 3, 150, 9, sp.base[key] / 110, theme.GOLD)

    def _draw_difficulty(self, r: Renderer) -> None:
        for i, (_, label, desc) in enumerate(DIFFICULTIES):
            y = 120 + i * 130
            chosen = i == self.difficulty
            panel(r, 160, y, 640, 112, fill="#fff4d6" if chosen else theme.PANEL,
                  border=theme.ACCENT if chosen else theme.BORDER)
            r.text(190, y + 16, label, 28, theme.INK, "nw", True)
            r.paragraph(190, y + 58, desc, 17, theme.INK_SOFT, 580, True)
            if chosen:
                r.poly([172, y + 26, 172, y + 42, 184, y + 34], fill=theme.ACCENT)


class ScoresScreen(Screen):
    background = theme.NIGHT

    def __init__(self, app):
        super().__init__(app)
        self.scores = load_scores()

    def on_key(self, action: str) -> None:
        if action in ("back", "confirm"):
            self.app.pop()

    def on_click(self, x: int, y: int) -> None:
        self.app.pop()

    def draw(self, r: Renderer) -> None:
        title_bar(r, "Récords del Duelo Clásico", "Top 10")
        panel(r, 160, 90, 640, 460, fill=theme.PANEL)
        if not self.scores:
            r.text(480, 320, "Aún no hay récords. ¡Juega un Duelo Clásico!", 20, theme.INK_SOFT, "center", True)
        medal_colors = ("#f4b942", "#b8c0cc", "#c08850")
        for i, entry in enumerate(self.scores):
            y = 108 + i * 43
            r.rrect(176, y, 784, y + 38, 10, fill=theme.PAPER if i % 2 == 0 else "#f0ead0")
            color = medal_colors[i] if i < 3 else theme.NIGHT_2
            r.oval(184, y + 4, 214, y + 34, fill=color, outline=theme.BORDER, width=2)
            r.text(199, y + 19, str(i + 1), 16, theme.WHITE, "center", True)
            r.text(236, y + 19, entry["name"], 20, theme.INK, "w", True)
            r.text(770, y + 19, f"{entry['score']} capturas", 18, theme.INK, "e", True)
        hint_bar(r, "Esc volver")
