<?php
// gemini.php — EL ÚNICO archivo que toca las claves de la IA.
// El navegador nunca habla con Claude ni con Google: habla con este archivo,
// en tu propio dominio. Copia esta plantilla a api/gemini.php y adáptala.
//
// Dos motores, un trabajo:
//   · Texto/documentos → Claude Haiku por defecto, Gemini de respaldo.
//   · Imágenes         → Gemini (requiere facturación).
// Con una sola clave el producto ya funciona. Ver 05-gemini-api.md.

// ---------- Configuración ----------
$MODELO_CLAUDE = 'claude-haiku-4-5';
// La familia 2.5 está retirada para claves nuevas. Estos responden hoy.
// NO añadir thinkingConfig: los *-lite dan HTTP 400 si se incluye.
$MODELS_GEMINI = ['gemini-3.5-flash', 'gemini-3.6-flash', 'gemini-flash-latest'];
$MODEL_IMG     = 'gemini-3.1-flash-image';   // imágenes: REQUIERE facturación
$PER_MIN       = 20;    // peticiones por IP y minuto
$PER_DAY       = 300;   // por IP y día
$GLOBAL_DAY    = 2000;  // tope global diario: protege la cuota
$TIMEOUT       = 60;    // segundos (sube a 180 en documentos muy largos)

// ---------- Claves: entorno -> fuera de public_html -> respaldo local ----------
function ia_key_claude() {
  $k = getenv('ANTHROPIC_API_KEY');
  if (!$k && is_file(__DIR__ . '/../../anthropic_api_key.php')) $k = @include __DIR__ . '/../../anthropic_api_key.php';
  if (!$k && is_file(__DIR__ . '/../datos/anthropic_config.php')) $k = @include __DIR__ . '/../datos/anthropic_config.php';
  $k = is_string($k) ? trim($k) : '';
  return ($k !== '' && $k !== 'TU_CLAVE_AQUI') ? $k : '';
}
function ia_key_gemini() {
  $k = getenv('GEMINI_API_KEY');
  if (!$k && is_file(__DIR__ . '/../../gemini_api_key.php')) $k = @include __DIR__ . '/../../gemini_api_key.php';
  if (!$k && is_file(__DIR__ . '/../datos/gemini_config.php')) $k = @include __DIR__ . '/../datos/gemini_config.php';
  if (!$k && is_file(__DIR__ . '/../datos/secret_config.php')) $k = @include __DIR__ . '/../datos/secret_config.php';
  $k = is_string($k) ? trim($k) : '';
  return ($k !== '' && $k !== 'TU_CLAVE_AQUI') ? $k : '';
}
// Hay servicio si AL MENOS un motor tiene clave.
function ia_hay_clave() { return ia_key_claude() !== '' || ia_key_gemini() !== ''; }

// ---------- Límites de uso (por encima del sistema de créditos) ----------
// Devuelve '' si se puede seguir, o un motivo ('rate_min'|'rate_day'|'rate_global').
function ia_limites($prefijo) {
  global $PER_MIN, $PER_DAY, $GLOBAL_DAY;
  $ip = $_SERVER['REMOTE_ADDR'] ?? '0.0.0.0';
  $tmp = sys_get_temp_dir(); $now = time(); $hoy = date('Ymd');

  $ipFile = $tmp . '/' . $prefijo . '_rl_' . md5($ip) . '.json';
  $stamps = is_file($ipFile) ? json_decode(@file_get_contents($ipFile), true) : [];
  if (!is_array($stamps)) $stamps = [];
  $enMin = array_filter($stamps, function ($t) use ($now) { return $t > $now - 60; });
  $enDia = array_filter($stamps, function ($t) use ($now) { return $t > $now - 86400; });
  if (count($enMin) >= $PER_MIN) return 'rate_min';
  if (count($enDia) >= $PER_DAY) return 'rate_day';

  $gFile  = $tmp . '/' . $prefijo . '_rl_global_' . $hoy . '.txt';
  $gCount = is_file($gFile) ? (int) @file_get_contents($gFile) : 0;
  if ($gCount >= $GLOBAL_DAY) return 'rate_global';

  $stamps[] = $now;
  $stamps = array_slice($stamps, -600);
  @file_put_contents($ipFile, json_encode(array_values($stamps)), LOCK_EX);
  @file_put_contents($gFile, (string) ($gCount + 1), LOCK_EX);
  return '';
}

// ---------- Llamada HTTP genérica ----------
function ia_http($url, $headers, $body, $timeout = null) {
  global $TIMEOUT;
  $ch = curl_init($url);
  curl_setopt_array($ch, [
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_POST           => true,
    CURLOPT_HTTPHEADER     => $headers,
    CURLOPT_POSTFIELDS     => $body,
    CURLOPT_TIMEOUT        => $timeout ?: $TIMEOUT,
  ]);
  $resp = curl_exec($ch);
  $code = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE);
  $err  = curl_error($ch);
  curl_close($ch);
  return [$resp, $code, $err];
}

