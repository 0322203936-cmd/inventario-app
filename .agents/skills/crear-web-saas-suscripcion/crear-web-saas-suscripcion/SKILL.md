---
name: crear-web-saas-suscripcion
description: Build a real AI SaaS with subscriptions on Hostinger, guided end to end. (a) CONNECT the Hostinger account to Claude Code. (b) BUILD a SaaS powered by Gemini from an 11-archetype catalog (redact PDFs, invoices to Excel, contract analysis, handwriting to notes, document translation, product photos, photo restyling, interior design, photo restoration, mockups, meal macros), with a secret-safe server proxy, real accounts and credits, a clearly-labelled MOCK payment system and a test account. (c) PUBLISH it to Hostinger. (d) GO LIVE - once tested, ask where the owner lives, recommend the payment platform available there and walk them from mock checkout to real charges. Use whenever the user wants a SaaS, a paid AI web app, a subscription site, an app with credits or plans, or wants to switch a demo checkout to real payments. Triggers include crea un saas, una web de suscripcion, una app con creditos, cobrar suscripciones en mi web, pasar a pagos reales, and their English equivalents.
---

# SaaS Studio · v2 — connect · build · publish · go live

Four **independent capabilities** for building a real AI SaaS with
subscriptions. Same studio logic as the sibling skills: read which door the
person walked through, do that well, verify it, stop.

- 🔌 **Connect** the Hostinger account to Claude.
- 🧠 **Build** the SaaS: AI product + accounts + credits + **mock payments**.
- 🚀 **Publish** it live to Hostinger (frontend + server proxy).
- 💳 **Go live**: swap the mock checkout for a real payment gateway, chosen by
  the owner's country and walked step by step.

**What makes this different from a micro-SaaS:** the AI costs money per use, so
there is a server proxy holding the key, accounts, and a credit ledger. The
money side ships as a **labelled mockup** first, and becomes real in 💳 — never
before, because payment platforms require a finished, working product to
approve an account.

**What v2 changed (learned in production — read these, they each cost a real
debugging session):**
- **Claude Haiku is the default AI engine** for text/document archetypes, with
  Gemini as automatic fallback. Gemini's free 2.5 models are retired for new
  keys and its structured-JSON output breaks intermittently; Claude is steadier
  and cheaper on text. Details and the exact call in `05-gemini-api.md`.
- **The credit ledger and accounts live OUTSIDE `public_html`.** A static deploy
  wipes the web folder, so a database inside it erases every customer on the
  next publish. This is the single most dangerous bug in the skill — `15` §4.
- **`censurar-pdf` no longer trusts the AI for coordinates.** The browser does
  the OCR (pdf.js text layer for digital PDFs, Tesseract.js for scans) and the
  AI only says *which* text is personal data. Real, verified redaction plus a
  manual-box tool. Full rewrite in `06-recipes-documents.md`.
- **Keys never travel through chat.** The owner pastes them into `setup.php` in
  their browser; if one slips into the conversation anyway, save it and tell
  them to rotate it. `15` §10.

---

## THE GOLDEN RULE: do only what was asked, then stop

- *"conéctame Hostinger"* → only connect and verify.
- *"hazme un SaaS que censure PDFs"* → only build (with mock payments). Don't
  publish, don't set up payments.
- *"publícala"* → only publish.
- *"quiero cobrar de verdad"* → only the go-live guidance.

At the end you may offer **one** sentence naming the natural next step. Never
start it unprompted. Read the state from context each time (connected? project
exists? published? still in mock mode?).

---

## Route the request → capability

| What they say / the situation | Capability | Primary ref |
|---|---|---|
| "conéctame Hostinger", "vincula mi hosting" | 🔌 **Connect** | `12-hostinger-connect.md` |
| "hazme un SaaS de…", "una app que…", "quiero cobrar por…" | 🧠 **Build** | the build sequence below |
| "¿qué SaaS me recomiendas?", "dame ideas" | 🎯 **Recommend** | `02-saas-catalog.md` |
| Project exists: "cambia…", "añade…", "otro plan" | ✏️ **Edit** | existing files + invariants |
| "publícala", "súbela", "ponla online" | 🚀 **Publish** | `13-hostinger-deploy.md` + `15-backend-proxy.md` §6 |
| "quiero cobrar de verdad", "pasarela real", "conectar Stripe/Polar" | 💳 **Go live** | `17-payments-by-country.md` → `18-go-live-playbooks.md` |
| "no funciona", "se ve vieja", "da error" | ✅ **Verify** | `08`, `10`, `15` §7 |

---

## 🧠 The build sequence (the heart of this skill)

Unlike the sibling skills, a build here IS a short guided sequence. Run it in
order, and don't skip the questions — the archetype and the plan shape decide
the whole architecture.

### Step 0 — Is Hostinger connected?
Check first. If it isn't, say so in one line and offer to connect
(`12-hostinger-connect.md`). If they'd rather build locally first, that's
fine — build now, connect before publishing. Never connect silently.

