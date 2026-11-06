"""Rutas del proyecto, siempre relativas a la carpeta del repositorio.

Así el juego funciona sin importar desde qué directorio se ejecute
(en la versión anterior `scores.json` dependía del directorio actual).
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
IMAGES_DIR = BASE_DIR / "images"
SAVES_DIR = BASE_DIR / "saves"
SCORES_FILE = BASE_DIR / "scores.json"
ADVENTURE_SAVE = SAVES_DIR / "aventura.json"