// ---------- Motor Claude (Anthropic) — por defecto para texto ----------
function ia_claude($system, $prompt, $maxTokens = 2000) {
  global $MODELO_CLAUDE;
  $key = ia_key_claude();
  if ($key === '') return ['ok' => false, 'motivo' => 'sin_clave_claude'];
  $body = json_encode([
    'model' => $MODELO_CLAUDE, 'max_tokens' => $maxTokens,
    'system' => $system, 'messages' => [['role' => 'user', 'content' => $prompt]],
  ], JSON_UNESCAPED_UNICODE);
  list($resp, $code, $err) = ia_http('https://api.anthropic.com/v1/messages',
    ['content-type: application/json', 'x-api-key: ' . $key, 'anthropic-version: 2023-06-01'], $body);
  if ($resp === false || $code >= 400) { @error_log("[claude] http $code $err " . substr((string)$resp,0,200)); return ['ok' => false, 'motivo' => "claude http $code"]; }
  $texto = json_decode($resp, true)['content'][0]['text'] ?? '';
  return $texto !== '' ? ['ok' => true, 'texto' => $texto] : ['ok' => false, 'motivo' => 'claude_vacio'];
}

// ---------- Motor Gemini — respaldo de texto ----------
function ia_gemini($system, $prompt, $maxTokens = 4096) {
  global $MODELS_GEMINI;
  $key = ia_key_gemini();
  if ($key === '') return ['ok' => false, 'motivo' => 'sin_clave_gemini'];
  $payload = [
    'system_instruction' => ['parts' => [['text' => $system]]],
    'contents'           => [['role' => 'user', 'parts' => [['text' => $prompt]]]],
    'generationConfig'   => ['temperature' => 0.1, 'topP' => 0.9, 'maxOutputTokens' => $maxTokens, 'responseMimeType' => 'application/json'],
    'safetySettings'     => [
      ['category' => 'HARM_CATEGORY_HARASSMENT',        'threshold' => 'BLOCK_ONLY_HIGH'],
      ['category' => 'HARM_CATEGORY_HATE_SPEECH',       'threshold' => 'BLOCK_ONLY_HIGH'],
      ['category' => 'HARM_CATEGORY_SEXUALLY_EXPLICIT', 'threshold' => 'BLOCK_ONLY_HIGH'],
      ['category' => 'HARM_CATEGORY_DANGEROUS_CONTENT', 'threshold' => 'BLOCK_ONLY_HIGH'],
    ],
  ];
  $body = json_encode($payload, JSON_UNESCAPED_UNICODE);
  $ultimo = '';
  foreach ($MODELS_GEMINI as $model) {
    $url = 'https://generativelanguage.googleapis.com/v1beta/models/' . rawurlencode($model) . ':generateContent?key=' . urlencode($key);
    list($resp, $code, $err) = ia_http($url, ['Content-Type: application/json'], $body);
    if ($resp === false || $code >= 400) { $ultimo = "$model http $code"; continue; }
    $texto = json_decode($resp, true)['candidates'][0]['content']['parts'][0]['text'] ?? '';
    if ($texto !== '') return ['ok' => true, 'texto' => $texto];
    $ultimo = "$model vacio";
  }
  @error_log('[gemini] ' . $ultimo);
  return ['ok' => false, 'motivo' => $ultimo];
}

// ---------- Texto: Claude primero, Gemini de respaldo ----------
// Devuelve ['ok'=>true,'texto'=>...] o ['ok'=>false,'motivo'=>...].
// El motivo es para el registro, NUNCA para enseñárselo a nadie.
function ia_texto($system, $prompt, $maxTokens = 2000) {
  $r = ia_claude($system, $prompt, $maxTokens);
  if ($r['ok']) return $r;
  return ia_gemini($system, $prompt, max($maxTokens, 4096));
}

// ---------- Generación de imágenes (Gemini, REQUIERE facturación) ----------
function ia_imagen($prompt, $imagenesBase64 = [], $mime = 'image/png') {
  global $MODEL_IMG;
  $key = ia_key_gemini();
  if ($key === '') return ['ok' => false, 'motivo' => 'sin_clave_gemini'];
  $partes = [['text' => $prompt]];
  foreach ($imagenesBase64 as $b64) $partes[] = ['inline_data' => ['mime_type' => $mime, 'data' => $b64]];
  $body = json_encode(['contents' => [['role' => 'user', 'parts' => $partes]]], JSON_UNESCAPED_UNICODE);
  $url = 'https://generativelanguage.googleapis.com/v1beta/models/' . rawurlencode($MODEL_IMG) . ':generateContent?key=' . urlencode($key);
  list($resp, $code, $err) = ia_http($url, ['Content-Type: application/json'], $body, 180);
  if ($resp === false || $code >= 400) { @error_log('[ia-img] http ' . $code . ' ' . $err); return ['ok' => false, 'motivo' => 'http_' . $code]; }
  foreach (json_decode($resp, true)['candidates'][0]['content']['parts'] ?? [] as $p) {
    if (isset($p['inline_data']['data'])) return ['ok' => true, 'imagen' => $p['inline_data']['data']];
  }
  return ['ok' => false, 'motivo' => 'sin_imagen'];
}

// ---------- Ayuda: extraer JSON aunque venga con ``` o texto alrededor ----------
// Neutraliza también el bug de Gemini que cierra el array con un ] de más.
function ia_json($texto) {
  $t = trim($texto);
  $t = preg_replace('/^```(?:json)?/m', '', $t);
  $t = preg_replace('/```$/m', '', $t);
  $d = json_decode(trim($t), true);
  if (!is_array($d)) {                       // 2º intento: del primer { al último }
    $a = strpos($t, '{'); $b = strrpos($t, '}');
    if ($a !== false && $b !== false && $b > $a) $d = json_decode(substr($t, $a, $b - $a + 1), true);
  }
  return is_array($d) ? $d : null;
}
