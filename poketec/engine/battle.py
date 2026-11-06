"""Motor de combate por turnos.

El motor NO conoce la interfaz: cada llamada a `submit()` resuelve un turno
completo y devuelve la lista de `Event` ocurridos (mensajes, daño, estados,
experiencia...). La GUI los reproduce con animaciones; las pruebas los
inspeccionan directamente.
"""
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .calc import capture_shakes, effective_stat, roll_damage
from .items import get_item
from .moves import MOVES, STRUGGLE, Move
from .pokemon import (MAX_LEVEL, STAT_NAMES_ES, STATUS_NAMES, Pokemon)
from .elements import effectiveness_text

PLAYER = "player"
FOE = "foe"


def other(side: str) -> str:
    return FOE if side == PLAYER else PLAYER


# ----------------------------------------------------------------------------- acciones
@dataclass
class Action:
    kind: str                      # fight | switch | item | ball | run
    index: int = 0                 # movimiento (-1 = Forcejeo) o miembro del equipo
    item_id: Optional[str] = None
    target: int = 0                # miembro del equipo objetivo de un objeto

    @staticmethod
    def fight(move_index: int) -> "Action":
        return Action("fight", move_index)

    @staticmethod
    def switch(team_index: int) -> "Action":
        return Action("switch", team_index)

    @staticmethod
    def use_item(item_id: str, target: int) -> "Action":
        return Action("item", item_id=item_id, target=target)

    @staticmethod
    def throw_ball(item_id: str) -> "Action":
        return Action("ball", item_id=item_id)

    @staticmethod
    def run() -> "Action":
        return Action("run")


@dataclass
class Event:
    kind: str
    data: dict = field(default_factory=dict)

    def __getitem__(self, key):
        return self.data[key]

    def get(self, key, default=None):
        return self.data.get(key, default)

    def __repr__(self) -> str:
        return f"Event({self.kind}, {self.data})"


