<?php
// setup.php — activar la IA UNA sola vez, desde el navegador.
// El dueño de la web nunca edita ficheros ni pega la clave en un chat.
// Reconoce sola si la clave es de Anthropic (Claude) o de Google (Gemini),
// la valida contra el proveedor y la guarda en el servidor, fuera de todo lo
// que el navegador puede descargar. Nunca se muestra ni se registra.
//
// El motor por defecto es Claude; Gemini funciona de respaldo. Con una basta;
// puedes configurar las dos ejecutando este formulario una vez por cada una.
//
// IMPORTANTE: cuando termines, borra este archivo o protégelo.

// Un fichero por proveedor, preferentemente fuera de public_html.
$PROV = [
  'claude' => [
    'nombre' => 'Anthropic (Claude)',
    'out'    => __DIR__ . '/../anthropic_api_key.php',
    'in'     => __DIR__ . '/datos/anthropic_config.php',
  ],
  'gemini' => [
    'nombre' => 'Google (Gemini)',
    'out'    => __DIR__ . '/../gemini_api_key.php',
    'in'     => __DIR__ . '/datos/gemini_config.php',
  ],
];

function leer($p) {
  foreach (['out', 'in'] as $d) {
    if (is_file($p[$d])) { $v = @include $p[$d]; if (is_string($v) && trim($v) !== '') return trim($v); }
  }
  return '';
}
function guardar($p, $key) {
  $c = "<?php return '" . str_replace("'", "\\'", $key) . "';\n";
  if (@file_put_contents($p['out'], $c) !== false) return 'fuera de la carpeta pública';
  @mkdir(dirname($p['in']), 0755, true);
  return (@file_put_contents($p['in'], $c) !== false) ? 'en la carpeta privada' : false;
}

// Detecta el proveedor por la forma de la clave. NO exigimos «AIza»: Google
// también emite claves «AQ.…». Descartamos lo que claramente no es una clave.
function detectar($k) {
  if (strpos($k, 'sk-ant-') === 0) return 'claude';
  if (strlen($k) >= 20 && !preg_match('/\s/', $k)) return 'gemini';
  return '';
}
function validar($prov, $key) {
  if (!function_exists('curl_init')) return true;   // sin cURL, confiamos
  if ($prov === 'claude') {
    $ch = curl_init('https://api.anthropic.com/v1/messages');
    curl_setopt_array($ch, [
      CURLOPT_RETURNTRANSFER => true, CURLOPT_POST => true, CURLOPT_TIMEOUT => 25,
      CURLOPT_HTTPHEADER => ['content-type: application/json', 'x-api-key: ' . $key, 'anthropic-version: 2023-06-01'],
      CURLOPT_POSTFIELDS => json_encode(['model' => 'claude-haiku-4-5', 'max_tokens' => 4, 'messages' => [['role' => 'user', 'content' => 'hola']]]),
    ]);
  } else {
    $ch = curl_init('https://generativelanguage.googleapis.com/v1beta/models?key=' . urlencode($key));
    curl_setopt_array($ch, [CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 20]);
  }
  $r = curl_exec($ch); $c = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE); curl_close($ch);
  return ($r !== false && $c === 200);
}

