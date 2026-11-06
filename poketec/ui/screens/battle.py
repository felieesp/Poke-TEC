"""Pantalla de combate.

El motor (`engine.battle.Battle`) resuelve cada turno al instante y devuelve una lista de
eventos. Esta pantalla los *reproduce* uno a uno con animaciones (movimientos, barras de
vida que bajan poco a poco, experiencia, captura...). Mientras se reproducen, la interfaz
muestra los datos de cada evento y no el estado final del motor, así todo se ve en orden.
"""
import math
from collections import deque
from typing import Callable, Deque, Dict, List, Optional, Set

from ...engine.battle import FOE, PLAYER, Action, Battle, Event
from ...engine.elements import TYPE_NAMES_ES
from ...engine.moves import PHYSICAL, SPECIAL
from ...engine.pokemon import STAT_NAMES_ES
from .. import fx, theme
from ..renderer import Renderer
from ..widgets import BACK, MenuItem, MenuList, MessageBox, bar, hp_bar, hp_color, panel, status_badge, type_badge
from .base import Screen

FOE_BOTTOM = (690, 232)           # (x central, y de los pies)
PLAYER_BOTTOM = (235, 392)
FOE_BOX = (30, 26, 350, 92)
PLAYER_BOX = (580, 262, 350, 112)
PANEL_TOP = 424
MSG_PAUSE = 0.55


class SideView:
    """Lo que se ve de un lado del combate en este instante."""

    def __init__(self) -> None:
        self.species_id: Optional[str] = None
        self.name = ""
        self.level = 1
        self.hp = 0.0
        self.max_hp = 1
        self.status: Optional[str] = None
        self.exp = 0.0
        self.shown = False          # ¿se ve el Pokémon?
        self.trainer = True         # ¿se ve el entrenador (antes de enviar al primero)?
        self.offset = (0.0, 0.0)
        self.flash = 0.0
        self.types: tuple = ()


class Step:
    """Un evento en reproducción."""

    def __init__(self, event: Event, duration: float):
        self.event = event
        self.kind = event.kind
        self.duration = duration
        self.t = 0.0

    @property
    def p(self) -> float:
        return min(1.0, self.t / self.duration) if self.duration > 0 else 1.0


