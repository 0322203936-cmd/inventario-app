# Library Pinning — versions, vendoring, the ESM bridge

Verified July 2026. **Do not improvise other libraries or newer versions
mid-build.** Upgrades are decided here first, then in the recipes.

Note how few libraries this skill needs: **Gemini reads documents and images
natively**, so there is no OCR engine, no vision library and no WASM monster in
the frontend. The browser only assembles and exports files.

---

## 1. Vendoring policy

Vendor at build time, same-origin at runtime.
`python scripts/descargar-librerias.py <arquetipo>` writes the pinned files
into `lib/vendor/`. No CDN hot-links in shipped HTML. Exceptions: Google Fonts
(`<link>`, per `01`) and nothing else — the AI now lives on the server, so the
frontend has no remote dependencies at all.

Server side: PHP needs **no dependencies** (cURL is built in). The Node
alternative uses `@google/genai@2.13.0` plus the payment SDK when going live
(`@polar-sh/sdk`, `stripe`, `@paddle/paddle-node-sdk` or `mercadopago`) —
installed on the server at build time, never shipped to the browser.

## 2. The pin table (frontend)

| Library | Version | File → destination | Global | License | Used by |
|---|---|---|---|---|---|
| pdf-lib | 1.17.1 | `npm/pdf-lib@1.17.1/dist/pdf-lib.min.js` → `lib/vendor/pdf-lib.min.js` | `PDFLib` | MIT | traducir (text-layer) |
| pdfjs-dist | 6.1.200 | `build/pdf.min.mjs` + `build/pdf.worker.min.mjs` → `lib/vendor/pdfjs/` — **API and worker must be the same version** | (ESM) | Apache-2.0 | censurar-pdf, herramientas PDF |
| jsPDF | 4.2.1 | `dist/jspdf.umd.min.js` → `lib/vendor/jspdf.umd.min.js` | `window.jspdf` | MIT | censurar-pdf export, apuntes, traducir |
| jspdf-autotable | 5.x | `dist/jspdf.plugin.autotable.min.js` → `lib/vendor/` | (plugin) | MIT | facturas, tablas |
| SheetJS (xlsx) | 0.20.3 | `https://cdn.sheetjs.com/xlsx-0.20.3/package/dist/xlsx.full.min.js` → `lib/vendor/xlsx.full.min.js` — ⚠️ **not on npm/jsdelivr**: SheetJS moved to its own CDN, the npm package is frozen at 0.18.5 | `XLSX` | Apache-2.0 | facturas-excel |
| JSZip | 3.10.1 | `dist/jszip.min.js` → `lib/vendor/jszip.min.js` | `JSZip` | MIT | batch downloads, mockups pack |
| Tesseract.js | 5.1.1 | 5 files (see §Tesseract) → `lib/vendor/tesseract/` | `Tesseract` | Apache-2.0 | censurar-pdf (scans only) |

CSV export needs no library — build the string and `Blob` it. Prefer CSV as
the default export and offer XLSX only when formatting matters.

**pdf.js 6 render — the two gotchas (cost a whole session):**
```js
// ✅ v6 API: pass `canvas`, and intent:'print'
await page.render({ canvas: myCanvas, viewport: vp, intent: "print" }).promise;
// ❌ page.render({ canvasContext: ctx, viewport: vp })  → hangs forever in v6
```
`intent:'print'` is also the ONLY mode that keeps rendering when the tab is
backgrounded (`display` waits on `requestAnimationFrame`, which a hidden tab
never fires — a 40-page job freezes if the user switches tabs). Always render
onto a fresh `<canvas>` element, never an `OffscreenCanvas` (same rAF trap).

## 3. The ESM bridge

The page skeleton stays classic `<script defer>` + IIFE (`01`). ESM-only
libraries (pdf.js) load through **dynamic `import()` from inside a classic
script**, lazily, wrapped in `safe()`:

```js
const pdfjsLib = await import("./lib/vendor/pdfjs/pdf.min.mjs");
pdfjsLib.GlobalWorkerOptions.workerSrc = "lib/vendor/pdfjs/pdf.worker.min.mjs";
```

