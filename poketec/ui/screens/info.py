"""Pantallas informativas: Pokédex, misiones y carné de entrenador."""
from ...engine.items import get_item
from ...engine.player import MEDALS
from ...engine.quests import QUESTS
from ...engine.species import SPECIES, get_species
from .. import theme
from ..renderer import Renderer
from ..widgets import BACK, MenuItem, MenuList, bar, draw_types, hint_bar, panel, title_bar
from .base import Screen

MEDAL_COLORS = {"roca": "#a0845c", "cascada": "#4a8ae8", "ceniza": "#e06030"}
STAT_LABELS = (("hp", "PS"), ("atk", "Ataque"), ("def", "Defensa"), ("spa", "At. Esp."), ("spd", "Def. Esp."),
               ("spe", "Velocidad"))


def draw_medal(r: Renderer, x: float, y: float, medal_id: str, have: bool, size: float = 34) -> None:
    color = MEDAL_COLORS.get(medal_id, "#c0a040") if have else "#6a7080"
    r.oval(x - size, y - size, x + size, y + size, fill=color, outline=theme.BORDER, width=4)
    r.oval(x - size * 0.7, y - size * 0.7, x + size * 0.7, y + size * 0.7, outline="#ffffff80" if have else "#808590", width=2)
    r.text(x, y, "★" if have else "?", int(size * 0.9), theme.WHITE, "center", True)


class _ListScreen(Screen):
    """Lista a la izquierda y detalle a la derecha."""
    background = theme.NIGHT
    title = ""

    def __init__(self, app):
        super().__init__(app)
        self.menu = MenuList([], row_h=44, gap=6, text_size=18, visible_rows=9)

    def on_key(self, action: str) -> None:
        if action == "back":
            self.app.pop()
        elif action in ("up", "down"):
            self.menu.move(action)

    def on_click(self, x: int, y: int) -> None:
        self.menu.handle_click(x, y)

    def on_motion(self, x: int, y: int) -> None:
        self.menu.handle_motion(x, y)


class PokedexScreen(_ListScreen):
    def __init__(self, app, player):
        super().__init__(app)
        self.player = player
        self.ids = list(SPECIES)
        items = []
        for n, sid in enumerate(self.ids, 1):
            caught, seen = sid in player.caught, sid in player.seen
            name = get_species(sid).name if seen else "???"
            items.append(MenuItem(f"{n:02d}  {name}", badge="●" if caught else "○" if seen else ""))
        self.menu.set_items(items)

    def draw(self, r: Renderer) -> None:
        p = self.player
        title_bar(r, "Pokédex", f"Vistos {len(p.seen)} · Capturados {len(p.caught)} / {len(self.ids)}")
        panel(r, 24, 80, 380, 480, fill=theme.PAPER)
        self.menu.draw(r, 38, 98, 352)
        panel(r, 424, 80, 512, 480, fill=theme.PANEL)
        sid = self.ids[self.menu.index]
        if sid not in p.seen:
            r.text(680, 290, "Aún no has visto", 22, theme.INK_SOFT, "center", True)
            r.text(680, 322, "este Pokémon", 22, theme.INK_SOFT, "center", True)
        else:
            sp = get_species(sid)
            r.image(self.app.assets.pokemon(sid, (200, 200)), 560, 200, "center")
            r.text(700, 120, sp.name, 28, theme.INK, "nw", True)
            draw_types(r, 700, 164, sp.types, 22)
            r.text(700, 200, "Capturado" if sid in p.caught else "Solo visto", 16,
                   theme.OK if sid in p.caught else theme.WARN, "nw", True)
            if sp.evolution:
                how = f"Nv{sp.evolution.value}" if sp.evolution.method == "level" else get_item(sp.evolution.value).name
                r.text(700, 232, f"Evoluciona a {get_species(sp.evolution.to).name}", 14, theme.INK, "nw", True)
                r.text(700, 252, f"({how})", 13, theme.INK_SOFT, "nw")
            else:
                r.text(700, 232, "Forma final", 14, theme.INK_SOFT, "nw", True)
            for i, (key, label) in enumerate(STAT_LABELS):
                y = 330 + i * 36
                r.text(450, y, label, 15, theme.INK_SOFT, "nw", True)
                r.text(560, y, str(sp.base[key]), 15, theme.INK, "nw", True)
                bar(r, 610, y + 4, 300, 10, sp.base[key] / 150, theme.GOLD)
        hint_bar(r, "↑ ↓ navegar · Esc volver")


