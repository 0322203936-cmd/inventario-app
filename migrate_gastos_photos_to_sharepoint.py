"""Copia fotos del respaldo local al almacenamiento compartido de SharePoint."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import threading

import requests

import app


SOURCE = Path(r"C:\Users\Yisus\Desktop\WALMEX-MIGRATION-BACKUP-20260722\storage-gastos-fotos")
PREFIX = app.SP_GASTOS_FOLDER
WORKERS = 4
_local = threading.local()


def _session():
    if not hasattr(_local, "session"):
        _local.session = requests.Session()
    return _local.session


def _exists(site_id, headers, target):
    url = (
        f"https://graph.microsoft.com/v1.0/sites/{site_id}"
        f"/drive/root:/{app._graph_path(target)}"
    )
    return _session().get(url, headers=headers, timeout=30).ok


def _upload(site_id, headers, target, content):
    url = (
        f"https://graph.microsoft.com/v1.0/sites/{site_id}"
        f"/drive/root:/{app._graph_path(target)}:/content"
    )
    response = _session().put(
        url,
        headers={**headers, "Content-Type": "image/jpeg"},
        data=content,
        timeout=120,
    )
    response.raise_for_status()


def _target_for(path):
    relative = path.relative_to(SOURCE).as_posix()
    if relative.startswith(f"{PREFIX}/"):
        return relative
    return f"{PREFIX}/{relative}"


def _copy_one(path, site_id, headers):
    target = _target_for(path)
    thumb_target = app._thumb_path(target)
    original_exists = _exists(site_id, headers, target)
    thumb_exists = _exists(site_id, headers, thumb_target)
    if original_exists and thumb_exists:
        return "skip", target

    content = path.read_bytes()
    if not original_exists:
        _upload(site_id, headers, target, content)
    if not thumb_exists:
        _upload(site_id, headers, thumb_target, app._thumbnail_bytes(content))
    return "copy", target


def main():
    files = []
    for path in SOURCE.rglob("*.jpg"):
        relative = path.relative_to(SOURCE).as_posix()
        files.append(path)

    token = app._get_sp_token()
    if not token:
        raise RuntimeError("No se pudo obtener token de Microsoft Graph")
    headers = {"Authorization": f"Bearer {token}"}
    site_id = app._get_site_id(headers)

    folders = sorted({_target_for(path).rsplit("/", 1)[0] for path in files})
    for folder in folders:
        app._ensure_sharepoint_folder(site_id, headers, folder)

    copied = skipped = failed = 0
    print(f"INICIO fotos={len(files)} carpetas={len(folders)}", flush=True)
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(_copy_one, path, site_id, headers): path for path in files}
        for index, future in enumerate(as_completed(futures), 1):
            try:
                status, target = future.result()
                if status == "copy":
                    copied += 1
                else:
                    skipped += 1
                print(f"[{index}/{len(files)}] {status.upper()} {target}", flush=True)
            except Exception as exc:
                failed += 1
                print(f"[{index}/{len(files)}] ERROR {futures[future]} :: {exc}", flush=True)

    print(f"FINAL copiados={copied} omitidos={skipped} errores={failed}", flush=True)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
