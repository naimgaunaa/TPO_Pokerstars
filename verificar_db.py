"""Script rápido para verificar el estado de PostgreSQL"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def verificar_postgres():
    try:
        db_url = os.getenv("DATABASE_PUBLIC_URL")
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        print("\n" + "="*50)
        print("📊 ESTADO DE POSTGRESQL EN RAILWAY")
        print("="*50)
        
        # 1. Verificar conexión
        cur.execute("SELECT current_database(), current_user;")
        db_name, user = cur.fetchone()
        print(f"\n✅ Base de datos: {db_name}")
        print(f"✅ Usuario: {user}")
        
        # 2. Listar tablas
        cur.execute("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public' 
            ORDER BY tablename;
        """)
        tablas = cur.fetchall()
        
        if tablas:
            print(f"\n📋 TABLAS EXISTENTES ({len(tablas)}):")
            print("-" * 50)
            for tabla in tablas:
                cur.execute(f"SELECT COUNT(*) FROM {tabla[0]};")
                count = cur.fetchone()[0]
                print(f"   {tabla[0]:25} | {count:>5} registros")
        else:
            print("\n⚠️  NO HAY TABLAS en el esquema public")
            print("   Necesitas crear las tablas primero (Opción 1)")
        
        # 3. Si hay tablas, mostrar algunos datos de usuario
        if tablas and ('usuario',) in tablas:
            print(f"\n👥 USUARIOS REGISTRADOS:")
            print("-" * 50)
            cur.execute("""
                SELECT id_usuario, nombre, email, pais, saldo_real 
                FROM usuario 
                ORDER BY id_usuario 
                LIMIT 10;
            """)
            usuarios = cur.fetchall()
            if usuarios:
                for u in usuarios:
                    print(f"   ID {u[0]}: {u[1]} ({u[2]}) - {u[3]} | Saldo: ${u[4]}")
            else:
                print("   (No hay usuarios aún)")
        
        cur.close()
        conn.close()
        print("\n" + "="*50 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verificar_postgres()
