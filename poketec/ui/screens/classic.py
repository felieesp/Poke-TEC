"""Duelo Clásico: el modo original de Poke-TEC (3 contra 3, el ganador captura)."""
from typing import List, Optional

from ...engine.battle import Battle
from ...engine.classic import CLASSIC_LEVEL, CLASSIC_ROSTER, TEAM_SIZE, ClassicDuel
from ...engine.scores import save_score
from ...engine.species import get_species
from .. import theme
from ..renderer import Renderer
from ..widgets import BACK, MonPicker, draw_types, hint_bar, panel, title_bar
from .base import Screen
from .battle import BattleScreen
from .dialogs import Choice, Dialog

COLS = 5
DIFFICULTY_IDS = ("easy", "normal", "hard")


class ClassicSetup(Screen):
    """Nombre -> dificultad -> elegir tres Pokémon."""
    background = theme.NIGHT

    def __init__(self, app):
        super().__init__(app)
        self.stage = "name"
        self.name = ""
        self.difficulty = "normal"
        self.cursor = 0
        self.chosen: List[str] = []
        self.cells: List[tuple] = []

    @property
    def wants_text(self) -> bool:          # type: ignore[override]
        return self.stage == "name"

    # ---- entrada
    def on_text(self, char: str) -> None:
        if self.stage == "name" and char.isprintable() and len(self.name) < 12:
            self.name += char

    def on_key(self, action: str) -> None:
        if self.stage == "name":
            if action == "back":
                self.app.pop()
            elif action == "backspace":
                self.name = self.name[:-1]
            elif action == "confirm":
                self.name = self.name.strip() or "Entrenador"
                self.app.push(Choice(self.app, "Dificultad del rival", ["Fácil", "Normal", "Difícil"], self._set_diff))
            return
        if action == "back":
            self.stage = "name" if not self.chosen else self.stage
            if self.chosen:
                self.chosen.pop()
            return
        total = len(CLASSIC_ROSTER) + 1                    # +1 = botón de comenzar
        if action == "left" and self.cursor % COLS > 0:
            self.cursor -= 1
        elif action == "right" and self.cursor % COLS < COLS - 1 and self.cursor + 1 < total:
            self.cursor += 1
        elif action == "up" and self.cursor - COLS >= 0:
            self.cursor -= COLS
        elif action == "down":
            self.cursor = min(total - 1, self.cursor + COLS)
        elif action == "confirm":
            self._select(self.cursor)

    def _set_diff(self, i: int) -> None:
        if i == BACK:
            return
        self.difficulty = DIFFICULTY_IDS[i]
        self.stage = "pick"

    def _select(self, i: int) -> None:
        if i == len(CLASSIC_ROSTER):
            if len(self.chosen) == TEAM_SIZE:
                self._start()
            else:
                self.notify(f"Elige {TEAM_SIZE} Pokémon para comenzar.")
            return
        sid = CLASSIC_ROSTER[i]
        if sid in self.chosen:
            self.chosen.remove(sid)
        elif len(self.chosen) < TEAM_SIZE:
            self.chosen.append(sid)
        else:
            self.notify(f"Ya elegiste {TEAM_SIZE}. Quita uno para cambiar.")

    def on_click(self, x: int, y: int) -> None:
        for rect, i in self.cells:
            if rect[0] <= x <= rect[2] and rect[1] <= y <= rect[3]:
                self.cursor = i
                self._select(i)
                return

    def on_motion(self, x: int, y: int) -> None:
        for rect, i in self.cells:
            if rect[0] <= x <= rect[2] and rect[1] <= y <= rect[3]:
                self.cursor = i

    def _start(self) -> None:
        duel = ClassicDuel(self.name, list(self.chosen), difficulty=self.difficulty, rng=self.app.rng)
        self.app.replace(ClassicHub(self.app, duel))

    # ---- dibujo
    def draw(self, r: Renderer) -> None:
        title_bar(r, "Duelo Clásico", f"{self.name or '...'}")
        if self.stage == "name":
            panel(r, 180, 160, 600, 260, fill=theme.PANEL)
            r.text(480, 210, "¿Cómo te llamas, entrenador?", 28, theme.INK, "center", True)
            r.rrect(260, 260, 700, 330, 12, fill=theme.WHITE, outline=theme.BORDER, width=3)
            cursor = "▌" if int(self.clock * 2) % 2 == 0 else " "
            r.text(480, 295, self.name + cursor, 34, theme.INK, "center", True)
            hint_bar(r, "Escribe tu nombre · Enter: continuar · Esc: volver")
            return
        r.text(480, 82, f"Elige {TEAM_SIZE} Pokémon ({len(self.chosen)}/{TEAM_SIZE}) — se combate a nivel {CLASSIC_LEVEL}",
               18, theme.WHITE, "center", True)
        self.cells = []
        cw, ch, gap = 172, 108, 10
        x0, y0 = (theme.WIDTH - (COLS * cw + (COLS - 1) * gap)) // 2, 104
        for i in range(len(CLASSIC_ROSTER) + 1):
            x, y = x0 + (i % COLS) * (cw + gap), y0 + (i // COLS) * (ch + gap)
            self.cells.append(((x, y, x + cw, y + ch), i))
            selected = i == self.cursor
            if i == len(CLASSIC_ROSTER):
                ready = len(self.chosen) == TEAM_SIZE
                r.rrect(x, y, x + cw, y + ch, 12, fill=theme.OK if ready else "#6a7080",
                        outline=theme.GOLD if selected else theme.BORDER, width=4 if selected else 3)
                r.text(x + cw / 2, y + ch / 2, "¡COMENZAR!", 20, theme.WHITE, "center", True)
                continue
            sid = CLASSIC_ROSTER[i]
            sp = get_species(sid)
            on = sid in self.chosen
            r.rrect(x, y, x + cw, y + ch, 12, fill="#fff4d6" if on else theme.PANEL,
                    outline=theme.ACCENT if selected else theme.OK if on else theme.BORDER,
                    width=4 if selected or on else 3)
            r.image(self.app.assets.icon(sid, 64), x + 40, y + ch / 2, "center")
            r.text(x + 78, y + 22, sp.name, 15, theme.INK, "nw", True)
            draw_types(r, x + 78, y + 50, sp.types, 15)
            if on:
                r.oval(x + cw - 28, y + 6, x + cw - 6, y + 28, fill=theme.OK, outline=theme.BORDER, width=2)
                r.text(x + cw - 17, y + 17, str(self.chosen.index(sid) + 1), 14, theme.WHITE, "center", True)
        hint_bar(r, "Flechas: mover · Enter: elegir/quitar · Esc: quitar último")
        self.draw_toast(r)


class ClassicHub(Screen):
    """Entre rondas: elige con qué Pokémon luchar."""
    background = theme.NIGHT

    def __init__(self, app, duel: ClassicDuel):
        super().__init__(app)
        self.duel = duel
        self.picker = MonPicker(duel.player_team)

    def on_resume(self, result=None) -> None:
        self.picker.set_team(self.duel.player_team)

    def _fight(self, index: int) -> None:
        duel = self.duel
        battle = duel.start_round(index)
        self.app.push(BattleScreen(self.app, battle, theme_id="classic", foe_avatar="Rival",
                                   player_avatar="Ash", allow_bag=False,
                                   on_done=lambda b: self._after_round(b)))

    def _after_round(self, battle: Battle) -> None:
        duel = self.duel
        mine, theirs = battle.player_team[0], battle.foe_team[0]
        outcome = duel.finish_round(battle)
        self.picker.set_team(duel.player_team)
        if outcome == "captured":
            lines = [f"¡Venciste a {theirs.name} y lo capturaste!"]
        elif outcome == "lost":
            lines = [f"{mine.name} cayó... ¡el rival se queda con él!"]
        else:
            lines = ["El combate terminó sin ganador."]
        if duel.is_over:
            self.app.push(Dialog(self.app, lines, on_done=self._finish_duel))
        else:
            self.app.push(Dialog(self.app, lines))

    def _finish_duel(self) -> None:
        duel = self.duel
        position = save_score(duel.player_name, duel.score)
        self.app.replace(ClassicResult(self.app, duel, position))

    def on_key(self, action: str) -> None:
        choice = self.picker.handle_key(action)
        if choice == BACK:
            from .dialogs import confirm
            confirm(self.app, "¿Abandonar el duelo? No se guardará el puntaje.", lambda: self.app.pop())
        elif choice is not None:
            self._fight(choice)

    def on_click(self, x: int, y: int) -> None:
        choice = self.picker.handle_click(x, y)
        if choice is not None:
            self._fight(choice)

    def on_motion(self, x: int, y: int) -> None:
        self.picker.handle_motion(x, y)

    def draw(self, r: Renderer) -> None:
        d = self.duel
        title_bar(r, "Duelo Clásico", f"Capturas: {d.score} · Ronda {d.rounds + 1}")
        r.text(30, 86, "Tu equipo — elige con quién luchar", 18, theme.WHITE, "nw", True)
        self.picker.draw(r, self.app.assets, 30, 116, 520, row_h=66, gap=8)
        r.text(590, 86, "Equipo rival", 18, theme.WHITE, "nw", True)
        panel(r, 580, 116, 350, 440, fill=theme.PAPER)
        for i, mon in enumerate(d.enemy_team):
            y = 132 + i * 82
            r.image(self.app.assets.icon(mon.species_id, 64), 624, y + 34, "center")
            r.text(668, y + 16, mon.name, 20, theme.INK, "nw", True)
            draw_types(r, 668, y + 44, mon.types, 16)
        r.text(755, 520, "El rival elige al azar", 14, theme.INK_SOFT, "center")
        hint_bar(r, "Enter: luchar · Esc: abandonar")


class ClassicResult(Screen):
    background = theme.NIGHT

    def __init__(self, app, duel: ClassicDuel, position: int):
        super().__init__(app)
        self.duel, self.position = duel, position

    def on_key(self, action: str) -> None:
        if action in ("confirm", "back"):
            from .menu import MainMenu
            self.app.reset_to(MainMenu(self.app))

    def on_click(self, x: int, y: int) -> None:
        self.on_key("confirm")

    def draw(self, r: Renderer) -> None:
        d = self.duel
        title_bar(r, "Duelo terminado", d.player_name)
        panel(r, 200, 130, 560, 330, fill=theme.PANEL)
        win = d.player_won
        r.text(480, 190, "¡VICTORIA!" if win else "Derrota", 48, theme.OK if win else theme.DANGER, "center", True)
        r.text(480, 270, f"Capturas: {d.score}", 30, theme.INK, "center", True)
        r.text(480, 320, f"Rondas jugadas: {d.rounds}", 18, theme.INK_SOFT, "center", True)
        msg = f"¡Entraste al Top 10 en el puesto {self.position}!" if self.position else "No entraste al Top 10."
        r.text(480, 380, msg, 20, theme.GOLD if self.position else theme.INK_SOFT, "center", True)
        hint_bar(r, "Enter: volver al menú")
