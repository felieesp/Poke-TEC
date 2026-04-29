import tkinter as tk  # Librería para interfaz gráfica
from tkinter import messagebox  # Para mostrar mensajes emergentes
import random  # Para seleccionar elementos aleatorios
import json  # Para guardar y cargar puntajes
import os  # Para manejar rutas de archivos
from PIL import Image, ImageTk  # Para manejar imágenes

# =========================
# RUTAS
# =========================

# Obtiene la ruta base donde está el archivo actual
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Función para construir rutas relativas correctamente
def ruta(rel):
    return os.path.join(BASE_DIR, rel)

# =========================
# MODELOS (CLASES)
# =========================

# Clase que representa un Pokémon
class Pokemon:
    def __init__(self, name, hp, attack, defense):
        self.name = name  # Nombre del Pokémon
        self.max_hp = hp  # Vida máxima
        self.hp = hp  # Vida actual
        self.attack = attack  # Ataque
        self.defense = defense  # Defensa

    # Verifica si el Pokémon sigue con vida
    def is_alive(self):
        return self.hp > 0

    # Método para atacar a otro Pokémon
    def attack_enemy(self, enemy):
        damage = max(0, self.attack - enemy.defense)  # Cálculo de daño
        enemy.hp -= damage  # Reduce la vida del enemigo

# Clase que representa a un entrenador
class Trainer:
    def __init__(self, name):
        self.name = name  # Nombre del entrenador
        self.pokemons = []  # Lista de Pokémon
        self.score = 0  # Puntaje

# =========================
# DATA (POKEMONES)
# =========================

# Función que crea todos los Pokémon disponibles
def create_pokemons():
    return [
        Pokemon("Blastoise", 120, 35, 25),
        Pokemon("Charmeleon", 90, 45, 10),
        Pokemon("Growlithe", 100, 40, 15),
        Pokemon("Haunter", 80, 50, 10),
        Pokemon("Ivysaur", 110, 35, 20),
        Pokemon("Kadabra", 85, 48, 8),
        Pokemon("Snorlaxx", 150, 30, 30),
        Pokemon("Squirttle", 105, 30, 25),
        Pokemon("Vulpix", 95, 40, 15),
    ]

# =========================
# SCORES (PUNTAJES)
# =========================

# Archivo donde se guardan los puntajes
SCORE_FILE = "scores.json"

# Carga los puntajes desde el archivo
def load_scores():
    if not os.path.exists(SCORE_FILE):
        return []
    with open(SCORE_FILE, "r") as f:
        return json.load(f)

# Guarda un nuevo puntaje
def save_score(player):
    scores = load_scores()
    scores.append({"name": player.name, "score": player.score})

    # Ordena los puntajes de mayor a menor y guarda solo los 10 mejores
    scores = sorted(scores, key=lambda x: x["score"], reverse=True)[:10]

    with open(SCORE_FILE, "w") as f:
        json.dump(scores, f, indent=4)

