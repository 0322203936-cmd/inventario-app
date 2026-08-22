# 11 — AI image generation (the image genie) · OpenAI gpt-image-2

This is capability ③ of the skill: generate **bespoke, brand-consistent
imagery** for a site — a real hero scene, cleaned-up product shots, a coherent
lifestyle set — with OpenAI's image model, when stock (Openverse) would look
generic and the user has no photos of their own good enough.

It is **opt-in and it costs the user money** (a few dollars of OpenAI credits).
Offer it, explain the cost, get a yes, then run. If they decline: use Openverse
stock or leave editable placeholders. Never generate silently on their bill.

> This file is the HTML-website adaptation of a workflow proven in production.
> The mechanics (model, endpoints, contracts) are the same; the **integration**
> is different — images land as **WebP in `assets/img/`** and feed the same
> pipeline as any other photo, and the **key + working files never get
> deployed**.

**Four pillars — do not skip any:**

1. **The photographic script** — every image is one call with a prompt written
   for *that* slot. No reused generic prompt.
2. **Anchor images** — the first 2-3 clean shots become the shared reference for
   every later call, so the subject/aesthetic don't drift.
3. **The banner contract** — heroes are generated at the *exact* ratio of their
   slot, with a vertical safe zone, and verified at 16:9 and mobile. This is the
   historical #1 bug.
4. **Chained series** — steps 1-2-3, before/after, storyboards are generated in
   a chain, each image using the previous one as a reference.

---

## 0. When to offer it, and how to ask

Reach for AI generation when:

- The **hero** needs a specific scene that must look *made for them* (not a
  stock photo everyone else uses).
- The user has **their own product/subject photos but they're ugly** (supplier
  images with text overlays, arrows, dirty backgrounds) — clean them into pro
  shots.
- The site needs a **coherent set** of lifestyle / detail / step images that
  stock can't deliver consistently.

How to offer (non-technical, no jargon — say "key", not "API key"):

> "Para la portada quedaría mucho mejor una imagen hecha a medida para ti que
> una foto de banco genérica. Puedo generarla con inteligencia artificial.
> Cuesta unos 2-3 € en créditos de OpenAI (una empresa de IA) y tendrías que
> crearte una cuenta ahí — te guío en 2 minutos. ¿Lo hacemos?"

If no → Openverse stock or placeholders. If yes → signup + key, below.

---

## 1. OpenAI signup + key (guide the user in plain words)

> 1. Entra en **platform.openai.com** y crea una cuenta (vale la de Google).
> 2. Ve a **Settings → Billing** y pulsa "Add to credit balance" para añadir
>    **10 $** de saldo (es el tope; las imágenes costarán solo una parte).
> 3. Ve a **API keys** → "Create new secret key", ponle un nombre y créala.
> 4. Copia la clave (empieza por `sk-`) y pégamela aquí en el chat.

If the user gets lost, ask for a screenshot and guide over it (OpenAI's UI
changes; if a path doesn't match, look it up in current docs rather than
insisting on old routes).

### Key handling — CRITICAL for the HTML skill

Unlike a Shopify theme (where only theme folders upload), **on a static site the
entire project folder is what gets zipped/uploaded to Hostinger.** So the key
and all working files must live **OUTSIDE the deployable folder**.

Use a sibling working folder next to the site, e.g. for a project at
`.../mysite/` create `.../mysite-ia/`:

```
mysite/                 ← THIS is what deploys
  index.html  styles.css  main.js  lib/  assets/img/*.webp  .htaccess
mysite-ia/              ← NEVER deployed — key + working images live here
  clave-openai.txt      ← the key, on its own line
  fotos-originales/     ← the user's raw photos
  fotos-generadas/      ← anchors + drafts + intermediate generations
```

- Read the key only from `clave-openai.txt`. **Never** write it into any file
  under the project, never print it, never put it in `assets/`.
- Only the **final chosen** images cross over into `mysite/assets/img/` (as
  WebP). Everything else stays in `mysite-ia/`.
- If a call returns `401`, the key is mistyped — ask the user to paste it again
  (keys are shown once; they may need to create a new one).

