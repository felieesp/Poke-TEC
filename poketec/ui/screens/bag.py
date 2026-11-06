"""Mochila (en combate y en el mundo) y tienda."""
from typing import Callable, List, Optional

from ...engine.battle import Action
from ...engine.items import Item, get_item
from .. import fx, theme
from ..renderer import Renderer
from ..widgets import BACK, MenuItem, MenuList, hint_bar, panel, title_bar
from .base import Screen
from .dialogs import Dialog

POCKETS = (
    ("Medicina", ("heal", "cure", "revive", "pp")),
    ("Poké Balls", ("ball",)),
    ("Otros", ("stone", "candy")),
)


def item_icon(r: Renderer, item: Item, x: float, y: float, size: float = 26) -> None:
    """Pequeño dibujo del objeto, centrado en (x, y)."""
    kind = item.kind
    if kind == "ball":
        fx.ball(r, x, y, item.id, 0.0, size * 0.7)
    elif kind in ("heal", "cure", "pp"):
        color = {"heal": "#c050c0", "cure": "#40b0e0", "pp": "#f0a030"}[kind]
        r.rrect(x - size * 0.4, y - size * 0.2, x + size * 0.4, y + size * 0.8, 6, fill=color, outline=theme.BORDER, width=2)
        r.rect(x - size * 0.18, y - size * 0.65, x + size * 0.18, y - size * 0.2, fill="#f8f8f8", outline=theme.BORDER, width=2)
    elif kind == "revive":
        r.poly([x, y - size * 0.8, x + size * 0.7, y, x, y + size * 0.8, x - size * 0.7, y], fill="#f4d442",
               outline=theme.BORDER, width=2)
    elif kind == "stone":
        color = {"piedra_fuego": "#f06030", "piedra_agua": "#4a8ae8", "piedra_trueno": "#f4d030"}.get(item.id, "#a0a0a0")
        r.poly([x - size * 0.6, y, x - size * 0.2, y - size * 0.7, x + size * 0.4, y - size * 0.6,
                x + size * 0.7, y + size * 0.1, x + size * 0.1, y + size * 0.7, x - size * 0.5, y + size * 0.5],
               fill=color, outline=theme.BORDER, width=2)
    else:
        r.oval(x - size * 0.6, y - size * 0.6, x + size * 0.6, y + size * 0.6, fill="#ff8ab0", outline=theme.BORDER, width=2)
        r.text(x, y, "★", int(size * 0.8), theme.WHITE, "center", True)


