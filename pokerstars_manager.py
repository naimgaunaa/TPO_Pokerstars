# ============================================================
#   POKERSTARS DATA MANAGER (SIMULADO EN MEMORIA)
#   CRUD COMPLETO + CASOS DE USO REALES + MENU INTERACTIVO
# ============================================================

import uuid
import datetime
import time

# ============================================================
#   BASE DE DATOS SIMULADA EN MEMORIA
# ============================================================

DB = {
    "Usuario": [],
    "Mesa": [],
    "Mano": [],
    "Jugada": [],
    "Metodo_Pago": [],
    "Transaccion": [],
    "Promocion": [],
    "Usuario_Mesa": [],
    "Usuario_Torneo": [],
    "Usuario_Mano": [],
    "Usuario_Promocion": [],
    "Torneo": []
}

# Cache simulado (para balance con TTL)
CACHE = {}

# ============================================================
#   GENERADORES DE ID
# ============================================================

def gen_id():
    return str(uuid.uuid4())

# ============================================================
#   FUNCIONES CRUD GENERALES
# ============================================================

def create(entity, data):
    data["id"] = gen_id()
    DB[entity].append(data)
    print(f"\n✔️ {entity} creado con éxito. ID = {data['id']}\n")
    return data

def read(entity, filters=None):
    if not filters:
        return DB[entity]

    results = []
    for item in DB[entity]:
        ok = True
        for key, value in filters.items():
            if item.get(key) != value:
                ok = False
                break
        if ok:
            results.append(item)
    return results

def update(entity, filters, new_data):
    updated = 0
    for item in DB[entity]:
        ok = True
        for key, value in filters.items():
            if item.get(key) != value:
                ok = False
                break
        if ok:
            item.update(new_data)
            updated += 1

    print(f"\n✔️ {updated} registro(s) actualizados.\n")
    return updated

def delete(entity, filters):
    before = len(DB[entity])
    DB[entity] = [
        item for item in DB[entity]
        if not all(item.get(k) == v for k, v in filters.items())
    ]
    after = len(DB[entity])
    print(f"\n✔️ {before - after} registro(s) eliminados.\n")
    return before - after

# ============================================================
#   FUNCIONES DE INPUT
# ============================================================

def ask(text):
    return input(text + ": ").strip()

# ============================================================
#   CRUD ESPECÍFICOS POR ENTIDAD
# ============================================================

def crear_usuario():
    data = {
        "nombre": ask("Nombre del usuario"),
        "pais": ask("País de residencia"),
        "verificacion_KYC": ask("¿Tiene verificación KYC? (sí/no)"),
        "email": ask("Correo electrónico"),
        "fecha_registro": str(datetime.datetime.now()),
        "saldo_real": 0,
        "saldo_virtual": 0,
        "balance_neto": 0,
        "mesas_jugadas": []
    }
    return create("Usuario", data)

def crear_mesa():
    data = {
        "modalidad": ask("Modalidad (Ej: NLHE, Omaha, Stud)"),
        "ciegas": ask("Ciegas (Ej: 1/2, 2/5)"),
        "max_jugadores": int(ask("Máximo número de jugadores")),
        "hora_inicio": ask("Hora de inicio (formato libre)"),
        "reglas": ask("Reglas específicas de la mesa")
    }
    return create("Mesa", data)

def crear_metodo_pago():
    data = {
        "tipo": ask("Tipo de método de pago (Tarjeta, PayPal, Crypto, etc.)"),
        "detalles_encriptados": ask("Detalles cifrados")
    }
    return create("Metodo_Pago", data)

def crear_transaccion():
    usuario_id = ask("ID Usuario")
    metodo_id = ask("ID Método de pago")
    monto = float(ask("Monto"))
    tipo = ask("Tipo (deposito/retiro)")

    if monto > 2000:
        print("⚠️ ALERTA AML: Transacción marcada para auditoría")

    data = {
        "id_usuario": usuario_id,
        "id_metodo": metodo_id,
        "monto": monto,
        "tipo": tipo,
        "fecha": str(datetime.datetime.now()),
        "cumplimiento_AML": "OK" if monto <= 2000 else "REVIEW"
    }
    return create("Transaccion", data)

def crear_promocion():
    data = {
        "nombre_promocion": ask("Nombre de la promoción"),
        "estado": ask("Estado (activa/inactiva)"),
        "descuento": ask("Monto del bono/descuento"),
        "fecha_inicio": ask("Fecha inicio"),
        "fecha_fin": ask("Fecha fin")
    }
    return create("Promocion", data)

