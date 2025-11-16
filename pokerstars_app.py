import os
import psycopg2
from pymongo import MongoClient
import redis
from neo4j import GraphDatabase
from dotenv import load_dotenv
import time
import datetime

# ===================================
#   CONEXIONES A LAS BASES DE DATOS
# ===================================

def get_postgres():
    try:
        db_url = os.getenv("DATABASE_URL")
        conn = psycopg2.connect(db_url)
        print("✔️  Conexión a PostgreSQL (Railway) exitosa.")
        return conn
    except Exception as e:
        print(f"❌ ERROR PostgreSQL: {e}")
        return None

# MongoDB Atlas devuelve la base de datos 'pokerstars'
def get_mongo_client():
    try:
        mongo_uri = os.getenv("MONGO_URI")
        client = MongoClient(mongo_uri)
        db = client['pokerstars'] # Selecciona tu base de datos
        print("✔️  Conexión a MongoDB (Atlas) exitosa.")
        return db
    except Exception as e:
        print(f"❌ ERROR MongoDB: {e}")
        return None

def get_redis():
    try:
        r = redis.Redis(
            host=os.getenv("REDIS_HOST"),
            port=int(os.getenv("REDIS_PORT")),
            password=os.getenv("REDIS_PASSWORD"),
            decode_responses=True # Para que devuelva strings
        )
        r.ping()
        print("✔️  Conexión a Redis (Cloud) exitosa.")
        return r
    except Exception as e:
        print(f"❌ ERROR Redis: {e}")
        return None

def get_neo4j_driver():
    try:
        uri = os.getenv("NEO4J_URI")
        user = os.getenv("NEO4J_USER")
        password = os.getenv("NEO4J_PASSWORD")
        driver = GraphDatabase.driver(uri, auth=(user, password))
        driver.verify_connectivity()
        print("✔️  Conexión a Neo4j (Local) exitosa.")
        return driver
    except Exception as e:
        print(f"❌ ERROR Neo4j: {e}")
        return None

# ================
#   INPUT HELPER
# ================

def ask(text):
    return input(text + ": ").strip()

# =======================================
#   1. LÓGICA DE POSTGRESQL (Master DB)
# =======================================

