# 14 — Range map: reachable-area by autonomy (optional premium feature)

A signature feature that lands very well for niches with a **range/battery/fuel**
spec (e-bikes, scooters, EVs, drones, cordless tools by runtime): an interactive
map where the user picks a point and the site shows **how far they could get**
with each product — as a real, street-shaped area (an *isochrone/isodistance*),
not a naive circle. On a ficha it's one product's area; on the comparator it
overlays every selected product's area, like the radar but for distance.

Build it **only when the niche has a meaningful range field** and the user wants
it (or offer it as an easy win). It is **100% front-end and keyless** — no API
keys, no backend, no accounts.

---

## The stack (all free, all keyless)

| Piece | What | Notes |
|---|---|---|
| **Leaflet 1.9** | map library | vendor `lib/leaflet.js` + `lib/leaflet.css` locally; it's a classic UMD script (`window.L`), loads fine with `defer` — no ESM issues |
| **CARTO dark tiles** | basemap | `https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png`, `subdomains:"abcd"` — matches a dark theme; keyless, attribute OSM + CARTO |
| **Nominatim** | geocoder (search box) | `https://nominatim.openstreetmap.org/search?format=json&limit=1&countrycodes=<cc>&q=…`; keyless, send `Accept-Language` |
| **Valhalla (public OSM)** | the isochrone engine | `https://valhalla1.openstreetmap.de/isochrone` — **keyless**, real road-network isochrones, `costing:"bicycle"` (or `auto`/`pedestrian`), `contours:[{distance: KM}]`, `polygons:true` → returns GeoJSON |

**Valhalla request** (GET, `json=` URL-encoded):
```json
{"locations":[{"lat":40.4,"lon":-3.7}],"costing":"bicycle","contours":[{"distance":70}],"polygons":true}
```
Response is a GeoJSON `FeatureCollection` with a `Polygon` — draw it with
`L.geoJSON`. **Hard limit: 150 km per contour** (it 400s above that: `Exceeded
max distance: 150`). Cap the requested distance at 150 and note it in the legend
when the product's range is higher.

> Load these as data at runtime (tiles, geocode, isochrone are inherently network
> calls — that's fine, they're content). The **library** (`leaflet.js`) is
> vendored locally per the no-CDN-libs rule (`01`).

---

## Behaviour

- **Where:** on each ficha (fairly high, right after the gallery/buybox) and on
  the comparator (above the table). Full-width block.
- **Input:** a search box (Nominatim) **and** click-to-place on the map.
- **Ida/vuelta toggle (important):** a segmented control "Ida y vuelta / Solo
  ida". In **round-trip** mode the reachable distance is **half** the autonomy
  (you need charge to get back) — default to round-trip, it's the honest, useful
  view. In **one-way** mode use the full autonomy. Changing the toggle redraws.
- **Ficha:** one product's area. **Comparator:** overlay all selected products'
  areas, largest drawn first (behind), each in that product's series colour, with
  a legend — reuse the radar's colour order so a bike is the same colour in both.
- **Marker** at the chosen origin. `fitBounds` to the drawn area(s).
- **Legend** per product: name + the distance actually used, e.g.
  `Prophete… · ida y vuelta → 85 km` or `… · alcance 170 km · máx. 150 km`.

---

## Implementation notes (the gotchas that bit, so you don't repeat them)

- **Init with `setTimeout`, not only IntersectionObserver.** Lazy-mounting the
  map purely on IO fails in non-composited/hidden preview tabs (see
  `04-critical-gotchas.md` E.4). Do `setTimeout(start, 350)`, idempotent, so it
  always mounts and stays testable. Cache isochrone results by
  `lat,lon,km` to avoid duplicate calls.
- **`scrollWheelZoom: true`** so wheel-over-map zooms the map (E.6).
- **Graceful fallback:** if Valhalla errors, draw a dashed `L.circle`
  (`radius ≈ km*1000*0.7`) as a rough approximation and note it — never leave the
  map blank.
- **Style Leaflet for dark:** override `.leaflet-control-attribution`,
  `.leaflet-bar a`, `.leaflet-popup-*` to the dark palette; give the map canvas a
  fixed height (`clamp(320px, 52vh, 480px)`) and a dark background.
- **Honesty:** label it an estimate — "zona alcanzable estimada sobre la red de
  carreteras; la autonomía real varía según modo, terreno, peso y viento."
- **Package it:** the deploy zip must include `lib/leaflet.js` and
  `lib/leaflet.css` (glob `lib/*.js` and `lib/*.css`), not just `db.js`.

---

## Reference sketch (vanilla, classic script, inside the main IIFE)

```js
var ISO = {};                                  // cache por lat,lon,km
function isochrone(lat, lon, km){
  var key = lat.toFixed(4)+","+lon.toFixed(4)+","+km;
  if (ISO[key]) return Promise.resolve(ISO[key]);
  var body = {locations:[{lat:lat,lon:lon}], costing:"bicycle",
              contours:[{distance:km}], polygons:true};
  var url = "https://valhalla1.openstreetmap.de/isochrone?json="+encodeURIComponent(JSON.stringify(body));
  return fetch(url).then(function(r){ if(!r.ok) throw 0; return r.json(); })
    .then(function(gj){ ISO[key]=gj; return gj; });
}
// per map: read bikes (fixed id on a ficha, or getCompare() on the comparator),
// mode = "roundtrip" | "oneway"; km = min(mode==="roundtrip"? auton/2 : auton, 150);
// draw L.geoJSON(gj) per bike in its colour, fitBounds, build the legend.
// toggle buttons [data-mode] flip mode and redraw; search box → Nominatim → draw.
```

Full, working versions of both the JS module and the CSS were built in
production; re-derive them from this spec — they're ~150 lines total.
