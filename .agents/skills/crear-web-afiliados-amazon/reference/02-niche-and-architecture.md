# Niche & Architecture — the data-driven principle

The reference site shipped hardcoded product cards and a thin page per item.
This skill inverts that: **one normalized database, many generated pages**. That
inversion is the whole quality jump — it's what lets a site have 15 products or
150 with the same code, real comparison, and consistent design.

---

## The principle (repeat it until it's reflex)

> A product is a **record**, not a page. Pages are **views** over records.
> Adding a product means adding a record — never writing HTML.

Consequences that must hold:
- The comparator, the charts, the category lists and the fichas all read the
  same `productos.json`.
- Design lives in CSS + templates, applied uniformly to every record.
- The user (or Claude) grows the site by pasting links, not by editing pages.

If you ever find yourself writing `<h1>Product Name</h1>` by hand, stop —
that belongs in the data.

## Page map (what a complete site has)

Far more than the reference's home + ficha + comparator. Target set:

| Page | Generated from | Purpose |
|---|---|---|
| **Home** | featured + newest records | hero, top picks, category entries, "cómo elegimos" |
| **Category / niche pages** | records filtered by `category`/`tipo_uso` | one per meaningful segment, each an entry point |
| **Product ficha** (1 per record, auto) | one record | the rich page — see `05` |
| **Comparator** | any 2-N records | side-by-side table + radar overlay |
| **Buying guide(s) / blog** | records + editorial | "mejor bici eléctrica para ciudad 2026" — SEO magnet, links to fichas |
| **Ranking / "los mejores X"** | records sorted by a score | "top 5 por autonomía" — generated lists |
| **Ofertas** | records where `discountedPrice < retailPrice` | the deals view |
| **Sobre nosotros / cómo elegimos** | static | trust + methodology (why the scores) |
| **Aviso de afiliados + legal** | static | required disclosure (`SKILL.md` inv. 5) + privacy |

Ship the home, category, ficha, comparator, one buying guide, ofertas and the
legal/disclosure pages minimum. Rankings and more guides are easy wins to offer.

## SEO shape (this is how affiliate sites get traffic)

- One buying-guide/ranking page per **search intent** ("mejor bici eléctrica
  calidad precio", "bici eléctrica plegable para metro"), each cross-linking the
  relevant fichas.
- Fichas target the product name; guides target the category queries.
- `title`/H1 match intent; JSON-LD `Product` on fichas (name, brand, offers,
  aggregateRating from the scraped data — only real values), `ItemList` on
  rankings, `FAQPage` on guides.
- Internal linking: every guide → fichas → comparator → related fichas. A dense
  internal graph is the affiliate SEO engine.

## Niche selection (🎯 Recommend)

Good affiliate niches share three traits — weigh them when advising:

1. **High-ticket enough that commission per sale is worth it.** E-bikes,
   monitors, robot vacuums, espresso machines, mattresses > phone cases.
2. **Spec-driven, so comparison adds real value.** Products people research and
   compare on numbers (autonomy, wattage, dpi) suit this engine; impulse buys
   don't.
3. **A niche the user knows or can speak to**, so the editorial is credible.

Recommend ONE niche with a one-line reason, or validate theirs. Multi-niche
"shop" sites work too — one schema per niche, compare within a niche only, and
a top-level `nicho` field. Don't over-recommend; if they already said "bicis
eléctricas", just build it.

## Why not the reference stack (React + PocketBase)

The reference used a heavy SPA + a database server. This skill deliberately does
**not**: it's static HTML/CSS/vanilla-JS (`01`) reading a JSON data file, so it
deploys as a plain zip to any Hostinger plan, has no build step, no server to
run, loads instantly and can't break at runtime. The optional PHP+SQLite admin
(`03`) is the only server piece, and only when the user wants to add products
without Claude. Same features, a tenth of the fragility.
