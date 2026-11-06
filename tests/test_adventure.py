"""Pruebas del modo Aventura: mundo, encuentros, entrenadores, tienda y consecuencias."""
import random

import pytest

from poketec.engine.adventure import Adventure
from poketec.engine.battle import Action
from poketec.engine.pokemon import Pokemon
from poketec.engine.world import TRAINERS, ZONES


def new(starter="charmander", seed=1, **kw):
    return Adventure.new_game("Ana", "Ash", starter, rng=random.Random(seed), **kw)


def play(battle, limit=400):
    battle.start()
    for _ in range(limit):
        if battle.is_over:
            return
        if battle.state == "need_switch":
            battle.submit(Action.switch(battle.available_switches()[0]))
            continue
        mon = battle.player
        usable = [(s.move.power, i) for i, s in enumerate(mon.moves) if s.pp > 0 and s.move.is_damaging]
        idx = max(usable)[1] if usable else next((i for i, s in enumerate(mon.moves) if s.pp > 0), -1)
        battle.submit(Action.fight(idx))
    raise AssertionError("combate sin fin")


def test_nueva_partida_da_inicial_y_mision():
    adv = new("squirtle")
    assert [m.species_id for m in adv.player.team] == ["squirtle"]
    assert adv.player.team[0].level == 5
    assert "primer_pokemon" in adv.player.completed_quests
    assert "squirtle" in adv.player.caught


def test_inicial_invalido_se_rechaza():
    with pytest.raises(ValueError):
        Adventure.new_game("Ana", "Ash", "mew")


def test_movimiento_bloqueado_por_arboles_y_npcs():
    adv = new()
    adv.player.pos = (1, 1)
    assert adv.step("up").kind in ("blocked", "turned")       # borde de árboles
    assert adv.player.pos == (1, 1)
    npc = next(n for n in adv.npcs_here())
    adv.player.pos = (npc.pos[0], npc.pos[1] + 1)
    adv.step("up")
    assert adv.player.pos != npc.pos


def test_salida_entre_zonas_y_bloqueo_por_medalla():
    adv = new()
    adv.player.zone, adv.player.pos = "roca", (18, 5)
    result = adv.step("right")
    assert result.kind == "locked" and adv.player.zone == "roca"
    adv.player.medals.add("roca")
    adv.player.pos = (18, 5)
    result = adv.step("right")
    assert result.kind == "warp" and adv.player.zone == "costa"


def test_se_puede_recorrer_todo_el_mapa_conectado():
    """Cada zona es alcanzable desde la anterior caminando (sin atascos)."""
    from collections import deque
    for zone in ZONES.values():
        grid = zone.grid
        start = zone.default_pos
        seen, queue = {start}, deque([start])
        while queue:
            x, y = queue.popleft()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if (nx, ny) in seen or zone.tile(nx, ny) in "#whr":
                    continue
                seen.add((nx, ny))
                queue.append((nx, ny))
        for key in zone.warps:
            exits = [(x, y) for y, row in enumerate(grid) for x, ch in enumerate(row) if ch == key]
            assert any(e in seen for e in exits), f"{zone.id}: salida {key} inalcanzable"


def test_encuentros_salvajes_solo_en_hierba_alta():
    adv = new(seed=3)
    adv.player.zone = "ruta1"
    found = 0
    # hierba alta
    adv.player.pos = (2, 2)
    for _ in range(300):
        adv.player.pos = (3, 2)
        adv.player.facing = "down"
        res = adv.step("right")
        if res.kind == "wild":
            found += 1
            assert res.pokemon.species_id in {e[0] for e in adv.zone.encounters}
    assert found > 10
    # camino
    adv.player.pos = (2, 5)
    for _ in range(100):
        adv.player.pos = (4, 5)
        assert adv.step("right").kind != "wild"


def test_entrenador_te_ve_y_solo_una_vez():
    adv = new(seed=2)
    adv.player.pos = (17, 5)           # justo delante del rival (mira hacia arriba)
    # llegamos caminando para disparar la comprobación
    adv.player.pos = (16, 5)
    res = adv.step("right")
    assert res.kind == "trainer" and res.trainer.id == "rival_1"
    adv.player.defeated.add("rival_1")
    adv.player.pos = (16, 5)
    assert adv.step("right").kind != "trainer"


def test_el_rival_elige_el_inicial_contra_el_tuyo():
    for mine, theirs in (("charmander", "squirtle"), ("squirtle", "bulbasaur"), ("bulbasaur", "charmander")):
        adv = new(mine)
        team = adv.build_trainer_team(TRAINERS["rival_1"])
        assert team[0].species_id == theirs


def test_victoria_contra_entrenador_da_dinero_una_sola_vez():
    adv = new("charmander")
    adv.player.team[0].set_level(30)
    trainer = TRAINERS["ruta1_luis"]
    money = adv.player.money
    battle = adv.start_trainer_battle(trainer)
    play(battle)
    assert battle.result == "win"
    out = adv.finish_battle(battle, trainer)
    assert adv.player.money == money + trainer.money
    assert trainer.id in adv.player.defeated
    assert adv.player.stats["trainer_wins"] == 1
    assert out.lines
    with pytest.raises(ValueError):
        adv.start_trainer_battle(trainer)        # ya derrotado


