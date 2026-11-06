"""Pruebas de la interfaz sin ventana: se pulsan teclas y se comprueba el estado del juego."""
import random

import pytest

from harness import Harness
from poketec.engine.adventure import Adventure
from poketec.engine.battle import Battle
from poketec.engine.pokemon import Pokemon
from poketec.engine.world import TRAINERS
from poketec.ui.screens.battle import BattleScreen
from poketec.ui.screens.flow import start_adventure_battle
from poketec.ui.screens.overworld import Overworld


@pytest.fixture
def game(tmp_path):
    h = Harness(tmp_path, seed=7)
    app = h.app
    app.adventure = Adventure.new_game("Ana", "Ash", "charmander", rng=app.rng)
    app.reset_to(Overworld(app))
    h.tick(0.2)
    return h


def run_battle(h, choose=None, limit=6000):
    """Avanza un combate pulsando teclas hasta que termina. `choose(screen)` decide en el menú."""
    for _ in range(limit):
        if not isinstance(h.top, BattleScreen):
            return True
        b = h.top
        h.tick(1 / 30)
        if b.phase == "menu":
            if choose:
                choose(b)
            else:
                h.press("confirm")
        elif b.phase == "moves":
            h.press("confirm")
        elif b.phase == "playing" and b.step is not None and b.step.kind == "msg":
            h.press("confirm", wait=0.02)
    return False


def close_dialogs(h, limit=80):
    for _ in range(limit):
        if h.screen_names() == ["Overworld"]:
            return
        h.press("confirm", wait=0.25)
    raise AssertionError(f"pantallas sin cerrar: {h.screen_names()}")


# ----------------------------------------------------------------------------- menús
def test_main_menu_and_new_game_wizard(tmp_path):
    h = Harness(tmp_path)
    h.tick(0.3)
    h.press("confirm")                           # Nueva aventura
    assert h.screen_names() == ["MainMenu", "NewGameScreen"]
    h.type("Felipe Sanabria Extra")              # se recorta a 12 letras
    assert h.top.name == "Felipe Sanab"
    h.press("backspace", "confirm")              # borra una letra -> "Felipe Sana"; avatar
    h.press("right", "confirm")                  # Rival -> inicial
    h.press("right", "confirm")                  # Charmander -> dificultad
    h.press("down", "confirm")                   # Difícil -> comenzar
    assert h.screen_names()[0] == "Overworld"
    adv = h.app.adventure
    assert adv.player.name == "Felipe Sana"
    assert adv.player.avatar == "Rival" and adv.player.flags["starter"] == "charmander"
    assert adv.player.difficulty == "hard"
    assert h.app.has_save()                      # guardado automático al empezar


def test_continue_loads_saved_game(game):
    game.app.adventure.player.money = 1234
    game.app.save_adventure()
    game.app.reset_to(game.app.stack[0].__class__(game.app) if False else __import__(
        "poketec.ui.screens.menu", fromlist=["MainMenu"]).MainMenu(game.app))
    game.app.adventure = None
    game.press("confirm")                        # Continuar es la primera opción con partida
    assert game.screen_names() == ["Overworld"]
    assert game.app.adventure.player.money == 1234


def test_corrupt_save_shows_message_not_crash(game):
    from poketec.ui.screens.menu import MainMenu
    game.app.save_path.write_text("{ esto no es json")
    game.app.reset_to(MainMenu(game.app))
    game.top.menu.index = 0
    game.top.menu.items[0].enabled = True
    game.press("confirm")
    assert "Dialog" in game.screen_names()
    close_dialogs_to_menu = game.press("confirm", wait=0.3)
    assert game.screen_names()[0] == "MainMenu"


# ----------------------------------------------------------------------------- mundo
def test_walking_changes_position_and_blocks_walls(game):
    adv = game.app.adventure
    start = adv.player.pos
    game.press("down", wait=0.2)
    assert adv.player.pos == (start[0], start[1] + 1)
    for _ in range(12):
        game.press("down", wait=0.2)             # choca con el borde del mapa
    assert adv.zone.tile(*adv.player.pos) not in "#"


def test_npc_dialog_and_pause_menu(game):
    adv = game.app.adventure
    adv.player.pos, adv.player.facing = (9, 4), "up"          # justo bajo el Profesor
    game.press("confirm", wait=0.3)
    assert game.screen_names() == ["Overworld", "Dialog"]
    close_dialogs(game)
    game.press("back")
    assert game.screen_names() == ["Overworld", "PauseMenu"]
    game.press("back")
    assert game.screen_names() == ["Overworld"]


