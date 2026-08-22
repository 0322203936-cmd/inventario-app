#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
descargar-librerias.py — vendoriza las (pocas) librerias de frontend de la skill
crear-web-afiliados-amazon dentro del proyecto actual.

Uso (desde la RAIZ del proyecto web):
    python scripts/descargar-librerias.py --list
    python scripts/descargar-librerias.py graficos
    python scripts/descargar-librerias.py galeria

Nota: el radar y las barras se pueden dibujar a mano en canvas/SVG sin libreria
(preferido, menos dependencias). Estas descargas son opcionales, solo si eliges
usar una libreria de graficos o un visor de galeria.

El scraper (amazon_extractor.py) NO se descarga aqui: ya viene en la skill y usa
Scrapling, que se instala con pip (ver reference/06-populate-pipeline.md).
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
    # Grafico (opcional; el radar a mano en SVG es la via preferida)
    "chartjs":   (CDN + "chart.js@4.5.0/dist/chart.umd.min.js",
                  "lib/vendor/chart.umd.min.js"),
    # Galeria de imagenes ligera (opcional)
    "glightbox-js": (CDN + "glightbox@3.3.1/dist/js/glightbox.min.js",
                     "lib/vendor/glightbox.min.js"),
    "glightbox-css": (CDN + "glightbox@3.3.1/dist/css/glightbox.min.css",
                      "lib/vendor/glightbox.min.css"),
}

GROUPS = {
    "graficos": ["chartjs"],
    "galeria":  ["glightbox-js", "glightbox-css"],
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
    req = urllib.request.Request(url, headers={"User-Agent": "crear-web-afiliados/1.0"})
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
        print("Grupos opcionales de librerias:\n")
        for name, keys in sorted(GROUPS.items()):
            print("  %-12s %s" % (name, ", ".join(keys)))
        print("\nEl radar/barras se pueden dibujar sin libreria (preferido).")
        print("El scraper usa Scrapling (pip), no se descarga aqui.")
        return 0
    keys, unknown = [], []
    for a in args:
        if a in GROUPS:
            keys.extend(GROUPS[a])
        else:
            unknown.append(a)
    if unknown:
        print("Grupo(s) desconocido(s): %s\nUsa --list para verlos." % ", ".join(unknown))
        return 1
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
        print("\n%d descarga(s) fallaron." % failures)
        return 2
    print("\nTodo vendorizado. [OK]")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
