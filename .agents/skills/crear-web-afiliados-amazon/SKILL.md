---
name: crear-web-afiliados-amazon
description: Build a data-driven Amazon affiliate website on Hostinger, guided end to end. (a) CONNECT the Hostinger account to Claude Code. (b) BUILD a premium comparison/blog affiliate site for ANY product niche (e-bikes, monitors, robot vacuums, multi-niche shops): a normalized product database and auto-generated pages with spec tables, radar-score panels, editorial text, pros/cons, reviews, a side-by-side comparator, category and buying-guide pages. (c) POPULATE it - the user pastes their Amazon affiliate links, the bundled scraper extracts each product, and you normalize and enrich it into the database so the site fills itself. (d) PUBLISH it to Hostinger and add features on request. Use whenever the user wants an affiliate site, an Amazon comparison or blog site, a product-recommendation web, or to add products from their affiliate links. Triggers include crea una web de afiliados, web de comparativas de amazon, blog de afiliados, anade estos productos con mis enlaces, and their English equivalents.
---

# Affiliate Studio · v2 — connect · build · populate · publish

Four **independent capabilities** for building a **data-driven Amazon affiliate
site**: not a flat list of product cards, but a comparison engine where every
product is a normalized record, and pages (fichas, comparators, category
guides, charts) are **generated from that data**. Same studio logic as the
sibling skills — read which door the person walked through, do that, verify it,
stop.

- 🔌 **Connect** the Hostinger account to Claude.
- 🏗️ **Build** the affiliate site: database schema + generated pages for a niche.
- 📥 **Populate** it: affiliate links → scraped, normalized, enriched records.
- 🚀 **Publish** it live to Hostinger (and add features on request).

**v2 — what a real build taught us (read these, they save hours):**
- The scraper now sets **`google_search=True`** by default — that single flag is
  what beats Amazon's anti-bot. Retry a blocked link 1–2× before giving up.
- **Prices/stock are per the shopper's country, and this needs NO proxy:** the
  user runs it from their own machine in their own country and prices come
  through. Only a foreign/cloud IP hides them. Details in `06-populate-pipeline.md`
  §3.1. **Never ask the user for proxies.**
- **Build pages with a generator script** (`tools/build_site.py`) — one static
  HTML per record, core facts baked in, JS enriches. It's the only clean way to
  get data-driven + works-without-JS + SEO. See `05-pages-and-features.md`.
- New **six real gotchas** (giant icons, nav-button contrast, clipped overhang
  badges, IntersectionObserver-in-hidden-tabs, local-preview caching, map wheel
  zoom): `04-critical-gotchas.md` TIER E.
- New optional **range map** (reachable-area isochrones, keyless, ida/vuelta
  toggle): `14-mapa-autonomia.md`.
- **Bump the `?v=` cache-buster on every build** (not just deploys), or you'll
  chase phantom bugs against stale local files.

**What makes this different from the micro-SaaS / SaaS skills:** there is no AI
proxy and no accounts. The value is a **normalized product database** and the
rich, comparable pages built on top of it. The reference site this improves on
(a Horizons/PocketBase e-bike site) reached maybe 30% of the target quality and
30% of the target completeness — this skill aims for the other 70%: more pages,
richer fichas, real charts, cleaner code, better design.

---

## THE GOLDEN RULE: do only what was asked, then stop

- *"conéctame Hostinger"* → only connect and verify.
- *"hazme una web de afiliados de X"* → only build the site + empty database.
  Don't scrape, don't publish.
- *"añade estos productos: <links>"* → only populate (scrape → normalize →
  enrich → save). Don't redesign.
- *"publícala"* → only publish.

At the end offer **one** sentence naming the next step («¿la lleno con tus
enlaces de afiliado?»). Never start it unprompted. Read the state each time:
connected? project exists? database empty or full? published?

---

## Route the request → capability

