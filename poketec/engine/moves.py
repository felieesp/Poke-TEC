"""Catálogo de movimientos.

Efectos soportados (clave `effect`):
  status  = (estado, prob%)           estado alterado sobre el objetivo
  stat    = (objetivo, stat, etapas, prob%)   objetivo: "self" | "foe"
  heal    = fracción de PS máx. que se recupera el usuario
  recoil  = fracción del daño causado que recibe el usuario
  drain   = fracción del daño causado que cura el usuario
  crit    = True  -> índice de crítico alto
"""
from dataclasses import dataclass, field
from typing import Dict, Optional

PHYSICAL = "fisico"
SPECIAL = "especial"
STATUS = "estado"


@dataclass(frozen=True)
class Move:
    id: str
    name: str
    type: str
    category: str
    power: int
    accuracy: Optional[int]      # None = no falla nunca
    pp: int
    priority: int = 0
    effect: Dict = field(default_factory=dict)

    @property
    def is_damaging(self) -> bool:
        return self.category != STATUS and self.power > 0


MOVES: Dict[str, Move] = {}


def _m(id_, name, type_, cat, power, acc, pp, prio=0, **effect):
    MOVES[id_] = Move(id_, name, type_, cat, power, acc, pp, prio, effect)


# --- Normal -----------------------------------------------------------------
_m("placaje", "Placaje", "normal", PHYSICAL, 40, 100, 35)
_m("aranazo", "Arañazo", "normal", PHYSICAL, 40, 100, 35)
_m("ataque_rapido", "Ataque Rápido", "normal", PHYSICAL, 40, 100, 30, 1)
_m("mordisco", "Mordisco", "normal", PHYSICAL, 60, 100, 25)
_m("derribo", "Derribo", "normal", PHYSICAL, 90, 85, 20, recoil=0.25)
_m("golpe_cuerpo", "Golpe Cuerpo", "normal", PHYSICAL, 85, 100, 15, status=("paralisis", 30))
_m("hiperrayo", "Hiperrayo", "normal", SPECIAL, 120, 90, 5)
_m("rapidez", "Rapidez", "normal", SPECIAL, 60, None, 20)
_m("gruñido", "Gruñido", "normal", STATUS, 0, 100, 40, stat=("foe", "atk", -1, 100))
_m("latigo", "Látigo", "normal", STATUS, 0, 100, 30, stat=("foe", "def", -1, 100))
_m("fortaleza", "Fortaleza", "normal", STATUS, 0, None, 30, stat=("self", "def", 1, 100))
_m("danza_espada", "Danza Espada", "normal", STATUS, 0, None, 20, stat=("self", "atk", 2, 100))
_m("recuperacion", "Recuperación", "normal", STATUS, 0, None, 10, heal=0.5)
_m("salpicadura", "Salpicadura", "normal", STATUS, 0, None, 40)
_m("forcejeo", "Forcejeo", "normal", PHYSICAL, 50, None, 1, recoil=0.25)  # sin PP

# --- Fuego ------------------------------------------------------------------
_m("ascuas", "Ascuas", "fire", SPECIAL, 40, 100, 25, status=("quemadura", 10))
_m("lanzallamas", "Lanzallamas", "fire", SPECIAL, 90, 100, 15, status=("quemadura", 10))
_m("llamarada", "Llamarada", "fire", SPECIAL, 110, 85, 5, status=("quemadura", 10))

# --- Agua -------------------------------------------------------------------
_m("pistola_agua", "Pistola Agua", "water", SPECIAL, 40, 100, 25)
_m("burbuja", "Burbuja", "water", SPECIAL, 40, 100, 30, stat=("foe", "spe", -1, 10))
_m("surf", "Surf", "water", SPECIAL, 90, 100, 15)
_m("hidrobomba", "Hidrobomba", "water", SPECIAL, 110, 80, 5)

