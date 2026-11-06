"""Estado persistente del jugador (equipo, caja, mochila, progreso)."""
from typing import Dict, List, Optional, Set, Tuple

from .items import Inventory
from .pokemon import Pokemon
from .species import SPECIES

MAX_TEAM = 6
MEDALS = {
    "roca": "Medalla Roca",
    "cascada": "Medalla Cascada",
    "ceniza": "Medalla Ceniza",
}


class Player:
    def __init__(self, name: str, avatar: str = "Ash"):
        self.name = name
        self.avatar = avatar
        self.money = 2000
        self.bag = Inventory({"pokeball": 5, "pocion": 3})
        self.team: List[Pokemon] = []
        self.box: List[Pokemon] = []
        self.medals: Set[str] = set()
        self.defeated: Set[str] = set()          # ids de entrenadores vencidos
        self.seen: Set[str] = set()
        self.caught: Set[str] = set()
        self.completed_quests: Set[str] = set()
        self.stats: Dict[str, int] = {"trainer_wins": 0, "wild_wins": 0, "captures": 0,
                                      "evolutions": 0, "blackouts": 0, "steps": 0}
        self.flags: Dict[str, object] = {}
        self.difficulty = "normal"
        self.zone = "pueblo"
        self.pos: Tuple[int, int] = (9, 7)
        self.facing = "down"
        self.last_heal: Tuple[str, int, int] = ("pueblo", 4, 5)

    # ---- equipo -----------------------------------------------------------------------------
    @property
    def alive_count(self) -> int:
        return sum(1 for m in self.team if not m.is_fainted)

    @property
    def has_usable_pokemon(self) -> bool:
        return self.alive_count > 0

    def register_seen(self, species_id: str) -> None:
        self.seen.add(species_id)

    def register_caught(self, species_id: str) -> None:
        self.seen.add(species_id)
        self.caught.add(species_id)

    def add_pokemon(self, mon: Pokemon) -> str:
        """Añade al equipo o, si está lleno, a la caja. Devuelve 'team' o 'box'."""
        self.register_caught(mon.species_id)
        if len(self.team) < MAX_TEAM:
            self.team.append(mon)
            return "team"
        self.box.append(mon)
        return "box"

    def heal_team(self) -> None:
        for mon in self.team:
            mon.full_restore()

    def deposit(self, team_index: int) -> bool:
        """Guarda un Pokémon del equipo en la caja (siempre debe quedar uno útil)."""
        if not 0 <= team_index < len(self.team) or len(self.team) <= 1:
            return False
        others_alive = any(not m.is_fainted for i, m in enumerate(self.team) if i != team_index)
        if not others_alive:
            return False
        self.box.append(self.team.pop(team_index))
        return True

    def withdraw(self, box_index: int) -> bool:
        if not 0 <= box_index < len(self.box) or len(self.team) >= MAX_TEAM:
            return False
        self.team.append(self.box.pop(box_index))
        return True

    def swap_team(self, a: int, b: int) -> bool:
        if a == b or not (0 <= a < len(self.team) and 0 <= b < len(self.team)):
            return False
        self.team[a], self.team[b] = self.team[b], self.team[a]
        return True

    # ---- persistencia -----------------------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "name": self.name, "avatar": self.avatar, "money": self.money,
            "bag": self.bag.to_dict(),
            "team": [m.to_dict() for m in self.team],
            "box": [m.to_dict() for m in self.box],
            "medals": sorted(self.medals), "defeated": sorted(self.defeated),
            "seen": sorted(self.seen), "caught": sorted(self.caught),
            "completed_quests": sorted(self.completed_quests),
            "stats": dict(self.stats), "flags": dict(self.flags),
            "difficulty": self.difficulty, "zone": self.zone, "pos": list(self.pos),
            "facing": self.facing, "last_heal": list(self.last_heal),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Player":
        player = cls(str(data.get("name", "Entrenador"))[:12] or "Entrenador",
                     str(data.get("avatar", "Ash")))
        player.money = max(0, int(data.get("money", 0)))
        player.bag = Inventory.from_dict(data.get("bag", {}))
        player.team = [Pokemon.from_dict(d) for d in data.get("team", []) if d.get("species") in SPECIES][:MAX_TEAM]
        player.box = [Pokemon.from_dict(d) for d in data.get("box", []) if d.get("species") in SPECIES]
        player.medals = {m for m in data.get("medals", []) if m in MEDALS}
        player.defeated = set(data.get("defeated", []))
        player.seen = {s for s in data.get("seen", []) if s in SPECIES}
        player.caught = {s for s in data.get("caught", []) if s in SPECIES}
        player.completed_quests = set(data.get("completed_quests", []))
        player.stats.update({k: int(v) for k, v in data.get("stats", {}).items()})
        player.flags = dict(data.get("flags", {}))
        player.difficulty = data.get("difficulty", "normal")
        player.zone = data.get("zone", "pueblo")
        pos = data.get("pos", [9, 7])
        player.pos = (int(pos[0]), int(pos[1]))
        player.facing = data.get("facing", "down")
        heal = data.get("last_heal", ["pueblo", 4, 5])
        player.last_heal = (heal[0], int(heal[1]), int(heal[2]))
        return player
