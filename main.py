"""
===========================================================
 PROYECTO: Sistema de Monitoreo de Humedad con Riego
 MODIFICACIÓN: Código Final Maestro Único (Todo de Corrido)
               Escala de 473 Celdas + Candado de Seguridad al Aire
===========================================================
"""

import serial 
import time
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import sqlite3
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# ====================================================
# ⚙️ CONFIGURACIÓN GLOBAL Y HARDWARE
# ====================================================
PUERTO = "COM3"      
BAUDIOS = 115200    

# Constantes de calibración real basadas en tu sensor limpio
VALOR_SECO = 1023    # Lectura al aire (0%)
VALOR_AGUA = 550     # Lectura en agua hasta la línea (100%)

# Constante de gasto de la minibomba (15 ml por segundo)
LITROS_POR_SEGUNDO = 0.015   

try:
    puerto = serial.Serial(PUERTO, BAUDIOS, timeout=0.1) 
    print(f"¡Conectado exitosamente al puerto {PUERTO}!")
except Exception as e:
    print(f"ALERTA: No se pudo conectar al {PUERTO}. La app iniciará en modo simulación.")
    puerto = None

# ====================================================
# 🗄️ GESTIÓN DE BASE DE DATOS (SQLITE3)
# ====================================================
DB_NAME = "humedad.db" 

def crear_tablas():
    conn = sqlite3.connect(DB_NAME) 
    cur = conn.cursor() 
    cur.execute("""
        CREATE TABLE IF NOT EXISTS lecturas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            humedad INTEGER,
            valor_sensor INTEGER,
            agua_litros REAL  
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS alertas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            tipo TEXT,
            mensaje TEXT,
            valor_sensor INTEGER
        )
    """) 
    conn.commit() 
    conn.close() 

def guardar_dato(humedad, valor_sensor, agua_litros):
    conn = sqlite3.connect(DB_NAME) 
    cur = conn.cursor() 
    cur.execute(
        "INSERT INTO lecturas (fecha, humedad, valor_sensor, agua_litros) VALUES (?, ?, ?, ?)",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), humedad, valor_sensor, agua_litros)
    ) 
    conn.commit() 
    conn.close() 

def leer_datos(dias):
    conn = sqlite3.connect(DB_NAME) 
    cur = conn.cursor() 
    cur.execute("""
        SELECT fecha, humedad, agua_litros  
        FROM lecturas
        WHERE fecha >= datetime('now', ?)
        ORDER BY fecha
    """, (f"-{dias} day",)) 
    datos = cur.fetchall() 
    conn.close() 
    return datos 

def guardar_alerta(tipo, mensaje, valor_sensor):
    conn = sqlite3.connect(DB_NAME) 
    cur = conn.cursor() 
    cur.execute(
        "INSERT INTO alertas (fecha, tipo, mensaje, valor_sensor) VALUES (?, ?, ?, ?)",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), tipo, mensaje, valor_sensor)
    ) 
    conn.commit() 
    conn.close() 

def leer_alertas():
    conn = sqlite3.connect(DB_NAME) 
    cur = conn.cursor() 
    cur.execute("""
        SELECT fecha, tipo, mensaje, valor_sensor
        FROM alertas
        ORDER BY fecha DESC
    """) 
    datos = cur.fetchall() 
    conn.close() 
    return datos 

crear_tablas() 

# ====================================================
# 📈 VARIABLES GLOBALES DE CONTROL
# ====================================================
# Inicializa en 786, que representa exactamente el 50% de tu escala real (473 celdas)
limite_riego_actual = 786  
ultimo_valor = None        
ultimo_guardado = 0        
alerta_seco_activa = False 

bomba_encendida_actualmente = False 
tiempo_inicio_riego = 0             
agua_total_acumulada = 0.0          

imagenes_planta = {} 

# ====================================================
# 🔌 COMUNICACIÓN SERIAL (USB)
# ====================================================
def enviar_comando_riego(comando):
    if puerto is not None and puerto.is_open: 
        try:
            puerto.write(f"{comando}\n".encode('utf-8')) 
            print(f"Comando enviado por USB: {comando}") 
        except Exception as e:
            print(f"Error al enviar comando: {e}") 
    else:
        print(f"ALERTA (Modo Simulación): Comando '{comando}' procesado localmente.") 

# ====================================================
# 📱 INTERFAZ GRÁFICA TKINTER
# ====================================================
app = tk.Tk() 
app.title("Monitoreo de Humedad - CONTROL REAL") 
app.geometry("360x640") 
app.resizable(False, False) 

