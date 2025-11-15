import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

"""Conexiones"""
# Conexión a PostgreSQL
def obtener_conexion_postgres():
    try:
        db_url = os.getenv("DATABASE_URL")
        conn = psycopg2.connect(db_url)
        print("¡Conexión a PostgreSQL exitosa! ")
        return conn
    except Exception as e:
        print(f"Error al conectar a la base de datos: {e}")
        return None
# Conexión a MongoDB
# Conexión a Redis
# Conexión a Neo4j

""" Funciones para crear tablas e insertar datos """
def crear_tablas(conn):
    try:
        cur = conn.cursor()
        
        # 1. Crear la tabla Usuario
        # Usamos SERIAL para claves primarias autoincrementales
        cur.execute("""
            CREATE TABLE IF NOT EXISTS Usuario (
                id_usuario SERIAL PRIMARY KEY,
                nombre VARCHAR(100),
                email VARCHAR(100) UNIQUE NOT NULL,
                pais VARCHAR(50),
                verificacion_kyc BOOLEAN DEFAULT FALSE,
                saldo_real NUMERIC(10, 2) DEFAULT 0,
                saldo_virtual NUMERIC(10, 2) DEFAULT 0,
                fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("Tabla 'Usuario' creada o ya existente.")

        # 2. Crear la tabla Transaccion (basado en tu DER )
        # Nota el FOREIGN KEY que la conecta con Usuario
        cur.execute("""
            CREATE TABLE IF NOT EXISTS Transaccion (
                id_transaccion SERIAL PRIMARY KEY,
                id_usuario INT NOT NULL,
                tipo VARCHAR(50),
                monto NUMERIC(10, 2),
                medio VARCHAR(50),
                estado VARCHAR(50),
                cumplimiento_aml BOOLEAN DEFAULT FALSE,
                fecha_transaccion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                CONSTRAINT fk_usuario
                    FOREIGN KEY(id_usuario) 
                    REFERENCES Usuario(id_usuario)
            );
        """)
        print("Tabla 'Transaccion' creada o ya existente.")
        
        # 3. Crear la tabla Mesa (basado en tu DER )
        cur.execute("""
            CREATE TABLE IF NOT EXISTS Mesa (
                id_mesa SERIAL PRIMARY KEY,
                modalidad VARCHAR(50),
                ciegas VARCHAR(50),
                max_jugadores INT,
                tipo VARCHAR(50) 
            );
        """)
        print("Tabla 'Mesa' creada o ya existente.")
        
        # ... Aquí agregarías el RESTO de tus CREATE TABLE ...
        # (Torneo, Mano, Jugada, Metodo_Pago, etc.)

        # Guardamos todos los cambios (DDL)
        conn.commit()
        print("Todas las tablas han sido creadas.")
        
    except Exception as e:
        print(f"Error al crear las tablas: {e}")
        conn.rollback() # Revertir cambios si hay un error
    finally:
        if cur:
            cur.close()

def insertar_usuario_terminal(conn):
    """
    Pide datos por terminal e inserta un nuevo Usuario.
    """
    try:
        # 1. Pedir datos por terminal
        print("\n--- Insertar Nuevo Usuario ---")
        nombre = input("Nombre del usuario: ")
        email = input("Email del usuario: ")
        pais = input("País del usuario: ")

        # 2. Preparar el query de INSERCIÓN
        # ¡¡IMPORTANTE!! Usamos (%s, %s, %s) para evitar SQL Injection.
        # psycopg2 reemplazará los %s de forma segura.
        query = """
            INSERT INTO Usuario (nombre, email, pais)
            VALUES (%s, %s, %s)
            RETURNING id_usuario;
        """
        
        # 3. Ejecutar el query
        cur = conn.cursor()
        cur.execute(query, (nombre, email, pais))
        
        # 4. Confirmar la transacción
        conn.commit()
        
        # 5. (Opcional) Obtener el ID del usuario recién creado
        id_nuevo = cur.fetchone()[0]
        print(f"¡Usuario '{nombre}' insertado con éxito! (ID: {id_nuevo})")

    except Exception as e:
        print(f"Error al insertar usuario: {e}")
        conn.rollback() # Revertir si algo falla
    finally:
        if cur:
            cur.close()
    
