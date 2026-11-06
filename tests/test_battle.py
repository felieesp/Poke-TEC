"""Pruebas del combate por turnos, la IA, el duelo clásico y la persistencia."""
import json
import random

import pytest

from poketec.engine.ai import AI
from poketec.engine.battle import FOE, PLAYER, Action, Battle
from poketec.engine.classic import TEAM_SIZE, ClassicDuel
from poketec.engine.items import Inventory
from poketec.engine.player import MAX_TEAM, Player
from poketec.engine.pokemon import Pokemon
from poketec.engine.quests import QUESTS, check_quests
from poketec.engine.save import SaveError, has_save, load_player, save_player
from poketec.engine.scores import load_scores, save_score


def make(species, level, seed=0):
    return Pokemon(species, level, rng=random.Random(seed))


def battle(player_team, foe_team, **kw):
    kw.setdefault("rng", random.Random(7))
    kw.setdefault("ai", AI("easy", random.Random(1)))
    b = Battle(player_team, foe_team, **kw)
    b.start()
    return b


def strongest(mon):
    """Índice del movimiento ofensivo más potente que aún tiene PP (-1 = Forcejeo)."""
    usable = [(slot.move.power, i) for i, slot in enumerate(mon.moves)
              if slot.pp > 0 and slot.move.is_damaging]
    if usable:
        return max(usable)[1]
    with_pp = [i for i, slot in enumerate(mon.moves) if slot.pp > 0]
    return with_pp[0] if with_pp else -1


def play_out(b, limit=300):
    """Juega con el mejor ataque hasta que acabe el combate (con tope de seguridad)."""
    for _ in range(limit):
        if b.is_over:
            return
        if b.state == "need_switch":
            b.submit(Action.switch(b.available_switches()[0]))
        else:
            b.submit(Action.fight(strongest(b.player)))
    raise AssertionError("el combate no terminó en el límite de turnos")


def kinds(events):
    return [e.kind for e in events]


# ----------------------------------------------------------------------------- flujo básico
def test_combate_requiere_pokemon_vivos():
    dead = make("pidgey", 5)
    dead.take_damage(10 ** 6)
    with pytest.raises(ValueError):
        Battle([dead], [make("rattata", 3)])
    with pytest.raises(ValueError):
        Battle([make("pidgey", 5)], [])


def test_un_turno_produce_eventos_y_avanza():
    b = battle([make("charmander", 12)], [make("pidgey", 5)])
    events = b.submit(Action.fight(0))
    assert b.turn == 1
    assert "move" in kinds(events)


def test_combate_termina_con_victoria_y_da_experiencia():
    b = battle([make("charmander", 30)], [make("caterpie", 3)])
    exp_before = b.player.exp
    play_out(b)
    assert b.is_over and b.result == "win"
    assert b.player.exp > exp_before


def test_derrota_cuando_no_quedan_pokemon():
    weak = make("magikarp", 3)
    b = battle([weak], [make("onix", 40)])
    play_out(b)
    assert b.result == "lose"


def test_debilitado_obliga_a_cambiar_y_se_puede_continuar():
    first, second = make("magikarp", 3), make("charmander", 20)
    b = battle([first, second], [make("onix", 40)])
    for _ in range(30):
        if b.state != "active":
            break
        b.submit(Action.fight(strongest(b.player)))
    assert b.state == "need_switch"
    # elegir un debilitado es inválido
    msg = b.submit(Action.switch(0))
    assert b.state == "need_switch" and "msg" in kinds(msg)
    b.submit(Action.switch(1))
    assert b.state == "active" and b.player is second


def test_cambio_voluntario_gasta_el_turno():
    a, c = make("charmander", 10), make("squirtle", 10)
    b = battle([a, c], [make("rattata", 5)])
    b.submit(Action.switch(1))
    assert b.player is c
    assert b.submit(Action.switch(1)) and b.player is c   # ya está en combate: no cambia


def test_no_se_puede_huir_de_un_entrenador_ni_capturar():
    b = battle([make("charmander", 10)], [make("rattata", 5)], kind="trainer", foe_name="Luis",
               bag=Inventory({"pokeball": 3}))
    run = b.submit(Action.run())
    assert not b.is_over and run
    turns = b.turn
    b.submit(Action.throw_ball("pokeball"))
    assert b.turn == turns and b.caught is None


def test_pp_se_consumen_y_forcejeo_sin_pp():
    mon = make("charmander", 10)
    for slot in mon.moves:
        slot.pp = 0
    b = battle([mon], [make("rattata", 5)])
    assert b.must_struggle()
    assert b.submit(Action.fight(0))  # sin PP: inválido, mensaje
    b.submit(Action.fight(-1))
    assert b.turn >= 1


def test_pp_decrece_al_usar_movimiento():
    mon = make("charmander", 10)
    b = battle([mon], [make("caterpie", 3)])
    before = mon.moves[0].pp
    b.submit(Action.fight(0))
    assert mon.moves[0].pp == before - 1