def crear_torneo():
    data = {
        "modalidad": ask("Modalidad (Ej: NLHE Deepstack, Omaha Turbo)"),
        "buy_in": float(ask("Buy-in del torneo")),
        "max_jugadores": int(ask("Máximo de jugadores")),
        "hora_inicio": ask("Hora de inicio"),
        "reglas": ask("Reglas del torneo")
    }
    return create("Torneo", data)

def crear_mano():
    data = {
        "id_mesa": ask("ID de la Mesa donde se jugó la mano"),
        "rake": float(ask("Rake (%) de la mano")),
        "bote_total": 0,
        "fecha_hora": str(datetime.datetime.now())
    }
    return create("Mano", data)

def crear_jugada():
    data = {
        "id_mano": ask("ID de la Mano"),
        "id_usuario": ask("ID del Usuario"),
        "accion": ask("Acción (fold, call, raise, all-in)"),
        "monto_apostado": float(ask("Monto apostado")),
        "ronda": ask("Ronda (preflop, flop, turn, river)")
    }
    return create("Jugada", data)

# ============================================================
#   CASOS DE USO REALES (10)
# ============================================================

def caso1_volumen_por_modalidad():
    print("\n📊 Volumen jugado por modalidad (última semana)")
    hace_7_dias = datetime.datetime.now() - datetime.timedelta(days=7)
    manos = [m for m in DB["Mano"] if datetime.datetime.fromisoformat(m["fecha_hora"]) >= hace_7_dias]

    conteo = {}
    for mano in manos:
        mesa = read("Mesa", {"id": mano["id_mesa"]})
        if mesa:
            modalidad = mesa[0]["modalidad"]
            conteo[modalidad] = conteo.get(modalidad, 0) + mano["bote_total"]

    print(conteo)

def caso2_top10_balance():
    print("\n💰 Top 10 jugadores con mayor balance neto")
    usuarios = sorted(DB["Usuario"], key=lambda x: x.get("balance_neto", 0), reverse=True)
    print(usuarios[:10])

def caso3_manos_mayor_1000_en_septiembre():
    print("\n🔥 Manos con bote > 1000 USD en septiembre")
    resultado = []
    for m in DB["Mano"]:
        fecha = datetime.datetime.fromisoformat(m["fecha_hora"])
        if fecha.month == 9 and m["bote_total"] > 1000:
            resultado.append(m)
    print(resultado)

def caso4_depositos_por_paypal():
    print("\n💳 Depósitos de un usuario por PayPal")
    user = ask("ID Usuario")
    resultado = [
        t for t in DB["Transaccion"]
        if t["id_usuario"] == user and t["tipo"] == "deposito"
        and read("Metodo_Pago", {"id": t["id_metodo"]})[0]["tipo"].lower() == "paypal"
    ]
    print(resultado)

def caso5_manos_por_fecha_y_mesa():
    print("\n🃏 Manos por fecha y mesa")
    fecha = ask("Fecha (YYYY-MM-DD)")
    mesa = ask("ID Mesa")
    resultado = []
    for m in DB["Mano"]:
        if m["id_mesa"] == mesa and m["fecha_hora"].startswith(fecha):
            resultado.append(m)
    print(resultado)

def caso6_transacciones_usuario_fecha():
    print("\n💵 Transacciones por usuario y fecha")
    usuario = ask("ID Usuario")
    fecha = ask("Fecha (YYYY-MM-DD)")
    resultado = [t for t in DB["Transaccion"] if t["id_usuario"] == usuario and t["fecha"].startswith(fecha)]
    print(resultado)

def caso7_ranking_jugadores_activos():
    print("\n🏆 Ranking de jugadores activos (simulado Redis Sorted Set)")
    actividad = {}
    for jugada in DB["Jugada"]:
        actividad[jugada["id_usuario"]] = actividad.get(jugada["id_usuario"], 0) + 1

    ranking = sorted(actividad.items(), key=lambda x: x[1], reverse=True)
    print(ranking)

def caso8_balance_cache():
    print("\n🧠 Balance en cache (TTL 5 min)")
    user = ask("ID Usuario")

    if user in CACHE and time.time() - CACHE[user]["timestamp"] < 300:
        print("Desde cache:", CACHE[user]["data"])
    else:
        usuario = read("Usuario", {"id": user})
        if usuario:
            CACHE[user] = {"data": usuario[0]["saldo_real"], "timestamp": time.time()}
            print("Desde base:", usuario[0]["saldo_real"])

def caso9_jugadores_en_dos_mesas():
    print("\n🎯 Jugadores que jugaron en ≥ 2 mesas")
    usuarios = DB["Usuario"]
    resultado = [u for u in usuarios if len(set(u["mesas_jugadas"])) >= 2]
    print(resultado)