---

## 2. The model & API (verified against current docs)

- **Model: `gpt-image-2`** — OpenAI's strongest for product/scene photography;
  excels at editing from reference images and at text-in-image.
- **Endpoints (the script handles both):**
  - From scratch: `POST /v1/images/generations` (JSON body).
  - From references: `POST /v1/images/edits` (multipart, `image[]` repeated per
    reference, **up to 16**). **This is what you'll use almost always** — the
    references teach the model the exact subject and aesthetic.
- **Auth:** `Authorization: Bearer <key>`.
- **`size` — this decides the banner.** gpt-image-2 accepts **any** `WxH` where:
  both sides multiples of 16, longest side ≤ 3840, max ratio 3:1, total pixels
  between 655,360 and 8,294,400. So **ask for the slot's exact ratio.** Staples:
  - `1024x1024` — cards, grids.
  - `1024x1536` — tall columns (2:3).
  - **`2048x1152` — 16:9 hero** (cheap draft: `1280x720`).
  - **`2688x1152` — 21:9 hero** (draft: `1680x720`).
  - **`1152x2048` — MOBILE hero 9:16** (draft: `720x1280`).
  - Ratio is controlled **only** by `size`; asking for "more panoramic" in the
    prompt does nothing. And mind the pixel minimum: `1024x576` is invalid; the
    cheap 16:9 draft is `1280x720`.
- **Other params:** `quality` (`low`/`medium`/`high`/`auto`), `n` (1-10
  variations of the *same* prompt in one call), `output_format` (`jpeg` for
  web), `moderation` (`auto`/`low`). **Do not send `input_fidelity`** — not
  supported on gpt-image-2 (it already processes inputs at high fidelity).
  gpt-image-2 does **not** support transparent background.
- **Response:** JSON with `data[N].b64_json` (base64 — the script decodes to a
  file for you).
- **Rate limits:** new accounts ~5 images/min. On `429`, wait 30-60 s.
- **Typical errors:** `401` bad key; `429` too fast; `insufficient_quota` = out
  of credit (top up); `400` mentioning content policy = reword the prompt; `400`
  about `size` = re-check the rules above.
- **Safety false positives (`moderation_blocked`):** with products near the
  mouth/body (mouthpieces, cosmetics) the classifier may block innocent prompts.
  Escalation (blocked calls are NOT charged): 1) reword the action in neutral,
  clinical language; 2) add `--moderacion low`; 3) change the scene to remove the
  person+product combo that trips it. Don't retry the same idea more than 2-3×.

---

## 3. Cost (keep spend ~2-3 $)

Price scales with size and quality. Per `1024x1024`: **low ≈ $0.006 · medium ≈
$0.05 · high ≈ $0.21** (input references add ~$0.01-0.03/call). A `2048x1152`
banner ≈ 2.25× a `1024x1024` of the same quality — that's why banner drafts use
`1280x720`. Spend policy:

- **Tests & variations: `low`**, with `--n 2` or `--n 3` in ONE call. Show them,
  regenerate only the chosen one at good quality.
