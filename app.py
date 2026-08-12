from flask import Flask, render_template, request, redirect, jsonify, make_response, send_file
import json
import os
from dotenv import load_dotenv
load_dotenv()
import base64
import requests as req_lib
import msal
import threading
from collections import OrderedDict
from urllib.parse import quote, quote_plus, unquote, urlsplit
from neon_db import database_client
import cv2
import numpy as np
import re
from datetime import datetime

# OCR eliminado a petición del usuario para ahorrar memoria RAM
reader = None
def mejorar_imagen_opencv(img_bytes):
    """Preprocesa la imagen usando OpenCV para mejorar el OCR"""
    img = cv2.imdecode(img_bytes, cv2.IMREAD_COLOR)
    
    # Convertir a escala de grises
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Aumentar contraste con CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    contrast_img = clahe.apply(gray)
    
    # Reducir ruido conservando bordes
    denoised = cv2.fastNlMeansDenoising(contrast_img, None, h=10, searchWindowSize=21, templateWindowSize=7)
    
    # Convertir de vuelta a BGR porque PaddleOCR espera 3 canales
    denoised_bgr = cv2.cvtColor(denoised, cv2.COLOR_GRAY2BGR)
    return denoised_bgr


app = Flask(__name__)

DELETE_PASSWORD = "CFBCWALMEX"

# Base de datos local: Neon PostgreSQL. La conexion privada vive solo en el servidor.

# ── SharePoint / Excel config ─────────────────────────────────────────────────
SP_TENANT_ID     = os.environ.get("SP_TENANT_ID",     "")
SP_CLIENT_ID     = os.environ.get("SP_CLIENT_ID",     "")
SP_CLIENT_SECRET = os.environ.get("SP_CLIENT_SECRET", "")
SP_SITE_URL      = os.environ.get("SP_SITE_URL",      "")
SP_FILE_PATH     = os.environ.get("SP_FILE_PATH",     "")
SP_SHEET_DETALLE  = os.environ.get("SP_SHEET_NAME", "Detalle")
SP_SHEET_GASTOS   = "REPORTE-GASTOSAPP"

HEADERS_DETALLE = [
    "Fecha de registro", "Tienda", "Fecha", "Usuario",
    "Producto", "Inventario", "Merma", "Razon de merma"
]

HEADERS_CF = [
    "Fecha de registro", "Tienda", "Fecha", "Usuario",
    "Producto", "Existencia"
]

HEADERS_GASTOS = [
    "Fecha de registro", "Tienda", "Fecha del Gasto", "Usuario",
    "Categoria", "Monto", "Fotos", "Viaticos", "Comentarios"
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
COLOR_HEADER_GASTOS  = "E67E22"
COLOR_ROW_ALT        = "EBF3FD"
COLOR_ROW_ALT_CF     = "F0FDFA"


import time

_TOKEN_CACHE = None
_TOKEN_EXPIRY = 0
_SITE_ID_CACHE = None
_DOWNLOAD_URL_CACHE = {}
_PHOTO_BYTES_CACHE = OrderedDict()
_PHOTO_BYTES_CACHE_SIZE = 0
_PHOTO_BYTES_CACHE_LIMIT = 24 * 1024 * 1024
_PHOTO_CACHE_LOCK = threading.RLock()
_DOWNLOAD_URL_CACHE_LOCK = threading.RLock()
# Microsoft Graph empieza a responder 429/5xx cuando el reporte intenta abrir
# demasiadas fotos en paralelo. Esta cola mantiene una concurrencia estable.
_GRAPH_PHOTO_SEMAPHORE = threading.BoundedSemaphore(4)
_GRAPH_RETRY_STATUSES = {408, 429, 500, 502, 503, 504}


def _retry_wait(response, attempt):
    """Respeta Retry-After de Graph y usa espera exponencial como respaldo."""
    retry_after = response.headers.get("Retry-After") if response is not None else None
    try:
        return min(max(float(retry_after), 0.25), 15.0)
    except (TypeError, ValueError):
        return min(0.75 * (2 ** attempt), 8.0)


def _photo_http_get(url, *, headers=None, timeout=30, attempts=5):
    """GET tolerante a limitacion y fallos transitorios de SharePoint/Graph."""
    last_response = None
    last_error = None
    for attempt in range(attempts):
        try:
            with _GRAPH_PHOTO_SEMAPHORE:
                last_response = req_lib.get(url, headers=headers, timeout=timeout)
            if last_response.ok or last_response.status_code not in _GRAPH_RETRY_STATUSES:
                return last_response
        except req_lib.RequestException as exc:
            last_error = exc
        if attempt < attempts - 1:
            time.sleep(_retry_wait(last_response, attempt))
    if last_response is not None:
        return last_response
    if last_error:
        raise last_error
    return None

def _get_sp_token():
    global _TOKEN_CACHE, _TOKEN_EXPIRY
    if _TOKEN_CACHE and time.time() < _TOKEN_EXPIRY:
        return _TOKEN_CACHE
        
    msal_app = msal.ConfidentialClientApplication(
        SP_CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{SP_TENANT_ID}",
        client_credential=SP_CLIENT_SECRET,
    )
    result = msal_app.acquire_token_for_client(
        scopes=["https://graph.microsoft.com/.default"]
    )
    
    token = result.get("access_token")
    if token:
        _TOKEN_CACHE = token
        _TOKEN_EXPIRY = time.time() + 3000 # Cache for 50 mins
    return token


def _get_site_id(headers):
    global _SITE_ID_CACHE
    if _SITE_ID_CACHE:
        return _SITE_ID_CACHE
        
    parts     = SP_SITE_URL.rstrip("/").split("/")
    hostname  = parts[2]
    site_path = "/".join(parts[3:])
    r = req_lib.get(
        f"https://graph.microsoft.com/v1.0/sites/{hostname}:/{site_path}",
        headers=headers, timeout=30
    )
    r.raise_for_status()
    _SITE_ID_CACHE = r.json()["id"]
    return _SITE_ID_CACHE


def _get_base_url(site_id):
    return (
        f"https://graph.microsoft.com/v1.0/sites/{site_id}"
        f"/drive/root:{SP_FILE_PATH}:"
    )


def _fmt_fecha_excel(fecha_str):
    """Convierte fecha de DD/MM/YYYY a YYYY-MM-DD para el Excel."""
    try:
        return datetime.strptime(fecha_str, "%d/%m/%Y").strftime("%Y-%m-%d")
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
                  font_color="000000", font_size=10, sheet_name=SP_SHEET_DETALLE):
    """Aplica formato de relleno y fuente a un rango dado."""
    fmt_url = (
        f"{base_url}/workbook/worksheets/{sheet_name}"
        f"/range(address='{address}')/format"
    )
    req_lib.patch(fmt_url + "/fill",
        headers={**headers_auth, "Content-Type": "application/json"},
        json={"color": bg_color}, timeout=30)
    req_lib.patch(fmt_url + "/font",
        headers={**headers_auth, "Content-Type": "application/json"},
        json={"bold": bold, "color": font_color, "size": font_size}, timeout=30)