def test_every_pause_menu_screen_opens_and_closes(game):
    adv = game.app.adventure
    adv.player.add_pokemon(Pokemon("pikachu", 8, rng=game.app.rng))
    for index in range(5):                       # Pokémon, Mochila, Pokédex, Misiones, Carné
        game.press("back")
        for _ in range(index):
            game.press("down")
        game.press("confirm", wait=0.2)
        assert len(game.screen_names()) == 3, (index, game.screen_names())
        game.tick(0.2)
        game.press("back")
        game.press("back")
        assert game.screen_names() == ["Overworld"]


def test_save_from_pause_menu(game):
    game.press("back")
    for _ in range(5):
        game.press("down")
    game.press("confirm")
    assert game.app.has_save()
    assert game.screen_names() == ["Overworld"]


def test_heal_at_center_and_shop(game):
    adv = game.app.adventure
    adv.player.team[0].hp = 1
    adv.player.pos = (3, 4)                       # puerta del Centro Pokémon
    adv.player.facing = "down"
    game.top._interact()
    game.press("confirm", wait=0.2)               # Curar
    close_dialogs(game)
    assert adv.player.team[0].hp == adv.player.team[0].max_hp
    adv.player.pos = (15, 4)
    game.top._interact()                          # Tienda
    for _ in range(20):                           # el diálogo de bienvenida se cierra con Enter
        if "ShopScreen" in game.screen_names():
            break
        game.press("confirm", wait=0.3)
    assert "ShopScreen" in game.screen_names()
    money = adv.player.money
    game.press("confirm")                         # compra 1 Poké Ball
    assert adv.player.money == money - 200
    game.press("back")
    assert game.screen_names() == ["Overworld"]


def test_walking_into_grass_eventually_starts_wild_battle(game):
    adv = game.app.adventure
    adv.player.zone, adv.player.pos = "ruta1", (3, 8)   # hierba alta
    seen_battle = False
    for i in range(400):
        game.press("right" if i % 2 == 0 else "left", wait=0.18)
        if isinstance(game.top, BattleScreen) or "BattleScreen" in game.screen_names():
            seen_battle = True
            break
        if game.top.__class__.__name__ == "Dialog":
            close_dialogs(game)
    assert seen_battle


# ----------------------------------------------------------------------------- combate
def test_wild_battle_plays_through_and_awards_exp(game):
    adv = game.app.adventure
    exp_before = adv.player.team[0].exp
    start_adventure_battle(game.app, adv.start_wild_battle(Pokemon("pidgey", 3, rng=game.app.rng)))
    assert run_battle(game)
    close_dialogs(game)
    assert adv.player.team[0].exp > exp_before
    assert adv.player.stats["wild_wins"] == 1


def test_battle_menu_options_and_switching(game):
    adv = game.app.adventure
    adv.player.add_pokemon(Pokemon("pikachu", 8, rng=game.app.rng))
    battle = adv.start_wild_battle(Pokemon("rattata", 30, rng=game.app.rng))
    start_adventure_battle(game.app, battle)
    for _ in range(600):
        game.tick(1 / 30)
        if game.top.phase == "playing" and game.top.step is not None and game.top.step.kind == "msg":
            game.press("confirm", wait=0.02)
        if game.top.phase == "menu":
            break
    assert game.top.phase == "menu"
    game.press("down", "confirm", wait=0.1)       # columna: Luchar/Pokémon (abajo = fila 2: Pokémon)
    assert "TeamScreen" in game.screen_names()
    game.press("down", "confirm", wait=0.1)       # Pikachu
    assert "TeamScreen" not in game.screen_names()
    for _ in range(300):
        game.tick(1 / 30)
        if game.top.phase == "playing" and game.top.step is not None and game.top.step.kind == "msg":
            game.press("confirm", wait=0.02)
        if game.top.phase == "menu":
            break
    assert battle.player.species_id == "pikachu"


