"""Datos del mundo: zonas, entrenadores, personajes y tiendas.

Cada mapa mide 20x12 casillas. Leyenda de casillas:
  #  árbol (bloquea)        .  camino            ,  césped corto
  g  hierba alta (combates salvajes)             f  flores
  w  agua (bloquea)         r  roca (bloquea)    h  edificio (bloquea)
  C  Centro Pokémon   M  Tienda   G  Gimnasio   L  Liga Poke-TEC
  1-4  salidas hacia otras zonas
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

MAP_W, MAP_H = 20, 12
BLOCKED = set("#whr")
INTERACT_TILES = set("CMGL")
DIRECTIONS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}


# ----------------------------------------------------------------------------- definiciones
@dataclass(frozen=True)
class Warp:
    zone: str
    pos: Tuple[int, int]
    requires_medal: Optional[str] = None
    blocked_text: str = ""


@dataclass(frozen=True)
class TrainerDef:
    id: str
    name: str
    zone: str
    pos: Tuple[int, int]
    facing: str
    sight: int
    team: Tuple[Tuple[str, int], ...]      # ("@rival", nivel) = starter rival según el jugador
    money: int
    intro: str
    defeat: str
    after: str
    color: str = "#c0392b"
    role: str = "trainer"                  # trainer | leader | rival | champion
    medal: Optional[str] = None
    items: Dict[str, int] = field(default_factory=dict)
    reward_items: Dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class NPC:
    id: str
    name: str
    zone: str
    pos: Tuple[int, int]
    lines: Tuple[str, ...]
    color: str = "#2980b9"


@dataclass
class Zone:
    id: str
    name: str
    grid: List[str]
    warps: Dict[str, Warp]
    encounters: List[Tuple[str, int, int, int]] = field(default_factory=list)  # (especie, nmin, nmax, peso)
    encounter_rate: float = 0.0
    theme: str = "route"                  # route | town | forest | coast | volcano
    default_pos: Tuple[int, int] = (1, 5)

    def tile(self, x: int, y: int) -> str:
        if 0 <= y < len(self.grid) and 0 <= x < len(self.grid[y]):
            return self.grid[y][x]
        return "#"


# ----------------------------------------------------------------------------- utilidades de mapa
class _Painter:
    def __init__(self, fill: str = ","):
        self.cells = [[fill] * MAP_W for _ in range(MAP_H)]

    def rect(self, ch: str, x1: int, y1: int, x2: int, y2: int) -> "_Painter":
        for y in range(y1, y2 + 1):
            for x in range(x1, x2 + 1):
                self.cells[y][x] = ch
        return self

    def put(self, ch: str, x: int, y: int) -> "_Painter":
        self.cells[y][x] = ch
        return self

    def border(self, ch: str = "#") -> "_Painter":
        self.rect(ch, 0, 0, MAP_W - 1, 0).rect(ch, 0, MAP_H - 1, MAP_W - 1, MAP_H - 1)
        self.rect(ch, 0, 0, 0, MAP_H - 1).rect(ch, MAP_W - 1, 0, MAP_W - 1, MAP_H - 1)
        return self

    def done(self) -> List[str]:
        return ["".join(row) for row in self.cells]


def _pueblo() -> List[str]:
    p = _Painter().border()
    p.rect(".", 1, 5, 18, 5)
    p.rect("h", 2, 2, 5, 4).put("C", 3, 4)
    p.rect("h", 14, 2, 17, 4).put("M", 15, 4)
    p.rect("f", 8, 2, 11, 3).rect("f", 3, 8, 5, 9).rect("f", 12, 8, 13, 10)
    p.rect("#", 15, 8, 17, 9).rect("#", 1, 10, 2, 10)
    p.put("1", 19, 5)
    return p.done()


def _ruta1() -> List[str]:
    p = _Painter().border()
    p.rect("g", 2, 1, 8, 3).rect("g", 12, 1, 17, 3).rect("g", 2, 7, 8, 10).rect("g", 12, 8, 17, 10)
    p.rect("#", 10, 1, 10, 3).rect("#", 10, 8, 10, 10)
    p.rect(".", 1, 5, 9, 5).put(".", 10, 5).put(".", 10, 6).rect(".", 10, 6, 18, 6)
    p.put("1", 0, 5).put("2", 19, 6)
    return p.done()


def _bosque() -> List[str]:
    p = _Painter().border()
    p.rect("g", 1, 1, 2, 4).rect("g", 6, 1, 9, 4).rect("g", 11, 8, 17, 10).rect("g", 1, 8, 6, 10)
    p.rect("#", 3, 1, 5, 2).rect("#", 7, 8, 9, 10).rect("#", 13, 7, 15, 9).rect("#", 16, 1, 17, 2)
    p.rect("#", 12, 5, 14, 5)
    p.rect(".", 1, 6, 10, 6).rect(".", 10, 3, 10, 6).rect(".", 10, 3, 18, 3).rect(".", 18, 3, 18, 5)
    p.put("1", 0, 6).put("2", 19, 5)
    return p.done()


def _roca() -> List[str]:
    p = _Painter().border()
    p.rect(".", 1, 5, 18, 5)
    p.rect("h", 2, 2, 5, 4).put("C", 3, 4)
    p.rect("h", 14, 2, 17, 4).put("M", 15, 4)
    p.rect("h", 8, 1, 11, 4).put("G", 9, 4)
    p.rect("r", 1, 8, 4, 10).rect("r", 14, 8, 18, 10).rect("f", 7, 8, 11, 9)
    p.put("1", 0, 5).put("2", 19, 5)
    return p.done()


def _costa() -> List[str]:
    p = _Painter().border()
    p.rect("w", 1, 9, 18, 10)
    p.rect("g", 12, 1, 17, 3).rect("g", 1, 6, 6, 8).rect("g", 9, 7, 17, 8)
    p.rect(".", 1, 5, 18, 5)
    p.rect("h", 2, 2, 5, 4).put("C", 3, 4)
    p.rect("h", 8, 1, 11, 4).put("G", 9, 4)
    p.put("1", 0, 5).put("2", 19, 5)
    return p.done()


def _pico() -> List[str]:
    p = _Painter().border()
    p.rect("g", 1, 7, 8, 10).rect("g", 11, 7, 17, 10)
    p.rect("r", 9, 9, 10, 10).rect("r", 1, 1, 3, 3).rect("r", 6, 1, 7, 2)
    p.rect(".", 1, 5, 18, 5)
    p.rect("h", 4, 2, 7, 4).put("C", 5, 4)
    p.rect("h", 9, 1, 12, 4).put("G", 10, 4)
    p.rect("h", 15, 0, 18, 3).put("L", 16, 3).rect(".", 16, 4, 16, 4)
    p.put("1", 0, 5)
    return p.done()


ZONES: Dict[str, Zone] = {
    "pueblo": Zone("pueblo", "Pueblo Origen", _pueblo(),
                   {"1": Warp("ruta1", (1, 5))}, theme="town", default_pos=(9, 7)),
    "ruta1": Zone("ruta1", "Ruta 1", _ruta1(),
                  {"1": Warp("pueblo", (18, 5)), "2": Warp("bosque", (1, 6))},
                  encounters=[("pidgey", 2, 5, 40), ("rattata", 2, 5, 40), ("caterpie", 3, 5, 15),
                              ("weedle", 3, 5, 15), ("pikachu", 4, 5, 3)],
                  encounter_rate=0.16, theme="route"),
    "bosque": Zone("bosque", "Bosque Verde", _bosque(),
                   {"1": Warp("ruta1", (18, 6)), "2": Warp("roca", (1, 5))},
                   encounters=[("caterpie", 4, 7, 25), ("weedle", 4, 7, 25), ("metapod", 6, 8, 10),
                               ("kakuna", 6, 8, 10), ("oddish", 5, 8, 20), ("pidgey", 5, 8, 15),
                               ("zubat", 6, 8, 10), ("pikachu", 5, 8, 4), ("abra", 6, 8, 3)],
                   encounter_rate=0.18, theme="forest"),
    "roca": Zone("roca", "Ciudad Roca", _roca(),
                 {"1": Warp("bosque", (18, 5)),
                  "2": Warp("costa", (1, 5), "roca",
                            "Un guardia bloquea el paso: «Solo pasan quienes tengan la Medalla Roca».")},
                 theme="town"),
    "costa": Zone("costa", "Costa Azul", _costa(),
                  {"1": Warp("roca", (18, 5)),
                   "2": Warp("pico", (1, 5), "cascada",
                             "Un guardia bloquea el paso: «El Pico Ceniza es peligroso. Trae la Medalla Cascada».")},
                  encounters=[("psyduck", 12, 16, 22), ("poliwag", 12, 16, 22), ("magikarp", 10, 16, 20),
                              ("geodude", 12, 16, 12), ("sandshrew", 12, 16, 12), ("machop", 13, 16, 8),
                              ("eevee", 12, 15, 4)],
                  encounter_rate=0.17, theme="coast"),
    "pico": Zone("pico", "Pico Ceniza", _pico(),
                 {"1": Warp("costa", (18, 5))},
                 encounters=[("growlithe", 22, 28, 18), ("vulpix", 22, 28, 18), ("geodude", 22, 27, 14),
                             ("machop", 22, 28, 12), ("onix", 24, 28, 10), ("zubat", 22, 27, 12),
                             ("gastly", 22, 27, 8), ("snorlax", 25, 28, 4), ("mew", 30, 30, 1)],
                 encounter_rate=0.18, theme="volcano"),
}

# ----------------------------------------------------------------------------- entrenadores
_RIVAL_DEFEAT = "¡Hmpf! Esta vez ganaste... ¡pero te alcanzaré!"

TRAINERS: Dict[str, TrainerDef] = {t.id: t for t in [
    TrainerDef("rival_1", "Rival", "pueblo", (17, 6), "up", 1,
               (("@rival", 5),), 300, "¡Eh! ¡Espera! Quiero probar a mi nuevo Pokémon contigo.",
               _RIVAL_DEFEAT, "Te estaré observando, ¡no te confíes!", "#2c3e50", "rival"),
    TrainerDef("ruta1_luis", "Joven Luis", "ruta1", (6, 4), "down", 3,
               (("rattata", 3), ("pidgey", 4)), 90, "¡Mis Pokémon son los más rápidos!",
               "¡Qué rápido perdí!", "Entrena más y llegarás lejos."),
    TrainerDef("ruta1_ana", "Chica Ana", "ruta1", (14, 7), "up", 2,
               (("caterpie", 4), ("weedle", 4), ("pidgey", 4)), 110, "¡Mira cuántos Pokémon bicho tengo!",
               "¡Mis bichitos...!", "Los Pokémon bicho evolucionan muy rápido.", "#e84393"),
    TrainerDef("bosque_tomas", "Cazabichos Tomás", "bosque", (6, 5), "down", 2,
               (("caterpie", 6), ("weedle", 6), ("metapod", 7)), 160, "¡Este bosque es mi territorio!",
               "¡Vaya, me ganaste!", "Los Pokémon de fuego les dan miedo a los bichos.", "#27ae60"),
    TrainerDef("bosque_marta", "Excursionista Marta", "bosque", (13, 2), "down", 2,
               (("oddish", 7), ("pidgey", 8)), 180, "¡Vamos a ver de qué estás hecho!",
               "¡Qué paliza!", "El tipo Planta es débil contra Fuego y Volador.", "#d35400"),
    TrainerDef("bosque_leo", "Cazabichos Leo", "bosque", (16, 4), "up", 1,
               (("weedle", 8), ("caterpie", 8), ("zubat", 9)), 200, "¡Nadie pasa sin luchar!",
               "¡Me quedé sin bichos!", "Cerca de Ciudad Roca hay un gimnasio muy duro.", "#27ae60"),
    TrainerDef("roca_pedro", "Líder Pedro", "roca", (9, 3), "down", 0,
               (("geodude", 12), ("geodude", 12), ("onix", 14)), 1400,
               "¡Soy Pedro, líder del Gimnasio Roca! ¡Mi defensa es inquebrantable!",
               "¡Increíble! Toma, la Medalla Roca es tuya.",
               "Tu estilo de lucha me impresionó. ¡Sigue hacia la Costa Azul!", "#7f8c8d", "leader", "roca",
               items={"pocion": 1}, reward_items={"piedra_trueno": 1}),
    TrainerDef("costa_sergio", "Nadador Sergio", "costa", (14, 4), "down", 1,
               (("poliwag", 16), ("psyduck", 17), ("magikarp", 15)), 340, "¡Al agua, patos!",
               "¡Me hundí!", "Las plantas y la electricidad derrotan al agua.", "#2980b9"),
    TrainerDef("costa_lia", "Pescadora Lía", "costa", (8, 6), "up", 2,
               (("magikarp", 18), ("psyduck", 18), ("poliwag", 18)), 360, "¡Mi caña atrapa de todo!",
               "¡Se escapó la victoria!", "Magikarp parece débil, pero tiene un secreto.", "#16a085"),
    TrainerDef("rival_2", "Rival", "costa", (16, 4), "down", 1,
               (("@rival", 22), ("pidgeotto", 20), ("kadabra", 21)), 1500,
               "¡Qué casualidad! Mi equipo ha mejorado mucho. ¡Veamos el tuyo!",
               _RIVAL_DEFEAT, "Seguiré entrenando. ¡Nos vemos en la Liga!", "#2c3e50", "rival"),
    TrainerDef("costa_marina", "Líder Marina", "costa", (9, 3), "down", 0,
               (("psyduck", 20), ("poliwhirl", 23), ("vaporeon", 26)), 2400,
               "¡Soy Marina, líder del Gimnasio Cascada! ¡Déjame arrastrarte con mis olas!",
               "¡Has sabido sortear mis olas! Toma la Medalla Cascada.",
               "El Pico Ceniza te espera. ¡Cuidado con el calor!", "#3498db", "leader", "cascada",
               items={"superpocion": 2}, reward_items={"piedra_agua": 1}),
    TrainerDef("pico_ivan", "Montañero Iván", "pico", (5, 6), "up", 1,
               (("geodude", 24), ("machop", 24), ("onix", 26)), 520, "¡La montaña pone a prueba a todos!",
               "¡Me aplastaste!", "Los Pokémon de agua apagan el fuego.", "#8e5b3a"),
    TrainerDef("pico_rosa", "Alpinista Rosa", "pico", (10, 6), "up", 1,
               (("sandshrew", 25), ("graveler", 26), ("zubat", 25)), 540, "¡Llegué a la cima antes que tú!",
               "¡Qué pena!", "Cada Pokémon aprende cosas nuevas al subir de nivel.", "#e67e22"),
    TrainerDef("pico_dante", "Fogonero Dante", "pico", (17, 6), "up", 1,
               (("growlithe", 27), ("vulpix", 27), ("charmeleon", 28)), 600, "¡Siente el calor de mi equipo!",
               "¡Me quemé yo solo!", "El gimnasio está a la izquierda de la Liga.", "#c0392b"),
    TrainerDef("pico_cenizo", "Líder Cenizo", "pico", (10, 3), "down", 0,
               (("charmeleon", 29), ("ninetales", 29), ("arcanine", 32)), 3400,
               "¡Soy Cenizo, líder del Gimnasio Ceniza! ¡Mis llamas no se apagan!",
               "¡Qué fuego tienes! La Medalla Ceniza es tuya.",
               "Ya puedes retar a la Liga Poke-TEC. ¡Mucha suerte!", "#e74c3c", "leader", "ceniza",
               items={"hiperpocion": 2}, reward_items={"superball": 5}),
    TrainerDef("rival_liga", "Rival Campeón", "pico", (16, 2), "down", 0,
               (("pidgeot", 36), ("alakazam", 36), ("gengar", 37), ("@rival", 38), ("mew", 40)), 8000,
               "Has llegado hasta aquí... ¡Soy el campeón de la Liga Poke-TEC! ¡Demuestra que mereces el título!",
               "¡Lo lograste! ¡Eres el nuevo campeón de Poke-TEC!",
               "Eres el mejor. ¡Gracias por el combate!", "#1a1a2e", "champion",
               items={"restaurar_todo": 2, "hiperpocion": 2}),
]}

# ----------------------------------------------------------------------------- personajes
NPCS: Dict[str, NPC] = {n.id: n for n in [
    NPC("pueblo_prof", "Profesor Robles", "pueblo", (9, 3),
        ("¡Bienvenido a Poke-TEC! Recorre las rutas, captura Pokémon y vence a los líderes.",
         "Pulsa ESC para abrir el menú: equipo, mochila, Pokédex, misiones y guardado.",
         "Cura a tus Pokémon en el Centro Pokémon: ¡es gratis!"), "#ecf0f1"),
    NPC("pueblo_nino", "Niño", "pueblo", (7, 7),
        ("Los Pokémon de fuego son fuertes contra la planta y el bicho.",),),
    NPC("ruta1_cartel", "Cartel", "ruta1", (11, 5),
        ("Ruta 1 — Al oeste: Pueblo Origen. Al este: Bosque Verde.",), "#a0743c"),
    NPC("bosque_viejo", "Anciano", "bosque", (9, 7),
        ("La hierba alta esconde Pokémon salvajes. ¡Lleva siempre Pociones!",
         "Dicen que un Pokémon legendario vive en el Pico Ceniza..."), "#7f8c8d"),
    NPC("roca_guia", "Guía", "roca", (12, 6),
        ("El Gimnasio Roca es de tipo Roca/Tierra. ¡Usa agua o planta!",), "#e67e22"),
    NPC("costa_marinero", "Marinero", "costa", (12, 6),
        ("El gimnasio de Marina es de tipo Agua. La electricidad y las plantas funcionan bien.",), "#34495e"),
    NPC("pico_guia", "Guía de montaña", "pico", (13, 6),
        ("La Liga Poke-TEC está arriba, a la derecha. Necesitas las tres medallas.",), "#8e5b3a"),
]}

# ----------------------------------------------------------------------------- tiendas
SHOP_STOCK: Dict[str, List[str]] = {
    "pueblo": ["pokeball", "pocion", "antidoto", "antiquemar", "antiparalizador", "despertar"],
    "roca": ["pokeball", "superball", "pocion", "superpocion", "revivir", "eter", "cura_total",
             "piedra_fuego", "piedra_agua", "piedra_trueno"],
}

STARTERS = ("bulbasaur", "charmander", "squirtle")
RIVAL_COUNTER = {"bulbasaur": "charmander", "charmander": "squirtle", "squirtle": "bulbasaur"}


def get_zone(zone_id: str) -> Zone:
    return ZONES[zone_id]


def trainers_in_zone(zone_id: str) -> List[TrainerDef]:
    return [t for t in TRAINERS.values() if t.zone == zone_id]


def npcs_in_zone(zone_id: str) -> List[NPC]:
    return [n for n in NPCS.values() if n.zone == zone_id]


def validate_world() -> List[str]:
    """Comprueba la consistencia de mapas, salidas y equipos (lista vacía = todo bien)."""
    from .species import SPECIES
    problems = []
    for zone in ZONES.values():
        if len(zone.grid) != MAP_H or any(len(row) != MAP_W for row in zone.grid):
            problems.append(f"{zone.id}: tamaño de mapa incorrecto")
        for y, row in enumerate(zone.grid):
            for x, ch in enumerate(row):
                if ch.isdigit() and ch not in zone.warps:
                    problems.append(f"{zone.id}: salida {ch} en {(x, y)} sin definir")
        for key, warp in zone.warps.items():
            if not any(key in row for row in zone.grid):
                problems.append(f"{zone.id}: salida {key} no aparece en el mapa")
            if warp.zone not in ZONES:
                problems.append(f"{zone.id}: destino inexistente {warp.zone}")
            else:
                dest = ZONES[warp.zone]
                if dest.tile(*warp.pos) in BLOCKED:
                    problems.append(f"{zone.id}->{warp.zone}: destino {warp.pos} bloqueado")
        for sp, lo, hi, w in zone.encounters:
            if sp not in SPECIES or lo > hi or w <= 0:
                problems.append(f"{zone.id}: encuentro inválido {sp}")
    for t in TRAINERS.values():
        zone = ZONES.get(t.zone)
        if zone is None:
            problems.append(f"{t.id}: zona inexistente")
            continue
        if t.role in ("trainer", "rival") and zone.tile(*t.pos) in BLOCKED:
            problems.append(f"{t.id}: está sobre una casilla bloqueada")
        for sp, lvl in t.team:
            if sp != "@rival" and sp not in SPECIES:
                problems.append(f"{t.id}: especie inexistente {sp}")
    for n in NPCS.values():
        if n.zone not in ZONES or ZONES[n.zone].tile(*n.pos) in BLOCKED:
            problems.append(f"{n.id}: posición inválida")
    return problems
