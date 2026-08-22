# Upgrade an Existing Portfolio — restyle, don't restart

When the person already has a portfolio (a folder, or a live Hostinger URL) and
wants it "mucho mejor". The goal: **keep everything true about them, raise the
craft dramatically.** Their story and achievements are the asset; the design is
what you rebuild.

---

## 1. Capture what exists (never guess)

- **Live URL:** open it in the preview browser, read the full page text and
  structure, and note every real fact — name, roles, stats, milestones, press,
  services, contact, and the images/assets used. If you can, pull the current
  files from Hostinger (`13-hostinger-deploy.md` / the connector) so you keep the
  original images and copy.
- **Local folder:** read the HTML/CSS/JS and inventory the same.
- Build a **content inventory** first: every real claim and asset, in a list.
  That inventory is sacred — the upgrade may re-say it better, never change what
  it asserts (invariant 1). If a number looks wrong, ask; don't silently alter
  it.

## 2. Diagnose (what's holding it back)

Judge against the quality bar (`SKILL.md`). Common gaps in a first-gen
portfolio:

- Flat hero (no wow first screen), weak type scale, generic palette.
- The work under-shown — small images, thin gallery, no lightbox, no case depth.
- No single clear hire-me path, or a dead contact button.
- Sections in a bland order (biography before proof).
- Mobile is a squashed desktop.
- Runtime fragility (module scripts, no cache-busting, reduced-motion killing
  everything on Windows — `04`, `07`, `10`).
- Assets not optimized (mixed formats, huge images, slow paint).

Name the 3-5 biggest levers before touching code.

## 3. Choose the upgrade depth

| Ask | Do |
|---|---|
| "mejora el diseño pero mantén la esencia" | Same structure & content, new archetype-grade visual layer: type scale, palette, hero, effects, spacing, imagery treatment, mobile. A **restyle**. |
| "rehazla, mucho mejor" | Keep the content inventory, redesign freely — new archetype, richer sections, better-shown work, real CTA. A **rebuild on the same truths**. |
| "añade X / arregla Y" | Surgical edit in the existing style (`SKILL.md` ✏️). |

Default to a **restyle** unless they say "rehazla". When unsure, ask one line.

## 4. Execute like a fresh build — with their content

- Pick ONE archetype fitting their niche (`02-portfolio-niches.md`); it can be a
  different, stronger one than the original used.
- Apply the full invariant set (`04`), the structure spine (`05`), the image
  pipeline (`15` — re-encode their existing images to WebP, upscale the
  showcase, fix aspect ratios).
- **Raise the craft everywhere:** a commanding hero, a real type hierarchy,
  intentional motion (not pasted), a genuine gallery/case/timeline for the work,
  a working hire-me path repeated 3×, a mobile composition of its own.
- Keep every real fact; improve every sentence of copy toward editorial quality
  without inventing new claims.

## 5. Preview side by side, then publish carefully

- Preview the new version over http; walk it on desktop AND a mobile viewport.
- Show the person before publishing over their live site. If it's a real,
  visited portfolio (personal brand, active URL), **confirm before overwriting**
  — offer to publish to a temporary domain first so they compare, then swap.
- On publish, bump `?v=`, keep the `.htaccess`, and verify the live URL actually
  serves the new version (cache — `10`), not the old cached one.

## 6. The honesty line

If the current site makes a claim you can't verify and the new design would
amplify it (a big stat in the hero), keep it exactly as the person stated it —
don't round it up, don't dramatize it. A portfolio's credibility is the whole
point; inflating it is the one way to actively harm the person.