# ----------------------------------------------------------------------------- objetos
def test_pocion_cura_y_se_consume():
    mon = make("charmander", 20)
    bag = Inventory({"pocion": 2})
    b = battle([mon], [make("caterpie", 3)], bag=bag)
    mon.take_damage(15)
    hp = mon.hp
    b.submit(Action.use_item("pocion", 0))
    assert bag.count("pocion") == 1
    assert mon.hp > hp


def test_objeto_inutil_no_se_gasta():
    mon = make("charmander", 20)
    bag = Inventory({"pocion": 2})
    b = battle([mon], [make("caterpie", 3)], bag=bag)
    turns = b.turn
    b.submit(Action.use_item("pocion", 0))     # vida completa
    assert bag.count("pocion") == 2 and b.turn == turns


def test_revivir_a_un_debilitado_del_equipo():
    a, c = make("charmander", 20), make("squirtle", 20)
    c.take_damage(10 ** 6)
    bag = Inventory({"revivir": 1})
    b = battle([a, c], [make("caterpie", 3)], bag=bag)
    b.submit(Action.use_item("revivir", 1))
    assert not c.is_fainted and bag.count("revivir") == 0


def test_captura_con_masterball_termina_el_combate():
    bag = Inventory({"masterball": 1})
    foe = make("mew", 30)
    b = battle([make("charmander", 20)], [foe], bag=bag)
    events = b.submit(Action.throw_ball("masterball"))
    assert b.result == "caught" and b.caught is foe
    assert any(e.kind == "ball" and e["caught"] for e in events)
    assert bag.count("masterball") == 0


def test_huir_de_un_salvaje_eventualmente_funciona():
    b = battle([make("charmander", 50)], [make("rattata", 2)])
    for _ in range(30):
        if b.is_over:
            break
        b.submit(Action.run())
    assert b.result == "run"


# ----------------------------------------------------------------------------- estados y efectos
def test_quemadura_y_veneno_hacen_dano_al_final_del_turno():
    for status in ("quemadura", "veneno"):
        mon = make("pidgey", 30)
        b = battle([mon], [make("snorlax", 50)])
        mon.set_status(status, random.Random(1))
        hp = mon.hp
        b._events = []
        b._end_of_turn()
        damages = [e for e in b._events if e.kind == "damage" and e["side"] == PLAYER]
        assert damages and mon.hp < hp, f"{status} no causó daño"


def test_paralisis_reduce_velocidad_efectiva():
    from poketec.engine.calc import effective_stat
    mon = make("pikachu", 20)
    normal = effective_stat(mon, "spe")
    mon.status = "paralisis"
    assert effective_stat(mon, "spe") < normal


def test_dormido_pierde_turnos_y_despierta():
    mon = make("charmander", 20)
    b = battle([mon], [make("onix", 3)])
    mon.set_status("sueno", random.Random(1))
    for _ in range(6):
        b.submit(Action.fight(strongest(mon)))
        if mon.status is None:
            break
    assert mon.status is None


# ----------------------------------------------------------------------------- IA
def test_ia_elige_movimiento_super_eficaz():
    ai = AI("hard", random.Random(3))
    foe = make("charmander", 30)
    target = make("bulbasaur", 30)
    b = Battle([target], [foe], ai=ai, rng=random.Random(2))
    b.start()
    action = ai.choose_action(b)
    assert action.kind == "fight"
    move = foe.moves[action.index].move
    assert move.type == "fire" or not move.is_damaging


def test_ia_nunca_usa_movimiento_inmune():
    ai = AI("hard", random.Random(3))
    foe = make("pikachu", 30)
    b = Battle([make("sandshrew", 30)], [foe], ai=ai, rng=random.Random(2))
    b.start()
    for _ in range(25):
        a = ai.choose_action(b)
        mv = foe.moves[a.index].move if a.kind == "fight" and a.index >= 0 else None
        assert mv is None or mv.type != "electric" or not mv.is_damaging


def test_ia_dificultades_validas_y_error_si_no():
    for level in ("easy", "normal", "hard"):
        AI(level)
    with pytest.raises(ValueError):
        AI("imposible")


def test_ia_cambia_ante_desventaja_clara_en_dificil():
    switched = 0
    for seed in range(40):
        ai = AI("hard", random.Random(seed))
        foe_team = [make("bulbasaur", 30), make("charmander", 30)]
        b = Battle([make("squirtle", 30)], foe_team, ai=ai, rng=random.Random(seed))
        b.start()
        b.turn = 5
        # bulbasaur enemigo (planta) vs rival agua: no hay desventaja; usamos eléctrico
    for seed in range(60):
        ai = AI("hard", random.Random(seed))
        foe_team = [make("squirtle", 30), make("bulbasaur", 30)]
        b = Battle([make("pikachu", 30)], foe_team, ai=ai, rng=random.Random(seed))
        b.start()
        b.turn = 5
        if ai.choose_action(b).kind == "switch":
            switched += 1
    assert switched > 0


