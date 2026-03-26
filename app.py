from flask import Flask, render_template, request, redirect
import sqlite3
from datetime import datetime

app = Flask(__name__)

def get_db():
    conn = sqlite3.connect("inventario.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS inventario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chofer TEXT,
            producto TEXT,
            cantidad INTEGER,
            fecha TEXT
        )
    """)
    conn.commit()
    conn.close()

@app.route("/", methods=["GET", "POST"])
def index():
    conn = get_db()

    if request.method == "POST":
        chofer = request.form["chofer"]
        producto = request.form["producto"]
        cantidad = request.form["cantidad"]
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M")

        conn.execute(
            "INSERT INTO inventario (chofer, producto, cantidad, fecha) VALUES (?, ?, ?, ?)",
            (chofer, producto, cantidad, fecha)
        )
        conn.commit()

        return redirect("/")

    registros = conn.execute("SELECT * FROM inventario ORDER BY id DESC").fetchall()
    conn.close()

    return render_template("index.html", registros=registros)

if __name__ == "__main__":
    init_db()
import os

if __name__ == "__main__":
    init_db()
   import os

if __name__ == "__main__":
    init_db()
import os

if __name__ == "__main__":
    init_db()
import os

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
