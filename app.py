from flask import Flask, render_template, request, redirect, jsonify
import psycopg2
import os
import requests as req_lib
import msal
from datetime import datetime

app = Flask(__name__)

DELETE_PASSWORD = "CFBCWALMEX"

# ── SharePoint / Excel config ─────────────────────────────────────────────────
SP_TENANT_ID     = os.environ.get("SP_TENANT_ID",     "073b7d65-a90c-4b41-8300-6555841d361f")
SP_CLIENT_ID     = os.environ.get("SP_CLIENT_ID",     "98625318-3270-42ab-ac73-6c43a82731b3")
SP_CLIENT_SECRET = os.environ.get("SP_CLIENT_SECRET", "f4R8Q~uEJ4agJag~cIlmBp4LP7BzQhz8jiWs-bMW")
SP_SITE_URL      = os.environ.get("SP_SITE_URL",      "https://pacificafarms.sharepoint.com/sites/requerimientovsproyeccion")
SP_FILE_PATH     = os.environ.get("SP_FILE_PATH",     "/requerimiento vs proyeccion/WALMEX/Analisis Walmart.xlsx")
SP_SHEET_NAME    = os.environ.get("SP_SHEET_NAME",    "Detalle")

EXCEL_HEADERS = [
    "Fecha de registro", "Tipo", "Tienda", "Fecha", "Usuario",
    "Producto", "Inventario", "Merma", "Razon de merma", "Existencia"
]


def _get_sp_token():
    msal_app = msal.ConfidentialClientApplication(
        SP_CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{SP_TENANT_ID}",
        client_credential=SP_CLIENT_SECRET,
    )
    result = msal_app.acquire_token_for_client(
        scopes=["https://graph.microsoft.com/.default"]
    )
    return result.get("access_token")


def _get_site_id(headers):
    parts     = SP_SITE_URL.rstrip("/").split("/")
    hostname  = parts[2]
    site_path = "/".join(parts[3:])
    r = req_lib.get(
        f"https://graph.microsoft.com/v1.0/sites/{hostname}:/{site_path}",
        headers=headers, timeout=30
    )
    r.raise_for_status()
    return r.json()["id"]


def _get_base_url(site_id):
    return (
        f"https://graph.microsoft.com/v1.0/sites/{site_id}"
        f"/drive/root:{SP_FILE_PATH}:"
    )


def _ensure_headers_in_sheet(headers, base_url):
    range_url = f"{base_url}/workbook/worksheets/{SP_SHEET_NAME}/range(address='A1')"
    r = req_lib.get(range_url, headers=headers, timeout=30)
    if r.ok:
        values = r.json().get("values", [[]])
        val = values[0][0] if values and values[0] else ""
        if not val:
            end_col   = chr(64 + len(EXCEL_HEADERS))
            patch_url = (
                f"{base_url}/workbook/worksheets/{SP_SHEET_NAME}"
                f"/range(address='A1:{end_col}1')"
            )
            req_lib.patch(
                patch_url,
                headers={**headers, "Content-Type": "application/json"},
                json={"values": [EXCEL_HEADERS]},
                timeout=30
            )


def _find_next_empty_row(headers, base_url):
    used_url = f"{base_url}/workbook/worksheets/{SP_SHEET_NAME}/usedRange"
    r = req_lib.get(used_url, headers=headers, timeout=30)
    if r.ok:
        row_count = r.json().get("rowCount", 0)
        return row_count + 1
    return 2


def escribir_en_excel(filas):
    """Agrega filas al final de la hoja Detalle. Falla silenciosamente."""
    try:
        token = _get_sp_token()
        if not token:
            print("[SharePoint] No se pudo obtener el token.")
            return

        auth_headers = {"Authorization": f"Bearer {token}"}
        site_id      = _get_site_id(auth_headers)
        base_url     = _get_base_url(site_id)

        _ensure_headers_in_sheet(auth_headers, base_url)
        next_row = _find_next_empty_row(auth_headers, base_url)

        n_cols   = len(EXCEL_HEADERS)
        end_col  = chr(64 + n_cols)
        end_row  = next_row + len(filas) - 1
        address  = f"A{next_row}:{end_col}{end_row}"

        patch_url = (
            f"{base_url}/workbook/worksheets/{SP_SHEET_NAME}"
            f"/range(address='{address}')"
        )
        resp = req_lib.patch(
            patch_url,
            headers={**auth_headers, "Content-Type": "application/json"},
            json={"values": filas},
            timeout=30
        )
        if not resp.ok:
            print(f"[SharePoint] Error al escribir: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"[SharePoint] Excepcion (no critica): {e}")


# ── Base de datos ─────────────────────────────────────────────────────────────

def get_db():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("No se encontro la variable de entorno DATABASE_URL")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return psycopg2.connect(url)


def init_db():
    conn = None
    cur  = None
    try:
        conn = get_db()
        cur  = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS merma_inventario (
                id SERIAL PRIMARY KEY,
                tienda TEXT, fecha TEXT, usuario TEXT, producto TEXT,
                inventario INTEGER, merma INTEGER, razon TEXT,
                fecha_modificacion TEXT
            )
        """)
        cur.execute("ALTER TABLE merma_inventario ADD COLUMN IF NOT EXISTS razon TEXT;")
        cur.execute("ALTER TABLE merma_inventario ADD COLUMN IF NOT EXISTS fecha_modificacion TEXT;")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cuarto_frio (
                id SERIAL PRIMARY KEY,
                tienda TEXT, fecha TEXT, usuario TEXT, producto TEXT,
                existencia INTEGER, fecha_modificacion TEXT
            )
        """)
        conn.commit()
    except Exception as e:
        print("Error al inicializar la base de datos:", e)
    finally:
        if cur:  cur.close()
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


