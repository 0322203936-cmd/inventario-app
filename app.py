from flask import Flask, render_template, request, redirect
import psycopg2
import os
from datetime import datetime

app = Flask(__name__)

def get_db():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("No se encontró la variable de entorno DATABASE_URL")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return psycopg2.connect(url)

def init_db():
    conn = None
    cur = None
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS merma_inventario (
                id SERIAL PRIMARY KEY,
                tienda TEXT,
                fecha TEXT,
                usuario TEXT,
                producto TEXT,
                inventario INTEGER,
                merma INTEGER
            )
        """)
        conn.commit()
    except Exception as e:
        print("Error al inicializar la base de datos:", e)
    finally:
        if cur: cur.close()
        if conn: conn.close()

init_db()

TIENDAS = [
    "Sucursal Centro",
    "Sucursal Norte",
    "Sucursal Sur",
    "Sucursal Este",
    "Sucursal Oeste"
]

@app.route("/", methods=["GET", "POST"])
def index():
    conn = None
    cur = None
    try:
        conn = get_db()
        cur = conn.cursor()

        if request.method == "POST":
            tienda = request.form.get("tienda")
            fecha = request.form.get("fecha")
            usuario = request.form.get("usuario")
            productos = request.form.getlist("producto[]")
            inventarios = request.form.getlist("inventario[]")
            mermas = request.form.getlist("merma[]")

            for i in range(len(productos)):
                if productos[i].strip():
                    cur.execute(
                        "INSERT INTO merma_inventario (tienda, fecha, usuario, producto, inventario, merma) VALUES (%s, %s, %s, %s, %s, %s)",
                        (tienda, fecha, usuario, productos[i], inventarios[i] or 0, mermas[i] or 0)
                    )
            conn.commit()
            return redirect("/registros")

        today = datetime.now().strftime("%d/%m/%Y")
        return render_template("index.html", tiendas=TIENDAS, today=today)

    except Exception as e:
        return f"<h2>Error en la aplicación:</h2><pre>{e}</pre>"
    finally:
        if cur: cur.close()
        if conn: conn.close()

@app.route("/registros")
def registros():
    conn = None
    cur = None
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM merma_inventario ORDER BY id DESC")
        registros = cur.fetchall()
        return render_template("registros.html", registros=registros)
    except Exception as e:
        return f"<h2>Error:</h2><pre>{e}</pre>"
    finally:
        if cur: cur.close()
        if conn: conn.close()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
