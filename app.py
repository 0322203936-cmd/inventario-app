from flask import Flask, render_template, request, redirect
import psycopg2
import os
from datetime import datetime

app = Flask(__name__)

# Conexión a PostgreSQL usando variable de entorno DATABASE_URL
def get_db():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("No se encontró la variable de entorno DATABASE_URL")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return psycopg2.connect(url)

# Crear tabla si no existe
def init_db():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS inventario (
                id SERIAL PRIMARY KEY,
                chofer TEXT,
                producto TEXT,
                cantidad INTEGER,
                fecha TEXT
            )
        """)
        conn.commit()
    except Exception as e:
        print("Error al inicializar la base de datos:", e)
    finally:
        if cur: cur.close()
        if conn: conn.close()

# Inicializamos la base de datos al importar la app
init_db()

@app.route("/", methods=["GET", "POST"])
def index():
    try:
        conn = get_db()
        cur = conn.cursor()

        if request.method == "POST":
            chofer = request.form.get("chofer")
            producto = request.form.get("producto")
            cantidad = request.form.get("cantidad")
            fecha = datetime.now().strftime("%Y-%m-%d %H:%M")

            cur.execute(
                "INSERT INTO inventario (chofer, producto, cantidad, fecha) VALUES (%s, %s, %s, %s)",
                (chofer, producto, cantidad, fecha)
            )
            conn.commit()
            return redirect("/")

        cur.execute("SELECT * FROM inventario ORDER BY id DESC")
        registros = cur.fetchall()
        return render_template("index.html", registros=registros)

    except Exception as e:
        return f"<h2>Error en la aplicación:</h2><pre>{e}</pre>"

    finally:
        if cur: cur.close()
        if conn: conn.close()

# Para desarrollo local
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