class BagScreen(Screen):
    """Mochila.

    mode="battle": `on_pick(Action)` recibe la acción elegida (o no se llama si se cancela).
    mode="field":  los objetos se usan directamente con `adventure.use_item`.
    """
    background = theme.NIGHT

    def __init__(self, app, mode: str = "field", battle=None, on_pick: Optional[Callable] = None):
        super().__init__(app)
        self.mode, self.battle, self.on_pick = mode, battle, on_pick
        self.pocket = 0
        self.menu = MenuList([], row_h=46, gap=6, text_size=19, visible_rows=7)
        self._rows: List = []
        self._refresh()

    # ---- datos
    @property
    def bag(self):
        return self.battle.bag if self.mode == "battle" else self.app.adventure.player.bag

    def _refresh(self) -> None:
        kinds = POCKETS[self.pocket][1]
        self._rows = self.bag.listing(list(kinds))
        items = []
        for item, qty in self._rows:
            ok = self._usable(item)
            items.append(MenuItem(item.name, enabled=ok, badge=f"×{qty}"))
        self.menu.set_items(items, keep_index=True)

    def _usable(self, item: Item) -> bool:
        if self.mode == "battle":
            if item.kind == "ball":
                return self.battle.kind == "wild"
            return item.kind in ("heal", "cure", "revive", "pp")
        return item.kind != "ball"

    @property
    def current(self) -> Optional[Item]:
        return self._rows[self.menu.index][0] if self._rows else None

    # ---- acciones
    def _use(self) -> None:
        item = self.current
        if item is None:
            return
        if self.mode == "battle":
            if item.kind == "ball":
                if self.battle.kind != "wild":
                    self.notify("¡No puedes robar los Pokémon de otro entrenador!")
                    return
                self.app.pop()
                self.on_pick(Action.throw_ball(item.id))
                return
            if not self._usable(item):
                self.notify("Solo sirve fuera de combate.")
                return
            self._pick_target(item)
        else:
            if item.kind == "ball":
                self.notify("Sirve para capturar Pokémon salvajes.")
                return
            self._pick_target(item)

    def _pick_target(self, item: Item) -> None:
        from .party import TeamScreen
        if self.mode == "battle":
            team = self.battle.player_team
            enabled = lambda i, m: self.battle.can_use_item(item.id, i)           # noqa: E731
        else:
            team = self.app.adventure.player.team
            enabled = lambda i, m: self.app.adventure.can_use_item(item.id, i)    # noqa: E731

        def picked(i: int) -> None:
            if i == BACK:
                return
            if self.mode == "battle":
                self.app.pop()
                self.on_pick(Action.use_item(item.id, i))
            else:
                ok, message = self.app.adventure.use_item(item.id, i)
                self._refresh()
                self.app.push(Dialog(self.app, [message]))

        self.app.push(TeamScreen(self.app, team, mode="target", on_pick=picked, enabled=enabled,
                                 title=f"Usar {item.name}"))

    def on_resume(self, result=None) -> None:
        self._refresh()

    # ---- entrada
    def on_key(self, action: str) -> None:
        if action == "back":
            self.app.pop()
            if self.mode == "battle" and self.on_pick:
                self.on_pick(None)
        elif action == "left":
            self._switch_pocket(-1)
        elif action == "right":
            self._switch_pocket(1)
        elif action in ("up", "down"):
            self.menu.move(action)
        elif action == "confirm":
            self._use()

    def _switch_pocket(self, step: int) -> None:
        self.pocket = (self.pocket + step) % len(POCKETS)
        self.menu.index = 0
        self._refresh()

    def on_click(self, x: int, y: int) -> None:
        if 80 <= y <= 120:
            for i in range(len(POCKETS)):
                if 40 + i * 200 <= x <= 230 + i * 200:
                    self.pocket = i
                    self.menu.index = 0
                    self._refresh()
                    return
        i = self.menu.handle_click(x, y)
        if i is not None or self.menu.hit(x, y) is not None:
            self._use()

    def on_motion(self, x: int, y: int) -> None:
        self.menu.handle_motion(x, y)

    # ---- dibujo
    def draw(self, r: Renderer) -> None:
        money = self.app.adventure.player.money if self.app.adventure else 0
        title_bar(r, "Mochila", f"${money}" if self.mode == "field" else "")
        for i, (name, _) in enumerate(POCKETS):
            x = 40 + i * 200
            active = i == self.pocket
            r.rrect(x, 80, x + 190, 120, 10, fill=theme.ACCENT if active else theme.NIGHT_2,
                    outline=theme.GOLD if active else "#4a5468", width=3)
            r.text(x + 95, 100, name, 18, theme.WHITE, "center", True)
        panel(r, 30, 136, 520, 424, fill=theme.PAPER)
        if not self._rows:
            r.text(290, 340, "No tienes objetos aquí.", 18, theme.INK_SOFT, "center", True)
        self.menu.draw(r, 46, 154, 488)
        panel(r, 570, 136, 366, 424, fill=theme.PANEL)
        item = self.current
        if item:
            item_icon(r, item, 753, 220, 48)
            r.text(753, 290, item.name, 24, theme.INK, "center", True)
            r.paragraph(596, 330, item.description, 17, theme.INK, 316, True)
            r.text(596, 500, f"En la mochila: {self.bag.count(item.id)}", 16, theme.INK_SOFT, "nw", True)
        hint_bar(r, "← → cambiar de bolsillo · Enter: usar · Esc: volver")
        self.draw_toast(r)


