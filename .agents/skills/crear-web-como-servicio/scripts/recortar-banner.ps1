# Recorta una imagen al ratio exacto de banner (contrato del banner, fase 3b).
# Sin dependencias: usa System.Drawing (incluido en Windows).
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File recortar-banner.ps1 `
#     -Entrada hero-bruto.jpg -Salida mt-hero-fondo.jpg -Ratio 16:9 [-CentroY 0.5] [-Calidad 90]
#
#   -Ratio    ancho:alto del recorte final (16:9, 21:9, 4:3, 1:1...)
#   -CentroY  0 = conserva la parte ALTA, 0.5 = centro (defecto), 1 = parte BAJA
#   -Calidad  calidad JPEG 1-100 (defecto 90). Si -Salida termina en .png, guarda PNG.
#
# Imprime "OK <ruta> (<ancho>x<alto>)" o "ERROR <detalle>". Código de salida 0/1.

param(
  [Parameter(Mandatory = $true)][string]$Entrada,
  [Parameter(Mandatory = $true)][string]$Salida,
  [string]$Ratio = "16:9",
  [double]$CentroY = 0.5,
  [int]$Calidad = 90
)

$ErrorActionPreference = "Stop"

function Fallo($msg) { Write-Output ("ERROR " + $msg); exit 1 }

try {
  if (-not (Test-Path $Entrada)) { Fallo ("no existe la imagen de entrada: " + $Entrada) }
  $partes = $Ratio -split "[:x/]"
  if ($partes.Count -ne 2) { Fallo ("ratio no valido: " + $Ratio + " (usa formato 16:9)") }
  $rw = [double]$partes[0]; $rh = [double]$partes[1]
  if ($rw -le 0 -or $rh -le 0) { Fallo ("ratio no valido: " + $Ratio) }
  if ($CentroY -lt 0) { $CentroY = 0 }
  if ($CentroY -gt 1) { $CentroY = 1 }

  Add-Type -AssemblyName System.Drawing

  $rutaEntrada = (Resolve-Path $Entrada).Path
  $img = [System.Drawing.Image]::FromFile($rutaEntrada)

  $ratioObjetivo = $rw / $rh
  $ratioOrigen = $img.Width / [double]$img.Height

  if ($ratioObjetivo -ge $ratioOrigen) {
    # El objetivo es mas panoramico: ancho completo, se recorta altura
    $anchoRecorte = $img.Width
    $altoRecorte = [int][math]::Round($img.Width / $ratioObjetivo)
  } else {
    # El objetivo es mas alto: altura completa, se recorta anchura
    $altoRecorte = $img.Height
    $anchoRecorte = [int][math]::Round($img.Height * $ratioObjetivo)
  }
  if ($altoRecorte -lt 1 -or $anchoRecorte -lt 1) { Fallo "el recorte resultante es de tamano cero" }

  $x = [int][math]::Round(($img.Width - $anchoRecorte) / 2)
  $y = [int][math]::Round(($img.Height - $altoRecorte) * $CentroY)

  $bmp = New-Object System.Drawing.Bitmap($anchoRecorte, $altoRecorte)
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
  $destino = New-Object System.Drawing.Rectangle(0, 0, $anchoRecorte, $altoRecorte)
  $origen = New-Object System.Drawing.Rectangle($x, $y, $anchoRecorte, $altoRecorte)
  $g.DrawImage($img, $destino, $origen, [System.Drawing.GraphicsUnit]::Pixel)

  if ([System.IO.Path]::IsPathRooted($Salida)) {
    $rutaSalida = $Salida
  } else {
    $rutaSalida = [System.IO.Path]::GetFullPath((Join-Path (Get-Location).Path $Salida))
  }
  $dir = [System.IO.Path]::GetDirectoryName($rutaSalida)
  if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }

  if ($rutaSalida.ToLower().EndsWith(".png")) {
    $bmp.Save($rutaSalida, [System.Drawing.Imaging.ImageFormat]::Png)
  } else {
    $codec = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() |
      Where-Object { $_.MimeType -eq "image/jpeg" } | Select-Object -First 1
    $ep = New-Object System.Drawing.Imaging.EncoderParameters(1)
    $ep.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter(
      [System.Drawing.Imaging.Encoder]::Quality, [long]$Calidad)
    $bmp.Save($rutaSalida, $codec, $ep)
    $ep.Dispose()
  }

  $g.Dispose(); $bmp.Dispose(); $img.Dispose()
  Write-Output ("OK " + $rutaSalida + " (" + $anchoRecorte + "x" + $altoRecorte + ")")
  exit 0
} catch {
  Fallo $_.Exception.Message
}