# ── Rutas ─────────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET", "POST"])
def index():
    conn = None
    cur  = None
    try:
        conn = get_db()
        cur  = conn.cursor()

        if request.method == "POST":
            tienda      = request.form.get("tienda")
            fecha       = request.form.get("fecha")
            usuario     = request.form.get("usuario")
            productos   = request.form.getlist("producto[]")
            inventarios = request.form.getlist("inventario[]")
            mermas      = request.form.getlist("merma[]")
            razones     = request.form.getlist("razon[]")
            fecha_reg   = datetime.now().strftime("%d/%m/%Y %H:%M")

            filas_excel = []

            # Merma / Inventario
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
                    razon = razones[i] if i < len(razones) else ""
                    cur.execute(
                        """INSERT INTO merma_inventario
                           (tienda, fecha, usuario, producto, inventario, merma, razon)
                           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                        (tienda, fecha, usuario, productos[i], inv, mer, razon)
                    )
                    filas_excel.append([
                        fecha_reg, "Merma/Inventario", tienda, fecha, usuario,
                        productos[i], inv, mer, razon, ""
                    ])

            # Cuarto Frio
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
                    filas_excel.append([
                        fecha_reg, "Cuarto Frio", tienda, fecha, usuario,
                        cf_productos[i], "", "", "", existencia
                    ])

            conn.commit()

            if filas_excel:
                escribir_en_excel(filas_excel)

            return redirect("/registros")

        today = datetime.now().strftime("%d/%m/%Y")
        return render_template("index.html", tiendas=TIENDAS, today=today)

    except Exception as e:
        return f"<h2>Error en la aplicacion:</h2><pre>{e}</pre>"
    finally:
        if cur:  cur.close()
        if conn: conn.close()


@app.route("/registros")
def registros():
    conn = None
    cur  = None
    try:
        conn = get_db()
        cur  = conn.cursor()
        cur.execute("SELECT * FROM merma_inventario ORDER BY id DESC")
        merma_rows = cur.fetchall()
        cur.execute("SELECT * FROM cuarto_frio ORDER BY id DESC")
        cf_rows = cur.fetchall()
        return render_template("registros.html", registros=merma_rows, cf_registros=cf_rows)
    except Exception as e:
        return f"<h2>Error:</h2><pre>{e}</pre>"
    finally:
        if cur:  cur.close()
        if conn: conn.close()


@app.route("/editar/<int:id>", methods=["GET", "POST"])
def editar(id):
    conn = None
    cur  = None
    try:
        conn = get_db()
        cur  = conn.cursor()

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
        if cur:  cur.close()
        if conn: conn.close()


@app.route("/borrar/<int:id>", methods=["POST"])
def borrar(id):
    password = request.form.get("password")
    if password != DELETE_PASSWORD:
        return jsonify({"ok": False, "msg": "Contrasena incorrecta"}), 403
    conn = None
    cur  = None
    try:
        conn = get_db()
        cur  = conn.cursor()
        cur.execute("DELETE FROM merma_inventario WHERE id=%s", (id,))
        conn.commit()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500
    finally:
        if cur:  cur.close()
        if conn: conn.close()


@app.route("/borrar_cf/<int:id>", methods=["POST"])
def borrar_cf(id):
    password = request.form.get("password")
    if password != DELETE_PASSWORD:
        return jsonify({"ok": False, "msg": "Contrasena incorrecta"}), 403
    conn = None
    cur  = None
    try:
        conn = get_db()
        cur  = conn.cursor()
        cur.execute("DELETE FROM cuarto_frio WHERE id=%s", (id,))
        conn.commit()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500
    finally:
        if cur:  cur.close()
        if conn: conn.close()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