def caso10_detectar_colusion():
    print("\n🚨 Detección de clusters de colusión (simple)")
    patrones = {}
    for jug in DB["Jugada"]:
        clave = (jug["id_mano"], jug["accion"])
        patrones[clave] = patrones.get(clave, 0) + 1

    sospechosos = [k for k, v in patrones.items() if v > 3]
    print("Patrones sospechosos:", sospechosos)

# ============================================================
#   MENÚS (con opción VOLVER y MENÚ PRINCIPAL)
# ============================================================

def menu_entidad():
    print("""
=== ENTIDADES ===
0. Volver
M. Menú principal
1. Usuario
2. Mesa
3. Mano
4. Jugada
5. Método de Pago
6. Transacción
7. Promoción
8. Torneo
9. Usuario_Mesa
10. Usuario_Mano
11. Usuario_Promoción
12. Usuario_Torneo
""")
    op = ask("Selecciona una entidad")
    if op.upper() == "M" or op == "0":
        return None
    return op

def menu_operacion():
    print("""
=== OPERACIONES CRUD ===
0. Volver
M. Menú principal
1. Crear
2. Leer
3. Actualizar
4. Eliminar
""")
    op = ask("Selecciona una operación")
    if op.upper() == "M" or op == "0":
        return None
    return op

def menu_casos():
    print("""
=== CASOS DE USO ===
0. Volver
M. Menú principal
1. Volumen jugado por modalidad (última semana)
2. Top 10 jugadores con mayor balance neto
3. Manos con bote > 1000 en septiembre
4. Depósitos de un usuario por PayPal
5. Manos por fecha y mesa
6. Transacciones por usuario y fecha
7. Ranking jugadores activos
8. Balance en cache (TTL 5 min)
9. Usuarios que jugaron en ≥2 mesas
10. Detección de clusters de colusión
""")
    op = ask("Selecciona un caso")
    if op.upper() == "M" or op == "0":
        return None
    return op

# ============================================================
#   MENÚ PRINCIPAL
# ============================================================

def main():
    while True:
        print("""
===================================
       POKERSTARS DATA MANAGER
===================================
1. CRUD de entidades
2. Casos de uso del negocio
3. Ver base completa (debug)
4. Salir
""")
        op = ask("Opción")

        if op == "1":
            ent = menu_entidad()
            if ent is None:
                continue

            op2 = menu_operacion()
            if op2 is None:
                continue

            entity_map = {
                "1": "Usuario",
                "2": "Mesa",
                "3": "Mano",
                "4": "Jugada",
                "5": "Metodo_Pago",
                "6": "Transaccion",
                "7": "Promocion",
                "8": "Torneo",
                "9": "Usuario_Mesa",
                "10": "Usuario_Mano",
                "11": "Usuario_Promocion",
                "12": "Usuario_Torneo"
            }

            entity = entity_map.get(ent)

            if op2 == "1":  # Crear
                if entity == "Usuario":
                    crear_usuario()
                elif entity == "Mesa":
                    crear_mesa()
                elif entity == "Metodo_Pago":
                    crear_metodo_pago()
                elif entity == "Transaccion":
                    crear_transaccion()
                elif entity == "Promocion":
                    crear_promocion()
                elif entity == "Torneo":
                    crear_torneo()
                elif entity == "Mano":
                    crear_mano()
                elif entity == "Jugada":
                    crear_jugada()
                else:
                    create(entity, {})

            elif op2 == "2":  # Leer
                print(read(entity))

            elif op2 == "3":  # Actualizar
                fid = ask("ID registro a actualizar")
                field = ask("Campo a modificar")
                value = ask("Nuevo valor")
                update(entity, {"id": fid}, {field: value})

            elif op2 == "4":  # Eliminar
                fid = ask("ID registro a eliminar")
                delete(entity, {"id": fid})

        elif op == "2":  # Casos de uso
            caso = menu_casos()
            if caso is None:
                continue

            casos_map = {
                "1": caso1_volumen_por_modalidad,
                "2": caso2_top10_balance,
                "3": caso3_manos_mayor_1000_en_septiembre,
                "4": caso4_depositos_por_paypal,
                "5": caso5_manos_por_fecha_y_mesa,
                "6": caso6_transacciones_usuario_fecha,
                "7": caso7_ranking_jugadores_activos,
                "8": caso8_balance_cache,
                "9": caso9_jugadores_en_dos_mesas,
                "10": caso10_detectar_colusion
            }

            if caso in casos_map:
                casos_map[caso]()

        elif op == "3":
            print(DB)

        elif op == "4":
            print("Saliendo...")
            break

# ============================================================
#   RUN
# ============================================================

if __name__ == "__main__":
    main()