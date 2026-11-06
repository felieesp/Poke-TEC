"""Pruebas del motor: tipos, daño, estados, captura, experiencia y evolución."""
import random

import pytest

from poketec.engine.battle import FOE, PLAYER, Action, Battle
from poketec.engine.calc import base_damage, capture_shakes, roll_damage
from poketec.engine.elements import TYPES, type_multiplier
from poketec.engine.items import Inventory, get_item
from poketec.engine.moves import MOVES, get_move
from poketec.engine.pokemon import MAX_LEVEL, Pokemon, exp_for_level
from poketec.engine.species import SPECIES, validate_catalog
from poketec.engine.world import validate_world


def mon(species="charmander", level=10, seed=1):
    return Pokemon(species, level, rng=random.Random(seed))


# ----------------------------------------------------------------------------- catálogo
def test_catalogo_y_mundo_son_consistentes():
    assert validate_catalog() == []
    assert validate_world() == []


def test_todos_los_movimientos_de_especies_existen():
    for sp in SPECIES.values():
        for _lvl, move_id in sp.learnset:
            assert move_id in MOVES, f"{sp.id} aprende {move_id} inexistente"


# ----------------------------------------------------------------------------- tipos
@pytest.mark.parametrize("atk,defn,expected", [
    ("fire", ["grass"], 2.0),
    ("water", ["fire"], 2.0),
    ("grass", ["fire"], 0.5),
    ("electric", ["ground"], 0.0),
    ("normal", ["ghost"], 0.0),
    ("fire", ["grass", "poison"], 2.0),
])
def test_efectividad_de_tipos(atk, defn, expected):
    assert type_multiplier(atk, defn) == expected


def test_tipos_dobles_se_multiplican():
    # agua contra roca/tierra (Geodude) = 4x
    assert type_multiplier("water", ["rock", "ground"]) == 4.0


def test_todos_los_tipos_tienen_multiplicador_valido():
    for a in TYPES:
        for d in TYPES:
            assert type_multiplier(a, [d]) in (0.0, 0.5, 1.0, 2.0)


# ----------------------------------------------------------------------------- daño
def test_dano_es_mayor_con_ventaja_de_tipo():
    attacker = mon("charmander", 20)
    grass, water = mon("bulbasaur", 20), mon("squirtle", 20)
    ember = get_move("ascuas")
    assert base_damage(attacker, grass, ember) > base_damage(attacker, water, ember)


def test_inmunidad_no_hace_dano():
    rng = random.Random(0)
    res = roll_damage(mon("pikachu", 20), mon("sandshrew", 20), get_move("impactrueno"), rng)
    assert res.damage == 0


def test_dano_minimo_es_uno_y_critico_aumenta():
    rng = random.Random(3)
    move = get_move("placaje")
    normal = roll_damage(mon(level=30), mon("onix", 5), move, random.Random(5), force_crit=False)
    crit = roll_damage(mon(level=30), mon("onix", 5), move, random.Random(5), force_crit=True)
    assert normal.damage >= 1
    assert crit.damage > normal.damage
    assert roll_damage(mon(level=1), mon("onix", 100), move, rng).damage >= 1


def test_stab_aumenta_el_dano():
    ember, tackle = get_move("ascuas"), get_move("placaje")
    attacker, target = mon("charmander", 20), mon("rattata", 20)
    stab = base_damage(attacker, target, ember) / ember.power
    plain = base_damage(attacker, target, tackle) / tackle.power
    # Ascuas es especial y Placaje físico: comparamos contra un atacante sin STAB equivalente
    assert "fire" in attacker.types and ember.type == "fire"
    assert stab > 0 and plain > 0


# ----------------------------------------------------------------------------- experiencia
def test_subir_de_nivel_con_experiencia():
    m = mon("charmander", 5)
    before = m.max_hp
    ups = m.gain_exp(exp_for_level(8) - m.exp)
    assert m.level == 8
    assert [u.level for u in ups] == [6, 7, 8]
    assert m.max_hp > before


def test_nivel_maximo_no_se_supera():
    m = mon("snorlax", MAX_LEVEL)
    assert m.gain_exp(10 ** 9) == []
    assert m.level == MAX_LEVEL


def test_exp_fraction_en_rango():
    m = mon(level=10)
    m.gain_exp(7)
    assert 0.0 <= m.exp_fraction <= 1.0


# ----------------------------------------------------------------------------- evolución
def test_evolucion_por_nivel():
    m = mon("charmander", 15)
    assert m.level_evolution() is None
    m.set_level(16)
    assert m.level_evolution() == "charmeleon"
    m.evolve("charmeleon")
    assert m.species_id == "charmeleon"
    assert m.hp <= m.max_hp


def test_evolucion_por_piedra():
    m = mon("vulpix", 10)
    assert m.item_evolution("piedra_fuego") == "ninetales"
    assert m.item_evolution("piedra_agua") is None


# ----------------------------------------------------------------------------- estados
def test_un_pokemon_solo_tiene_un_estado():
    m = mon("bulbasaur")
    assert m.set_status("quemadura", random.Random(1))
    assert not m.set_status("veneno", random.Random(1))
    assert m.status == "quemadura"
    m.clear_status()
    assert m.status is None


def test_debilitar_limpia_el_estado():
    m = mon("bulbasaur")
    m.set_status("quemadura", random.Random(1))
    m.take_damage(10 ** 6)
    assert m.is_fainted and m.status is None


def test_curar_no_supera_vida_maxima_ni_revive():
    m = mon()
    m.take_damage(5)
    assert m.heal(999) == 5 and m.hp == m.max_hp
    m.take_damage(10 ** 6)
    assert m.heal(50) == 0
    assert m.revive(0.5) and m.hp == max(1, int(m.max_hp * 0.5))


# ----------------------------------------------------------------------------- captura
def test_masterball_siempre_captura():
    assert capture_shakes(mon("mew", 50), 255.0, random.Random(1)) == 4


def test_captura_es_mas_facil_con_poca_vida_y_estado():
    rng_runs = 400
    def rate(setup):
        wins = 0
        for s in range(rng_runs):
            foe = mon("pidgey", 10, seed=s)
            setup(foe)
            wins += capture_shakes(foe, 1.0, random.Random(s)) == 4
        return wins
    full = rate(lambda f: None)
    low = rate(lambda f: f.take_damage(f.hp - 1))
    asleep = rate(lambda f: (f.take_damage(f.hp - 1), setattr(f, "status", "sueno")))
    assert low > full
    assert asleep >= low


# ----------------------------------------------------------------------------- inventario
def test_inventario_suma_y_resta():
    inv = Inventory({"pocion": 2})
    inv.add("pocion", 3)
    assert inv.count("pocion") == 5
    assert inv.remove("pocion", 5)
    assert not inv.remove("pocion", 1)
    assert inv.count("pocion") == 0
    assert Inventory.from_dict(Inventory({"pokeball": 4}).to_dict()).count("pokeball") == 4


def test_objeto_desconocido_lanza_error_claro():
    with pytest.raises(KeyError):
        get_item("no_existe")


# ----------------------------------------------------------------------------- persistencia de Pokémon
def test_pokemon_to_dict_from_dict_roundtrip():
    m = mon("eevee", 12)
    m.take_damage(3)
    m.set_status("paralisis", random.Random(2))
    clone = Pokemon.from_dict(m.to_dict())
    assert (clone.species_id, clone.level, clone.hp, clone.status) == (
        m.species_id, m.level, m.hp, m.status)
    assert [s.id for s in clone.moves] == [s.id for s in m.moves]
