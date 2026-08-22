# The Server Proxy — the key, the credits, the endpoints

Everything that must not be trusted to the browser lives here: the AI keys
(Claude + Gemini), the credit ledger, the sessions. It runs **on the Hostinger
plan itself** — no VPS needed.

---

## 1. Two paths (pick one, don't mix)

| | **PHP** (default) | **Node/Express** (alternative) |
|---|---|---|
| Deploy | Same zip as the site, via `hosting_deployStaticWebsite` | `hosting_createNodeJSBuildFromArchiveV1` |
| Build step | None | Yes (server-side, automatic) |
| Gemini calls | REST + cURL (`05` §1) | Official SDK `@google/genai` |
| Works on | Every Hostinger plan | Plans with Node (18/20/22/24) |
| Choose it when | Default. Fewer moving parts, one deploy | The archetype needs heavy processing, streaming or npm libraries |

**Default to PHP.** One deploy, no build logs to debug, and the REST call is
six lines. Switch to Node only for a concrete reason, and say why.

## 2. Folder layout — and the one that must live OUTSIDE it

```
home/uXXXX/domains/<dominio>/
├── anonimiza_datos/        ← ⚠️ OUTSIDE public_html — SURVIVES every deploy
│   └── usuarios.json       ←    accounts, credits, sessions live HERE
├── anthropic_api_key.php   ← <?php return 'sk-ant-…';   (also outside)
├── gemini_api_key.php      ← <?php return 'AIza…';       (optional fallback)
└── public_html/            ← everything below is WIPED and replaced on deploy
    ├── index.html  app.html  cuenta.html  styles.css  main.js  auth.js …
    ├── .htaccess                    ← from template
    ├── setup.php                    ← one-time key setup (delete after)
    ├── lib/vendor/…                 ← pinned libs (pdfjs, tesseract…)
    ├── api/
    │   ├── index.php  gemini.php     ← router + the only file that reads keys
    │   └── .htaccess                 ← protects api internals
    └── datos/                        ← only a fallback DB location; .htaccess deny
        └── .htaccess
```

**🔴 The most dangerous bug in this skill: `hosting_deployStaticWebsite` replaces
the ENTIRE `public_html`.** Any database inside it (even in `datos/`) is deleted
on the next publish — every registered customer, every credit balance, gone. So
the store lives **one level above `public_html`**, in a folder the deploy never
touches. Resolve its path server-side and create it on first use:

```php
function ruta_db() {
  $fuera = dirname(dirname(__DIR__)) . '/anonimiza_datos';   // from api/ → above public_html
  if (is_dir($fuera) || @mkdir($fuera, 0750, true)) {
    if (is_writable($fuera)) return $fuera . '/usuarios.json';
  }
  return __DIR__ . '/../datos/usuarios.json';                 // last-resort fallback
}
```
**Verify it:** create the test account, redeploy, confirm it still logs in. If it
doesn't, the DB is inside `public_html` — fix before doing anything else.

**Key storage (`05` §10):** each key is `<?php return 'sk-ant-…';` — so even if
the server stops parsing PHP it is never served as text. One file per provider,
one level **above** `public_html`, with an in-`datos/` fallback. `setup.php`
writes them from the browser after validating live (auto-detecting Anthropic vs
Google), so the owner never edits a file by hand or pastes a key in chat. Tell
them to delete `setup.php` after.

Node path: `server.mjs` + `package.json` at the app root, keys in an env file
included in the deployed archive, DB written to a path above the served folder.

## 3. The AI call

Full implementation, payload shapes, engine chain, rate limits and key storage
are in `05-gemini-api.md` — the source of truth. In short: **Claude Haiku by
default** (`POST api.anthropic.com/v1/messages`), **Gemini as fallback**
(`gemini-3.5-flash → 3.6-flash → flash-latest`, 2.5 is retired), with per-IP and
global daily caps on top of the credit system. Keep the whole AI call in **one
file** (`api/gemini.php`) — the only place the keys are read.

## 4. The credit transaction (get this order right)

For every `POST /api/usar`:

```
1. Is there a session?          → no  → 401, stop
2. Compute the cost             (pages × 1, images × 1 …) — server-side ONLY
3. Are there enough credits?    → no  → 402 + upgrade payload, stop (do NOT call the AI)
4. RESERVE the credits          (subtract now, write to disk with a lock)
5. Call the AI                  (Claude → Gemini fallback, with retries)
6a. Success → log it in history, return result
6b. Failure → REFUND the reserved credits, return a human error
```

Reserving before the call (not after) is what stops two simultaneous requests
from spending credits the user doesn't have. Never trust a cost sent by the
browser — recompute it server-side. When the whole page has no text to send
(a blank/again-empty OCR), refund and return an empty result instead of charging
for nothing.

## 5. Handling uploads

- Enforce limits server-side: file type (real MIME, not the extension), size
  (default 20 MB, 50 MB max for PDFs), page count. Reject with a human message.
- Store temporary files in `datos/tmp/` with a random name, and **delete them
  in a `finally`** — success or failure. Never leave user documents on disk.
- Never write anything the user uploaded into a public folder. Results too:
  return them in the response body (base64/binary), don't park them on a
  guessable URL.
- PHP defaults (`upload_max_filesize`, `post_max_size`, `max_execution_time`)
  are usually too small — set them in `.htaccess`/`.user.ini` and verify with a
  real large file before claiming done.

## 6. Deploying it

**PHP:** it ships in the same zip as the site (`13-hostinger-deploy.md`). Two
extra rules: include `api/` and `datos/`, and confirm after deploy that
`https://<dominio>/datos/config.php` returns **403**, not the file. If it
doesn't, stop and fix before doing anything else.

**Node:** archive the source WITHOUT `node_modules` (≤ 50 MB), deploy with
`hosting_createNodeJSBuildFromArchiveV1` (`app_type: "express"`, pick a Node
version), then poll `hosting_listJsDeployments` until `completed` and read
`hosting_showJsDeploymentLogs` if it fails. Don't declare success on "uploaded"
— wait for the build.

## 7. Verify before claiming (do all five)

1. **No key is public:** fetch the deployed `index.html` and every JS file and
   grep for `sk-ant`, `AIza`, `AQ.` and the key's first characters. Zero hits.
   Confirm `/datos/` is 403 and the DB path above `public_html` returns 404 (not
   even reachable by URL).
2. **The credits are real:** call the AI endpoint twice from the browser and
   watch the counter drop server-side; then edit the counter in DevTools and
   confirm the server ignores it.
3. **The refund works:** force a failure (temporarily remove/rename the key) and
   confirm the credits come back.
4. **The limits hold:** upload something oversized and confirm a human error,
   not a 500 or a hang.
5. **Accounts survive a deploy:** create the test account, redeploy the site,
   log in again. If it fails, the DB is inside `public_html` (§2) — fix it.

Only then is the server done.
