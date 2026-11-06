"""Equipo, resumen de Pokémon, aprendizaje de movimientos, evolución y Caja."""
import math
from typing import Callable, List, Optional, Sequence

from ...engine.items import get_item
from ...engine.moves import PHYSICAL, SPECIAL, get_move
from ...engine.player import MAX_TEAM
from ...engine.pokemon import STAT_NAMES_ES, Pokemon
from ...engine.species import get_species
from .. import fx, theme
from ..renderer import Renderer
from ..widgets import (BACK, MenuItem, MenuList, MonPicker, MessageBox, bar, draw_mon_row, draw_types, hint_bar,
                       hp_bar, panel, status_badge, title_bar, type_badge)
from .base import Screen
from .dialogs import Choice, Dialog

STAT_ROWS = (("hp", "PS"), ("atk", "Ataque"), ("def", "Defensa"), ("spa", "At. Esp."), ("spd", "Def. Esp."),
             ("spe", "Velocidad"))


# =================================================================================== resumen
class SummaryScreen(Screen):
    """Ficha completa de un Pokémon. Izquierda/derecha cambia de miembro del equipo."""
    background = theme.NIGHT

    def __init__(self, app, team: Sequence[Pokemon], index: int = 0):
        super().__init__(app)
        self.team = list(team)
        self.index = index

    @property
    def mon(self) -> Pokemon:
        return self.team[self.index]

    def on_key(self, action: str) -> None:
        if action in ("back", "confirm"):
            self.app.pop()
        elif action in ("left", "up") and self.index > 0:
            self.index -= 1
        elif action in ("right", "down") and self.index < len(self.team) - 1:
            self.index += 1

    def on_click(self, x: int, y: int) -> None:
        self.on_key("back")

    def draw(self, r: Renderer) -> None:
        mon = self.mon
        title_bar(r, "Resumen", f"{self.index + 1}/{len(self.team)}")
        # tarjeta izquierda
        panel(r, 24, 84, 300, 470, fill=theme.PANEL)
        r.image(self.app.assets.pokemon(mon.species_id, (230, 230)), 174, 200, "center")
        r.text(174, 330, mon.name, 28, theme.INK, "center", True)
        r.text(174, 362, f"Nivel {mon.level}", 18, theme.INK_SOFT, "center", True)
        w = sum(r.text_width(t.upper(), 12, True) + 22 for t in mon.types)
        draw_types(r, 174 - w // 2, 388, mon.types, 22)
        if mon.status:
            status_badge(r, 150, 424, mon.status)
        r.text(40, 458, f"PS {mon.hp}/{mon.max_hp}", 16, theme.INK, "nw", True)
        hp_bar(r, 40, 482, 268, mon.hp_fraction, 14)
        r.text(40, 506, f"EXP {mon.exp_into_level}/{mon.exp_needed_for_next}", 14, theme.BLUE, "nw", True)
        bar(r, 40, 528, 268, 10, mon.exp_fraction, theme.BLUE)
        # estadísticas
        panel(r, 340, 84, 280, 470, fill=theme.PANEL)
        r.text(360, 100, "Estadísticas", 20, theme.INK, "nw", True)
        top = max(mon.stats.values())
        for i, (key, label) in enumerate(STAT_ROWS):
            y = 148 + i * 58
            value = mon.max_hp if key == "hp" else mon.stats[key]
            r.text(360, y, label, 15, theme.INK_SOFT, "nw", True)
            r.text(600, y, str(value), 16, theme.INK, "ne", True)
            bar(r, 360, y + 24, 240, 10, value / max(1, top), theme.GOLD if key != "hp" else theme.OK)
        species = mon.species
        evo = species.evolution
        if evo:
            target = get_species(evo.to).name
            how = f"Nv{evo.value}" if evo.method == "level" else get_item(evo.value).name
            r.text(360, 500, f"Evoluciona a {target}", 14, theme.INK, "nw", True)
            r.text(360, 520, f"({how})", 13, theme.INK_SOFT, "nw")
        else:
            r.text(360, 505, "Forma final", 14, theme.INK_SOFT, "nw", True)
        # movimientos
        panel(r, 636, 84, 300, 470, fill=theme.PANEL)
        r.text(656, 100, "Movimientos", 20, theme.INK, "nw", True)
        for i, slot in enumerate(mon.moves):
            mv = slot.move
            y = 140 + i * 100
            r.rrect(652, y, 920, y + 88, 10, fill=theme.PAPER, outline=theme.BORDER, width=2)
            r.text(666, y + 8, mv.name, 18, theme.INK, "nw", True)
            type_badge(r, 666, y + 36, mv.type, 18)
            cat = {PHYSICAL: "Físico", SPECIAL: "Especial"}.get(mv.category, "Estado")
            r.text(906, y + 12, cat, 13, theme.INK_SOFT, "ne", True)
            r.text(666, y + 62, f"Poder {mv.power or '—'}  Prec. {mv.accuracy or '—'}", 13, theme.INK_SOFT, "nw", True)
            r.text(906, y + 62, f"PP {slot.pp}/{slot.max_pp}", 14, theme.INK, "ne", True)
        hint_bar(r, "← → cambiar de Pokémon · Esc volver")


# =================================================================================== equipo
class TeamScreen(Screen):
    """Lista del equipo.

    mode:
      view   - desde el menú del mundo: ver resumen y reordenar
      switch - en combate: elegir a quién enviar
      target - elegir sobre quién usar un objeto
    """
    background = theme.NIGHT

    def __init__(self, app, team: List[Pokemon], mode: str = "view", on_pick: Optional[Callable[[int], None]] = None,
                 forced: bool = False, current: Optional[int] = None,
                 enabled: Optional[Callable[[int, Pokemon], bool]] = None, title: str = "Equipo",
                 player=None):
        super().__init__(app)
        self.team = team
        self.mode, self.on_pick, self.forced, self.current, self.title = mode, on_pick, forced, current, title
        self.player = player
        self.moving: Optional[int] = None
        self._enabled = enabled
        self.picker = MonPicker(team, enabled=self._is_enabled, hint=self._hint)

    # ---- reglas
    def _is_enabled(self, i: int, mon: Pokemon) -> bool:
        if self.mode == "switch":
            return not mon.is_fainted and i != self.current
        if self._enabled:
            return self._enabled(i, mon)
        return True

    def _hint(self, i: int, mon: Pokemon) -> str:
        if self.mode == "switch" and i == self.current:
            return "EN COMBATE"
        if self.moving == i:
            return "MOVIENDO"
        return ""

    def _reason(self, mon: Pokemon, i: int) -> str:
        if self.mode == "switch":
            if mon.is_fainted:
                return f"¡{mon.name} está debilitado!"
            if i == self.current:
                return f"¡{mon.name} ya está en combate!"
        return "No tendría ningún efecto."

    # ---- entrada
    def _choose(self, i: int) -> None:
        mon = self.team[i]
        if self.mode in ("switch", "target"):
            self.app.pop()
            if self.on_pick:
                self.on_pick(i)
            return
        # modo ver
        if self.moving is not None:
            a, self.moving = self.moving, None
            if a != i and self.player is not None:
                self.player.swap_team(a, i)
                self.picker.set_team(self.player.team)
            return
        options = ["Resumen", "Mover", "Cancelar"]

        def picked(k: int) -> None:
            if k == 0:
                self.app.push(SummaryScreen(self.app, self.team, i))
            elif k == 1 and len(self.team) > 1:
                self.moving = i

        self.app.push(Choice(self.app, mon.name, options, picked))

    def on_key(self, action: str) -> None:
        result = self.picker.handle_key(action)
        if result is None:
            if action == "menu" and self.team:
                self.app.push(SummaryScreen(self.app, self.team, self.picker.index))
            elif action == "confirm" and self.team:
                self.notify(self._reason(self.team[self.picker.index], self.picker.index))
            return
        if result == BACK:
            if self.moving is not None:
                self.moving = None
            elif self.forced:
                self.notify("Debes elegir un Pokémon para continuar.")
            else:
                self.app.pop()
                if self.on_pick and self.mode != "view":
                    self.on_pick(BACK)
            return
        self._choose(result)

    def on_click(self, x: int, y: int) -> None:
        result = self.picker.handle_click(x, y)
        if result is not None:
            self._choose(result)
        elif self.picker._hit(x, y) is not None:
            i = self.picker.index
            self.notify(self._reason(self.team[i], i))

    def on_motion(self, x: int, y: int) -> None:
        self.picker.handle_motion(x, y)

    # ---- dibujo
    def draw(self, r: Renderer) -> None:
        title_bar(r, self.title, f"{len(self.team)}/{MAX_TEAM}")
        self.picker.draw(r, self.app.assets, 24, 84, 540, row_h=70, gap=8)
        if self.team:
            self._draw_detail(r, self.team[self.picker.index])
        text = "Enter: elegir · M: resumen · Esc: volver"
        if self.moving is not None:
            text = "Elige con quién intercambiar el lugar · Esc: cancelar"
        hint_bar(r, text)
        self.draw_toast(r)

    def _draw_detail(self, r: Renderer, mon: Pokemon) -> None:
        panel(r, 584, 84, 352, 470, fill=theme.PANEL)
        r.image(self.app.assets.pokemon(mon.species_id, (180, 180)), 760, 190, "center")
        r.text(760, 288, mon.name, 24, theme.INK, "center", True)
        w = sum(r.text_width(t.upper(), 12, True) + 22 for t in mon.types)
        draw_types(r, 760 - w // 2, 316, mon.types, 20)
        y = 358
        for key, label in STAT_ROWS[1:]:
            r.text(608, y, label, 14, theme.INK_SOFT, "nw", True)
            r.text(912, y, str(mon.stats[key]), 14, theme.INK, "ne", True)
            bar(r, 700, y + 4, 170, 8, mon.stats[key] / 200, theme.GOLD)
            y += 24
        r.text(608, y + 8, f"EXP {mon.exp_into_level}/{mon.exp_needed_for_next}", 13, theme.BLUE, "nw", True)
        bar(r, 608, y + 28, 304, 8, mon.exp_fraction, theme.BLUE)


# =================================================================================== aprender movimiento
class LearnMoveScreen(Screen):
    """El Pokémon quiere aprender un movimiento y ya conoce cuatro."""
    background = theme.NIGHT

    def __init__(self, app, mon: Pokemon, move_id: str, on_done: Optional[Callable[[], None]] = None):
        super().__init__(app)
        self.mon, self.move_id, self.on_done = mon, move_id, on_done
        items = [MenuItem(s.move.name, badge=f"PP {s.pp}/{s.max_pp}", color=theme.TYPE_COLORS.get(s.move.type))
                 for s in mon.moves]
        items.append(MenuItem("No aprender", color=theme.INK_SOFT))
        self.menu = MenuList(items, row_h=48, gap=8, text_size=20)

    def _finish(self, learned: bool) -> None:
        if not learned:
            self.mon.forget_pending(self.move_id)
        self.app.pop()
        if self.on_done:
            self.on_done()

    def _pick(self, i: int) -> None:
        mv = get_move(self.move_id)
        if i == len(self.mon.moves):
            self._finish(False)
            return
        old = self.mon.moves[i].move.name
        ok = self.mon.learn_move(self.move_id, i)
        self.app.pop()
        lines = [f"{self.mon.name} olvidó {old} y aprendió {mv.name}."] if ok else [f"{self.mon.name} no aprendió {mv.name}."]
        self.app.push(Dialog(self.app, lines, on_done=self.on_done))

    def on_key(self, action: str) -> None:
        choice = self.menu.handle_key(action)
        if choice == BACK:
            self._finish(False)
        elif choice is not None:
            self._pick(choice)

    def on_click(self, x: int, y: int) -> None:
        choice = self.menu.handle_click(x, y)
        if choice is not None:
            self._pick(choice)

    def on_motion(self, x: int, y: int) -> None:
        self.menu.handle_motion(x, y)

    def draw(self, r: Renderer) -> None:
        mv = get_move(self.move_id)
        title_bar(r, "Nuevo movimiento", self.mon.name)
        panel(r, 40, 90, 420, 330, fill=theme.PANEL)
        r.image(self.app.assets.pokemon(self.mon.species_id, (170, 170)), 250, 190, "center")
        r.paragraph(60, 290, f"{self.mon.name} quiere aprender {mv.name}, pero ya conoce cuatro movimientos. "
                             "¿Cuál debe olvidar?", 17, theme.INK, 380, True)
        panel(r, 40, 440, 420, 120, fill=theme.PAPER)
        type_badge(r, 56, 454, mv.type, 20)
        r.text(440, 463, {PHYSICAL: "Físico", SPECIAL: "Especial"}.get(mv.category, "Estado"), 14, theme.INK_SOFT,
               "e", True)
        r.text(56, 486, mv.name, 22, theme.INK, "nw", True)
        r.text(56, 520, f"Poder {mv.power or '—'}   Precisión {mv.accuracy or '—'}   PP {mv.pp}", 15,
               theme.INK_SOFT, "nw", True)
        self.menu.draw(r, 500, 100, 430)
        hint_bar(r, "Elige el movimiento que se olvidará · Esc: no aprender")


# =================================================================================== evolución
class EvolutionScreen(Screen):
    """Animación de evolución. Esc cancela (como en los juegos originales)."""
    background = "#0c1020"
    DURATION = 4.0

    def __init__(self, app, mon: Pokemon, new_species_id: str, apply: Callable[[], None],
                 on_done: Optional[Callable[[], None]] = None):
        super().__init__(app)
        self.mon, self.target, self.apply, self.on_done = mon, new_species_id, apply, on_done
        self.old_species = mon.species_id
        self.old_name = mon.name
        self.done = False
        self.cancelled = False
        self.box = MessageBox()
        self.box.say(f"¿Qué? ¡{self.old_name} está evolucionando!")
        self.applied = False

    def update(self, dt: float) -> None:
        super().update(dt)
        self.box.update(dt)
        if not self.done and self.clock >= self.DURATION:
            self.apply()
            self.applied = True
            self.done = True
            self.box.say(f"¡Felicidades! ¡{self.old_name} evolucionó a {get_species(self.target).name}!")

    def on_key(self, action: str) -> None:
        if self.done:
            if action in ("confirm", "back") and self.box.done:
                self._finish()
            elif action in ("confirm", "back"):
                self.box.skip()
        elif action == "back" and not self.cancelled:
            self.cancelled = True
            self.done = True
            self.box.say(f"¡{self.old_name} dejó de evolucionar!")

    def on_click(self, x: int, y: int) -> None:
        self.on_key("confirm")

    def _finish(self) -> None:
        self.app.pop()
        if self.on_done:
            self.on_done()

    def draw(self, r: Renderer) -> None:
        cx, cy = 480, 240
        t = self.clock
        for k in range(14):                                    # rayos de fondo
            ang = k * math.pi * 2 / 14 + t * 0.6
            r.line([cx, cy, cx + math.cos(ang) * 600, cy + math.sin(ang) * 600], "#1c2a50", 6)
        if self.done:
            species = self.old_species if self.cancelled else self.target
            r.image(self.app.assets.pokemon(species, (260, 260)), cx, cy, "center")
            fx.sparkles(r, cx, cy, (t * 0.8) % 1.0, "#ffe070")
        else:
            p = min(1.0, t / self.DURATION)
            blink = abs(math.sin(t * (2 + p * 14)))              # alterna forma vieja y nueva cada vez más rápido
            species = self.target if (blink > 0.5 and p > 0.25) else self.old_species
            size = int(230 + 50 * math.sin(t * 6) * p)
            r.image(self.app.assets.pokemon(species, (size, size)), cx, cy, "center")
            glow = 80 + 140 * p
            r.oval(cx - glow, cy - glow, cx + glow, cy + glow, outline="#ffffff", width=3)
        self.box.draw(r, 40, 440, 880, 120, 22, prompt=self.done and self.box.done, blink=self.clock)
        if not self.done:
            r.text(480, 580, "Esc: cancelar evolución", 13, "#c8d0e8", "center")


# =================================================================================== Caja
class BoxScreen(Screen):
    """Caja del Centro Pokémon: intercambia Pokémon entre el equipo y la Caja."""
    background = theme.NIGHT

    def __init__(self, app, player):
        super().__init__(app)
        self.player = player
        self.side = 0                                     # 0 = equipo, 1 = caja
        self.team_menu = MenuList([], row_h=44, gap=6, text_size=18, visible_rows=8)
        self.box_menu = MenuList([], row_h=44, gap=6, text_size=18, visible_rows=8)
        self._refresh()

    def _items(self, mons: Sequence[Pokemon]) -> List[MenuItem]:
        return [MenuItem(m.name, badge=f"Nv{m.level}", color="#c06060" if m.is_fainted else None) for m in mons]

    def _refresh(self) -> None:
        self.team_menu.set_items(self._items(self.player.team), keep_index=True)
        self.box_menu.set_items(self._items(self.player.box), keep_index=True)

    @property
    def menu(self) -> MenuList:
        return self.team_menu if self.side == 0 else self.box_menu

    def _act(self) -> None:
        if not self.menu.items:
            return
        i = self.menu.index
        if self.side == 0:
            if not self.player.deposit(i):
                self.notify("Debe quedarte al menos un Pokémon en condiciones de luchar.")
        elif not self.player.withdraw(i):
            self.notify("Tu equipo está completo (6).")
        self._refresh()

    def on_key(self, action: str) -> None:
        if action == "back":
            self.app.pop()
        elif action in ("left", "right"):
            self.side = 0 if action == "left" else 1
        elif action in ("up", "down"):
            self.menu.move(action)
        elif action == "confirm":
            self._act()

    def on_click(self, x: int, y: int) -> None:
        for side, menu in ((0, self.team_menu), (1, self.box_menu)):
            i = menu.hit(x, y)
            if i is not None:
                self.side, menu.index = side, i
                self._act()
                return

    def on_motion(self, x: int, y: int) -> None:
        for side, menu in ((0, self.team_menu), (1, self.box_menu)):
            i = menu.hit(x, y)
            if i is not None:
                self.side, menu.index = side, i

    def draw(self, r: Renderer) -> None:
        title_bar(r, "Caja Pokémon", f"Equipo {len(self.player.team)}/{MAX_TEAM} · Caja {len(self.player.box)}")
        for side, (menu, label, x) in enumerate(((self.team_menu, "Equipo", 30), (self.box_menu, "Caja", 500))):
            panel(r, x - 6, 80, 440, 476, fill=theme.PAPER if side == self.side else "#d8d2b8")
            r.text(x + 8, 94, label, 20, theme.INK, "nw", True)
            if not menu.items:
                r.text(x + 214, 300, "(vacío)", 18, theme.INK_SOFT, "center")
            menu.draw(r, x + 8, 130, 410)
        hint_bar(r, "← → cambiar de lista · Enter: mover entre equipo y Caja · Esc: salir")
        self.draw_toast(r)
