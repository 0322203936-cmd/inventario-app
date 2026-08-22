# Portfolio Structure — sections, the hire-me path, per-niche layout

A portfolio isn't a brochure with a person's name on it. It's an argument:
*this is who I am, this is the proof, here's how to reach me.* This file is the
skeleton every niche fills differently.

Rendering pattern: HTML ships the content + the CTA (works with JS off);
`main.js` (IIFE) reads `window.__BRAND__` and mounts galleries, players,
filters, timeline animations (`04-critical-gotchas.md` D.3 — idempotent,
`safe()`-wrapped).

---

## The universal spine (every portfolio, in this order)

1. **Hero** — name, what they do (roles/tagline), and the single strongest
   proof (a flagship stat, a hero piece, a featured track). A visitor must know
   "who is this and are they good" within one screen. One clear CTA visible here.
2. **The work** — the niche's core section (gallery / cases / player / series /
   clips / timeline). This is 60% of the page. Lead with the best.
3. **About / story** — human, short, specific. The path that makes them
   credible, not a life history. Photo of the person if they have one.
4. **Proof** — press, clients, awards, testimonials, stats, logos — whatever's
   real. Social proof converts skeptics.
5. **Services / what I offer** (if the goal is clients) — 2-4 concrete offerings
   in plain language, optionally with "desde X€" or "hablemos".
6. **Contact / hire me** — the destination the whole page funnels to. Email +
   form or intent-split ("negocios", "prensa", "encargos"), social links.
7. **Footer** — quiet: copyright, socials, back-to-top, maybe a CV download.

Not every portfolio needs all seven — a pure artist may skip "services", a
job-seeker may add a "download CV". But the spine (hero → work → about → contact)
is non-negotiable.

## The hire-me path (invariant 3 — get this right)

- **One primary CTA**, chosen from the goal: `contratar` / `encargar` /
  `contactar` / `descargar CV` / `escuchar en Spotify` / `reservar llamada`.
- Present it in the **hero**, after the **work**, and in the **contact** section
  — three touchpoints, same action.
- Make it real: a `mailto:` with a useful subject, or a form that actually
  submits (Formspree-style endpoint the user provides, or a `mailto` fallback —
  never a dead button). If a form, keep it to name + email + message.
- Intent-split contact (the `trayectoria` pattern) when different audiences want
  different things: business / press / collaboration, each its own line.

## Per-niche core section (how "the work" is built)

- **`arte` / `foto` — gallery:** masonry/justified grid → lightbox (title, year,
  medium, CTA). Filters by series. Images WebP, lazy, correct aspect ratio,
  never stretched. Full-bleed hero piece optional.
- **`dev` — case studies:** a few deep cards. Each: mockup, problem→build→result,
  quiet stack tags, live + repo links. A services list + a compact stack strip.
- **`musica` — player:** HTML5 `<audio>` track list with inline play, cover art,
  streaming links, featured track. No external player SDK.
- **`escritura` — clips:** grouped list (title, outlet, year, one-line, link/PDF),
  pull-quotes as design. Reading-first typography.
- **`trayectoria` — story + timeline:** stats band → origin → "what I do" trio →
  **milestones timeline** → press → manifesto → collaborations. Numbers and
  press do the persuading.
- **`multi` — hub:** discipline cards routing to sub-sections, each using its
  own mechanic, one archetype for coherence.

## Content the person must provide (don't invent — invariant 1)

Gather in intake: their name, roles/tagline, the pieces/projects/tracks/clips/
milestones (with real titles, years, links), their photos/work files, real
proof (press, clients, stats), and the contact target. Anything missing is a
clearly-labelled placeholder to swap — never a fabricated achievement.

## SEO & sharing (a portfolio is shared from a bio link)

- `<title>` = "Nombre — qué hace" (e.g. "Adrián Sáenz — Emprendedor · Inversor").
- Meta description in first person, one line. `og:image` = a strong hero/piece
  rendered to 1200×630 WebP.
- JSON-LD `Person` (name, jobTitle, sameAs: social URLs, image). `CreativeWork`
  per gallery piece if it's an artist.
- Fast first paint — bio-link visitors bounce on a slow load.

## Definition of done (structure)

- [ ] Hero states who + what + one proof, with a CTA, in one screen.
- [ ] The niche core section leads with the strongest work; every item opens/
      plays/links correctly.
- [ ] The primary CTA appears in hero, after the work, and in contact — and
      actually works (mailto or submitting form).
- [ ] About is short and specific; proof is real; nothing fabricated.
- [ ] Mobile is its own composition; gallery/player/timeline work on touch.
- [ ] JS off → name, work items, about and contact still render.
- [ ] `Person` JSON-LD, og:image, correct title. `?v=` bumped. Previewed over
      http.