def cargar_rostros_planta():
    global imagenes_planta
    try:
        imagenes_planta['triste'] = ImageTk.PhotoImage(Image.open("imagenes/planta_triste.png").resize((120, 120)))
        imagenes_planta['ok'] = ImageTk.PhotoImage(Image.open("imagenes/planta_ok.png").resize((120, 120)))
        imagenes_planta['feliz'] = ImageTk.PhotoImage(Image.open("imagenes/planta_feliz.png").resize((120, 120)))
        print("¡Rostros cargados con éxito desde /imagenes!")
    except Exception as e:
        print(f"Nota: No se encontraron los rostros en /imagenes, usando respaldo visual: {e}")

cargar_rostros_planta()

# --- NAVEGACIÓN ---
frame_home = tk.Frame(app, bg="#2E86DE") 
frame_graficas = tk.Frame(app, bg="white") 
frame_alertas = tk.Frame(app, bg="#F5F5F5") 
frame_ajustes = tk.Frame(app, bg="white") 

for f in (frame_home, frame_graficas, frame_alertas, frame_ajustes):
    f.place(x=360, y=0, width=360, height=580) 

frame_home.place(x=0, y=0) 

def mostrar_frame(frame):
    for f in (frame_home, frame_graficas, frame_alertas, frame_ajustes):
        f.place_forget() 
    frame.place(x=0, y=0) 
    if frame == frame_alertas:
        actualizar_alertas() 
    if frame == frame_graficas:
        actualizar_grafica() 

# ====================================================
# 🏠 PANTALLA 1: INICIO
# ====================================================
canvas = tk.Canvas(frame_home, width=360, height=580, bg="#2E86DE", highlightthickness=0) 
canvas.pack() 

CX, CY, R = 180, 220, 115 

if 'triste' in imagenes_planta:
    img_planta_dinamica = canvas.create_image(CX, CY - 15, image=imagenes_planta['triste'])
else:
    img_planta_dinamica = canvas.create_text(CX, CY - 15, text="🌵", font=("Segoe UI", 40), fill="white")

txt_porcentaje = canvas.create_text(
    CX, CY + 65, text="-- %",
    fill="white", font=("Segoe UI", 26, "bold")
) 

txt_sensor = canvas.create_text(
    CX, 410, text="Sensor: ---",
    fill="#E0E0E0", font=("Segoe UI", 12)
) 

led = canvas.create_oval(110, 403, 124, 417, fill="#FF3B30", outline="") 

txt_agua = canvas.create_text(
    CX, 440, text="Agua Usada: 0.00 L",
    fill="#A9DFBF", font=("Segoe UI", 14, "bold")
)

# --- MATEMÁTICA INTERPOLADA DE 473 CELDAS ---
def calcular_porcentaje(valor):
    if valor >= VALOR_SECO: return 0
    if valor <= VALOR_AGUA: return 100
    p = int((VALOR_SECO - valor) * 100 / (VALOR_SECO - VALOR_AGUA))
    return max(0, min(100, p))

def dibujar_barra(p):
    canvas.delete("barra") 
    x1, y1, x2, y2 = CX - R, CY - R, CX + R, CY + R 
    canvas.create_oval(x1, y1, x2, y2, width=12, outline="#4DA3FF", tags="barra") 
    color = "#FF3B30" if p < 30 else "#FFD60A" if p < 60 else "#00E676" 
    canvas.create_arc(x1, y1, x2, y2, start=90, extent=-p * 3.6, width=12, style="arc", outline=color, tags="barra") 

