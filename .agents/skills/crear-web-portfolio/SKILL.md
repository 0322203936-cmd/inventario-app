---
name: crear-web-portfolio
description: Build a stunning PORTFOLIO website on Hostinger for any creative or professional niche. (a) CONNECT the Hostinger account to Claude Code. (b) BUILD a premium portfolio (static HTML/CSS/vanilla JS, no build, no backend) tailored to the person's field - illustrator/artist gallery, developer/designer case studies, musician track player, photographer/filmmaker/video-editor reel, writer clips, or a personal-brand trajectory/CV with milestones, press and services. Real work showcased, one clear hire CTA. (c) PUBLISH it to Hostinger, connect a custom domain, and improve or restyle an existing portfolio on request. Use whenever the user wants a portfolio, personal site, "sobre mi", a web to show their work, get hired or offer services, a creative showcase, or to upgrade an existing portfolio. Triggers include crea mi portfolio, una web para mi trabajo, portfolio de mis dibujos/webs/canciones, pagina personal, web para encontrar trabajo, and their English equivalents.
---

# Portfolio Studio · v2 — connect · build · publish

Three **independent capabilities** for building a **personal portfolio site**:
a beautiful page that gathers someone's work, milestones and story so they get
hired or land clients. Same studio logic as the sibling skills — read which door
the person walked through, do that, verify it, stop.

- 🔌 **Connect** the Hostinger account to Claude.
- 🎨 **Build** the portfolio: pick the niche, showcase the real work, wow-grade.
- 🚀 **Publish** it to Hostinger (and restyle/improve an existing one on request).

**What makes this different from the affiliate / SaaS / micro-SaaS skills:** no
database, no AI proxy, no accounts, no scraper. The whole value is **visual
craft + the right structure for THIS person's field** — an illustrator needs a
gallery, a developer needs case studies, a musician needs a player, a
personal-brand needs a trajectory. One person, one story, told beautifully.

This skill inherits the visual-quality engine of the premium-website work
(archetypes, effects, gotchas, image pipeline) and specializes it for
portfolios across niches.

---

## THE GOLDEN RULE: do only what was asked, then stop

- *"conéctame Hostinger"* → only connect and verify.
- *"hazme un portfolio de mis dibujos"* → only build it. Don't publish.
- *"publícalo"* → only publish.
- *"mejora mi portfolio de X"* → only restyle what exists, in its own spirit,
  bigger and better — don't silently rebuild from zero unless that's the ask.

At the end offer **one** sentence naming the next step («¿lo publico en tu
hosting?»). Never start it unprompted. Read the state each time: connected?
project exists? published?

---

## Route the request → capability

| What they say / the situation | Capability | Primary ref |
|---|---|---|
| "conéctame Hostinger", "vincula mi hosting" | 🔌 **Connect** | `12-hostinger-connect.md` |
| "hazme un portfolio de <lo que sea>", no project yet | 🎨 **Build** | `02-portfolio-niches.md` → `05` → `03` |
| Project exists: "cambia…", "añade un proyecto", "otra sección" | ✏️ **Edit** | existing files + invariants |
| "mejora / rediseña mi portfolio actual" (theirs or a live URL) | 🔁 **Upgrade** | `06-upgrade-existing.md` |
| "publícalo", "súbelo", "ponle mi dominio" | 🚀 **Publish** | `13-hostinger-deploy.md` |
| "¿qué diseño le pondrías?", "dame ideas" | 🎯 **Direction** | `02` + `03` |
| "no funciona", "se ve vieja", "se ve plano en mi PC" | ✅ **Verify** | `04`, `07`, `10` |

---

## 🎨 The build flow

A portfolio build is short and design-led. In order:

### Step 1 — Whose portfolio, and what field?
This is THE question that shapes everything. Map to a **niche** in
`02-portfolio-niches.md` (illustrator, developer, musician, photographer,
writer, personal-brand/trajectory, multi-discipline…). The niche decides the
core section (gallery vs. case studies vs. player vs. timeline), the archetype
family and the tone. Ask it plainly if not obvious; infer if it is.

