# Recipes — Patterns A, B, C: documents

Six archetypes that read documents. All AI calls go through the proxy
(`15-backend-proxy.md`); models, limits and costs in `05-gemini-api.md`.
Front-end libraries are pinned in `14-library-pinning.md`.

**Shared machinery:** dropzone with `data-state` (`03`), cost shown before
acting, server-side credit reservation, temporary files deleted in a `finally`.

---

## C.1 · `censurar-pdf` — the reference implementation

The most complex pipeline in the skill; every other archetype is a subset.
**This is the v2 rewrite — the whole architecture was proven end to end in
production and it replaces the old "ask the AI for boxes" approach, which failed
on real documents (misplaced boxes → visible personal data).**

**The golden principle: the AI never gives coordinates.** The browser knows
*where* the text is (from the PDF's own text layer, or from local OCR). The AI
only says *which* text is personal data. This means:
- Positioning is deterministic and exact — no misplaced boxes.
- Only **text** is sent to the AI, never the page image → cheaper, more private.
- Claude (the default engine) works perfectly, because it only reads text.

**The flow (who does what):**

```
1. Browser → opens the PDF with pdf.js (the file itself never uploads)
2. Browser → per page, gets text + position:
             · digital PDF  → pdf.js getTextContent()      (no OCR, instant)
             · scanned page → Tesseract.js OCR, in-browser  (words + boxes)
3. Browser → sends ONLY the page's plain text to the server   (1 credit/page)
4. Server  → Claude (fallback Gemini): "which fragments are personal data?"
             returns [{ tipo, texto }]  — no coordinates
5. Browser → finds each returned text in its own text layer and draws a black
             box over EVERY occurrence; user toggles each, or draws own boxes
6. Browser → rebuilds each page as an image with the boxes burned in, and
             exports the PDF   (100% local)
```

**Extracting text + position (browser):**
- Digital PDF: `page.getTextContent()` → items with transforms; convert each to
  a chunk `{str, x0,y0,x1,y1}` in 0-1 fractions of the page. Reconstruct the
  page's plain text by joining chunks, inserting a newline when the Y changes —
  that reconstructed text is what the AI sees, so the literal it returns can be
  found again.
- **Scan detection:** if a page yields almost no text (say < 12 chars / < 2
  chunks) it's an image → run OCR.
- OCR: Tesseract.js on the rendered page image → `data.words` with `bbox`
  (pixels); divide by canvas width/height to get the same 0-1 chunks. Setup and
  the fiddly self-hosting config are in `14-library-pinning.md` §Tesseract —
  **read it, the worker hangs silently if `corePath` points at a folder.**

**The AI call (per page) — text in, `{tipo,texto}` out:**

```
Engine: Claude Haiku (default) → Gemini (fallback).  See 05 §1/§3b.
        ⚠️ Personal data — use a PAID tier before real customers (05 §3).
System: "You anonymise documents. You receive a page's text and locate the
         personal data of natural persons. You return only JSON."
Prompt rules that matter:
 - types (exact): nombre, dni, telefono, email, direccion, iban,
   fecha_nacimiento, cups, matricula.   (CUPS = the ES… electricity/gas supply
   point code — it IS personal data on Spanish utility bills; users ask for it.)
 - "texto" = the LITERAL fragment, copied char-for-char, COMPLETE (whole address,
   whole IBAN) — it will be searched in the page to redact it.
 - Do NOT mark the issuer company's own data (its CIF, registered address,
   customer-service phone/email). Only natural persons.
 - Do NOT mark amounts, invoice/contract/reference numbers, non-birth dates.
 - No data → { "detecciones": [] }. Never invent.
Schema: { detecciones: [ { tipo:string, texto:string } ] }
```

Server-side, validate: keep only allowed types, drop empties, **de-duplicate**
by `tipo|lowercase(texto)` (the model repeats), cap at ~200.

**Anchoring the detections (browser):** for each `{tipo,texto}` returned,
normalise (lowercase, strip accents, collapse spaces) and search the page's
chunk stream for **every** occurrence — build a black box per occurrence (a
match can span several chunks → one rect per chunk touched). If the text isn't
found (OCR read it differently, or the AI reworded it), list it as **"no
localizada"**, starting OFF, so the user knows to place it by hand. Marking all
occurrences is correct for anonymisation: the same name three times gets covered
three times.

**Manual boxes (non-negotiable UX — invariant 11):** a «Tapar una zona a mano»
toggle lets the user drag a rectangle over anything the AI missed. Store it as a
detection `{tipo:'manual', recuadros:[{x0,y0,x1,y1}]}`, listed with a delete
button, burned into the PDF like the rest. Support mouse AND touch (gestorías
use tablets).

**Burning the redaction (browser):** the honest, verified way — for each page,
draw the rendered page image onto a canvas, fill every active box with opaque
black, `toDataURL('image/jpeg')`, and add THAT image to a new PDF (jsPDF, one
image per page). The rebuilt PDF has **no text objects at all**, so nothing can
be selected, searched or copied. This is what makes the redaction real.

- Render pages with pdf.js using `page.render({canvas, viewport, intent:'print'})`
  — the v6 API; `canvasContext` hangs forever and `intent:'print'` is the only
  mode that keeps going in a backgrounded tab (`14` / `04`).
- Consequence to state honestly in the UI: the exported PDF **loses selectable
  text** (can't be searched or copy-pasted) and weighs more. It looks and prints
  identical. That is exactly what an anonymised document should be.

**Verify the redaction is real before claiming it (do this in testing):** open
the exported PDF, extract its text — must be **zero characters** — and grep the
raw bytes for a couple of the redacted values — **zero hits**. Only then call it
irreversible.

**Honest limits for the UI:** handwriting and bad scans reduce OCR accuracy (an
email with odd characters can slip through — that's what the manual box is for);
the user must review before downloading; recommend a final visual check. Say it
plainly — this archetype's buyers are liable if it fails.

## A.1 · `facturas-excel`

Per document (PDF or photo): one AI call with a strict schema —
`{ fecha, proveedor, nif, base, iva_porcentaje, iva_importe, total, moneda, categoria, numero_factura }`
plus `confianza` per field. Send the PDF natively (no rasterizing needed here).

- **Batch is the feature**: a queue with per-file status, processed with a
  concurrency of 2-3, partial results visible as they land. One credit per
  document, reserved per document (so a failure only refunds that one).
- Editable results table before export (the user fixes what the AI got wrong —
  highlight low-confidence cells in amber).
- Export: CSV by default (Excel opens it, zero dependencies) and XLSX via
  SheetJS if the user wants formatting. Include a totals row.
- Sanity checks in code, not by the AI: does `base + iva = total`? Is the date
  parseable? Flag mismatches instead of exporting silently wrong numbers.

## A.2 · `apuntes-resumen`

Photos of handwriting → one call per photo with schema
`{ transcripcion, resumen, esquema:[…], conceptos_clave:[{termino, definicion}], preguntas:[{p, r}] }`.
Prompt must say: preserve the original language, keep formulas in LaTeX,
mark unreadable words as `[?]` rather than inventing them (this instruction
matters — invented content is the failure mode students notice).

Multi-photo sessions: send up to ~10 images in one call so the summary spans
the whole set. Outputs: copy, PDF (jsPDF), Markdown. The flashcards/quiz mode
is free content from the same response — build it, it's what drives retention.

## B.1 · `analizar-contratos`

Send the PDF natively. Schema:
`{ resumen_ejecutivo, partes:[…], objeto, duracion, importes:[…], clausulas:[{titulo, texto, riesgo:"alto|medio|bajo", explicacion, recomendacion}], fechas_clave:[…], preguntas_antes_de_firmar:[…] }`.

UI: risk-sorted list, each clause expandable to its literal text, and a
prominent **«Esto es información, no asesoramiento legal»** notice — visible
always, not in a footer. Prompt must forbid inventing clauses that aren't in
the document and require quoting the literal text of each finding.

Extra that sells: «compara dos versiones» — send both PDFs in one call and ask
for what changed and what it implies.

## A.3 · `traducir-documentos`

Two strategies. Pick by document type and TELL the user which one ran:

- **Reflowed rebuild (default, robust):** extract text per page, translate with
  structure hints (headings, lists, tables as markdown), rebuild a clean PDF
  with jsPDF. Layout is *similar*, not identical. Works everywhere.
- **Text-layer replacement (only for simple, text-based PDFs):** pdf-lib
  replaces text in place keeping the page design. Breaks on complex layouts and
  fails on scanned documents — detect and fall back to the first strategy.

Always: preserve numbers, names and units verbatim (say so in the prompt),
keep a glossary the user can pin for consistent terminology across documents,
1 credit per page, and a side-by-side preview before download.

## B.2 · `macros-foto`

One photo → `{ alimentos:[{nombre, porcion_g, calorias, proteina, carbos, grasa, confianza}], total:{…}, notas }`.
Prompt: estimate portions from visual cues, list assumptions, never claim
precision. UI: editable portions (recalculating locally), daily log in
localStorage plus server history, weekly chart, goal tracking. Mandatory
honesty line: «estimación aproximada, no sustituye a un análisis nutricional».
The cheapest archetype to run — be generous with the free tier.

---

## Definition of done (documents)

Run each archetype's happy path with a REAL document (not a synthetic one),
driving a real browser on the deployed site or the http preview: a scanned
invoice, a genuine contract, a photo of actual handwriting. Then force one
failure and confirm the credit came back. Then the product checklist in `03` §6.

For `censurar-pdf` specifically, all of these must pass before you hand it over:
- A **digital PDF** (e.g. a utility bill) → detects names/DNI/IBAN/**CUPS**/
  address, ignores the issuer company's data, boxes land exactly on the text.
- A **scanned page** → OCR runs in-browser, boxes land on the words.
- **Manual box** → drag one, it burns into the export.
- **Real redaction** → exported PDF has zero selectable text and zero raw-byte
  hits for the redacted values.
- A **redeploy** in the middle does not wipe the test account (`15` §4).
