from tkinter import *   # Importa todo lo necesario para crear interfaces gráficas
from os import path     # Permite trabajar con rutas de archivos (ver si existen)
import random           # Para generar elecciones aleatorias

# ================= DATOS =================

pokemones_base = [  # Lista de Pokémon con sus estadísticas base
    {"nombre": "Charmander", "vida": 100, "ataque": 30, "defensa": 10},
    {"nombre": "Squirtle", "vida": 120, "ataque": 20, "defensa": 20},
    {"nombre": "Bulbasaur", "vida": 110, "ataque": 25, "defensa": 15},
    {"nombre": "Pikachu", "vida": 90, "ataque": 35, "defensa": 10},
    {"nombre": "Eevee", "vida": 95, "ataque": 28, "defensa": 12},
    {"nombre": "Snorlax", "vida": 150, "ataque": 20, "defensa": 25},
    {"nombre": "Gengar", "vida": 80, "ataque": 40, "defensa": 5},
    {"nombre": "Onix", "vida": 130, "ataque": 15, "defensa": 30},
    {"nombre": "Machop", "vida": 110, "ataque": 32, "defensa": 10},
    {"nombre": "Psyduck", "vida": 100, "ataque": 22, "defensa": 18}
]

jugador_equipo = []      # Lista del equipo del jugador
enemigo_equipo = []      # Lista del equipo enemigo
puntaje_jugador = 0      # Puntos del jugador
puntaje_enemigo = 0      # Puntos del enemigo

# ================= FUNCIONES =================

def copiar_pokemon(p):
    return p.copy()  # Devuelve una copia del Pokémon para no modificar el original

def restaurar_vida(p):
    for base in pokemones_base:   # Busca el Pokémon original
        if base["nombre"] == p["nombre"]:
            p["vida"] = base["vida"]  # Restaura su vida al valor inicial

# ================= SELECCIÓN =================

def seleccionar_pokemon(nombre):
    ventana_sel = Toplevel()  # Crea una nueva ventana
    ventana_sel.title("Selecciona 3 Pokémon")

    seleccionados = []  # Lista temporal para los Pokémon elegidos

    def elegir(p):
        if len(seleccionados) < 3 and p not in seleccionados:
            seleccionados.append(copiar_pokemon(p))  # Agrega Pokémon seleccionado

        if len(seleccionados) == 3:  # Cuando ya eligió 3
            global jugador_equipo, enemigo_equipo
            jugador_equipo = seleccionados.copy()  # Asigna equipo del jugador
            enemigo_equipo = [copiar_pokemon(p) for p in random.sample(pokemones_base, 3)]  # Equipo enemigo aleatorio
            ventana_sel.destroy()  # Cierra la ventana de selección
            pantalla_combate(nombre)  # Abre la pantalla de combate

    Label(ventana_sel, text="Elige 3 Pokémon").pack()  # Texto en pantalla

    for p in pokemones_base:
        Button(ventana_sel, text=p["nombre"],
               command=lambda p=p: elegir(p)).pack(pady=5)  # Botón por cada Pokémon

# ================= COMBATE =================

def pantalla_combate(nombre):
    combate = Toplevel()  # Nueva ventana
    combate.title("Combate Pokémon")

    global puntaje_jugador, puntaje_enemigo

    turno = {"jugador": None, "enemigo": None}  # Guarda Pokémon actuales

    lbl_info = Label(combate, text="Selecciona tu Pokémon", font=("Arial", 14))
    lbl_info.pack(pady=10)

    lbl_puntaje = Label(combate, text=f"Puntos: {puntaje_jugador}", font=("Arial", 12))
    lbl_puntaje.pack()

    def elegir_pokemon(p):
        turno["jugador"] = p  # Pokémon del jugador
        turno["enemigo"] = random.choice(enemigo_equipo)  # Pokémon enemigo aleatorio
        actualizar()  # Inicia combate

    def actualizar():
        nonlocal turno
        global puntaje_jugador, puntaje_enemigo

        p1 = turno["jugador"]
        p2 = turno["enemigo"]

        # Calcula daño restando defensa
        daño_jugador = max(0, p1["ataque"] - p2["defensa"])
        daño_enemigo = max(0, p2["ataque"] - p1["defensa"])

        # Aplica daño
        p2["vida"] -= daño_jugador
        p1["vida"] -= daño_enemigo

        # Texto informativo
        texto = f"{p1['nombre']} VS {p2['nombre']}\n"
        texto += f"Daño jugador: {daño_jugador} | Daño enemigo: {daño_enemigo}\n"
        texto += f"Vida jugador: {p1['vida']} | Vida enemigo: {p2['vida']}"

        if p2["vida"] <= 0:  # Si el enemigo pierde
            enemigo_equipo.remove(p2)
            jugador_equipo.append(p2)  # Lo capturas
            restaurar_vida(p2)
            puntaje_jugador += 1
            texto += "\n¡Capturaste un Pokémon!"

        elif p1["vida"] <= 0:  # Si pierdes
            jugador_equipo.remove(p1)
            enemigo_equipo.append(p1)  # Te capturan
            restaurar_vida(p1)
            puntaje_enemigo += 1
            texto += "\nTe capturaron un Pokémon"

        lbl_info.config(text=texto)  # Actualiza texto en pantalla
        lbl_puntaje.config(text=f"Puntos: {puntaje_jugador}")

        verificar_fin()  # Revisa si terminó el juego

    def verificar_fin():
        if len(jugador_equipo) == 0 or len(enemigo_equipo) == 0:
            guardar_puntaje(nombre, puntaje_jugador)  # Guarda score
            mostrar_top10()  # Muestra ranking

    for p in jugador_equipo:
        Button(combate, text=p["nombre"],
               command=lambda p=p: elegir_pokemon(p),
               width=20).pack(pady=5)  # Botones para elegir Pokémon

# ================= TOP 10 =================

def guardar_puntaje(nombre, puntaje):
    archivo = "puntajes.txt"
    datos = []

    if path.exists(archivo):  # Si el archivo existe
        with open(archivo, "r") as f:
            for linea in f:
                n, p = linea.strip().split(",")
                datos.append((n, int(p)))  # Guarda nombre y puntaje

    datos.append((nombre, puntaje))  # Agrega nuevo puntaje
    datos = sorted(datos, key=lambda x: x[1], reverse=True)[:10]  # Ordena top 10

    with open(archivo, "w") as f:
        for n, p in datos:
            f.write(f"{n},{p}\n")  # Guarda en archivo

def mostrar_top10():
    top = Toplevel()
    top.title("TOP 10")

    Label(top, text="Mejores Puntajes", font=("Arial", 14)).pack(pady=10)

    if path.exists("puntajes.txt"):
        with open("puntajes.txt", "r") as f:
            for linea in f:
                Label(top, text=linea.strip()).pack()  # Muestra cada puntaje

# ================= VENTANA PRINCIPAL =================

ventana = Tk()  # Ventana principal
ventana.title("Pokémon Azul")
ventana.geometry("400x300")

Label(ventana, text="Nombre del entrenador", font=("Arial", 12)).pack(pady=10)

entrada_nombre = Entry(ventana)  # Campo para escribir nombre
entrada_nombre.pack(pady=10)

def iniciar():
    nombre = entrada_nombre.get()  # Obtiene nombre
    if nombre != "":
        seleccionar_pokemon(nombre)  # Inicia selección

Button(ventana, text="Iniciar Juego", command=iniciar, width=20).pack(pady=20)

ventana.mainloop()  # Mantiene la ventana abierta