### Step 2 — Gather the real material (once, in one message)
`intake-template.md` — the few things only the person can give you: their name,
what they want the visitor to do (hire / commission / contact / download CV),
their pieces/projects/tracks, and their photos/work files (or "use tasteful
placeholders and I'll swap them"). Never invent their achievements — a portfolio
is a claim about a real person (invariant 1).

### Step 3 — Pick ONE archetype and build
Choose a single visual archetype (`02-portfolio-niches.md` maps niche→archetype;
full catalog in `03-effects-catalog.md` and the inherited archetype rules).
Generate `index.html` / `styles.css` / `main.js` / `lib/manifest.js` per
`01-stack-and-conventions.md`, structure per `05-portfolio-structure.md`, images
per `15-image-and-asset-pipeline.md`. Copy `templates/htaccess.template` →
`.htaccess`. **Never combine two archetypes** — it reads as confused.

If the person has a **real public audience** (a channel, a feed, published
releases), you may add **one** optional live-proof module — a rolling scoreboard
counter, a real subscriber/follower count, a platform-search reveal animation, or
an auto-updating "latest content" carousel — from `16-creator-live-modules.md`.
Only with real, public facts (invariant 1); it's garnish, the work stays the hero.

### Step 4 — Verify and preview
`scripts/verify_project.py`, then a local `python -m http.server` preview (charts
/ fetch / transitions need http, not `file://`). Exercise it: every work item
opens, the contact CTA works, mobile is its own composition, it looks alive on
Windows (reduced-motion gotcha, `07`).

### Step 5 — Offer the next step (one line)
«¿lo publico en tu hosting?» / «¿le conecto tu dominio?». Then stop.

---

## Always-on invariants

**Communication:** the person is **non-technical**. Zero jargon. Run every
command yourself; the only manual step is them dropping their work files or
pasting a URL. Announce before acting, celebrate milestones (✅), never show a
raw error, verify before claiming.

**Portfolio invariants:**
1. **It's about a real person — never fabricate.** Don't invent projects,
   clients, awards, stream counts or press. If the person didn't give it, it
   doesn't go on the page. Placeholders are clearly placeholders to be swapped.
2. **The work is the hero, not the chrome.** Effects serve the pieces — an
   illustration gallery must show the art crisp and big; a developer's cases
   must be legible. If a flourish competes with the work, the work wins.
3. **One clear "hire me" path.** Every portfolio has a single obvious next
   action (email, form, commission, download CV, book a call) visible without
   scrolling and repeated at the end. A portfolio with no CTA is a dead end.
4. **Show, then tell.** Lead with the strongest pieces / the biggest milestone,
   not with a wall of biography. The visitor decides in seconds.
5. **Their real files, treated well.** Convert uploads to WebP, keep aspect
   ratios, never stretch a piece. If they have no images yet, use tasteful
   niche-appropriate placeholders and say so — never ship a broken `<img>`.
6. **Mobile is a real composition**, not a squashed desktop — a portfolio is
   opened on phones from a bio link constantly.

**Web quality invariants** (inherited, full detail in `04-critical-gotchas.md`):
classic `<script defer>` + IIFE + `window.__BRAND__`; `.htaccess` +
`?v=YYYYMMDD`; native scroll by default (Lenis opt-in); reduced-motion gates
only intrusive effects (Windows ships it ON — `07`); content hardcoded in HTML
(JS enriches); `safe()` around inits; IntersectionObserver threshold ≤ 0.05 +
timeout; splash double safety net; content first, animation second; robustness >
spectacle; verify before claiming. ESM-bridge amendment in `01` §16 applies.

**Quality bar (what "premium" means here):** first-screen wow; effects feel
intentional, never pasted; editorial copy (no "unlock/transform/revolutionary");
mobile is its own composition; robustness > spectacle when in doubt. If the
person opens it and says "wow, ese soy yo", it's right.

If an invariant and a flourish conflict, the invariant wins.

---

## Diversity mandate

Every portfolio is a different person — every output must look meaningfully
different. Don't clone the last portfolio you made; rotate archetype, palette
family, layout topology and the signature effects (`03-effects-catalog.md`). The
person must never feel "this looks like a template". The niche examples are
quality references, not molds.

---

## Environment

- 🔌 Connect needs **Node.js 24+** (`scripts/diagnostico.*`).
- 🎨 Build needs **Python 3** (helpers, WebP conversion, Openverse stock, local
  preview). Everything degrades gracefully without Python (`09`); WebP falls
  back to the originals, stock to placeholders.
- No VPS, no accounts, no keys.

---

## Files index

```
SKILL.md                              ← this file — the router + build flow
intake-template.md                    ← the few things only the person can give
recommended-settings.json             ← optional zero-prompt pre-authorization
evals/evals.json                      ← capability-routing evals
reference/
  01-stack-and-conventions.md         ← file structure, IIFE, ESM bridge (shared)
  02-portfolio-niches.md              ← niche → core section + archetype + tone
  03-effects-catalog.md               ← 40+ copy-paste effects (inherited)
  04-critical-gotchas.md              ← the web invariants, in full (shared)
  05-portfolio-structure.md           ← sections, hire-me path, per-niche layout
  06-upgrade-existing.md              ← restyle/improve an existing portfolio
  07-windows-troubleshooting.md       ← reduced-motion + Windows quirks (shared)
  08-pre-deploy-checklist.md          ← the verify pass (shared)
  09-environment-detection.md         ← Python/Bash detection (shared)
  10-deployment-and-cache.md          ← cache-busting + .htaccess (shared)
  12-hostinger-connect.md             ← 🔌 connect the account (shared)
  13-hostinger-deploy.md              ← 🚀 publish to Hostinger (shared)
  15-image-and-asset-pipeline.md      ← photos: user work / Openverse / WebP (inherited)
  16-creator-live-modules.md          ← OPTIONAL live-proof: rolling counters, real
                                        subscriber count, platform-search reveal,
                                        auto-updating "latest content" carousel
templates/
  htaccess.template                   ← copy as `.htaccess` to every root
scripts/
  diagnostico.ps1 / .sh               ← environment check for the connection
  download_libs.py / .sh              ← GSAP/ScrollTrigger/Lenis to lib/
  openverse_fetch.py / .sh            ← free stock/placeholder images (no key)
  webp_convert.py                     ← any image → optimized WebP
  verify_project.py                   ← post-generation sanity check
```

---

## Zero-prompt mode

Merge `recommended-settings.json` into `~/.claude/settings.json` once to
pre-authorize this skill's scripts, the Hostinger connection commands and the
preview server. Nothing destructive.

---

## Final note

The work is the hero; the design makes it shine; the CTA turns a visitor into a
client or an employer. When they say *"hazme mi portfolio"* they get a page that
looks like them at their best, opens with a wow, and gives whoever lands there
one clear way to reach them.
