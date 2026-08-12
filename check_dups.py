from neon_db import database_client, get_pool

def check_duplicates():
    with get_pool().connection() as connection:
        with connection.cursor() as cursor:
            # Group by folio and producto, check if any have count > 1
            sql = """
            SELECT folio, producto, COUNT(*) as c 
            FROM facturas_folios 
            GROUP BY folio, producto 
            HAVING COUNT(*) > 1
            """
            cursor.execute(sql)
            duplicates = cursor.fetchall()
            
            if duplicates:
                print(f"SE ENCONTRARON {len(duplicates)} COMBINACIONES DE FOLIO/PRODUCTO DUPLICADAS!")
                total_dups = sum(row['c'] for row in duplicates)
                print(f"Total de registros involucrados en duplicados: {total_dups}")
            else:
                print("NO SE ENCONTRARON DUPLICADOS. Todo está limpio.")
                
            # Also just count total records to be sure
            cursor.execute("SELECT COUNT(*) as t FROM facturas_folios")
            total = cursor.fetchone()
            print(f"Total de registros en la tabla: {total['t']}")

check_duplicates()
