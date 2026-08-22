# The AI engines — every call this skill needs (verified July 2026)

The AI half of every archetype. **All calls happen server-side** through the
proxy (`15-backend-proxy.md`). Never from the browser.

**Two engines, one job.** For text and documents the default is **Claude Haiku**
(Anthropic); **Gemini** is the automatic fallback and the only engine for image
generation. Both are called with PHP + cURL, walked in order, with per-IP and
global rate limits and a graceful fallback chain. The proxy holds both keys;
either one alone makes the product work.

Why Claude first for text (all learned the hard way in production):
- Gemini's **free 2.5 models are retired for new API keys** (`404 … no longer
  available to new users`).
- Gemini's structured-JSON output **breaks intermittently** — it closes an array
  with a duplicated `]` (`… ]  ]  }`, `finishReason: STOP`), so a strict
  `json_decode` fails and the user sees "couldn't read the page". Claude does not
  do this.
- Claude is excellent and cheap on plain text, which is what the new document
  pipeline sends it (`06-recipes-documents.md`): the browser extracts the text,
  the AI only classifies it.

Keep Gemini wired up: it is the fallback, it is better at raw vision when you
genuinely must send an image, and it is the image generator.

---

## 1. Claude (Anthropic) — the default text engine

```
POST https://api.anthropic.com/v1/messages
Headers: content-type: application/json
         x-api-key: <sk-ant-…>
         anthropic-version: 2023-06-01
Body:    { "model":"claude-haiku-4-5", "max_tokens":2000,
           "system":"<role>", "messages":[{"role":"user","content":"<prompt>"}] }
Reply:   data["content"][0]["text"]
```

- Model id: **`claude-haiku-4-5`**. No `thinkingConfig`, no `responseMimeType` —
  ask for JSON in the prompt and strip stray ```` ``` ```` fences defensively
  (Claude sometimes wraps JSON in a code fence).
- Content can be plain text (the document pipeline) or a vision block
  `[{type:"image",source:{type:"base64",media_type,data}}, {type:"text",text}]`
  if you ever need Claude to read an image directly. **Do not ask Claude for
  bounding-box coordinates** — it returns them badly misplaced; positioning is
  done locally (`06`).

## 2. Gemini — the fallback engine, and the image generator

Endpoint `POST /v1beta/models/{model}:generateContent?key=KEY` (cURL, `?key=` in
the URL). For fallback text/vision use the **current free models**, declared as
an ordered array and walked on failure:

```php
// The 2.5 family is GONE for new keys. These are the ones that answer today:
$MODELS = ['gemini-3.5-flash', 'gemini-3.6-flash', 'gemini-flash-latest'];
```

- **Never send `thinkingConfig.thinkingBudget`** with these models — the *-lite*
  variants return `HTTP 400 invalid argument` if you do. Omit it entirely.
- `responseMimeType: application/json` still helps, but validate the result
  anyway (see the duplicated-`]` bug above): parse, and on failure retry trimming
  from the first `{` to the last `}`.
- Paid tiers (`gemini-3.1-pro-preview`) are better on dense documents; offer as
  an upgrade only if the free models underperform, and say what it costs.

**Image generation is Gemini-only and paid, always** — there is no free tier:

| Model | Per image | Notes |
|---|---|---|
| `gemini-3.1-flash-image` | $0.045 (1K $0.067, 2K $0.101, 4K $0.151) | **Default.** Up to 10 input images |
| `gemini-3.1-flash-lite-image` | $0.0336 (1K only) | Cheapest |
| `gemini-3-pro-image` | $0.134 (4K $0.24) | Best quality |

All generated images carry an invisible **SynthID** watermark — say so in the
FAQ.

## 3. Free tier and training: what each engine costs you

**Gemini free tier uses submitted content to improve Google's products**; the
paid tier does not. **Anthropic does not train on API content by default**, which
is one more reason Claude is the default for personal-data archetypes. Be
straight with the user:

- Fine on a free/default tier: `foto-estilos`, `macros-foto`, `apuntes-resumen`,
  generic document demos, and all testing.
- **Move to a paid tier before real customers upload sensitive documents**
  (`censurar-pdf`, `facturas-excel`, `analizar-contratos`, payslips, medical or
  legal material). On Gemini it's a billing switch on the same key; on Anthropic
  the default already doesn't train — confirm the current terms and say so.
