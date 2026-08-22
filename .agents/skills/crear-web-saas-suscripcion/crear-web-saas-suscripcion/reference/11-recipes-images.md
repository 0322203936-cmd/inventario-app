# Recipes — Pattern D: image generation

Five archetypes that take a photo and give back new images. All generation runs
**server-side** (`15-backend-proxy.md`); models and per-image prices in
`05-gemini-api.md` §2.

**These archetypes cost real money per action** (~0,045-0,15 € per image). The
credit maths matters more here than anywhere else: never ship a plan whose
included images cost more than the price.

---

## Shared machinery

**The call:** `gemini-3.1-flash-image` (default) on the same
`generateContent` endpoint as everything else — full snippet in
`05-gemini-api.md` §9. Input = prompt + the user's photo as `inline_data`;
it accepts **up to 10 input images**, which is what makes "product + scene"
and "design + mockup" work.

**These archetypes require a paid key** — image generation has no free tier,
unlike the text/vision archetypes. Tell the owner before building: the free
Gemini key that powers the rest of the catalog will return an error here, and
they need billing enabled on the same key.

Read the result from `candidates[0].content.parts[]` — the part carrying
`inline_data` is the image. Return it to the browser in the response body;
never save it to a public folder.

**Prompt craft (this is where quality lives):** describe the *photograph*, not
the wish. Camera and lens, lighting, surface, background, mood, and an explicit
**"keep the product/person exactly as in the reference"** clause. Short prompts
give generic results; three or four sentences of concrete visual language give
the studio look. Keep the prompts in `lib/manifest.js` as editable presets so
the owner can tune them without touching code.

**Resolution and cost:** default to 1K for previews (cheap) and offer 2K/4K as
the paid perk («descarga en alta resolución»). Charge more credits for higher
resolution — the cost scales the same way.

**SynthID:** every generated image carries an invisible Google watermark. State
it in the FAQ. Don't claim the images are indistinguishable from originals for
legal/documentary purposes.

**UI:** always show the original next to the result (before/after slider or
side-by-side), always allow "generar otra variante" (a new call = a new
credit — say so), and keep a session gallery so nothing gets lost on reload.

**Consistency across a batch:** to keep a whole catalog looking alike, send the
same style-reference image with every generation (the model supports style
references) and reuse the exact same prompt template. Do NOT rely on a "seed" —
treat consistency as a prompting job.

---

## D.1 · `fotos-producto`

Input: one amateur product photo. Output: clean studio shot and/or lifestyle
scene. Presets to ship: fondo blanco puro (marketplace), mármol de cocina,
madera cálida, superficie de hormigón, exterior con luz natural, flat-lay
cenital.

Prompt skeleton:
> Place this exact product on <surface>. <Lighting description>. <Background
> description>. Studio product photography, <lens>, soft shadows grounding the
> product. **Keep the product's shape, colour, label and proportions exactly as
> in the reference image — do not redesign it.**

Extras that sell: batch mode (whole catalogue, one preset), marketplace export
sizes (square 1:1 for Amazon/Shopify), and a "misma escena para todos los
productos" toggle that reuses one style reference.

Honest limit for the UI: text on labels can distort — review before publishing.

## D.2 · `foto-estilos`

Input: a photo (usually a portrait). Output: the same photo in N styles.
Ship 8-12 presets (acuarela, óleo, cómic, anime, cyberpunk, retrato de
estudio B/N, ilustración infantil, pixel art…), each a full prompt in the
manifest.

Prompt skeleton:
> Reimagine this photo as <style>, <medium and technique details>. **Preserve
> the person's facial features, pose and composition** — same identity, new
> medium.

The volume archetype: 1 credit per style, generous free tier (3 credits),
shareable result card. Add a hard rule in the UI copy: no uploading photos of
other people without consent — and route the prompt away from any request to
make someone look nude, younger/older for deceptive purposes, or to place a
real person in a compromising scene. Refuse those in the server prompt
guardrails, not just the UI.

## D.3 · `diseno-interiores`

Input: a photo of a room. Output: the same room redecorated. Styles: nórdico,
industrial, japandi, mediterráneo, clásico, minimalista.

Prompt skeleton:
> Redecorate this room in <style>. **Keep the architecture identical: same
> walls, windows, doors, ceiling height and camera angle.** Replace furniture,
> textiles, lighting and decoration. Photorealistic interior photography,
> natural light from the existing windows.

The architecture-preservation clause is the whole trick — without it the model
invents a different room and the tool feels broken. Modes worth adding: «solo
cambiar paredes y suelo», «amueblar habitación vacía» (virtual staging for
estate agents — a strong B2B upsell).

## D.4 · `restaurar-fotos`

Input: damaged/faded/black-and-white photo. Output: restored, optionally
colorized.

Prompt skeleton:
> Restore this old photograph: repair scratches, tears, stains and fading;
> recover detail; correct exposure. **Preserve the exact identity, clothing,
> era and composition of the people — invent nothing.** <If colorizing:> Add
> natural, period-accurate colour.

Two buttons, two credits: «restaurar» and «restaurar y colorear». Emotional
product — the before/after slider IS the marketing; make it the landing hero.
Honest note in the UI: colours are a plausible reconstruction, not the real
historical colours, and faces may shift subtly — offer «generar otra versión».
High-resolution download is the natural paid perk.

## D.5 · `mockups-producto`

Input: a design/logo (PNG, ideally transparent) + optionally a base photo.
Output: the design applied to t-shirts, mugs, tote bags, packaging, signage,
phone cases.

Prompt skeleton (two input images: design + product reference):
> Apply this design onto the <product> in the second image. Follow the fabric
> folds and perspective, respect the lighting of the scene. **Keep the design's
> proportions, colours and text exactly as provided — do not redraw it.**
> Commercial product photography.

The premium action: «pack de 10 mockups» — one click, ten products, ten
credits, downloaded as a zip. Print-on-demand sellers will pay monthly for
exactly that.

---

## Definition of done (images)

Generate with a REAL user photo (not a stock image) for each preset the UI
offers — a preset that produces garbage must be fixed or removed, never
shipped. Confirm: the credit drops once per generated image, a failed
generation refunds it, the result downloads at the advertised resolution, and
the before/after shows the original unmodified. Then the product checklist in
`03` §6.
