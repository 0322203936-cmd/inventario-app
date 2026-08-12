import os
import pandas as pd
import datetime

# Importamos el cliente de tu nuevo archivo neon_db.py
from neon_db import database_client

# 1. Obtener la última fecha registrada en Neon
print("Consultando la última fecha registrada en Neon...")
try:
    # Traemos el registro más reciente ordenado por 'diario' de forma descendente
    response = database_client.table('facturas_folios').select('diario').order('diario', desc=True).limit(1).execute()
    if response.data and response.data[0]['diario']:
        last_date_str = response.data[0]['diario']
        # Nos aseguramos de convertirlo a objeto date para compararlo fácilmente
        if isinstance(last_date_str, str):
            # Si viene con hora extraída (ej. 2026-07-20T00:00:00), tomamos solo la fecha
            last_date_str = last_date_str.split('T')[0]
            last_date = datetime.datetime.strptime(last_date_str, '%Y-%m-%d').date()
        else:
            # Si ya es un objeto datetime o date
            last_date = getattr(last_date_str, 'date', lambda: last_date_str)()
        print(f"Último registro en Neon es del: {last_date}")
    else:
        last_date = None
        print("La base de datos está vacía o no tiene fechas válidas. Se subirá todo.")
except Exception as e:
    print(f"Error consultando la base de datos: {e}")
    exit(1)

print("Leyendo archivo de Excel 'Analisis CFBC MAYO-JUNIO.xlsx'...")
try:
    df = pd.read_excel('Analisis CFBC MAYO-JUNIO.xlsx')
except Exception as e:
    print(f"Error leyendo excel: {e}")
    exit(1)

df = df.fillna("")

records_to_insert = []
ignorados_por_fecha = 0

for index, row in df.iterrows():
    diario_val = row.get('Diario', '')
    
    # Procesar la fecha de la fila
    if isinstance(diario_val, datetime.datetime):
        fila_date = diario_val.date()
        diario_str = diario_val.strftime('%Y-%m-%d')
    elif str(diario_val).strip() == "":
        fila_date = None
        diario_str = None
    else:
        try:
            dt = pd.to_datetime(diario_val)
            fila_date = dt.date()
            diario_str = dt.strftime('%Y-%m-%d')
        except:
            fila_date = None
            diario_str = None

    # 2. Filtrar por fecha: Solo agregar si la fecha de la fila es MAYOR a la última registrada
    if last_date and fila_date:
        if fila_date <= last_date:
            ignorados_por_fecha += 1
            continue  # Saltamos esta fila porque es igual o anterior a la última fecha

    def clean_num(val):
        try:
            v = float(val)
            return v if pd.notna(v) else 0.0
        except:
            return 0.0

    record = {
        "diario": diario_str,
        "ruta": str(row.get('Ruta', '')),
        "viajes_por_ruta": str(row.get('Viajes Por Ruta', '')),
        "prueba": str(row.get('Prueba', '')),
        "sem": str(row.get('SEM', '')),
        "tienda": str(row.get('Nombre Tienda/Club', '')),
        "salida": str(row.get('Salida', '')),
        "folio": str(row.get('Folio contpaq', '')),
        "producto": str(row.get('Producto', '')),
        "unidades": clean_num(row.get('Unidades', 0)),
        "precio_unidad": clean_num(row.get('Precio Unidad', 0)),
        "venta_total": clean_num(row.get('Venta Total', 0))
    }
    records_to_insert.append(record)

print(f"Filas ignoradas por ser fechas pasadas o iguales a la última: {ignorados_por_fecha}")
print(f"Preparados {len(records_to_insert)} registros nuevos. Subiendo a Neon...")

if len(records_to_insert) == 0:
    print("No hay registros nuevos para subir. ¡Todo está al día!")
    exit(0)

BATCH_SIZE = 100
total_inserted = 0

for i in range(0, len(records_to_insert), BATCH_SIZE):
    batch = records_to_insert[i:i+BATCH_SIZE]
    try:
        response = database_client.table('facturas_folios').insert(batch).execute()
        total_inserted += len(batch)
        print(f"Progreso: {total_inserted}/{len(records_to_insert)}")
    except Exception as e:
        print(f"Error en el lote {i}-{i+BATCH_SIZE}: {e}")

print("¡Proceso de subida finalizado!")
