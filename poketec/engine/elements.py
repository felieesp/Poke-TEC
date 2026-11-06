"""Tipos elementales y tabla de efectividad."""
from typing import Iterable

TYPES = [
    "normal", "fire", "water", "grass", "electric", "fighting", "poison",
    "ground", "flying", "psychic", "bug", "rock", "ghost",
]

TYPE_NAMES_ES = {
    "normal": "Normal", "fire": "Fuego", "water": "Agua", "grass": "Planta",
    "electric": "Eléctrico", "fighting": "Lucha", "poison": "Veneno",
    "ground": "Tierra", "flying": "Volador", "psychic": "Psíquico",
    "bug": "Bicho", "rock": "Roca", "ghost": "Fantasma",
}

# atacante -> {defensor: multiplicador}. Lo que no aparece vale 1.0.
_CHART = {
    "normal":   {"rock": 0.5, "ghost": 0.0},
    "fire":     {"fire": 0.5, "water": 0.5, "grass": 2.0, "bug": 2.0, "rock": 0.5},
    "water":    {"fire": 2.0, "water": 0.5, "grass": 0.5, "ground": 2.0, "rock": 2.0},
    "grass":    {"fire": 0.5, "water": 2.0, "grass": 0.5, "poison": 0.5, "ground": 2.0,
                 "flying": 0.5, "bug": 0.5, "rock": 2.0},
    "electric": {"water": 2.0, "grass": 0.5, "electric": 0.5, "ground": 0.0, "flying": 2.0},
    "fighting": {"normal": 2.0, "poison": 0.5, "flying": 0.5, "psychic": 0.5, "bug": 0.5,
                 "rock": 2.0, "ghost": 0.0},
    "poison":   {"grass": 2.0, "poison": 0.5, "ground": 0.5, "rock": 0.5, "ghost": 0.5},
    "ground":   {"fire": 2.0, "electric": 2.0, "grass": 0.5, "poison": 2.0, "flying": 0.0,
                 "bug": 0.5, "rock": 2.0},
    "flying":   {"electric": 0.5, "grass": 2.0, "fighting": 2.0, "bug": 2.0, "rock": 0.5},
    "psychic":  {"fighting": 2.0, "poison": 2.0, "psychic": 0.5},
    "bug":      {"fire": 0.5, "grass": 2.0, "fighting": 0.5, "poison": 0.5, "flying": 0.5,
                 "psychic": 2.0, "ghost": 0.5},
    "rock":     {"fire": 2.0, "fighting": 0.5, "ground": 0.5, "flying": 2.0, "bug": 2.0},
    "ghost":    {"normal": 0.0, "psychic": 2.0, "ghost": 2.0},
}


def type_multiplier(attack_type: str, defender_types: Iterable[str]) -> float:
    """Multiplicador total de un ataque contra uno o dos tipos defensores."""
    row = _CHART.get(attack_type, {})
    mult = 1.0
    for defender in defender_types:
        mult *= row.get(defender, 1.0)
    return mult


def effectiveness_text(mult: float) -> str:
    """Texto para el jugador ('' si el daño es normal)."""
    if mult == 0:
        return "No afecta..."
    if mult >= 2:
        return "¡Es muy eficaz!"
    if mult < 1:
        return "No es muy eficaz..."
    return ""
