# Intake — the few things worth asking (v2 is light on this)

v2 doesn't run an intake wizard. Most sessions need **zero or one** question:
you infer the brief and decide palette/fonts/layout/effects yourself. Only ask
what you genuinely can't infer, and ask it in **one** short message.

## First, route (don't ask yet)

Read the request against the routing table in `SKILL.md`. If it's a surgical
edit, an image ask, or a design-direction ask, you usually need **no** intake at
all — just do the thing. Reserve questions for a **full build** with a thin
brief.

## For a full build — ask at most these, once

This skill builds a site for a CLIENT/business, so the niche matters. Only ask
what their message didn't answer:

1. **Niche / business** — what business is the web for (paneles solares,
   clínica, restaurante, despacho…). This drives the archetype, the copy AND
   which AI feature makes it sellable (`15-selling-the-web.md`). Infer if given.
2. **Brand name** — the business name (invent a plausible one for a demo if
   there's no real client yet, and say it's a demo name).
3. **Images** — which source? Offer plainly:
   - "usa imágenes de stock" → free CC from Openverse (default).
   - "genera imágenes a medida con IA" → bespoke, ~2-3 € de OpenAI
     (`reference/11-ai-image-generation.md`).
   - "tengo fotos del cliente" → drop them in `assets/photos/source/`.
4. **AI feature?** — the differentiator. «¿Le añadimos un asistente de IA y/o una
   calculadora inteligente (p.ej. que lea la factura de la luz)?» Default: build
   the site first, offer the AI feature as the next step (it needs a free Gemini
   key). Don't force it into the first build unless asked.
5. **Main goal / CTA** — pedir presupuesto / reservar / contactar / llamar.
   Infer from the niche if obvious.

Template (Spanish — translate to the user's language):

> Para clavarlo necesito un par de cosas:
> 1. **¿Para qué negocio?** (el nicho: paneles solares, clínica, restaurante…).
> 2. **Nombre** (si aún no hay cliente, te propongo uno de ejemplo).
> 3. **Imágenes**: ¿banco de imágenes gratis, o te las genero a medida con IA
>    (unos 2-3 € de créditos)?
> 4. La monto primero y, si quieres, luego le añadimos un **asistente de IA** o
>    una **calculadora inteligente** que la hagan mucho más vendible.
>
> El diseño, colores y efectos los decido yo.

## Never ask

The skill decides these — asking is a mistake:
palette, fonts, layout, which effects, "do you want a custom cursor?", any tech
decision. (See the invariants in `SKILL.md`.)

## After they reply

Acknowledge in one line, then go quiet and build. If they left gaps: images →
Openverse stock; pages → one; CTA → infer from industry; anything else →
sensible default for the archetype. Tell them when it's ready — don't narrate
every step.