class ShopScreen(Screen):
    """Tienda de Ciudad Roca / Pueblo Origen: compra y venta."""
    background = theme.NIGHT

    def __init__(self, app, on_done: Optional[Callable[[], None]] = None):
        super().__init__(app)
        self.adv = app.adventure
        self.on_done = on_done
        self.selling = False
        self.qty = 1
        self.menu = MenuList([], row_h=46, gap=6, text_size=19, visible_rows=7)
        self._rows: List[Item] = []
        self._refresh()

    def _refresh(self) -> None:
        if self.selling:
            self._rows = [i for i, _ in self.adv.player.bag.listing() if i.price > 0]
            items = [MenuItem(i.name, badge=f"${self.adv.sell_price(i.id)}  (×{self.adv.player.bag.count(i.id)})")
                     for i in self._rows]
        else:
            self._rows = [get_item(i) for i in self.adv.shop_stock()]
            items = [MenuItem(i.name, badge=f"${i.price}", enabled=i.price <= self.adv.player.money)
                     for i in self._rows]
        self.menu.set_items(items, keep_index=True)

    @property
    def current(self) -> Optional[Item]:
        return self._rows[self.menu.index] if self._rows else None

    def _close(self) -> None:
        self.app.pop()
        if self.on_done:
            self.on_done()

    def _transact(self) -> None:
        item = self.current
        if item is None:
            return
        ok, message = (self.adv.sell(item.id, self.qty) if self.selling else self.adv.buy(item.id, self.qty))
        self.notify(message)
        self._refresh()
        if self.selling and self.qty > self.adv.player.bag.count(item.id):
            self.qty = max(1, self.adv.player.bag.count(item.id))

    def on_key(self, action: str) -> None:
        if action == "back":
            self._close()
        elif action in ("up", "down"):
            self.menu.move(action)
        elif action == "left":
            self.qty = max(1, self.qty - 1)
        elif action == "right":
            self.qty = min(99, self.qty + 1)
        elif action == "menu":
            self.selling = not self.selling
            self.qty = 1
            self.menu.index = 0
            self._refresh()
        elif action == "confirm":
            self._transact()

    def on_click(self, x: int, y: int) -> None:
        if self.menu.handle_click(x, y) is not None:
            self._transact()

    def on_motion(self, x: int, y: int) -> None:
        self.menu.handle_motion(x, y)

    def draw(self, r: Renderer) -> None:
        title_bar(r, "Tienda — " + ("Vender" if self.selling else "Comprar"), f"Dinero: ${self.adv.player.money}")
        panel(r, 30, 84, 540, 470, fill=theme.PAPER)
        if not self._rows:
            r.text(300, 300, "No hay nada que vender.", 18, theme.INK_SOFT, "center", True)
        self.menu.draw(r, 46, 104, 508)
        panel(r, 590, 84, 346, 470, fill=theme.PANEL)
        item = self.current
        if item:
            item_icon(r, item, 763, 170, 46)
            r.text(763, 240, item.name, 24, theme.INK, "center", True)
            r.paragraph(612, 282, item.description, 17, theme.INK, 304, True)
            price = self.adv.sell_price(item.id) if self.selling else item.price
            r.text(612, 400, f"Cantidad: ◀ {self.qty} ▶", 20, theme.INK, "nw", True)
            r.text(612, 436, f"Total: ${price * self.qty}", 20, theme.ACCENT_DARK, "nw", True)
            r.text(612, 472, f"Tienes: {self.adv.player.bag.count(item.id)}", 16, theme.INK_SOFT, "nw", True)
        hint_bar(r, "Enter: " + ("vender" if self.selling else "comprar") + " · ← → cantidad · M: " +
                 ("comprar" if self.selling else "vender") + " · Esc: salir")
        self.draw_toast(r)
