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
        db_url = os.getenv("DATABASE_PUBLIC_URL")
        if not db_url:
            raise ValueError("No se encontró DATABASE_PUBLIC_URL ni DATABASE_URL en .env")
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
        user = os.getenv("NEO4J_USERNAME")
        password = os.getenv("NEO4J_PASSWORD")
        driver = GraphDatabase.driver(uri, auth=(user, password))
        driver.verify_connectivity()
        print("✔️  Conexión a Neo4j (Aura) exitosa.")
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
        estado VARCHAR(20) DEFAULT 'activo'
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
    
    query_pg = "INSERT INTO usuario (nombre, email, pais) VALUES (%s, %s, %s) RETURNING id_usuario, saldo_real;"
    
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
        INSERT INTO transaccion (id_usuario, id_metodo, monto, tipo, estado)
        VALUES (%s, %s, %s, %s, 'completada') RETURNING id_transaccion, fecha;
    """
    
    try:
        cur = pg_con.cursor()
        cur.execute(query_pg, (id_usuario, id_metodo, monto, tipo))
        id_transaccion = cur.fetchone()
        
        # Actualizar saldo en Postgres
        op = "+" if tipo == "deposito" else "-"
        cur.execute(f"UPDATE usuario SET saldo_real = saldo_real {op} %s WHERE id_usuario = %s RETURNING saldo_real;", (monto, id_usuario))
        pg_con.commit()
        cur.close()
        print(f"✔️ Transacción {id_transaccion} creada en PostgreSQL.")
        
    except Exception as e:
        print(f"❌ Error al crear transacción: {e}")
        pg_con.rollback()

def registrar_jugador_en_mesa(pg_con):
    id_usuario = int(ask("ID Usuario a sentar"))
    id_mesa = int(ask("ID Mesa a la que entra"))
    
    query_pg = "INSERT INTO usuario_mesa (id_usuario, id_mesa) VALUES (%s, %s);"
    
    try:
        cur = pg_con.cursor()
        cur.execute(query_pg, (id_usuario, id_mesa))
        pg_con.commit()
        cur.close()
        print(f"✔️ Usuario {id_usuario} sentado en mesa {id_mesa} en PostgreSQL.")

    except Exception as e:
        print(f"❌ Error al sentar jugador: {e}")
        pg_con.rollback()

def crear_torneo(pg_con):
    """Crear un nuevo torneo"""
    print("\n--- Crear Nuevo Torneo ---")
    nombre = ask("Nombre del torneo")
    tipo = ask("Tipo (Freeroll/Buy-in/Satélite)")
    modalidad = ask("Modalidad (Texas Holdem/Omaha/Seven Card Stud)")
    buy_in = float(ask("Buy-in (0 para freeroll)"))
    max_jugadores = int(ask("Máximo de jugadores"))
    
    query = """
        INSERT INTO torneo (nombre, tipo, modalidad, buy_in, max_jugadores, hora_inicio)
        VALUES (%s, %s, %s, %s, %s, NOW() + INTERVAL '1 hour')
        RETURNING id_torneo;
    """
    
    try:
        cur = pg_con.cursor()
        cur.execute(query, (nombre, tipo, modalidad, buy_in, max_jugadores))
        id_torneo = cur.fetchone()[0]
        pg_con.commit()
        cur.close()
        print(f"✔️ Torneo {id_torneo} '{nombre}' creado en PostgreSQL.")
        
    except Exception as e:
        print(f"❌ Error al crear torneo: {e}")
        pg_con.rollback()

def crear_mesa(pg_con):
    """Crear una nueva mesa de poker"""
    print("\n--- Crear Nueva Mesa ---")
    modalidad = ask("Modalidad (Texas Holdem/Omaha/Seven Card Stud)")
    tipo = ask("Tipo (Cash Game/Sit & Go/Torneo)")
    max_jugadores = int(ask("Máximo jugadores (6/8/9)"))
    ciegas = ask("Ciegas (ej: 5/10, 10/20, 25/50)")
    
    # Preguntar si pertenece a un torneo
    torneo_input = ask("ID Torneo (dejar vacío si es Cash Game)")
    id_torneo = int(torneo_input) if torneo_input else None
    
    query = """
        INSERT INTO mesa (modalidad, tipo, max_jugadores, ciegas, id_torneo, reglas)
        VALUES (%s, %s, %s, %s, %s, 'Reglas estándar')
        RETURNING id_mesa;
    """
    
    try:
        cur = pg_con.cursor()
        cur.execute(query, (modalidad, tipo, max_jugadores, ciegas, id_torneo))
        id_mesa = cur.fetchone()[0]
        pg_con.commit()
        cur.close()
        print(f"✔️ Mesa {id_mesa} ({modalidad} - {tipo}) creada en PostgreSQL.")
        
    except Exception as e:
        print(f"❌ Error al crear mesa: {e}")
        pg_con.rollback()

def crear_metodo_pago(pg_con):
    """Crear un método de pago para un usuario"""
    print("\n--- Crear Método de Pago ---")
    id_usuario = int(ask("ID Usuario"))
    
    print("Tipos disponibles: paypal, tarjeta, transferencia, criptomoneda")
    tipo = ask("Tipo de método de pago")
    
    # Simulamos datos encriptados
    datos_encriptados = f"enc_{tipo}_{id_usuario}_{datetime.datetime.now().timestamp()}"
    
    query = """
        INSERT INTO metodo_pago (id_usuario, tipo, datos_encriptados, estado)
        VALUES (%s, %s, %s, 'activo')
        RETURNING id_metodo;
    """
    
    try:
        cur = pg_con.cursor()
        cur.execute(query, (id_usuario, tipo, datos_encriptados))
        id_metodo = cur.fetchone()[0]
        pg_con.commit()
        cur.close()
        print(f"✔️ Método de pago {id_metodo} ({tipo}) creado para usuario {id_usuario}.")
        
    except Exception as e:
        print(f"❌ Error al crear método de pago: {e}")
        pg_con.rollback()

def crear_mano(pg_con):
    """Crear una mano de poker con datos aleatorios"""
    import random
    
    print("\n--- Crear Mano de Poker ---")
    id_mesa = int(ask("ID Mesa"))
    
    # Verificar que la mesa existe y obtener su modalidad
    try:
        cur = pg_con.cursor()
        cur.execute("SELECT modalidad, tipo FROM mesa WHERE id_mesa = %s", (id_mesa,))
        mesa_info = cur.fetchone()
        
        if not mesa_info:
            print(f"❌ La mesa {id_mesa} no existe.")
            cur.close()
            return
        
        modalidad, tipo_mesa = mesa_info
        
        # Obtener usuarios sentados en esta mesa
        cur.execute("""
            SELECT id_usuario FROM usuario_mesa WHERE id_mesa = %s
        """, (id_mesa,))
        usuarios_en_mesa = [row[0] for row in cur.fetchall()]
        
        if len(usuarios_en_mesa) < 2:
            print(f"⚠️ La mesa {id_mesa} tiene menos de 2 jugadores. Agrega jugadores primero.")
            cur.close()
            return
        
        # Seleccionar jugador aleatorio que participó en la mano
        id_usuario = random.choice(usuarios_en_mesa)
        
        # Generar datos aleatorios
        bote_total = round(random.uniform(100, 5000), 2)
        rake = round(bote_total * 0.05, 2)  # 5% de rake
        ganador_id = random.choice(usuarios_en_mesa)
        
        # Preguntar si quiere personalizar el bote o usar uno específico
        print(f"Bote generado automáticamente: ${bote_total}")
        personalizar = ask("¿Personalizar bote? (s/n)").lower()
        
        if personalizar == 's':
            bote_total = float(ask("Monto del bote"))
            rake = round(bote_total * 0.05, 2)
            
            print(f"Jugadores en mesa: {usuarios_en_mesa}")
            ganador_id = int(ask("ID del ganador"))
        
        # Generar fecha (puede ser reciente o específica)
        fecha_input = ask("Fecha (dejar vacío para ahora, o formato YYYY-MM-DD)")
        if fecha_input:
            fecha_hora = f"{fecha_input} {random.randint(10, 23)}:{random.randint(0, 59)}:00"
        else:
            fecha_hora = None  # Usará NOW()
        
        query = """
            INSERT INTO mano (id_mesa, id_usuario, rake, bote_total, fecha_hora, ganador_id, modalidad, cartas_repartidas)
            VALUES (%s, %s, %s, %s, COALESCE(%s::timestamp, NOW()), %s, %s, %s)
            RETURNING id_mano, fecha_hora;
        """
        
        cartas = f"[{random.choice(['As', 'K', 'Q', 'J', '10'])}, {random.choice(['As', 'K', 'Q', 'J', '10'])}]"
        
        cur.execute(query, (id_mesa, id_usuario, rake, bote_total, fecha_hora, ganador_id, modalidad, cartas))
        id_mano, fecha_final = cur.fetchone()
        
        # Insertar relación usuario-mano para todos los participantes
        for usuario in usuarios_en_mesa:
            cur.execute("""
                INSERT INTO usuario_mano (id_usuario, id_mano) VALUES (%s, %s)
            """, (usuario, id_mano))
        
        pg_con.commit()
        cur.close()
        
        print(f"✔️ Mano {id_mano} creada:")
        print(f"   Mesa: {id_mesa} ({modalidad})")
        print(f"   Bote: ${bote_total} | Rake: ${rake}")
        print(f"   Ganador: Usuario {ganador_id}")
        print(f"   Fecha: {fecha_final}")
        print(f"   Participantes: {len(usuarios_en_mesa)} jugadores")
        
    except Exception as e:
        print(f"❌ Error al crear mano: {e}")
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
            SELECT u.id_usuario, u.nombre, u.email, u.pais, u.saldo_real, u.saldo_fichas
            FROM usuario u
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
                'balance_neto': 0.0,
                'manos_jugadas': 0
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

def caso1_volumen_modalidad(pg_con, db):
    print("\n[MongoDB] 📊 1. Volumen jugado por modalidad (última semana)")
    
    # 1. ETL bajo demanda
    print("🔄 Cargando datos desde PostgreSQL...")
    sync_manos_to_mongo(pg_con, db)
    
    # 2. Ejecutar consulta en MongoDB
    hace_7_dias = datetime.datetime.now() - datetime.timedelta(days=7)
    pipeline = [
        { "$match": { "fecha_hora": { "$gte": hace_7_dias } } },
        { "$group": {
            "_id": "$modalidad",
            "volumen_total": { "$sum": "$bote_total" }
        }}
    ]
    resultados = list(db.manos.aggregate(pipeline))
    
    if resultados:
        print("\nResultados:")
        for r in resultados:
            print(f"  {r['_id']}: ${r['volumen_total']:.2f}")
    else:
        print("  (Sin datos)")

def caso2_top10_balance(pg_con, db):
    print("\n[MongoDB] 💰 2. Top 10 jugadores con mayor balance neto")
    
    # 1. ETL bajo demanda
    print("🔄 Cargando datos desde PostgreSQL...")
    sync_all_usuarios_to_mongo(pg_con, db)
    
    # 2. Ejecutar consulta en MongoDB
    resultados = list(db.usuarios.find().sort("balance_neto", -1).limit(10))
    
    if resultados:
        print("\nTop 10:")
        for i, user in enumerate(resultados, 1):
            print(f"  {i}. {user['nombre']}: ${user.get('balance_neto', 0):.2f}")
    else:
        print("  (Sin datos)")

def caso3_manos_1000_septiembre(pg_con, db):
    print("\n[MongoDB] 🔥 3. Manos con bote > 1000 USD en septiembre")
    
    # 1. ETL bajo demanda
    print("🔄 Cargando datos desde PostgreSQL...")
    sync_manos_to_mongo(pg_con, db)
    
    # 2. Ejecutar consulta
    resultados = list(db.manos.find({
        "bote_total": { "$gt": 1000 },
        "$expr": { "$eq": [{ "$month": "$fecha_hora" }, 9] }
    }))
    
    if resultados:
        print(f"\nManos con bote > $1000 en septiembre:")
        for m in resultados:
            print(f"  Mano {m['id_mano']}: ${m['bote_total']:.2f} - {m['fecha_hora']}")
    else:
        print("  (Sin datos)")

def caso4_depositos_paypal(pg_con, db):
    print("\n[MongoDB] 💳 4. Depósitos de un usuario por PayPal")
    
    # 1. ETL bajo demanda
    print("🔄 Cargando transacciones desde PostgreSQL...")
    sync_transacciones_to_mongo(pg_con, db)
    
    # 2. Pedir datos
    user_id = int(ask("ID Usuario"))
    
    # 3. Ejecutar consulta
    resultados = list(db.transacciones.find({
        "id_usuario": user_id,
        "tipo": "deposito",
        "medio": "paypal"
    }))
    
    if resultados:
        print(f"\nDepósitos de usuario {user_id} por PayPal:")
        total = 0
        for t in resultados:
            print(f"  {t['fecha']}: ${t['monto']:.2f}")
            total += t['monto']
        print(f"\nTotal: ${total:.2f}")
    else:
        print("  (Sin depósitos por PayPal)")

def caso5_rake_por_mesa(pg_con, db):
    print("\n[MongoDB] 💸 5. Análisis de rake generado por mesa")
    
    # 1. ETL bajo demanda
    print("🔄 Cargando datos desde PostgreSQL...")
    sync_manos_to_mongo(pg_con, db)
    
    # 2. Ejecutar consulta
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
    
    if resultados:
        print("\nTop 10 mesas por rake:")
        for r in resultados:
            print(f"  Mesa {r['_id']}: ${r['rake_total']:.2f} rake, {r['manos_jugadas']} manos")
    else:
        print("  (Sin datos)")

def caso6_usuarios_por_pais(pg_con, db):
    print("\n[MongoDB] 🌍 6. Distribución de usuarios por país")
    
    # 1. ETL bajo demanda
    print("🔄 Cargando datos desde PostgreSQL...")
    sync_all_usuarios_to_mongo(pg_con, db)
    
    # 2. Ejecutar consulta en MongoDB
    pipeline = [
        { "$group": {
            "_id": "$pais",
            "total_usuarios": { "$count": {} }
        }},
        { "$sort": { "total_usuarios": -1 }}
    ]
    resultados = list(db.usuarios.aggregate(pipeline))
    
    if resultados:
        print("\nDistribución por país:")
        for r in resultados:
            print(f"  {r['_id']}: {r['total_usuarios']} usuarios")
    else:
        print("  (Sin datos)")

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
            cur.execute("SELECT saldo_real FROM usuario WHERE id_usuario = %s", (id_usuario,))
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

def caso9_usuarios_dos_mesas(pg_con, driver):
    print("\n[Neo4j] 🎯 9. Usuarios que jugaron en ≥2 mesas distintas")
    
    # 1. ETL bajo demanda
    print("🔄 Cargando relaciones desde PostgreSQL...")
    sync_usuarios_mesas_to_neo4j(pg_con, driver)
    
    # 2. Ejecutar consulta
    query = """
        MATCH (u:Usuario)-[:JUGO_EN]->(m:Mesa)
        WITH u, count(DISTINCT m) as mesas_jugadas
        WHERE mesas_jugadas >= 2
        RETURN u.id_usuario, u.nombre, mesas_jugadas
        ORDER BY mesas_jugadas DESC
    """
    
    with driver.session() as session:
        resultados = session.run(query).data()
        
        if resultados:
            print("\nUsuarios en múltiples mesas:")
            for r in resultados:
                print(f"  Usuario {r['u.id_usuario']} ({r['u.nombre']}): {r['mesas_jugadas']} mesas")
        else:
            print("  (Sin datos)")
def caso10_colusion(pg_con, driver):
    print("\n[Neo4j] 🚨 10. Detección de clusters de colusión (Top 5 pares)")
    
    # 1. ETL bajo demanda
    print("🔄 Cargando relaciones desde PostgreSQL...")
    sync_usuarios_mesas_to_neo4j(pg_con, driver)
    
    # 2. Ejecutar consulta
    query = """
        MATCH (u1:Usuario)-[:JUGO_EN]->(m:Mesa)<-[:JUGO_EN]-(u2:Usuario)
        WHERE id(u1) < id(u2)
        WITH u1, u2, count(m) as mesas_compartidas
        WHERE mesas_compartidas > 2
        RETURN u1.id_usuario, u1.nombre, u2.id_usuario, u2.nombre, mesas_compartidas
        ORDER BY mesas_compartidas DESC
        LIMIT 5
    """
    
    with driver.session() as session:
        resultados = session.run(query).data()
        
        if resultados:
            print("\nPosible colusión (pares que juegan juntos frecuentemente):")
            for r in resultados:
                print(f"  {r['u1.nombre']} <-> {r['u2.nombre']}: {r['mesas_compartidas']} mesas compartidas")
        else:
            print("  (Sin datos)")

# ================================
#   MENÚ PRINCIPAL (ORQUESTADOR)
# ================================
def main():
    # 1. Cargar .env
    load_dotenv()
    
    # 2. Iniciar todas las conexiones
    pg_con = get_postgres()
    mongo_db = get_mongo_client()
    redis_con = get_redis()
    neo4j_driver = get_neo4j_driver()
    
    # Validar conexiones (mongo_db no puede usarse con bool directamente)
    if pg_con is None or mongo_db is None or redis_con is None or neo4j_driver is None:
        print("Faltan conexiones de base de datos. Saliendo.")
        return

    while True:
        print("\n===================================")
        print("       POKERSTARS DATA MANAGER")
        print("===================================")
        print("--- Admin (PostgreSQL) ---")
        print("1. Crear Tablas en PostgreSQL")
        print("--- Escritura (PostgreSQL) ---")
        print("2. Crear Nuevo Usuario")
        print("3. Crear Método de Pago")
        print("4. Crear Transacción")
        print("5. Crear Torneo")
        print("6. Crear Mesa")
        print("7. Registrar Jugador en Mesa")
        print("8. Crear Mano (Aleatoria)")
        print("9. Simular Jugador juega una mano (Redis)")
        print("--- Lectura (Casos de Uso NoSQL) ---")
        print("m. Ver Casos de Uso (MongoDB)")
        print("r. Ver Casos de Uso (Redis)")
        print("n. Ver Casos de Uso (Neo4j)")
        print("s. Salir")
        
        op = ask("Opción")

        try:
            if op == '1':
                crear_tablas_postgres(pg_con)
            elif op == '2':
                crear_usuario(pg_con)
            elif op == '3':
                crear_metodo_pago(pg_con)
            elif op == '4':
                crear_transaccion(pg_con)
            elif op == '5':
                crear_torneo(pg_con)
            elif op == '6':
                crear_mesa(pg_con)
            elif op == '7':
                registrar_jugador_en_mesa(pg_con)
            elif op == '8':
                crear_mano(pg_con)
            elif op == '9':
                simular_juego(redis_con)
            
            elif op == 'm':
                if mongo_db:
                    print("\n--- Casos de Uso MongoDB ---")
                    caso1_volumen_modalidad(pg_con, mongo_db)
                    caso2_top10_balance(pg_con, mongo_db)
                    caso3_manos_1000_septiembre(pg_con, mongo_db)
                    caso4_depositos_paypal(pg_con, mongo_db)
                    caso5_rake_por_mesa(pg_con, mongo_db)
                    caso6_usuarios_por_pais(pg_con, mongo_db)
                else:
                    print("❌ MongoDB no disponible")
            
            elif op == 'r':
                print("\n--- Casos de Uso Redis ---")
                caso7_ranking(redis_con)
                caso8_balance_cache(redis_con, pg_con)

            elif op == 'n':
                if neo4j_driver:
                    print("\n--- Casos de Uso Neo4j ---")
                    caso9_usuarios_dos_mesas(pg_con, neo4j_driver)
                    caso10_colusion(pg_con, neo4j_driver)
                else:
                    print("❌ Neo4j no disponible")

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