- The new document pipeline (`06`) sends the AI **only extracted text, never the
  page image**, which already shrinks exposure. Say it once, plainly, when the AI
  part starts, put it in the go-live checklist, and state the truth in the
  privacy page whatever they choose.

Free quotas are per project and not published as a fixed table — which is
exactly why the rate limiting in §5 exists.

## 3b. The engine chain in one function (copy this shape)

```
ia_detectar(system, prompt):
    r = ia_claude(system, prompt)          # default
    if r.ok and parse(r.text) is valid: return parsed
    r = ia_gemini(system, prompt)          # fallback
    if r.ok and parse(r.text) is valid: return parsed
    return failure                          # → caller refunds the credit
```

`ia_hay_clave()` is true if **either** key is present. `parse()` strips ```` ``` ````
fences, `json_decode`s, and on failure retries from the first `{` to the last
`}` — this is what neutralises Gemini's duplicated-`]` bug. Keep the whole AI
call in one file (`api/gemini.php`), the only place the keys are read.

## 4. The call, in full (PHP — copy this)

```php
function call_gemini($model, $key, $body) {
  $url = 'https://generativelanguage.googleapis.com/v1beta/models/'
       . rawurlencode($model) . ':generateContent?key=' . urlencode($key);
  $ch = curl_init($url);
  curl_setopt_array($ch, [
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_POST           => true,
    CURLOPT_HTTPHEADER     => ['Content-Type: application/json'],
    CURLOPT_POSTFIELDS     => $body,
    CURLOPT_TIMEOUT        => 30,      // 120+ for multi-page documents
  ]);
  $resp = curl_exec($ch);
  $code = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE);
  $err  = curl_error($ch);
  curl_close($ch);
  return [$resp, $code, $err];
}

// Walk the models until one answers
$reply = ''; $lastErr = '';
foreach ($MODELS as $model) {
  list($resp, $code, $err) = call_gemini($model, $key, $body);
  if ($resp === false || $code >= 400) { $lastErr = "$model http $code $err"; continue; }
  $data  = json_decode($resp, true);
  $reply = $data['candidates'][0]['content']['parts'][0]['text'] ?? '';
  if ($reply !== '') break;
  $block   = $data['promptFeedback']['blockReason']
           ?? ($data['candidates'][0]['finishReason'] ?? 'desconocido');
  $lastErr = "$model respuesta vacía ($block)";
}
if ($reply === '') { @error_log('[ia] ' . $lastErr); /* human fallback */ }
```

**Never surface `$lastErr` to the user.** Log it; show a sentence like «Ahora
mismo no puedo procesarlo, inténtalo en un momento» and refund the credit.

### The payload

```php
$payload = [
  'system_instruction' => ['parts' => [['text' => $system]]],
  'contents'           => $contents,      // see the shapes below
  'generationConfig'   => [
    'temperature'      => 0.2,            // 0.1-0.3 extraction · 0.4-0.7 prose
    'topP'             => 0.9,
    'maxOutputTokens'  => 2048,
    'responseMimeType' => 'application/json',   // when you want JSON (see §6)
    // NO 'thinkingConfig' here — the current *-lite models 400 on it (§2).
  ],
  'safetySettings' => [
    ['category' => 'HARM_CATEGORY_HARASSMENT',        'threshold' => 'BLOCK_ONLY_HIGH'],
    ['category' => 'HARM_CATEGORY_HATE_SPEECH',       'threshold' => 'BLOCK_ONLY_HIGH'],
    ['category' => 'HARM_CATEGORY_SEXUALLY_EXPLICIT', 'threshold' => 'BLOCK_ONLY_HIGH'],
    ['category' => 'HARM_CATEGORY_DANGEROUS_CONTENT', 'threshold' => 'BLOCK_ONLY_HIGH'],
  ],
];
$body = json_encode($payload, JSON_UNESCAPED_UNICODE);
```

`BLOCK_ONLY_HIGH` is the right default for business documents: it stops real
abuse without refusing a contract that mentions weapons or an invoice from a
tobacco shop. Always handle a block anyway (`finishReason`, `blockReason`).

### Content shapes

```php
// (a) Plain text
$contents = [['role' => 'user', 'parts' => [['text' => $prompt]]]];

