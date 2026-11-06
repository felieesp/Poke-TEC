"""Secuencias que enlazan varias pantallas: combate de aventura y sus consecuencias."""
from typing import Callable, Optional

from ...engine.battle import Battle
from ...engine.save import SaveError
from ...engine.world import TrainerDef
from .battle import BattleScreen
from .dialogs import Dialog, run_sequence
from .party import EvolutionScreen, LearnMoveScreen


def autosave(app) -> bool:
    """Guarda en silencio. Devuelve False si no se pudo (el juego sigue funcionando)."""
    try:
        app.save_adventure()
        return True
    except (SaveError, OSError):
        return False


def start_adventure_battle(app, battle: Battle, trainer: Optional[TrainerDef] = None,
                           then: Optional[Callable[[], None]] = None) -> None:
    adv = app.adventure
    avatar = "Rival" if trainer and trainer.role in ("rival", "champion") else None
    color = trainer.color if trainer else "#c0392b"

    def finished(b: Battle) -> None:
        after_battle(app, b, trainer, then)

    app.push(BattleScreen(app, battle, theme_id=adv.zone.theme, foe_avatar=avatar, foe_color=color,
                          player_avatar=adv.player.avatar, on_done=finished))


def after_battle(app, battle: Battle, trainer: Optional[TrainerDef], then: Optional[Callable[[], None]]) -> None:
    """Movimientos nuevos -> evoluciones -> premios/derrota -> guardado automático."""
    adv = app.adventure
    state = {"outcome": None}
    steps = []

    for mon, move_id in list(battle.pending_learn):
        if move_id in mon.pending_moves and not mon.knows(move_id):
            steps.append(lambda nxt, m=mon, mv=move_id: app.push(LearnMoveScreen(app, m, mv, on_done=nxt)))

    for mon, target in adv.pending_evolutions(battle):
        steps.append(lambda nxt, m=mon, t=target: app.push(
            EvolutionScreen(app, m, t, apply=lambda: adv.evolve(m, t), on_done=nxt)))

    def outcome_step(nxt) -> None:
        out = adv.finish_battle(battle, trainer)
        state["outcome"] = out
        lines = []
        if battle.result == "win" and trainer and trainer.defeat:
            lines.append(trainer.defeat)
        speaker = trainer.name if trainer and battle.result == "win" else ""
        if lines and out.lines:
            app.push(Dialog(app, lines, speaker=speaker,
                            on_done=lambda: app.push(Dialog(app, out.lines, on_done=nxt))))
        elif lines or out.lines:
            app.push(Dialog(app, lines or out.lines, speaker=speaker, on_done=nxt))
        else:
            nxt()

    steps.append(outcome_step)

    def champion_step(nxt) -> None:
        out = state["outcome"]
        if out and out.champion:
            app.push(Dialog(app, ["¡Has derrotado a la Liga Poke-TEC!",
                                  f"¡{adv.player.name} es el nuevo Campeón!",
                                  "Gracias por jugar. Puedes seguir explorando y completando misiones."],
                            on_done=nxt))
        else:
            nxt()

    steps.append(champion_step)

    def final() -> None:
        autosave(app)
        if then:
            then()

    run_sequence(steps, final)
