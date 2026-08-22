#!/bin/bash
# Recorta una imagen al ratio exacto de banner (contrato del banner, fase 3b).
# Solo Mac: usa sips (incluido en macOS). El recorte es SIEMPRE centrado
# (sips no permite desplazarlo; si necesitas conservar la parte alta/baja,
# regenera la foto con mas zona segura o usa la posicion focal del CSS).
#
# Uso:
#   bash recortar-banner.sh entrada.jpg salida.jpg [16:9]
#
# Imprime "OK <ruta> (<ancho>x<alto>)" o "ERROR <detalle>". Codigo de salida 0/1.

set -u

ENTRADA="${1:-}"
SALIDA="${2:-}"
RATIO="${3:-16:9}"

fallo() { echo "ERROR $1"; exit 1; }

[ -n "$ENTRADA" ] && [ -n "$SALIDA" ] || fallo "uso: recortar-banner.sh entrada.jpg salida.jpg [16:9]"
[ -f "$ENTRADA" ] || fallo "no existe la imagen de entrada: $ENTRADA"
command -v sips >/dev/null 2>&1 || fallo "sips no esta disponible (este script es solo para Mac)"

RW="${RATIO%%[:x/]*}"
RH="${RATIO##*[:x/]}"
case "$RW$RH" in (*[!0-9.]*) fallo "ratio no valido: $RATIO (usa formato 16:9)";; esac
[ -n "$RW" ] && [ -n "$RH" ] || fallo "ratio no valido: $RATIO"

W=$(sips -g pixelWidth  "$ENTRADA" | awk '/pixelWidth/  {print $2}')
H=$(sips -g pixelHeight "$ENTRADA" | awk '/pixelHeight/ {print $2}')
[ -n "$W" ] && [ -n "$H" ] || fallo "no se pudieron leer las dimensiones de $ENTRADA"

read -r CW CH <<EOF
$(awk -v w="$W" -v h="$H" -v rw="$RW" -v rh="$RH" 'BEGIN {
  objetivo = rw / rh; origen = w / h;
  if (objetivo >= origen) { cw = w; ch = int(w / objetivo + 0.5) }
  else { ch = h; cw = int(h * objetivo + 0.5) }
  if (cw < 1 || ch < 1) { print 0, 0 } else { print cw, ch }
}')
EOF
[ "$CW" -gt 0 ] && [ "$CH" -gt 0 ] || fallo "el recorte resultante es de tamano cero"

mkdir -p "$(dirname "$SALIDA")" || fallo "no se pudo crear la carpeta de salida"

if sips -c "$CH" "$CW" "$ENTRADA" --out "$SALIDA" >/dev/null 2>&1; then
  echo "OK $SALIDA (${CW}x${CH})"
  exit 0
else
  fallo "sips no pudo recortar la imagen"
fi
