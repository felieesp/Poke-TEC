"""Un Pokémon concreto: nivel, estadísticas individuales (IV), movimientos, estado."""
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .moves import Move, get_move
from .species import STAT_KEYS, Species, default_moves, get_species

MAX_LEVEL = 100
MAX_MOVES = 4

STATUSES = ("quemadura", "paralisis", "veneno", "sueno")
STATUS_LABELS = {"quemadura": "QUE", "paralisis": "PAR", "veneno": "ENV", "sueno": "DOR"}
STATUS_NAMES = {"quemadura": "quemado", "paralisis": "paralizado",
                "veneno": "envenenado", "sueno": "dormido"}

BATTLE_STATS = ("atk", "def", "spa", "spd", "spe")
STAT_NAMES_ES = {"atk": "Ataque", "def": "Defensa", "spa": "Ataque Esp.",
                 "spd": "Defensa Esp.", "spe": "Velocidad"}


def exp_for_level(level: int) -> int:
    """Experiencia total necesaria para alcanzar `level` (curva cúbica)."""
    return level ** 3


class MoveSlot:
    """Movimiento aprendido con sus PP actuales."""
    __slots__ = ("id", "pp")

    def __init__(self, move_id: str, pp: Optional[int] = None):
        self.id = move_id
        self.pp = get_move(move_id).pp if pp is None else pp

    @property
    def move(self) -> Move:
        return get_move(self.id)

    @property
    def max_pp(self) -> int:
        return self.move.pp


@dataclass
class LevelUp:
    level: int
    learned: List[str] = field(default_factory=list)   # aprendidos automáticamente
    pending: List[str] = field(default_factory=list)   # esperan decisión del jugador


