# Populate — affiliate links → scraped → normalized → enriched → saved

This is where the site fills itself. The user pastes their own affiliate links;
you turn each into a complete, comparable record. The scraper is bundled and
proven (`scripts/amazon_extractor.py`, Scrapling + stealth browser).

**Golden rule of this step:** scrape is FACTS, enrich is JUDGMENT, and the two
never blur. A scraped fact you couldn't get is `null`; an editorial score is
labelled editorial. Inventing a spec to fill a chart is the one unforgivable
error (`SKILL.md` invariant 4).

---

## 1. Environment (install it yourself, once)

The scraper needs **Scrapling** with its stealth browser (Camoufox). Prefer the
project's official Scrapling skill if present; otherwise:

```bash
python -m pip install "scrapling[fetchers]"
scrapling install          # downloads the stealth browser (one time, ~200 MB)
```

Announce it plainly («voy a instalar la herramienta que saca los datos de tus
enlaces, tarda un par de minutos la primera vez»). If pip/venv is fiddly on the
user's machine, create a `.venv` in the project's `tools/` and install there —
never make the user do it.

## 2. The input contract (both link forms work)

The user pastes **their own Amazon affiliate links**, one per line. Accepted:

- Short: `https://amzn.to/XXXXXXX`
- Full with tag: `https://www.amazon.es/dp/ASIN?...&tag=mi-tag-21`

The scraper expands short links itself and derives `affiliate_url` (verbatim),
`affiliate_tag`, `resolved_url`, `canonical_url`, `asin`. **The tag is the
user's money — it is preserved exactly** (invariant 1). If a pasted link has no
tag, flag it back: «este enlace no lleva tu etiqueta de afiliado, ¿me pasas el
bueno?» — never ship an unmonetized button.

## 3. Scrape (one call per link)

```bash
python scripts/amazon_extractor.py "<enlace>" --download --out datos/raw/<asin>
```

It returns per product: title, brand, price, currency, rating, reviews_count,
all hi-res images, feature bullets, A+ text (`aplus_text`), the full spec/detail
table (`details`), and first-page reviews with full text. `--download` saves
the images locally. It handles Amazon's anti-bot (stealth browser, HTTP 200, no
captcha), waits for `#productTitle`, and tries multiple selectors per field so
an Amazon layout change degrades gracefully instead of crashing.

Run links **sequentially with a small pause** between them (the scraper is
polite; hammering invites blocks). For a big paste, process in small batches and
report progress. If one link fails (captcha, dead ASIN), skip it, log it, and
keep going — never abort the whole batch for one bad link.

### 3.1 The two things that decide whether the scrape works (learned the hard way)

1. **`google_search=True` is what beats Amazon's anti-bot.** The bundled scraper
   now sets it by default (referer = Google). With it off, Amazon frequently
   returns a block page with no `#productTitle` and you get an empty record. If a
   link fails, **retry it 1–2 times with a short pause** before giving up — the
   block is probabilistic and usually clears on retry.

2. **Prices/stock are shown per the visitor's COUNTRY (no proxy needed).** Amazon
   hides the price and shows "Currently unavailable" to shoppers it detects
   **outside the marketplace's country**. The signal is mainly the IP.
   - **The end user runs this on their own computer, from their own country →
     their home IP is already in-country → prices and stock come through with
     zero setup.** This is the normal, expected case. Do NOT ask the user for
     proxies or any network configuration.
   - The only time you'll see "unavailable / no price" for an item the user
     swears is in stock is when the code is running from a machine whose internet
     exit is in another country (a cloud/CI box). The fix is simply to run the
     scraper on the user's own machine in the target country — never to add
     proxies. If you truly can't (headless cloud), say so plainly and, if the
     user provides prices, use them; never fabricate stock.
   - The scraper reads the marketplace from the affiliate link (`amazon.es` →
     Spain/EUR/es). Trust that for currency and locale.

### 3.2 Dead links (404) — flag, don't invent

Some affiliate links resolve to an ASIN that returns **HTTP 404 / "Documento no
encontrado"** — the product was delisted, or the ASIN is a non-addressable
variation child. The scraper detects this and prints a `[!] ENLACE CAÍDO` warning.
When it happens: **exclude that product and tell the user exactly which link is
dead so they can send an updated one.** Never invent a product to fill the gap.
In a batch, a couple of dead links among many is normal — report them together
at the end ("estos 3 enlaces ya no existen en Amazon, ¿me pasas los nuevos?").

