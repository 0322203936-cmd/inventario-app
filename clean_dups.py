from neon_db import get_pool

def clean_duplicates():
    with get_pool().connection() as connection:
        with connection.cursor() as cursor:
            # Check what 'id' looks like
            cursor.execute("SELECT id FROM facturas_folios LIMIT 1")
            row = cursor.fetchone()
            print(f"ID format: {row['id']}")
            
            # We can delete duplicates by keeping the max id (or min id)
            # CTID is a safe fallback in postgres if we don't want to rely on ID comparison
            sql = """
            DELETE FROM facturas_folios
            WHERE ctid NOT IN (
                SELECT min(ctid)
                FROM facturas_folios
                GROUP BY folio, producto, diario, ruta, tienda
            )
            """
            cursor.execute(sql)
            deleted = cursor.rowcount
            connection.commit()
            print(f"Se eliminaron {deleted} registros duplicados!")
            
            cursor.execute("SELECT COUNT(*) as t FROM facturas_folios")
            total = cursor.fetchone()
            print(f"Total de registros restantes: {total['t']}")

clean_duplicates()
