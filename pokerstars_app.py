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

def ask(text):
    return input(text + ": ").strip()

# ======================================
#    LÓGICA DE POSTGRESQL (Master DB)
# ======================================

def crear_tablas_postgres(conn):
    SQL_SCHEMA = """
    CREATE TABLE usuario (
        id_usuario SERIAL PRIMARY KEY,
        nombre VARCHAR(100) NOT NULL,
        pais VARCHAR(50),
        verificacion_kyc BOOLEAN DEFAULT FALSE,
        email VARCHAR(150) UNIQUE NOT NULL,
        fecha_registro TIMESTAMP DEFAULT NOW(),
        saldo_real NUMERIC(12,2) DEFAULT 0.00,
        saldo_fichas NUMERIC(12,2) DEFAULT 0.00
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
        id_usuario INT NOT NULL REFERENCES usuario(id_usuario) ON DELETE CASCADE,
        tipo VARCHAR(50) NOT NULL,
        datos_encriptados TEXT,
        estado VARCHAR(20) DEFAULT 'activo',
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
        cartas_repartidas TEXT,
        ganador_id INT REFERENCES usuario(id_usuario),
        modalidad VARCHAR(50)
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

def crear_usuario(pg_con):
    nombre = ask("Nombre del usuario")
    email = ask("Email del usuario")
    pais = ask("País del usuario")
    
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

def crear_transaccion(pg_con):
    id_usuario = int(ask("ID Usuario"))
    id_metodo = int(ask("ID Método de pago")) # Asumimos que ya existe
    monto = float(ask("Monto"))
    tipo = ask("Tipo (deposito/retiro)")
    
    query_pg = """
        INSERT INTO Transaccion (id_usuario, id_metodo, monto, tipo, estado)
        VALUES (%s, %s, %s, %s, 'completada') RETURNING id_transaccion, fecha;
    """
    
    try:
        cur = pg_con.cursor()
        cur.execute(query_pg, (id_usuario, id_metodo, monto, tipo))
        id_transaccion = cur.fetchone()
        
        # Actualizar saldo en Postgres
        op = "+" if tipo == "deposito" else "-"
        cur.execute(f"UPDATE Usuario SET saldo_real = saldo_real {op} %s WHERE id_usuario = %s RETURNING saldo_real;", (monto, id_usuario))
        pg_con.commit()
        cur.close()
        print(f"✔️ Transacción {id_transaccion} creada en PostgreSQL.")
        
    except Exception as e:
        print(f"❌ Error al crear transacción: {e}")
        pg_con.rollback()

def registrar_jugador_en_mesa(pg_con):
    id_usuario = int(ask("ID Usuario a sentar"))
    id_mesa = int(ask("ID Mesa a la que entra"))
    
    query_pg = "INSERT INTO Usuario_Mesa (id_usuario, id_mesa) VALUES (%s, %s);"
    
    try:
        cur = pg_con.cursor()
        cur.execute(query_pg, (id_usuario, id_mesa))
        pg_con.commit()
        cur.close()
        print(f"✔️ Usuario {id_usuario} sentado en mesa {id_mesa} en PostgreSQL.")

    except Exception as e:
        print(f"❌ Error al sentar jugador: {e}")
        pg_con.rollback()

# ====================================
#    ETL BAJO DEMANDA
# ====================================

def sync_usuario_to_mongo(pg_con, mongo_db, id_usuario):
    """Sincroniza UN usuario específico a MongoDB"""
    try:
        cur = pg_con.cursor()
        cur.execute("""
            SELECT id_usuario, nombre, email, pais, saldo_real, saldo_fichas
            FROM usuario WHERE id_usuario = %s
        """, (id_usuario,))
        
        row = cur.fetchone()
        cur.close()
        
        if row:
            usuario_doc = {
                'id_usuario': row[0],
                'nombre': row[1],
                'email': row[2],
                'pais': row[3],
                'saldo_real': float(row[4]) if row[4] else 0.0,
                'saldo_fichas': float(row[5]) if row[5] else 0.0,
                'balance_neto': 0.0,  # Se calculará con manos
                'manos_jugadas': 0
            }
            
            mongo_db.usuarios.update_one(
                {'id_usuario': id_usuario},
                {'$set': usuario_doc},
                upsert=True
            )
            return True
    except Exception as e:
        print(f"⚠️ Error sincronizando usuario {id_usuario}: {e}")
        return False

def sync_all_usuarios_to_mongo(pg_con, mongo_db):
    """Sincroniza TODOS los usuarios a MongoDB (para casos de uso)"""
    print("🔄 Sincronizando usuarios desde PostgreSQL a MongoDB...")
    try:
        cur = pg_con.cursor()
        cur.execute("""
            SELECT u.id_usuario, u.nombre, u.email, u.pais, u.saldo_real, u.saldo_fichas,
                   COALESCE(SUM(um.ganancia), 0) as balance_neto,
                   COUNT(DISTINCT um.id_mano) as manos_jugadas
            FROM usuario u
            LEFT JOIN usuario_mano um ON u.id_usuario = um.id_usuario
            GROUP BY u.id_usuario
        """)
        
        usuarios = cur.fetchall()
        cur.close()
        
        for row in usuarios:
            usuario_doc = {
                'id_usuario': row[0],
                'nombre': row[1],
                'email': row[2],
                'pais': row[3],
                'saldo_real': float(row[4]) if row[4] else 0.0,
                'saldo_fichas': float(row[5]) if row[5] else 0.0,
                'balance_neto': float(row[6]) if row[6] else 0.0,
                'manos_jugadas': row[7]
            }
            
            mongo_db.usuarios.update_one(
                {'id_usuario': row[0]},
                {'$set': usuario_doc},
                upsert=True
            )
        
        print(f"✅ {len(usuarios)} usuarios sincronizados a MongoDB")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def sync_manos_to_mongo(pg_con, mongo_db):
    """Sincroniza manos con toda su info desnormalizada"""
    print("🔄 Sincronizando manos desde PostgreSQL a MongoDB...")
    try:
        cur = pg_con.cursor()
        cur.execute("""
            SELECT m.id_mano, m.id_mesa, m.rake, m.bote_total, m.fecha_hora,
                   m.ganador_id, m.modalidad, ms.tipo as tipo_mesa
            FROM mano m
            JOIN mesa ms ON m.id_mesa = ms.id_mesa
        """)
        
        manos = cur.fetchall()
        
        for row in manos:
            mano_doc = {
                'id_mano': row[0],
                'id_mesa': row[1],
                'rake': float(row[2]) if row[2] else 0.0,
                'bote_total': float(row[3]) if row[3] else 0.0,
                'fecha_hora': row[4],
                'ganador_id': row[5],
                'modalidad': row[6],
                'tipo_mesa': row[7]
            }
            
            mongo_db.manos.update_one(
                {'id_mano': row[0]},
                {'$set': mano_doc},
                upsert=True
            )
        
        cur.close()
        print(f"✅ {len(manos)} manos sincronizadas a MongoDB")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def sync_transacciones_to_mongo(pg_con, mongo_db):
    """Sincroniza transacciones con info desnormalizada"""
    print("🔄 Sincronizando transacciones desde PostgreSQL a MongoDB...")
    try:
        cur = pg_con.cursor()
        cur.execute("""
            SELECT t.id_transaccion, t.id_usuario, u.nombre, mp.tipo as medio,
                   t.fecha, t.monto, t.estado, t.tipo
            FROM transaccion t
            JOIN usuario u ON t.id_usuario = u.id_usuario
            JOIN metodo_pago mp ON t.id_metodo = mp.id_metodo
        """)
        
        transacciones = cur.fetchall()
        
        for row in transacciones:
            trans_doc = {
                'id_transaccion': row[0],
                'id_usuario': row[1],
                'usuario_nombre': row[2],
                'medio': row[3],
                'fecha': row[4],
                'monto': float(row[5]) if row[5] else 0.0,
                'estado': row[6],
                'tipo': row[7]
            }
            
            mongo_db.transacciones.update_one(
                {'id_transaccion': row[0]},
                {'$set': trans_doc},
                upsert=True
            )
        
        cur.close()
        print(f"✅ {len(transacciones)} transacciones sincronizadas a MongoDB")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def sync_usuarios_mesas_to_neo4j(pg_con, neo4j_driver):
    """Sincroniza relaciones Usuario-Mesa a Neo4j"""
    print("🔄 Sincronizando relaciones Usuario-Mesa a Neo4j...")
    try:
        cur = pg_con.cursor()
        
        # Sincronizar usuarios
        cur.execute("SELECT id_usuario, nombre FROM usuario")
        usuarios = cur.fetchall()
        
        with neo4j_driver.session() as session:
            for id_usuario, nombre in usuarios:
                session.run("""
                    MERGE (u:Usuario {id_usuario: $id_usuario})
                    SET u.nombre = $nombre
                """, {'id_usuario': id_usuario, 'nombre': nombre})
        
        # Sincronizar mesas
        cur.execute("SELECT id_mesa, modalidad, tipo FROM mesa")
        mesas = cur.fetchall()
        
        with neo4j_driver.session() as session:
            for id_mesa, modalidad, tipo in mesas:
                session.run("""
                    MERGE (m:Mesa {id_mesa: $id_mesa})
                    SET m.modalidad = $modalidad, m.tipo = $tipo
                """, {'id_mesa': id_mesa, 'modalidad': modalidad, 'tipo': tipo})
        
        # Sincronizar relaciones
        cur.execute("SELECT id_usuario, id_mesa FROM usuario_mesa")
        relaciones = cur.fetchall()
        
        with neo4j_driver.session() as session:
            for id_usuario, id_mesa in relaciones:
                session.run("""
                    MATCH (u:Usuario {id_usuario: $id_usuario})
                    MATCH (m:Mesa {id_mesa: $id_mesa})
                    MERGE (u)-[r:JUGO_EN]->(m)
                """, {'id_usuario': id_usuario, 'id_mesa': id_mesa})
        
        cur.close()
        print(f"✅ {len(relaciones)} relaciones sincronizadas a Neo4j")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

# ====================================
#    LÓGICA DE MONGODB (Casos 1-6)
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

def caso5_rake_por_mesa(db):
    print("\n[MongoDB] 💸 5. Análisis de rake generado por mesa")
    pipeline = [
        { "$group": {
            "_id": "$id_mesa",
            "rake_total": { "$sum": "$rake" },
            "manos_jugadas": { "$count": {} }
        }},
        { "$sort": { "rake_total": -1 }},
        { "$limit": 10 }
    ]
    resultados = list(db.manos.aggregate(pipeline))
    for r in resultados:
        print(f"Mesa {r['_id']}: ${r['rake_total']:.2f} rake, {r['manos_jugadas']} manos")

def caso6_usuarios_por_pais(db):
    print("\n[MongoDB] 🌍 6. Distribución de usuarios por país")
    pipeline = [
        { "$group": {
            "_id": "$pais",
            "total_usuarios": { "$count": {} }
        }},
        { "$sort": { "total_usuarios": -1 }}
    ]
    resultados = list(db.usuarios.aggregate(pipeline))
    for r in resultados:
        print(f"{r['_id']}: {r['total_usuarios']} usuarios")

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
            elif op == '4':
                registrar_jugador_en_mesa(pg_con)
            elif op == '5':
                simular_juego(redis_con)
            
            elif op == '6':
                print("\n--- Casos de Uso MongoDB ---")
                caso1_volumen_modalidad(mongo_db)
                caso2_top10_balance(mongo_db)
                caso3_manos_1000_septiembre(mongo_db)
                caso4_depositos_paypal(mongo_db)
                caso5_rake_por_mesa(mongo_db)
                caso6_usuarios_por_pais(mongo_db)
            
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