def crear_tablas_postgres(conn):
    SQL_SCHEMA = """
    CREATE TABLE usuario (
        id_usuario SERIAL PRIMARY KEY,
        nombre VARCHAR(100) NOT NULL,
        pais VARCHAR(50),
        verificacion_kyc BOOLEAN DEFAULT FALSE,
        email VARCHAR(150) UNIQUE NOT NULL,
        fecha_registro TIMESTAMP DEFAULT NOW()
    );

    CREATE TABLE promocion (
        id_promocion SERIAL PRIMARY KEY,
        nombre_promocion VARCHAR(100) NOT NULL,
        estado VARCHAR(20),
        descuento NUMERIC(5,2),
        fecha_inicio DATE,
        fecha_fin DATE
    );

    CREATE TABLE usuario_promocion (
        id_usuario INT REFERENCES usuario(id_usuario),
        id_promocion INT REFERENCES promocion(id_promocion),
        PRIMARY KEY (id_usuario, id_promocion)
    );

    CREATE TABLE metodo_pago (
        id_metodo SERIAL PRIMARY KEY,
        tipo VARCHAR(50),
        datos_encriptados TEXT,
        estado VARCHAR(20)
    );

    CREATE TABLE transaccion (
        id_transaccion SERIAL PRIMARY KEY,
        id_usuario INT NOT NULL REFERENCES usuario(id_usuario),
        id_metodo INT NOT NULL REFERENCES metodo_pago(id_metodo),
        fecha TIMESTAMP DEFAULT NOW(),
        monto NUMERIC(12,2) NOT NULL,
        estado VARCHAR(20),
        cumplimiento_aml BOOLEAN DEFAULT FALSE,
        tipo VARCHAR(50)
    );

    CREATE TABLE torneo (
        id_torneo SERIAL PRIMARY KEY,
        nombre VARCHAR(100) NOT NULL,
        hora_inicio TIMESTAMP,
        tipo VARCHAR(50),
        modalidad VARCHAR(50),
        reglas TEXT,
        buy_in NUMERIC(10,2),
        max_jugadores INT
    );

    CREATE TABLE mesa (
        id_mesa SERIAL PRIMARY KEY,
        modalidad VARCHAR(50),
        tipo VARCHAR(50),
        reglas TEXT,
        max_jugadores INT,
        ciegas VARCHAR(50),
        id_torneo INT REFERENCES torneo(id_torneo)
    );

    CREATE TABLE usuario_mesa (
        id_usuario INT REFERENCES usuario(id_usuario),
        id_mesa INT REFERENCES mesa(id_mesa),
        PRIMARY KEY (id_usuario, id_mesa)
    );

    CREATE TABLE usuario_torneo (
        id_usuario INT REFERENCES usuario(id_usuario),
        id_torneo INT REFERENCES torneo(id_torneo),
        PRIMARY KEY (id_usuario, id_torneo)
    );

    CREATE TABLE mano (
        id_mano SERIAL PRIMARY KEY,
        id_mesa INT NOT NULL REFERENCES mesa(id_mesa),
        id_usuario INT NOT NULL REFERENCES usuario(id_usuario),
        rake NUMERIC(10,2),
        bote_total NUMERIC(12,2),
        fecha_hora TIMESTAMP DEFAULT NOW(),
        cartas_repartidas TEXT
    );

    CREATE TABLE usuario_mano (
        id_usuario INT REFERENCES usuario(id_usuario),
        id_mano INT REFERENCES mano(id_mano),
        PRIMARY KEY (id_usuario, id_mano)
    );

    CREATE TABLE jugada (
        id_jugada SERIAL PRIMARY KEY,
        id_mano INT NOT NULL REFERENCES mano(id_mano),
        id_usuario INT NOT NULL REFERENCES usuario(id_usuario),
        monto_apostado NUMERIC(10,2),
        ronda VARCHAR(50),
        accion VARCHAR(50)
    );
"""

    try:
        cur = conn.cursor()
        cur.execute(SQL_SCHEMA)
        conn.commit()
        cur.close()
        print("✔️ Tablas de PostgreSQL creadas (o ya existentes).")
        
    except Exception as e:
        print(f"❌ Error al crear tablas: {e}")
        conn.rollback()

# Crea el Usuario en Postgres
def crear_usuario(pg_con):
    nombre = ask("Nombre del usuario")
    email = ask("Email del usuario")
    pais = ask("País del usuario")
    
    # 1. Escribir en PostgreSQL
    query_pg = "INSERT INTO Usuario (nombre, email, pais) VALUES (%s, %s, %s) RETURNING id_usuario, saldo_real;"
    
    try:
        cur = pg_con.cursor()
        cur.execute(query_pg, (nombre, email, pais))
        id_usuario, saldo_real = cur.fetchone()
        pg_con.commit()
        cur.close()
        print(f"✔️ Usuario {id_usuario} creado en PostgreSQL.")
        
    except Exception as e:
        print(f"❌ Error al crear usuario: {e}")
        pg_con.rollback()

