"""Inteligencia artificial de los rivales.

Niveles:
  easy   - elige movimientos al azar, nunca cambia ni usa objetos.
  normal - prefiere el movimiento más dañino (con algo de ruido), a veces
           cambia de Pokémon ante una desventaja clara y se cura.
  hard   - maximiza daño esperado y remates (KO), explota debilidades de
           tipo, cambia estratégicamente y usa pociones con criterio.
"""
import random
from typing import List, Optional

from .calc import expected_damage
from .items import get_item
from .moves import STATUS
from .elements import type_multiplier

LEVELS = ("easy", "normal", "hard")


class AI:
    def __init__(self, level: str = "normal", rng: Optional[random.Random] = None):
        if level not in LEVELS:
            raise ValueError(f"Dificultad desconocida: {level!r}")
        self.level = level
        self.rng = rng or random.Random()
        self._last_switch_turn = -99

    # ---- decisión principal -----------------------------------------------------------------
    def choose_action(self, battle):
        from .battle import FOE, Action
        me, enemy = battle.foe, battle.player

        usable = [(i, s.move) for i, s in enumerate(me.moves) if s.pp > 0]
        if not usable:
            return Action.fight(-1)
        if self.level == "easy":
            return Action.fight(self.rng.choice(usable)[0])

        item = self._pick_heal_item(battle)
        if item:
            return Action.use_item(item, battle.foe_index)

        switch_to = self._pick_switch(battle, usable)
        if switch_to is not None:
            self._last_switch_turn = battle.turn
            return Action.switch(switch_to)

        if self.level == "normal" and self.rng.random() < 0.15:
            return Action.fight(self.rng.choice(usable)[0])
        noise = 12 if self.level == "normal" else 4
        scored = [(self.score_move(me, enemy, mv) + self.rng.uniform(-noise, noise), i)
                  for i, mv in usable]
        return Action.fight(max(scored)[1])

    def choose_replacement(self, battle, options: List[int]) -> int:
        if self.level == "easy" or len(options) == 1:
            return self.rng.choice(options)
        enemy = battle.player
        return max(options, key=lambda i: self.matchup_score(battle.foe_team[i], enemy))

    # ---- puntuación -------------------------------------------------------------------------
    def score_move(self, me, enemy, move) -> float:
        accuracy = (move.accuracy or 100) / 100
        if move.is_damaging:
            if type_multiplier(move.type, enemy.types) == 0:
                return -100.0
            damage = expected_damage(me, enemy, move)
            score = min(damage / max(1, enemy.hp), 1.0) * 100 * accuracy
            if damage >= enemy.hp and accuracy >= 0.9:
                score += 40                      # remate
            if move.effect.get("status") and enemy.status is None:
                score += 5
            return score
        effect = move.effect
        score = 0.0
        if "heal" in effect:
            score = 80 if me.hp_fraction < 0.4 else (5 if me.hp_fraction < 0.7 else -50)
        if "status" in effect:
            immune = type_multiplier(move.type, enemy.types) == 0
            usable = enemy.status is None and not immune and enemy.can_get_status(effect["status"][0])
            score = 55 * accuracy if usable and enemy.hp_fraction > 0.4 else -50
        if "stat" in effect:
            target, stat, stages, _ = effect["stat"]
            if target == "self":
                score = 30 if me.stages[stat] < 2 and me.hp_fraction > 0.5 else -20
            else:
                score = 20 if enemy.stages[stat] > -2 else -20
        return score

    def matchup_score(self, candidate, enemy) -> float:
        """Cuán bien le va a `candidate` contra `enemy` (mayor = mejor)."""
        damaging = [s.move for s in candidate.moves if s.pp > 0 and s.move.is_damaging]
        offense = max((expected_damage(candidate, enemy, mv) for mv in damaging), default=0.0)
        threat = max(type_multiplier(t, candidate.types) for t in enemy.types)
        return min(offense / max(1, enemy.hp), 2.0) * 50 - threat * 20 + candidate.hp_fraction * 20

    # ---- cambios y objetos ------------------------------------------------------------------
    def _pick_switch(self, battle, usable) -> Optional[int]:
        from .battle import FOE
        chance = {"normal": 0.25, "hard": 0.7}.get(self.level, 0)
        options = battle.available_switches(FOE)
        if not options or battle.turn - self._last_switch_turn <= 2:
            return None
        me, enemy = battle.foe, battle.player
        threat = max(type_multiplier(t, me.types) for t in enemy.types)
        my_best = max((type_multiplier(mv.type, enemy.types) for _, mv in usable if mv.is_damaging),
                      default=1.0)
        if not (threat >= 2 and my_best <= 1.0):
            return None
        best = max(options, key=lambda i: self.matchup_score(battle.foe_team[i], enemy))
        if self.matchup_score(battle.foe_team[best], enemy) <= self.matchup_score(me, enemy) + 10:
            return None
        return best if self.rng.random() < chance else None

    def _pick_heal_item(self, battle) -> Optional[str]:
        me = battle.foe
        if me.hp_fraction >= 0.3 or not battle.foe_items:
            return None
        if self.rng.random() > (0.5 if self.level == "normal" else 0.9):
            return None
        missing = me.max_hp - me.hp
        healers = [(get_item(i), n) for i, n in battle.foe_items.items()
                   if n > 0 and get_item(i).kind == "heal"]
        if not healers:
            return None
        healers.sort(key=lambda pair: pair[0].power)
        for item, _ in healers:                       # la más pequeña que alcance
            if item.power >= missing:
                return item.id
        return healers[-1][0].id
