# The SaaS Catalog — 11 archetypes, 4 AI patterns

Every archetype here is a **subscription SaaS powered by Gemini**: the user
uploads something, the AI does the valuable work, and they download or view a
result. The AI runs **server-side through the proxy** (`15-backend-proxy.md`) —
never from the browser, because the API key must stay secret and every call
costs money.

**How to use this file:** match the ask to an archetype → note its pattern →
open the recipe (`06-recipes-documents.md` or `11-recipes-images.md`). New
ideas map to the closest pattern and reuse its machinery. The catalog is a
launchpad, not a fence.

---

## The 4 AI patterns

| Pattern | What the AI does | Output | Recipe |
|---|---|---|---|
| **A. Read → extract** | Reads a document, returns structured data | Table / Excel / filled form | `06` |
| **B. Read → judge** | Reads and analyzes with expert criteria | Report / verdict / summary | `06` |
| **C. Read → locate** | Reads AND returns WHERE things are (bounding boxes) | Annotated / edited document | `06` |
| **D. See → generate** | Takes an image, generates new images | New image(s) | `11` |

Pattern C is the most differentiated (and the hardest): it's what lets the app
edit the original document instead of just talking about it.

---

## The 11 archetypes

### Pattern C — read and locate

**1. Censurar PDFs · `censurar-pdf`** ⭐ *reference implementation*
Upload a contract/invoice/payslip → the AI finds personal data (names, IDs,
phones, emails, bank accounts, addresses) **and their position** → the app
paints black boxes over them → the user toggles each one on/off → downloads the
redacted PDF. Buyers: gestorías, law firms, HR — legally required to anonymize,
doing it by hand today. Credits: 1 per page. See `06` for the full pipeline
(this is the archetype every other one borrows machinery from).

### Pattern A — read and extract

**2. Facturas y tickets a Excel · `facturas-excel`**
Photos or PDFs of invoices/receipts → structured table (date, supplier, tax ID,
base, VAT, total, category) → export to Excel/CSV. Buyers: gestorías and any
business that files taxes quarterly. Recurring by definition. Credits: 1 per
document. Killer extra: batch upload of 50 files at once.

**3. Apuntes manuscritos a resúmenes · `apuntes-resumen`**
Photos of handwritten notes → clean digital text → structured summary, outline,
flashcards. Buyers: students (subscribed all school year), professionals with
notebooks. Credits: 1 per photo. Extra: export to PDF/Markdown, and a
"quiz me" mode built from the same content.

**4. Traducir documentos manteniendo formato · `traducir-documentos`**
Upload a PDF/DOCX → translated document with the layout intact. Buyers:
exporters, agencies, anyone with recurring documentation. Credits: 1 per page.
Honest limit: complex layouts degrade — see `06` for the two strategies
(text-layer replacement vs. reflowed rebuild) and when to use each.

### Pattern B — read and judge

**5. Analizador de contratos · `analizar-contratos`**
Upload a contract → abusive clauses flagged by severity, obligations, dates,
penalties, plain-language summary, and questions to ask before signing.
Buyers: freelancers and small businesses. Credits: 1 per contract.
**Mandatory disclaimer** in the UI: informational, not legal advice.

**6. Calorías y macros desde la foto del plato · `macros-foto`**
Photo of a meal → identified foods, portions, calories and macros → daily log
with history. Buyers: consumers, daily use — the best retention of the catalog.
Credits: 1 per photo. Honest limit: estimates, not lab measurements. Extras:
daily goal, weekly chart, local history.

### Pattern D — see and generate

**7. Fotos de producto profesionales · `fotos-producto`**
Amateur product photo → clean studio shots and lifestyle scenes, consistent
across the catalog. Buyers: ecommerce, constantly adding products. Credits: 1
per generated image. Extras: preset backgrounds, batch mode, marketplace-ready
sizes.

**8. Foto en distintos estilos · `foto-estilos`**
A portrait/photo → the same photo in several artistic styles. Buyers: mass
consumer — volume game, works with a cheap tier. Credits: 1 per image. Extras:
style gallery, side-by-side comparison, shareable result card.

**9. Diseño de interiores desde foto · `diseno-interiores`**
Photo of a room → the same room redecorated in several styles (nordic,
industrial, japandi…), keeping the architecture. Buyers: renovation companies,
decorators, homeowners deciding. Credits: 1 per variant. Extra: "keep the
furniture, change the walls" mode via prompt constraints.

**10. Restaurar y colorear fotos antiguas · `restaurar-fotos`**
Damaged/black-and-white photos → restored and colorized. Buyers: consumers
(high emotional value, shares itself), photo studios. Credits: 1 per photo.
Extras: before/after slider, high-res download as the paid perk.

**11. Mockups de producto · `mockups-producto`**
A design/logo → applied onto t-shirts, mugs, packaging, signage. Buyers:
brands, print-on-demand sellers, designers. Credits: 1 per mockup. Extras:
mockup pack (10 formats in one go) as a premium action.

---

## Choosing (🎯 Recommend)

Weigh in this order:

1. **Does the buyer have the problem every month?** Gestorías (2), students
   (3), ecommerce (7) yes; one-off tools no. Subscription needs recurrence.
2. **Would they pay 20-50 €/month?** B2B (1, 2, 4, 5, 7) sustains higher
   prices; consumer (6, 8, 10) needs volume and a cheaper tier.
3. **Cost per use.** Image generation (7-11) costs real money per image —
   price the plan above cost (`05-gemini-api.md` has the numbers). Text/vision
   archetypes are cents.
4. **Demo appeal.** 1, 9, 10, 11 are spectacular on camera; 2 and 5 are boring
   to watch but easier to sell.

Recommend ONE with a one-line reason and offer to build it. Don't recite the
catalog.

## When the ask isn't in the catalog

Map it to a pattern and build it — the machinery is the same. Only push back if
the idea needs something Gemini can't do (real-time video, guaranteed-accurate
legal/medical judgments, actions on third-party systems). Then say so plainly
and propose the closest thing that works.