# ====================================================
# 🔄 NÚCLEO: LÓGICA DE ACTUALIZACIÓN EN CALIENTE
# ====================================================
def actualizar():
    global ultimo_valor, ultimo_guardado, alerta_seco_activa, limite_riego_actual
    global bomba_encendida_actualmente, tiempo_inicio_riego, agua_total_acumulada

    # Lectura del umbral interactivo en tiempo real desde la caja de texto
    str_umbral = entrada.get()
    if str_umbral.isdigit():
        limite_riego_actual = int(str_umbral)

    dato_nuevo_recibido = False

    if puerto is not None and puerto.is_open and puerto.in_waiting > 0: 
        try:
            linea = puerto.readline().decode('utf-8').strip() 
            if linea.isdigit(): 
                ultimo_valor = int(linea) 
                dato_nuevo_recibido = True 
        except Exception as e:
            pass 
            
    if puerto is None:
        dato_nuevo_recibido = True

    if ultimo_valor is not None and dato_nuevo_recibido:
        p = calcular_porcentaje(ultimo_valor) 
        canvas.itemconfig(txt_porcentaje, text=f"{p} %") 
        canvas.itemconfig(txt_sensor, text=f"Sensor: {ultimo_valor}") 
        canvas.itemconfig(led, fill="#FF3B30" if p < 10 else "#00E676") 
        dibujar_barra(p) 

        # Cambiar el rostro dinámicamente según porcentaje de celdas
        if 'triste' in imagenes_planta:
            if p < 30:
                canvas.itemconfig(img_planta_dinamica, image=imagenes_planta['triste'])
            elif 30 <= p < 60:
                canvas.itemconfig(img_planta_dinamica, image=imagenes_planta['ok'])
            else:
                canvas.itemconfig(img_planta_dinamica, image=imagenes_planta['feliz'])

        # --- ✨ AQUÍ QUEDÓ EL CANDADO DE SEGURIDAD PARA EL AIRE (1020+) ✨ ---
        if ultimo_valor >= 1020:  
            # SEGURO: Si el sensor detecta que está al aire, fuerza el apagado inmediato
            if bomba_encendida_actualmente:
                enviar_comando_riego("RIEGO_OFF")
                bomba_encendida_actualmente = False
                segundos = time.time() - tiempo_inicio_riego
                agua_total_acumulada += (segundos * LITROS_POR_SEGUNDO)
                canvas.itemconfig(txt_agua, text=f"Agua Usada: {agua_total_acumulada:.2f} L")
                
        elif ultimo_valor > limite_riego_actual: 
            # Riego normal por umbral: Si supera el valor de sequedad, enciende
            if not bomba_encendida_actualmente:
                enviar_comando_riego("RIEGO_ON")
                bomba_encendida_actualmente = True
                tiempo_inicio_riego = time.time()
        else:
            # Apagado normal: Si ya se recuperó la humedad, apaga
            if bomba_encendida_actualmente:
                enviar_comando_riego("RIEGO_OFF")
                bomba_encendida_actualmente = False
                segundos = time.time() - tiempo_inicio_riego
                agua_total_acumulada += (segundos * LITROS_POR_SEGUNDO)
                canvas.itemconfig(txt_agua, text=f"Agua Usada: {agua_total_acumulada:.2f} L")

        if p == 0 and not alerta_seco_activa:
            alerta_seco_activa = True 
            guardar_alerta("HUMEDAD CRÍTICA", "Humedad llegó a 0 %", ultimo_valor) 
        elif p > 5:
            alerta_seco_activa = False 

        # Registro síncrono cada 5 minutos
        if time.time() - ultimo_guardado >= 300:
            guardar_dato(p, ultimo_valor, round(agua_total_acumulada, 2)) 
            ultimo_guardado = time.time() 

    app.after(100, actualizar) 

# ====================================================
# 📊 PANTALLA 2: GRÁFICAS (DOBLE PANEL)
# ====================================================
tk.Label(frame_graficas, text="HISTORIAL METRICO", font=("Segoe UI", 14, "bold"), bg="white").pack(pady=2) 

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(3.3, 2.6), dpi=100, sharex=True)
fig.tight_layout(pad=1.5) 

canvas_plot = FigureCanvasTkAgg(fig, master=frame_graficas) 
canvas_plot.get_tk_widget().pack() 

tabla = ttk.Treeview(frame_graficas, columns=("fecha", "humedad", "agua"), show="headings", height=5) 
tabla.heading("fecha", text="Fecha") 
tabla.heading("humedad", text="Humedad %") 
tabla.heading("agua", text="Agua Usada") 
tabla.column("agua", width=90, anchor="center")
tabla.pack(pady=2) 

vista_actual = 1 

def actualizar_grafica():
    ax1.clear() 
    ax2.clear()
    tabla.delete(*tabla.get_children()) 

    datos = leer_datos(vista_actual) 
    if datos:
        historico_humedad = [d[1] for d in datos] 
        historico_agua = [d[2] for d in datos]

        ax1.plot(historico_humedad, color="green", linewidth=1.5) 
        ax1.set_ylabel("Hum (%)", color="green", fontsize=9)
        ax1.tick_params(axis='y', labelcolor="green", labelsize=8)
        ax1.set_xticks([]) 

        ax2.plot(historico_agua, color="blue", linewidth=1.5)
        ax2.set_ylabel("Agua (L)", color="blue", fontsize=9)
        ax2.tick_params(axis='y', labelcolor="blue", labelsize=8)
        ax2.set_xticks([])

        for fila in datos[-10:]:
            fecha, hum, ag = fila
            tabla.insert("", "end", values=(fecha, f"{hum}%", f"{ag:.2f} L")) 

    canvas_plot.draw() 

