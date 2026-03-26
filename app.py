from flask import Flask, render_template, request, redirect, jsonify
import psycopg2
import os
from datetime import datetime

app = Flask(__name__)

DELETE_PASSWORD = "CFBCWALMEX"

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
                merma INTEGER,
                razon TEXT,
                fecha_modificacion TEXT
            )
        """)
        cur.execute("ALTER TABLE merma_inventario ADD COLUMN IF NOT EXISTS razon TEXT;")
        cur.execute("ALTER TABLE merma_inventario ADD COLUMN IF NOT EXISTS fecha_modificacion TEXT;")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS cuarto_frio (
                id SERIAL PRIMARY KEY,
                tienda TEXT,
                fecha TEXT,
                usuario TEXT,
                producto TEXT,
                existencia INTEGER,
                fecha_modificacion TEXT
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
    "5041 Nuevo Mexicali","4155 Tijuana 2000","3015 Ensenada",
    "2947 Ensenada Centro","1613 Playas De Tijuana","190 Lomas de Santa Fe",
    "4187 Rosarito","2023 Macro Plaza Insurgentes","3664 Diaz Ordaz",
    "4011 Tijuana Hipodromo","1616 Pacifico","1617 Novena",
    "1140 Plaza San Pedro","4026 Galerías Del Valle","2304 Mexicali",
    "5295 Tecate Garita"
]

@app.route("/", methods=["GET", "POST"])
def index():
    conn = None
    cur = None
    try:
        conn = get_db()
        cur = conn.cursor()

        if request.method == "POST":
            tienda      = request.form.get("tienda")
            fecha       = request.form.get("fecha")
            usuario     = request.form.get("usuario")
            productos   = request.form.getlist("producto[]")
            inventarios = request.form.getlist("inventario[]")
            mermas      = request.form.getlist("merma[]")
            razones     = request.form.getlist("razon[]")

            # Merma/inventario: solo guarda si inventario > 0 O merma > 0
            for i in range(len(productos)):
                if not productos[i].strip():
                    continue
                try:
                    inv = int(inventarios[i]) if inventarios[i] else 0
                except ValueError:
                    inv = 0
                try:
                    mer = int(mermas[i]) if mermas[i] else 0
                except ValueError:
                    mer = 0

                if inv > 0 or mer > 0:
                    cur.execute(
                        """INSERT INTO merma_inventario
                           (tienda, fecha, usuario, producto, inventario, merma, razon)
                           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                        (tienda, fecha, usuario, productos[i], inv, mer,
                         razones[i] if i < len(razones) else "")
                    )

            # Cuarto frío: solo guarda si existencia > 0
            cf_productos   = request.form.getlist("cf_producto[]")
            cf_existencias = request.form.getlist("cf_existencia[]")

            for i in range(len(cf_productos)):
                try:
                    existencia = int(cf_existencias[i]) if cf_existencias[i] else 0
                except ValueError:
                    existencia = 0
                if existencia > 0:
                    cur.execute(
                        """INSERT INTO cuarto_frio
                           (tienda, fecha, usuario, producto, existencia)
                           VALUES (%s, %s, %s, %s, %s)""",
                        (tienda, fecha, usuario, cf_productos[i], existencia)
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
        merma_rows = cur.fetchall()
        cur.execute("SELECT * FROM cuarto_frio ORDER BY id DESC")
        cf_rows = cur.fetchall()
        return render_template("registros.html", registros=merma_rows, cf_registros=cf_rows)
    except Exception as e:
        return f"<h2>Error:</h2><pre>{e}</pre>"
    finally:
        if cur: cur.close()
        if conn: conn.close()


@app.route("/editar/<int:id>", methods=["GET", "POST"])
def editar(id):
    conn = None
    cur = None
    try:
        conn = get_db()
        cur = conn.cursor()

        if request.method == "POST":
            tienda     = request.form.get("tienda")
            fecha      = request.form.get("fecha")
            usuario    = request.form.get("usuario")
            producto   = request.form.get("producto")
            inventario = request.form.get("inventario") or 0
            merma      = request.form.get("merma") or 0
            razon      = request.form.get("razon") or ""
            fecha_mod  = datetime.now().strftime("%d/%m/%Y %H:%M")

            cur.execute("""
                UPDATE merma_inventario
                SET tienda=%s, fecha=%s, usuario=%s, producto=%s,
                    inventario=%s, merma=%s, razon=%s, fecha_modificacion=%s
                WHERE id=%s
            """, (tienda, fecha, usuario, producto, inventario, merma, razon, fecha_mod, id))
            conn.commit()
            return redirect("/registros")

        cur.execute("SELECT * FROM merma_inventario WHERE id=%s", (id,))
        reg = cur.fetchone()
        if not reg:
            return redirect("/registros")
        return render_template("editar.html", reg=reg, tiendas=TIENDAS)

    except Exception as e:
        return f"<h2>Error:</h2><pre>{e}</pre>"
    finally:
        if cur: cur.close()
        if conn: conn.close()


@app.route("/borrar/<int:id>", methods=["POST"])
def borrar(id):
    password = request.form.get("password")
    if password != DELETE_PASSWORD:
        return jsonify({"ok": False, "msg": "Contraseña incorrecta"}), 403
    conn = None
    cur = None
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("DELETE FROM merma_inventario WHERE id=%s", (id,))
        conn.commit()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500
    finally:
        if cur: cur.close()
        if conn: conn.close()


@app.route("/borrar_cf/<int:id>", methods=["POST"])
def borrar_cf(id):
    password = request.form.get("password")
    if password != DELETE_PASSWORD:
        return jsonify({"ok": False, "msg": "Contraseña incorrecta"}), 403
    conn = None
    cur = None
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("DELETE FROM cuarto_frio WHERE id=%s", (id,))
        conn.commit()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500
    finally:
        if cur: cur.close()
        if conn: conn.close()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
