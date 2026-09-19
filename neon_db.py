import os
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


TABLE_COLUMNS = {
    "facturas_folios": {
        "id", "diario", "ruta", "viajes_por_ruta", "prueba", "sem", "tienda",
        "salida", "folio", "producto", "unidades", "precio_unidad", "venta_total",
        "created_at", "url_factura", "url_acuse", "razon_sin_acuse",
    },
    "facturas_canceladas": {
        "id", "diario", "ruta", "viajes_por_ruta", "prueba", "sem", "tienda",
        "salida", "folio", "producto", "unidades", "precio_unidad", "venta_total",
        "created_at", "fecha_cancelacion", "url_factura", "url_acuse", "razon_sin_acuse",
    },
    "devoluciones": {
        "id", "created_at", "folio", "serie", "producto", "cantidad_devuelta",
        "precio_unidad", "total_devolucion", "razon_devolucion",
        "verificado", "verificado_at", "modificada", "modificada_at", "modificacion_razon",
        "reemplazada", "reemplazada_at", "reemplazada_razon",
    },
}


def _central_database_url():
    path = Path.home() / "Desktop" / "migration-secrets.env"
    if not path.exists():
        return ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("TARGET_DATABASE_URL="):
            return line.split("=", 1)[1].strip()
    return ""


DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("TARGET_DATABASE_URL") or _central_database_url()
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL de Neon no esta configurada.")

_pool = None

def get_pool():
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            conninfo=DATABASE_URL,
            min_size=0,
            max_size=6,
            timeout=30,
            kwargs={"row_factory": dict_row},
            open=True,
        )
    return _pool


