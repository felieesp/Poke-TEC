"""Lógica del modo Aventura, independiente de la interfaz.

`Adventure` envuelve a un `Player` y resuelve todo lo que ocurre en el mundo:
movimiento, salidas entre zonas, encuentros salvajes, entrenadores que te ven,
edificios (Centro Pokémon, Tienda, Gimnasio, Liga), tienda, objetos fuera de
combate, evoluciones y las consecuencias de ganar o perder un combate.

La GUI solo llama a estos métodos y dibuja el resultado; las pruebas
automáticas hacen lo mismo sin ninguna ventana.
"""
import random
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .ai import AI
from .battle import Battle
from .items import get_item
from .player import MEDALS, Player
from .pokemon import Pokemon
from .quests import Quest, check_quests
from .save import save_player
from .species import SPECIES
from .world import (BLOCKED, DIRECTIONS, NPC, RIVAL_COUNTER, SHOP_STOCK, STARTERS, TrainerDef, Zone,
                    get_zone, npcs_in_zone, trainers_in_zone)

STARTER_LEVEL = 5
SELL_RATIO = 0.5
BLACKOUT_MONEY_LOSS = 0.5
AI_STEP_UP = {"easy": "normal", "normal": "hard", "hard": "hard"}


# ----------------------------------------------------------------------------- resultados
@dataclass
class StepResult:
    """Qué pasó al intentar dar un paso.

    kind: blocked | moved | warp | locked | wild | trainer | building | turned
    """
    kind: str
    text: str = ""
    pokemon: Optional[Pokemon] = None       # encuentro salvaje
    trainer: Optional[TrainerDef] = None    # entrenador que te vio
    building: str = ""                      # C | M | G | L
    new_zone: bool = False                  # cambió de mapa


@dataclass
class BattleOutcome:
    """Consecuencias de un combate ya terminado."""
    lines: List[str] = field(default_factory=list)
    quests: List[Quest] = field(default_factory=list)
    blackout: bool = False
    medal: Optional[str] = None
    champion: bool = False