def cambiar_vista(dias):
    global vista_actual
    vista_actual = dias 
    actualizar_grafica() 

botones = tk.Frame(frame_graficas, bg="white") 
botones.pack() 

tk.Button(botones, text="DÍA", command=lambda: cambiar_vista(1)).pack(side="left", padx=5) 
tk.Button(botones, text="SEMANA", command=lambda: cambiar_vista(7)).pack(side="left", padx=5) 
tk.Button(botones, text="MES", command=lambda: cambiar_vista(30)).pack(side="left", padx=5) 

# =======================
# 🔔 PANTALLA 3: ALERTAS
# =======================
tabla_alertas = ttk.Treeview(frame_alertas, columns=("fecha", "tipo", "mensaje", "valor"), show="headings") 
tabla_alertas.heading("fecha", text="Fecha") 
tabla_alertas.heading("tipo", text="Tipo") 
tabla_alertas.heading("mensaje", text="Mensaje") 
tabla_alertas.heading("valor", text="Sensor") 

scroll_alertas = ttk.Scrollbar(frame_alertas, orient="vertical", command=tabla_alertas.yview) 
tabla_alertas.configure(yscrollcommand=scroll_alertas.set) 

tabla_alertas.pack(side="left", fill="both", expand=True) 
scroll_alertas.pack(side="right", fill="y") 

def actualizar_alertas():
    tabla_alertas.delete(*tabla_alertas.get_children()) 
    for fila in leer_alertas():
        tabla_alertas.insert("", "end", values=fila) 

# ====================================================
# ⚙️ PANTALLA 4: AJUSTES DIRECTOS
# ====================================================
tk.Label(frame_ajustes, text="Control Manual de Riego", font=("Segoe UI", 16, "bold"), bg="white").pack(pady=15) 

def activar_riego_manual():
    global bomba_encendida_actualmente, tiempo_inicio_riego
    if not bomba_encendida_actualmente:
        enviar_comando_riego("RIEGO_ON")
        bomba_encendida_actualmente = True
        tiempo_inicio_riego = time.time()

def desactivar_riego_manual():
    global bomba_encendida_actualmente, tiempo_inicio_riego, agua_total_acumulada
    if bomba_encendida_actualmente:
        enviar_comando_riego("RIEGO_OFF")
        bomba_encendida_actualmente = False
        segundos = time.time() - tiempo_inicio_riego
        agua_total_acumulada += (segundos * LITROS_POR_SEGUNDO)
        canvas.itemconfig(txt_agua, text=f"Agua Usada: {agua_total_acumulada:.2f} L")

tk.Button(frame_ajustes, text="🚀 ENCENDER BOMBA", bg="#00E676", fg="white", font=("Segoe UI", 12, "bold"), width=20, command=activar_riego_manual).pack(pady=10) 
tk.Button(frame_ajustes, text="🛑 APAGAR BOMBA", bg="#FF3B30", fg="white", font=("Segoe UI", 12, "bold"), width=20, command=desactivar_riego_manual).pack(pady=10) 

tk.Label(frame_ajustes, text="Límite de Riego Modificable (Ajuste en Vivo)", font=("Segoe UI", 12, "bold"), bg="white").pack(pady=(25, 5)) 

# Caja interactiva para el umbral que lee directo el loop()
entrada = tk.Entry(frame_ajustes, font=("Segoe UI", 12), justify="center") 
entrada.insert(0, "786")  # Punto medio perfecto (50%) para tu sensor limpio
entrada.pack(pady=5) 

# =======================
# 📱 MENÚ INFERIOR
# =======================
menu = tk.Frame(app, bg="white", height=60) 
menu.pack(fill="x", side="bottom") 

def menu_item(icon, text, frame):
    f = tk.Frame(menu, bg="white") 
    f.pack(side="left", expand=True) 
    tk.Label(f, text=icon, font=("Segoe UI Emoji", 18), bg="white").pack() 
    tk.Label(f, text=text, font=("Segoe UI", 10), bg="white").pack() 
    f.bind("<Button-1>", lambda e: mostrar_frame(frame)) 
    for w in f.winfo_children():
        w.bind("<Button-1>", lambda e: mostrar_frame(frame)) 

menu_item("🏠", "Inicio", frame_home) 
menu_item("📊", "Gráficas", frame_graficas) 
menu_item("🔔", "Alertas", frame_alertas) 
menu_item("⚙️", "Ajustes", frame_ajustes) 

# =======================
# EXECUTE
# =======================
actualizar() 
app.mainloop()