class Pokemon:
    def __init__(self, species_id: str, level: int = 5, *, rng=None, ivs=None,
                 moves=None, nickname: Optional[str] = None):
        rng = rng or random
        get_species(species_id)
        self.species_id = species_id
        self.level = max(1, min(MAX_LEVEL, int(level)))
        self.nickname = nickname
        self.ivs: Dict[str, int] = dict(ivs) if ivs else {k: rng.randint(0, 15) for k in STAT_KEYS}
        self.exp = exp_for_level(self.level)
        self.moves: List[MoveSlot] = [MoveSlot(m) for m in
                                      (moves or default_moves(species_id, self.level))][:MAX_MOVES]
        self.status: Optional[str] = None
        self.sleep_turns = 0
        self.pending_moves: List[str] = []
        self.stages: Dict[str, int] = {k: 0 for k in BATTLE_STATS}
        self.stats: Dict[str, int] = {}
        self.max_hp = 1
        self._recalculate()
        self.hp = self.max_hp

    # ----- propiedades -----------------------------------------------------------------------
    @property
    def species(self) -> Species:
        return get_species(self.species_id)

    @property
    def name(self) -> str:
        return self.nickname or self.species.name

    @property
    def types(self):
        return self.species.types

    @property
    def is_fainted(self) -> bool:
        return self.hp <= 0

    @property
    def hp_fraction(self) -> float:
        return max(0.0, self.hp / self.max_hp)

    # ----- estadísticas ----------------------------------------------------------------------
    def _recalculate(self) -> None:
        base = self.species.base
        stats = {}
        for key in STAT_KEYS:
            core = ((2 * base[key] + self.ivs.get(key, 0)) * self.level) // 100
            stats[key] = core + self.level + 10 if key == "hp" else core + 5
        self.stats = stats
        self.max_hp = stats["hp"]

    # ----- vida y estados --------------------------------------------------------------------
    def take_damage(self, amount: int) -> int:
        dealt = max(0, min(self.hp, int(amount)))
        self.hp -= dealt
        if self.hp <= 0:
            self.hp = 0
            self.status = None
            self.sleep_turns = 0
        return dealt

    def heal(self, amount: int) -> int:
        if self.is_fainted:
            return 0
        restored = max(0, min(self.max_hp - self.hp, int(amount)))
        self.hp += restored
        return restored

    def revive(self, fraction: float = 0.5) -> bool:
        if not self.is_fainted:
            return False
        self.hp = max(1, int(self.max_hp * fraction))
        return True

    def can_get_status(self, status: str) -> bool:
        if self.is_fainted or self.status is not None:
            return False
        if status == "quemadura" and "fire" in self.types:
            return False
        if status == "paralisis" and "electric" in self.types:
            return False
        if status == "veneno" and "poison" in self.types:
            return False
        return True

    def set_status(self, status: str, rng=None) -> bool:
        if status not in STATUSES or not self.can_get_status(status):
            return False
        self.status = status
        self.sleep_turns = (rng or random).randint(1, 3) if status == "sueno" else 0
        return True

    def clear_status(self) -> None:
        self.status = None
        self.sleep_turns = 0

    def reset_battle_state(self) -> None:
        self.stages = {k: 0 for k in BATTLE_STATS}

    def restore_pp(self, amount: Optional[int] = None) -> None:
        for slot in self.moves:
            slot.pp = slot.max_pp if amount is None else min(slot.max_pp, slot.pp + amount)

    def full_restore(self) -> None:
        """Cura total (Centro Pokémon)."""
        self.hp = self.max_hp
        self.clear_status()
        self.restore_pp()
        self.reset_battle_state()

    # ----- experiencia -----------------------------------------------------------------------
    @property
    def exp_into_level(self) -> int:
        return self.exp - exp_for_level(self.level)

    @property
    def exp_needed_for_next(self) -> int:
        if self.level >= MAX_LEVEL:
            return 0
        return exp_for_level(self.level + 1) - exp_for_level(self.level)

    @property
    def exp_fraction(self) -> float:
        needed = self.exp_needed_for_next
        return 1.0 if needed == 0 else max(0.0, min(1.0, self.exp_into_level / needed))

    def gain_exp(self, amount: int) -> List[LevelUp]:
        """Suma experiencia y devuelve un registro por cada nivel subido."""
        results: List[LevelUp] = []
        if amount <= 0 or self.level >= MAX_LEVEL:
            return results
        self.exp = min(exp_for_level(MAX_LEVEL), self.exp + int(amount))
        while self.level < MAX_LEVEL and self.exp >= exp_for_level(self.level + 1):
            results.append(self._level_up())
        return results

    def _level_up(self) -> LevelUp:
        old_max = self.max_hp
        self.level += 1
        self._recalculate()
        if not self.is_fainted:
            self.hp = min(self.max_hp, self.hp + (self.max_hp - old_max))
        info = LevelUp(self.level)
        for lvl, move_id in self.species.learnset:
            if lvl != self.level or self.knows(move_id) or move_id in self.pending_moves:
                continue
            if len(self.moves) < MAX_MOVES:
                self.moves.append(MoveSlot(move_id))
                info.learned.append(move_id)
            else:
                self.pending_moves.append(move_id)
                info.pending.append(move_id)
        return info

    def set_level(self, level: int) -> None:
        """Fija el nivel sin aprender movimientos (para generar rivales/pruebas)."""
        self.level = max(1, min(MAX_LEVEL, level))
        self.exp = exp_for_level(self.level)
        self._recalculate()
        self.hp = min(self.hp, self.max_hp)

    # ----- movimientos -----------------------------------------------------------------------
    def knows(self, move_id: str) -> bool:
        return any(s.id == move_id for s in self.moves)

    def learn_move(self, move_id: str, replace_index: Optional[int] = None) -> bool:
        """Aprende un movimiento (reemplazando el de `replace_index` si hay 4)."""
        if self.knows(move_id):
            self._drop_pending(move_id)
            return False
        if len(self.moves) < MAX_MOVES:
            self.moves.append(MoveSlot(move_id))
        elif replace_index is not None and 0 <= replace_index < len(self.moves):
            self.moves[replace_index] = MoveSlot(move_id)
        else:
            return False
        self._drop_pending(move_id)
        return True

    def forget_pending(self, move_id: str) -> None:
        self._drop_pending(move_id)

    def _drop_pending(self, move_id: str) -> None:
        if move_id in self.pending_moves:
            self.pending_moves.remove(move_id)

    # ----- evolución -------------------------------------------------------------------------
    def level_evolution(self) -> Optional[str]:
        evo = self.species.evolution
        if evo and evo.method == "level" and self.level >= evo.value:
            return evo.to
        return None

    def item_evolution(self, item_id: str) -> Optional[str]:
        evo = self.species.evolution
        if evo and evo.method == "item" and evo.value == item_id:
            return evo.to
        return None

    def evolve(self, new_species_id: str) -> None:
        get_species(new_species_id)
        old_max = self.max_hp
        self.species_id = new_species_id
        self._recalculate()
        if not self.is_fainted:
            self.hp = min(self.max_hp, self.hp + max(0, self.max_hp - old_max))
        for lvl, move_id in self.species.learnset:
            if lvl <= self.level and not self.knows(move_id) and len(self.moves) < MAX_MOVES:
                self.moves.append(MoveSlot(move_id))

    # ----- persistencia ----------------------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "species": self.species_id, "level": self.level, "exp": self.exp,
            "nickname": self.nickname, "ivs": dict(self.ivs), "hp": self.hp,
            "status": self.status, "sleep_turns": self.sleep_turns,
            "moves": [[s.id, s.pp] for s in self.moves],
            "pending_moves": list(self.pending_moves),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Pokemon":
        mon = cls(data["species"], data.get("level", 5), ivs=data.get("ivs"),
                  moves=[m[0] for m in data.get("moves", [])] or None,
                  nickname=data.get("nickname"))
        mon.exp = max(mon.exp, int(data.get("exp", mon.exp)))
        for slot, saved in zip(mon.moves, data.get("moves", [])):
            slot.pp = max(0, min(slot.max_pp, int(saved[1])))
        mon.hp = max(0, min(mon.max_hp, int(data.get("hp", mon.max_hp))))
        status = data.get("status")
        mon.status = status if status in STATUSES and mon.hp > 0 else None
        mon.sleep_turns = int(data.get("sleep_turns", 0)) if mon.status == "sueno" else 0
        mon.pending_moves = [m for m in data.get("pending_moves", []) if not mon.knows(m)]
        return mon

    def clone(self) -> "Pokemon":
        return Pokemon.from_dict(self.to_dict())

    def __repr__(self) -> str:
        return f"<{self.name} Nv{self.level} {self.hp}/{self.max_hp}>"
