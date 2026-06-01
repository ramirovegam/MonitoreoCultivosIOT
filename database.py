"""
===========================================================
 MÓDULO: Base de Datos - Sistema de Humedad
 AUTOR: Ramiro Vega Meza
===========================================================

DESCRIPCIÓN GENERAL:
Este archivo se encarga de gestionar la base de datos del
sistema de monitoreo de humedad del suelo. Utiliza SQLite
para almacenar tanto las lecturas del sensor como las
alertas generadas por el sistema.

FUNCIONALIDADES:
- Crear la base de datos si no existe
- Crear tablas necesarias (lecturas y alertas)
- Guardar datos del sensor
- Guardar eventos o alertas del sistema
- Leer datos almacenados
- Consultar historial reciente de alertas

BASE DE DATOS:
- Nombre del archivo: humedad.db
- Tipo: SQLite (base de datos local)

TABLAS:
1. lecturas
   - id: identificador único
   - fecha: fecha y hora del registro
   - humedad: porcentaje calculado
   - valor_sensor: valor crudo del sensor (0 - 1023)

2. alertas
   - id: identificador único
   - fecha: fecha y hora del evento
   - tipo: tipo de alerta (ej: "SECO", "RIEGO")
   - mensaje: descripción del evento
   - valor_sensor: valor del sensor en ese momento

FLUJO DE USO:
1. Se crea la conexión a la base de datos
2. Se crean las tablas si no existen
3. Se guardan lecturas periódicamente
4. Se registran alertas cuando hay condiciones críticas
5. La aplicación consulta los datos para mostrarlos

DEPENDENCIAS:
- sqlite3 (gestión de base de datos)
- datetime (registro de fecha y hora)

NOTAS IMPORTANTES:
- Todos los registros incluyen timestamp automático
- Se recomienda crear las tablas al iniciar la aplicación
- Este módulo puede ser importado por otros archivos
- DB_NAME debe estar definido correctamente

===========================================================
"""


import sqlite3
from datetime import datetime
import database


def conectar():
    return sqlite3.connect("humedad.db")

def crear_tabla():
    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS lecturas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT,
        humedad INTEGER,
        valor_sensor INTEGER
    )
    """)

    conn.commit()
    conn.close()

def guardar_dato(humedad, valor_sensor):
    conn = conectar()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO lecturas (fecha, humedad, valor_sensor) VALUES (?, ?, ?)",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), humedad, valor_sensor)
    )

    conn.commit()
    conn.close()

def crear_tabla_alertas():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
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

def guardar_alerta(tipo, mensaje, valor_sensor):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO alertas (fecha, tipo, mensaje, valor_sensor) VALUES (?, ?, ?, ?)",
        (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            tipo,
            mensaje,
            valor_sensor
        )
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
        LIMIT 20
    """)
    datos = cur.fetchall()
    conn.close()
    return datos