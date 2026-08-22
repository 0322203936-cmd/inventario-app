# App Shell Design — this is a product, not a landing

A micro-SaaS tool is a page. A subscription SaaS is a **product with an account
around it**: someone logs in, sees what they have left, uses it, and pays to
keep using it. That shell is what makes the subscription believable — build it
even in mockup mode.

---

## 1. The four surfaces (and only these)

```
index.html      → LANDING: what it does, demo, pricing, CTA «Probar gratis»
app.html        → THE APP: the tool + credit counter (needs session)
cuenta.html     → ACCOUNT: plan, credits, history, invoices, cancel
precios.html    → PRICING (can live inside index.html as a section)
```

Plus the legal skeletons (`privacidad.html`, `terminos.html`) — required by
every payment platform before they approve a real account.

**Landing rules:** unlike a tool page, here the demo comes BEFORE the signup —
show the product working (a real before/after of the archetype, an embedded
30-second video or an interactive sample with 1 free credit). The pricing table
is the second most important element. Nothing else matters.

**App rules:** the opposite of the landing — zero marketing, zero animation.
Top bar with logo, credits pill (`⚡ 43 créditos`) and account menu; the tool
fills everything else. The tool card machinery is the same as in the micro-SaaS
skill: dropzone → `data-state` (idle → uploading → working → done → error) →
result with download. What changes is that the heavy work happens on the
server, so progress comes from the response, not from a local engine.

## 2. Credits: the unit of value

Everything is priced in credits — never in "tokens", "requests" or "API calls".
The user must understand what one credit buys them.

- Show the cost **before** acting: «Este documento tiene 8 páginas → 8 créditos».
- Show the counter **always**, in the top bar, and animate the decrease.
- Block **before** spending, not after: if credits < cost, show the upgrade
  modal instead of starting the job. Refund the credits if the job fails
  (`15-backend-proxy.md` covers the transaction order).
- Free tier: give enough to feel the value once (3-10 credits, one document),
  never enough to live on it.

Suggested plan shape (adapt to the archetype's real cost — see `05`):

| Plan | Credits/month | Price | Purpose |
|---|---|---|---|
| Gratis | 5 | 0 € | Try it once |
| Pro | 200 | 19 €/mes | The real plan |
| Empresa | 1.000 | 59 €/mes | The anchor that makes Pro look cheap |

Always show the annual option (2 months free) — it doubles cash up front and
is one line in the pricing table.

## 3. Accounts in mockup mode

Real login is NOT built in mockup mode — but the app must **behave** as if it
were real, or testing means nothing (`16-mock-subscription.md` implements it):

- Email + password stored server-side (hashed) in a JSON/SQLite file.
- Session cookie, `app.html` and `cuenta.html` redirect to the landing when
  there's no session.
- Credits per account, decremented server-side on every AI call.
- **A test account is created and handed over** at the end of the build, so
  the owner can click through the whole funnel: signup → free credits → run out
  → "upgrade" → simulated payment → credits recharged → cancel.

Everything about the payment is simulated and **clearly labeled** in the UI
(`MODO DEMO` badge), so nobody thinks money moved. Everything about the AI is
real — the product works from day one.

## 4. The pricing page (built for the real gateway from day one)

Build the pricing table with each plan's CTA as a `<a data-plan="pro"
href="#">`. In mockup mode a script intercepts it and runs the simulated
checkout. When the user goes live (`18-go-live-playbooks.md`), the ONLY change
is replacing those `href`s with the real checkout links — that's the whole
migration on the frontend side. Design it so this is a 2-minute edit, not a
rebuild.

Include, because payment platforms check for them before approving:
clear prices with currency and VAT statement, what a credit is, refund policy,
cancellation policy, contact email, company/freelancer identity, and links to
terms + privacy.

## 5. Visual identity

The app should look like a real SaaS: neutral base (light or dark), ONE accent
color, generous whitespace, cards with soft borders, `Inter`/`Manrope`-class
sans. Inline SVG icons only. The landing may have personality and movement; the
app must be calm and fast. Dark mode via `prefers-color-scheme` if it's cheap.

Non-negotiables: the credit counter and the primary action are always visible
without scrolling; errors are human sentences, never codes; and every
destructive action (delete history, cancel plan) confirms first.

## 6. Definition of done (product level)

- [ ] Landing shows the product working before asking for anything.
- [ ] Signup → app → run the archetype's happy path with a real file → result
      downloaded. Done in the http preview, not `file://`.
- [ ] Credits decrease server-side; a failed job refunds them.
- [ ] Running out of credits shows the upgrade modal, not an error.
- [ ] Simulated checkout recharges credits; cancel works; `MODO DEMO` visible.
- [ ] Test account handed to the user with its password.
- [ ] Legal pages exist and are linked; pricing states currency and taxes.
- [ ] The Gemini key appears NOWHERE in the frontend (grep the deployed files).
- [ ] JS off → landing and pricing still readable.
