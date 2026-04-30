import tkinter as tk
from tkinter import messagebox
import random
import json
import os
from PIL import Image, ImageTk

# =========================
# RUTAS
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def ruta(rel):
    return os.path.join(BASE_DIR, rel)

# =========================
# MODELOS (CLASES)
# =========================
class Pokemon:
    def __init__(self, name, hp, attack, defense):
        self.name = name
        self.max_hp = hp
        self.hp = hp
        self.attack = attack
        self.defense = defense

    def is_alive(self):
        return self.hp > 0

    def attack_enemy(self, enemy):
        damage = max(0, self.attack - enemy.defense)
        enemy.hp -= damage

class Trainer:
    def __init__(self, name, avatar=None):
        self.name = name
        self.avatar = avatar  # Nombre del archivo de imagen
        self.pokemons = []
        self.score = 0

# =========================
# DATA (POKEMONES)
# =========================
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
SCORE_FILE = "scores.json"

def load_scores():
    if not os.path.exists(SCORE_FILE): return []
    with open(SCORE_FILE, "r") as f: return json.load(f)

def save_score(player):
    scores = load_scores()
    scores.append({"name": player.name, "score": player.score})
    scores = sorted(scores, key=lambda x: x["score"], reverse=True)[:10]
    with open(SCORE_FILE, "w") as f: json.dump(scores, f, indent=4)

