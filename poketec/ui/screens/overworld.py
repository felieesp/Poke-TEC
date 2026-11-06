"""Exploración del mapa, edificios y menú de pausa."""
from typing import Callable, List, Optional, Tuple

from ...engine.save import SaveError
from ...engine.world import DIRECTIONS, TrainerDef
from .. import fx, theme
from ..assets import TILE
from ..renderer import Renderer
from ..widgets import BACK, MenuItem, MenuList, panel
from .base import Screen
from .dialogs import Choice, Dialog, confirm
from .flow import autosave, start_adventure_battle

STEP_TIME = 0.13
AVATAR_COLORS = {"Ash": "#e63946", "Rival": "#3a6ea5"}


class Overworld(Screen):
    background = "#000000"

    def __init__(self, app):
        super().__init__(app)
        self.adv = app.adventure
        self.anim: Optional[Tuple[Tuple[int, int], Tuple[int, int], float]] = None
        self.after: Optional[Callable[[], None]] = None
        self.queued: Optional[str] = None
        self.later: List[List] = []                  # [segundos restantes, función]
        self.banner = ("", 0.0)
        self.alert: Optional[Tuple[Tuple[int, int], float]] = None
        self.flash = 0.0

    # ---- ciclo de vida
    def on_enter(self) -> None:
        self.show_banner()

    def show_banner(self) -> None:
        self.banner = (self.adv.zone.name, 2.2)

    def update(self, dt: float) -> None:
        super().update(dt)
        name, left = self.banner
        if left > 0:
            self.banner = (name, left - dt)
        if self.flash > 0:
            self.flash -= dt
        for item in list(self.later):
            item[0] -= dt
            if item[0] <= 0:
                self.later.remove(item)
                item[1]()
        if self.anim:
            a, b, t = self.anim
            t += dt
            if t >= STEP_TIME:
                self.anim = None
                action, self.after = self.after, None
                if action:
                    action()
                elif self.queued:
                    d, self.queued = self.queued, None
                    self._move(d)
            else:
                self.anim = (a, b, t)

    def _schedule(self, seconds: float, fn: Callable[[], None]) -> None:
        self.later.append([seconds, fn])

    @property
    def busy(self) -> bool:
        return bool(self.anim or self.later or self.alert)

    # ---- movimiento
    def on_key(self, action: str) -> None:
        if action in DIRECTIONS:
            if self.anim:
                self.queued = action
            elif not self.later:
                self._move(action)
        elif action == "confirm" and not self.busy:
            self._interact()
        elif action in ("back", "menu") and not self.busy:
            self.app.push(PauseMenu(self.app, self))

    def _move(self, direction: str) -> None:
        before = self.adv.player.pos
        result = self.adv.step(direction)
        after = self.adv.player.pos
        kind = result.kind
        if kind in ("blocked", "turned"):
            if result.text:
                self.notify(result.text)
            return
        if kind == "locked":
            self.app.push(Dialog(self.app, [result.text]))
            return
        if kind == "warp":
            self.anim = None
            self.show_banner()
            autosave(self.app)
            return
        self.anim = (before, after, 0.0)
        if kind == "building":
            self.after = lambda: self._building(result.building)
        elif kind == "trainer":
            self.after = lambda: self._trainer_sees(result.trainer)
        elif kind == "wild":
            self.after = lambda: self._wild(result.pokemon)

    # ---- encuentros
    def _wild(self, mon) -> None:
        self.flash = 0.45

        def go() -> None:
            battle = self.adv.start_wild_battle(mon)
            start_adventure_battle(self.app, battle, None)
        self._schedule(0.45, go)

    def _trainer_sees(self, trainer: TrainerDef) -> None:
        self.alert = (trainer.pos, 0.7)

        def go() -> None:
            self.alert = None
            self._challenge(trainer)
        self._schedule(0.7, go)

    def _challenge(self, trainer: TrainerDef) -> None:
        ok, text = self.adv.challenge_status(trainer)
        if not ok:
            self.app.push(Dialog(self.app, [text], speaker=trainer.name))
            return

        def begin() -> None:
            try:
                battle = self.adv.start_trainer_battle(trainer)
            except ValueError as err:
                self.app.push(Dialog(self.app, [str(err)]))
                return
            start_adventure_battle(self.app, battle, trainer)
        self.app.push(Dialog(self.app, [text], speaker=trainer.name, on_done=begin))

    # ---- interacción
    def _interact(self) -> None:
        occupant = self.adv.interact()
        if occupant is None:
            tile = self.adv.zone.tile(*self.adv.player.pos)
            if tile in "CMGL":
                self._building(tile)
            return
        if isinstance(occupant, TrainerDef):
            if occupant.id in self.adv.player.defeated:
                self.app.push(Dialog(self.app, [self.adv.trainer_after_text(occupant)], speaker=occupant.name))
            else:
                self._challenge(occupant)
        else:
            self.app.push(Dialog(self.app, self.adv.npc_lines(occupant), speaker=occupant.name))

    def _building(self, tile: str) -> None:
        app, adv = self.app, self.adv
        if tile == "C":
            def picked(i: int) -> None:
                if i == 0:
                    text = adv.heal_at_center()
                    autosave(app)
                    app.push(Dialog(app, ["Dejando a tus Pokémon en la máquina...", text], speaker="Enfermera"))
                elif i == 1:
                    from .party import BoxScreen
                    app.push(BoxScreen(app, adv.player))
            app.push(Choice(app, "Centro Pokémon: ¿en qué puedo ayudarte?",
                            ["Curar a mis Pokémon", "Usar la Caja", "Salir"], picked, width=460))
        elif tile == "M":
            from .bag import ShopScreen
            app.push(Dialog(app, ["¡Bienvenido a la Tienda Poke-TEC!"], speaker="Dependiente",
                            on_done=lambda: app.push(ShopScreen(app))))
        else:
            trainer = adv.building_trainer(tile)
            if trainer is None:
                app.push(Dialog(app, ["Aquí no hay nadie por ahora."]))
            else:
                self._challenge(trainer)

    # ---- dibujo
    def draw(self, r: Renderer) -> None:
        adv, assets, player = self.adv, self.app.assets, self.adv.player
        r.image(assets.zone_map(adv.zone.id), 0, 0)
        actors = []
        for npc in adv.npcs_here():
            actors.append((npc.pos[1], npc.pos, assets.character(npc.color, "down", TILE)))
        for tr in adv.trainers_here():
            actors.append((tr.pos[1], tr.pos, assets.character(tr.color, tr.facing, TILE)))
        px, py = player.pos
        if self.anim:
            (ax, ay), (bx, by), t = self.anim
            q = min(1.0, t / STEP_TIME)
            px, py = ax + (bx - ax) * q, ay + (by - ay) * q
        color = AVATAR_COLORS.get(player.avatar, "#e63946")
        actors.append((py, (px, py), assets.character(color, player.facing, TILE)))
        for _, (x, y), img in sorted(actors, key=lambda a: a[0]):
            r.image(img, x * TILE, y * TILE)
        if self.alert:
            (x, y), _ = self.alert
            r.text(x * TILE + TILE / 2, y * TILE - 6, "!", 40, theme.ACCENT, "s", True)
        self._draw_hud(r)
        if self.flash > 0:
            stripes = int(self.flash * 40)
            for i in range(0, theme.HEIGHT, 40):
                if (i // 40 + stripes) % 2 == 0:
                    r.rect(0, i, theme.WIDTH, i + 40, fill="#ffffff")
        self.draw_toast(r)

    def _draw_hud(self, r: Renderer) -> None:
        p = self.adv.player
        r.rect(0, 576, theme.WIDTH, theme.HEIGHT, fill=theme.NIGHT_2)
        r.text(14, 588, self.adv.zone.name, 14, theme.WHITE, "w", True)
        r.text(250, 588, f"${p.money}", 14, theme.GOLD, "w", True)
        r.text(380, 588, f"Medallas: {len(p.medals)}/3", 14, "#c8d0e8", "w", True)
        r.text(540, 588, f"Equipo: {p.alive_count}/{len(p.team)}", 14, "#c8d0e8", "w", True)
        r.text(theme.WIDTH - 14, 588, "WASD mover · Enter hablar · Esc menú", 12, "#c8d0e8", "e")
        name, left = self.banner
        if left > 0:
            w = r.text_width(name, 24, True) + 60
            panel(r, (theme.WIDTH - w) // 2, 14, w, 46, fill=theme.NIGHT_2, border=theme.GOLD, radius=23)
            r.text(theme.WIDTH // 2, 37, name, 24, theme.WHITE, "center", True)


class PauseMenu(Screen):
    overlay = True

    LABELS = ["Pokémon", "Mochila", "Pokédex", "Misiones", "Carné", "Guardar", "Salir al menú"]

    def __init__(self, app, world: Overworld):
        super().__init__(app)
        self.world = world
        self.menu = MenuList(self.LABELS, row_h=42, gap=6, text_size=19)

    def _pick(self, i: int) -> None:
        app, adv = self.app, self.app.adventure
        from .bag import BagScreen
        from .info import PokedexScreen, QuestsScreen, TrainerCardScreen
        from .party import TeamScreen
        if i == 0:
            app.push(TeamScreen(app, adv.player.team, mode="view", player=adv.player))
        elif i == 1:
            app.push(BagScreen(app, mode="field"))
        elif i == 2:
            app.push(PokedexScreen(app, adv.player))
        elif i == 3:
            app.push(QuestsScreen(app, adv.player))
        elif i == 4:
            app.push(TrainerCardScreen(app, adv.player))
        elif i == 5:
            try:
                app.save_adventure()
                self.world.notify("Partida guardada")
            except (SaveError, OSError) as err:
                app.push(Dialog(app, [f"No se pudo guardar: {err}"]))
                return
            app.pop()
        elif i == 6:
            def leave() -> None:
                from .menu import MainMenu
                app.reset_to(MainMenu(app))
            confirm(app, "¿Volver al menú principal? Se perderá el progreso no guardado.", leave)

    def on_key(self, action: str) -> None:
        if action == "menu":
            action = "back"
        choice = self.menu.handle_key(action)
        if choice == BACK:
            self.app.pop()
        elif choice is not None:
            self._pick(choice)

    def on_click(self, x: int, y: int) -> None:
        choice = self.menu.handle_click(x, y)
        if choice is not None:
            self._pick(choice)
        elif x < 720:
            self.app.pop()

    def on_motion(self, x: int, y: int) -> None:
        self.menu.handle_motion(x, y)

    def draw(self, r: Renderer) -> None:
        panel(r, 730, 20, 214, 20 + len(self.LABELS) * 48 + 20, fill=theme.PAPER)
        self.menu.draw(r, 742, 38, 190)
