from flask import Flask, render_template, request, redirect, jsonify
import psycopg2
import os
import requests as req_lib
import msal
from datetime import datetime
import threading


app = Flask(__name__)

DELETE_PASSWORD = "CFBCWALMEX"

# ── SharePoint / Excel config ─────────────────────────────────────────────────
SP_TENANT_ID     = os.environ.get("SP_TENANT_ID",     "073b7d65-a90c-4b41-8300-6555841d361f")
SP_CLIENT_ID     = os.environ.get("SP_CLIENT_ID",     "98625318-3270-42ab-ac73-6c43a82731b3")
SP_CLIENT_SECRET = os.environ.get("SP_CLIENT_SECRET", "f4R8Q~uEJ4agJag~cIlmBp4LP7BzQhz8jiWs-bMW")
SP_SITE_URL      = os.environ.get("SP_SITE_URL",      "https://pacificafarms.sharepoint.com/sites/requerimientovsproyeccion")
SP_FILE_PATH     = os.environ.get("SP_FILE_PATH",     "/requerimiento vs proyeccion/WALMEX/Analisis Walmart.xlsx")
SP_SHEET_DETALLE  = os.environ.get("SP_SHEET_NAME", "Detalle")

HEADERS_DETALLE = [
    "Fecha de registro", "Tienda", "Fecha", "Usuario",
    "Producto", "Inventario", "Merma", "Razon de merma"
]

HEADERS_CF = [
    "Fecha de registro", "Tienda", "Fecha", "Usuario",
    "Producto", "Existencia"
]

# Tabla Detalle: columnas A-H (col 1-8)
# Separador:    columna I (9) vacia
# Tabla CF:     columnas J-O (col 10-15)
COL_DETALLE_START = 1   # A
COL_CF_START      = 10  # J

# Colores en hex para Graph API (sin #)
COLOR_HEADER_DETALLE = "1A73E8"
COLOR_TEXT_HEADER    = "FFFFFF"
COLOR_HEADER_CF      = "0D9488"
COLOR_ROW_ALT        = "EBF3FD"
COLOR_ROW_ALT_CF     = "F0FDFA"


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


def _col_letter(n):
    """Convierte número de columna (1-based) a letra(s). Ej: 1->A, 27->AA"""
    result = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        result = chr(65 + r) + result
    return result


def _ensure_sheet_exists(headers, base_url, sheet_name):
    """Crea la hoja si no existe."""
    r = req_lib.get(f"{base_url}/workbook/worksheets", headers=headers, timeout=30)
    if r.ok:
        names = [s.get("name", "") for s in r.json().get("value", [])]
        if sheet_name not in names:
            req_lib.post(
                f"{base_url}/workbook/worksheets",
                headers={**headers, "Content-Type": "application/json"},
                json={"name": sheet_name}, timeout=30
            )


def _format_range(headers_auth, base_url, address, bg_color, bold=False,
                  font_color="000000", font_size=10):
    """Aplica formato de relleno y fuente a un rango dado."""
    fmt_url = (
        f"{base_url}/workbook/worksheets/{SP_SHEET_DETALLE}"
        f"/range(address='{address}')/format"
    )
    req_lib.patch(fmt_url + "/fill",
        headers={**headers_auth, "Content-Type": "application/json"},
        json={"color": bg_color}, timeout=30)
    req_lib.patch(fmt_url + "/font",
        headers={**headers_auth, "Content-Type": "application/json"},
        json={"bold": bold, "color": font_color, "size": font_size}, timeout=30)


def _ensure_table_headers(headers_auth, base_url, col_start, col_headers, bg_color):
    """
    Verifica y escribe encabezados en la fila 1 a partir de col_start.
    También aplica formato a esa fila de encabezados.
    """
    col_end      = col_start + len(col_headers) - 1
    start_letter = _col_letter(col_start)
    end_letter   = _col_letter(col_end)
    address      = f"{start_letter}1:{end_letter}1"
    range_url    = (
        f"{base_url}/workbook/worksheets/{SP_SHEET_DETALLE}"
        f"/range(address='{address}')"
    )

    r = req_lib.get(range_url, headers=headers_auth, timeout=30)
    needs_write = True
    if r.ok:
        values = r.json().get("values", [[]])
        row = values[0] if values else []
        if row and all(str(row[i]).strip() == col_headers[i]
                       for i in range(len(col_headers)) if i < len(row)):
            needs_write = False

    if needs_write:
        req_lib.patch(range_url,
            headers={**headers_auth, "Content-Type": "application/json"},
            json={"values": [col_headers]}, timeout=30)
        _format_range(headers_auth, base_url, address,
                      bg_color=bg_color, bold=True,
                      font_color=COLOR_TEXT_HEADER, font_size=11)