def _normalize(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _normalize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    return value


def _column(table, name):
    if name not in TABLE_COLUMNS[table]:
        raise ValueError(f"Columna no permitida: {name}")
    return name


class QueryBuilder:
    def __init__(self, table):
        if table not in TABLE_COLUMNS:
            raise ValueError("Tabla no permitida")
        self.table_name = table
        self.action = "select"
        self.selection = "*"
        self.payload = None
        self.filters = []
        self.ordering = None
        self.row_limit = None

    def select(self, columns="*"):
        self.action = "select"
        self.selection = columns
        return self

    def eq(self, column, value):
        self.filters.append((_column(self.table_name, column), value))
        return self

    def order(self, column, desc=False):
        self.ordering = (_column(self.table_name, column), bool(desc))
        return self

    def limit(self, count):
        self.row_limit = max(0, int(count))
        return self

    def insert(self, payload):
        self.action = "insert"
        self.payload = payload
        return self

    def update(self, payload):
        self.action = "update"
        self.payload = payload
        return self

    def delete(self):
        self.action = "delete"
        return self

    def _where(self, params):
        if not self.filters:
            return ""
        parts = []
        for column, value in self.filters:
            params.append(value)
            parts.append(f'"{column}" = %s')
        return " WHERE " + " AND ".join(parts)

    def execute(self):
        with get_pool().connection() as connection:
            with connection.cursor() as cursor:
                if self.action == "select":
                    if self.selection == "*":
                        selected = "*"
                    else:
                        names = [part.strip() for part in self.selection.split(",")]
                        selected = ",".join(f'"{_column(self.table_name, name)}"' for name in names)
                    params = []
                    sql = f'SELECT {selected} FROM "{self.table_name}"' + self._where(params)
                    if self.ordering:
                        column, desc = self.ordering
                        sql += f' ORDER BY "{column}" {"DESC" if desc else "ASC"}'
                    if self.row_limit is not None:
                        sql += f" LIMIT {self.row_limit}"
                    cursor.execute(sql, params)
                    rows = cursor.fetchall()
                elif self.action == "insert":
                    records = self.payload if isinstance(self.payload, list) else [self.payload]
                    rows = []
                    for record in records:
                        columns = list(record.keys())
                        for column in columns:
                            _column(self.table_name, column)
                        placeholders = ",".join(["%s"] * len(columns))
                        sql = (
                            f'INSERT INTO "{self.table_name}" '
                            f'({",".join(f"{chr(34)}{column}{chr(34)}" for column in columns)}) '
                            f"VALUES ({placeholders}) RETURNING *"
                        )
                        cursor.execute(sql, [record[column] for column in columns])
                        rows.append(cursor.fetchone())
                elif self.action == "update":
                    columns = list((self.payload or {}).keys())
                    for column in columns:
                        _column(self.table_name, column)
                    if not columns:
                        rows = []
                    else:
                        params = [self.payload[column] for column in columns]
                        assignments = ",".join(f'"{column}" = %s' for column in columns)
                        sql = f'UPDATE "{self.table_name}" SET {assignments}' + self._where(params) + " RETURNING *"
                        cursor.execute(sql, params)
                        rows = cursor.fetchall()
                elif self.action == "delete":
                    if not self.filters:
                        raise ValueError("Se requiere filtro para eliminar")
                    params = []
                    sql = f'DELETE FROM "{self.table_name}"' + self._where(params) + " RETURNING *"
                    cursor.execute(sql, params)
                    rows = cursor.fetchall()
                else:
                    raise ValueError("Operacion no permitida")
            connection.commit()
        return SimpleNamespace(data=_normalize(rows))


class NeonClient:
    def table(self, name):
        return QueryBuilder(name)

    def ping(self):
        with get_pool().connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                return cursor.fetchone() is not None


database_client = NeonClient()


def _ensure_capture_reset_schema(cursor):
    """Prepara los estados de reemplazo y el historial de evidencias.

    Se ejecuta dentro de la misma conexion que usa una captura/restablecimiento,
    por lo que una instalacion existente se actualiza sin requerir un script
    manual de migracion.
    """
    cursor.execute(
        """ALTER TABLE devoluciones
           ADD COLUMN IF NOT EXISTS verificado BOOLEAN NOT NULL DEFAULT FALSE,
           ADD COLUMN IF NOT EXISTS verificado_at TIMESTAMPTZ,
           ADD COLUMN IF NOT EXISTS modificada BOOLEAN NOT NULL DEFAULT FALSE,
           ADD COLUMN IF NOT EXISTS modificada_at TIMESTAMPTZ,
           ADD COLUMN IF NOT EXISTS modificacion_razon TEXT,
           ADD COLUMN IF NOT EXISTS reemplazada BOOLEAN NOT NULL DEFAULT FALSE,
           ADD COLUMN IF NOT EXISTS reemplazada_at TIMESTAMPTZ,
           ADD COLUMN IF NOT EXISTS reemplazada_razon TEXT"""
    )
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS facturas_capturas_historial (
             id BIGSERIAL PRIMARY KEY,
             folio TEXT NOT NULL,
             serie TEXT,
             url_factura TEXT,
             url_acuse TEXT,
             razon_sin_acuse TEXT,
             motivo TEXT,
             created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )"""
    )
    cursor.execute(
        "ALTER TABLE facturas_capturas_historial ADD COLUMN IF NOT EXISTS razon_sin_acuse TEXT"
    )


def get_invoice_capture_state(folio):
    """Devuelve el estado de capturas activas de un folio para la UI."""
    with get_pool().connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT id, url_factura, url_acuse, razon_sin_acuse
                     FROM facturas_folios
                    WHERE folio = %s
                    ORDER BY id""",
                [str(folio)],
            )
            invoice_rows = cursor.fetchall()
            _ensure_capture_reset_schema(cursor)
            cursor.execute(
                """SELECT id, producto, cantidad_devuelta, verificado,
                          COALESCE(modificada, FALSE) AS modificada,
                          COALESCE(reemplazada, FALSE) AS reemplazada
                     FROM devoluciones
                    WHERE folio = %s
                      AND COALESCE(reemplazada, FALSE) = FALSE
                    ORDER BY id""",
                [str(folio)],
            )
            rows = cursor.fetchall()
        connection.commit()

    has_evidence = any(
        row.get("url_factura") or row.get("url_acuse") or row.get("razon_sin_acuse")
        for row in invoice_rows
    )
    exists = bool(rows) or has_evidence
    return {
        "exists": exists,
        "can_reset": exists and not any(
            bool(row.get("verificado")) or bool(row.get("modificada")) for row in rows
        ),
        "has_verified": any(bool(row.get("verificado")) for row in rows),
        "has_modified": any(bool(row.get("modificada")) for row in rows),
        "has_evidence": has_evidence,
        "rows": _normalize(rows),
    }


