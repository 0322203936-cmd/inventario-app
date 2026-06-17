from flask import Flask, render_template, request, redirect, jsonify, make_response, send_file, session
import json
import os
import base64
import requests as req_lib
import msal
from datetime import datetime
import threading


app = Flask(__name__)
app.secret_key = "cfbc_secret_key_2026"

DELETE_PASSWORD = "CFBCWALMEX"
REPORTE_PASSWORD = "cfbc2026"

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

HEADERS_GASTOS = [
    "Fecha de registro", "Tienda", "Fecha", "Usuario",
    "Categoria", "Monto"
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


def _fmt_fecha_excel(fecha_str):
    """Convierte fecha de DD/MM/YYYY a MM/DD/YY para el Excel."""
    try:
        return datetime.strptime(fecha_str, "%d/%m/%Y").strftime("%m/%d/%y")
    except Exception:
        return fecha_str  # si falla, deja el valor original


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


# ── Funcion para escribir gastos en hoja "Gastos" ─────────────────────────────

def escribir_gastos_en_excel(filas_gastos):
    """
    Escribe los montos de gastos en la hoja "Gastos" del Excel.
    """
    if not filas_gastos:
        return

    try:
        token = _get_sp_token()
        if not token:
            print("[GASTOS] No se pudo obtener token.")
            return

        auth_headers = {"Authorization": f"Bearer {token}"}
        site_id      = _get_site_id(auth_headers)
        base_url     = _get_base_url(site_id)

        sheet_name = "REPORTE-GASTOSAPP"
        _ensure_sheet_exists(auth_headers, base_url, sheet_name)

        # ── Escribir encabezados en columna A (1) ─────────────────────────
        COL_START = 1
        n_cols    = len(HEADERS_GASTOS)
        s_col     = _col_letter(COL_START)
        e_col     = _col_letter(COL_START + n_cols - 1)
        address   = f"{s_col}1:{e_col}1"

        range_url = (
            f"{base_url}/workbook/worksheets/{sheet_name}"
            f"/range(address='{address}')"
        )
        r = req_lib.get(range_url, headers=auth_headers, timeout=30)
        needs_write = True
        if r.ok:
            row = r.json().get("values", [[]])[0] if r.json().get("values") else []
            if row and all(str(row[i]).strip() == HEADERS_GASTOS[i]
                           for i in range(n_cols) if i < len(row)):
                needs_write = False

        if needs_write:
            req_lib.patch(range_url,
                headers={**auth_headers, "Content-Type": "application/json"},
                json={"values": [HEADERS_GASTOS]}, timeout=30)
            _format_range(auth_headers, base_url, address,
                          bg_color="E67E22", bold=True,
                          font_color="FFFFFF", font_size=11)

        # ── Buscar siguiente fila vacia ───────────────────────────────────
        used_url = f"{base_url}/workbook/worksheets/{sheet_name}/usedRange"
        r = req_lib.get(used_url, headers=auth_headers, timeout=30)
        next_row = 2
        if r.ok:
            row_count = r.json().get("rowCount", 1)
            if row_count >= 1:
                col_letter = _col_letter(COL_START)
                col_url = (
                    f"{base_url}/workbook/worksheets/{sheet_name}"
                    f"/range(address='{col_letter}1:{col_letter}{row_count}')"
                )
                r2 = req_lib.get(col_url, headers=auth_headers, timeout=30)
                if r2.ok:
                    values = r2.json().get("values", [])
                    last_row = 1
                    for i, cell in enumerate(values):
                        if cell and str(cell[0]).strip():
                            last_row = i + 1
                    next_row = last_row + 1

        end_row  = next_row + len(filas_gastos) - 1
        address  = f"{s_col}{next_row}:{e_col}{end_row}"

        resp = req_lib.patch(
            f"{base_url}/workbook/worksheets/{sheet_name}/range(address='{address}')",
            headers={**auth_headers, "Content-Type": "application/json"},
            json={"values": filas_gastos}, timeout=30
        )
        if resp.ok:
            for i in range(len(filas_gastos)):
                row_idx = next_row + i
                if row_idx % 2 == 0:
                    _format_range(auth_headers, base_url,
                                  f"{s_col}{row_idx}:{e_col}{row_idx}",
                                  bg_color="FFF3E0", font_size=10)
        else:
            print(f"[GASTOS] Error al escribir Excel: {resp.status_code} {resp.text[:200]}")

    except Exception as e:
        print(f"[GASTOS] Excepcion al escribir Excel: {e}")


# ── Leer gastos desde hoja "Gastos" ───────────────────────────────────────────

def leer_gastos_desde_excel():
    """
    Lee los montos desde la hoja "Gastos" del Excel.
    Retorna una lista de diccionarios con: fecha_reg, tienda, fecha, usuario, categoria, monto
    """
    try:
        token = _get_sp_token()
        if not token:
            return []
        auth_headers = {"Authorization": f"Bearer {token}"}
        site_id  = _get_site_id(auth_headers)
        base_url = _get_base_url(site_id)

        sheet_name = "REPORTE-GASTOSAPP"
        used_url = f"{base_url}/workbook/worksheets/{sheet_name}/usedRange"
        r = req_lib.get(used_url, headers=auth_headers, timeout=30)
        if not r.ok:
            print(f"[GASTOS] Hoja 'Gastos' no existe o no tiene datos: {r.status_code}")
            return []

        values = r.json().get("values", [])
        if not values or len(values) <= 1:
            return []

        gastos_excel = []
        for i, row in enumerate(values):
            if i == 0:
                continue  # saltar encabezados
            if len(row) >= 6 and str(row[0]).strip():
                gastos_excel.append({
                    "fecha_reg": str(row[0]) if len(row) > 0 else "",
                    "tienda":    str(row[1]) if len(row) > 1 else "",
                    "fecha":     str(row[2]) if len(row) > 2 else "",
                    "usuario":   str(row[3]) if len(row) > 3 else "",
                    "categoria": str(row[4]) if len(row) > 4 else "",
                    "monto":     str(row[5]) if len(row) > 5 else "0"
                })
        return gastos_excel

    except Exception as e:
        print(f"[GASTOS] Excepcion al leer Excel: {e}")
        return []


# ── Base de datos eliminada ───────────────────────────────────────────────────

TIENDAS = [
    "SC MEXICALI NOVENA","SC NUEVO MEXICALI","SC PLAZA SAN PEDRO",
    "SC MEXICALI","SC PLAYAS DE TIJUANA","SC LOMAS DE SANTA FE",
    "SC GALERIAS DEL VALLE","SC TIJUANA 2000","SC TECATE GARITA",
    "SC ROSARITO","SC ENSENADA CENTRO","SC MACROPLAZA INSURGENTES",
    "SC ENSENADA","SC TIJUANA HIPODROMO","SC PACIFICO",
    "SC DIAZ ORDAZ"
]


# ── Rutas ─────────────────────────────────────────────

@app.route("/sw.js")
def service_worker_root():
    """
    Sirve el Service Worker desde la raiz (/) para que su scope cubra
    toda la aplicacion y pueda interceptar todas las rutas sin internet.
    Sin este header, el navegador limita el scope al directorio /static/.
    """
    sw_path = os.path.join(app.root_path, 'static', 'service-worker.js')
    with open(sw_path, 'r', encoding='utf-8') as f:
        content = f.read()
    resp = make_response(content)
    resp.headers['Content-Type']           = 'application/javascript; charset=utf-8'
    resp.headers['Service-Worker-Allowed'] = '/'
    resp.headers['Cache-Control']          = 'no-cache, no-store, must-revalidate'
    return resp


@app.route("/")
def home():
    """Pantalla de inicio con los dos modulos: Inventario y Gastos."""
    return render_template("home.html")

@app.route("/inventario", methods=["GET", "POST"])
def index():
    try:
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
                    filas_detalle.append([
                        fecha_reg, tienda, _fmt_fecha_excel(fecha), usuario,
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
                    filas_cf.append([
                        fecha_reg, tienda, _fmt_fecha_excel(fecha), usuario,
                        cf_productos[i], existencia
                    ])

            if filas_detalle or filas_cf:
                t = threading.Thread(
                    target=escribir_en_excel,
                    args=(filas_detalle, filas_cf),
                    daemon=True
                )
                t.start()

            return redirect("/inventario?success=1")

        today = datetime.now().strftime("%d/%m/%Y")
        resp = make_response(render_template("index.html", tiendas=TIENDAS, today=today))
        resp.headers['Cache-Control'] = 'no-cache'
        return resp

    except Exception as e:
        return f"<h2>Error en la aplicacion:</h2><pre>{e}</pre>"


@app.route("/gastos")
def gastos():
    """Pantalla de captura de gastos (tickets por categoria)."""
    resp = make_response(render_template("gastos.html"))
    resp.headers['Cache-Control'] = 'no-cache'
    return resp


@app.route("/reporte", methods=["GET", "POST"])
def reporte():
    """Pantalla de reporte de gastos con autenticación."""
    if request.method == "POST":
        password = request.form.get("password")
        if password == REPORTE_PASSWORD:
            session["reporte_auth"] = True
            return redirect("/reporte")
        else:
            return render_template("reporte.html", error=True, auth_required=True)
    
    if not session.get("reporte_auth"):
        return render_template("reporte.html", auth_required=True)
    
    try:
        gastos_data = obtener_gastos_sharepoint()
        return render_template("reporte.html", gastos=gastos_data, auth_required=False)
    except Exception as e:
        return f"<h2>Error:</h2><pre>{e}</pre>"


def _listar_archivos_recursivo(headers_auth, site_id, folder_path, max_depth=3):
    """
    Lista recursivamente todos los archivos de imagen dentro de una carpeta
    y sus subcarpetas (hasta max_depth niveles de profundidad).
    Retorna una lista de archivos (dicts de Graph API).
    """
    all_files = []
    seen_ids  = set()

    def _explore(fpath, depth):
        if depth > max_depth:
            return
        if not fpath.startswith("/"):
            fpath = "/" + fpath
        children_url = (
            f"https://graph.microsoft.com/v1.0/sites/{site_id}"
            f"/drive/root:{fpath}:/children"
        )
        try:
            r = req_lib.get(children_url, headers=headers_auth, timeout=30)
            if not r.ok:
                return
            items = r.json().get("value", [])
            for item in items:
                item_id = item.get("id", "")
                if item_id in seen_ids:
                    continue
                seen_ids.add(item_id)

                name = item.get("name", "")
                # Si es carpeta, explorar recursivamente
                if item.get("folder"):
                    _explore(f"{fpath}/{name}", depth + 1)
                # Si es imagen, agregarla
                elif name.lower().endswith(('.jpg', '.jpeg', '.png')):
                    all_files.append(item)
        except Exception:
            pass

    _explore(folder_path, 0)
    return all_files


def obtener_gastos_sharepoint():
    """
    Obtiene la lista de fotos y montos de gastos de SharePoint.
    Retorna una lista de diccionarios con: nombre, url, categoria, fecha, tienda, usuario, monto
    """
    try:
        token = _get_sp_token()
        if not token:
            print("[GASTOS] No se pudo obtener token")
            return []
        
        auth_headers = {"Authorization": f"Bearer {token}"}
        site_id = _get_site_id(auth_headers)
        
        # ── Leer montos desde hoja Excel "Gastos" ─────────────────────────
        gastos_excel = leer_gastos_desde_excel()

        # ── Listar fotos recursivamente en todas las subcarpetas ──────────
        print(f"[GASTOS] Listando archivos recursivamente en: {SP_GASTOS_FOLDER}")
        files = _listar_archivos_recursivo(auth_headers, site_id, SP_GASTOS_FOLDER)
        print(f"[GASTOS] Archivos de imagen encontrados: {len(files)}")
        
        gastos = []
        
        for file in files:
            name = file.get("name", "")
            if not name.lower().endswith(('.jpg', '.jpeg', '.png')):
                continue
                
            # ── Parsear nombre del archivo ────────────────────────────────
            # Formato: TIENDA_USUARIO_FECHA_TIMESTAMP_NUMERO.jpg
            # Ejemplo: SC_Tijuana_Mizael_17-06-2025_20250617_083045_1.jpg
            base_name = name.rsplit(".", 1)[0]  # quitar extension
            parts = base_name.split("_")
            
            if len(parts) >= 3:
                # Reconstruir tienda: puede tener varias partes
                # Buscar: los primeros partes hasta encontrar un nombre de usuario conocido
                # Estrategia simple: partes[0] puede ser "SC" o nombre de ciudad
                # Unir partes que no sean fecha, usuario conocido o timestamp
                idx_usuario = -1
                usuarios_conocidos = ["Mizael", "Esteban", "Victor"]
                for j, p in enumerate(parts):
                    if p in usuarios_conocidos:
                        idx_usuario = j
                        break
                
                if idx_usuario >= 2:
                    tienda = " ".join(parts[:idx_usuario]).replace("_", " ")
                    usuario = parts[idx_usuario]
                    # La fecha deberia estar en parts[idx_usuario+1]
                    fecha_str = parts[idx_usuario + 1] if len(parts) > idx_usuario + 1 else "01-01-2025"
                else:
                    tienda = parts[0].replace("_", " ") if parts[0] else "Desconocido"
                    usuario = parts[1] if len(parts) > 1 else "Desconocido"
                    fecha_str = parts[2] if len(parts) > 2 else "01-01-2025"
                
                timestamp_parts = [p for p in parts if len(p) == 15 and p[:4].isdigit() and p[4:6].isdigit()]
                timestamp = timestamp_parts[0] if timestamp_parts else "20250101_000000"
                
                # ── Determinar categoría por la ruta ──────────────────────
                parent_path = file.get("parentReference", {}).get("path", "")
                categoria = "DESCONOCIDO"
                if "CASETAS" in parent_path.upper():
                    categoria = "CASETAS"
                elif "COMIDA" in parent_path.upper():
                    categoria = "COMIDA"
                elif "OTROS" in parent_path.upper():
                    categoria = "OTROS"

                # URL de descarga
                download_url = file.get("@microsoft.graph.downloadUrl", "")
                
                # ── Buscar el monto correspondiente en Excel ──────────────
                monto = ""
                for ge in gastos_excel:
                    if (ge["tienda"].lower().strip() == tienda.lower().strip() and
                        ge["usuario"].lower().strip() == usuario.lower().strip() and
                        ge["categoria"].lower().strip() == categoria.lower().strip()):
                        # Verificar fecha aproximada
                        if fecha_str in ge["fecha"] or ge["fecha"] in fecha_str:
                            monto = ge["monto"]
                            break
                
                gasto = {
                    "nombre": name,
                    "url": download_url,
                    "categoria": categoria,
                    "tienda": tienda,
                    "usuario": usuario,
                    "fecha": fecha_str,
                    "timestamp": timestamp,
                    "monto": monto
                }
                gastos.append(gasto)
        
        # ── Ordenar por fecha más reciente ────────────────────────────────
        gastos.sort(key=lambda x: x["timestamp"], reverse=True)
        print(f"[GASTOS] Total gastos procesados: {len(gastos)}")
        return gastos
        
    except Exception as e:
        print(f"[GASTOS] Excepcion: {e}")
        return []


def leer_desde_excel():
    token = _get_sp_token()
    if not token:
        return [], []
    auth_headers = {"Authorization": f"Bearer {token}"}
    site_id = _get_site_id(auth_headers)
    base_url = _get_base_url(site_id)
    
    used_url = f"{base_url}/workbook/worksheets/{SP_SHEET_DETALLE}/usedRange"
    r = req_lib.get(used_url, headers=auth_headers, timeout=30)
    if not r.ok:
        return [], []
    
    values = r.json().get("values", [])
    if not values:
        return [], []
    
    merma_rows = []
    cf_rows = []
    
    for i, row in enumerate(values):
        if i == 0: continue
        row_id = i + 1
        
        # Merma (Cols A-H -> index 0-7)
        if len(row) > 4 and str(row[1]).strip() and str(row[4]).strip():
            tienda = row[1] if len(row) > 1 else ""
            fecha = row[2] if len(row) > 2 else ""
            usuario = row[3] if len(row) > 3 else ""
            producto = row[4] if len(row) > 4 else ""
            inv = row[5] if len(row) > 5 else 0
            merma = row[6] if len(row) > 6 else 0
            razon = row[7] if len(row) > 7 else ""
            merma_rows.append([row_id, tienda, fecha, usuario, producto, inv, merma, razon, ""])
            
        # CF (Cols J-O -> index 9-14)
        if len(row) > 13 and str(row[10]).strip() and str(row[13]).strip():
            tienda_cf = row[10] if len(row) > 10 else ""
            fecha_cf = row[11] if len(row) > 11 else ""
            usuario_cf = row[12] if len(row) > 12 else ""
            producto_cf = row[13] if len(row) > 13 else ""
            existencia = row[14] if len(row) > 14 else 0
            cf_rows.append([row_id, tienda_cf, fecha_cf, usuario_cf, producto_cf, existencia, ""])

    merma_rows.reverse()
    cf_rows.reverse()
    return merma_rows, cf_rows


@app.route("/registros")
def registros():
    try:
        merma_rows, cf_rows = leer_desde_excel()
        return render_template("registros.html", registros=merma_rows, cf_registros=cf_rows)
    except Exception as e:
        return f"<h2>Error:</h2><pre>{e}</pre>"


@app.route("/editar/<int:id>", methods=["GET", "POST"])
def editar(id):
    try:
        merma_rows, _ = leer_desde_excel()
        reg = next((r for r in merma_rows if r[0] == id), None)
        
        if request.method == "POST":
            tienda     = request.form.get("tienda")
            fecha      = request.form.get("fecha")
            usuario    = request.form.get("usuario")
            producto   = request.form.get("producto")
            inventario = request.form.get("inventario") or 0
            merma      = request.form.get("merma") or 0
            razon      = request.form.get("razon") or ""
            
            token = _get_sp_token()
            if token:
                auth_headers = {"Authorization": f"Bearer {token}"}
                site_id = _get_site_id(auth_headers)
                base_url = _get_base_url(site_id)
                address = f"B{id}:H{id}"
                valores = [[tienda, _fmt_fecha_excel(fecha), usuario, producto, inventario, merma, razon]]
                req_lib.patch(
                    f"{base_url}/workbook/worksheets/{SP_SHEET_DETALLE}/range(address='{address}')",
                    headers={**auth_headers, "Content-Type": "application/json"},
                    json={"values": valores}, timeout=30
                )
            return redirect("/registros")

        if not reg:
            return redirect("/registros")
        return render_template("editar.html", reg=reg, tiendas=TIENDAS)
    except Exception as e:
        return f"<h2>Error:</h2><pre>{e}</pre>"


@app.route("/borrar/<int:id>", methods=["POST"])
def borrar(id):
    password = request.form.get("password")
    if password != DELETE_PASSWORD:
        return jsonify({"ok": False, "msg": "Contrasena incorrecta"}), 403
    try:
        token = _get_sp_token()
        if token:
            auth_headers = {"Authorization": f"Bearer {token}"}
            site_id = _get_site_id(auth_headers)
            base_url = _get_base_url(site_id)
            req_lib.post(
                f"{base_url}/workbook/worksheets/{SP_SHEET_DETALLE}/range(address='A{id}:H{id}')/delete",
                headers={**auth_headers, "Content-Type": "application/json"},
                json={"shift": "Up"}, timeout=30
            )
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500


@app.route("/borrar_cf/<int:id>", methods=["POST"])
def borrar_cf(id):
    password = request.form.get("password")
    if password != DELETE_PASSWORD:
        return jsonify({"ok": False, "msg": "Contrasena incorrecta"}), 403
    try:
        token = _get_sp_token()
        if token:
            auth_headers = {"Authorization": f"Bearer {token}"}
            site_id = _get_site_id(auth_headers)
            base_url = _get_base_url(site_id)
            req_lib.post(
                f"{base_url}/workbook/worksheets/{SP_SHEET_DETALLE}/range(address='J{id}:O{id}')/delete",
                headers={**auth_headers, "Content-Type": "application/json"},
                json={"shift": "Up"}, timeout=30
            )
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500


# ── Endpoints para soporte offline ──────────────────────────────────────────

@app.route("/ping")
def ping():
    """Endpoint liviano para verificar conectividad desde el cliente."""
    resp = make_response(jsonify({"ok": True}), 200)
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp


# ── SharePoint: subida de fotos ───────────────────────────────────────────────

SP_GASTOS_FOLDER = "/requerimiento vs proyeccion/WALMEX/Gastos"

def subir_foto_sharepoint(imagen_base64, ruta_destino, auth_headers, base_url):
    """
    Sube una imagen (base64) a SharePoint via Graph API.
    ruta_destino: ej. 'Gastos/2025-06/CASETAS/Mizael_20250617_083045.jpg'
    """
    # Decodificar base64 (puede venir como data:image/jpeg;base64,...)
    if ',' in imagen_base64:
        imagen_base64 = imagen_base64.split(',', 1)[1]
    img_bytes = base64.b64decode(imagen_base64)

    # Construir URL de subida en el drive del sitio
    site_parts    = SP_SITE_URL.rstrip("/").split("/")
    sp_hostname   = site_parts[2]
    sp_site_path  = "/".join(site_parts[3:])

    token    = auth_headers["Authorization"].replace("Bearer ", "")
    site_url = f"https://graph.microsoft.com/v1.0/sites/{sp_hostname}:/{sp_site_path}"
    r = req_lib.get(site_url, headers=auth_headers, timeout=30)
    r.raise_for_status()
    site_id = r.json()["id"]

    upload_url = (
        f"https://graph.microsoft.com/v1.0/sites/{site_id}"
        f"/drive/root:/{ruta_destino}:/content"
    )
    resp = req_lib.put(
        upload_url,
        headers={**auth_headers, "Content-Type": "image/jpeg"},
        data=img_bytes,
        timeout=60
    )
    return resp.ok


def procesar_gastos(pendiente):
    """
    Sube las fotos de un registro de gastos a SharePoint
    Y guarda los montos en la hoja 'Gastos' del Excel.
    Se ejecuta en un hilo separado.
    """
    try:
        token = _get_sp_token()
        if not token:
            print("[GASTOS] No se pudo obtener token.")
            return

        auth_headers = {"Authorization": f"Bearer {token}"}
        site_id  = _get_site_id(auth_headers)
        base_url = _get_base_url(site_id)

        tienda   = pendiente.get("tienda", "SinTienda").replace(" ", "_")
        usuario  = pendiente.get("usuario", "SinUsuario")
        fecha    = pendiente.get("fecha", "").replace("/", "-")  # DD-MM-YYYY
        fecha_reg = datetime.now()
        timestamp = fecha_reg.strftime("%Y%m%d_%H%M%S")
        mes_folder = fecha_reg.strftime("%Y-%m")

        # ── Filas para el Excel de gastos (montos) ───────────────────────
        filas_gastos = []

        categorias = ["casetas", "comida", "otros"]
        for cat in categorias:
            cat_data = pendiente.get(cat, {})
            fotos = cat_data.get("fotos", [])
            monto = cat_data.get("monto", 0)
            
            # Subir fotos a SharePoint
            for i, foto_b64 in enumerate(fotos):
                nombre_archivo = f"{tienda}_{usuario}_{fecha}_{timestamp}_{i+1}.jpg"
                ruta = (
                    f"{SP_GASTOS_FOLDER.lstrip('/')}/"
                    f"{mes_folder}/{cat.upper()}/{nombre_archivo}"
                )
                ok = subir_foto_sharepoint(foto_b64, ruta, auth_headers, base_url)
                if ok:
                    print(f"[GASTOS] Subida: {ruta}")
                else:
                    print(f"[GASTOS] Error al subir: {ruta}")

            # Guardar el monto en el Excel (una fila por categoria)
            if monto > 0:
                fecha_reg_str = fecha_reg.strftime("%d/%m/%Y %H:%M")
                filas_gastos.append([
                    fecha_reg_str,
                    pendiente.get("tienda", ""),
                    pendiente.get("fecha", ""),
                    usuario,
                    cat.upper(),
                    monto
                ])

        # ── Escribir montos en Excel ──────────────────────────────────────
        if filas_gastos:
            t_excel = threading.Thread(
                target=escribir_gastos_en_excel,
                args=(filas_gastos,),
                daemon=True
            )
            t_excel.start()

    except Exception as e:
        print(f"[GASTOS] Excepcion: {e}")


@app.route("/gastos/sync", methods=["POST"])
def gastos_sync():
    """
    Recibe registros de gastos (fotos en base64) y los sube a SharePoint.
    Body JSON: { "pendientes": [ { tipo, tienda, usuario, fecha, casetas, comida, otros }, ... ] }
    """
    try:
        data = request.get_json(force=True)
        if not data or "pendientes" not in data:
            return jsonify({"ok": False, "msg": "Formato invalido"}), 400

        pendientes = data["pendientes"]
        if not pendientes:
            return jsonify({"ok": True, "sincronizados": 0})

        for p in pendientes:
            t = threading.Thread(target=procesar_gastos, args=(p,), daemon=True)
            t.start()

        return jsonify({"ok": True, "sincronizados": len(pendientes)})

    except Exception as e:
        print(f"[GASTOS SYNC] Error: {e}")
        return jsonify({"ok": False, "msg": str(e)}), 500


@app.route("/sync", methods=["POST"])
def sync():
    """
    Recibe registros capturados offline (almacenados en IndexedDB del navegador)
    y los escribe en SharePoint igual que la ruta principal.

    Formato esperado del body JSON:
    {
        "pendientes": [
            {
                "tipo": "form",          // Un envio de formulario completo
                "tienda": "SC MEXICALI",
                "fecha": "06/17/25",
                "usuario": "Mizael",
                "fecha_reg": "17/06/2025 08:30",
                "filas_detalle": [[fecha_reg, tienda, fecha, usuario, producto, inv, merma, razon], ...],
                "filas_cf": [[fecha_reg, tienda, fecha, usuario, producto, existencia], ...]
            },
            ...
        ]
    }
    """
    try:
        data = request.get_json(force=True)
        if not data or "pendientes" not in data:
            return jsonify({"ok": False, "msg": "Formato invalido"}), 400

        pendientes = data["pendientes"]
        if not pendientes:
            return jsonify({"ok": True, "sincronizados": 0})

        all_detalle = []
        all_cf      = []

        for p in pendientes:
            filas_d = p.get("filas_detalle", [])
            filas_c = p.get("filas_cf", [])
            if filas_d:
                all_detalle.extend(filas_d)
            if filas_c:
                all_cf.extend(filas_c)

        if all_detalle or all_cf:
            # Escribir en segundo plano igual que el envio normal
            t = threading.Thread(
                target=escribir_en_excel,
                args=(all_detalle, all_cf),
                daemon=True
            )
            t.start()

        return jsonify({"ok": True, "sincronizados": len(pendientes)})

    except Exception as e:
        print(f"[SYNC] Error: {e}")
        return jsonify({"ok": False, "msg": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))