class BattleScreen(Screen):
    def __init__(self, app, battle: Battle, *, theme_id: str = "route", foe_avatar: Optional[str] = None,
                 foe_color: str = "#c0392b", player_avatar: str = "Ash", allow_bag: bool = True,
                 on_done: Optional[Callable[[Battle], None]] = None):
        super().__init__(app)
        self.b = battle
        self.theme_id = theme_id
        self.foe_avatar, self.foe_color, self.player_avatar = foe_avatar, foe_color, player_avatar
        self.allow_bag = allow_bag and battle.bag is not None
        self.on_done = on_done
        self.view: Dict[str, SideView] = {PLAYER: SideView(), FOE: SideView()}
        self.queue: Deque[Event] = deque()
        self.step: Optional[Step] = None
        self.phase = "playing"                 # playing | menu | moves | ended
        self.msg = MessageBox()
        self.menu = MenuList([], cols=2, row_h=48, gap=10, text_size=21)
        self.moves = MenuList([], cols=2, row_h=54, gap=10, text_size=19)
        self.down: Dict[str, Set[int]] = {
            side: {id(m) for m in battle.team(side) if m.is_fainted} for side in (PLAYER, FOE)}
        self.end_timer = 0.0
        self.finished = False
        self.picking = False                   # hay una pantalla emergente abierta
        self.last_message = ""
        self._turn_hint = ""

    # =============================================================================== ciclo de vida
    def on_enter(self) -> None:
        self.queue.extend(self.b.start())

    def on_resume(self, result=None) -> None:
        self.picking = False

    # =============================================================================== reproducción
    def _duration(self, e: Event) -> float:
        k = e.kind
        if k == "msg":
            return len(e["text"]) / MessageBox.SPEED + MSG_PAUSE
        return {"send_out": 0.55, "switch_out": 0.3, "move": 0.8, "miss": 0.35, "status": 0.45,
                "stat": 0.8, "faint": 0.75}.get(k) or self._custom_duration(e)

    def _custom_duration(self, e: Event) -> float:
        k = e.kind
        if k == "damage":
            frac = e["amount"] / max(1, e["max_hp"])
            return 0.45 + 0.9 * frac
        if k == "heal":
            return 0.5 + 0.7 * e["amount"] / max(1, e["max_hp"])
        if k == "exp":
            return 0.35 + 0.7 * len(e["segments"]) if e["is_active"] else 0.0
        if k == "level_up":
            return 0.9 if e.get("is_active") else 0.0
        if k == "ball":
            return 0.9 + 0.75 * e["shakes"] + 0.8
        return 0.0

    def _begin(self, e: Event) -> None:
        self.step = Step(e, self._duration(e))
        k = e.kind
        if k == "msg":
            self.msg.say(e["text"])
            self.last_message = e["text"]
        elif k == "send_out":
            v = self.view[e["side"]]
            mon = e["mon"]
            v.species_id, v.name, v.level = mon.species_id, mon.name, e["level"]
            v.hp, v.max_hp, v.status, v.types = float(e["hp"]), e["max_hp"], e["status"], mon.types
            if e["side"] == PLAYER:
                v.exp = mon.exp_fraction
            v.shown, v.trainer, v.offset = True, False, (0.0, 0.0)
        elif k == "switch_out":
            pass
        elif k == "status":
            self.view[e["side"]].status = e["status"]
        elif k == "ball":
            self.view[FOE].shown = True

    def _tick_step(self, dt: float) -> None:
        s = self.step
        s.t += dt
        e, p = s.event, s.p
        k = s.kind
        if k == "damage":
            v = self.view[e["side"]]
            v.hp = e["hp_before"] + (e["hp"] - e["hp_before"]) * fx.ease_out(p)
            if e.get("source") == "move" and e["amount"] > 0:
                v.offset = (math.sin(s.t * 55) * 9 * (1 - p), 0.0)
                v.flash = 1 - p
        elif k == "heal":
            v = self.view[e["side"]]
            if e.get("is_active", True):
                v.hp = e["hp_before"] + (e["hp"] - e["hp_before"]) * fx.ease_out(p)
        elif k == "move":
            v = self.view[e["side"]]
            toward = (1.0, -0.35) if e["side"] == PLAYER else (-1.0, 0.35)
            v.offset = fx.lunge_offset(p, toward) if e["category"] == PHYSICAL else (0.0, 0.0)
        elif k == "miss":
            v = self.view[FOE if e["side"] == PLAYER else PLAYER]
            v.offset = (math.sin(p * math.pi) * (30 if e["side"] == PLAYER else -30), 0.0)
        elif k == "switch_out":
            self.view[e["side"]].offset = (0.0, p * 60)
        elif k == "faint":
            self.view[e["side"]].offset = (0.0, fx.ease_in_out(p) * 90)
        elif k == "send_out":
            self.view[e["side"]].offset = (0.0, (1 - fx.ease_out(p)) * 70)
        elif k == "exp" and e["is_active"]:
            segs = e["segments"]
            per = s.duration / (len(segs) + 0.5)
            i = min(len(segs) - 1, int(s.t / per))
            local = min(1.0, (s.t - i * per) / per)
            _, start, end = segs[i]
            self.view[PLAYER].exp = start + (end - start) * fx.ease_out(local)
        elif k == "ball":
            self.view[FOE].shown = s.t < 0.55 or (not e["caught"] and s.t > s.duration - 0.45)
            if not e["caught"] and s.t > s.duration - 0.45:
                self.view[FOE].offset = (0.0, (1 - (s.t - (s.duration - 0.45)) / 0.45) * 30)
        for v in self.view.values():
            v.flash = max(0.0, v.flash - dt * 2)
        if s.t >= s.duration:
            self._end_step()

    def _end_step(self) -> None:
        s = self.step
        e, k = s.event, s.kind
        self.step = None
        if k == "damage":
            v = self.view[e["side"]]
            v.hp, v.offset = float(e["hp"]), (0.0, 0.0)
        elif k == "heal":
            v = self.view[e["side"]]
            if e.get("is_active", True):
                v.hp = float(e["hp"])
        elif k == "move" or k == "miss":
            for v in self.view.values():
                v.offset = (0.0, 0.0)
        elif k == "switch_out":
            v = self.view[e["side"]]
            v.shown, v.offset = False, (0.0, 0.0)
        elif k == "faint":
            v = self.view[e["side"]]
            v.shown, v.offset = False, (0.0, 0.0)
            self.down[e["side"]].add(id(e["mon"]))
        elif k == "send_out":
            self.view[e["side"]].offset = (0.0, 0.0)
        elif k == "exp" and e["is_active"]:
            self.view[PLAYER].exp = e["segments"][-1][2]
        elif k == "level_up" and e.get("is_active"):
            v = self.view[PLAYER]
            v.level, v.hp, v.max_hp = e["level"], float(e["hp"]), e["max_hp"]
            v.exp = 0.0
        elif k == "ball":
            self.view[FOE].shown = not e["caught"]
            self.view[FOE].offset = (0.0, 0.0)

    def _queue_empty(self) -> bool:
        return self.step is None and not self.queue

    def _after_events(self) -> None:
        """La cola se vació: ¿terminó el combate, hay que elegir relevo o toca el menú?"""
        b = self.b
        if b.is_over:
            self.phase, self.end_timer = "ended", 0.5
        elif b.state == "need_switch":
            self.phase = "playing"
            self._open_team(forced=True)
        else:
            self._open_main_menu()

    # =============================================================================== menús
    def _open_main_menu(self) -> None:
        self.phase = "menu"
        wild = self.b.kind == "wild"
        self.menu.set_items([
            MenuItem("Luchar"),
            MenuItem("Mochila", enabled=self.allow_bag),
            MenuItem("Pokémon", enabled=len(self.b.available_switches()) > 0),
            MenuItem("Huir" if wild else "—", enabled=wild),
        ])
        self.msg.say(f"¿Qué hará {self.b.player.name}?")

    def _open_moves(self) -> None:
        mon = self.b.player
        if self.b.must_struggle():
            self._submit(Action.fight(-1))
            return
        items = []
        for slot in mon.moves:
            mv = slot.move
            items.append(MenuItem(mv.name, enabled=slot.pp > 0, badge=f"{slot.pp}/{slot.max_pp}",
                                  color=theme.TYPE_COLORS.get(mv.type)))
        self.moves.set_items(items)
        self.phase = "moves"

    def _open_team(self, forced: bool = False) -> None:
        from .party import TeamScreen
        b = self.b
        current = b.player_index

        def picked(i: int) -> None:
            if i == BACK:
                return
            self._submit(Action.switch(i))

        self.picking = True
        self.app.push(TeamScreen(
            self.app, b.player_team, mode="switch", on_pick=picked, forced=forced, current=current,
            title="¿A quién enviar?" if not forced else "Elige al siguiente Pokémon"))

    def _open_bag(self) -> None:
        from .bag import BagScreen
        self.picking = True
        self.app.push(BagScreen(self.app, mode="battle", battle=self.b, on_pick=self._submit_from_bag))

    def _submit_from_bag(self, action: Optional[Action]) -> None:
        if action is not None:
            self._submit(action)

    def _submit(self, action: Action) -> None:
        self.picking = False
        events = self.b.submit(action)
        self.queue.extend(events)
        self.phase = "playing"

    def _choose_main(self, index: int) -> None:
        if index == 0:
            self._open_moves()
        elif index == 1:
            self._open_bag()
        elif index == 2:
            self._open_team()
        elif index == 3:
            self._submit(Action.run())

    # =============================================================================== bucle
    def update(self, dt: float) -> None:
        super().update(dt)
        self.msg.update(dt)
        if self.phase == "playing" and not self.picking:
            if self.step is None and self.queue:
                self._begin(self.queue.popleft())
            if self.step is not None:
                self._tick_step(dt)
            if self._queue_empty() and self.phase == "playing" and not self.picking:
                self._after_events()
        elif self.phase == "ended":
            if self.step is None and self.queue:
                self.phase = "playing"
                return
            self.end_timer -= dt
            if self.end_timer <= 0 and not self.finished:
                self._finish()

    def _finish(self) -> None:
        self.finished = True
        self.app.pop()
        if self.on_done:
            self.on_done(self.b)

    # =============================================================================== entrada
    def on_key(self, action: str) -> None:
        if self.phase == "playing" and self.step is not None and action in ("confirm", "back"):
            if self.step.kind == "msg":
                if not self.msg.done:
                    self.msg.skip()
                else:
                    self.step.t = self.step.duration        # saltar la pausa
            return
        if self.phase == "menu":
            choice = self.menu.handle_key(action)
            if choice is not None and choice != BACK:
                self._choose_main(choice)
        elif self.phase == "moves":
            choice = self.moves.handle_key(action)
            if choice == BACK:
                self._open_main_menu()
            elif choice is not None:
                self._submit(Action.fight(choice))

    def on_click(self, x: int, y: int) -> None:
        if self.phase == "menu":
            choice = self.menu.handle_click(x, y)
            if choice is not None:
                self._choose_main(choice)
        elif self.phase == "moves":
            choice = self.moves.handle_click(x, y)
            if choice is not None:
                self._submit(Action.fight(choice))
            elif x > 640 and y > PANEL_TOP:
                self._open_main_menu()
        else:
            self.on_key("confirm")

    def on_motion(self, x: int, y: int) -> None:
        if self.phase == "menu":
            self.menu.handle_motion(x, y)
        elif self.phase == "moves":
            self.moves.handle_motion(x, y)

    # =============================================================================== dibujo
    def draw(self, r: Renderer) -> None:
        assets = self.app.assets
        r.image(assets.battle_backdrop(self.theme_id), 0, 0)
        self._draw_actor(r, FOE)
        self._draw_actor(r, PLAYER)
        self._draw_step_fx(r)
        self._draw_foe_box(r)
        self._draw_player_box(r)
        self._draw_bottom(r)
        self.draw_toast(r)

    def _draw_actor(self, r: Renderer, side: str) -> None:
        v = self.view[side]
        assets = self.app.assets
        bx, by = FOE_BOTTOM if side == FOE else PLAYER_BOTTOM
        if v.trainer:
            if side == FOE:
                img = assets.trainer(self.foe_avatar, (170, 210)) if self.foe_avatar else \
                    assets.character(self.foe_color, "down", 200)
            else:
                img = assets.trainer(self.player_avatar, (190, 240))
            if self.b.kind == "wild" and side == FOE:
                return
            r.image(img, bx, by + 6, "s")
            return
        if not v.shown or not v.species_id:
            return
        size = (200, 200) if side == FOE else (240, 240)
        img = assets.pokemon(v.species_id, size)
        ox, oy = v.offset
        r.oval(bx - 70 + ox * 0.2, by - 12, bx + 70 + ox * 0.2, by + 8, fill="#00000030")
        r.image(img, bx + ox, by + oy, "s")
        if v.flash > 0.35:
            r.oval(bx - 60 + ox, by - size[1] * 0.6 + oy, bx + 60 + ox, by - size[1] * 0.2 + oy,
                   outline="#ffffff", width=3)

    def _center(self, side: str):
        bx, by = FOE_BOTTOM if side == FOE else PLAYER_BOTTOM
        return bx, by - (100 if side == FOE else 120)

    def _draw_step_fx(self, r: Renderer) -> None:
        s = self.step
        if s is None:
            return
        e, p = s.event, s.p
        if s.kind == "move":
            src, dst = self._center(e["side"]), self._center(FOE if e["side"] == PLAYER else PLAYER)
            fx.attack(r, e["move_type"], e["category"], p, src, dst)
        elif s.kind == "stat":
            x, y = self._center(e["side"])
            fx.stat_arrows(r, x, y, p, e["change"] > 0)
        elif s.kind == "heal":
            x, y = self._center(e["side"])
            fx.sparkles(r, x, y, p)
        elif s.kind == "status" and e["status"]:
            x, y = self._center(e["side"])
            fx.impact(r, x, y, p, theme.STATUS_COLORS.get(e["status"], "#ffffff"), 60)
        elif s.kind == "level_up" and e.get("is_active"):
            x, y = self._center(PLAYER)
            fx.sparkles(r, x, y, p, "#ffe070")
        elif s.kind == "send_out":
            x, y = self._center(e["side"])
            fx.sparkles(r, x, y, p, "#ffffff")
        elif s.kind == "ball":
            self._draw_ball(r, s)

    def _draw_ball(self, r: Renderer, s: Step) -> None:
        e, t = s.event, s.t
        sx, sy = self._center(PLAYER)
        fx_x, fx_y = self._center(FOE)
        rest = (fx_x, FOE_BOTTOM[1] - 14)
        throw = 0.7
        if t < throw:
            q = t / throw
            x = sx + (fx_x - sx) * q
            y = sy + (fx_y - sy) * q - math.sin(q * math.pi) * 90
            fx.ball(r, x, y, e["ball_id"], tilt=q * 9)
            return
        drop = min(1.0, (t - throw) / 0.3)
        y = fx_y + (rest[1] - fx_y) * drop
        tilt = 0.0
        shake_t = t - throw - 0.3
        total_shake = 0.75 * e["shakes"]
        if shake_t > 0 and shake_t < total_shake:
            phase = (shake_t % 0.75) / 0.75
            tilt = math.sin(phase * math.pi * 2) * 0.5
        if e["caught"] and shake_t > total_shake:
            fx.sparkles(r, rest[0], rest[1] - 10, min(1.0, (shake_t - total_shake) / 0.7), "#ffe070")
        if not e["caught"] and t > s.duration - 0.45:
            return
        fx.ball(r, rest[0], y, e["ball_id"], tilt=tilt)

    # ---- cajas de estado
    def _team_balls(self, r: Renderer, side: str, x: int, y: int, align_right: bool = False) -> None:
        team = self.b.team(side)
        for i, mon in enumerate(team):
            cx = (x - i * 20) if align_right else (x + i * 20)
            gone = id(mon) in self.down[side]
            r.oval(cx - 7, y - 7, cx + 7, y + 7, fill="#9aa0aa" if gone else theme.ACCENT,
                   outline=theme.BORDER, width=2)
            if not gone:
                r.line([cx - 7, y, cx + 7, y], theme.BORDER, 2)

    def _draw_foe_box(self, r: Renderer) -> None:
        v = self.view[FOE]
        x, y, w, h = FOE_BOX
        if not v.species_id or v.trainer:
            if self.b.kind == "trainer" and self.b.foe_name:
                r.text(x, y, self.b.foe_name, 18, theme.WHITE, "nw", True)
                self._team_balls(r, FOE, x + 10, y + 36)
            return
        panel(r, x, y, w, h, fill=theme.PANEL)
        r.text(x + 16, y + 10, v.name, 22, theme.INK, "nw", True)
        r.text(x + w - 16, y + 14, f"Nv{v.level}", 18, theme.INK_SOFT, "ne", True)
        cx = x + 16
        for t in v.types:
            cx += type_badge(r, cx, y + 40, t, 16) + 4
        status_badge(r, x + w - 56, y + 40, v.status)
        r.text(x + 16, y + 68, "PS", 13, theme.INK_SOFT, "w", True)
        hp_bar(r, x + 42, y + 62, w - 62, v.hp / max(1, v.max_hp), 12)
        if self.b.kind == "trainer":
            self._team_balls(r, FOE, x + 14, y + h + 16)

    def _draw_player_box(self, r: Renderer) -> None:
        v = self.view[PLAYER]
        x, y, w, h = PLAYER_BOX
        if not v.species_id or v.trainer:
            return
        panel(r, x, y, w, h, fill=theme.PANEL)
        r.text(x + 16, y + 8, v.name, 22, theme.INK, "nw", True)
        r.text(x + w - 16, y + 12, f"Nv{v.level}", 18, theme.INK_SOFT, "ne", True)
        status_badge(r, x + 16, y + 38, v.status)
        r.text(x + 16, y + 58, "PS", 13, theme.INK_SOFT, "w", True)
        hp_bar(r, x + 42, y + 52, w - 62, v.hp / max(1, v.max_hp), 12)
        r.text(x + w - 16, y + 68, f"{int(round(v.hp))}/{v.max_hp}", 16, theme.INK, "ne", True)
        r.text(x + 16, y + 94, "EXP", 12, theme.BLUE, "w", True)
        bar(r, x + 52, y + 89, w - 72, 9, v.exp, theme.BLUE)
        self._team_balls(r, PLAYER, x + w - 16, y + h + 16, align_right=True)

    # ---- panel inferior
    def _draw_bottom(self, r: Renderer) -> None:
        r.rect(0, PANEL_TOP, theme.WIDTH, theme.HEIGHT, fill=theme.NIGHT_2)
        r.rect(0, PANEL_TOP, theme.WIDTH, PANEL_TOP + 4, fill=theme.ACCENT)
        if self.phase == "moves":
            self._draw_moves(r)
            return
        self.msg.draw(r, 24, PANEL_TOP + 18, 560 if self.phase == "menu" else 912, 140, 22,
                      prompt=self.phase == "playing" and self.msg.done, blink=self.clock)
        if self.phase == "menu":
            panel(r, 604, PANEL_TOP + 18, 332, 140, fill=theme.PAPER, radius=14)
            self.menu.draw(r, 620, PANEL_TOP + 32, 300)

    def _draw_moves(self, r: Renderer) -> None:
        panel(r, 24, PANEL_TOP + 14, 600, 150, fill=theme.PAPER, radius=14)
        self.moves.draw(r, 40, PANEL_TOP + 26, 568)
        panel(r, 640, PANEL_TOP + 14, 296, 150, fill=theme.PANEL, radius=14)
        if not self.moves.items:
            return
        slot = self.b.player.moves[self.moves.index]
        mv = slot.move
        type_badge(r, 658, PANEL_TOP + 26, mv.type, 22)
        cat = {PHYSICAL: "Físico", SPECIAL: "Especial"}.get(mv.category, "Estado")
        r.text(920, PANEL_TOP + 37, cat, 16, theme.INK_SOFT, "e", True)
        r.text(658, PANEL_TOP + 66, f"Poder: {mv.power if mv.power else '—'}", 17, theme.INK, "nw", True)
        r.text(658, PANEL_TOP + 90, f"Precisión: {mv.accuracy if mv.accuracy else '—'}", 17, theme.INK, "nw", True)
        r.text(658, PANEL_TOP + 114, f"PP: {slot.pp}/{slot.max_pp}", 17,
               theme.DANGER if slot.pp == 0 else theme.INK, "nw", True)
        r.text(920, PANEL_TOP + 148, "Esc: volver", 12, theme.INK_SOFT, "se")