def _ensure_table_headers(headers_auth, base_url, col_start, col_headers, bg_color, sheet_name=SP_SHEET_DETALLE):
    """
    Verifica y escribe encabezados en la fila 1 a partir de col_start.
    También aplica formato a esa fila de encabezados.
    """
    col_end      = col_start + len(col_headers) - 1
    start_letter = _col_letter(col_start)
    end_letter   = _col_letter(col_end)
    address      = f"{start_letter}1:{end_letter}1"
    range_url    = (
        f"{base_url}/workbook/worksheets/{sheet_name}"
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
                      font_color=COLOR_TEXT_HEADER, font_size=11, sheet_name=sheet_name)


def _find_next_empty_row_col(headers_auth, base_url, col_start, sheet_name=SP_SHEET_DETALLE):
    """
    Busca la primera fila vacia en la columna col_start (1-based),
    leyendo celda a celda para ignorar filas borradas.
    """
    used_url = f"{base_url}/workbook/worksheets/{sheet_name}/usedRange"
    r = req_lib.get(used_url, headers=headers_auth, timeout=30)
    if not r.ok:
        return 2

    row_count = r.json().get("rowCount", 1)
    if row_count <= 1:
        return 2

    col_letter = _col_letter(col_start)
    col_url = (
        f"{base_url}/workbook/worksheets/{sheet_name}"
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

def escribir_gasto_en_excel(filas_gastos):
    """Escribe registros en la hoja Gastos."""
    if not filas_gastos:
        return
    try:
        token = _get_sp_token()
        if not token:
            print("[SP Gastos] No se pudo obtener token.")
            return

        auth_headers = {"Authorization": f"Bearer {token}"}
        site_id      = _get_site_id(auth_headers)
        base_url     = _get_base_url(site_id)

        _ensure_sheet_exists(auth_headers, base_url, SP_SHEET_GASTOS)
        
        _ensure_table_headers(auth_headers, base_url, 1, HEADERS_GASTOS, COLOR_HEADER_GASTOS, sheet_name=SP_SHEET_GASTOS)
        
        next_row = _find_next_empty_row_col(auth_headers, base_url, 1, sheet_name=SP_SHEET_GASTOS)
        n_cols   = len(HEADERS_GASTOS)
        s_col    = "A"
        e_col    = _col_letter(n_cols)
        end_row  = next_row + len(filas_gastos) - 1
        address  = f"{s_col}{next_row}:{e_col}{end_row}"

        resp = req_lib.patch(
            f"{base_url}/workbook/worksheets/{SP_SHEET_GASTOS}/range(address='{address}')",
            headers={**auth_headers, "Content-Type": "application/json"},
            json={"values": filas_gastos}, timeout=30
        )
        if resp.ok:
            for i in range(len(filas_gastos)):
                row_idx = next_row + i
                if row_idx % 2 == 0:
                    _format_range(auth_headers, base_url,
                                  f"{s_col}{row_idx}:{e_col}{row_idx}",
                                  bg_color=COLOR_ROW_ALT, font_size=10, sheet_name=SP_SHEET_GASTOS)
        else:
            print(f"[SP Gastos] Error: {resp.status_code} {resp.text[:200]}")

    except Exception as e:
        print(f"[SP Gastos] Excepcion: {e}")


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
            fecha_reg   = datetime.now().strftime("%Y-%m-%d %H:%M")

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

@app.route("/facturacion")
def facturacion():
    """Pantalla de facturación."""
    resp = make_response(render_template("facturacion.html"))
    resp.headers['Cache-Control'] = 'no-cache'
    return resp


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

SP_GASTOS_FOLDER = "requerimiento vs proyeccion/WALMEX/Gastos"


def _graph_path(path):
    """Codifica una ruta de SharePoint conservando sus separadores."""
    return quote(path.strip("/"), safe="/")


def _ensure_sharepoint_folder(site_id, auth_headers, folder_path):
    """Crea, si hace falta, cada segmento de una carpeta del drive del sitio."""
    current = ""
    for segment in [p for p in folder_path.strip("/").split("/") if p]:
        parent = current
        current = f"{current}/{segment}" if current else segment
        check_url = (
            f"https://graph.microsoft.com/v1.0/sites/{site_id}"
            f"/drive/root:/{_graph_path(current)}"
        )
        check = req_lib.get(check_url, headers=auth_headers, timeout=30)
        if check.ok:
            continue
        if check.status_code != 404:
            check.raise_for_status()

        if parent:
            children_url = (
                f"https://graph.microsoft.com/v1.0/sites/{site_id}"
                f"/drive/root:/{_graph_path(parent)}:/children"
            )
        else:
            children_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/root/children"
        created = req_lib.post(
            children_url,
            headers={**auth_headers, "Content-Type": "application/json"},
            json={"name": segment, "folder": {}, "@microsoft.graph.conflictBehavior": "fail"},
            timeout=30,
        )
        if not created.ok and created.status_code != 409:
            created.raise_for_status()


def _thumbnail_bytes(img_bytes, max_side=360, quality=68):
    """Genera una miniatura JPEG liviana para el reporte."""
    image = cv2.imdecode(np.frombuffer(img_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        return img_bytes
    height, width = image.shape[:2]
    scale = min(1.0, max_side / max(height, width))
    if scale < 1.0:
        image = cv2.resize(
            image,
            (max(1, round(width * scale)), max(1, round(height * scale))),
            interpolation=cv2.INTER_AREA,
        )
    ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return encoded.tobytes() if ok else img_bytes


def _thumb_path(path):
    stem, ext = os.path.splitext(path)
    return f"{stem}__thumb{ext or '.jpg'}"


def _legacy_object_path(value):
    marker = "/storage/v1/object/public/gastos-fotos/"
    if marker not in value:
        return None
    return unquote(value.split(marker, 1)[1].split("?", 1)[0])


def _download_legacy_photo(value):
    """Recupera una foto historica desde su URL publica original de Supabase."""
    try:
        parsed = urlsplit(value)
        if parsed.scheme != "https" or not parsed.hostname or not parsed.hostname.endswith(".supabase.co"):
            return None
        if "/storage/v1/object/public/gastos-fotos/" not in parsed.path:
            return None
        response = _photo_http_get(value, timeout=30, attempts=4)
        if not response.ok:
            print(f"[FOTO] Legacy download error {response.status_code}: {value}")
            return None
        return response.content, response.headers.get("Content-Type", "image/jpeg")
    except Exception as exc:
        print(f"[FOTO] Legacy download exception: {exc}")
        return None


def _photo_proxy_url(value, thumbnail=False):
    if not value:
        return ""
    suffix = "&thumb=1" if thumbnail else ""
    return f"/api/foto?path={quote_plus(value)}{suffix}"


app.jinja_env.globals["foto_proxy_url"] = _photo_proxy_url


def _photo_cache_get(key):
    with _PHOTO_CACHE_LOCK:
        item = _PHOTO_BYTES_CACHE.get(key)
        if item is None:
            return None
        _PHOTO_BYTES_CACHE.move_to_end(key)
        return item


def _photo_cache_put(key, content, content_type):
    global _PHOTO_BYTES_CACHE_SIZE
    if len(content) > _PHOTO_BYTES_CACHE_LIMIT // 2:
        return
    with _PHOTO_CACHE_LOCK:
        old = _PHOTO_BYTES_CACHE.pop(key, None)
        if old:
            _PHOTO_BYTES_CACHE_SIZE -= len(old[0])
        _PHOTO_BYTES_CACHE[key] = (content, content_type)
        _PHOTO_BYTES_CACHE_SIZE += len(content)
        while _PHOTO_BYTES_CACHE and _PHOTO_BYTES_CACHE_SIZE > _PHOTO_BYTES_CACHE_LIMIT:
            _, removed = _PHOTO_BYTES_CACHE.popitem(last=False)
            _PHOTO_BYTES_CACHE_SIZE -= len(removed[0])


def _sharepoint_download_url(site_id, auth_headers, candidate, force_refresh=False):
    """Obtiene y cachea el enlace temporal de descarga de una foto."""
    if not force_refresh:
        with _DOWNLOAD_URL_CACHE_LOCK:
            cached = _DOWNLOAD_URL_CACHE.get(candidate)
            if cached and cached["expiry"] > time.time():
                return cached["url"], None

    meta_url = (
        f"https://graph.microsoft.com/v1.0/sites/{site_id}"
        f"/drive/root:/{_graph_path(candidate)}"
    )
    response = _photo_http_get(meta_url, headers=auth_headers, timeout=20, attempts=5)
    if response is None or not response.ok:
        return None, response
    download_url = response.json().get("@microsoft.graph.downloadUrl")
    if download_url:
        with _DOWNLOAD_URL_CACHE_LOCK:
            _DOWNLOAD_URL_CACHE[candidate] = {
                "url": download_url,
                "expiry": time.time() + 2700,
            }
    return download_url, response


def _download_sharepoint_photo(site_id, auth_headers, candidate):
    """Descarga una foto y renueva una vez su enlace si Microsoft lo invalido."""
    for refresh in (False, True):
        download_url, metadata_response = _sharepoint_download_url(
            site_id, auth_headers, candidate, force_refresh=refresh
        )
        if not download_url:
            return None, metadata_response
        response = _photo_http_get(download_url, timeout=40, attempts=5)
        if response is not None and response.ok:
            return response, metadata_response
        # Los enlaces @microsoft.graph.downloadUrl son temporales. Si uno
        # expiro o fallo repetidamente, se elimina y se solicita uno nuevo.
        with _DOWNLOAD_URL_CACHE_LOCK:
            _DOWNLOAD_URL_CACHE.pop(candidate, None)
    return response, metadata_response

def subir_foto_sharepoint(imagen_base64, ruta_destino, auth_headers, base_url=None,
                          site_id=None, crear_miniatura=True):
    """
    Sube una imagen (base64) a SharePoint via Graph API.
    ruta_destino: ej. 'Gastos/2025-06/CASETAS/Mizael_20250617_083045.jpg'
    """
    # Decodificar base64 (puede venir como data:image/jpeg;base64,...)
    if ',' in imagen_base64:
        imagen_base64 = imagen_base64.split(',', 1)[1]
    img_bytes = base64.b64decode(imagen_base64)

    site_id = site_id or _get_site_id(auth_headers)
    parent_folder = os.path.dirname(ruta_destino).replace("\\", "/")
    _ensure_sharepoint_folder(site_id, auth_headers, parent_folder)

    upload_url = (
        f"https://graph.microsoft.com/v1.0/sites/{site_id}"
        f"/drive/root:/{_graph_path(ruta_destino)}:/content"
    )
    resp = req_lib.put(
        upload_url,
        headers={**auth_headers, "Content-Type": "image/jpeg"},
        data=img_bytes,
        timeout=60
    )
    resp.raise_for_status()

    if crear_miniatura:
        thumb = _thumbnail_bytes(img_bytes)
        thumb_url = (
            f"https://graph.microsoft.com/v1.0/sites/{site_id}"
            f"/drive/root:/{_graph_path(_thumb_path(ruta_destino))}:/content"
        )
        thumb_resp = req_lib.put(
            thumb_url,
            headers={**auth_headers, "Content-Type": "image/jpeg"},
            data=thumb,
            timeout=60,
        )
        thumb_resp.raise_for_status()
    return True


def subir_foto_sharepoint_auto(imagen_base64, ruta_relativa):
    """Sube una foto y devuelve una ruta estable, nunca una URL temporal."""
    try:
        token = _get_sp_token()
        if not token:
            raise RuntimeError("No se pudo obtener token de Microsoft Graph")
        auth_headers = {"Authorization": f"Bearer {token}"}
        site_id = _get_site_id(auth_headers)
        ruta_destino = f"{SP_GASTOS_FOLDER}/{ruta_relativa.lstrip('/')}"
        subir_foto_sharepoint(
            imagen_base64,
            ruta_destino,
            auth_headers,
            site_id=site_id,
            crear_miniatura=True,
        )
        return ruta_destino
    except Exception as exc:
        print(f"[SHAREPOINT] Error subiendo foto: {exc}")
        return None


def procesar_gastos(pendiente):
    """
    Sube las fotos de un registro de gastos a SharePoint.
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

        categorias = ["casetas", "comida", "otros"]
        filas_gastos = []
        for cat in categorias:
            cat_data = pendiente.get(cat, {})
            fotos = cat_data.get("fotos", [])
            monto = cat_data.get("monto", 0)
            comentario = cat_data.get("comentario", "")
            if not fotos and monto == 0 and not comentario:
                continue
                
            rutas_fotos = []
            for i, foto_b64 in enumerate(fotos):
                nombre_archivo = f"{tienda}_{usuario}_{fecha}_{timestamp}_{i+1}.jpg"
                ruta_sharepoint = f"{SP_GASTOS_FOLDER}/{mes_folder}/{cat.upper()}/{nombre_archivo}"

                # Guardamos una ruta estable; nunca una URL temporal de Microsoft.
                if subir_foto_sharepoint(
                    foto_b64,
                    ruta_sharepoint,
                    auth_headers,
                    base_url=base_url,
                    site_id=site_id,
                ):
                    rutas_fotos.append(ruta_sharepoint)
                    print(f"[GASTOS] Subida a SharePoint: {ruta_sharepoint}")
                    
            filas_gastos.append([
                fecha_reg.strftime("%Y-%m-%d %H:%M"),
                tienda.replace("_", " "),
                _fmt_fecha_excel(pendiente.get("fecha", "")),
                usuario,
                cat.upper(),
                monto,
                ",".join(rutas_fotos),
                "",
                comentario
            ])
            
        if filas_gastos:
            escribir_gasto_en_excel(filas_gastos)

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


@app.route("/api/foto")
def api_foto():
    """
    Descarga la imagen desde SharePoint (server-side) y la devuelve al browser.
    Evita problemas de CORS/expiración con las URLs pre-autenticadas de Microsoft Graph.
    """
    ruta = request.args.get("path")
    if not ruta:
        return "Ruta no proporcionada", 400

    try:
        wants_thumb = request.args.get("thumb") == "1"
        legacy_path = _legacy_object_path(ruta) if ruta.startswith(("http://", "https://")) else None
        if legacy_path and legacy_path.startswith(f"{SP_GASTOS_FOLDER}/"):
            stable_path = legacy_path
        elif legacy_path:
            stable_path = f"{SP_GASTOS_FOLDER}/{legacy_path}"
        else:
            stable_path = ruta.lstrip("/")
        cache_key = f"{'thumb' if wants_thumb else 'full'}:{stable_path}"
        cached_bytes = _photo_cache_get(cache_key)
        if cached_bytes:
            content, content_type = cached_bytes
            resp = make_response(content)
            resp.headers["Content-Type"] = content_type
            resp.headers["Cache-Control"] = "public, max-age=86400, stale-while-revalidate=604800"
            return resp

        token = _get_sp_token()
        if not token:
            return "No autorizado", 401
        auth_headers = {"Authorization": f"Bearer {token}"}
        site_id   = _get_site_id(auth_headers)
        candidates = [_thumb_path(stable_path), stable_path] if wants_thumb else [stable_path]
        img = None
        downloaded_from_original = False
        last_metadata_response = None
        for candidate in candidates:
            img, last_metadata_response = _download_sharepoint_photo(
                site_id, auth_headers, candidate
            )
            if img is not None and img.ok:
                downloaded_from_original = wants_thumb and candidate == stable_path
                break
            status = last_metadata_response.status_code if last_metadata_response is not None else "NA"
            if status != 404:
                print(f"[FOTO] Metadata/download error {status}: {candidate}")

        if img is None or not img.ok:
            # Algunas fotos historicas todavia conservan la URL publica de
            # Supabase y no alcanzaron a copiarse a SharePoint. Se recuperan
            # desde esa URL sin modificar el registro guardado.
            legacy_photo = _download_legacy_photo(ruta) if legacy_path else None
            if not legacy_photo:
                return "Imagen no encontrada en SharePoint", 404
            content, content_type = legacy_photo
            if wants_thumb:
                content = _thumbnail_bytes(content)
                content_type = "image/jpeg"
            _photo_cache_put(cache_key, content, content_type)
            resp = make_response(content)
            resp.headers["Content-Type"] = content_type
            resp.headers["Cache-Control"] = "public, max-age=86400, stale-while-revalidate=604800"
            resp.headers["X-Content-Type-Options"] = "nosniff"
            return resp

        content = img.content
        if downloaded_from_original:
            content = _thumbnail_bytes(content)
        content_type = "image/jpeg" if downloaded_from_original else img.headers.get("Content-Type", "image/jpeg")
        _photo_cache_put(cache_key, content, content_type)
        resp = make_response(content)
        resp.headers["Content-Type"]  = content_type
        resp.headers["Cache-Control"] = "public, max-age=86400, stale-while-revalidate=604800"
        resp.headers["X-Content-Type-Options"] = "nosniff"
        return resp

    except Exception as e:
        print(f"[FOTO] Excepcion: {e}")
        return str(e), 500


@app.route("/reporte")
def reporte():
    """Muestra el reporte de gastos leyendo la hoja Gastos."""
    try:
        token = _get_sp_token()
        gastos = []
        if token:
            auth_headers = {"Authorization": f"Bearer {token}"}
            site_id = _get_site_id(auth_headers)
            base_url = _get_base_url(site_id)
            
            used_url = f"{base_url}/workbook/worksheets/{SP_SHEET_GASTOS}/usedRange"
            r = req_lib.get(used_url, headers=auth_headers, timeout=30)
            if r.ok:
                values = r.json().get("values", [])
                if len(values) > 1:
                    # El índice de valores asume:
                    # 0: Fecha reg, 1: Tienda, 2: Fecha gasto, 3: Usuario, 4: Categoria, 5: Monto, 6: Fotos
                    grouped = {}
                    for idx, row in enumerate(values[1:]):
                        if len(row) >= 6:
                            row_num = idx + 2
                            tienda = row[1]
                            
                            fecha_reg_raw = row[0]
                            fecha_reg_date = None
                            try:
                                from datetime import datetime, timedelta
                                fecha_reg_num = float(str(fecha_reg_raw))
                                fecha_reg_date = datetime(1899, 12, 30) + timedelta(days=fecha_reg_num)
                                fecha_reg_str = fecha_reg_date.strftime("%d/%m/%Y %H:%M")
                            except (ValueError, TypeError):
                                fecha_reg_str = str(fecha_reg_raw)
                                try:
                                    from datetime import datetime
                                    fecha_reg_date = datetime.strptime(fecha_reg_str, "%d/%m/%Y %H:%M")
                                except Exception:
                                    pass
                            # Excel puede devolver la fecha como número serial (ej: 46088)
                            fecha_raw = row[2]
                            try:
                                fecha_num = float(str(fecha_raw))
                                # Convertir número serial de Excel a fecha real
                                from datetime import date, timedelta
                                excel_epoch = date(1899, 12, 30)
                                fecha_date = excel_epoch + timedelta(days=int(fecha_num))
                                
                                # Fix for swapped days and months in old records
                                is_old_record = False
                                if fecha_reg_date:
                                    if fecha_reg_date < datetime(2026, 8, 12):
                                        is_old_record = True
                                    elif fecha_reg_date.day <= 12:
                                        try:
                                            swapped_reg = datetime(fecha_reg_date.year, fecha_reg_date.day, fecha_reg_date.month)
                                            if swapped_reg < datetime(2026, 8, 12):
                                                is_old_record = True
                                        except ValueError:
                                            pass
                                            
                                if is_old_record:
                                    if fecha_date.day <= 12 and fecha_date.month != fecha_date.day:
                                        from datetime import date as dt_date
                                        try:
                                            fecha_date = dt_date(fecha_date.year, fecha_date.day, fecha_date.month)
                                        except ValueError:
                                            pass
                                            
                                fecha = fecha_date.strftime("%d/%m/%Y")
                            except (ValueError, TypeError):
                                fecha = str(fecha_raw)
                            usuario = row[3]
                            categoria = row[4]
                            
                            try:
                                monto = float(str(row[5]).replace('$', '').replace(',', '').strip()) if row[5] else 0.0
                            except ValueError:
                                monto = 0.0
                                
                            try:
                                viaticos_val = float(str(row[7]).replace('$', '').replace(',', '').strip()) if len(row) > 7 and row[7] else None
                            except ValueError:
                                viaticos_val = None
                                
                            comentario_str = str(row[8]).strip() if len(row) > 8 and row[8] else ""
                            
                            fotos_str = row[6] if len(row) > 6 and row[6] else ""
                            fotos_list = [f.strip() for f in fotos_str.split(",") if f.strip()]
                            
                            key = (tienda, fecha, usuario)
                            
                            if key not in grouped:
                                grouped[key] = {
                                    "fecha_reg": fecha_reg_str,
                                    "tienda": tienda,
                                    "fecha": fecha,
                                    "usuario": usuario,
                                    "categoria": [categoria] if categoria else [],
                                    "monto": monto,
                                    "fotos": list(fotos_list),
                                    "viaticos": viaticos_val,
                                    "comentarios": [comentario_str] if comentario_str else [],
                                    "detalles": {},
                                    "row_nums": [row_num]
                                }
                                if categoria:
                                    grouped[key]["detalles"][categoria] = {
                                        "monto": monto, 
                                        "fotos": list(fotos_list), 
                                        "comentarios": [comentario_str] if comentario_str else [],
                                        "row_nums": [row_num]
                                    }
                            else:
                                grouped[key]["monto"] += monto
                                grouped[key]["fotos"].extend(fotos_list)
                                grouped[key]["row_nums"].append(row_num)
                                if comentario_str:
                                    grouped[key]["comentarios"].append(comentario_str)
                                if viaticos_val is not None:
                                    grouped[key]["viaticos"] = viaticos_val
                                if categoria and categoria not in grouped[key]["categoria"]:
                                    grouped[key]["categoria"].append(categoria)
                                
                                if categoria:
                                    if categoria not in grouped[key]["detalles"]:
                                        grouped[key]["detalles"][categoria] = {"monto": 0.0, "fotos": [], "comentarios": [], "row_nums": []}
                                    grouped[key]["detalles"][categoria]["monto"] += monto
                                    grouped[key]["detalles"][categoria]["fotos"].extend(fotos_list)
                                    grouped[key]["detalles"][categoria]["row_nums"].append(row_num)
                                    if comentario_str:
                                        grouped[key]["detalles"][categoria]["comentarios"].append(comentario_str)

                                grouped[key]["fecha_reg"] = fecha_reg_str # Mostrar última fecha de actualización
                                
                    gastos = list(grouped.values())
                    gastos.reverse() # Mostrar los grupos más recientes primero
                            
        resp = make_response(render_template("reporte.html", gastos=gastos, tiendas=TIENDAS))
        resp.headers['Cache-Control'] = 'no-cache'
        return resp
    except Exception as e:
        return f"<h2>Error cargando reporte:</h2><pre>{e}</pre>"


@app.route("/api/editar_gasto", methods=["POST"])
def api_editar_gasto():
    """Actualiza Monto por categoría y Viáticos globales de un grupo de gastos."""
    data = request.json
    pwd = data.get("password")
    if pwd != "cfbc2026":
        return jsonify({"ok": False, "msg": "Contraseña incorrecta."}), 403
        
    categorias = data.get("categorias", {})
    nuevo_viatico = data.get("viaticos", 0)
    
    if not categorias:
        return jsonify({"ok": False, "msg": "No hay datos para editar."}), 400
        
    try:
        token = _get_sp_token()
        if not token:
            return jsonify({"ok": False, "msg": "Error de token SP."}), 500
            
        auth_headers = {"Authorization": f"Bearer {token}"}
        site_id = _get_site_id(auth_headers)
        base_url = _get_base_url(site_id)
        
        # Encontrar la primera fila global para guardar los viáticos
        todas_filas = []
        for cat_data in categorias.values():
            todas_filas.extend(cat_data.get("row_nums", []))
            
        if not todas_filas:
            return jsonify({"ok": False, "msg": "No hay filas para editar."}), 400
            
        primera_fila = min(todas_filas)
        
        # Actualizar viáticos (Columna H) solo si viene en el payload
        if "viaticos" in data:
            nuevo_viatico = data["viaticos"]
            resp_v = req_lib.patch(
                f"{base_url}/workbook/worksheets/{SP_SHEET_GASTOS}/range(address='H{primera_fila}')",
                headers={**auth_headers, "Content-Type": "application/json"},
                json={"values": [[nuevo_viatico]]}, timeout=30
            )
            if not resp_v.ok:
                return jsonify({"ok": False, "msg": f"Error editando viáticos: {resp_v.text}"}), 500
        
        # Actualizar los montos por categoría
        for cat, cat_data in categorias.items():
            cat_monto = cat_data.get("monto", 0)
            cat_rows = cat_data.get("row_nums", [])
            
            if not cat_rows: continue
            cat_rows.sort()
            r1 = cat_rows[0]
            
            # Actualizar monto en F de la primera fila de la categoría
            resp_m = req_lib.patch(
                f"{base_url}/workbook/worksheets/{SP_SHEET_GASTOS}/range(address='F{r1}')",
                headers={**auth_headers, "Content-Type": "application/json"},
                json={"values": [[cat_monto]]}, timeout=30
            )
            if not resp_m.ok:
                return jsonify({"ok": False, "msg": f"Error editando monto de {cat}: {resp_m.text}"}), 500
            
            # Poner en 0 las demás filas de esta categoría
            for rn in cat_rows[1:]:
                req_lib.patch(
                    f"{base_url}/workbook/worksheets/{SP_SHEET_GASTOS}/range(address='F{rn}')",
                    headers={**auth_headers, "Content-Type": "application/json"},
                    json={"values": [[0]]}, timeout=30
                )
                
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500

@app.route("/api/eliminar_foto", methods=["POST"])
def api_eliminar_foto():
    """Elimina una foto específica de la base de datos (Excel)."""
    data = request.json
    pwd = data.get("password")
    if pwd != "cfbc2026":
        return jsonify({"ok": False, "msg": "Contraseña incorrecta."}), 403
        
    foto_path = data.get("foto_path")
    if not foto_path:
        return jsonify({"ok": False, "msg": "No se proporcionó la ruta de la foto."}), 400
        
    try:
        token = _get_sp_token()
        if not token:
            return jsonify({"ok": False, "msg": "Error de token SP."}), 500
            
        auth_headers = {"Authorization": f"Bearer {token}"}
        site_id = _get_site_id(auth_headers)
        base_url = _get_base_url(site_id)
        
        # Obtener todas las filas para buscar la foto
        used_url = f"{base_url}/workbook/worksheets/{SP_SHEET_GASTOS}/usedRange"
        r = req_lib.get(used_url, headers=auth_headers, timeout=30)
        if not r.ok:
            return jsonify({"ok": False, "msg": "Error obteniendo datos."}), 500
            
        values = r.json().get("values", [])
        for idx, row in enumerate(values):
            if len(row) > 6 and row[6]:
                fotos = [f.strip() for f in str(row[6]).split(",")]
                if foto_path in fotos:
                    fotos.remove(foto_path)
                    new_fotos_str = ",".join(fotos)
                    row_num = idx + 1
                    
                    # Actualizar celda G{row_num}
                    resp_p = req_lib.patch(
                        f"{base_url}/workbook/worksheets/{SP_SHEET_GASTOS}/range(address='G{row_num}')",
                        headers={**auth_headers, "Content-Type": "application/json"},
                        json={"values": [[new_fotos_str]]}, timeout=30
                    )
                    if resp_p.ok:
                        return jsonify({"ok": True, "msg": "Foto eliminada correctamente."})
                    else:
                        return jsonify({"ok": False, "msg": f"Error al actualizar celda: {resp_p.text}"}), 500
                        
        return jsonify({"ok": False, "msg": "Foto no encontrada en los registros."}), 404
        
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500

@app.route("/api/analizar_factura", methods=["POST"])
def api_analizar_factura():
    try:
        folio_manual = request.form.get('folio_manual', '').strip()
        if not folio_manual:
            return jsonify({"ok": False, "error": "Folio es requerido"}), 400

        print(f"Bypassing OCR. Folio manual: {folio_manual}", flush=True)
        
        folio_encontrado = folio_manual
        fecha_detectada = "N/A"
        total_detectado = "N/A"
        serie = "N/A"
        productos_gemini = [] 
        full_text = "OCR Bypass. Manual Folio."

        db_productos = []
        db_status = "NOT_FOUND"
        
        # Buscar en Neon usando el folio detectado (o manual)
        db_res = database_client.table("facturas_folios").select("*").eq("folio", folio_encontrado).execute()
        db_productos = db_res.data
        if db_productos:
            db_status = "FOUND"
            
        comparacion = []
        if db_status == "FOUND":
            first_row = db_productos[0]
            fecha_detectada = str(first_row.get("diario", "N/A"))
            serie = str(first_row.get("salida", "N/A"))
            
            total_sum = 0.0
            for db_p in db_productos:
                prod_name = str(db_p.get("producto", "")).strip()
                cant_db = float(db_p.get("unidades", 0))
                precio_db = float(db_p.get("precio_unidad", 0))
                venta_total = float(db_p.get("venta_total", 0))
                total_sum += venta_total
                
                comparacion.append({
                    "producto_db": prod_name,
                    "cantidad_db": cant_db,
                    "precio_db": precio_db,
                    "estado": "OK" # Asumimos OK porque no hay validación OCR
                })
            
            total_detectado = f"${total_sum:,.2f}"
                    
        url_factura_temp = ""
            
        return jsonify({
              "ok": True,
              "factura": {
                  "serie": serie,
                  "folio": folio_encontrado,
                  "fecha": fecha_detectada,
                  "total": total_detectado,
                  "url_factura": url_factura_temp
              },
              "db_status": db_status,
              "comparacion": comparacion,
              "productos_gemini": productos_gemini,
              "ocr_raw_text": full_text
          })
        
    except Exception as e:
        print(f"Error procesando factura manual: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route('/api/analizar_recibo', methods=['POST'])
def analizar_recibo():
    if 'imagen' not in request.files:
        return jsonify({"ok": False, "error": "No image provided"}), 400
        
    file = request.files['imagen']
    esperados_json = request.form.get('esperados', '[]')
    
    try:
        import json
        esperados = json.loads(esperados_json)
    except Exception as e:
        esperados = []

    try:
        # Ya no usamos OCR, así que si llegamos aquí sin folio manual, es un error
        if not folio_manual:
            return jsonify({"ok": False, "error": "El folio manual es requerido ahora que el OCR está desactivado."}), 400
        
        full_text = "OCR desactivado."
                
        # Heurística para Walmart Recibo
        import unicodedata
        import re
        def remove_accents(input_str):
            return unicodedata.normalize('NFKD', input_str).encode('ASCII', 'ignore').decode('utf-8')
            
        ocr_clean = remove_accents(full_text.lower())
        
        # Subir foto a SharePoint si tenemos folio
        folio = request.form.get("folio")
        if folio:
            import base64, time
            try:
                b64_str = base64.b64encode(img_bytes).decode('utf-8')
                ruta_sharepoint = f"Acuses/acuse_{folio}_{int(time.time())}.jpg"
                url_publica = subir_foto_sharepoint_auto(b64_str, ruta_sharepoint)
                if url_publica:
                      update_data = {"url_acuse": url_publica}
                      url_factura = request.form.get("url_factura")
                      if url_factura:
                          update_data["url_factura"] = url_factura
                      database_client.table("facturas_folios").update(update_data).eq("folio", folio).execute()
            except Exception as ex:
                print(f"Error subiendo foto acuse: {ex}")

        conciliacion = []
        for prod in esperados:
            prod_name = prod.get("producto", "")
            cant_esperada = float(prod.get("cantidad", 0))
            
            # Buscar el nombre del producto en el OCR
            prod_clean = remove_accents(prod_name.lower())
            words = [w for w in prod_clean.split() if len(w) > 3]
            
            matched_words = [w for w in words if w in ocr_clean]
            is_match = False
            if len(words) > 0 and (len(matched_words) / len(words)) >= 0.5:
                is_match = True
                
            cant_recibida = 0
            if is_match:
                idx = ocr_clean.find(matched_words[0]) if matched_words else -1
                if idx != -1:
                    texto_antes = ocr_clean[max(0, idx - 150):idx]
                    
                    # En Walmart, la cantidad suele venir antes del nombre. 
                    # Usamos .0\d\d para evitar atrapar precios como 1.454.00
                    matches = re.findall(r'\b([1-9]\d*)\.0\d{2}\b', texto_antes)
                    if matches:
                        val = float(matches[-1])
                        # Mitigar error de OCR que lee '10' como '18'
                        if val == 18 and cant_esperada == 10:
                            cant_recibida = 10.0
                        else:
                            cant_recibida = val
                    else:
                        cant_recibida = cant_esperada
            
            conciliacion.append({
                "producto": prod_name,
                "esperado": cant_esperada,
                "recibido": cant_recibida,
                "diferencia": cant_recibida - cant_esperada,
                "estado": "OK" if cant_recibida == cant_esperada else "DIFF"
            })
            
        return jsonify({
            "ok": True,
            "conciliacion": conciliacion,
            "ocr_raw": full_text
        })
        
    except Exception as e:
        print(f"Error procesando recibo: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route('/api/actualizar_recibo', methods=['POST'])
def actualizar_recibo():
    try:
        folio = request.form.get('folio')
        serie = request.form.get('serie', '')
        # Ya no recibimos url_factura como string desde el form
        productos_str = request.form.get('productos', '[]')
        
        import json
        try:
            productos = json.loads(productos_str)
        except:
            productos = []
            
        if not folio or not productos:
            return jsonify({"ok": False, "error": "Faltan datos de folio o productos."}), 400
            
        import base64, time
        
        # Subir foto acuse si existe
        url_acuse = None
        if 'imagen_acuse' in request.files:
            file_acuse = request.files['imagen_acuse']
            if file_acuse.filename != '':
                file_bytes_acuse = file_acuse.read()
                b64_str_acuse = base64.b64encode(file_bytes_acuse).decode('utf-8')
                ruta_supa_acuse = f"Acuses/acuse_{folio}_{int(time.time())}.jpg"
                url_acuse = subir_foto_sharepoint_auto(b64_str_acuse, ruta_supa_acuse)

        # Subir foto factura si existe
        url_factura_form = None
        if 'imagen_factura' in request.files:
            file_fact = request.files['imagen_factura']
            if file_fact.filename != '':
                file_bytes_fact = file_fact.read()
                b64_str_fact = base64.b64encode(file_bytes_fact).decode('utf-8')
                ruta_supa_fact = f"Facturas/factura_{folio}_{int(time.time())}.jpg"
                url_factura_form = subir_foto_sharepoint_auto(b64_str_fact, ruta_supa_fact)

        for p in productos:
            producto_nombre = p.get('producto')
            nueva_cantidad = p.get('nueva_cantidad')
            esperado = p.get('esperado', nueva_cantidad)
            precio = p.get('precio', 0)
            razon_devolucion = p.get('razon_devolucion', '')
            
            if producto_nombre and nueva_cantidad is not None:
                nueva_venta = float(nueva_cantidad) * float(precio)
                update_data = {'unidades': nueva_cantidad, 'venta_total': nueva_venta}
                if url_acuse:
                    update_data['url_acuse'] = url_acuse
                if url_factura_form:
                    update_data['url_factura'] = url_factura_form
                # Update the database
                database_client.table('facturas_folios').update(update_data).eq('folio', folio).eq('producto', producto_nombre).execute()
                
                # Guardar devolucion si hay discrepancia
                try:
                    cant_esp = float(esperado)
                    cant_recib = float(nueva_cantidad)
                    if cant_esp > cant_recib:
                        cantidad_devuelta = cant_esp - cant_recib
                        total_devolucion = cantidad_devuelta * float(precio)
                        database_client.table('devoluciones').insert({
                            'folio': folio,
                            'serie': serie,
                            'producto': producto_nombre,
                            'cantidad_devuelta': cantidad_devuelta,
                            'precio_unidad': float(precio),
                            'total_devolucion': total_devolucion,
                            'razon_devolucion': razon_devolucion
                        }).execute()
                except Exception as ex_dev:
                    print(f"Error al guardar devolucion: {ex_dev}")
                
                
        return jsonify({"ok": True})
    except Exception as e:
        print(f"Error actualizando recibo: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/sin_acuse", methods=["POST"])
def sin_acuse():
    data = request.json
    folio = data.get("folio")
    razon = data.get("razon")
    url_factura = data.get("url_factura")
    
    if not folio or not razon:
        return jsonify({"success": False, "error": "Folio y razón requeridos"}), 400
        
    try:
        # Actualizar la base de datos
        update_data = {"razon_sin_acuse": razon}
        if url_factura:
            update_data["url_factura"] = url_factura
        database_client.table("facturas_folios").update(update_data).eq("folio", folio).execute()
        return jsonify({"success": True})
    except Exception as e:
        print(f"[ERROR] Al reportar sin acuse: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/cancelar_factura", methods=["POST"])
def cancelar_factura():
    data = request.json
    folio = data.get("folio")
    serie = data.get("serie", "")
    if not folio:
        return jsonify({"success": False, "error": "Folio requerido"}), 400
        
    try:
        # Obtener los datos actuales de la factura
        res = database_client.table("facturas_folios").select("*").eq("folio", folio).execute()
        if not res.data:
            return jsonify({"success": False, "error": "Factura no encontrada en base de datos"}), 404
            
        registros_a_mover = res.data
        
        # Eliminar el id para evitar conflictos de llave primaria si es identity
        for reg in registros_a_mover:
            if "id" in reg:
                del reg["id"]
                
        # Insertar en facturas_canceladas
        database_client.table("facturas_canceladas").insert(registros_a_mover).execute()
        
        # Insertar en devoluciones automáticamente
        devoluciones_a_insertar = []
        for reg in registros_a_mover:
            cant = float(reg.get("unidades", 0))
            precio = float(reg.get("precio_unidad", 0))
            if cant > 0:
                devoluciones_a_insertar.append({
                    "folio": folio,
                    "serie": serie,
                    "producto": reg.get("producto", ""),
                    "cantidad_devuelta": cant,
                    "precio_unidad": precio,
                    "total_devolucion": cant * precio,
                    "razon_devolucion": "Cancelada automáticamente"
                })
        
        if devoluciones_a_insertar:
            database_client.table("devoluciones").insert(devoluciones_a_insertar).execute()
        
        # Eliminar de facturas_folios
        database_client.table("facturas_folios").delete().eq("folio", folio).execute()
        
        return jsonify({"success": True})
    except Exception as e:
        print(f"[ERROR] Al cancelar factura: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