def reset_invoice_capture(folio, reason="Captura reemplazada por nueva captura"):
    """Restablece una captura no verificada y conserva su evidencia.

    La operacion es transaccional: restaura unidades, archiva las devoluciones
    anteriores y limpia las URLs activas para que la nueva captura suba fotos
    nuevas. Las filas reemplazadas permanecen en Neon para auditoria.
    """
    folio = str(folio or "").strip()
    if not folio:
        raise ValueError("El folio es requerido.")

    with get_pool().connection() as connection:
        try:
            with connection.transaction():
                with connection.cursor() as cursor:
                    _ensure_capture_reset_schema(cursor)
                    cursor.execute(
                        """SELECT id, producto, unidades, precio_unidad,
                                  url_factura, url_acuse, razon_sin_acuse, salida
                             FROM facturas_folios
                            WHERE folio = %s
                            ORDER BY id
                            FOR UPDATE""",
                        [folio],
                    )
                    invoice_rows = cursor.fetchall()
                    if not invoice_rows:
                        raise ValueError("La factura no existe o ya fue cancelada.")

                    cursor.execute(
                        """SELECT id, producto, cantidad_devuelta, verificado,
                                  COALESCE(modificada, FALSE) AS modificada,
                                  COALESCE(reemplazada, FALSE) AS reemplazada
                             FROM devoluciones
                            WHERE folio = %s
                              AND COALESCE(reemplazada, FALSE) = FALSE
                            ORDER BY id
                            FOR UPDATE""",
                        [folio],
                    )
                    return_rows = cursor.fetchall()
                    has_evidence = any(
                        row.get("url_factura") or row.get("url_acuse") or row.get("razon_sin_acuse")
                        for row in invoice_rows
                    )
                    if not return_rows and not has_evidence:
                        raise ValueError("Esta factura no tiene una captura previa para restablecer.")
                    if any(bool(row.get("verificado")) for row in return_rows):
                        raise ValueError(
                            "La devolución ya fue verificada en Walmex. La corrección debe hacerse desde Walmex."
                        )
                    if any(bool(row.get("modificada")) for row in return_rows):
                        raise ValueError(
                            "La devolución ya fue modificada en Walmex. La captura no puede restablecerse desde Choferes."
                        )

                    # Conserva las evidencias actuales antes de limpiar las URLs activas.
                    first_with_url = next(
                        (row for row in invoice_rows if row.get("url_factura") or row.get("url_acuse")),
                        invoice_rows[0],
                    )
                    cursor.execute(
                        """INSERT INTO facturas_capturas_historial
                              (folio, serie, url_factura, url_acuse, razon_sin_acuse, motivo)
                           VALUES (%s, %s, %s, %s, %s, %s)""",
                        [
                            folio,
                            first_with_url.get("salida"),
                            first_with_url.get("url_factura"),
                            first_with_url.get("url_acuse"),
                            first_with_url.get("razon_sin_acuse"),
                            str(reason or "Captura reemplazada por nueva captura").strip(),
                        ],
                    )

                    restore_by_product = {}
                    for row in return_rows:
                        product = str(row.get("producto") or "").strip()
                        restore_by_product[product] = restore_by_product.get(product, 0) + float(
                            row.get("cantidad_devuelta") or 0
                        )

                    for row in invoice_rows:
                        product = str(row.get("producto") or "").strip()
                        current_units = float(row.get("unidades") or 0)
                        restored_units = current_units + restore_by_product.get(product, 0)
                        price = float(row.get("precio_unidad") or 0)
                        cursor.execute(
                            """UPDATE facturas_folios
                                  SET unidades = %s,
                                      venta_total = %s,
                                      url_factura = NULL,
                                      url_acuse = NULL,
                                      razon_sin_acuse = NULL
                                WHERE id = %s""",
                            [restored_units, restored_units * price, row.get("id")],
                        )

                    cursor.execute(
                        """UPDATE devoluciones
                              SET reemplazada = TRUE,
                                  reemplazada_at = NOW(),
                                  reemplazada_razon = %s
                            WHERE folio = %s
                              AND COALESCE(reemplazada, FALSE) = FALSE""",
                        [str(reason or "Captura reemplazada por nueva captura").strip(), folio],
                    )

            return {
                "folio": folio,
                "restored_products": len(invoice_rows),
                "replaced_returns": len(return_rows),
            }
        except Exception:
            connection.rollback()
            raise
