"""Duelo Clásico: el modo original de Poke-TEC.

Cada jugador tiene 3 Pokémon. En cada ronda eliges uno y el rival elige otro
al azar; quien gana el combate **captura** al Pokémon derrotado (que vuelve
con la vida restaurada). La partida termina cuando alguien se queda sin
Pokémon; el puntaje es el número de capturas, como en la versión original.
"""
import random
from typing import List, Optional

from .ai import AI
from .battle import Battle
from .pokemon import Pokemon

CLASSIC_LEVEL = 30
TEAM_SIZE = 3
# Los Pokémon con los que contaba la versión original
CLASSIC_ROSTER = [
    "charmander", "squirtle", "bulbasaur", "pikachu", "eevee", "snorlax", "gengar",
    "onix", "machop", "psyduck", "blastoise", "charmeleon", "growlithe", "haunter",
    "ivysaur", "kadabra", "vulpix", "vaporeon", "mew",
]


class ClassicDuel:
    def __init__(self, player_name: str, chosen_species: List[str], *, difficulty: str = "normal",
                 rng: Optional[random.Random] = None, level: int = CLASSIC_LEVEL):
        if len(chosen_species) != TEAM_SIZE or len(set(chosen_species)) != TEAM_SIZE:
            raise ValueError(f"Debes elegir exactamente {TEAM_SIZE} Pokémon distintos")
        self.rng = rng or random.Random()
        self.player_name = player_name
        self.difficulty = difficulty
        self.player_team = [Pokemon(s, level, rng=self.rng) for s in chosen_species]
        rival_pool = self.rng.sample([s for s in CLASSIC_ROSTER if s not in chosen_species]
                                     if len(CLASSIC_ROSTER) - TEAM_SIZE >= TEAM_SIZE else CLASSIC_ROSTER,
                                     TEAM_SIZE)
        self.enemy_team = [Pokemon(s, level, rng=self.rng) for s in rival_pool]
        self.score = 0           # capturas del jugador
        self.rounds = 0

    @property
    def is_over(self) -> bool:
        return not self.player_team or not self.enemy_team

    @property
    def player_won(self) -> bool:
        return bool(self.player_team) and not self.enemy_team

    def start_round(self, player_index: int) -> Battle:
        """Prepara un combate 1 contra 1: el elegido contra un rival al azar."""
        if self.is_over:
            raise RuntimeError("El duelo ya terminó")
        mine = self.player_team[player_index]
        theirs = self.rng.choice(self.enemy_team)
        mine.reset_battle_state()
        theirs.reset_battle_state()
        self.rounds += 1
        ai_level = {"easy": "easy", "normal": "normal", "hard": "hard"}[self.difficulty]
        return Battle([mine], [theirs], kind="trainer", foe_name="Rival",
                      player_name=self.player_name, bag=None, ai=AI(ai_level, self.rng),
                      rng=self.rng, award_exp=False)

    def finish_round(self, battle: Battle) -> str:
        """Aplica la regla de captura. Devuelve 'captured', 'lost' o 'none'."""
        mine, theirs = battle.player_team[0], battle.foe_team[0]
        if battle.result == "win":
            self.enemy_team.remove(theirs)
            theirs.full_restore()
            self.player_team.append(theirs)
            self.score += 1
            return "captured"
        if battle.result == "lose":
            self.player_team.remove(mine)
            mine.full_restore()
            self.enemy_team.append(mine)
            return "lost"
        return "none"