# =========================
# APP PRINCIPAL
# =========================

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Pokemon Battle")  # Título de la ventana

        # Lista de todos los Pokémon disponibles
        self.all_pokemons = create_pokemons()

        # Inicialización de variables del juego
        self.player = None
        self.enemy = None
        self.current_index = 0  # Índice del Pokémon activo

        # Muestra la pantalla inicial
        self.start_screen()

    # Pantalla inicial donde se selecciona el nombre y Pokémon
    def start_screen(self):
        self.clear()

        tk.Label(self.root, text="Nombre del Entrenador").pack()
        self.name_entry = tk.Entry(self.root)
        self.name_entry.pack()

        tk.Label(self.root, text="Selecciona 3 Pokémon").pack()

        # Lista de checkboxes para seleccionar Pokémon
        self.vars = []
        for p in self.all_pokemons:
            var = tk.IntVar()
            tk.Checkbutton(self.root, text=p.name, variable=var).pack(anchor="w")
            self.vars.append((var, p))

        tk.Button(self.root, text="INICIAR", command=self.start_game).pack()

    # Inicia el juego
    def start_game(self):
        # Obtiene los Pokémon seleccionados
        selected = [p for var, p in self.vars if var.get() == 1]

        # Verifica que se seleccionen exactamente 3
        if len(selected) != 3:
            messagebox.showerror("Error", "Debes elegir 3 Pokémon")
            return

        # Crea el jugador
        self.player = Trainer(self.name_entry.get())
        self.player.pokemons = selected

        # Crea el enemigo con Pokémon aleatorios
        self.enemy = Trainer("Rival")
        self.enemy.pokemons = random.sample(create_pokemons(), 3)

        self.current_index = 0

        # Muestra la pantalla de batalla
        self.game_screen()

    # Pantalla principal del combate
    def game_screen(self):
        self.clear()

        # Crea el canvas donde se dibuja todo
        self.canvas = tk.Canvas(self.root, width=800, height=500, bg="black")
        self.canvas.pack()

        # FONDO
        try:
            img = Image.open(ruta("images/Escenario/escenario.png"))
            img = img.resize((800, 500))
            self.bg = ImageTk.PhotoImage(img)
            self.canvas.create_image(0, 0, anchor="nw", image=self.bg)
        except:
            self.canvas.create_text(400, 250, text="ERROR FONDO", fill="red")

        # ENTRENADOR RIVAL (ARRIBA DERECHA)
        try:
            img_rival = Image.open(ruta("images/Entrenadores/Rival.png"))
            img_rival = img_rival.resize((120, 120))
            self.rival_img = ImageTk.PhotoImage(img_rival)
            self.canvas.create_image(700, 80, image=self.rival_img)
        except:
            self.canvas.create_text(700, 80, text="ERROR RIVAL", fill="red")

        # ENTRENADOR JUGADOR (ABAJO IZQUIERDA)
        try:
            img_ash = Image.open(ruta("images/Entrenadores/Ash.png"))
            img_ash = img_ash.resize((120, 120))
            self.ash_img = ImageTk.PhotoImage(img_ash)
            self.canvas.create_image(100, 300, image=self.ash_img)
        except:
            self.canvas.create_text(100, 300, text="ERROR ASH", fill="red")

        # Selecciona Pokémon actual del jugador
        self.player_pokemon = self.player.pokemons[self.current_index]

        # Selecciona Pokémon aleatorio del enemigo
        self.enemy_pokemon = random.choice(self.enemy.pokemons)

        # DIBUJO DEL POKEMON ENEMIGO
        try:
            img_enemy = Image.open(ruta(f"images/Pokemones/{self.enemy_pokemon.name}.png"))
            img_enemy = img_enemy.resize((150, 150))
            img_enemy = img_enemy.transpose(Image.FLIP_LEFT_RIGHT)

            self.enemy_img = ImageTk.PhotoImage(img_enemy)
            self.canvas.create_image(600, 150, image=self.enemy_img)
        except:
            self.canvas.create_text(600, 150, text="ERROR IMG", fill="red")

        # DIBUJO DEL POKEMON JUGADOR
        try:
            img_player = Image.open(ruta(f"images/Pokemones/{self.player_pokemon.name}.png"))
            img_player = img_player.resize((150, 150))

            self.player_img = ImageTk.PhotoImage(img_player)
            self.canvas.create_image(200, 350, image=self.player_img)
        except:
            self.canvas.create_text(200, 350, text="ERROR IMG", fill="red")

        # BARRA DE VIDA ENEMIGA
        self.canvas.create_rectangle(50, 50, 250, 100, fill="white")
        hp_enemy = self.enemy_pokemon.hp / self.enemy_pokemon.max_hp
        self.canvas.create_rectangle(60, 70, 60 + (180 * hp_enemy), 90, fill="green")
        self.canvas.create_text(150, 60, text=self.enemy_pokemon.name)

        # BARRA DE VIDA DEL JUGADOR
        self.canvas.create_rectangle(500, 300, 700, 350, fill="white")
        hp_player = self.player_pokemon.hp / self.player_pokemon.max_hp
        self.canvas.create_rectangle(510, 320, 510 + (180 * hp_player), 340, fill="green")
        self.canvas.create_text(600, 310, text=self.player_pokemon.name)

        # BOTON DE ATAQUE
        self.canvas.create_rectangle(50, 400, 300, 480, fill="#0b3c5d", outline="yellow", width=3)
        btn = tk.Button(self.root, text="ATACAR", command=self.battle_turn)
        self.canvas.create_window(175, 440, window=btn)

        # BOTONES PARA CAMBIAR POKEMON
        x_start = 400
        for i, p in enumerate(self.player.pokemons):
            if i == self.current_index:
                continue

            try:
                img = Image.open(ruta(f"images/Pokemones/{p.name}.png"))
                img = img.resize((60, 60))
                img_tk = ImageTk.PhotoImage(img)

                btn = tk.Button(self.root, image=img_tk,
                                command=lambda i=i: self.cambiar_pokemon(i))
                btn.image = img_tk

                self.canvas.create_window(x_start, 440, window=btn)
                x_start += 80
            except:
                pass

    # Cambia el Pokémon activo
    def cambiar_pokemon(self, index):
        if index < len(self.player.pokemons):
            self.current_index = index
            self.game_screen()

    # Turno de batalla
    def battle_turn(self):
        p = self.player_pokemon
        e = self.enemy_pokemon

        # Ataque del jugador
        p.attack_enemy(e)

        # Ataque del enemigo si sigue vivo
        if e.is_alive():
            e.attack_enemy(p)

        # Si el enemigo muere
        if not e.is_alive():
            self.player.pokemons.append(e)
            self.enemy.pokemons.remove(e)
            e.hp = e.max_hp
            self.player.score += 1

        # Si el jugador muere
        elif not p.is_alive():
            self.enemy.pokemons.append(p)
            self.player.pokemons.remove(p)
            p.hp = p.max_hp

        # Ajuste del índice
        if self.current_index >= len(self.player.pokemons):
            self.current_index = 0

        # Fin del juego
        if not self.player.pokemons or not self.enemy.pokemons:
            self.end_game()
        else:
            self.game_screen()

    # Finaliza el juego
    def end_game(self):
        save_score(self.player)
        messagebox.showinfo("Fin del juego", f"Puntaje: {self.player.score}")
        self.start_screen()

    # Limpia la pantalla
    def clear(self):
        for w in self.root.winfo_children():
            w.destroy()

# =========================
# EJECUCION PRINCIPAL
# =========================

root = tk.Tk()
app = App(root)
root.mainloop()