### Step 1 — What service does it offer?
Match to an archetype in `02-saas-catalog.md`, or map a new idea to its closest
pattern. If they didn't name one, offer 2-3 picks matched to their situation
(🎯 in `02`). One question, not an interview. Also settle the **niche and
language** here if it isn't obvious.

### Step 2 — What subscription model?
Ask ONCE, offering a sensible default they can just accept
(`intake-template.md` has the wording). What you need: free-tier size, one or
two paid tiers with price and monthly credits, and what one credit buys. Cost
per use from `05-gemini-api.md` decides whether the numbers are sane — if their
price would lose money on Gemini calls, say so with the arithmetic and propose
numbers that work.

### Step 3 — Build it
1. Front: landing + app + account + pricing per `03-app-shell-design.md`,
   stack per `01-stack-and-conventions.md`.
2. Server: proxy per `15-backend-proxy.md` (holds the AI key, checks and
   decrements credits, stores accounts **outside `public_html`**). PHP by
   default — same deploy as the site, no build.
3. AI: the archetype's recipe (`06-recipes-documents.md` /
   `11-recipes-images.md`) + `05-gemini-api.md` for engines, prompts and cost.
   Default engine is **Claude Haiku**, Gemini fallback (`05` §1).
4. Money: mock system per `16-mock-subscription.md`, with the `MODO DEMO`
   badge visible.
5. Libraries: `scripts/descargar-librerias.py <arquetipo>` (pins in `14`).

### Step 3b — The AI key, without friction
The build works the moment the code is deployed, but the AI only answers once a
key is stored. Handle it the friendly way:
- **Never ask for the key in chat.** Deploy `setup.php` and send the owner one
  link: they paste the key in their own browser, it is validated live against
  the provider and saved on the server, out of reach of anything downloadable.
- The setup page **auto-detects the provider** — Anthropic (`sk-ant-…`) or
  Google (`AIza…` / `AQ.…`) — and saves each to its own file. One key is enough
  (Claude); a second (Gemini) just adds a fallback.
- **If a key still lands in the conversation** (the owner pastes it anyway),
  save it for them so nothing blocks, then tell them plainly to rotate it,
  because chat history is not a safe place for a secret.

### Step 4 — Test it, then hand over a test account
Run the full funnel yourself in the http preview OR the deployed site, driving a
real browser: signup → use the tool with a **REAL file** → credits drop
server-side → run out → upgrade modal → simulated payment → credits recharge →
cancel. For document archetypes, open the downloaded result and **prove the
redaction is real** (select-all, search the bytes — zero hits). Then create the
test account and give the user its credentials plus the click-path (`16` §6).
**The build is not done until this path passes**, and a redeploy in the middle
must not wipe the account you just created (`15` §4).

### Step 5 — Offer the next step (one line)
«¿La publico en tu hosting?» or, if already published, «¿pasamos a cobros
reales?». Then stop.

---

## 💳 Go live (only when they ask, only after it's tested)

Never before the product works — every platform reviews the live site and
rejects half-built ones. The sequence:

1. **Confirm it's tested and published.** If it's still local, publish first.
2. **Ask where they live** (or where the company is registered) and whether
   they're an individual/autónomo or a registered company. That's it — two
   facts.
3. **Recommend the platform** from `17-payments-by-country.md`, which maps
   country → what's actually available, with fees, merchant-of-record status
   and the tax implications. Give ONE recommendation plus one alternative, in
   two lines. Don't lecture.
4. **Walk them through it** with the platform's playbook in
   `18-go-live-playbooks.md`: account, verification, product, price, checkout
   link, keys, webhook. They click in their browser; you do everything on the
   code side and verify each step before moving on.
5. **Swap the mockup**: checkout links, webhook handler, credit recharge, and
   **remove the `MODO DEMO` badge** (`18` has the exact checklist).
6. **Verify with a real test purchase** in the platform's test mode, then one
   real charge if they want certainty. Confirm credits landed in the account.

Honesty rules for this capability: never promise approval (platforms reject
accounts), never give tax or legal advice beyond "this platform handles VAT for
you / this one doesn't, ask your gestor", and never touch their banking or
identity data yourself — they enter it in the platform's own site.

---

## Always-on invariants

**Communication:** the user is **non-technical**. Zero jargon — no "proxy",
"endpoint", "webhook", "hash", "API". Say "el servidor que guarda tu clave",
"el aviso que manda la plataforma cuando alguien paga". Run every command
yourself; the only manual steps are browser clicks (Hostinger login, payment
platform signup). Announce before acting, celebrate milestones (✅), never show
a raw error, **verify before claiming**.

**Security (non-negotiable — money and secrets are involved):**
1. **The AI key lives only on the server.** Never in HTML/JS/anything the
   browser downloads. Grep the deploy before publishing (`15` §7).
2. **Credits are checked and decremented server-side**, before the AI call, in
   that order, with a refund if the call fails. Client-side counters are
   decoration.
