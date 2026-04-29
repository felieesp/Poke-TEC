from tkinter import *
from os import path

ventana = Tk()
ventana.title("Título de prueba")
ventana.minsize(1200, 800)
ventana.resizable(width=NO, height=NO)

fuentegeneral= ('Noto Sans', 15)


about = """
Pokémon azul 
"""
C_principal = Canvas(ventana, width=1200, height=800)
C_principal.place(x=0, y=0)

L_about = Label(C_principal, text=about, font=('Noto Sans', 15), bg='#ffffff', fg='black')
L_about.place(x=280, y=360)

def cargar_img(nombre):
    ruta = path.join('images', nombre)   # construye la ruta correctamente
    img = PhotoImage(file=ruta)          # carga la imagen (PNG recomendado)
    return img

# Canvas principal (del tamaño de la ventana)

# Cargar imagen
C_principal.fondo = cargar_img('PantallaDeCarga.png')

# Colocar imagen como fondo
C_principal.create_image(250, 250, anchor=NW, image=C_principal.fondo)

E_nombre = Entry(ventana, width=10, font=fuentegeneral) # creación de un entry
E_nombre.place(x=20, y=200)

def mostrar_nombre():
    global E_nombre # llamamos a la variable global para poder usarla dentro de la función
    nombre_data = E_nombre.get() # obtenemos el texto que el usuario escribió en el entry
    print(nombre_data) # mostramos el texto en la consola (puede ser útil para depuración)
    if(nombre_data!=''):
        ventana_hija=Toplevel()
        L_nombre=Label(ventana_hija, text = f'El nuevo entrenador se llama {nombre_data}' ,font=fuentegeneral)
        L_nombre.place(x=200, y=100)
Btn_empezar = Button(ventana, text='Iniciar',command =mostrar_nombre, width=20, height=10)
Btn_empezar.place(x=20, y=300)
























ventana.mainloop()