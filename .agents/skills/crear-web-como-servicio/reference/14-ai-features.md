# 🧠 AI Features — the differentiator that sells the web

This is what makes a client's site worth thousands: features their current
agency can't build. All of them run on **Google Gemini's free tier** through a
**same-domain PHP proxy** on the Hostinger plan (no VPS, no Node backend). The
pattern is proven in production (the solar-panels site: an AI assistant + a
bill-reading savings calculator). Templates are in `templates/`.

**The AI key never touches the browser.** The browser calls a `.php` on the same
domain; the key lives outside `public_html` (or in a `.php` never served as
text). This is invariant 1 — grep the deploy before publishing.

---

## 0. The proxy architecture (shared by every AI feature)

```
web/
├── index.html … (the static site; JS calls the .php below via fetch)
├── setup.php              ← paste the Gemini key once, from the browser (setup-ia.php.template)
├── asistente-ia.php       ← support chat proxy (asistente-ia.php.template)
├── lector-documento.php   ← read a bill/photo/PDF → JSON (lector-documento.php.template)
├── knowledge.php          ← the assistant's persona + facts (knowledge.php.template)
├── lead.php               ← capture emails/phones (lead.php.template)
└── (key lives at ../gemini_api_key.php, above public_html)
```

Every proxy `.php` follows the same shape (already implemented in the templates):

1. **JSON header + POST-only + same-origin guard** (Origin/Referer host must
   match the site's host — stops other sites from using the client's quota).
2. **Rate limiting**, three layers, in `sys_get_temp_dir()`: per-IP per-minute,
   per-IP per-day, and a **global daily cap** that protects the free quota. When
   a limit trips, return a friendly sentence, never a 429 with jargon.
3. **Key resolution**: `getenv` → `../gemini_api_key.php` (above public_html) →
   local `secret_config.php`. Stored as `<?php return 'AIza…';` so it's never
   served as text.
4. **Call Gemini**, walk a model array on failure, optional second-engine
   fallback (Claude Haiku) for the chat.
5. **Never surface the raw error** — log it, return a human message.

The models (free tier, walk the array): `gemini-2.5-flash-lite` (preferred) →
`gemini-2.5-flash` (fallback). Endpoint:
`POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key=…`.

---

## 1. The support chat assistant (`asistente-ia.php`)

An always-available assistant that answers visitors about the business. The
solar site calls it "Sol". Reusable for any niche.

**Server (`asistente-ia.php.template`, ready to adapt):** the persona +
knowledge live in `knowledge.php` (the system instruction). It receives
`{message, history[]}`, sends the last few turns to Gemini with the system
prompt, and returns `{reply}`. `generationConfig`: `temperature 0.4`,
`maxOutputTokens 700`, `thinkingConfig.thinkingBudget 0`, `BLOCK_ONLY_HIGH`
safety. Per-IP 8/min · 100/day, global 1200/day.