# =========================
# APP PRINCIPAL
# =========================
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Pokemon Battle")
        self.all_pokemons = create_pokemons()
        self.avatars = ["Ash.png", "Rival.png", "Bob.png", "Emma.png", "Julianita.png"]
        self.selected_avatar = tk.StringVar(value="Ash.png")
        self.player = None
        self.enemy = None
        self.current_index = 0
        self.start_screen()

    def start_screen(self):
        self.clear()
        
        tk.Label(self.root, text="Nombre del Entrenador", font=("Arial", 12, "bold")).pack(pady=5)
        self.name_entry = tk.Entry(self.root)
        self.name_entry.pack(pady=5)

        tk.Label(self.root, text="Selecciona tu Avatar", font=("Arial", 10)).pack(pady=5)
        
        # Frame para selección de Avatar
        avatar_frame = tk.Frame(self.root)
        avatar_frame.pack(pady=10)
        
        self.avatar_imgs = [] # Para evitar que el recolector de basura borre las imágenes
        for av in self.avatars:
            try:
                img = Image.open(ruta(f"images/Entrenadores/{av}")).resize((60, 60))
                img_tk = ImageTk.PhotoImage(img)
                self.avatar_imgs.append(img_tk)
                
                rb = tk.Radiobutton(avatar_frame, image=img_tk, variable=self.selected_avatar, value=av)
                rb.pack(side="left", padx=5)
            except:
                tk.Radiobutton(avatar_frame, text=av, variable=self.selected_avatar, value=av).pack(side="left")

        tk.Label(self.root, text="Selecciona 3 Pokémon", font=("Arial", 12, "bold")).pack(pady=5)
        self.vars = []
        poke_frame = tk.Frame(self.root)
        poke_frame.pack()
        for p in self.all_pokemons:
            var = tk.IntVar()
            tk.Checkbutton(poke_frame, text=p.name, variable=var).pack(anchor="w")
            self.vars.append((var, p))

        tk.Button(self.root, text="¡A LUCHAR!", bg="red", fg="white", font=("Arial", 10, "bold"), 
                  command=self.start_game).pack(pady=20)

    def start_game(self):
        selected = [p for var, p in self.vars if var.get() == 1]
        if len(selected) != 3:
            messagebox.showerror("Error", "Debes elegir exactamente 3 Pokémon")
            return

        # Configuración Jugador
        self.player = Trainer(self.name_entry.get() or "Jugador", self.selected_avatar.get())
        self.player.pokemons = selected

        # Configuración Rival (No puede tener el mismo avatar)
        posibles_rivales = [av for av in self.avatars if av != self.player.avatar]
        rival_avatar = random.choice(posibles_rivales)
        
        self.enemy = Trainer("Rival", rival_avatar)
        self.enemy.pokemons = random.sample(create_pokemons(), 3)
        self.current_index = 0
        self.game_screen()

    def game_screen(self):
        self.clear()
        self.canvas = tk.Canvas(self.root, width=800, height=500, bg="black")
        self.canvas.pack()

        # Fondo
        try:
            img = Image.open(ruta("images/Escenario/escenario.png")).resize((800, 500))
            self.bg = ImageTk.PhotoImage(img)
            self.canvas.create_image(0, 0, anchor="nw", image=self.bg)
        except:
            self.canvas.create_text(400, 250, text="FONDO NO ENCONTRADO", fill="white")

        # Dibujar Entrenadores (Basado en selección)
        try:
            img_r = Image.open(ruta(f"images/Entrenadores/{self.enemy.avatar}")).resize((120, 120))
            self.rival_img = ImageTk.PhotoImage(img_r)
            self.canvas.create_image(700, 80, image=self.rival_img)
            
            img_p = Image.open(ruta(f"images/Entrenadores/{self.player.avatar}")).resize((120, 120))
            self.ash_img = ImageTk.PhotoImage(img_p)
            self.canvas.create_image(100, 300, image=self.ash_img)
        except:
            pass

        self.player_pokemon = self.player.pokemons[self.current_index]
        self.enemy_pokemon = random.choice(self.enemy.pokemons)

        # Pokémon Rival
        try:
            img_e = Image.open(ruta(f"images/Pokemones/{self.enemy_pokemon.name}.png")).resize((150, 150)).transpose(Image.FLIP_LEFT_RIGHT)
            self.enemy_img = ImageTk.PhotoImage(img_e)
            self.canvas.create_image(600, 150, image=self.enemy_img)
        except:
            self.canvas.create_text(600, 150, text=self.enemy_pokemon.name, fill="red")

        # Pokémon Jugador
        try:
            img_pl = Image.open(ruta(f"images/Pokemones/{self.player_pokemon.name}.png")).resize((150, 150))
            self.player_img = ImageTk.PhotoImage(img_pl)
            self.canvas.create_image(200, 350, image=self.player_img)
        except:
            self.canvas.create_text(200, 350, text=self.player_pokemon.name, fill="blue")

        # Barras de vida
        self.canvas.create_rectangle(50, 50, 250, 100, fill="white")
        hp_e = self.enemy_pokemon.hp / self.enemy_pokemon.max_hp
        self.canvas.create_rectangle(60, 70, 60 + (180 * hp_e), 90, fill="green")
        self.canvas.create_text(150, 60, text=f"{self.enemy_pokemon.name} (Rival)")

        self.canvas.create_rectangle(500, 300, 700, 350, fill="white")
        hp_p = self.player_pokemon.hp / self.player_pokemon.max_hp
        self.canvas.create_rectangle(510, 320, 510 + (180 * hp_p), 340, fill="green")
        self.canvas.create_text(600, 310, text=f"{self.player_pokemon.name} ({self.player.name})")

        # Interfaz de comandos
        btn = tk.Button(self.root, text="ATACAR", font=("Arial", 12, "bold"), command=self.battle_turn)
        self.canvas.create_window(175, 440, window=btn)

        x_start = 400
        for i, p in enumerate(self.player.pokemons):
            if i == self.current_index: continue
            try:
                img_ico = Image.open(ruta(f"images/Pokemones/{p.name}.png")).resize((50, 50))
                tk_ico = ImageTk.PhotoImage(img_ico)
                btn_p = tk.Button(self.root, image=tk_ico, command=lambda idx=i: self.cambiar_pokemon(idx))
                btn_p.image = tk_ico
                self.canvas.create_window(x_start, 440, window=btn_p)
                x_start += 70
            except:
                pass

    def cambiar_pokemon(self, index):
        self.current_index = index
        self.game_screen()

    def battle_turn(self):
        p, e = self.player_pokemon, self.enemy_pokemon
        p.attack_enemy(e)
        if e.is_alive(): e.attack_enemy(p)

        if not e.is_alive():
            self.player.pokemons.append(e)
            self.enemy.pokemons.remove(e)
            e.hp = e.max_hp
            self.player.score += 1
        elif not p.is_alive():
            self.enemy.pokemons.append(p)
            self.player.pokemons.remove(p)
            p.hp = p.max_hp

        if self.current_index >= len(self.player.pokemons): self.current_index = 0
        if not self.player.pokemons or not self.enemy.pokemons:
            self.end_game()
        else:
            self.game_screen()

    def end_game(self):
        save_score(self.player)
        messagebox.showinfo("Fin del juego", f"Resultado: {'¡Ganaste!' if self.player.pokemons else 'Perdiste...'}\nPuntaje final: {self.player.score}")
        self.start_screen()

    def clear(self):
        for w in self.root.winfo_children(): w.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
