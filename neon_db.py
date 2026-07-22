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

_pool = ConnectionPool(
    conninfo=DATABASE_URL,
    min_size=0,
    max_size=6,
    timeout=30,
    kwargs={"row_factory": dict_row},
    open=True,
)


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
        with _pool.connection() as connection:
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
        with _pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                return cursor.fetchone() is not None


database_client = NeonClient()