# Escribe en PG, Mongo y Redis
def crear_transaccion(pg_con, mongo_db, redis_con):
    id_usuario = int(ask("ID Usuario"))
    id_metodo = int(ask("ID Método de pago")) # Asumimos que ya existe
    monto = float(ask("Monto"))
    tipo = ask("Tipo (deposito/retiro)")
    
    # 1. Escribir en PostgreSQL
    query_pg = """
        INSERT INTO Transaccion (id_usuario, id_metodo, monto, tipo, estado)
        VALUES (%s, %s, %s, %s, 'completada') RETURNING id_transaccion, fecha;
    """
    
    try:
        cur = pg_con.cursor()
        cur.execute(query_pg, (id_usuario, id_metodo, monto, tipo))
        id_transaccion, fecha_transaccion = cur.fetchone()
        
        # Actualizar saldo en Postgres
        op = "+" if tipo == "deposito" else "-"
        cur.execute(f"UPDATE Usuario SET saldo_real = saldo_real {op} %s WHERE id_usuario = %s RETURNING saldo_real;", (monto, id_usuario))
        nuevo_saldo = cur.fetchone()[0]
        pg_con.commit()
        cur.close()
        print(f"✔️ Transacción {id_transaccion} creada en PostgreSQL.")

        # 2. Escribir en MongoDB
        # Obtenemos el 'tipo' del método de pago desde PG para desnormalizar
        cur = pg_con.cursor()
        cur.execute("SELECT tipo FROM Metodo_Pago WHERE id_metodo = %s", (id_metodo,))
        tipo_metodo = cur.fetchone()[0]
        cur.close()
        
        coleccion_transacciones = mongo_db['transacciones']
        documento_transaccion = {
            "id_transaccion": id_transaccion,
            "id_usuario": id_usuario,
            "id_metodo": id_metodo,
            "medio": tipo_metodo, # Ej: 'PayPal' (Desnormalizado para Caso 4)
            "monto": monto,
            "tipo": tipo,
            "fecha": fecha_transaccion
        }
        coleccion_transacciones.insert_one(documento_transaccion)
        print(f"✔️ Transacción {id_transaccion} copiada a MongoDB.")
        
        # 3. Escribir en Redis
        user_cache_key = f"user_balance:{id_usuario}"
        redis_con.set(user_cache_key, float(nuevo_saldo), ex=300) # TTL de 5 min
        print(f"✔️ Cache de balance para usuario {id_usuario} actualizado en Redis.")
        
    except Exception as e:
        print(f"❌ Error al crear transacción: {e}")
        pg_con.rollback()

# Escribe en Postgres y Neo4j para casos 9 y 10
def registrar_jugador_en_mesa(pg_con, neo4j_driver):
    id_usuario = int(ask("ID Usuario a sentar"))
    id_mesa = int(ask("ID Mesa a la que entra"))
    
    # 1. Escribir en PostgreSQL
    query_pg = "INSERT INTO Usuario_Mesa (id_usuario, id_mesa) VALUES (%s, %s);"
    
    try:
        cur = pg_con.cursor()
        cur.execute(query_pg, (id_usuario, id_mesa))
        pg_con.commit()
        cur.close()
        print(f"✔️ Usuario {id_usuario} sentado en mesa {id_mesa} en PostgreSQL.")
        
        # 2. Escribir en Neo4j
        query_neo4j = """
            MERGE (u:Usuario {id_usuario: $id_usuario})
            MERGE (m:Mesa {id_mesa: $id_mesa})
            MERGE (u)-[:JUGO_EN]->(m)
        """
        with neo4j_driver.session() as session:
            session.run(query_neo4j, id_usuario=id_usuario, id_mesa=id_mesa)
        print(f"✔️ Relación (Usuario)-[:JUGO_EN]->(Mesa) creada en Neo4j.")

    except Exception as e:
        print(f"❌ Error al sentar jugador: {e}")
        pg_con.rollback()

# ====================================
#   2. LÓGICA DE MONGODB (Casos 1-6)
# ====================================

def caso1_volumen_modalidad(db):
    print("\n[MongoDB] 📊 1. Volumen jugado por modalidad (última semana)")
    hace_7_dias = datetime.datetime.now() - datetime.timedelta(days=7)
    pipeline = [
        { "$match": { "fecha_hora": { "$gte": hace_7_dias } } },
        { "$group": {
            "_id": "$modalidad", # 'modalidad' debe estar en la colección 'manos'
            "volumen_total": { "$sum": "$bote_total" }
        }}
    ]
    resultados = list(db.manos.aggregate(pipeline))
    print(resultados)