| What they say / the situation | Capability | Primary ref |
|---|---|---|
| "conéctame Hostinger", "vincula mi hosting" | 🔌 **Connect** | `12-hostinger-connect.md` |
| "hazme una web de afiliados de <nicho>", no project yet | 🏗️ **Build** | `02` → `03` → `05` |
| "añade estos productos", pastes affiliate links | 📥 **Populate** | `06-populate-pipeline.md` |
| Project exists: "cambia…", "añade una feature", "otra sección" | ✏️ **Edit** | existing files + invariants |
| "publícala", "súbela" | 🚀 **Publish** | `13-hostinger-deploy.md` |
| "¿qué nicho me recomiendas?", "dame ideas" | 🎯 **Recommend** | `02-niche-and-architecture.md` |
| "no funciona", "se ve vieja", "el comparador falla" | ✅ **Verify** | `08`, `10`, `04` |

The natural full arc is Build → Populate → Publish, but each runs alone. Only
chain when the user asks for the whole thing at once.

---

## The build → populate flow (the heart of this skill)

The reference site had it backwards: it shipped hardcoded product cards. Here
the **data model comes first, pages are generated from it, and the data arrives
later** from the user's affiliate links. That order is what makes it scale to
any product and any number of items.

### 🏗️ Build (structure first, empty of products)
1. **Pin the niche and the schema.** Pick the product niche
   (`02-niche-and-architecture.md`); derive its normalized field set
   (`04-product-schema.md`) — commercial fields + technical specs + 0-10
   comparison scores + editorial fields. E-bikes ship as the worked example
   (35 fields); any niche follows the same shape.
2. **Choose the data store** (`03-data-store.md`): a static `productos.json` +
   `lib/manifest.js` for a site the user rarely changes, or a tiny PHP+SQLite
   admin when they want to add products without Claude. Default: JSON.
3. **Generate the pages** (`05-pages-and-features.md`): home, category pages,
   auto-generated product fichas (spec table + radar chart + editorial + pros/
   cons + reviews), the **comparator**, buying-guide/blog pages, legal pages —
   all reading from the data, none hardcoded per product.
4. Stack and code quality per `01-stack-and-conventions.md` and the invariants
   below. Copy `templates/htaccess.template` → `.htaccess`, verify, preview.
   **Ship it with 2-3 realistic sample products so the user sees it working**,
   clearly marked as samples to be replaced on populate.

### 📥 Populate (data arrives from affiliate links)
`06-populate-pipeline.md` is the full recipe. In short:
1. The user pastes **their own Amazon affiliate links** (short `amzn.to` or
   full `?tag=` URLs — both work; the tag is theirs and is preserved).
2. `scripts/amazon_extractor.py` scrapes each: title, brand, price, rating,
   reviews, all hi-res images, feature bullets, A+ text, the full spec table,
   and first-page reviews — **from the link alone**, anti-bot handled.
3. **Normalize + enrich** the raw scrape into the niche schema: map spec text
   to typed fields, compute the 0-10 scores, write the editorial description,
   pros/cons and `ideal_para`. This is the step that turns a scrape into a
   comparable record — never skip it.
4. Save into the data store. The site now works — fichas, comparator and charts
   populate themselves. Report what came through and what needs a human check
   (missing price, ambiguous spec) — never invent a spec you couldn't extract.

### 🚀 Publish & extend
Deploy per `13-hostinger-deploy.md`. Then any extra the user wants — «oferta del
día», price-history note, savings calculator, the **range map**
(`14-mapa-autonomia.md`: reachable-area isochrones with an ida/vuelta toggle,
keyless), newsletter capture — is just another feature on the same data. Build it
on request, not by reflex. Remember: **every rebuild bumps `?v=`** and the deploy
zip must include any new libs (e.g. `lib/leaflet.*`).

---

## Always-on invariants

**Communication:** the user is **non-technical**. Zero jargon — no "scraper",
"schema", "JSON", "normalize". Say "saco los datos de tus enlaces", "la ficha de
cada producto", "la base de datos de tus productos". Run every command
yourself; the only manual step is the user pasting their affiliate links.
Announce before acting, celebrate milestones (✅), never show a raw error,
verify before claiming.

**Affiliate invariants:**
1. **The affiliate link is sacred.** Preserve the user's exact affiliate URL
   and tag on every product; every «comprar» button uses it. Never strip,
   rewrite or substitute a tag. If a link arrives without a tag, flag it —
   don't silently ship an unmonetized button.
2. **Data first, pages second.** Every product page, comparator row and chart
   reads from the database. Adding a product = adding a record, never editing
   HTML. If you're hand-writing a product into a page, you're doing it wrong.