# ----------------------------------------------------------------------------- aventura
class Adventure:
    def __init__(self, player: Player, rng: Optional[random.Random] = None):
        self.player = player
        self.rng = rng or random.Random()

    # ---- creación ---------------------------------------------------------------------------
    @classmethod
    def new_game(cls, name: str, avatar: str, starter_id: str, difficulty: str = "normal",
                 rng: Optional[random.Random] = None) -> "Adventure":
        if starter_id not in STARTERS:
            raise ValueError(f"Pokémon inicial no válido: {starter_id!r}")
        rng = rng or random.Random()
        player = Player((name or "Entrenador").strip()[:12] or "Entrenador", avatar)
        player.difficulty = difficulty
        player.flags["starter"] = starter_id
        player.add_pokemon(Pokemon(starter_id, STARTER_LEVEL, rng=rng))
        check_quests(player)
        return cls(player, rng)

    # ---- acceso al mundo --------------------------------------------------------------------
    @property
    def zone(self) -> Zone:
        return get_zone(self.player.zone)

    @property
    def starter(self) -> str:
        return self.player.flags.get("starter", STARTERS[0])

    def trainers_here(self) -> List[TrainerDef]:
        return trainers_in_zone(self.player.zone)

    def npcs_here(self) -> List[NPC]:
        return npcs_in_zone(self.player.zone)

    def occupant_at(self, x: int, y: int):
        """NPC o entrenador que ocupa la casilla, si lo hay."""
        for npc in self.npcs_here():
            if npc.pos == (x, y):
                return npc
        for trainer in self.trainers_here():
            if trainer.pos == (x, y):
                return trainer
        return None

    def is_walkable(self, x: int, y: int) -> bool:
        return self.zone.tile(x, y) not in BLOCKED and self.occupant_at(x, y) is None

    # ---- movimiento -------------------------------------------------------------------------
    def step(self, direction: str) -> StepResult:
        if direction not in DIRECTIONS:
            raise ValueError(f"Dirección desconocida: {direction!r}")
        player = self.player
        if not player.has_usable_pokemon:
            return StepResult("blocked", "Tus Pokémon están agotados.")
        turned = player.facing != direction
        player.facing = direction
        dx, dy = DIRECTIONS[direction]
        x, y = player.pos[0] + dx, player.pos[1] + dy

        if not self.is_walkable(x, y):
            return StepResult("turned" if turned else "blocked")

        tile = self.zone.tile(x, y)
        if tile.isdigit():
            return self._take_warp(tile)

        player.pos = (x, y)
        player.stats["steps"] += 1

        if tile in "CMGL":
            return StepResult("building", building=tile)

        spotter = self._trainer_spotting_player()
        if spotter:
            return StepResult("trainer", trainer=spotter, text=spotter.intro)

        if tile == "g" and self.zone.encounters and self.rng.random() < self.zone.encounter_rate:
            wild = self.roll_wild_pokemon()
            if wild:
                return StepResult("wild", pokemon=wild)
        return StepResult("moved")

    def _take_warp(self, key: str) -> StepResult:
        warp = self.zone.warps[key]
        if warp.requires_medal and warp.requires_medal not in self.player.medals:
            return StepResult("locked", warp.blocked_text)
        self.player.zone = warp.zone
        self.player.pos = warp.pos
        return StepResult("warp", f"{get_zone(warp.zone).name}", new_zone=True)

    def _trainer_spotting_player(self) -> Optional[TrainerDef]:
        px, py = self.player.pos
        for trainer in self.trainers_here():
            if trainer.sight <= 0 or trainer.id in self.player.defeated:
                continue
            dx, dy = DIRECTIONS[trainer.facing]
            for dist in range(1, trainer.sight + 1):
                x, y = trainer.pos[0] + dx * dist, trainer.pos[1] + dy * dist
                if self.zone.tile(x, y) in BLOCKED:
                    break
                if (x, y) == (px, py):
                    return trainer
        return None

    # ---- interacción ------------------------------------------------------------------------
    def facing_tile(self) -> Tuple[int, int]:
        dx, dy = DIRECTIONS[self.player.facing]
        return self.player.pos[0] + dx, self.player.pos[1] + dy

    def interact(self):
        """Devuelve el NPC o entrenador que tienes delante (o None)."""
        return self.occupant_at(*self.facing_tile())

    def npc_lines(self, npc: NPC) -> List[str]:
        return list(npc.lines)

    def trainer_after_text(self, trainer: TrainerDef) -> str:
        return trainer.after if trainer.id in self.player.defeated else trainer.intro

    def building_trainer(self, building: str) -> Optional[TrainerDef]:
        """Líder del gimnasio o campeón de la Liga de la zona actual."""
        role = {"G": "leader", "L": "champion"}.get(building)
        for trainer in self.trainers_here():
            if trainer.role == role:
                return trainer
        return None

    def challenge_status(self, trainer: TrainerDef) -> Tuple[bool, str]:
        """¿Puede el jugador retar a este entrenador ahora?"""
        if trainer.id in self.player.defeated:
            return False, trainer.after
        if trainer.role == "champion" and not set(MEDALS) <= self.player.medals:
            return False, "Necesitas las tres medallas para entrar a la Liga Poke-TEC."
        if not self.player.has_usable_pokemon:
            return False, "No tienes Pokémon en condiciones de combatir."
        return True, trainer.intro

    # ---- combates ---------------------------------------------------------------------------
    def roll_wild_pokemon(self) -> Optional[Pokemon]:
        encounters = self.zone.encounters
        if not encounters:
            return None
        weights = [e[3] for e in encounters]
        species_id, lo, hi, _ = self.rng.choices(encounters, weights=weights, k=1)[0]
        mon = Pokemon(species_id, self.rng.randint(lo, hi), rng=self.rng)
        return mon

    def _resolve_species(self, species_id: str) -> str:
        return RIVAL_COUNTER[self.starter] if species_id == "@rival" else species_id

    def build_trainer_team(self, trainer: TrainerDef) -> List[Pokemon]:
        return [Pokemon(self._resolve_species(sp), lvl, rng=self.rng) for sp, lvl in trainer.team]

    def start_wild_battle(self, wild: Pokemon) -> Battle:
        self.player.register_seen(wild.species_id)
        return Battle(self.player.team, [wild], kind="wild", player_name=self.player.name,
                      bag=self.player.bag, ai=AI("easy", self.rng), rng=self.rng)

    def start_trainer_battle(self, trainer: TrainerDef) -> Battle:
        ok, reason = self.challenge_status(trainer)
        if not ok:
            raise ValueError(reason)
        team = self.build_trainer_team(trainer)
        for mon in team:
            self.player.register_seen(mon.species_id)
        level = self.player.difficulty
        if trainer.role in ("leader", "champion", "rival"):
            level = AI_STEP_UP.get(level, level)
        return Battle(self.player.team, team, kind="trainer", foe_name=trainer.name,
                      player_name=self.player.name, bag=self.player.bag,
                      foe_items=trainer.items, ai=AI(level, self.rng), rng=self.rng)

    def finish_battle(self, battle: Battle, trainer: Optional[TrainerDef] = None) -> BattleOutcome:
        """Aplica premios, capturas o la derrota. Llamar una sola vez por combate."""
        player = self.player
        out = BattleOutcome()
        result = battle.result
        if result == "caught" and battle.caught is not None:
            place = player.add_pokemon(battle.caught)
            player.stats["captures"] += 1
            where = "tu equipo" if place == "team" else "la Caja"
            out.lines.append(f"¡{battle.caught.name} fue añadido a {where}!")
        elif result == "win":
            if trainer is None:
                player.stats["wild_wins"] += 1
            else:
                self._reward_trainer(trainer, out)
        elif result == "lose":
            self._blackout(out)
        out.quests = check_quests(player)
        for quest in out.quests:
            out.lines.append(f"¡Misión completada: {quest.title}!")
        return out

    def _reward_trainer(self, trainer: TrainerDef, out: BattleOutcome) -> None:
        player = self.player
        first_time = trainer.id not in player.defeated
        player.defeated.add(trainer.id)
        if not first_time:
            return
        player.stats["trainer_wins"] += 1
        player.money += trainer.money
        out.lines.append(f"Ganaste ${trainer.money} por vencer a {trainer.name}.")
        if trainer.medal and trainer.medal not in player.medals:
            player.medals.add(trainer.medal)
            out.medal = trainer.medal
            out.lines.append(f"¡Obtuviste la {MEDALS[trainer.medal]}!")
        for item_id, qty in trainer.reward_items.items():
            player.bag.add(item_id, qty)
            out.lines.append(f"Recibiste {qty} × {get_item(item_id).name}.")
        if trainer.role == "champion":
            player.flags["champion"] = True
            out.champion = True

    def _blackout(self, out: BattleOutcome) -> None:
        player = self.player
        lost = int(player.money * BLACKOUT_MONEY_LOSS)
        player.money -= lost
        player.stats["blackouts"] += 1
        player.heal_team()
        zone_id, x, y = player.last_heal
        player.zone, player.pos = zone_id, (x, y)
        out.blackout = True
        out.lines.append(f"Perdiste ${lost}... Despiertas en el Centro Pokémon.")

    # ---- Centro Pokémon, tienda -------------------------------------------------------------
    def heal_at_center(self) -> str:
        self.player.heal_team()
        self.player.last_heal = (self.player.zone, self.player.pos[0], self.player.pos[1])
        return "¡Tus Pokémon están como nuevos!"

    def shop_stock(self) -> List[str]:
        return list(SHOP_STOCK.get(self.player.zone, []))

    def buy(self, item_id: str, qty: int = 1) -> Tuple[bool, str]:
        if item_id not in self.shop_stock():
            return False, "Ese objeto no está a la venta aquí."
        if qty <= 0:
            return False, "Cantidad no válida."
        item = get_item(item_id)
        cost = item.price * qty
        if cost > self.player.money:
            return False, "No tienes suficiente dinero."
        self.player.money -= cost
        self.player.bag.add(item_id, qty)
        return True, f"Compraste {qty} × {item.name}."

    def sell_price(self, item_id: str) -> int:
        return int(get_item(item_id).price * SELL_RATIO)

    def sell(self, item_id: str, qty: int = 1) -> Tuple[bool, str]:
        item = get_item(item_id)
        if item.price <= 0:
            return False, "Ese objeto no se puede vender."
        if qty <= 0 or self.player.bag.count(item_id) < qty:
            return False, "No tienes tantos."
        self.player.bag.remove(item_id, qty)
        self.player.money += self.sell_price(item_id) * qty
        return True, f"Vendiste {qty} × {item.name}."

    # ---- objetos fuera de combate -----------------------------------------------------------
    def can_use_item(self, item_id: str, team_index: int) -> bool:
        """¿Serviría este objeto fuera de combate sobre ese miembro del equipo? (lo usa la interfaz)"""
        if not 0 <= team_index < len(self.player.team):
            return False
        item, mon = get_item(item_id), self.player.team[team_index]
        if item.kind == "stone":
            return mon.item_evolution(item_id) is not None
        if item.kind == "candy":
            return mon.level < 100
        if item.kind == "ball":
            return False
        return Battle._item_useful(item, mon)

    def use_item(self, item_id: str, team_index: int) -> Tuple[bool, str]:
        """Usa un objeto sobre un miembro del equipo desde la mochila."""
        player = self.player
        if not 0 <= team_index < len(player.team):
            return False, "Pokémon no válido."
        item = get_item(item_id)
        mon = player.team[team_index]
        if player.bag.count(item_id) <= 0:
            return False, "No te queda ese objeto."

        if item.kind == "heal":
            useful = not mon.is_fainted and (mon.hp < mon.max_hp or (item.cures == "*" and mon.status))
            if not useful:
                return False, "No tendría ningún efecto."
            restored = mon.heal(int(item.power))
            if item.cures == "*":
                mon.clear_status()
            message = f"{mon.name} recuperó {restored} PS."
        elif item.kind == "cure":
            if mon.is_fainted or mon.status is None or item.cures not in ("*", mon.status):
                return False, "No tendría ningún efecto."
            mon.clear_status()
            message = f"{mon.name} se curó."
        elif item.kind == "revive":
            if not mon.is_fainted:
                return False, "No tendría ningún efecto."
            mon.revive(item.power)
            message = f"¡{mon.name} volvió a la vida!"
        elif item.kind == "pp":
            if mon.is_fainted or all(s.pp >= s.max_pp for s in mon.moves):
                return False, "No tendría ningún efecto."
            mon.restore_pp(int(item.power))
            message = f"{mon.name} recuperó PP."
        elif item.kind == "stone":
            target = mon.item_evolution(item_id)
            if target is None:
                return False, f"{mon.name} no reacciona a la {item.name}."
            old = mon.name
            self.evolve(mon, target)
            message = f"¡{old} evolucionó a {SPECIES[target].name}!"
        elif item.kind == "candy":
            if mon.level >= 100:
                return False, "No tendría ningún efecto."
            mon.gain_exp(mon.exp_needed_for_next - mon.exp_into_level)
            message = f"¡{mon.name} subió al nivel {mon.level}!"
        else:
            return False, "Ese objeto solo sirve en combate."
        player.bag.remove(item_id)
        check_quests(player)
        return True, message

    # ---- evolución --------------------------------------------------------------------------
    def evolve(self, mon: Pokemon, new_species_id: str) -> None:
        mon.evolve(new_species_id)
        self.player.stats["evolutions"] += 1
        self.player.register_caught(new_species_id)

    def pending_evolutions(self, battle: Battle) -> List[Tuple[Pokemon, str]]:
        """Pokémon que cumplen las condiciones de evolución tras el combate."""
        out = []
        for mon in battle.pending_evolve:
            target = mon.level_evolution()
            if target:
                out.append((mon, target))
        return out

    # ---- equipo y guardado ------------------------------------------------------------------
    def save(self) -> None:
        save_player(self.player)

    def difficulty_label(self) -> str:
        return {"easy": "Fácil", "normal": "Normal", "hard": "Difícil"}.get(self.player.difficulty, "Normal")
