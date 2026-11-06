"""Guardado y carga de partidas (JSON, escritura atómica con copia de respaldo)."""
import json
import os
from pathlib import Path
from typing import Union

from ..paths import ADVENTURE_SAVE
from .player import Player

SAVE_VERSION = 1


class SaveError(Exception):
    """La partida no existe o está dañada."""


def has_save(path: Union[str, Path] = ADVENTURE_SAVE) -> bool:
    return Path(path).exists()


def save_player(player: Player, path: Union[str, Path] = ADVENTURE_SAVE) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": SAVE_VERSION, "player": player.to_dict()}
    tmp = path.with_suffix(".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        if path.exists():
            os.replace(path, path.with_suffix(".bak"))
        os.replace(tmp, path)
    except OSError as exc:
        raise SaveError(f"No se pudo guardar la partida: {exc}") from exc


def _read(path: Path) -> Player:
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict) or "player" not in data:
        raise ValueError("formato desconocido")
    if data.get("version", 0) > SAVE_VERSION:
        raise ValueError("la partida es de una versión más nueva del juego")
    player = Player.from_dict(data["player"])
    if not player.team and not player.box:
        raise ValueError("la partida no contiene Pokémon")
    return player


def load_player(path: Union[str, Path] = ADVENTURE_SAVE) -> Player:
    """Carga la partida; si el archivo está dañado intenta la copia de respaldo."""
    path = Path(path)
    if not path.exists():
        raise SaveError("No hay ninguna partida guardada.")
    try:
        return _read(path)
    except (OSError, ValueError, KeyError, TypeError) as first_error:
        backup = path.with_suffix(".bak")
        if backup.exists():
            try:
                return _read(backup)
            except (OSError, ValueError, KeyError, TypeError):
                pass
        raise SaveError(f"La partida está dañada ({first_error}).") from first_error