def test_lider_da_medalla_y_objetos_y_desbloquea_mision():
    adv = new("squirtle")
    adv.player.team[0] = Pokemon("blastoise", 40, rng=random.Random(1))
    leader = TRAINERS["roca_pedro"]
    adv.player.zone = "roca"
    battle = adv.start_trainer_battle(leader)
    play(battle)
    out = adv.finish_battle(battle, leader)
    assert battle.result == "win" and out.medal == "roca"
    assert "roca" in adv.player.medals
    assert adv.player.bag.count("piedra_trueno") == 1
    assert "medalla_roca" in adv.player.completed_quests


def test_la_liga_exige_las_tres_medallas():
    adv = new()
    champion = TRAINERS["rival_liga"]
    ok, reason = adv.challenge_status(champion)
    assert not ok and "medallas" in reason
    adv.player.medals.update({"roca", "cascada", "ceniza"})
    assert adv.challenge_status(champion)[0]


def test_derrota_cura_cobra_y_teletransporta():
    adv = new("magikarp" if False else "charmander")
    adv.player.money = 1000
    adv.player.zone, adv.player.pos = "ruta1", (5, 5)
    for m in adv.player.team:
        m.set_level(2)
    boss = TRAINERS["roca_pedro"]
    adv.player.zone = "roca"
    battle = adv.start_trainer_battle(boss)
    play(battle)
    assert battle.result == "lose"
    out = adv.finish_battle(battle, boss)
    assert out.blackout and adv.player.money == 500
    assert adv.player.zone == "pueblo" and adv.player.pos == (4, 5)
    assert adv.player.alive_count == len(adv.player.team)
    assert adv.player.stats["blackouts"] == 1


def test_captura_en_combate_salvaje_agrega_al_equipo():
    adv = new(seed=5)
    adv.player.bag.add("masterball", 1)
    adv.player.zone = "ruta1"
    wild = adv.roll_wild_pokemon()
    battle = adv.start_wild_battle(wild)
    battle.start()
    battle.submit(Action.throw_ball("masterball"))
    out = adv.finish_battle(battle)
    assert battle.result == "caught"
    assert len(adv.player.team) == 2 and adv.player.stats["captures"] == 1
    assert wild.species_id in adv.player.caught
    assert any("añadido" in line for line in out.lines)


def test_pokemon_capturado_va_a_la_caja_con_equipo_lleno():
    adv = new(seed=5)
    adv.player.zone = "ruta1"
    for _ in range(5):
        adv.player.add_pokemon(adv.roll_wild_pokemon() or adv.player.team[0].clone())
    assert len(adv.player.team) == 6
    adv.player.bag.add("masterball", 1)
    battle = adv.start_wild_battle(adv.roll_wild_pokemon())
    battle.start()
    battle.submit(Action.throw_ball("masterball"))
    adv.finish_battle(battle)
    assert len(adv.player.box) >= 1


# ----------------------------------------------------------------------------- tienda y objetos
def test_comprar_y_vender():
    adv = new()
    adv.player.zone = "pueblo"
    money, potions = adv.player.money, adv.player.bag.count("pocion")
    ok, _ = adv.buy("pocion", 2)
    assert ok and adv.player.money == money - 600 and adv.player.bag.count("pocion") == potions + 2
    assert not adv.buy("masterball", 1)[0]             # no está en stock
    assert not adv.buy("pocion", 999)[0]               # sin dinero
    ok, _ = adv.sell("pocion", 1)
    assert ok and adv.player.money == money - 600 + 150
    assert not adv.sell("masterball", 1)[0]


def test_usar_objetos_fuera_de_combate():
    adv = new()
    mon = adv.player.team[0]
    mon.take_damage(5)
    assert adv.use_item("pocion", 0)[0] and mon.hp == mon.max_hp
    assert not adv.use_item("pocion", 0)[0]            # vida completa: no se gasta
    assert adv.player.bag.count("pocion") == 4


def test_caramelo_raro_sube_nivel_y_piedra_evoluciona():
    adv = new("charmander")
    adv.player.bag.add("caramelo_raro", 1)
    level = adv.player.team[0].level
    assert adv.use_item("caramelo_raro", 0)[0]
    assert adv.player.team[0].level == level + 1
    adv.player.add_pokemon(Pokemon("vulpix", 10))
    adv.player.bag.add("piedra_fuego", 1)
    assert adv.use_item("piedra_fuego", 1)[0]
    assert adv.player.team[1].species_id == "ninetales"
    assert adv.player.stats["evolutions"] == 1
    assert not adv.use_item("piedra_fuego", 0)[0]      # Charmander no reacciona


def test_evolucion_tras_combate_por_nivel():
    adv = new("charmander")
    mon = adv.player.team[0]
    mon.set_level(15)
    adv.player.zone = "ruta1"
    wild = adv.roll_wild_pokemon()
    wild.set_level(30)
    battle = adv.start_wild_battle(wild)
    play(battle)
    if battle.result == "win" and mon.level >= 16:
        pending = adv.pending_evolutions(battle)
        assert pending and pending[0][1] == "charmeleon"


def test_curar_en_centro_actualiza_punto_de_regreso():
    adv = new()
    adv.player.zone, adv.player.pos = "roca", (3, 4)
    adv.player.team[0].take_damage(3)
    adv.heal_at_center()
    assert adv.player.team[0].hp == adv.player.team[0].max_hp
    assert adv.player.last_heal == ("roca", 3, 4)


def test_edificios_se_detectan_al_pisar_la_puerta():
    adv = new()
    adv.player.zone, adv.player.pos = "roca", (9, 5)
    res = adv.step("up")
    assert res.kind == "building" and res.building == "G"
    assert adv.building_trainer("G").id == "roca_pedro"