3. **Normalize everything.** Raw Amazon specs are messy ("40 Nm", "40Nm",
   "40 newton metros"). Map them to typed fields with units, or the comparator
   and charts break. Unmapped data goes in a free-text section, never faked
   into a numeric field.
4. **Never invent specs or reviews.** If the scrape didn't yield a value, it's
   `null` and the UI shows "—". Editorial text is clearly editorial; scraped
   facts stay factual. Inventing a battery capacity to fill a chart is the one
   unforgivable error here.
5. **Affiliate disclosure is legally required.** Every page states, visibly,
   that it contains affiliate links and earns a commission (Amazon's operating
   agreement demands it). Ship the disclosure + the "Amazon" trademark notice.
6. **Prices go stale.** Scraped prices are a snapshot — label them "precio
   orientativo, consúltalo en Amazon" with the capture date. Never present a
   scraped price as live.

**Web quality invariants** (shared, full detail in `04-critical-gotchas.md`):
classic `<script defer>` + IIFE + `window.__DB__`; `.htaccess` + `?v=YYYYMMDD`;
native scroll; reduced-motion gates only intrusive effects; **content hardcoded
where it must render without JS** (fichas' core facts, legal, disclosure) while
the data layer enriches (charts, comparator, filters); `safe()` around inits;
IntersectionObserver threshold ≤ 0.05 + timeout; content first, animation
second; robustness > spectacle; verify before claiming. ESM-bridge amendment in
`01` §16 applies (dynamic `import()` for chart libs; preview over http).

If an invariant and a flourish conflict, the invariant wins.

---

## Environment

- 🔌 Connect needs **Node.js 24+** (`scripts/diagnostico.*`).
- 🏗️ Build needs **Python 3** (helpers + local preview server; charts/comparator
  need http, not `file://`).
- 📥 Populate needs **Python 3 + Scrapling** (the scraper's stealth browser).
  Install per `06-populate-pipeline.md` §1; the skill installs it itself.
- No VPS, no accounts, no AI key. Optional PHP+SQLite admin runs on the same
  Hostinger plan if the user wants self-service product editing (`03`).

---

## Files index

```
SKILL.md                              ← this file — the router + build/populate flow
intake-template.md                    ← the few questions worth asking
recommended-settings.json             ← optional zero-prompt pre-authorization
evals/evals.json                      ← capability-routing evals
reference/
  01-stack-and-conventions.md         ← file structure, IIFE, ESM bridge (shared)
  02-niche-and-architecture.md        ← pick niche, page map, data-driven principle
  03-data-store.md                    ← JSON vs PHP+SQLite; the admin option
  04-product-schema.md                ← the normalized field set (e-bike worked example)
  04-critical-gotchas.md              ← the web invariants, in full (shared)
  05-pages-and-features.md            ← home, fichas, comparator, charts, guides, generator
  06-populate-pipeline.md             ← links → scrape → normalize → enrich → save (v2 fixes)
  14-mapa-autonomia.md                ← optional range map (isochrones, keyless) — v2
  03-effects-catalog.md               ← copy-paste effects (shared)
  07..10, 12, 13                      ← windows, checklist, env, cache, connect, deploy (shared)
templates/
  htaccess.template                   ← copy as `.htaccess` to every root
  producto.schema.json                ← the record shape + field metadata
  ficha.example.html                  ← a reference product page (structure)
scripts/
  amazon_extractor.py                 ← the Scrapling scraper (link → full product data)
  descargar-librerias.py              ← vendor chart/comparator libs into lib/
  diagnostico.ps1 / .sh               ← environment check for the connection
  verify_project.py                   ← post-generation sanity check
```

---

## Zero-prompt mode

Merge `recommended-settings.json` into `~/.claude/settings.json` once to
pre-authorize this skill's scripts, the Hostinger connection commands, the
Scrapling install and the local preview server. Nothing destructive.

---

## Final note

Structure first, data second, pages generated from data. When they say *"hazme
una web de afiliados de X"* they get a real comparison engine; when they paste
their links they get it filled with their monetized products; when they say
*"publícala"* they get a live URL — each on its own, each finished.
