# Poke-TEC v2

Aventura Pokémon por turnos hecha en Python (tkinter + Pillow). Es la evolución del Poke-TEC original: se conserva el
**Duelo Clásico** (la versión anterior) y se añade un modo **Aventura** completo.

## Ejecutar

```bash
pip install -r requirements.txt   # Pillow (tkinter viene con Python; en Linux: sudo apt install python3-tk)
python main.py                    # o: python -m poketec
```

Controles: flechas / WASD mover, `Enter`/`Z`/`Espacio` aceptar, `Esc`/`X` atrás, `M`/`Tab` menú. También funciona con el ratón.

## Qué incluye

- **Combate por turnos** con daño basado en estadísticas, 13 tipos y su efectividad, STAB, críticos, precisión, prioridad,
  estados (parálisis, quemadura, veneno, sueño), cambio de Pokémon, huida y **captura** con Poké Balls.
- **55 especies**, **56 movimientos**, **19 objetos** (pociones, curas, revivir, balls, piedras evolutivas, caramelos).
- **Niveles, experiencia, aprendizaje de movimientos y evoluciones** (por nivel y por piedra).
- **Equipo de hasta 6** + Caja, mochila por bolsillos, tienda y Centro Pokémon.
- **Mundo**: 6 zonas (Pueblo Origen → Ruta 1 → Bosque Verde → Ciudad Roca → Costa Azul → Pico Ceniza), hierba alta con
  encuentros aleatorios, 16 entrenadores, gimnasios con **medallas** que desbloquean el paso, misiones y progresión.
- **IA rival** en 3 dificultades (fácil / normal / difícil): elige por daño esperado, explota debilidades, remata,
  cambia de Pokémon y usa pociones con criterio.
- **Guardado y carga** (autoguardado, copia `.bak` y recuperación si el archivo está corrupto) y tabla de **récords**.
- **Interfaz**: menú animado, barras de PS/EXP dinámicas, efectos de ataque, transiciones, avisos y diálogos con
  máquina de escribir, estilo coherente en todas las pantallas. Errores en pantalla se registran y no cierran el juego.

## Arquitectura

```
poketec/
  engine/   Lógica pura, sin dependencias de interfaz (testeable sin ventana)
    elements.py  tipos y tabla de efectividad      calc.py      fórmulas de daño/captura/EXP
    species.py   especies y evoluciones            moves.py     movimientos
    pokemon.py   Pokémon individual                items.py/player.py  objetos, mochila, jugador
    battle.py    máquina de estados del combate    ai.py        IA rival
    world.py     zonas, entrenadores                adventure.py  orquesta la partida
    quests.py, save.py, scores.py, classic.py (Duelo Clásico)
  ui/       Presentación (tkinter) sobre un Renderer abstracto
    renderer.py  Renderer (Tk) y PilRenderer (pruebas)     app.py  pila de pantallas
    screens/     menú, mundo, combate, equipo, mochila, diálogos…
legacy/     Código original (conservado, sin tocar)
tests/      Pruebas del motor y de la interfaz (sin ventana)
```

La interfaz nunca contiene reglas de juego y el motor nunca importa la interfaz.

## Pruebas

```bash
pip install pytest
python -m pytest -q      # 104 pruebas: daño, tipos, estados, captura, evolución, IA, guardado, menús y flujo completo
```

Consulta [docs/CHANGELOG.md](docs/CHANGELOG.md) para el detalle de cambios.
