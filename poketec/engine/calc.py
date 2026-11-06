"""Fórmulas de combate: etapas de estadísticas, daño y captura."""
import math
import random
from dataclasses import dataclass
from typing import Optional

from .moves import Move, PHYSICAL
from .elements import type_multiplier

CRIT_CHANCE = 1 / 16
HIGH_CRIT_CHANCE = 1 / 8
STAB = 1.5
CRIT_MULT = 1.5


def stage_multiplier(stage: int) -> float:
    stage = max(-6, min(6, stage))
    return (2 + stage) / 2 if stage >= 0 else 2 / (2 - stage)


def effective_stat(mon, stat: str) -> float:
    """Estadística con etapas, parálisis (velocidad) y quemadura (ataque)."""
    value = mon.stats[stat] * stage_multiplier(mon.stages.get(stat, 0))
    if stat == "spe" and mon.status == "paralisis":
        value *= 0.5
    if stat == "atk" and mon.status == "quemadura":
        value *= 0.5
    return max(1.0, value)


@dataclass
class DamageResult:
    damage: int
    effectiveness: float
    critical: bool


def base_damage(attacker, defender, move: Move) -> float:
    """Daño sin factores aleatorios (ni crítico ni variación)."""
    if move.category == PHYSICAL:
        atk, dfn = effective_stat(attacker, "atk"), effective_stat(defender, "def")
    else:
        atk, dfn = effective_stat(attacker, "spa"), effective_stat(defender, "spd")
    raw = ((2 * attacker.level / 5 + 2) * move.power * atk / dfn) / 50 + 2
    if move.type in attacker.types:
        raw *= STAB
    return raw * type_multiplier(move.type, defender.types)


def expected_damage(attacker, defender, move: Move) -> float:
    """Daño medio esperado (lo usa la IA para comparar movimientos)."""
    if not move.is_damaging:
        return 0.0
    crit = HIGH_CRIT_CHANCE if move.effect.get("crit") else CRIT_CHANCE
    return base_damage(attacker, defender, move) * 0.925 * (1 + crit * (CRIT_MULT - 1))


def roll_damage(attacker, defender, move: Move, rng: random.Random,
                force_crit: Optional[bool] = None) -> DamageResult:
    eff = type_multiplier(move.type, defender.types)
    if eff == 0:
        return DamageResult(0, 0.0, False)
    chance = HIGH_CRIT_CHANCE if move.effect.get("crit") else CRIT_CHANCE
    crit = rng.random() < chance if force_crit is None else force_crit
    dmg = base_damage(attacker, defender, move) * rng.uniform(0.85, 1.0)
    if crit:
        dmg *= CRIT_MULT
    return DamageResult(max(1, int(dmg)), eff, crit)


def capture_shakes(foe, ball_multiplier: float, rng: random.Random) -> int:
    """Simula el lanzamiento: devuelve 4 si se captura, 0-3 sacudidas si escapa."""
    if ball_multiplier >= 255:
        return 4
    max_hp = foe.max_hp
    bonus = 2.0 if foe.status == "sueno" else 1.5 if foe.status else 1.0
    a = ((3 * max_hp - 2 * foe.hp) * foe.species.catch_rate * ball_multiplier * bonus) / (3 * max_hp)
    a = max(1.0, a)
    if a >= 255:
        return 4
    b = 1048560 / math.sqrt(math.sqrt(16711680 / a))
    shakes = 0
    for _ in range(4):
        if rng.randrange(65536) < b:
            shakes += 1
        else:
            break
    return shakes