class QuestsScreen(_ListScreen):
    def __init__(self, app, player):
        super().__init__(app)
        self.player = player
        self.menu.visible_rows = 8
        self.menu.row_h = 50
        self.menu.set_items([MenuItem(q.title, badge="✔" if q.id in player.completed_quests else
                                      "{}/{}".format(*q.progress(player))) for q in QUESTS])

    def draw(self, r: Renderer) -> None:
        p = self.player
        done = len(p.completed_quests)
        title_bar(r, "Misiones", f"{done}/{len(QUESTS)} completadas")
        panel(r, 24, 80, 420, 480, fill=theme.PAPER)
        self.menu.draw(r, 38, 98, 392)
        panel(r, 464, 80, 472, 480, fill=theme.PANEL)
        q = QUESTS[self.menu.index]
        cur, target = q.progress(p)
        complete = q.id in p.completed_quests
        r.text(490, 104, q.title, 26, theme.INK, "nw", True)
        r.paragraph(490, 150, q.description, 18, theme.INK, 420, True)
        bar(r, 490, 230, 420, 18, cur / max(1, target), theme.OK if complete else theme.BLUE)
        r.text(700, 270, f"{cur} / {target}", 16, theme.INK_SOFT, "center", True)
        r.text(490, 320, "Recompensa", 18, theme.INK, "nw", True)
        rewards = ([f"${q.money}"] if q.money else []) + [f"{n} × {get_item(i).name}" for i, n in q.items.items()]
        for i, line in enumerate(rewards):
            r.text(510, 354 + i * 28, "• " + line, 17, theme.INK, "nw", True)
        if complete:
            r.text(700, 500, "¡COMPLETADA!", 26, theme.OK, "center", True)
        hint_bar(r, "↑ ↓ navegar · Esc volver")


class TrainerCardScreen(Screen):
    background = theme.NIGHT

    def __init__(self, app, player):
        super().__init__(app)
        self.player = player

    def on_key(self, action: str) -> None:
        if action in ("back", "confirm"):
            self.app.pop()

    def on_click(self, x: int, y: int) -> None:
        self.app.pop()

    def draw(self, r: Renderer) -> None:
        p = self.player
        title_bar(r, "Carné de entrenador", p.name)
        panel(r, 40, 90, 880, 450, fill=theme.PANEL)
        r.image(self.app.assets.trainer(p.avatar, (180, 240)), 150, 330, "center")
        r.text(280, 110, p.name, 34, theme.INK, "nw", True)
        label = {"easy": "Fácil", "normal": "Normal", "hard": "Difícil"}.get(p.difficulty, "Normal")
        r.text(280, 160, f"Dificultad: {label}", 18, theme.INK_SOFT, "nw", True)
        rows = (("Dinero", f"${p.money}"), ("Pokédex", f"{len(p.caught)} capturados / {len(p.seen)} vistos"),
                ("Entrenadores vencidos", p.stats["trainer_wins"]), ("Combates salvajes", p.stats["wild_wins"]),
                ("Capturas", p.stats["captures"]), ("Evoluciones", p.stats["evolutions"]),
                ("Pasos", p.stats["steps"]), ("Derrotas", p.stats["blackouts"]))
        for i, (k, v) in enumerate(rows):
            y = 200 + i * 34
            r.text(280, y, k, 18, theme.INK_SOFT, "nw", True)
            r.text(620, y, str(v), 18, theme.INK, "nw", True)
        r.text(280, 490, "Medallas", 18, theme.INK, "nw", True)
        for i, (mid, name) in enumerate(MEDALS.items()):
            draw_medal(r, 450 + i * 90, 502, mid, mid in p.medals, 28)
        if p.flags.get("champion"):
            r.text(880, 130, "★ CAMPEÓN ★", 22, theme.GOLD, "ne", True)
        hint_bar(r, "Esc volver")