// (b) Chat with history (roles alternate 'user' / 'model')
$contents[] = ['role' => 'model', 'parts' => [['text' => $previousAnswer]]];
$contents[] = ['role' => 'user',  'parts' => [['text' => $message]]];

// (c) Image or PDF inline (up to ~10-15 MB of base64; bigger → File API §8)
$contents = [['role' => 'user', 'parts' => [
  ['text' => $instruccion],
  ['inline_data' => ['mime_type' => $mime, 'data' => base64_encode($bytes)]],
]]];

// (d) Several images in one call (comparisons, multi-page, style refs)
$parts = [['text' => $instruccion]];
foreach ($imagenes as $img) {
  $parts[] = ['inline_data' => ['mime_type' => 'image/png', 'data' => $img]];
}
$contents = [['role' => 'user', 'parts' => $parts]];
```

Accepted MIME types: `application/pdf`, `image/jpeg`, `image/png`,
`image/webp`, `image/heic`, `image/heif`. Detect the **real** type with
`finfo_file`, never trust the extension.

## 5. Rate limiting (mandatory — it protects the free quota and the wallet)

Three layers, all cheap, all proven:

```php
$PER_MIN    = 8;     // per IP per minute
$PER_DAY    = 100;   // per IP per day
$GLOBAL_DAY = 1200;  // whole site per day — the one that saves you
```

Counters live in `sys_get_temp_dir()` as `md5(ip).json` (timestamps) and
`global_YYYYMMDD.txt`. Check BEFORE calling, record AFTER validating, and when
a limit trips return a **friendly sentence**, never a 429 with jargon
(«Vas muy rápido 🙂 espera unos segundos»). For heavy operations (documents,
images) use lower numbers — the proven invoice reader uses 6/min, 40/day,
400/day global.

In this skill these limits sit **on top of** the credit system: credits stop
paying users overusing, rate limits stop abuse and runaway bills.

## 6. Structured JSON (use it for every extraction)

Two things together, and only then is it reliable:

1. `'responseMimeType' => 'application/json'` in `generationConfig`.
2. The exact JSON shape spelled out in the prompt, with rules.

The proven prompt style — copy this discipline:

```
Devuelve EXCLUSIVAMENTE un objeto JSON válido (sin texto adicional, sin ```)
con EXACTAMENTE estas claves:
{ "campo_a": string|null, "campo_b": number|null, "confianza": number }

Reglas:
- Usa PUNTO como separador decimal. Sin símbolos de moneda dentro de los números.
- Si un dato no aparece, pon null. NO lo inventes.
- <reglas de normalización específicas del dominio>
```

Then in PHP: strip stray fences defensively, `json_decode`, and **validate**
(keys present, types right, numbers sane) before using it. The model obeys the
schema but can still return nulls or empty arrays — that's a UI state, not a
crash.

Optional: `responseSchema` (a JSON-Schema object next to `responseMimeType`)
enforces the shape server-side. Use it when the structure is deep; for flat
objects the prompt rules above are enough and cheaper.

## 7. Bounding boxes — legacy technique, avoid for redaction

> ⚠️ **The document pipeline no longer asks the AI for coordinates** — the
> browser positions everything from the local text layer / OCR (`06`). Claude in
> particular returns badly misplaced boxes, and misplaced boxes on a redaction
> tool leave personal data visible. Keep this section only for the rare case
> where you truly cannot get a text layer AND must locate something in a raw
> image; then use **Gemini** (not Claude) for the boxes and treat them as
> approximate.

Gemini returns coordinates as `box_2d` = `[ymin, xmin, ymax, xmax]` normalized
**0-1000**. Rescale: `x = xmin/1000 * width`.

> `Detect <lo que buscas>. The box_2d should be [ymin, xmin, ymax, xmax] normalized to 0-1000.`

Rules if you ever must: rasterize each page to PNG server-side and ask for boxes
on the image (deterministic pixel↔box mapping); **do not send `thinkingConfig`**
(§2); pad every box a few pixels and let the user adjust; rectangles only, which
is all a redaction needs.

## 8. Big files: the File API

Inline base64 is fine up to ~10-15 MB (the proven implementation caps uploads
at 10 MB and it covers most real documents). Above that:

```
POST https://generativelanguage.googleapis.com/upload/v1beta/files?key=KEY
→ returns { file: { uri, mimeType } }
then use  ['file_data' => ['mime_type' => $mime, 'file_uri' => $uri]]  as a part
```

Uploaded files are free, up to 2 GB each, and **expire after 48 h**. PDFs are
read natively (text, tables and charts) up to **1.000 pages**, at ~258 tokens
per page. Only PDF gets true visual understanding — DOCX/TXT lose structure,
so convert to PDF first when layout matters.

## 9. Image generation (paid — the only part that requires billing)

```php
$url = 'https://generativelanguage.googleapis.com/v1beta/models/'
     . 'gemini-3.1-flash-image:generateContent?key=' . urlencode($key);
$payload = ['contents' => [['role' => 'user', 'parts' => [
  ['text' => $prompt],
  ['inline_data' => ['mime_type' => 'image/png', 'data' => $fotoBase64]],
]]]];
// response: candidates[0].content.parts[] → the part carrying inline_data is the image
$img = null;
foreach ($data['candidates'][0]['content']['parts'] ?? [] as $p) {
  if (isset($p['inline_data']['data'])) { $img = $p['inline_data']['data']; break; }
}
```

Accepts **up to 10 input images** (product + scene, design + mockup, style
references). Resolutions 512px/1K/2K/4K; aspect ratios `1:1, 3:2, 2:3, 3:4,
4:3, 4:5, 5:4, 9:16, 16:9, 21:9`. Prompt craft in `11-recipes-images.md` §
Shared machinery. Return the image to the browser in the response body — never
save it to a public folder.

## 10. The keys: storage, validation, setup (two providers)

One resolver **per provider**, each with its own file, each resolved
env → above-`public_html` → in-folder fallback:

```php
function ia_key_claude() {
  $k = getenv('ANTHROPIC_API_KEY');
  if (!$k && is_file(__DIR__.'/../../anthropic_api_key.php')) $k = @include __DIR__.'/../../anthropic_api_key.php';
  if (!$k && is_file(__DIR__.'/../datos/anthropic_config.php')) $k = @include __DIR__.'/../datos/anthropic_config.php';
  $k = is_string($k) ? trim($k) : '';
  return ($k !== '' && $k !== 'TU_CLAVE_AQUI') ? $k : '';
}
// ia_key_gemini(): identical shape, files gemini_api_key.php / secret_config.php
```

Storing each as **`<?php return 'sk-ant-…';`** matters: even if the web server
ever stops parsing PHP, the file is never served as text. Best location is one
level **above** `public_html`; the in-folder file is the fallback.

**Ship a `setup.php`** so the owner never edits files by hand, and never pastes a
key in chat. It:
1. **Auto-detects the provider** — `sk-ant-…` → Anthropic, else → Google. Do NOT
   gate on `AIza`: Google now also issues `AQ.…` keys. Gate on length + no
   whitespace, then let the provider decide.
2. **Validates live**: Anthropic → a 4-token `messages` call (200 = good);
   Google → `GET /v1beta/models?key=KEY` (200 = good).
3. Writes it to the right file, and refuses to display or log it afterwards.
4. Tells them to delete or protect `setup.php` once configured.

Optional hardening: restrict the Google key in Cloud Console (by website/IP, to
the Generative Language API only); scope the Anthropic key to the workspace.

## 11. Errors to handle

| Situation | What to do |
|---|---|
| Claude/Gemini HTTP 429 / 5xx | Fall through to the other engine; then retry with backoff (1→2→4 s) |
| HTTP 400 | Your payload is wrong (e.g. `thinkingBudget` on a lite model) — log it, never retry blindly |
| HTTP 404 `no longer available to new users` | You used a retired Gemini 2.5 model — use the §2 array |
| Duplicated-`]` / invalid JSON | Retry the tolerant parse (first `{` to last `}`); this is the Gemini bug — Claude first avoids it |
| `promptFeedback.blockReason` | Safety block: human message, refund the credit |
| Empty text from an engine | Treat as failure, fall through to the other engine |
| Both engines fail | A human sentence, a refunded credit, a logged error — never a raw 500 |