- **Final section images: `medium`.** The sweet spot; ~30-40 medium images ≈ $2.
- **`high` ONLY for the hero.**
- Keep a rough running tally and mention it now and then ("llevamos ~$1.20 de
  los $10").

---

## 4. The script: `scripts/generar-foto.mjs`

Node 18+ (native `fetch`/`FormData`). Always use it — hand-rolling multipart +
base64 fails often, especially on Windows PowerShell.

```
node <skill-dir>/scripts/generar-foto.mjs \
  --clave <project>-ia/clave-openai.txt \
  --prompt "<description of the desired photo>" \
  --salida <project>-ia/fotos-generadas/hero-bruto.jpg \
  --ref <project>-ia/fotos-generadas/ancla-frontal.jpg \
  --ref <project>-ia/fotos-generadas/ancla-lateral.jpg \
  --calidad medium --tamano 2048x1152 \
  [--n 3] [--mascara <zona.png>] [--moderacion low]
```

- No `--ref` → generation endpoint; one or more `--ref` (≤16) → edit endpoint.
- `--n 2..10` → variations of the same prompt; files come out numbered
  (`hero-bruto-1.jpg`, `hero-bruto-2.jpg`…).
- Prints `OK <path>` per image or `ERROR <legible detail>`. On ERROR, consult
  the error table above.
- **Generate into `<project>-ia/fotos-generadas/`** (the working folder), never
  straight into `assets/`. The chosen finals get converted to WebP into
  `assets/img/` (§8).

---

## 5. THE PHOTOGRAPHIC SCRIPT (write it before generating anything)

The historical failure: every photo requested with the same "professional
product photo, clean background…" prompt, two words changed. Result:
interchangeable images with no intent.

**The rule: one image = one call = one prompt written for that slot.**

Derive the script from the **design you've chosen** — the archetype and its
image slots (hero, gallery cells, feature-card details, lifestyle band,
backgrounds) dictate what images are needed, in what format, with what intent.
Before the first API call, write the full list (in your working notes):

| Field | What it holds |
|---|---|
| File | `hero.webp`, `gallery-2.webp`, `card-detalle-1.webp`… (final WebP name) |
| Slot | Which archetype slot it fills (hero / gallery cell / card / background) |
| Format | Exact `size` for that slot (e.g. `2048x1152`) |
| Framing | What's seen, from where, how much the subject occupies |
| **What makes it different** | The one phrase that sets it apart from EVERY other image in the script |
| Prompt | The full individual prompt |

Rules:

- **If you can't write "what makes it different", the image is redundant or
  ill-conceived.** Two images with the same differentiator → rethink one.
- Each prompt describes **a concrete scene**: place, light, camera angle, what
  the subject does, where the product sits, what emotion. Not "lifestyle photo
  of the product" but "low side angle of a runner in a park at dawn, golden
  rim light, breath visible, product sharp, face softly out of focus".
- A block with several images (mosaic, gallery, bento) = several calls, one per
  cell, each its own scene. NEVER "generate 4 varied images" in one call
  (`--n` makes variations of ONE scene to pick from, not different scenes).
- Think like a DP: vary the shot type (macro / medium / wide), context and
  composition, but keep it **one session** — define the light/background/color
  vocabulary in 1-2 sentences at the top of the script and paste it into every
  prompt.

---

## 6. ANCHOR IMAGES (this is where set coherence is decided)

Without a shared reference, every call "reinvents" the subject: tones shift,
materials drift, light changes per image. The defense:

1. **Generate 2-3 anchors first**: subject alone, clean, on the brief's neutral
   background, from 2-3 angles (front, side/back, detail). Made *with the user's
   photos as references*, at `medium`, and checked **against the real thing with
   a magnifying glass** (shape, exact color, seams, logo). These are the "truth"
   everything else copies. Keep in `<project>-ia/fotos-generadas/ancla-*.jpg`.
2. **Every later call carries the anchors as references** (plus whatever else it
   needs). 16 references per call is plenty.
3. **Optional fine styling:** once you have 1-2 approved section images that nail
   the mood, add them as style references too, asking in the prompt for "same
   light, palette and treatment as the reference images".

That's how scenes with different subjects still look like the same shoot: same
exact subject + same set vocabulary + same anchors.

---

## 7. THE BANNER CONTRACT (the #1 historical bug — obey all five clauses)

Symptom: the hero image "isn't panoramic enough" and the subject comes out
**cropped at the top** on the site. Real causes, in order: it was generated on a
canvas that wasn't the banner's and CSS `object-fit: cover` cropped the
difference; the aspect ratio was forced by prompt (which can't change the
canvas); nobody checked the result at the real ratios.

### Clause 1 — `size` IS the banner ratio

Every hero/banner is generated at its slot's **exact** ratio: **`2048x1152` for
16:9**, **`2688x1152` for 21:9** (cheap drafts `1280x720` / `1680x720`). Never a
"close-ish" canvas the CSS then crops, never square "the CSS will stretch it".
If a slot is more panoramic than 3:1, generate 3:1 and crop locally (clause 3).

### Clause 2 — Vertical safe zone in the prompt

Even at the right canvas, `object-fit: cover` still micro-crops when the real
window doesn't match the image ratio exactly. So the banner prompt MUST keep
what matters away from the edges: subject **complete, within the central ~70%
vertical band**, top and bottom edges only expendable background. Template:

> "Panoramic web-banner composition. The subject appears COMPLETE, occupying at
> most two-thirds of the frame height, vertically centered, with air above and
> below. Nothing important touching the top or bottom edge. Subject in the
> [right/left] third, clean negative space in the rest for overlaid text."

- **Contained-and-whole beats big-and-decapitated**; the text needs air too.
- Ask for an "extendable" background (gradient, studio, sky, texture) that
  survives a few cropped pixels.

### Clause 3 — Local crop, for anything not already at ratio

With clause 1 the generated banners are born at final ratio. The crop scripts
`recortar-banner.ps1` (Windows) / `.sh` (Mac) remain for: **user photos** used
as banners (any proportion — crop them to the slot ratio before `assets/`);
**re-framing** (cheaper than regenerating when the motif is off); **ratios more
panoramic than 3:1**.

```
powershell -ExecutionPolicy Bypass -File <skill-dir>/scripts/recortar-banner.ps1 `
  -Entrada hero-bruto.jpg -Salida hero-crop.jpg -Ratio 16:9 [-CentroY 0.5]
bash <skill-dir>/scripts/recortar-banner.sh hero-bruto.jpg hero-crop.jpg 16:9
```

**Invariant:** whatever enters `assets/img/` as a banner is ALREADY at the
slot's final ratio. After generating or cropping, **open the image and look**:
subject whole, air top and bottom? If not, regenerate (in `low` until it obeys,
then final quality). Never "fix" a bad banner by nudging CSS.

### Clause 4 — Mobile gets its OWN (vertical) image + `<picture>`

A landscape banner cropped to a phone (~9:19) is a lottery. For each hero,
generate a **second vertical image at `1152x2048`** (draft `720x1280`) with its
own prompt (same scene and light — pass the desktop banner and anchors as
references — vertical framing, subject whole in the central band, air for text).
Wire it with `<picture>`:

```html
<picture>
  <source media="(max-width: 640px)" srcset="assets/img/hero-mobile.webp">
  <img src="assets/img/hero.webp" alt="…" fetchpriority="high" loading="eager" decoding="async">
</picture>
```

(See `reference/05-image-and-asset-pipeline.md` §6 for the pattern.)

### Clause 5 — Verify the hero at two sizes before calling it done

With the site running, check the hero at **desktop 16:9 (1920×1080) AND mobile
(390×844)**: subject WHOLE (not a pixel cropped top/bottom), text legible over
the image, image covers the whole hero with no page-colored bands. If anything
fails, fix (regenerate / re-crop with a different `-CentroY` / adjust the CSS
focal position) and re-check BEFORE showing the user. This folds into the
skill's ⑥ Verify pass.

---

## 8. From generation to the site (the WebP handoff)

Generated files are JPEG in `<project>-ia/fotos-generadas/`. To put one on the
site:

1. If it's a banner from a user photo or a re-frame → crop to ratio (clause 3).
2. Convert the chosen file(s) to optimized WebP into the site's `assets/img/`:

   ```
   # Point webp_convert at a folder of the finals; it writes .webp to assets/img
   python <skill-dir>/scripts/webp_convert.py --src <project>-ia/finales --dst <project>/assets/img
   ```

   `webp_convert.py` names by prefix: `hero*` → 2000px hero treatment;
   `avatar*/portrait*` → 600px; `*thumb*` → 560px; else 1200px. Name the finals
   accordingly (`hero.jpg`, `gallery-1.jpg`, `card-detalle-1.jpg`) so they map to
   the right slot and come out as `hero.webp`, etc.
3. Reference them in HTML like any other image — hero with
   `<link rel="preload">` + `fetchpriority="high"`, everything else
   `loading="lazy"`. **All `.webp`, never mixed** (invariant #5).

The generated images become the **default** for each slot; the site owner can
swap any of them later just by replacing the file. Nothing about the site's
structure changes because an image was AI-generated vs stock vs their own.

---

## 9. Chained series (steps, before/after, storyboards)

Any group that tells a sequence is generated **in a chain**, not in parallel:

1. **Write the mini-story first**: one visible, distinct action per step. Test:
   cover the numbers — can you tell step 1 from 2 from 3 by the images alone? If
   not, change the gesture/framing/state between steps.
2. **Generate step 1** with the subject anchors as reference.
3. **Generate step 2 passing step 1's image as an ADDITIONAL reference**
   (`--ref paso-1.jpg --ref ancla-frontal.jpg …`) with: *"exactly the same
   scene, same person, same camera and same light as the reference; now
   [action of step 2]"*.
4. **Step 3 uses step 2's image**, same way.
5. **Review the series in a row**: same world, clearly distinct actions, legible
   progression. Regenerate the weakest.

Before/after with a slider: generate "before"; for "after" pass "before" as
reference and ask for *"the same framing, camera and light exactly, changing
only X"*. Overlay the pair to confirm before accepting.

---

## 10. Mask retouches (fix one area without touching the rest)

The edit endpoint accepts a **mask**: a PNG with alpha, same dimensions as the
FIRST `image[]`. Transparent areas mark what may be repainted; the rest is kept.
Use it when a photo is good except one detail (a warped logo → mask over it +
prompt describing the correct logo + an anchor where it's clear; a stray
background object → mask + "continuous studio background, no objects"; recolor
one part).

With the script: `--mascara zona.png` (the first `--ref` is the photo to fix).
Two caveats: the mask is a *guide* (the model may not respect the border to the
pixel — check the result), and to build the alpha PNG without design tools you
can script a transparent rectangle over the region. If a mask retouch doesn't
converge in 2 tries, regenerate the whole photo.

---

## 11. Writing the prompts (this decides quality)

1. **Describe the subject from what you SEE in the references** — material,
   exact color, shape, details (valve, seams, logo). The model is faithful to
   references, but the prompt must reinforce what can't be lost.
2. **Specify the background with intent, per destination:**
   - To FUSE with a section background (e.g. subject "floating" on the section's
     dark teal): ask for *"pure uniform background of the exact color #06110f,
     no cast shadow, no vignette, no gradient"* — use the SAME hex as the CSS.
     Never ask for transparent (gpt-image-2 can't; you'll get a checkerboard).
   - For a card/frame where depth reads well: *"light gray studio background with
     a soft realistic shadow under the subject"*.
3. **Photographic style:** "product/editorial photography, soft studio light,
   sharp focus, no text, no watermark, no people" (add people/context only for
   lifestyle shots).
4. **Text inside the image:** put it in quotes and in the site's language.
5. **Set coherence:** define the light/background vocabulary once in the script
   and paste it into every call, alongside the anchors.
6. Write prompts in any language you like (the model understands all); precision
   is what matters.

---

## 12. Recommended flow (compact)

1. User accepts → signup + key → `<project>-ia/clave-openai.txt`.
2. **Write the photographic script** (§5) from the chosen archetype's image
   slots: file, slot, exact `size`, framing, "what makes it different", prompt.
3. **Generate and approve the anchors** (§6), checked against the real subject.
4. Per script image: `low` variations with `--n 2/3` → pick → regenerate chosen
   at `medium` (`high` only for the hero), always with anchors as references.
   Banners: full contract (§7). Series: chained (§9). Small defects on an
   otherwise-good photo: mask (§10).
5. **WebP handoff** (§8) → integrate → preview → verify hero at 16:9 + mobile.
6. Note in your working notes which images are AI-generated (with a short prompt
   summary), which are the anchors, and the rough spend — so a later session can
   regenerate consistently.

Remember: the key and every working file stay in `<project>-ia/`. Only WebP
finals live in `<project>/assets/img/`, and only `<project>/` ever gets
deployed.