# --- Planta -----------------------------------------------------------------
_m("latigo_cepa", "Látigo Cepa", "grass", PHYSICAL, 45, 100, 25)
_m("hoja_afilada", "Hoja Afilada", "grass", PHYSICAL, 55, 95, 25, crit=True)
_m("absorber", "Absorber", "grass", SPECIAL, 20, 100, 25, drain=0.5)
_m("megaagotar", "Megaagotar", "grass", SPECIAL, 40, 100, 15, drain=0.5)
_m("rayo_solar", "Rayo Solar", "grass", SPECIAL, 110, 100, 5)
_m("somnifero", "Somnífero", "grass", STATUS, 0, 75, 15, status=("sueno", 100))
_m("paralizador", "Paralizador", "grass", STATUS, 0, 75, 30, status=("paralisis", 100))

# --- Eléctrico --------------------------------------------------------------
_m("impactrueno", "Impactrueno", "electric", SPECIAL, 40, 100, 30, status=("paralisis", 10))
_m("rayo", "Rayo", "electric", SPECIAL, 90, 100, 15, status=("paralisis", 10))
_m("trueno", "Trueno", "electric", SPECIAL, 110, 70, 10, status=("paralisis", 30))
_m("onda_trueno", "Onda Trueno", "electric", STATUS, 0, 90, 20, status=("paralisis", 100))

# --- Lucha ------------------------------------------------------------------
_m("golpe_karate", "Golpe Kárate", "fighting", PHYSICAL, 50, 100, 25, crit=True)
_m("submision", "Sumisión", "fighting", PHYSICAL, 80, 80, 20, recoil=0.25)
_m("patada_salto", "Patada Salto", "fighting", PHYSICAL, 100, 90, 10)

# --- Veneno -----------------------------------------------------------------
_m("picotazo_veneno", "Picotazo Veneno", "poison", PHYSICAL, 15, 100, 35, status=("veneno", 30))
_m("acido", "Ácido", "poison", SPECIAL, 40, 100, 30, stat=("foe", "spd", -1, 10))
_m("bomba_lodo", "Bomba Lodo", "poison", SPECIAL, 90, 100, 10, status=("veneno", 30))
_m("polvo_veneno", "Polvo Veneno", "poison", STATUS, 0, 75, 35, status=("veneno", 100))

# --- Tierra -----------------------------------------------------------------
_m("terremoto", "Terremoto", "ground", PHYSICAL, 100, 100, 10)
_m("disparo_lodo", "Disparo Lodo", "ground", SPECIAL, 55, 95, 15, stat=("foe", "spe", -1, 100))

# --- Volador ----------------------------------------------------------------
_m("picotazo", "Picotazo", "flying", PHYSICAL, 35, 100, 35)
_m("ataque_ala", "Ataque Ala", "flying", PHYSICAL, 60, 100, 35)
_m("tornado", "Tornado", "flying", SPECIAL, 40, 100, 35)

# --- Psíquico ---------------------------------------------------------------
_m("confusion", "Confusión", "psychic", SPECIAL, 50, 100, 25, stat=("foe", "spd", -1, 10))
_m("psiquico", "Psíquico", "psychic", SPECIAL, 90, 100, 10, stat=("foe", "spd", -1, 10))
_m("hipnosis", "Hipnosis", "psychic", STATUS, 0, 60, 20, status=("sueno", 100))

# --- Bicho ------------------------------------------------------------------
_m("picadura", "Picadura", "bug", PHYSICAL, 60, 100, 20)
_m("tijera_x", "Tijera X", "bug", PHYSICAL, 80, 100, 15)
_m("chupasangre", "Chupasangre", "bug", SPECIAL, 80, 100, 10, drain=0.5)
_m("disparo_demora", "Disparo Demora", "bug", STATUS, 0, 95, 40, stat=("foe", "spe", -1, 100))

# --- Roca -------------------------------------------------------------------
_m("lanzarrocas", "Lanzarrocas", "rock", PHYSICAL, 50, 90, 15)
_m("avalancha", "Avalancha", "rock", PHYSICAL, 75, 90, 10)

# --- Fantasma ---------------------------------------------------------------
_m("lenguetazo", "Lengüetazo", "ghost", PHYSICAL, 30, 100, 30, status=("paralisis", 30))
_m("bola_sombra", "Bola Sombra", "ghost", SPECIAL, 80, 100, 15, stat=("foe", "spd", -1, 20))

STRUGGLE = MOVES["forcejeo"]


def get_move(move_id: str) -> Move:
    try:
        return MOVES[move_id]
    except KeyError:
        raise KeyError(f"Movimiento desconocido: {move_id!r}") from None
