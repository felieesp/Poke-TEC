"""Misiones y objetivos de la aventura."""
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Tuple

from .player import Player


@dataclass(frozen=True)
class Quest:
    id: str
    title: str
    description: str
    progress: Callable[[Player], Tuple[int, int]]    # (actual, objetivo)
    money: int = 0
    items: Dict[str, int] = field(default_factory=dict)

    def is_complete(self, player: Player) -> bool:
        current, target = self.progress(player)
        return current >= target


def _stat(key: str, target: int):
    return lambda p: (min(p.stats.get(key, 0), target), target)


def _medal(medal_id: str):
    return lambda p: (1 if medal_id in p.medals else 0, 1)


QUESTS: List[Quest] = [
    Quest("primer_pokemon", "Un gran comienzo", "Elige a tu primer Pokémon.",
          lambda p: (min(len(p.team) + len(p.box), 1), 1), items={"pocion": 2}),
    Quest("primer_entrenador", "Entrenador novato", "Gana tu primer combate contra un entrenador.",
          _stat("trainer_wins", 1), items={"pokeball": 5}),
    Quest("coleccionista", "Coleccionista", "Captura 3 Pokémon salvajes.",
          _stat("captures", 3), items={"superball": 3}),
    Quest("medalla_roca", "Corazón de piedra", "Consigue la Medalla Roca.",
          _medal("roca"), money=1000, items={"hiperpocion": 2}),
    Quest("evolucion", "¡Evolución!", "Haz evolucionar a un Pokémon.",
          _stat("evolutions", 1), items={"caramelo_raro": 2}),
    Quest("pokedex_15", "Aprendiz de la Pokédex", "Captura 15 especies distintas.",
          lambda p: (min(len(p.caught), 15), 15), items={"ultraball": 5}),
    Quest("medalla_cascada", "Contra la corriente", "Consigue la Medalla Cascada.",
          _medal("cascada"), money=1500, items={"revivir": 2}),
    Quest("veterano", "Veterano", "Gana 10 combates contra entrenadores.",
          _stat("trainer_wins", 10), items={"restaurar_todo": 2}),
    Quest("medalla_ceniza", "Fuego interior", "Consigue la Medalla Ceniza.",
          _medal("ceniza"), money=2000, items={"piedra_fuego": 1}),
    Quest("campeon", "Campeón de Poke-TEC", "Derrota al Rival en la Liga Poke-TEC.",
          lambda p: (1 if p.flags.get("champion") else 0, 1), money=5000, items={"masterball": 1}),
]
QUESTS_BY_ID = {q.id: q for q in QUESTS}


def check_quests(player: Player) -> List[Quest]:
    """Marca como completadas las misiones cumplidas, entrega premios y las devuelve."""
    done = []
    for quest in QUESTS:
        if quest.id in player.completed_quests or not quest.is_complete(player):
            continue
        player.completed_quests.add(quest.id)
        player.money += quest.money
        for item_id, qty in quest.items.items():
            player.bag.add(item_id, qty)
        done.append(quest)
    return done
