# Data Store — where the products live

The database is the product. Two options; pick by whether the user will edit
products **without** Claude.

---

## Option A — `productos.json` + `lib/manifest.js` (DEFAULT)

A static JSON file, loaded by the site. Zero server, deploys in the zip, can't
break at runtime. Right for almost everyone.

```
proyecto/
├── datos/
│   ├── productos.json        ← the array of records (source of truth)
│   └── productos.schema.json ← the niche schema (from templates/)
├── lib/
│   └── db.js                 ← exposes window.__DB__ = { productos, meta }
└── assets/img/               ← WebP product images, <id>-N.webp
```

`lib/db.js` is generated from `productos.json` at populate time (or the site
`fetch`es the JSON at runtime — prefer generating `db.js` so it works on
`file://` too and needs no fetch):

```js
(function () {
  "use strict";
  window.__DB__ = {
    productos: [ /* records, inlined from productos.json */ ],
    nichos:    ["bici-electrica"],
    scoreAxes: ["autonomia","potencia","confort","deportividad","facilidad_uso","calidad_precio"],
    updated:   "2026-07-22"
  };
})();
```

Everything (fichas, comparator, charts, filters) reads `window.__DB__`. Adding
products = regenerating `db.js` from the updated `productos.json`. Keep
`productos.json` as the human-readable source; `db.js` is the built artifact.

**Scale:** fine to a few hundred products. Beyond that, split by niche
(`db.bici.js`, `db.patinete.js`) and load per section.

## Option B — PHP + SQLite admin (when the user wants self-service)

Only when the user says they want to add/edit products themselves without
Claude. A tiny admin on the same Hostinger plan — no extra hosting.

```
proyecto/
├── datos/                    ← NOT public
│   ├── productos.sqlite      ← the database
│   └── .htaccess             ← Require all denied
├── admin/
│   ├── index.php             ← password-protected product CRUD
│   └── .htaccess
├── api/
│   └── productos.php         ← reads SQLite → JSON for the frontend
└── (frontend as Option A, but fetches api/productos.php)
```

- One table mirroring the schema (`04-product-schema.md`); columns typed as the
  schema says. `specs_extra` and arrays (`pros`, `images`) as JSON columns.
- Admin: session-password login (hashed, per the sibling skills' pattern), a
  form generated from the schema, and a «pegar enlaces de afiliado» box that
  calls the same scrape→normalize→enrich pipeline server-side (needs Python
  available on the plan — check first; if not, keep populate in Claude and let
  the admin only edit).
- The frontend still renders from data — it just fetches it from
  `api/productos.php` instead of `db.js`. Cache the API response and bump
  `?v=` on deploy.
- Protect `datos/` (403) and verify it, exactly like the SaaS skill's proxy.

## Which to choose

| If the user… | Use |
|---|---|
| "just make me the site, I'll ask you to add products" | **A (JSON)** |
| "I want to add products myself from a panel" | **B (PHP+SQLite)** |
| unsure | **A** — offer B as a later upgrade |

Default to A. It's simpler, faster and unbreakable. B is a real feature but a
real cost — only build it on explicit ask.

## The schema file travels with the data

Whichever store, ship `productos.schema.json` (from `templates/`, filled for the
niche). It's the contract the scraper maps into and the pages render from —
keep it next to the data so the two never drift.