## 4. Normalize (raw scrape → typed schema)

The raw `details` table is free text ("Par motor: 40 Nm", "Autonomía 70 km").
Map it into the niche schema (`04-product-schema.md`):

- Match each schema spec field against the detail keys with a small synonym map
  per field (`par_motor_nm` ← "par", "torque", "Nm", "newton"). Parse the
  number, drop the unit, store typed.
- Enums: snap free text to the field's allowed values ("motor en el buje
  trasero" → `tipo_motor: "trasero"`).
- Booleans: presence/keywords ("batería extraíble" → `bateria_extraible: true`).
- **Anything you can't map goes to `specs_extra` as `{label: value}`** — kept,
  shown on the ficha, never force-cast into a numeric field.
- **Missing a spec? Complete it from an authoritative source first.** Amazon's
  detail table is often incomplete or self-contradictory (it may list a wheel
  size that clashes with the bullets, or omit torque/charge time). Before leaving
  a field empty, do a quick web search and take the value from the
  **manufacturer's official page or a reputable retailer/spec site for that exact
  model** — that is *completing* the record from real evidence, not inventing it.
  When two scraped sources conflict, prefer the manufacturer's figure and move on.
  Only if a value truly can't be found anywhere does it stay `null` (UI shows
  "—"). Never guess a number just to fill a chart or a comparator row.
- Images: convert the downloaded originals to WebP into `assets/img/`
  (`<id>-1.webp`…), strip Amazon URLs from the record (host locally so the site
  doesn't hotlink Amazon's CDN).
- Price: store with `precio_fecha` (today) — it's a snapshot (invariant 6).

## 5. Enrich (compute scores + write editorial)

Now the judgment layer, grounded in what was scraped:

- **Scores (Group D):** compute each 0-10 axis from the underlying specs across
  the catalog's current min/max (`04` §D), nudged ±1 by editorial sense.
  **Recompute ALL products' scores** whenever the catalog changes, so they stay
  comparable.
- **Editorial (Group E):** from the feature bullets, A+ text and reviews, write
  `description` (2-4 sentences), `cuerpo_editorial` (a few real paragraphs),
  `pros`/`contras` (grounded in specs + reviews), `ideal_para`, and
  `resenas_resumen` (summarize the scraped reviews — don't invent new ones).
- `rango_precio` from the price relative to the catalog.
- Keep it honest: editorial is written from evidence, not marketing fantasy. If
  reviews are thin, say the reviews are thin.

## 6. Save + rebuild

Write each record into the data store (`03-data-store.md` — `productos.json` by
default). Then:

- Fichas, comparator, category pages and charts **regenerate from the data** —
  no page is hand-edited (invariant 2).
- Bump `?v=YYYYMMDD` on assets and re-verify the comparator and one ficha in the
  http preview.
- **Report the outcome honestly:** N products added, which fields are `null` and
  worth a human check, any link that failed and why, any price that looked
  suspicious. Never present a half-scraped record as complete.

## 7. Adding more later

Same pipeline, incrementally: new links → scrape → normalize → enrich →
**recompute all scores** (the min/max may have moved) → save. The user can also
paste links for a different niche in a multi-niche shop — keep each niche's
schema and only compare within a niche.

## Failure modes to handle out loud

| Symptom | Do |
|---|---|
| Captcha / block on a link | **Retry 1–2× with a pause** (`google_search=True` + retry clears most); if it persists, skip, log, tell the user |
| Link resolves but page is 404 / "Documento no encontrado" | Dead/delisted ASIN — **exclude it and tell the user which link to replace**; never invent a product |
| Product shows "unavailable / no price" but user says it's in stock | The machine's internet exit is outside the marketplace country — run the scraper on the user's own machine in that country; **no proxies** (see §3.1) |
| No affiliate tag in link | Flag it, ask for the tagged link, don't ship it |
| Spec table sparse or contradictory | Complete from the manufacturer/retailer page (§4); `null` only what's truly unfindable; say so |
| Price missing (genuinely out of stock) | `null` + "consultar en Amazon", never invent |
| Images fail to download | Ship with a placeholder, note it, retry on request |
| Non-Amazon link pasted | Say this skill scrapes Amazon; offer manual entry |
