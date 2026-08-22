# The Product Schema — normalize everything

The whole skill rests on this: every product is a **typed, normalized record**.
Messy Amazon text in, comparable fields out. Pages, comparator and charts read
these fields — so if a value isn't here, it can't be compared or charted.

The e-bike set below is the **worked example** (the reference site's 35 fields,
cleaned up). Any niche follows the same five **groups**; only the technical
specs and scores change.

---

## The five field groups (every niche has these)

| Group | Purpose | Per-niche? |
|---|---|---|
| **A. Identity & affiliate** | what it is + how it earns | same for all niches |
| **B. Commercial** | price, offer, rating | same for all niches |
| **C. Technical specs** | the comparable numbers | **niche-specific** |
| **D. Comparison scores** | 0-10 axes for the radar chart | **niche-specific** |
| **E. Editorial** | human text: description, pros/cons, who it's for | same shape, niche content |

Groups A, B, E are fixed. When you build a new niche, you design C and D — and
that design IS the product. Get 8-15 spec fields and 5-7 score axes that
actually differentiate the products.

---

## Group A — Identity & affiliate (never edit by hand, never fake)

```json
"id":            "e-001",                       // stable slug, kebab
"asin":          "B0CKHWXP4G",                  // from the link
"name":          "F.lli Schiano E-Ride 28\"",
"marca":         "F.lli Schiano",
"affiliate_url": "https://amzn.to/4yDcP7X",     // the user's link, VERBATIM
"affiliate_tag": "voltbike-21",                 // their tag, preserved
"canonical_url": "https://www.amazon.es/dp/B0CKHWXP4G",
"images":        ["assets/img/e-001-1.webp", "..."],   // downloaded + WebP
"category":      "Ciudad",
"isFeatured":    false,
"showInTopMenu": false
```

`affiliate_url` and `affiliate_tag` are **load-bearing** — every buy button
uses them (invariant 1). Never derive, rewrite or drop them.

## Group B — Commercial (a snapshot, labelled as such)

```json
"retailPrice":     999.99,
"discountedPrice": 862.33,        // == retailPrice if no offer
"rango_precio":    "medio",       // bajo | medio | alto | premium — computed
"valoracion_media": 4.4,          // Amazon stars
"resenas_cantidad": 1284,
"precio_fecha":    "2026-07-22"    // capture date — prices go stale (invariant 6)
```

## Group C — Technical specs (THE niche design; e-bike example)

Every spec is **typed and unit-carrying**. Text like "40Nm" becomes
`par_motor_nm: 40`. Unmapped specs go to `specs_extra` (free text), never
force-cast into a number.

```json
"tipo_uso":            "ciudad",        // ciudad | trekking | montaña | plegable | carga
"tipo_motor":          "trasero",       // central | trasero | delantero
"potencia_w":          250,
"par_motor_nm":        40,
"autonomia_km":        70,
"capacidad_bateria_wh": 374,
"bateria_extraible":   true,
"velocidad_max_kmh":   25,
"tiempo_carga_h":      3.5,
"peso_bici_kg":        24,
"peso_max_usuario_kg": 120,
"num_marchas":         21,
"talla_cuadro":        "única",
"diametro_rueda_pulg": 28,
"frenos":              "V-Brake",
"suspension":          "delantera",
"garantia_anos":       2,
"specs_extra": { "Pantalla": "LED", "Sillín": "Selle Royal" }   // anything unmapped
```

**Rules for spec normalization:**
- One canonical unit per field, in the field name (`_km`, `_wh`, `_kg`, `_nm`).
- Booleans for yes/no features (`bateria_extraible`).
- Enums for categoricals, with a fixed value list per field — the comparator
  filters depend on it.
- `null` when the scrape didn't yield it. Never guess.
- `specs_extra` is the escape hatch: real scraped facts that don't map to a
  field, kept as `{label: value}` text so the ficha can still show them.

## Group D — Comparison scores (0-10, the radar chart axes)

These are **derived, editorial judgments** — computed from the specs during
enrich, not scraped. 5-7 axes that let two products be compared at a glance.

```json
"score_autonomia":      6,   // from autonomia_km, normalized to the niche range
"score_potencia":       4,
"score_confort":        7,
"score_deportividad":   4,
"score_facilidad_uso":  8,
"score_calidad_precio": 8
```

How to compute them (document the rule per niche so they're consistent):
map each underlying spec to 0-10 across the **range seen in this catalog**
(e.g. `score_autonomia = round(10 * (autonomia_km - min) / (max - min))`), then
let editorial judgment nudge ±1. They must be **comparable across products** —
recompute all scores when the catalog's min/max shifts. Mark them in the UI as
"valoración del editor", never as a manufacturer spec.

## Group E — Editorial (human text; clearly editorial)

```json
"description":     "Bicicleta eléctrica de trekking con motor trasero de 250W…",  // 2-4 sentences
"cuerpo_editorial": "<p>…</p>",     // the long-form review body (blog touch), HTML
"pros":            ["Batería extraíble", "Muy cómoda en ciudad", "Buen precio"],
"contras":         ["Peso elevado", "Sin suspensión trasera"],
"ideal_para":      "Quien busca una bici cómoda para el día a día urbano sin gastar de más.",
"destacado_editorial": "La mejor relación calidad-precio para ciudad.",
"resenas_resumen": "Los compradores destacan el montaje sencillo y la autonomía real."
```

Editorial text is written during enrich from the scraped bullets, A+ content
and reviews — grounded in what was scraped, never inventing facts. The
`cuerpo_editorial` is the "blog" depth the reference site lacked: a few real
paragraphs per product.

---

## Designing the schema for a NEW niche

1. Scrape 2-3 sample products first (`06`) and read their real spec tables.
2. Pick **8-15 spec fields** that (a) most products have and (b) actually
   differ — those are the comparison levers. Name each with its unit.
3. Pick **5-7 score axes** that a buyer cares about; write the spec→score rule
   for each.
4. Keep A, B, E as-is. Write `templates/producto.schema.json` for the niche
   (field, type, unit, enum values, required, how-to-compute).
5. Multi-niche shop: add a top-level `nicho` field and keep a schema per niche;
   the comparator only compares within the same niche.

The schema file is the contract every later step reads — the scraper maps into
it, the pages render from it, the comparator filters on it. Write it well and
everything downstream is mechanical.
