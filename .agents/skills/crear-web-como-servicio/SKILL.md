---
name: crear-web-como-servicio
description: Build premium client websites to SELL to businesses on Hostinger, guided end to end. (a) CONNECT the Hostinger account. (b) BUILD an agency-grade static website (HTML/CSS/vanilla JS, no build) for any business niche - solar installers, clinics, restaurants, law firms, gyms - that looks like a $30.000 project. (c) IMAGES - free stock (Openverse) or bespoke AI images via an OpenAI key. (d) AI FEATURES - add a Gemini support chat assistant, a document/photo reader (e.g. read an electricity bill), interactive calculators and lead capture, on the free Gemini tier with a secret-safe server proxy. (e) PUBLISH to Hostinger and connect a domain to sell it. Use whenever the user wants a web for a client or business, a web to sell as a service, an agency landing, to add an AI assistant or calculator to a site, or to fill a site with images. Triggers include crea una web para un cliente, una web para vender, una landing de agencia, anade un asistente de IA, una calculadora, rellena la web con imagenes.
---

# Web-as-a-Service Studio · v1 — connect · build · images · AI · publish

Five **independent capabilities** for building **premium websites you sell to
businesses**. This is the "$38.000 web" play: create a studio-grade site for a
niche (solar installers, clinics, restaurants, law firms…), make it feel
expensive, add real AI features most agencies can't, and sell it. Same studio
logic as the sibling skills — read which door the person walked through, do
that, verify it, stop.

- 🔌 **Connect** the Hostinger account to Claude.
- 🎨 **Build** an agency-grade static site for a business niche (wow factor).
- 🖼️ **Images** — free stock (Openverse) or bespoke AI (OpenAI gpt-image key).
- 🧠 **AI features** — Gemini support chat, document/photo reader, interactive
  calculators, lead capture, on the free tier with a secret-safe proxy.
- 🚀 **Publish** to Hostinger and connect a domain to sell it.

**What makes this different from the other skills:** the site is for a CLIENT,
not the owner. The value is *agency-grade craft + AI features that justify the
price*. The reference is the solar-panels site: a premium landing + an AI
assistant + an interactive savings calculator that reads the customer's
electricity bill with AI. This skill reproduces that playbook for any niche.

It inherits the full build + image engine (archetypes, effects, gotchas,
Openverse stock, OpenAI gpt-image, deploy) and adds the **AI-features layer**
(`reference/14-ai-features.md`) on top.

---

## THE GOLDEN RULE: do only what was asked, then stop

- *"conéctame Hostinger"* → only connect and verify.
- *"hazme una web para una empresa de X"* → only build it (placeholders for
  images unless asked). Don't add AI, don't deploy.
- *"rellénala con imágenes"* → only images (stock, or AI if they gave a key).
- *"añádele un asistente de IA / una calculadora"* → only the AI feature.
- *"publícala / ponle el dominio"* → only publish.

At the end offer **one** sentence naming the next step. Never chain by reflex.
Read the state each time: connected? project exists? has images? has AI? live?

---

## Route the request → capability

| What they say / the situation | Capability | Primary ref |
|---|---|---|
| "conéctame Hostinger", "vincula mi hosting" | 🔌 **Connect** | `12-hostinger-connect.md` |
| "hazme una web para [empresa/nicho]", no project yet | 🎨 **Build** | `02-archetypes.md` + `06` + `01` + `15-selling-the-web.md` |
| A project exists and "cambia…/ añade sección/ otro color" | ✏️ **Edit** | existing files + invariants |
| "rellénala con imágenes", "fotos de stock", "genera imágenes con IA" | 🖼️ **Images** | `05-image-and-asset-pipeline.md` + `11-ai-image-generation.md` |
| "añade un asistente de IA / un chat", "una calculadora", "que lea la factura/el documento", "captura de leads" | 🧠 **AI features** | `14-ai-features.md` |
| "publícala / súbela / ponle mi dominio" | 🚀 **Publish** | `13-hostinger-deploy.md` |
| "¿qué nicho vendo?", "¿a quién se la vendo?" | 🎯 **Sell** | `15-selling-the-web.md` |
| "¿está lista?", "se ve rota/vieja", "el chat no responde" | ✅ **Verify** | `08`, `10`, `07`, `14` §Verify |