Consequences: preview over `python -m http.server`, never `file://`. The
shipped `.htaccess` already serves `.mjs` and `.wasm` with the right types —
keep those lines.

## 3b. Tesseract.js 5.1.1 — self-hosted OCR (scans only, lazy)

Only `censurar-pdf` needs it, only for scanned pages, and it's downloaded the
first time a scan appears. Vendor **five** files into `lib/vendor/tesseract/`
(from jsDelivr):

```
tesseract.js@5.1.1/dist/tesseract.min.js           → tesseract.min.js
tesseract.js@5.1.1/dist/worker.min.js              → worker.min.js
tesseract.js-core@5.1.1/tesseract-core-simd.wasm.js → tesseract-core-simd.wasm.js
tesseract.js-core@5.1.1/tesseract-core-simd.wasm    → tesseract-core-simd.wasm   ⚠️ the BINARY
@tesseract.js-data/spa@1.0.0/4.0.0_best_int/spa.traineddata.gz → lang/spa.traineddata.gz
```

⚠️ The `.wasm.js` is Emscripten **glue that fetches the `.wasm` binary** (~3.4 MB)
— it's easy to grab only the `.wasm.js` and then the worker hangs. Grab both.

Loading it (config learned the hard way — every deviation hangs silently):
```js
const w = await Tesseract.createWorker("spa", 1, {
  workerPath:    origin + "/lib/vendor/tesseract/worker.min.js",
  // corePath MUST be the exact FILE, not the folder. Folder → worker hangs at
  // "loading tesseract core" with no error.
  corePath:      origin + "/lib/vendor/tesseract/tesseract-core-simd.wasm.js",
  langPath:      origin + "/lib/vendor/tesseract/lang/",
  gzip:          true,
  workerBlobURL: false   // blob worker can't resolve relative paths → hangs
});
const { data } = await w.recognize(canvasOrDataURL);  // data.words[].bbox in px
```
Serve `.wasm` as `application/wasm` and the `.gz` **without** `Content-Encoding`
(the `.htaccess` template already does; don't let mod_deflate touch the `.gz`).

## 4. Server pins

| Piece | Pin | Notes |
|---|---|---|
| Claude (default) | `POST https://api.anthropic.com/v1/messages`, `claude-haiku-4-5`, header `anthropic-version: 2023-06-01` | text engine; full call in `05` §1 |
| Gemini REST (fallback) | `POST …/v1beta/models/{model}:generateContent?key=…` | shapes in `05` §2 |
| Gemini models (fallback text) | `gemini-3.5-flash` → `gemini-3.6-flash` → `gemini-flash-latest` | ordered array; **2.5 family is retired for new keys**; NO `thinkingBudget` |
| Gemini models (paid, images) | `gemini-3.1-flash-image` | billing required; `05` §9 |
| Node SDK (alt.) | `@google/genai@2.13.0` | ESM only. **Never** `@google/generative-ai` (deprecated) |
| PHP | none | cURL + `json_encode` are enough |

## 5. Banned

| What | Why |
|---|---|
| `@google/generative-ai` | deprecated Nov 2025 — use `@google/genai` |
| Gemini `gemini-2.5-*` models | retired for new keys — HTTP 404 (`05` §2) |
| `thinkingConfig.thinkingBudget` on Gemini | current *-lite models HTTP 400 on it |
| Asking any engine for bounding-box coordinates in `censurar-pdf` | misplaced boxes leak data — position locally (`06`) |
| Any client-side AI SDK | would expose the key; all AI is server-side |
| Free-tier Gemini for real personal-data users | content is used for training (`05` §3) |

## 6. `scripts/descargar-librerias.py`

```
python scripts/descargar-librerias.py --list
python scripts/descargar-librerias.py censurar-pdf
python scripts/descargar-librerias.py facturas-excel apuntes-resumen
```

Run from the project root. Idempotent (skips existing files). If a URL 404s
someday, that's an upgrade decision for this file — never improvise a
replacement mid-build.