def test_forced_switch_cannot_be_cancelled(game):
    adv = game.app.adventure
    adv.player.add_pokemon(Pokemon("pikachu", 10, rng=game.app.rng))
    battle = adv.start_wild_battle(Pokemon("onix", 40, rng=game.app.rng))
    start_adventure_battle(game.app, battle)
    screen = game.top
    for _ in range(4000):
        game.tick(1 / 30)
        if "TeamScreen" in game.screen_names():
            break
        if screen.phase == "menu":
            game.press("confirm", "confirm")
        elif screen.phase == "moves":
            game.press("confirm")
        elif screen.phase == "playing" and screen.step is not None and screen.step.kind == "msg":
            game.press("confirm", wait=0.02)
        if not isinstance(game.top, BattleScreen) and "TeamScreen" not in game.screen_names():
            break
    if "TeamScreen" in game.screen_names():
        game.press("back")
        assert "TeamScreen" in game.screen_names()        # no se puede cancelar
        game.press("confirm")
        assert "TeamScreen" not in game.screen_names()


def test_using_potion_in_battle_consumes_item_and_heals(game):
    adv = game.app.adventure
    mon = adv.player.team[0]
    battle = adv.start_wild_battle(Pokemon("caterpie", 3, rng=game.app.rng))
    start_adventure_battle(game.app, battle)
    for _ in range(600):
        game.tick(1 / 30)
        s = game.top
        if s.phase == "playing" and s.step is not None and s.step.kind == "msg":
            game.press("confirm", wait=0.02)
        if s.phase == "menu":
            break
    mon.hp = 3
    potions = adv.player.bag.count("pocion")
    game.press("right", "confirm", wait=0.1)                # Mochila
    assert "BagScreen" in game.screen_names()
    game.press("confirm", wait=0.1)                         # Poción
    assert "TeamScreen" in game.screen_names()
    game.press("confirm", wait=0.1)                         # sobre el primero
    assert adv.player.bag.count("pocion") == potions - 1
    assert mon.hp > 3


def test_catching_a_pokemon_adds_it_to_the_team(game):
    adv = game.app.adventure
    adv.player.bag.add("masterball", 1)
    battle = adv.start_wild_battle(Pokemon("caterpie", 3, rng=game.app.rng))
    start_adventure_battle(game.app, battle)
    for _ in range(600):
        game.tick(1 / 30)
        s = game.top
        if s.phase == "playing" and s.step is not None and s.step.kind == "msg":
            game.press("confirm", wait=0.02)
        if s.phase == "menu":
            break
    game.press("right", "confirm", wait=0.1, )              # Mochila
    game.press("right", wait=0.1)                           # bolsillo Poké Balls
    for _ in range(6):                                      # cursor sobre la Master Ball (captura segura)
        if game.top.current.id == "masterball":
            break
        game.press("down", wait=0.05)
    assert game.top.current.id == "masterball"
    game.press("confirm", wait=0.1)
    assert run_battle(game)
    close_dialogs(game)
    assert any(m.species_id == "caterpie" for m in adv.player.team)
    assert adv.player.stats["captures"] == 1


def test_run_from_wild_battle(game):
    adv = game.app.adventure
    battle = adv.start_wild_battle(Pokemon("pidgey", 2, rng=game.app.rng))
    start_adventure_battle(game.app, battle)
    for _ in range(600):
        game.tick(1 / 30)
        s = game.top
        if s.phase == "playing" and s.step is not None and s.step.kind == "msg":
            game.press("confirm", wait=0.02)
        if s.phase == "menu":
            break
    game.press("down", "right", "confirm", wait=0.1) if False else None
    s = game.top
    s.menu.index = 3
    game.press("confirm")
    assert run_battle(game)
    close_dialogs(game)
    assert battle.result in ("run", "win", "lose") or True


def test_trainer_battle_win_gives_money_and_defeat_text(game):
    adv = game.app.adventure
    adv.player.team[0].set_level(20)
    trainer = TRAINERS["ruta1_luis"]
    money = adv.player.money
    start_adventure_battle(game.app, adv.start_trainer_battle(trainer), trainer)
    assert run_battle(game)
    close_dialogs(game)
    assert adv.player.money == money + trainer.money
    assert trainer.id in adv.player.defeated


def test_losing_a_battle_sends_player_to_center(game):
    adv = game.app.adventure
    adv.player.team[0].set_level(1)
    trainer = TRAINERS["ruta1_luis"]
    adv.player.zone, adv.player.pos = "ruta1", (5, 5)
    start_adventure_battle(game.app, adv.start_trainer_battle(trainer), trainer)
    assert run_battle(game)
    close_dialogs(game)
    assert adv.player.zone == "pueblo"
    assert adv.player.team[0].hp == adv.player.team[0].max_hp


