# Cambios — Poke-TEC v2

## Diagnóstico del proyecto original
- Un único script con lógica y dibujo mezclados, sin separar datos, combate e interfaz; pocas especies y sin
  persistencia más allá de `scores.json`.
- Se conserva todo el código original en `legacy/` y el modo clásico sigue disponible como **Duelo Clásico**.

## Nueva versión
- Reorganización en paquete `poketec/` (motor / interfaz), rama `poketec-v2`; originales movidos con `git mv` (historial intacto).
- Motor de combate completo, IA con tres dificultades, modo aventura, guardado/carga, captura, evoluciones, objetos.
- Rediseño visual completo con renderer abstracto (Tk en juego, PIL en pruebas).

## Correcciones en esta revisión
- **Cambio forzado de Pokémon:** el cursor empezaba sobre el Pokémon debilitado, de modo que Enter no hacía nada y el
  jugador parecía bloqueado. Ahora el cursor empieza en el primer Pokémon elegible (`MonPicker`).
- Pruebas de interfaz arregladas (eran frágiles, no el juego): nombre recortado, diálogo de la tienda, casilla de
  hierba de la Ruta 1, selección de Master Ball (antes dependía del azar) y posición del Duelo Clásico en el menú.
- `poketec_error.log` y cachés añadidos a `.gitignore`.

## Pruebas
104 pruebas automáticas pasan. El entorno de revisión no tenía `tkinter`, así que la ventana real no se abrió aquí:
la interfaz se verificó con el renderer PIL (capturas y flujo completo por teclado).