Capabilities compose when the user asks for the whole thing ("conéctame y
súbeme una web para una clínica con asistente de IA e imágenes" → 🔌 → 🎨 → 🖼️
→ 🧠 → 🚀). Compose because they asked, never by reflex.

---

## The build sequence (a sellable site)

1. **Pick the niche and the pitch.** What business is this for? The niche
   decides the archetype, the copy and — crucially — which AI feature makes it
   sellable (`15-selling-the-web.md`). A solar installer wants a bill-reading
   savings calculator; a clinic wants an appointment assistant; a restaurant
   wants a reservation/AI-menu helper.
2. **Build the premium site** with ONE archetype (`02-archetypes.md`, honor the
   diversity rules `06`), agency-grade, per `01-stack-and-conventions.md` and
   the invariants. Ship it with tasteful placeholders and real, specific copy —
   never lorem ipsum, never invented client testimonials presented as real
   (mark demo content as demo).
3. **Images** (`05` + `11`): stock by default (free), OpenAI gpt-image if the
   user provides a key and wants bespoke. Everything ends as WebP.
4. **AI features** (`14-ai-features.md`): the differentiator. Add the Gemini
   support chat and/or the document reader + interactive calculator + lead
   capture, on the free tier, with the secret-safe PHP proxy, rate limiting and
   `setup.php` for the key. This is what makes the site worth thousands.
5. **Publish** (`13`) and, to sell it, connect the plan's free domain so the
   demo has a real, professional URL (`15`).

Each step is independent — run only what's asked.

---

## Always-on invariants

**Communication:** the user is **non-technical**. Zero jargon — never say
"proxy", "endpoint", "API", "MCP", "deploy". Say "el asistente", "la clave de la
IA", "los archivos del diseño", "publicar la web". Run every command yourself;
the only manual steps are browser clicks (Hostinger login, pasting an API key
into `setup.php`). Announce before acting, celebrate milestones (✅), never show
a raw error, verify before claiming.

**Web quality invariants** (inherited, full detail in `04-critical-gotchas.md`):
classic `<script defer>` + IIFE + `window.__BRAND__`; `.htaccess` in every root +
`?v=YYYYMMDD`; native scroll by default; reduced-motion gates only intrusive
effects (Windows ships it ON — `07`); all images WebP; hardcode content in HTML
(JS enriches); `safe()` around inits; IntersectionObserver threshold ≤ 0.05 +
timeout; splash double safety net; content first, animation second; robustness >
spectacle; **one archetype, never two**; verify before claiming.

**AI-feature invariants** (full detail in `14-ai-features.md`):
1. **The AI key lives ONLY on the server.** Never in HTML/JS. The browser talks
   to a same-domain PHP proxy; the key sits outside `public_html` or in a `.php`
   that's never served as text. Grep the deploy before publishing.
2. **Free Gemini tier by default**, with per-IP and a global daily cap that
   protects the quota (the proven pattern). Say plainly that a client with real
   traffic should move to a paid key, and that the free tier trains on submitted
   content — so a feature handling personal data (bills, documents) belongs on a
   paid key before real customers use it.
3. **Never invent what the AI extracts.** A missing field is "—", not a guess.
   The AI reads real documents; editorial/marketing copy stays separate.
4. **Graceful fallback always.** If the key isn't set or the AI fails, the
   feature degrades to a human message or a manual form — never a dead UI.
5. **Lead capture is honest.** If the site collects emails/phones, say what
   happens with them and store them where only the owner can read them
   (`lead.php` pattern, protected `datos/`).