$msg = ''; $tono = 'warn';
if (($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
  $k = trim((string) ($_POST['clave'] ?? ''));
  $prov = detectar($k);
  if ($prov === '') {
    $msg = 'Eso no parece una clave. Pégala entera, sin espacios.';
  } elseif (!validar($prov, $k)) {
    $msg = $PROV[$prov]['nombre'] . ' no ha aceptado esa clave. Compruébala y vuelve a pegarla.';
  } else {
    $donde = guardar($PROV[$prov], $k);
    if ($donde === false) {
      $msg = 'La clave es válida, pero el servidor no me deja escribirla. Revisa los permisos.';
    } else {
      $msg = '¡Listo! La clave de ' . $PROV[$prov]['nombre'] . ' es válida y ha quedado guardada ' . $donde . '.';
      $tono = 'ok';
    }
  }
}

$tieneClaude = leer($PROV['claude']) !== '';
$tieneGemini = leer($PROV['gemini']) !== '';
?><!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex">
<title>Activar la IA</title>
<style>
  :root{--bg:#0f1115;--card:#171a21;--tx:#e7e9ee;--mu:#9aa3b2;--ac:#4f7cff;--ok:#2fa46a;--wa:#d08b28}
  *{box-sizing:border-box}
  body{margin:0;min-height:100vh;display:grid;place-items:center;background:var(--bg);color:var(--tx);
       font:16px/1.6 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;padding:24px}
  .card{background:var(--card);border:1px solid #262b36;border-radius:16px;padding:32px;max-width:560px;width:100%}
  h1{margin:0 0 8px;font-size:22px}
  p{color:var(--mu);margin:0 0 16px}
  ol{color:var(--mu);padding-left:20px;margin:0 0 16px}
  a{color:var(--ac)}
  code{background:#0d1016;padding:1px 6px;border-radius:5px}
  input{width:100%;padding:12px 14px;border-radius:10px;border:1px solid #2c3342;background:#0d1016;
        color:var(--tx);font:inherit;font-family:ui-monospace,monospace}
  button{margin-top:14px;width:100%;padding:12px;border:0;border-radius:10px;background:var(--ac);
         color:#fff;font:inherit;font-weight:600;cursor:pointer}
  .msg{padding:12px 14px;border-radius:10px;margin-bottom:18px;font-size:15px}
  .ok{background:rgba(47,164,106,.12);color:#7fd6a6;border:1px solid rgba(47,164,106,.3)}
  .warn{background:rgba(208,139,40,.12);color:#e6b866;border:1px solid rgba(208,139,40,.3)}
  .estado{display:flex;gap:16px;margin:0 0 20px;font-size:14px;color:var(--mu)}
  .pin{display:inline-flex;align-items:center;gap:6px}
  .dot{width:9px;height:9px;border-radius:50%;background:#3a4150}
  .on{background:var(--ok)}
</style></head><body>
<div class="card">
  <h1>Activar la inteligencia artificial</h1>
  <?php if ($msg): ?><div class="msg <?= $tono === 'ok' ? 'ok' : 'warn' ?>"><?= htmlspecialchars($msg) ?></div><?php endif; ?>

  <div class="estado">
    <span class="pin"><span class="dot <?= $tieneClaude ? 'on' : '' ?>"></span> Claude <?= $tieneClaude ? '(activa)' : '(sin configurar)' ?></span>
    <span class="pin"><span class="dot <?= $tieneGemini ? 'on' : '' ?>"></span> Gemini <?= $tieneGemini ? '(activa)' : '(respaldo, opcional)' ?></span>
  </div>

  <?php if ($tieneClaude || $tieneGemini): ?>
    <p>Ya puedes usar la herramienta. Por seguridad, cuando termines
    <strong>borra este archivo (<code>setup.php</code>)</strong> desde tu panel de
    hosting. Puedes volver a pegar otra clave abajo para actualizarla o añadir la de respaldo.</p>
  <?php else: ?>
    <p>Pega tu clave. El sistema reconoce sola si es de <strong>Claude</strong>
    (empieza por <code>sk-ant-</code>) o de <strong>Gemini</strong>. Con una basta;
    Claude es el motor por defecto.</p>
  <?php endif; ?>
  <p style="font-size:14px">Claves gratis: Claude en
    <a href="https://console.anthropic.com/settings/keys" target="_blank" rel="noopener">console.anthropic.com</a> ·
    Gemini en <a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener">aistudio.google.com</a>.</p>
  <form method="post">
    <input name="clave" type="password" placeholder="sk-ant-...  o  AIza..." autocomplete="off" required>
    <button type="submit">Guardar y comprobar</button>
  </form>
</div></body></html>
