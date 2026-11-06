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
# MODELOS 
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
        #  Cálculo de daño (Ataque - Defensa)
        damage = max(0, self.attack - enemy.defense)
        enemy.hp -= damage

class Trainer:
    def __init__(self, name, avatar=None):
        self.name = name
        self.avatar = avatar
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
        Pokemon("Vaporeon", 140, 32, 22), 
        Pokemon("Mew", 100, 45, 20)
    ]

# =========================
#  (PUNTAJES) - 
# =========================
SCORE_FILE = "scores.json"

def load_scores():
    if not os.path.exists(SCORE_FILE): return []
    try:
        with open(SCORE_FILE, "r") as f: return json.load(f)
    except: return []

def save_score(player):
    scores = load_scores()
    scores.append({
        "name": player.name, 
        "score": player.score, 
        "avatar": player.avatar
    })
    scores = sorted(scores, key=lambda x: x["score"], reverse=True)[:10]
    with open(SCORE_FILE, "w") as f: json.dump(scores, f, indent=4)

# =========================
# APP PRINCIPAL
# =========================
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Pokemon Battle - Proyecto")
        self.all_pokemons = create_pokemons()
        self.avatars = ["Ash.png", "Rival.png", "Bob.png", "Emma.png", "Julianita.png"]
        self.selected_avatar = tk.StringVar(value="Ash.png")
        self.start_screen()

    def start_screen(self):
        self.clear()
        tk.Label(self.root, text="REGISTRO DE ENTRENADOR", font=("Arial", 14, "bold")).pack(pady=10)
        
        tk.Label(self.root, text="Nombre:").pack()
        self.name_entry = tk.Entry(self.root)
        self.name_entry.pack(pady=5)

        tk.Label(self.root, text="Selecciona tu Avatar:").pack(pady=5)
        avatar_frame = tk.Frame(self.root)
        avatar_frame.pack()
        
        self.avatar_imgs = []
        for av in self.avatars:
            try:
                img = Image.open(ruta(f"images/Entrenadores/{av}")).resize((50, 50))
                img_tk = ImageTk.PhotoImage(img)
                self.avatar_imgs.append(img_tk)
                tk.Radiobutton(avatar_frame, image=img_tk, variable=self.selected_avatar, value=av).pack(side="left", padx=5)
            except:
                tk.Radiobutton(avatar_frame, text=av, variable=self.selected_avatar, value=av).pack(side="left")

        tk.Label(self.root, text="Selecciona 3 Pokémon:", font=("Arial", 10, "bold")).pack(pady=10)
        self.vars = []
        # Organizar en dos columnas para que quepan los 11
        list_frame = tk.Frame(self.root)
        list_frame.pack()
        for i, p in enumerate(self.all_pokemons):
            var = tk.IntVar()
            cb = tk.Checkbutton(list_frame, text=p.name, variable=var)
            cb.grid(row=i//2, column=i%2, sticky="w")
            self.vars.append((var, p))

        tk.Button(self.root, text="INICIAR", bg="green", fg="white", font=("Arial", 12, "bold"), 
                  command=self.start_game).pack(pady=20)

    def start_game(self):
        selected = [p for var, p in self.vars if var.get() == 1]
        if len(selected) != 3:
            messagebox.showerror("Error", "Debes elegir exactamente 3 Pokémon")
            return

        self.player = Trainer(self.name_entry.get() or "Felipe", self.selected_avatar.get())
        self.player.pokemons = selected

        # Rival aleatorio 
        posibles = [av for av in self.avatars if av != self.player.avatar]
        self.enemy = Trainer("Rival", random.choice(posibles))
        self.enemy.pokemons = random.sample(create_pokemons(), 3)
        
        self.current_index = 0
        self.game_screen()

    def game_screen(self):
        self.clear()
        self.canvas = tk.Canvas(self.root, width=800, height=500, bg="black")
        self.canvas.pack()

        # Fondos y Entrenadores
        try:
            bg_img = Image.open(ruta("images/Escenario/escenario.png")).resize((800, 500))
            self.bg = ImageTk.PhotoImage(bg_img)
            self.canvas.create_image(0, 0, anchor="nw", image=self.bg)
            
            # Avatar Rival
            img_r = Image.open(ruta(f"images/Entrenadores/{self.enemy.avatar}")).resize((100, 100))
            self.rival_img = ImageTk.PhotoImage(img_r)
            self.canvas.create_image(720, 70, image=self.rival_img)
            
            # Avatar Jugador
            img_p = Image.open(ruta(f"images/Entrenadores/{self.player.avatar}")).resize((100, 100))
            self.player_img = ImageTk.PhotoImage(img_p)
            self.canvas.create_image(80, 320, image=self.player_img)
        except: pass

        self.player_pokemon = self.player.pokemons[self.current_index]
        self.enemy_pokemon = random.choice(self.enemy.pokemons)

        # Dibujar Pokémon
        try:
            img_e = Image.open(ruta(f"images/Pokemones/{self.enemy_pokemon.name}.png")).resize((140, 140)).transpose(Image.FLIP_LEFT_RIGHT)
            self.enemy_p_img = ImageTk.PhotoImage(img_e)
            self.canvas.create_image(600, 150, image=self.enemy_p_img)

            img_pl = Image.open(ruta(f"images/Pokemones/{self.player_pokemon.name}.png")).resize((140, 140))
            self.player_p_img = ImageTk.PhotoImage(img_pl)
            self.canvas.create_image(200, 360, image=self.player_p_img)
        except: pass

        # Barras de Vida e Info
        self.draw_ui()

    def draw_ui(self):
        # UI Rival
        self.canvas.create_rectangle(50, 30, 280, 90, fill="white", outline="black")
        hp_e = self.enemy_pokemon.hp / self.enemy_pokemon.max_hp
        self.canvas.create_rectangle(60, 60, 60 + (200 * hp_e), 80, fill="red")
        self.canvas.create_text(165, 45, text=f"{self.enemy_pokemon.name} (Rival)", font=("Arial", 10, "bold"))

        # UI Jugador
        self.canvas.create_rectangle(520, 280, 750, 340, fill="white", outline="black")
        hp_p = self.player_pokemon.hp / self.player_pokemon.max_hp
        self.canvas.create_rectangle(530, 310, 530 + (200 * hp_p), 330, fill="blue")
        self.canvas.create_text(635, 295, text=f"{self.player_pokemon.name} ({self.player.name})", font=("Arial", 10, "bold"))

        # Botón Atacar
        btn_atk = tk.Button(self.root, text="ATACAR", font=("Arial", 12, "bold"), bg="orange", command=self.battle_turn)
        self.canvas.create_window(150, 460, window=btn_atk)

        # Selector de cambio de Pokémon 
        x = 400
        for i, p in enumerate(self.player.pokemons):
            if i == self.current_index: continue
            try:
                img_ico = Image.open(ruta(f"images/Pokemones/{p.name}.png")).resize((45, 45))
                tk_ico = ImageTk.PhotoImage(img_ico)
                btn = tk.Button(self.root, image=tk_ico, command=lambda idx=i: self.cambiar_pokemon(idx))
                btn.image = tk_ico
                self.canvas.create_window(x, 460, window=btn)
                x += 60
            except: pass

    def cambiar_pokemon(self, index):
        self.current_index = index
        self.game_screen()

    def battle_turn(self):
        p, e = self.player_pokemon, self.enemy_pokemon
        
        # Turno Jugador
        p.attack_enemy(e)
        
        # Turno Rival 
        if e.is_alive():
            e.attack_enemy(p)

        # Lógica de KO y Robo de Pokémon
        if not e.is_alive():
            messagebox.showinfo("¡KO!", f"¡Has capturado a {e.name}!")
            e.hp = e.max_hp # Restablecer vida al ser adueñado
            self.player.pokemons.append(e)
            self.enemy.pokemons.remove(e)
            self.player.score += 1 # Aumentar puntaje
        elif not p.is_alive():
            messagebox.showinfo("KO", f"El rival se ha llevado a {p.name}...")
            p.hp = p.max_hp # Restablecer vida al ser adueñado
            self.enemy.pokemons.append(p)
            self.player.pokemons.remove(p)
           
        # Verificar fin del juego
        if not self.player.pokemons or not self.enemy.pokemons:
            self.end_game()
        else:
            if self.current_index >= len(self.player.pokemons): self.current_index = 0
            self.game_screen()

    def end_game(self):
        save_score(self.player)
        ganador = "¡ERES EL CAMPEÓN!" if self.player.pokemons else "EL RIVAL GANÓ..."
        messagebox.showinfo("FIN DE LA PARTIDA", f"{ganador}\nPuntaje Final: {self.player.score}")
        self.show_scores()

    def show_scores(self):
        self.clear()
        tk.Label(self.root, text="TOP 10 ENTRENADORES", font=("Arial", 16, "bold")).pack(pady=20)
        
        scores = load_scores()
        frame = tk.Frame(self.root)
        frame.pack()

        for i, s in enumerate(scores):
            texto = f"{i+1}. {s['name']} - {s['score']} Pts"
            tk.Label(frame, text=texto, font=("Arial", 12)).pack(anchor="w")

        tk.Button(self.root, text="VOLVER AL MENÚ", command=self.start_screen).pack(pady=20)

    def clear(self):
        for w in self.root.winfo_children(): w.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("800x600")
    app = App(root)
    root.mainloop()