3. **Passwords are always hashed** (bcrypt/argon), even in mockup mode.
3b. **Accounts and credits persist OUTSIDE `public_html`.** `hosting_deployStaticWebsite`
   replaces the whole web folder on every publish; a JSON/SQLite database inside
   it is erased — every customer, gone — the next time you update the site.
   Store it one level above `public_html` (`15` §4). Verify by redeploying and
   confirming the test account still logs in.
3c. **Right engine for the archetype.** Text/vision/document archetypes default
   to **Claude Haiku** (steady on text, cheap), Gemini as fallback. **Image
   archetypes need Gemini billing** (no free tier). Archetypes handling personal
   data (redaction, payslips, contracts) should run on a **paid** tier before
   real customers arrive — free tiers may train on submitted content. Say which
   case applies, once, plainly (`05` §3).
4. **No real payment data ever touches this code.** Real checkout always
   happens on the platform's hosted page. If a user asks you to build a card
   form that collects numbers, refuse and explain why.
5. **The mockup announces itself** (`MODO DEMO`) until go-live removes it.
6. Never commit or paste keys into chat, files the user shares, or the repo. If
   the owner pastes one into chat, it is compromised: save it, then tell them to
   rotate it.

**Product invariants:**
7. **The AI is real from minute one** — only the money is simulated. A demo
   that fakes the AI teaches nothing and sells nothing.
8. **Show the cost before spending it**, block before the call when credits are
   short, and never fail silently.
9. **State the limits honestly** in the UI (file sizes, pages, "estimates, not
   measurements", "informational, not legal advice").
10. **Uploaded files are the user's**: don't store them longer than the job
    needs, say so in the privacy page, and delete temporary files.
11. **The human keeps the last word.** For anything the AI locates or decides
    (redactions, extracted fields, flagged clauses), the app must let the user
    review, toggle each item, AND add what the AI missed by hand — a manual
    override, not just accept/reject. The buyer is liable for the result; give
    them the controls to be.
12. **Errors are human sentences shown in the page, never `alert()`.** A blocking
    `alert()`/`confirm()` freezes a background tab and reads as a crash. Use a
    small in-page toast/notice; keep `confirm()` only for truly destructive,
    user-triggered actions.

**Web quality invariants** (shared, full detail in `04-critical-gotchas.md`):
classic `<script defer>` + IIFE; `.htaccess` + `?v=YYYYMMDD` cache-busting;
content hardcoded in HTML (JS enriches); `safe()` around inits; content first,
animation second; robustness > spectacle; verify before claiming. The ESM
bridge amendment in `01` §16 applies here too (dynamic `import()` for
ESM-only libraries; preview over http, never `file://`).

---

## Environment

- 🔌 Connect needs **Node.js 24+** (`scripts/diagnostico.*`).
- 🧠 Build needs **Python 3** (helpers + local preview server). The preview
  server is mandatory: sessions, cookies and the server proxy don't work on
  `file://`.
- The **server proxy runs on the Hostinger plan itself** — PHP by default (no
  build, deploys with the site), Node/Express as the alternative (`15` §5).
  A separate VPS is never required.

---

## Files index

```
SKILL.md                              ← this file — the router + build sequence
intake-template.md                    ← the two questions worth asking
recommended-settings.json             ← optional zero-prompt pre-authorization
evals/evals.json                      ← capability-routing evals
reference/
  01-stack-and-conventions.md         ← file structure, IIFE, ESM bridge (shared)
  02-saas-catalog.md                  ← the 11 archetypes in 4 AI patterns
  03-app-shell-design.md              ← landing + app + account + pricing
  04-critical-gotchas.md              ← the web invariants, in full (shared)
  05-gemini-api.md                    ← models, prompts, structured output, cost
  06-recipes-documents.md             ← read/extract/locate archetypes
  07-windows-troubleshooting.md       ← (shared)
  08-pre-deploy-checklist.md          ← the verify pass (shared)
  09-environment-detection.md         ← (shared)
  10-deployment-and-cache.md          ← cache-busting + .htaccess (shared)
  11-recipes-images.md                ← image-generation archetypes
  12-hostinger-connect.md             ← 🔌 connect the account (shared)
  13-hostinger-deploy.md              ← 🚀 publish to Hostinger (shared)
  14-library-pinning.md               ← pinned versions + vendoring
  15-backend-proxy.md                 ← the server: key, credits, endpoints
  16-mock-subscription.md             ← accounts, credits, mock checkout, test account
  17-payments-by-country.md           ← 💳 which platform per country
  18-go-live-playbooks.md             ← 💳 step by step to real charges
templates/
  htaccess.template                   ← copy as `.htaccess` to every root
  api-gemini.php.template             ← the AI call: models, limits, key (copy to api/gemini.php)
  setup.php.template                  ← one-time key setup from the browser
scripts/
  diagnostico.ps1 / .sh               ← environment check for the connection
  descargar-librerias.py              ← vendor pinned libs per archetype
  verify_project.py                   ← post-generation sanity check
```

---

## Final note

Build the product first, make the money real last. When they say *"hazme un
SaaS"* they get something that genuinely works, that they can test with their
own account, and that they can start charging for the day they decide to —
without rebuilding anything.