def caso2_top10_balance(db):
    print("\n[MongoDB] 💰 2. Top 10 jugadores con mayor balance neto")
    resultados = list(db.usuarios.find().sort("balance_neto", -1).limit(10))
    print(resultados)

def caso3_manos_1000_septiembre(db):
    print("\n[MongoDB] 🔥 3. Manos con bote > 1000 USD en septiembre")
    # Asume que 'fecha_hora' es un objeto datetime
    resultados = list(db.manos.find({
        "bote_total": { "$gt": 1000 },
        "$expr": { "$eq": [{ "$month": "$fecha_hora" }, 9] }
    }))
    print(resultados)

def caso4_depositos_paypal(db):
    print("\n[MongoDB] 💳 4. Depósitos de un usuario por PayPal")
    user_id = int(ask("ID Usuario"))
    resultados = list(db.transacciones.find({
        "id_usuario": user_id,
        "tipo": "deposito",
        "medio": "PayPal" # Asume que este campo se desnormalizó
    }))
    print(resultados)

# Faltan aplicar casos 5 y 6

# ====================================
#   3. LÓGICA DE REDIS (Casos 7-8)
# ====================================

# Asume que 'simular_juego' se llama cada vez que un jugador juega una mano
def simular_juego(redis_con):
    id_usuario = ask("ID Usuario que jugó una mano")
    # ZINCRBY: Incrementa el score del 'id_usuario' en el set 'ranking_activos' en 1
    redis_con.zincrby("ranking_activos", 1, id_usuario)
    print(f"Actividad de {id_usuario} registrada en Redis.")

def caso7_ranking(r):
    print("\n[Redis] 🏆 7. Ranking de jugadores activos (Top 5)")
    # ZREVRANGE: Obtener el ranking en orden descendente
    resultados = r.zrevrange("ranking_activos", 0, 4, withscores=True)
    print(resultados)

def caso8_balance_cache(r, pg_con):
    print("\n[Redis] 🧠 8. Balance en cache (TTL 5 min)")
    id_usuario = int(ask("ID Usuario a consultar balance"))
    user_key = f"user_balance:{id_usuario}"
    
    # 1. Intentar leer de Redis
    cached_balance = r.get(user_key)
    
    if cached_balance:
        print(f"✔️ Balance obtenido DESDE CACHÉ: {cached_balance}")
    else:
        # 2. Si falla, leer de PostgreSQL (Master)
        print("... Cache miss. Consultando PostgreSQL ...")
        try:
            cur = pg_con.cursor()
            cur.execute("SELECT saldo_real FROM Usuario WHERE id_usuario = %s", (id_usuario,))
            resultado = cur.fetchone()
            cur.close()
            
            if resultado:
                balance_pg = float(resultado[0])
                # 3. Guardar en Redis para la próxima vez
                r.set(user_key, balance_pg, ex=300) # ex=300 -> 5 minutos TTL
                print(f"✔️ Balance obtenido DESDE POSTGRES: {balance_pg} (y guardado en caché)")
            else:
                print(f"❌ Usuario {id_usuario} no encontrado en PostgreSQL.")
        except Exception as e:
            print(f"❌ Error al consultar PostgreSQL: {e}")

# ============================================================
#   4. LÓGICA DE NEO4J (Casos 9-10)
# ============================================================
# Asume que 'registrar_jugador_en_mesa' se ha usado varias veces