# ----------------------------------------------------------------------------- combate
class Battle:
    def __init__(self, player_team: List[Pokemon], foe_team: List[Pokemon], *,
                 kind: str = "wild", foe_name: str = "", player_name: str = "Tú",
                 bag=None, foe_items: Optional[Dict[str, int]] = None, ai=None,
                 rng: Optional[random.Random] = None, award_exp: bool = True):
        if kind not in ("wild", "trainer"):
            raise ValueError("kind debe ser 'wild' o 'trainer'")
        if not any(not m.is_fainted for m in player_team):
            raise ValueError("El jugador no tiene Pokémon en condiciones de combatir")
        if not foe_team:
            raise ValueError("El rival no tiene Pokémon")
        from .ai import AI  # import tardío para evitar ciclo
        self.rng = rng or random.Random()
        self.player_team = player_team
        self.foe_team = foe_team
        self.kind = kind
        self.foe_name = foe_name
        self.player_name = player_name
        self.bag = bag
        self.foe_items = dict(foe_items or {})
        self.ai = ai or AI("normal", self.rng)
        self.award_exp = award_exp

        self.player_index = next(i for i, m in enumerate(player_team) if not m.is_fainted)
        self.foe_index = next((i for i, m in enumerate(foe_team) if not m.is_fainted), 0)
        self.state = "new"            # new | active | need_switch | ended
        self.result: Optional[str] = None   # win | lose | run | caught
        self.turn = 0
        self.run_attempts = 0
        self.caught: Optional[Pokemon] = None
        self.pending_learn: List[Tuple[Pokemon, str]] = []
        self.pending_evolve: List[Pokemon] = []
        self._participants: List[Pokemon] = []
        self._events: List[Event] = []

    # ---- acceso -----------------------------------------------------------------------------
    @property
    def player(self) -> Pokemon:
        return self.player_team[self.player_index]

    @property
    def foe(self) -> Pokemon:
        return self.foe_team[self.foe_index]

    def active(self, side: str) -> Pokemon:
        return self.player if side == PLAYER else self.foe

    def team(self, side: str) -> List[Pokemon]:
        return self.player_team if side == PLAYER else self.foe_team

    def available_switches(self, side: str = PLAYER) -> List[int]:
        current = self.player_index if side == PLAYER else self.foe_index
        return [i for i, m in enumerate(self.team(side)) if not m.is_fainted and i != current]

    def must_struggle(self, mon: Optional[Pokemon] = None) -> bool:
        mon = mon or self.player
        return all(s.pp <= 0 for s in mon.moves)

    @property
    def is_over(self) -> bool:
        return self.state == "ended"

    def _label(self, side: str) -> str:
        mon = self.active(side)
        if side == PLAYER:
            return mon.name
        return f"{mon.name} salvaje" if self.kind == "wild" else f"{mon.name} rival"

    # ---- eventos ----------------------------------------------------------------------------
    def _emit(self, kind: str, **data) -> None:
        self._events.append(Event(kind, data))

    def _msg(self, text: str) -> None:
        self._emit("msg", text=text)

    # ---- inicio -----------------------------------------------------------------------------
    def start(self) -> List[Event]:
        self._events = []
        self.state = "active"
        if self.kind == "wild":
            self._msg(f"¡Un {self.foe.name} salvaje apareció!")
        else:
            self._msg(f"¡{self.foe_name} te desafía a un combate!")
        self._send_out(FOE, announce=self.kind == "trainer")
        self._send_out(PLAYER, announce=True)
        self._participants = [self.player]
        return self._events

    def _send_out(self, side: str, announce: bool) -> None:
        mon = self.active(side)
        mon.reset_battle_state()
        if announce:
            if side == PLAYER:
                self._msg(f"¡Adelante, {mon.name}!")
            else:
                self._msg(f"{self.foe_name} envía a {mon.name}.")
        self._emit("send_out", side=side, mon=mon, hp=mon.hp, max_hp=mon.max_hp,
                   level=mon.level, status=mon.status)

    # ---- turno ------------------------------------------------------------------------------
    def submit(self, action: Action) -> List[Event]:
        """Resuelve la acción del jugador (y la del rival) y devuelve los eventos."""
        self._events = []
        if self.state in ("ended", "new"):
            return self._events

        if self.state == "need_switch":
            ok, error = self._validate(action)
            if action.kind != "switch" or not ok:
                self._msg(error or "Debes elegir un Pokémon para continuar.")
                return self._events
            self._do_switch(PLAYER, action.index, voluntary=False)
            self.state = "active"
            return self._events

        ok, error = self._validate(action)
        if not ok:
            self._msg(error)
            return self._events

        foe_action = self.ai.choose_action(self)
        self.turn += 1
        queue = self._build_queue(action, foe_action)
        for side, act, actor in queue:
            if self.state != "active":
                break
            if act.kind == "fight" and (self.active(side) is not actor or actor.is_fainted):
                continue
            self._execute(side, act)
            if self._resolve_faints():
                break
        if self.state == "active":
            self._end_of_turn()
        return self._events

    def _build_queue(self, player_action: Action, foe_action: Action):
        entries = []
        for side, act in ((PLAYER, player_action), (FOE, foe_action)):
            mon = self.active(side)
            if act.kind == "fight":
                move = self._move_for(mon, act.index)
                priority = move.priority
                speed = effective_stat(mon, "spe")
            else:
                priority, speed = 6, 0
            entries.append((priority, speed, self.rng.random(), side, act, mon))
        entries.sort(key=lambda e: (e[0], e[1], e[2]), reverse=True)
        return [(side, act, mon) for _, _, _, side, act, mon in entries]

    @staticmethod
    def _move_for(mon: Pokemon, index: int) -> Move:
        if index < 0 or index >= len(mon.moves):
            return STRUGGLE
        return mon.moves[index].move

    # ---- validación -------------------------------------------------------------------------
    def _validate(self, action: Action) -> Tuple[bool, str]:
        if action.kind == "fight":
            if action.index == -1:
                return (True, "") if self.must_struggle() else (False, "Aún tienes movimientos con PP.")
            if not 0 <= action.index < len(self.player.moves):
                return False, "Movimiento no válido."
            if self.player.moves[action.index].pp <= 0:
                return False, "¡No quedan PP para ese movimiento!"
            return True, ""
        if action.kind == "switch":
            if not 0 <= action.index < len(self.player_team):
                return False, "Pokémon no válido."
            target = self.player_team[action.index]
            if target.is_fainted:
                return False, f"¡{target.name} está debilitado!"
            if action.index == self.player_index:
                return False, f"¡{target.name} ya está en combate!"
            return True, ""
        if action.kind == "item":
            if self.bag is None:
                return False, "No puedes usar objetos en este combate."
            if not action.item_id or self.bag.count(action.item_id) <= 0:
                return False, "No te queda ese objeto."
            if not 0 <= action.target < len(self.player_team):
                return False, "Objetivo no válido."
            if not self._item_useful(get_item(action.item_id), self.player_team[action.target]):
                return False, "Eso no tendría ningún efecto."
            return True, ""
        if action.kind == "ball":
            if self.kind != "wild":
                return False, "¡No puedes robar los Pokémon de otro entrenador!"
            if self.bag is None or not action.item_id or self.bag.count(action.item_id) <= 0:
                return False, "No te quedan Poké Balls de ese tipo."
            if get_item(action.item_id).kind != "ball":
                return False, "Eso no es una Poké Ball."
            return True, ""
        if action.kind == "run":
            if self.kind != "wild":
                return False, "¡No puedes huir de un combate contra un entrenador!"
            return True, ""
        return False, "Acción desconocida."

    @staticmethod
    def _item_useful(item, mon: Pokemon) -> bool:
        if item.kind == "heal":
            return not mon.is_fainted and (mon.hp < mon.max_hp or (item.cures == "*" and mon.status is not None))
        if item.kind == "cure":
            return not mon.is_fainted and mon.status is not None and item.cures in ("*", mon.status)
        if item.kind == "revive":
            return mon.is_fainted
        if item.kind == "pp":
            return not mon.is_fainted and any(s.pp < s.max_pp for s in mon.moves)
        return False

    def can_use_item(self, item_id: str, team_index: int) -> bool:
        """¿Serviría este objeto sobre ese miembro del equipo? (lo usa la interfaz)"""
        if self.bag is None or not 0 <= team_index < len(self.player_team):
            return False
        return self._item_useful(get_item(item_id), self.player_team[team_index])

    # ---- ejecución --------------------------------------------------------------------------
    def _execute(self, side: str, act: Action) -> None:
        if act.kind == "fight":
            self._use_move(side, act.index)
        elif act.kind == "switch":
            self._do_switch(side, act.index, voluntary=True)
        elif act.kind == "item":
            self._use_item(side, act)
        elif act.kind == "ball":
            self._throw_ball(act.item_id)
        elif act.kind == "run":
            self._try_run()

    def _do_switch(self, side: str, index: int, voluntary: bool) -> None:
        old = self.active(side)
        if voluntary:
            if side == PLAYER:
                self._msg(f"¡Vuelve, {old.name}!")
            else:
                self._msg(f"{self.foe_name} retira a {old.name}.")
        old.reset_battle_state()
        self._emit("switch_out", side=side)
        if side == PLAYER:
            self.player_index = index
            self._send_out(PLAYER, announce=True)
            if self.player not in self._participants:
                self._participants.append(self.player)
        else:
            self.foe_index = index
            self._send_out(FOE, announce=True)
            self._participants = [self.player] if not self.player.is_fainted else []

    def _use_item(self, side: str, act: Action) -> None:
        item = get_item(act.item_id)
        if side == FOE:
            mon = self.foe
            self.foe_items[act.item_id] = self.foe_items.get(act.item_id, 0) - 1
            self._msg(f"{self.foe_name} usa {item.name} en {mon.name}.")
        else:
            mon = self.player_team[act.target]
            self.bag.remove(act.item_id)
            self._msg(f"Usaste {item.name} en {mon.name}.")
        is_active = mon is self.active(side)
        if item.kind == "heal":
            hp_before = mon.hp
            amount = mon.heal(int(item.power))
            if item.cures == "*":
                mon.clear_status()
                if is_active:
                    self._emit("status", side=side, status=None, mon=mon)
            self._emit("heal", side=side, amount=amount, hp_before=hp_before, hp=mon.hp,
                       max_hp=mon.max_hp, mon=mon, is_active=is_active)
            self._msg(f"¡{mon.name} recuperó {amount} PS!")
        elif item.kind == "cure":
            mon.clear_status()
            if is_active:
                self._emit("status", side=side, status=None, mon=mon)
            self._msg(f"¡{mon.name} se curó!")
        elif item.kind == "revive":
            hp_before = mon.hp
            mon.revive(item.power)
            self._emit("heal", side=side, amount=mon.hp, hp_before=hp_before, hp=mon.hp,
                       max_hp=mon.max_hp, mon=mon, is_active=is_active)
            self._msg(f"¡{mon.name} volvió a la vida!")
        elif item.kind == "pp":
            mon.restore_pp(int(item.power))
            self._msg(f"¡Los PP de {mon.name} fueron restaurados!")

    def _throw_ball(self, ball_id: str) -> None:
        ball = get_item(ball_id)
        self.bag.remove(ball_id)
        self._msg(f"¡{self.player_name} lanzó una {ball.name}!")
        foe = self.foe
        shakes = capture_shakes(foe, ball.power, self.rng)
        self._emit("ball", ball_id=ball_id, shakes=min(shakes, 3), caught=shakes >= 4)
        if shakes >= 4:
            self._msg(f"¡Has capturado a {foe.name}!")
            self.caught = foe
            self._end("caught")
        else:
            self._msg(["¡Oh, no! ¡El Pokémon se ha escapado!", "¡Qué lástima! ¡Casi lo atrapas!",
                       "¡Aaah! ¡Casi lo has logrado!", "¡Por muy poco!"][shakes])

    def _try_run(self) -> None:
        self.run_attempts += 1
        mine, theirs = effective_stat(self.player, "spe"), effective_stat(self.foe, "spe")
        chance = (mine * 128 / theirs + 30 * self.run_attempts) % 256
        if mine >= theirs or self.rng.randrange(256) < chance:
            self._msg("¡Escapaste sin problemas!")
            self._end("run")
        else:
            self._msg("¡No pudiste escapar!")

    # ---- movimientos ------------------------------------------------------------------------
    def _use_move(self, side: str, index: int) -> None:
        attacker, defender = self.active(side), self.active(other(side))
        # Estados que impiden actuar
        if attacker.status == "sueno":
            if attacker.sleep_turns <= 0:
                attacker.clear_status()
                self._emit("status", side=side, status=None, mon=attacker)
                self._msg(f"¡{attacker.name} se despertó!")
            else:
                attacker.sleep_turns -= 1
                self._msg(f"{self._label(side)} está profundamente dormido.")
                return
        if attacker.status == "paralisis" and self.rng.random() < 0.25:
            self._msg(f"¡{self._label(side)} está paralizado! ¡No se puede mover!")
            return

        if index < 0 or index >= len(attacker.moves):
            move = STRUGGLE
            self._msg(f"¡{self._label(side)} no tiene movimientos con PP!")
        else:
            slot = attacker.moves[index]
            slot.pp = max(0, slot.pp - 1)
            move = slot.move
        self._msg(f"¡{self._label(side)} usó {move.name}!")
        self._emit("move", side=side, move_id=move.id, move_type=move.type, category=move.category)

        if move.accuracy is not None and self.rng.randrange(100) >= move.accuracy:
            self._emit("miss", side=side)
            self._msg(f"¡El ataque de {attacker.name} falló!")
            return

        if not move.is_damaging:
            self._apply_status_move(side, attacker, defender, move)
            return

        result = roll_damage(attacker, defender, move, self.rng)
        if result.effectiveness == 0:
            self._msg(f"No afecta a {self._label(other(side))}...")
            return
        hp_before = defender.hp
        dealt = defender.take_damage(result.damage)
        self._emit("damage", side=other(side), amount=dealt, hp_before=hp_before,
                   hp=defender.hp, max_hp=defender.max_hp, effectiveness=result.effectiveness,
                   critical=result.critical, source="move", move_type=move.type)
        if result.critical:
            self._msg("¡Un golpe crítico!")
        text = effectiveness_text(result.effectiveness)
        if text:
            self._msg(text)

        eff = move.effect
        if eff.get("drain") and dealt > 0:
            self._heal_user(side, attacker, max(1, int(dealt * eff["drain"])),
                            f"¡{attacker.name} absorbió energía!")
        if eff.get("recoil") and dealt > 0:
            self._recoil(side, attacker, max(1, int(dealt * eff["recoil"])))
        if not defender.is_fainted:
            self._secondary_effects(side, attacker, defender, move)

    def _secondary_effects(self, side, attacker, defender, move) -> None:
        eff = move.effect
        if "status" in eff:
            status, chance = eff["status"]
            if self.rng.randrange(100) < chance:
                self._inflict_status(other(side), defender, status)
        if "stat" in eff:
            target, stat, stages, chance = eff["stat"]
            if self.rng.randrange(100) < chance:
                tside = side if target == "self" else other(side)
                self._change_stat(tside, stat, stages)

    def _apply_status_move(self, side, attacker, defender, move) -> None:
        eff = move.effect
        did_something = False
        if "heal" in eff:
            if attacker.hp >= attacker.max_hp:
                self._msg("¡Pero falló!")
                return
            self._heal_user(side, attacker, max(1, int(attacker.max_hp * eff["heal"])),
                            f"¡{attacker.name} recuperó salud!")
            did_something = True
        if "status" in eff:
            from .elements import type_multiplier
            if type_multiplier(move.type, defender.types) == 0:
                self._msg(f"No afecta a {self._label(other(side))}...")
                return
            if self._inflict_status(other(side), defender, eff["status"][0]):
                did_something = True
            else:
                self._msg("¡Pero falló!")
                return
        if "stat" in eff:
            target, stat, stages, _ = eff["stat"]
            tside = side if target == "self" else other(side)
            self._change_stat(tside, stat, stages)
            did_something = True
        if not did_something:
            self._msg("¡Pero no pasó nada!")

    def _inflict_status(self, side: str, mon: Pokemon, status: str) -> bool:
        if not mon.set_status(status, self.rng):
            return False
        self._emit("status", side=side, status=status, mon=mon)
        verbs = {"quemadura": "se quemó", "paralisis": "quedó paralizado",
                 "veneno": "fue envenenado", "sueno": "se durmió"}
        self._msg(f"¡{self._label(side)} {verbs[status]}!")
        return True

    def _change_stat(self, side: str, stat: str, stages: int) -> None:
        mon = self.active(side)
        current = mon.stages[stat]
        new = max(-6, min(6, current + stages))
        label = STAT_NAMES_ES[stat]
        if new == current:
            self._msg(f"¡El {label} de {self._label(side)} no puede {'subir' if stages > 0 else 'bajar'} más!")
            return
        mon.stages[stat] = new
        self._emit("stat", side=side, stat=stat, change=new - current)
        verb = "subió" if stages > 0 else "bajó"
        extra = " mucho" if abs(stages) >= 2 else ""
        self._msg(f"¡El {label} de {self._label(side)} {verb}{extra}!")

    def _heal_user(self, side: str, mon: Pokemon, amount: int, text: str) -> None:
        hp_before = mon.hp
        restored = mon.heal(amount)
        if restored:
            self._emit("heal", side=side, amount=restored, hp_before=hp_before, hp=mon.hp,
                       max_hp=mon.max_hp, mon=mon, is_active=True)
            self._msg(text)

    def _recoil(self, side: str, mon: Pokemon, amount: int) -> None:
        hp_before = mon.hp
        dealt = mon.take_damage(amount)
        self._emit("damage", side=side, amount=dealt, hp_before=hp_before, hp=mon.hp,
                   max_hp=mon.max_hp, effectiveness=1.0, critical=False, source="recoil",
                   move_type="normal")
        self._msg(f"¡{mon.name} se hirió por el retroceso!")

    # ---- fin de turno -----------------------------------------------------------------------
    def _end_of_turn(self) -> None:
        for side in (PLAYER, FOE):
            mon = self.active(side)
            if mon.is_fainted or mon.status not in ("quemadura", "veneno"):
                continue
            status = mon.status
            hp_before = mon.hp
            dealt = mon.take_damage(max(1, mon.max_hp // (16 if status == "quemadura" else 8)))
            self._emit("damage", side=side, amount=dealt, hp_before=hp_before, hp=mon.hp,
                       max_hp=mon.max_hp, effectiveness=1.0, critical=False, source="status",
                       move_type=status)
            cause = "la quemadura" if status == "quemadura" else "el veneno"
            self._msg(f"¡{self._label(side)} sufre por {cause}!")
            if self._resolve_faints():
                return

    # ---- debilitados, experiencia y fin -----------------------------------------------------
    def _resolve_faints(self) -> bool:
        """Gestiona Pokémon debilitados. Devuelve True si el turno debe detenerse."""
        if self.foe.is_fainted:
            self._on_foe_faint()
            if self.state == "ended":
                return True
        if self.player.is_fainted:
            self._emit("faint", side=PLAYER, mon=self.player)
            self._msg(f"¡{self.player.name} se debilitó!")
            if self.available_switches(PLAYER):
                self.state = "need_switch"
                self._emit("need_switch")
            else:
                self._end("lose")
            return True
        return False

    def _on_foe_faint(self) -> None:
        foe = self.foe
        self._emit("faint", side=FOE, mon=foe)
        self._msg(f"¡{self._label(FOE)} se debilitó!")
        if self.award_exp:
            self._award_exp(foe)
        replacements = self.available_switches(FOE)
        if not replacements:
            self._end("win")
            return
        index = self.ai.choose_replacement(self, replacements)
        self.foe_index = index
        self._send_out(FOE, announce=True)
        self._participants = [self.player] if not self.player.is_fainted else []

    def _award_exp(self, foe: Pokemon) -> None:
        alive = [m for m in self._participants if not m.is_fainted and m.level < MAX_LEVEL]
        if not alive:
            return
        total = foe.species.base_exp * foe.level / 7
        if self.kind == "trainer":
            total *= 1.5
        share = max(1, int(total / len(alive)))
        for mon in alive:
            level_before, frac_before = mon.level, mon.exp_fraction
            ups = mon.gain_exp(share)
            segments, cur_level, start = [], level_before, frac_before
            for up in ups:
                segments.append((cur_level, start, 1.0))
                cur_level, start = up.level, 0.0
            segments.append((cur_level, start, mon.exp_fraction))
            self._msg(f"¡{mon.name} ganó {share} puntos de experiencia!")
            self._emit("exp", mon=mon, amount=share, segments=segments, is_active=mon is self.player)
            for up in ups:
                self._emit("level_up", mon=mon, level=up.level, hp=mon.hp, max_hp=mon.max_hp,
                           is_active=mon is self.player)
                self._msg(f"¡{mon.name} subió al nivel {up.level}!")
                for move_id in up.learned:
                    self._msg(f"¡{mon.name} aprendió {MOVES[move_id].name}!")
                for move_id in up.pending:
                    self.pending_learn.append((mon, move_id))
            if mon.level_evolution() and mon not in self.pending_evolve:
                self.pending_evolve.append(mon)

    def _end(self, result: str) -> None:
        self.state = "ended"
        self.result = result
        for mon in self.player_team:
            mon.reset_battle_state()
        for mon in self.foe_team:
            mon.reset_battle_state()
        if result == "win":
            self._msg("¡Has ganado el combate!" if self.kind == "trainer" else "¡Has vencido!")
        elif result == "lose":
            self._msg("¡Te has quedado sin Pokémon en condiciones de luchar!")
        self._emit("end", result=result)
