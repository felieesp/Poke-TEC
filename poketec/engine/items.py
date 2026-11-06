"""Objetos e inventario."""
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class Item:
    id: str
    name: str
    description: str
    price: int            # 0 = no se vende en tiendas
    kind: str             # heal | revive | cure | pp | ball | stone | candy
    power: float = 0      # PS curados, multiplicador de ball, etc.
    cures: Optional[str] = None   # estado que cura ("*" = todos)


ITEMS: Dict[str, Item] = {}


def _i(id_, name, desc, price, kind, power=0, cures=None):
    ITEMS[id_] = Item(id_, name, desc, price, kind, power, cures)


_i("pocion", "Poción", "Restaura 20 PS.", 300, "heal", 20)
_i("superpocion", "Superpoción", "Restaura 60 PS.", 700, "heal", 60)
_i("hiperpocion", "Hiperpoción", "Restaura 200 PS.", 1200, "heal", 200)
_i("restaurar_todo", "Restaurar Todo", "Restaura todos los PS y cura estados.", 2500, "heal", 9999, "*")
_i("antidoto", "Antídoto", "Cura el envenenamiento.", 100, "cure", cures="veneno")
_i("antiquemar", "Antiquemar", "Cura las quemaduras.", 250, "cure", cures="quemadura")
_i("antiparalizador", "Antiparalizador", "Cura la parálisis.", 200, "cure", cures="paralisis")
_i("despertar", "Despertar", "Despierta a un Pokémon dormido.", 250, "cure", cures="sueno")
_i("cura_total", "Cura Total", "Cura cualquier estado alterado.", 600, "cure", cures="*")
_i("revivir", "Revivir", "Revive a un Pokémon debilitado con la mitad de sus PS.", 1500, "revive", 0.5)
_i("eter", "Éter", "Restaura 10 PP de cada movimiento.", 400, "pp", 10)
_i("pokeball", "Poké Ball", "Sirve para capturar Pokémon salvajes.", 200, "ball", 1.0)
_i("superball", "Súper Ball", "Mayor probabilidad de captura que la Poké Ball.", 600, "ball", 1.5)
_i("ultraball", "Ultra Ball", "Muy alta probabilidad de captura.", 1200, "ball", 2.0)
_i("masterball", "Master Ball", "Captura cualquier Pokémon salvaje sin fallar.", 0, "ball", 255.0)
_i("piedra_fuego", "Piedra Fuego", "Hace evolucionar a ciertos Pokémon de fuego.", 2100, "stone")
_i("piedra_agua", "Piedra Agua", "Hace evolucionar a ciertos Pokémon.", 2100, "stone")
_i("piedra_trueno", "Piedra Trueno", "Hace evolucionar a ciertos Pokémon eléctricos.", 2100, "stone")
_i("caramelo_raro", "Caramelo Raro", "Sube un nivel al Pokémon que lo coma.", 0, "candy")


def get_item(item_id: str) -> Item:
    try:
        return ITEMS[item_id]
    except KeyError:
        raise KeyError(f"Objeto desconocido: {item_id!r}") from None


class Inventory:
    """Mochila: cantidades por objeto."""

    def __init__(self, contents: Optional[Dict[str, int]] = None):
        self._items: Dict[str, int] = {}
        for item_id, qty in (contents or {}).items():
            self.add(item_id, qty)

    def count(self, item_id: str) -> int:
        return self._items.get(item_id, 0)

    def add(self, item_id: str, qty: int = 1) -> None:
        get_item(item_id)
        if qty > 0:
            self._items[item_id] = min(99, self.count(item_id) + qty)

    def remove(self, item_id: str, qty: int = 1) -> bool:
        if qty <= 0 or self.count(item_id) < qty:
            return False
        self._items[item_id] -= qty
        if self._items[item_id] == 0:
            del self._items[item_id]
        return True

    def listing(self, kinds: Optional[List[str]] = None):
        """[(Item, cantidad)] ordenado por catálogo; opcionalmente filtrado por clase."""
        rows = []
        for item_id in ITEMS:
            if item_id in self._items and (kinds is None or ITEMS[item_id].kind in kinds):
                rows.append((ITEMS[item_id], self._items[item_id]))
        return rows

    def to_dict(self) -> Dict[str, int]:
        return dict(self._items)

    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> "Inventory":
        inv = cls()
        for item_id, qty in (data or {}).items():
            if item_id in ITEMS and isinstance(qty, int):
                inv.add(item_id, qty)
        return inv