def _find_next_empty_row_col(headers_auth, base_url, col_start):
    """
    Busca la primera fila vacia en la columna col_start (1-based),
    leyendo celda a celda para ignorar filas borradas.
    """
    used_url = f"{base_url}/workbook/worksheets/{SP_SHEET_DETALLE}/usedRange"
    r = req_lib.get(used_url, headers=headers_auth, timeout=30)
    if not r.ok:
        return 2

    row_count = r.json().get("rowCount", 1)
    if row_count <= 1:
        return 2

    col_letter = _col_letter(col_start)
    col_url = (
        f"{base_url}/workbook/worksheets/{SP_SHEET_DETALLE}"
        f"/range(address='{col_letter}1:{col_letter}{row_count}')"
    )
    r2 = req_lib.get(col_url, headers=headers_auth, timeout=30)
    if not r2.ok:
        return row_count + 1

    values = r2.json().get("values", [])
    last_row_with_data = 1
    for i, cell in enumerate(values):
        if cell and str(cell[0]).strip():
            last_row_with_data = i + 1

    return last_row_with_data + 1


def escribir_en_excel(filas_detalle, filas_cf):
    """
    Escribe ambas tablas en la hoja Detalle:
      - Tabla Merma/Inventario: columnas A-H (col 1-8)  encabezado azul
      - Separador:              columna I (9) vacia
      - Tabla Cuarto Frio:      columnas J-O (col 10-15) encabezado teal
    """
    try:
        token = _get_sp_token()
        if not token:
            print("[SP] No se pudo obtener token.")
            return

        auth_headers = {"Authorization": f"Bearer {token}"}
        site_id      = _get_site_id(auth_headers)
        base_url     = _get_base_url(site_id)

        _ensure_sheet_exists(auth_headers, base_url, SP_SHEET_DETALLE)

        # ── Tabla Merma / Inventario (columnas A-H) ───────────────────────
        if filas_detalle:
            _ensure_table_headers(auth_headers, base_url,
                                  COL_DETALLE_START, HEADERS_DETALLE,
                                  COLOR_HEADER_DETALLE)
            next_row = _find_next_empty_row_col(auth_headers, base_url, COL_DETALLE_START)
            n_cols   = len(HEADERS_DETALLE)
            s_col    = _col_letter(COL_DETALLE_START)
            e_col    = _col_letter(COL_DETALLE_START + n_cols - 1)
            end_row  = next_row + len(filas_detalle) - 1
            address  = f"{s_col}{next_row}:{e_col}{end_row}"

            resp = req_lib.patch(
                f"{base_url}/workbook/worksheets/{SP_SHEET_DETALLE}/range(address='{address}')",
                headers={**auth_headers, "Content-Type": "application/json"},
                json={"values": filas_detalle}, timeout=30
            )
            if resp.ok:
                for i in range(len(filas_detalle)):
                    row_idx = next_row + i
                    if row_idx % 2 == 0:
                        _format_range(auth_headers, base_url,
                                      f"{s_col}{row_idx}:{e_col}{row_idx}",
                                      bg_color=COLOR_ROW_ALT, font_size=10)
            else:
                print(f"[SP] Error Detalle: {resp.status_code} {resp.text[:200]}")

        # ── Tabla Cuarto Frio (columnas J-O) ─────────────────────────────
        if filas_cf:
            _ensure_table_headers(auth_headers, base_url,
                                  COL_CF_START, HEADERS_CF,
                                  COLOR_HEADER_CF)
            next_row = _find_next_empty_row_col(auth_headers, base_url, COL_CF_START)
            n_cols   = len(HEADERS_CF)
            s_col    = _col_letter(COL_CF_START)
            e_col    = _col_letter(COL_CF_START + n_cols - 1)
            end_row  = next_row + len(filas_cf) - 1
            address  = f"{s_col}{next_row}:{e_col}{end_row}"

            resp = req_lib.patch(
                f"{base_url}/workbook/worksheets/{SP_SHEET_DETALLE}/range(address='{address}')",
                headers={**auth_headers, "Content-Type": "application/json"},
                json={"values": filas_cf}, timeout=30
            )
            if resp.ok:
                for i in range(len(filas_cf)):
                    row_idx = next_row + i
                    if row_idx % 2 == 0:
                        _format_range(auth_headers, base_url,
                                      f"{s_col}{row_idx}:{e_col}{row_idx}",
                                      bg_color=COLOR_ROW_ALT_CF, font_size=10)
            else:
                print(f"[SP] Error CuartoFrio: {resp.status_code} {resp.text[:200]}")

    except Exception as e:
        print(f"[SP] Excepcion: {e}")


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

            filas_detalle = []
            filas_cf      = []

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
                    filas_detalle.append([
                        fecha_reg, tienda, fecha, usuario,
                        productos[i], inv, mer, razon
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
                    filas_cf.append([
                        fecha_reg, tienda, fecha, usuario,
                        cf_productos[i], existencia
                    ])

            conn.commit()

            if filas_detalle or filas_cf:
                t = threading.Thread(
                    target=escribir_en_excel,
                    args=(filas_detalle, filas_cf),
                    daemon=True
                )
                t.start()

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
