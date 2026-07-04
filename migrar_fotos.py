import os
import time
import requests as req_lib
from app import (
    _get_sp_token, _get_site_id, _get_base_url, supabase_client,
    SP_SHEET_GASTOS
) # Wait, app might not have auth_headers globally exported in a way that doesn't cause issues.

def migrar_fotos():
    print("Iniciando migracion de fotos...")
    
    token = _get_sp_token()
    if not token:
        print("Error: No se pudo obtener el token de SharePoint.")
        return
        
    auth_headers = {"Authorization": f"Bearer {token}"}
    try:
        site_id = _get_site_id(auth_headers)
        base_url = _get_base_url(site_id)
    except Exception as e:
        print(f"Error obteniendo site_id o base_url: {e}")
        return

    # Obtener todas las filas de REPORTE-GASTOSAPP
    used_url = f"{base_url}/workbook/worksheets/{SP_SHEET_GASTOS}/usedRange"
    r = req_lib.get(used_url, headers=auth_headers, timeout=30)
    if not r.ok:
        print(f"Error obteniendo datos del excel: {r.text}")
        return
        
    values = r.json().get("values", [])
    if len(values) <= 1:
        print("No hay datos suficientes para migrar.")
        return
        
    filas_modificadas = 0
    fotos_migradas = 0
    
    for idx, row in enumerate(values[1:]): # Saltar el encabezado
        row_num = idx + 2
        # Asumiendo: 0: Fecha reg, 1: Tienda, 2: Fecha gasto, 3: Usuario, 4: Categoria, 5: Monto, 6: Fotos
        if len(row) > 6 and row[6]:
            fotos_string = str(row[6])
            fotos_paths = [f.strip() for f in fotos_string.split(",") if f.strip()]
            
            needs_update = False
            new_paths = []
            
            for path in fotos_paths:
                if path.startswith("http"):
                    # Ya es una URL completa (migrada o subida directo a Supabase)
                    new_paths.append(path)
                else:
                    print(f"Migrando foto: {path}")
                    # Descargar de SharePoint
                    ruta_limpia = path.lstrip("/")
                    meta_url  = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/root:/{ruta_limpia}"
                    
                    r_meta = None
                    for attempt in range(3):
                        r_meta = req_lib.get(meta_url, headers=auth_headers, timeout=15)
                        if r_meta.ok: break
                        if r_meta.status_code in (429, 503) and attempt < 2:
                            time.sleep(1.5)
                            
                    if not r_meta or not r_meta.ok:
                        print(f"  Error obteniendo metadata de {path}: {r_meta.status_code if r_meta else 'NA'}")
                        new_paths.append(path) # Mantener original si falla
                        continue
                        
                    download_url = r_meta.json().get("@microsoft.graph.downloadUrl")
                    if not download_url:
                        print(f"  No se encontro download_url para {path}")
                        new_paths.append(path)
                        continue
                        
                    img_resp = None
                    for attempt in range(3):
                        img_resp = req_lib.get(download_url, timeout=30)
                        if img_resp.ok: break
                        if attempt < 2: time.sleep(1.5)
                        
                    if not img_resp or not img_resp.ok:
                        print(f"  Error descargando la imagen {path}")
                        new_paths.append(path)
                        continue
                        
                    img_bytes = img_resp.content
                    
                    # Subir a Supabase
                    ruta_supa = path # Use the same path structure
                    try:
                        supabase_client.storage.from_("gastos-fotos").upload(
                            ruta_supa, 
                            img_bytes, 
                            file_options={"content-type": "image/jpeg", "upsert": "true"}
                        )
                        public_url = supabase_client.storage.from_("gastos-fotos").get_public_url(ruta_supa)
                        new_paths.append(public_url)
                        fotos_migradas += 1
                        needs_update = True
                        print(f"  -> Migrada con exito a: {public_url}")
                    except Exception as e:
                        print(f"  Error subiendo a Supabase: {e}")
                        new_paths.append(path) # Revert to original path on failure
            
            if needs_update:
                new_fotos_str = ",".join(new_paths)
                # Actualizar celda G{row_num}
                try:
                    patch_resp = req_lib.patch(
                        f"{base_url}/workbook/worksheets/{SP_SHEET_GASTOS}/range(address='G{row_num}')",
                        headers={**auth_headers, "Content-Type": "application/json"},
                        json={"values": [[new_fotos_str]]}, timeout=30
                    )
                    if patch_resp.ok:
                        print(f"Fila {row_num} actualizada exitosamente.")
                        filas_modificadas += 1
                    else:
                        print(f"Error actualizando fila {row_num}: {patch_resp.text}")
                except Exception as e:
                    print(f"Excepcion actualizando fila {row_num}: {e}")
                    
    print("\nResumen de Migracion:")
    print(f"Fotos migradas: {fotos_migradas}")
    print(f"Filas de Excel modificadas: {filas_modificadas}")
    print("Migracion completada.")

if __name__ == "__main__":
    migrar_fotos()