@pytest.mark.parametrize("level", ["easy", "normal", "hard"])
def test_simulacion_completa_no_falla(level):
    for seed in range(15):
        rng = random.Random(seed)
        b = Battle([make("charmander", 25, seed), make("squirtle", 25, seed)],
                   [make("bulbasaur", 25, seed), make("pidgey", 25, seed)],
                   kind="trainer", foe_name="Rival", ai=AI(level, rng), rng=rng,
                   bag=Inventory({"pocion": 3}), foe_items={"pocion": 2})
        b.start()
        for _ in range(300):
            if b.is_over:
                break
            if b.state == "need_switch":
                b.submit(Action.switch(b.available_switches()[0]))
            else:
                b.submit(Action.fight(strongest(b.player)))
        assert b.is_over, f"combate infinito con IA {level}, semilla {seed}"
        assert b.result in ("win", "lose")


# ----------------------------------------------------------------------------- duelo clásico
def test_duelo_clasico_exige_tres_distintos():
    with pytest.raises(ValueError):
        ClassicDuel("Ana", ["pikachu", "pikachu", "eevee"])
    with pytest.raises(ValueError):
        ClassicDuel("Ana", ["pikachu", "eevee"])


def test_duelo_clasico_victoria_captura_al_rival():
    duel = ClassicDuel("Ana", ["blastoise", "mew", "snorlax"], rng=random.Random(4))
    battle_ = duel.start_round(1)
    battle_.start()
    play_out(battle_)
    outcome = duel.finish_round(battle_)
    if battle_.result == "win":
        assert outcome == "captured" and len(duel.player_team) == TEAM_SIZE + 1 and duel.score == 1
        assert len(duel.enemy_team) == TEAM_SIZE - 1
    else:
        assert outcome == "lost" and len(duel.player_team) == TEAM_SIZE - 1


def test_duelo_clasico_termina():
    duel = ClassicDuel("Ana", ["blastoise", "mew", "snorlax"], rng=random.Random(11))
    for _ in range(100):
        if duel.is_over:
            break
        b = duel.start_round(0)
        b.start()
        play_out(b)
        duel.finish_round(b)
    assert duel.is_over


# ----------------------------------------------------------------------------- jugador, guardado, puntajes
def test_equipo_maximo_seis_y_el_resto_va_a_la_caja():
    p = Player("Ana")
    results = [p.add_pokemon(make("rattata", 3, s)) for s in range(8)]
    assert len(p.team) == MAX_TEAM and len(p.box) == 2
    assert results.count("team") == 6 and results.count("box") == 2
    assert "rattata" in p.caught


def test_guardar_y_cargar_conserva_el_progreso(tmp_path):
    p = Player("Ana")
    p.add_pokemon(make("charmander", 9))
    p.medals.add("roca")
    p.money = 1234
    p.bag.add("superball", 3)
    p.zone, p.pos = "ruta1", (4, 5)
    path = tmp_path / "s.json"
    save_player(p, path)
    q = load_player(path)
    assert (q.name, q.money, q.zone, tuple(q.pos)) == ("Ana", 1234, "ruta1", (4, 5))
    assert q.medals == {"roca"} and q.bag.count("superball") == 3
    assert q.team[0].species_id == "charmander" and q.team[0].level == 9


def test_cargar_sin_partida_o_corrupta_da_error_claro(tmp_path):
    with pytest.raises(SaveError):
        load_player(tmp_path / "nada.json")
    bad = tmp_path / "bad.json"
    bad.write_text("{no es json")
    with pytest.raises(SaveError):
        load_player(bad)
    assert not has_save(tmp_path / "nada.json")


def test_carga_usa_copia_de_respaldo_si_el_archivo_se_danya(tmp_path):
    p = Player("Ana")
    p.add_pokemon(make("eevee", 5))
    path = tmp_path / "s.json"
    save_player(p, path)
    p.money = 999
    save_player(p, path)            # la primera versión queda como .bak
    path.write_text("basura")
    q = load_player(path)
    assert q.name == "Ana"


def test_ranking_top10_ordenado_y_resistente(tmp_path):
    path = tmp_path / "scores.json"
    for i in range(12):
        save_score(f"J{i}", i, path=path)
    scores = load_scores(path)
    assert len(scores) == 10 and scores[0]["score"] == 11
    assert [s["score"] for s in scores] == sorted((s["score"] for s in scores), reverse=True)
    path.write_text("[{\"name\": \"x\"}, 5, null]")
    assert load_scores(path) == []
    path.write_text("roto")
    assert load_scores(path) == []


def test_ranking_acepta_el_formato_del_juego_original(tmp_path):
    path = tmp_path / "scores.json"
    path.write_text(json.dumps([{"name": "Felipe", "score": 8}]))
    assert load_scores(path)[0]["name"] == "Felipe"


# ----------------------------------------------------------------------------- misiones
def test_misiones_se_completan_una_vez_y_dan_premio():
    p = Player("Ana")
    p.add_pokemon(make("charmander", 5))
    p.stats["captures"] = 100
    p.stats["trainer_wins"] = 100
    p.medals.update({"roca", "cascada", "ceniza"})
    money = p.money
    done = check_quests(p)
    assert done and p.money > money
    assert check_quests(p) == []
    assert len(p.completed_quests) <= len(QUESTS)
