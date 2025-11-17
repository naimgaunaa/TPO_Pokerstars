"""reset_postgres.py

Script destructivo para limpiar TODAS las tablas del esquema public en la base de datos PostgreSQL (Railway) indicada por la variable
DATABASE_PUBLIC_URL en .env. Úsalo sólo si estás 100% seguro.

Acciones:
1. Carga .env
2. Pide confirmación interactiva (debe escribir CONFIRM)
3. Intenta DROP SCHEMA public CASCADE y lo recrea.
   - Si el hosting no permite DROP SCHEMA, hace fallback: obtiene lista de tablas y las elimina con DROP TABLE ... CASCADE.
4. Muestra reporte final.

Advertencias:
- Irreversible: perderás datos.
- No elimina extensiones fuera de public.
- No toca otros esquemas si existieran.

Uso rápido:
python reset_postgres.py

"""
import os
import sys
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv


def connect():
    db_url = os.getenv("DATABASE_PUBLIC_URL")
    if not db_url:
        raise RuntimeError("DATABASE_PUBLIC_URL no definido en .env")
    return psycopg2.connect(db_url)


def drop_schema_public(conn):
    print("➡️  Intentando DROP SCHEMA public CASCADE ...")
    cur = conn.cursor()
    try:
        cur.execute("DROP SCHEMA public CASCADE;")
        cur.execute("CREATE SCHEMA public;")
        # Reasignar privilegios básicos al usuario actual
        cur.execute("GRANT ALL ON SCHEMA public TO PUBLIC;")
        conn.commit()
        print("✅ Schema public reiniciado.")
        return True
    except Exception as e:
        conn.rollback()
        print(f"⚠️  No se pudo dropear el schema public directamente: {e}")
        cur.close()
        return False


def drop_all_tables_fallback(conn):
    print("➡️  Fallback: Dropping all tables en public...")
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public';
        """)
        tables = [r[0] for r in cur.fetchall()]
        if not tables:
            print("(No hay tablas en public)")
            cur.close()
            return
        for t in tables:
            print(f"   - DROP TABLE {t} CASCADE")
            cur.execute(sql.SQL("DROP TABLE IF EXISTS {} CASCADE;").format(sql.Identifier(t)))
        conn.commit()
        cur.close()
        print("✅ Todas las tablas fueron eliminadas.")
    except Exception as e:
        conn.rollback()
        cur.close()
        print(f"❌ Error al eliminar tablas: {e}")
        sys.exit(1)


def main():
    load_dotenv()

    print("⚠️  ATENCIÓN: Esto borrará TODOS los datos del esquema public.")
    print("Escribe EXACTAMENTE 'CONFIRM' para continuar, cualquier otra cosa cancela.")
    user_input = input("Confirmación: ").strip()
    if user_input != "CONFIRM":
        print("❌ Operación cancelada.")
        return

    try:
        conn = connect()
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return

    # Intento preferente: drop schema
    success_schema = drop_schema_public(conn)
    if not success_schema:
        # Fallback a drop table individual
        drop_all_tables_fallback(conn)

    # Confirmar que está limpio
    cur = conn.cursor()
    cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public';")
    remaining = cur.fetchall()
    cur.close()
    if remaining:
        print("⚠️  Aún quedan tablas:")
        for r in remaining:
            print("   *", r[0])
    else:
        print("🧹 Esquema public limpio (sin tablas).")

    conn.close()
    print("✔️  Finalizado.")


if __name__ == "__main__":
    main()
