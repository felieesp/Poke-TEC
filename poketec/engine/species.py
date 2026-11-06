"""Catálogo de especies: estadísticas base, evoluciones y movimientos.

Para añadir una especie basta con una nueva llamada a `_s(...)`.
Si existe `images/Pokemones/<sprite>.png` se usa ese arte; si no, la
interfaz dibuja una criatura genérica de respaldo.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

STAT_KEYS = ("hp", "atk", "def", "spa", "spd", "spe")


@dataclass(frozen=True)
class Evolution:
    to: str
    method: str          # "level" | "item"
    value: object        # nivel (int) o id de objeto (str)


@dataclass(frozen=True)
class Species:
    id: str
    name: str
    types: Tuple[str, ...]
    base: Dict[str, int]
    base_exp: int
    catch_rate: int
    evolution: Optional[Evolution]
    learnset: Tuple[Tuple[int, str], ...]
    sprite: str                      # nombre de archivo sin extensión

    @property
    def primary_type(self) -> str:
        return self.types[0]


SPECIES: Dict[str, Species] = {}
_PRE_EVOLUTION: Dict[str, str] = {}

# Archivos de arte que ya existían en el repositorio con otro nombre.
_SPRITE_FILES = {"snorlax": "Snorlaxx", "squirtle": "Squirttle"}


def _s(id_, name, types, stats, base_exp, catch, evo, learnset):
    base = dict(zip(STAT_KEYS, stats))
    evolution = Evolution(evo[2], evo[0], evo[1]) if evo else None
    SPECIES[id_] = Species(
        id_, name, tuple(types.split("/")), base, base_exp, catch,
        evolution, tuple(learnset), _SPRITE_FILES.get(id_, name),
    )


#          id            nombre        tipos             PS atk def spa spd spe  exp  cap  evolución
# --- Inicial planta -----------------------------------------------------------------------------
_s("bulbasaur", "Bulbasaur", "grass/poison", (45, 49, 49, 65, 65, 45), 64, 45, ("level", 16, "ivysaur"),
   [(1, "placaje"), (3, "gruñido"), (7, "latigo_cepa"), (10, "polvo_veneno"), (15, "hoja_afilada"), (20, "somnifero")])
_s("ivysaur", "Ivysaur", "grass/poison", (60, 62, 63, 80, 80, 60), 142, 45, ("level", 32, "venusaur"),
   [(22, "megaagotar"), (26, "golpe_cuerpo")])
_s("venusaur", "Venusaur", "grass/poison", (80, 82, 83, 100, 100, 80), 236, 45, None,
   [(32, "rayo_solar"), (36, "bomba_lodo")])
# --- Inicial fuego ------------------------------------------------------------------------------
_s("charmander", "Charmander", "fire", (39, 52, 43, 60, 50, 65), 62, 45, ("level", 16, "charmeleon"),
   [(1, "aranazo"), (1, "gruñido"), (7, "ascuas"), (13, "mordisco"), (24, "lanzallamas")])
_s("charmeleon", "Charmeleon", "fire", (58, 64, 58, 80, 65, 80), 142, 45, ("level", 36, "charizard"),
   [(30, "derribo")])
_s("charizard", "Charizard", "fire/flying", (78, 84, 78, 109, 85, 100), 240, 45, None,
   [(36, "ataque_ala"), (42, "llamarada")])
# --- Inicial agua -------------------------------------------------------------------------------
_s("squirtle", "Squirtle", "water", (44, 48, 65, 50, 64, 43), 63, 45, ("level", 16, "wartortle"),
   [(1, "placaje"), (4, "latigo"), (7, "burbuja"), (10, "pistola_agua"), (16, "mordisco"), (22, "golpe_cuerpo")])
_s("wartortle", "Wartortle", "water", (59, 63, 80, 65, 80, 58), 142, 45, ("level", 36, "blastoise"),
   [(28, "surf")])
_s("blastoise", "Blastoise", "water", (79, 83, 100, 85, 105, 78), 239, 45, None,
   [(36, "hidrobomba")])
# --- Eléctrico / Eevee --------------------------------------------------------------------------
_s("pikachu", "Pikachu", "electric", (35, 55, 40, 50, 50, 90), 112, 190, ("item", "piedra_trueno", "raichu"),
   [(1, "impactrueno"), (1, "gruñido"), (5, "ataque_rapido"), (10, "onda_trueno"), (18, "rapidez"),
    (26, "rayo"), (33, "golpe_cuerpo")])
_s("raichu", "Raichu", "electric", (60, 90, 55, 90, 80, 110), 218, 75, None,
   [(36, "trueno")])
_s("eevee", "Eevee", "normal", (55, 55, 50, 45, 65, 55), 65, 45, ("item", "piedra_agua", "vaporeon"),
   [(1, "placaje"), (1, "latigo"), (8, "ataque_rapido"), (16, "mordisco"), (24, "golpe_cuerpo")])
_s("vaporeon", "Vaporeon", "water", (130, 65, 60, 110, 95, 65), 184, 45, None,
   [(1, "pistola_agua"), (30, "surf"), (40, "hidrobomba")])
# --- Otros del roster original ------------------------------------------------------------------
_s("snorlax", "Snorlax", "normal", (160, 110, 65, 65, 110, 30), 189, 25, None,
   [(1, "placaje"), (5, "fortaleza"), (12, "golpe_cuerpo"), (25, "terremoto"), (30, "derribo"), (40, "hiperrayo")])
_s("gastly", "Gastly", "ghost/poison", (30, 35, 30, 100, 35, 80), 62, 190, ("level", 25, "haunter"),
   [(1, "lenguetazo"), (5, "hipnosis"), (12, "acido"), (20, "bola_sombra")])
_s("haunter", "Haunter", "ghost/poison", (45, 50, 45, 115, 55, 95), 142, 90, ("level", 38, "gengar"),
   [(28, "bomba_lodo")])
_s("gengar", "Gengar", "ghost/poison", (60, 65, 60, 130, 75, 110), 225, 45, None,
   [(38, "psiquico")])
_s("onix", "Onix", "rock/ground", (35, 45, 160, 30, 45, 70), 77, 45, None,
   [(1, "placaje"), (5, "fortaleza"), (10, "lanzarrocas"), (18, "mordisco"), (25, "avalancha"), (33, "terremoto")])
_s("machop", "Machop", "fighting", (70, 80, 50, 35, 35, 35), 61, 180, ("level", 28, "machoke"),
   [(1, "golpe_karate"), (6, "gruñido"), (14, "submision"), (26, "patada_salto")])
_s("machoke", "Machoke", "fighting", (80, 100, 70, 50, 60, 45), 142, 90, ("level", 40, "machamp"),
   [(30, "derribo")])
_s("machamp", "Machamp", "fighting", (90, 130, 80, 65, 85, 55), 227, 45, None,
   [(40, "avalancha")])
_s("psyduck", "Psyduck", "water", (50, 52, 48, 65, 50, 55), 64, 190, ("level", 33, "golduck"),
   [(1, "aranazo"), (5, "gruñido"), (8, "pistola_agua"), (14, "confusion"), (25, "surf")])
_s("golduck", "Golduck", "water", (80, 82, 78, 95, 80, 85), 175, 75, None,
   [(36, "psiquico")])
_s("abra", "Abra", "psychic", (25, 20, 15, 105, 55, 90), 62, 200, ("level", 16, "kadabra"),
   [(1, "confusion"), (8, "hipnosis")])
_s("kadabra", "Kadabra", "psychic", (40, 35, 30, 120, 70, 105), 140, 100, ("level", 36, "alakazam"),
   [(20, "psiquico")])
_s("alakazam", "Alakazam", "psychic", (55, 50, 45, 135, 95, 120), 225, 50, None,
   [(40, "bola_sombra")])
_s("growlithe", "Growlithe", "fire", (55, 70, 45, 70, 50, 60), 70, 190, ("item", "piedra_fuego", "arcanine"),
   [(1, "mordisco"), (1, "gruñido"), (6, "ascuas"), (14, "ataque_rapido"), (22, "lanzallamas"), (30, "derribo")])
_s("arcanine", "Arcanine", "fire", (90, 110, 80, 100, 80, 95), 194, 75, None,
   [(36, "llamarada")])
_s("vulpix", "Vulpix", "fire", (38, 41, 40, 50, 65, 65), 60, 190, ("item", "piedra_fuego", "ninetales"),
   [(1, "ascuas"), (4, "latigo"), (10, "ataque_rapido"), (20, "lanzallamas")])
_s("ninetales", "Ninetales", "fire", (73, 76, 75, 81, 100, 100), 177, 75, None,
   [(36, "llamarada")])
_s("mew", "Mew", "psychic", (100, 100, 100, 100, 100, 100), 270, 45, None,
   [(1, "placaje"), (1, "confusion"), (10, "ataque_rapido"), (20, "psiquico"), (30, "bola_sombra"), (40, "hiperrayo")])
# --- Fauna salvaje ------------------------------------------------------------------------------
_s("pidgey", "Pidgey", "normal/flying", (40, 45, 40, 35, 35, 56), 50, 255, ("level", 18, "pidgeotto"),
   [(1, "placaje"), (5, "tornado"), (9, "ataque_rapido"), (15, "picotazo"), (21, "ataque_ala")])
_s("pidgeotto", "Pidgeotto", "normal/flying", (63, 60, 55, 50, 50, 71), 122, 120, ("level", 36, "pidgeot"),
   [(30, "golpe_cuerpo")])
_s("pidgeot", "Pidgeot", "normal/flying", (83, 80, 75, 70, 70, 101), 216, 45, None,
   [(38, "hiperrayo")])
_s("rattata", "Rattata", "normal", (30, 56, 35, 25, 35, 72), 51, 255, ("level", 20, "raticate"),
   [(1, "placaje"), (1, "latigo"), (7, "ataque_rapido"), (14, "mordisco"), (23, "derribo")])
_s("raticate", "Raticate", "normal", (55, 81, 60, 50, 70, 97), 145, 127, None,
   [(28, "golpe_cuerpo")])
_s("caterpie", "Caterpie", "bug", (45, 30, 35, 20, 20, 45), 39, 255, ("level", 7, "metapod"),
   [(1, "placaje"), (1, "disparo_demora")])
_s("metapod", "Metapod", "bug", (50, 20, 55, 25, 25, 30), 72, 120, ("level", 10, "butterfree"),
   [(7, "fortaleza")])
_s("butterfree", "Butterfree", "bug/flying", (60, 45, 50, 90, 80, 70), 178, 45, None,
   [(10, "confusion"), (15, "paralizador"), (20, "somnifero"), (28, "psiquico")])
_s("weedle", "Weedle", "bug/poison", (40, 35, 30, 20, 20, 50), 39, 255, ("level", 7, "kakuna"),
   [(1, "picotazo_veneno"), (1, "disparo_demora")])
_s("kakuna", "Kakuna", "bug/poison", (45, 25, 50, 25, 25, 35), 72, 120, ("level", 10, "beedrill"),
   [(7, "fortaleza")])
_s("beedrill", "Beedrill", "bug/poison", (65, 90, 40, 45, 80, 75), 178, 45, None,
   [(10, "picadura"), (20, "chupasangre"), (28, "tijera_x")])
_s("zubat", "Zubat", "poison/flying", (40, 45, 35, 30, 40, 55), 49, 255, ("level", 22, "golbat"),
   [(1, "chupasangre"), (6, "tornado"), (12, "mordisco"), (18, "acido")])
_s("golbat", "Golbat", "poison/flying", (75, 80, 70, 65, 75, 90), 159, 90, None,
   [(24, "ataque_ala")])
_s("geodude", "Geodude", "rock/ground", (40, 80, 100, 30, 30, 20), 60, 255, ("level", 25, "graveler"),
   [(1, "placaje"), (5, "fortaleza"), (11, "lanzarrocas"), (21, "avalancha")])
_s("graveler", "Graveler", "rock/ground", (55, 95, 115, 45, 45, 35), 137, 120, ("level", 40, "golem"),
   [(30, "terremoto")])
_s("golem", "Golem", "rock/ground", (80, 120, 130, 55, 65, 45), 223, 45, None,
   [(40, "derribo")])
_s("magikarp", "Magikarp", "water", (20, 10, 55, 15, 20, 80), 40, 255, ("level", 20, "gyarados"),
   [(1, "salpicadura"), (15, "placaje")])
_s("gyarados", "Gyarados", "water/flying", (95, 125, 79, 60, 100, 81), 189, 45, None,
   [(20, "mordisco"), (22, "pistola_agua"), (30, "surf"), (36, "hiperrayo")])
_s("oddish", "Oddish", "grass/poison", (45, 50, 55, 75, 65, 30), 64, 255, ("level", 21, "gloom"),
   [(1, "absorber"), (5, "polvo_veneno"), (9, "paralizador"), (13, "acido"), (15, "somnifero")])
_s("gloom", "Gloom", "grass/poison", (60, 65, 70, 85, 75, 40), 138, 120, None,
   [(24, "megaagotar")])
_s("poliwag", "Poliwag", "water", (40, 50, 40, 40, 40, 90), 60, 255, ("level", 25, "poliwhirl"),
   [(1, "burbuja"), (1, "hipnosis"), (10, "pistola_agua"), (20, "golpe_cuerpo")])
_s("poliwhirl", "Poliwhirl", "water", (65, 65, 65, 50, 50, 90), 135, 120, None,
   [(28, "surf")])
_s("sandshrew", "Sandshrew", "ground", (50, 75, 85, 20, 30, 40), 60, 255, ("level", 22, "sandslash"),
   [(1, "aranazo"), (5, "fortaleza"), (10, "disparo_lodo"), (28, "terremoto")])
_s("sandslash", "Sandslash", "ground", (75, 100, 110, 45, 55, 65), 158, 90, None,
   [(30, "avalancha")])


# Relación inversa de evoluciones (para heredar movimientos de la preevolución)
for _sp in SPECIES.values():
    if _sp.evolution:
        _PRE_EVOLUTION[_sp.evolution.to] = _sp.id


def get_species(species_id: str) -> Species:
    try:
        return SPECIES[species_id]
    except KeyError:
        raise KeyError(f"Especie desconocida: {species_id!r}") from None


def evolution_chain(species_id: str) -> List[str]:
    """Cadena desde la forma base hasta `species_id` (inclusive)."""
    chain = [species_id]
    while chain[0] in _PRE_EVOLUTION:
        chain.insert(0, _PRE_EVOLUTION[chain[0]])
    return chain


def default_moves(species_id: str, level: int) -> List[str]:
    """Hasta 4 movimientos más recientes que una especie sabría a ese nivel."""
    learned: List[str] = []
    for sid in evolution_chain(species_id):
        for lvl, move in SPECIES[sid].learnset:
            if lvl <= level:
                if move in learned:
                    learned.remove(move)
                learned.append(move)
    return learned[-4:]


def species_at_level(species_id: str, level: int) -> str:
    """Sigue las evoluciones por nivel (útil para generar rivales)."""
    sp = SPECIES[species_id]
    while sp.evolution and sp.evolution.method == "level" and level >= sp.evolution.value:
        sp = SPECIES[sp.evolution.to]
    return sp.id


def validate_catalog() -> List[str]:
    """Devuelve una lista de problemas de consistencia (vacía si todo está bien)."""
    from .moves import MOVES
    from .elements import TYPES
    problems = []
    for sp in SPECIES.values():
        for t in sp.types:
            if t not in TYPES:
                problems.append(f"{sp.id}: tipo inválido {t}")
        for _, mv in sp.learnset:
            if mv not in MOVES:
                problems.append(f"{sp.id}: movimiento inexistente {mv}")
        if sp.evolution and sp.evolution.to not in SPECIES:
            problems.append(f"{sp.id}: evoluciona a especie inexistente {sp.evolution.to}")
        if not default_moves(sp.id, 1):
            problems.append(f"{sp.id}: sin movimientos a nivel 1")
    return problems
