"""Ranking Top 10 del Duelo Clásico (compatible con el scores.json original)."""
import json
import os
from pathlib import Path
from typing import Dict, List, Union

from ..paths import SCORES_FILE

TOP_N = 10


def load_scores(path: Union[str, Path] = SCORES_FILE) -> List[Dict]:
    """Lee los puntajes; ignora entradas inválidas y archivos corruptos."""
    path = Path(path)
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except (OSError, ValueError):
        return []
    scores = []
    for entry in raw if isinstance(raw, list) else []:
        try:
            scores.append({"name": str(entry["name"])[:12], "score": int(entry["score"]),
                           "avatar": entry.get("avatar")})
        except (KeyError, TypeError, ValueError):
            continue
    return sorted(scores, key=lambda e: e["score"], reverse=True)[:TOP_N]


def save_score(name: str, score: int, avatar=None, path: Union[str, Path] = SCORES_FILE) -> int:
    """Guarda un puntaje y devuelve la posición (1-based) o 0 si no entró al Top 10."""
    path = Path(path)
    scores = load_scores(path)
    entry = {"name": (name or "Entrenador")[:12], "score": int(score), "avatar": avatar}
    scores.append(entry)
    scores = sorted(scores, key=lambda e: e["score"], reverse=True)
    position = next((i + 1 for i, e in enumerate(scores) if e is entry), 0)
    scores = scores[:TOP_N]
    tmp = path.with_suffix(".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(scores, fh, indent=4, ensure_ascii=False)
        os.replace(tmp, path)
    except OSError:
        return 0
    return position if position <= TOP_N else 0
