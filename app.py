from flask import Flask, render_template, request, redirect
import psycopg2
import os
from datetime import datetime

app = Flask(__name__)

# Conexión a PostgreSQL usando la variable de entorno
def get_db():
    url = os.environ.get("DATABASE_URL")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    conn = psycopg2.connect(url)
    return conn

# Crear tabla si no existe
def init_db():
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
    cur.close()
    conn.close()

@app.route("/", methods=["GET", "POST"])
def index():
    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        chofer = request.form["chofer"]
        producto = request.form["producto"]
        cantidad = request.form["cantidad"]
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M")

        cur.execute(
            "INSERT INTO inventario (chofer, producto, cantidad, fecha) VALUES (%s, %s, %s, %s)",
            (chofer, producto, cantidad, fecha)
        )
        conn.commit()

        return redirect("/")

    cur.execute("SELECT * FROM inventario ORDER BY id DESC")
    registros = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("index.html", registros=registros)

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