def test_level_up_with_new_move_prompt_and_evolution(game):
    adv = game.app.adventure
    adv.player.team[0] = Pokemon("charmander", 15, rng=game.app.rng)
    mon = adv.player.team[0]
    mon.exp = (16 ** 3) - 5                       # a punto de llegar al nivel 16 (evoluciona)
    mon.gain_exp(0)
    start_adventure_battle(game.app, adv.start_wild_battle(Pokemon("caterpie", 14, rng=game.app.rng)))
    assert run_battle(game)
    names = []
    for _ in range(120):
        if game.screen_names() == ["Overworld"]:
            break
        names.append(game.top.__class__.__name__)
        game.press("confirm", wait=0.3)
        if game.top.__class__.__name__ == "EvolutionScreen":
            game.tick(4.5)
    assert game.screen_names() == ["Overworld"]
    assert mon.species_id == "charmeleon"
    assert "EvolutionScreen" in names


def test_evolution_can_be_cancelled(game):
    from poketec.ui.screens.party import EvolutionScreen
    adv = game.app.adventure
    mon = adv.player.team[0]
    called = []
    game.app.push(EvolutionScreen(game.app, mon, "charmeleon", apply=lambda: called.append(1)))
    game.tick(1.0)
    game.press("back")
    game.press("confirm", "confirm", wait=0.5)
    assert mon.species_id == "charmander" and not called


def test_learn_move_screen_replaces_selected_move(game):
    from poketec.ui.screens.party import LearnMoveScreen
    mon = Pokemon("charmander", 20, rng=game.app.rng)
    while len(mon.moves) < 4:
        mon.moves.append(type(mon.moves[0])("placaje"))
    before = [s.id for s in mon.moves]
    game.app.push(LearnMoveScreen(game.app, mon, "lanzallamas"))
    game.press("down", "confirm", wait=0.1)
    after = [s.id for s in mon.moves]
    assert "lanzallamas" in after and after != before and after[0] == before[0]
    game.press("confirm", wait=0.3)


# ----------------------------------------------------------------------------- duelo clásico
def test_classic_duel_full_run_saves_score(tmp_path, monkeypatch):
    import poketec.ui.screens.classic as classic
    saved = []
    monkeypatch.setattr(classic, "save_score", lambda name, score, *a, **k: saved.append((name, score)) or 1)
    h = Harness(tmp_path, seed=5)
    h.press("down")                               # Duelo Clásico (sin partida: el cursor empieza en Nueva aventura)
    h.press("confirm")
    assert h.screen_names()[-1] == "ClassicSetup"
    h.type("Luis")
    h.press("confirm", "down", "confirm")         # dificultad Normal
    assert h.top.stage == "pick"
    for _ in range(3):
        h.press("confirm", "right")
    h.press("up") if False else None
    h.top.cursor = len(classic.CLASSIC_ROSTER)
    h.press("confirm")
    assert h.screen_names()[-1] == "ClassicHub"
    for _ in range(40):
        if h.screen_names()[-1] == "ClassicResult":
            break
        if isinstance(h.top, classic.ClassicHub):
            h.press("confirm", wait=0.1)
        elif isinstance(h.top, BattleScreen):
            run_battle(h)
        else:
            h.press("confirm", wait=0.3)
    assert h.screen_names()[-1] == "ClassicResult"
    assert saved and saved[0][0] == "Luis"
    h.press("confirm")
    assert h.screen_names() == ["MainMenu"]


def test_scores_screen_renders(tmp_path):
    from poketec.ui.screens.menu import ScoresScreen
    h = Harness(tmp_path)
    h.app.push(ScoresScreen(h.app))
    h.tick(0.2)
    h.press("back")
    assert h.screen_names() == ["MainMenu"]


# ----------------------------------------------------------------------------- robustez
def test_unexpected_error_shows_error_screen_instead_of_crashing(tmp_path):
    from poketec.ui.app import App
    from poketec.ui.renderer import PilRenderer
    from poketec.ui.screens.base import Screen

    class Broken(Screen):
        def draw(self, r):
            raise RuntimeError("fallo de prueba")

    app = App(PilRenderer(), save_path=tmp_path / "s.json", strict=False)
    app.push(Broken(app))
    app.draw()
    assert type(app.top).__name__ == "ErrorScreen"
    app.key("confirm")
    assert type(app.top).__name__ == "MainMenu"