**Adapt per client:** rewrite `knowledge.php` — the persona (name, tone, "solo
responde sobre X, invita a pedir presupuesto"), and the real facts of the
business (services, prices-orientation, coverage area, FAQs). Never let it
promise things the business doesn't offer; ground it in the knowledge file.

**Front-end:** a floating chat bubble → panel. `main.js` posts to
`asistente-ia.php`, renders the reply, keeps a short history. Hardcode a
friendly opener and 2-3 suggested questions so it's alive on first paint.
Fallback if the key isn't set: the assistant says it's "configurándose" and
shows the contact form.

## 2. The document / photo reader (`lector-documento.php`)

The killer feature: the visitor uploads a photo or PDF (an electricity bill, an
invoice, an insurance policy, a prescription…) and the AI **reads it** and
returns structured data the site uses. The solar site reads the electricity
bill to pre-fill the savings calculator.

**Server (`lector-documento.php.template`):** accepts a multipart file (10 MB
cap), detects the real MIME (`finfo`), sends it inline (base64) to Gemini
multimodal with a strict extraction prompt, and returns
`{ok:true, ...campos}` or `{ok:false, reason}`. Multimodal accepts
`application/pdf`, `image/jpeg|png|webp|heic|heif`. Heavier op → lower limits
(6/min, 40/day, 400/day global).

**The extraction prompt (adapt the schema per use case):**
```
Eres un extractor de datos de <tipo de documento>. Devuelve EXCLUSIVAMENTE un
objeto JSON válido (sin texto, sin ```), con EXACTAMENTE estas claves: { … }.
Reglas: PUNTO como decimal; sin símbolos de moneda dentro de los números; si un
dato no aparece, null (NO lo inventes); normaliza <lo que aplique>.
```
Set `responseMimeType: application/json`. In PHP, strip stray fences, `json_decode`,
**validate** keys/types before use. `null` → the UI shows "—" (invariant 3).

**Honesty gate:** bills/policies contain personal data. On the free tier Google
may use content for training — say so, and tell the owner to switch to a **paid
Gemini key** before real customers upload real documents.

## 3. Interactive calculators (the savings-study pattern)

Client-side maths that turn a document + a few inputs into a personalized study
— the thing that captures leads and justifies the price. Solar example:
bill (read by feature 2) → address → draw the roof on a map → panels that fit →
annual savings + payback → email gate → the study.

Build it with **vanilla JS + the data already extracted** (no extra AI cost per
step). Maps: free **Leaflet + OpenStreetMap tiles** (no key); geocoding via the
optional `geocode.php` (Nominatim, rate-limited) or a free keyless endpoint.
The study is real arithmetic (consumption → kWp → generation → € saved →
months), labelled "estimación orientativa", never a guaranteed number. End with
the email gate → `lead.php`. Adapt the formula to the niche (a gym: usage →
plan savings; a clinic: treatment estimator).

## 4. Lead capture (`lead.php`)

Where the calculator/chat funnels. Stores `{nombre, email, telefono, datos…,
fecha}` into a **protected** file (`datos/leads.json` or a `.php`, outside
public reach, `.htaccess` Deny). Same-origin guard + simple rate limit. The
owner reads the leads; nobody else can. Say clearly on the site what the data
is used for. Optionally email the owner on each lead (leave a TODO if no mail
service).

## 5. Setup — the key, without touching code (`setup.php`)

Ship `setup-ia.php.template` as `setup.php`: a one-page form where the owner
pastes the Gemini key. It (1) rejects anything not starting with `AIza`, (2)
validates it live (`GET …/v1beta/models?key=`), (3) writes it as
`<?php return 'AIza…';` **above public_html** if possible, and (4) refuses to
show or log it. Tell the owner to delete `setup.php` after. Getting the free key:
Google AI Studio → «Crear clave de API» → paste. Restrict the key by
website/IP in Google Cloud Console — it still lives server-side.

---

## Verify (before claiming any AI feature works)

1. **Key not public:** fetch the deployed HTML + every JS file, grep for `AIza`
   and the key's first chars → zero hits. Confirm `setup.php`/key file behavior.
2. **Chat answers** on the live URL, on-topic, and degrades to the form when the
   key is unset.
3. **Reader** extracts a REAL sample document correctly; missing fields show
   "—", not invented values; oversized/wrong file → human error, not a 500.
4. **Rate limits** trip to a friendly message (hit the endpoint fast a few times).
5. **Leads** land in the protected file and `datos/` returns 403.
6. **Fallbacks**: rename the key temporarily and confirm nothing dies — human
   messages everywhere.

Only then is the AI layer done. Then the pre-deploy checklist in `08`.

---

## Cost & honesty script (say this once, plainly)

«Estas funciones usan la IA de Google en su capa gratuita, que tiene un límite
diario generoso y no cuesta nada para empezar. Si la web recibe mucho tráfico o
va a leer documentos con datos personales de clientes reales, conviene pasar a
la clave de pago de Google (es el mismo sitio, solo activar facturación), porque
en la gratuita Google puede usar el contenido para mejorar sus modelos.»