**Selling invariants** (`15-selling-the-web.md`): demo content is clearly demo;
never fabricate a real business's reviews, certifications or claims; the $38.000
figure is Clutch's average, cited honestly, not a promise of earnings.

If an invariant and a flourish conflict, the invariant wins.

---

## Environment

- 🔌 Connect needs **Node.js 24+** (`scripts/diagnostico.*`).
- 🎨 Build needs **Python 3** (helpers, WebP, local preview). Degrades
  gracefully without it (`09`).
- 🖼️ AI images need **Node 18+** and the user's **OpenAI key** (`11`).
- 🧠 AI features run on the **PHP of the Hostinger plan itself** (no VPS): the
  proxy is plain PHP + cURL against Gemini's free tier. Needs a **Gemini API
  key** the owner gets free from Google AI Studio, pasted once via `setup.php`.
- Install what's missing yourself; only ask the user to install something if
  every automatic path failed.

---

## Files index

```
SKILL.md                                ← this file — the router + build sequence
intake-template.md                      ← the few questions worth asking
recommended-settings.json               ← optional zero-prompt pre-authorization
evals/evals.json                        ← capability-routing evals
reference/
  01-stack-and-conventions.md           ← file structure, IIFE, script order
  02-archetypes.md                      ← 10 archetypes (pick ONE)
  03-effects-catalog.md                 ← 40+ copy-paste effects
  04-critical-gotchas.md                ← the web invariants, in full
  05-image-and-asset-pipeline.md        ← photos: user / Openverse / AI / WebP
  06-diversity-guardrails.md            ← never clone; rotate archetypes
  07-windows-troubleshooting.md         ← reduced-motion + the 3-machine test
  08-pre-deploy-checklist.md            ← the verify pass
  09-environment-detection.md           ← Node/Python/curl detection
  10-deployment-and-cache.md            ← cache-busting + .htaccess strategy
  11-ai-image-generation.md             ← OpenAI gpt-image bespoke imagery
  12-hostinger-connect.md               ← 🔌 connect the account
  13-hostinger-deploy.md                ← 🚀 publish to Hostinger
  14-ai-features.md                     ← 🧠 Gemini chat, doc reader, calculators, leads
  15-selling-the-web.md                 ← 🎯 niche, pitch, find clients, $38k framing
templates/
  htaccess.template                     ← copy as `.htaccess` to every root
  asistente-ia.php.template             ← Gemini support-chat proxy (free tier)
  lector-documento.php.template         ← read a bill/photo/PDF → JSON (multimodal)
  setup-ia.php.template                 ← paste the Gemini key once, from the browser
  knowledge.php.template                ← the assistant's persona + knowledge base
  lead.php.template                     ← capture emails/phones to a protected file
  geocode.php.template                  ← optional: address → coords for map features
scripts/
  diagnostico.ps1 / .sh                 ← environment check for the connection
  download_libs.py / .sh                ← GSAP/ScrollTrigger to lib/
  openverse_fetch.py / .sh              ← free stock images (no key)
  webp_convert.py                       ← any image → optimized WebP
  generar-foto.mjs                      ← OpenAI gpt-image generator
  recortar-banner.ps1 / .sh             ← crop to exact banner ratio
  verify_project.py                     ← post-generation sanity check
```

---

## Zero-prompt mode

Merge `recommended-settings.json` into `~/.claude/settings.json` once to
pre-authorize this skill's scripts, the Hostinger connection commands, the image
helpers and the preview server. Nothing destructive.

---

## Final note

Build a site a business would pay thousands for, give it AI features their
current agency can't, and put it live on a real domain to close the deal. When
they say *"hazme una web para un cliente de X"* you hand them a studio-grade site;
*"añádele un asistente de IA"* you hand them the feature that justifies the price;
*"publícala"* you hand them a live URL to sell.