def caso9_usuarios_dos_mesas(driver):
    print("\n[Neo4j] 🎯 9. Usuarios que jugaron en ≥2 mesas distintas")
    query = """
        MATCH (u:Usuario)-[:JUGO_EN]->(m:Mesa)
        WITH u, count(DISTINCT m) as mesas_jugadas
        WHERE mesas_jugadas >= 2
        RETURN u.id_usuario, mesas_jugadas
        ORDER BY mesas_jugadas DESC;
    """
    with driver.session() as session:
        resultados = session.run(query).data()
        print(resultados)

def caso10_colusion(driver):
    print("\n[Neo4j] 🚨 10. Detección de clusters de colusión (Top 5 pares)")
    query = """
        MATCH (u1:Usuario)-[:JUGO_EN]->(m:Mesa)<-[:JUGO_EN]-(u2:Usuario)
        WHERE id(u1) < id(u2)
        WITH u1, u2, count(m) as mesas_compartidas
        WHERE mesas_compartidas > 2
        RETURN u1.id_usuario, u2.id_usuario, mesas_compartidas
        ORDER BY mesas_compartidas DESC
        LIMIT 5;
    """
    with driver.session() as session:
        resultados = session.run(query).data()
        print(resultados)

# ============================================================
#   MENÚ PRINCIPAL (ORQUESTADOR)
# ============================================================

def main():
    # 1. Cargar .env
    load_dotenv()
    
    # 2. Iniciar todas las conexiones
    pg_con = get_postgres()
    mongo_db = get_mongo_client()
    redis_con = get_redis()
    neo4j_driver = get_neo4j_driver()
    
    if not all([pg_con, mongo_db, redis_con, neo4j_driver]):
        print("Faltan conexiones de base de datos. Saliendo.")
        return

    while True:
        print("\n===================================")
        print("       POKERSTARS DATA MANAGER")
        print("===================================")
        print("--- Admin (PostgreSQL) ---")
        print("1. (SOLO 1 VEZ) Crear Tablas en PostgreSQL")
        print("--- Escritura (Orquestada) ---")
        print("2. Crear Nuevo Usuario (PG + Mongo)")
        print("3. Crear Transacción (PG + Mongo + Redis)")
        print("4. Registrar Jugador en Mesa (PG + Neo4j)")
        print("5. (Simular) Jugador juega una mano (Redis)")
        print("--- Lectura (Casos de Uso NoSQL) ---")
        print("6. Ver Casos de Uso (MongoDB)")
        print("7. Ver Casos de Uso (Redis)")
        print("8. Ver Casos de Uso (Neo4j)")
        print("s. Salir")
        
        op = ask("Opción")

        try:
            if op == '1':
                crear_tablas_postgres(pg_con)
            elif op == '2':
                crear_usuario(pg_con)
            elif op == '3':
                crear_transaccion(pg_con)
            elif op == '4.':
                registrar_jugador_en_mesa(pg_con)
            elif op == '5':
                simular_juego(redis_con)
            
            elif op == '6':
                print("\n--- Casos de Uso MongoDB ---")
                caso1_volumen_modalidad(mongo_db)
                caso2_top10_balance(mongo_db)
                caso3_manos_1000_septiembre(mongo_db)
                caso4_depositos_paypal(mongo_db)
                # (Llamar a casos 5 y 6 aquí)
            
            elif op == '7':
                print("\n--- Casos de Uso Redis ---")
                caso7_ranking(redis_con)
                caso8_balance_cache(redis_con, pg_con)

            elif op == '8':
                print("\n--- Casos de Uso Neo4j ---")
                caso9_usuarios_dos_mesas(neo4j_driver)
                caso10_colusion(neo4j_driver)

            elif op == 's':
                print("Cerrando todas las conexiones...")
                pg_con.close()
                neo4j_driver.close()
                # Mongo y Redis no requieren cierre explícito de la misma forma
                break
            else:
                print("Opción no válida.")
                
        except Exception as e:
            print(f"❌ ERROR INESPERADO: {e}")
            print("... revirtiendo cambios en PostgreSQL ...")
            pg_con.rollback()

if __name__ == "__main__":
    main()