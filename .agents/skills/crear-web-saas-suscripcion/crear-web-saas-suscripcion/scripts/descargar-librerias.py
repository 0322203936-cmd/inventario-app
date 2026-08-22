#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
descargar-librerias.py — vendoriza las librerías pinneadas de la skill
crear-web-saas-suscripcion dentro del proyecto actual.

Uso (desde la RAÍZ del proyecto web):
    python scripts/descargar-librerias.py --list
    python scripts/descargar-librerias.py censurar-pdf
    python scripts/descargar-librerias.py facturas-excel apuntes-resumen

Versiones/URLs = reference/14-library-pinning.md (verificadas jul-2026).
Idempotente: los archivos ya presentes se saltan.

Nota: la detección de la IA corre en el SERVIDOR (Claude por defecto, Gemini de
respaldo). El navegador monta y exporta archivos, y en censurar-pdf hace además
el OCR de los escaneos en local con Tesseract.js (por eso ese arquetipo trae
varios archivos: el motor OCR completo, incluido el binario .wasm).
"""
import os
import sys
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

CDN = "https://cdn.jsdelivr.net/npm/"

FILES = {
    "pdf-lib":         (CDN + "pdf-lib@1.17.1/dist/pdf-lib.min.js",
                        "lib/vendor/pdf-lib.min.js"),
    "pdfjs":           (CDN + "pdfjs-dist@6.1.200/build/pdf.min.mjs",
                        "lib/vendor/pdfjs/pdf.min.mjs"),
    "pdfjs-worker":    (CDN + "pdfjs-dist@6.1.200/build/pdf.worker.min.mjs",
                        "lib/vendor/pdfjs/pdf.worker.min.mjs"),
    "jspdf":           (CDN + "jspdf@4.2.1/dist/jspdf.umd.min.js",
                        "lib/vendor/jspdf.umd.min.js"),
    "jspdf-autotable": (CDN + "jspdf-autotable@5/dist/jspdf.plugin.autotable.min.js",
                        "lib/vendor/jspdf.plugin.autotable.min.js"),
    # SheetJS ya NO se publica en npm: su CDN propio es la fuente oficial.
    "xlsx":            ("https://cdn.sheetjs.com/xlsx-0.20.3/package/dist/xlsx.full.min.js",
                        "lib/vendor/xlsx.full.min.js"),
    "jszip":           (CDN + "jszip@3.10.1/dist/jszip.min.js",
                        "lib/vendor/jszip.min.js"),
    # Tesseract.js — OCR local para escaneos (solo censurar-pdf).
    # El .wasm.js es el "glue" que descarga el binario .wasm: hacen falta AMBOS.
    "tesseract":       (CDN + "tesseract.js@5.1.1/dist/tesseract.min.js",
                        "lib/vendor/tesseract/tesseract.min.js"),
    "tesseract-worker": (CDN + "tesseract.js@5.1.1/dist/worker.min.js",
                        "lib/vendor/tesseract/worker.min.js"),
    "tesseract-core":  (CDN + "tesseract.js-core@5.1.1/tesseract-core-simd.wasm.js",
                        "lib/vendor/tesseract/tesseract-core-simd.wasm.js"),
    "tesseract-wasm":  (CDN + "tesseract.js-core@5.1.1/tesseract-core-simd.wasm",
                        "lib/vendor/tesseract/tesseract-core-simd.wasm"),
    "tesseract-spa":   (CDN + "@tesseract.js-data/spa@1.0.0/4.0.0_best_int/spa.traineddata.gz",
                        "lib/vendor/tesseract/lang/spa.traineddata.gz"),
}

ARCHETYPES = {
    # Patrón C — leer y localizar (OCR local en el navegador para escaneos)
    "censurar-pdf": ["pdfjs", "pdfjs-worker", "jspdf",
                     "tesseract", "tesseract-worker", "tesseract-core",
                     "tesseract-wasm", "tesseract-spa"],
    # Patrón A — leer y extraer
    "facturas-excel": ["xlsx", "jszip"],
    "apuntes-resumen": ["jspdf"],
    "traducir-documentos": ["pdf-lib", "pdfjs", "pdfjs-worker", "jspdf"],
    # Patrón B — leer y juzgar
    "analizar-contratos": ["jspdf"],
    "macros-foto": [],
    # Patrón D — ver y generar (todo servidor; el navegador solo descarga)
    "fotos-producto": ["jszip"],
    "foto-estilos": ["jszip"],
    "diseno-interiores": ["jszip"],
    "restaurar-fotos": ["jszip"],
    "mockups-producto": ["jszip"],
}


def human(n):
    for unit in ("B", "KB", "MB"):
        if n < 1024:
            return "%.0f %s" % (n, unit)
        n /= 1024.0
    return "%.1f GB" % n


def download(url, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        print("  = ya existe  %s" % dest)
        return
    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
    print("  [descargando] %s" % url)
    req = urllib.request.Request(url, headers={"User-Agent": "crear-web-saas-suscripcion/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r, open(dest + ".part", "wb") as f:
        total = 0
        while True:
            chunk = r.read(1 << 16)
            if not chunk:
                break
            f.write(chunk)
            total += len(chunk)
    os.replace(dest + ".part", dest)
    print("  [OK] %s (%s)" % (dest, human(total)))


def main(argv):
    args = [a for a in argv if not a.startswith("-")]
    if "--list" in argv or not args:
        print("Arquetipos y archivos que vendorizan:\n")
        for name, keys in sorted(ARCHETYPES.items()):
            print("  %-22s %s" % (name, ", ".join(keys) if keys else "(sin librerias)"))
        print("\nLa IA (Gemini) corre en el servidor: no se vendoriza nada de IA.")
        return 0
    keys, unknown = [], []
    for a in args:
        if a in ARCHETYPES:
            keys.extend(ARCHETYPES[a])
        else:
            unknown.append(a)
    if unknown:
        print("Arquetipo(s) desconocido(s): %s\nUsa --list para verlos." % ", ".join(unknown))
        return 1
    if not keys:
        print("Esos arquetipos no necesitan librerias en el navegador. [OK]")
        return 0
    seen = []
    for k in keys:
        if k not in seen:
            seen.append(k)
    print("Vendorizando %d archivo(s) en %s\n" % (len(seen), os.getcwd()))
    failures = 0
    for k in seen:
        url, dest = FILES[k]
        try:
            download(url, dest)
        except Exception as e:
            failures += 1
            print("  [FALLO] %s -> %s (%s)" % (k, dest, e))
    if failures:
        print("\n%d descarga(s) fallaron. Revisa reference/14-library-pinning.md." % failures)
        return 2
    print("\nTodo vendorizado. [OK]")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
