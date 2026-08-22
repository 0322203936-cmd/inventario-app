# 💳 Go Live — from mock checkout to real charges (verified July 2026)

Only run this when the product is **built, published and tested**. Every
platform reviews the live site; half-finished ones get rejected.

The user clicks in their browser. You do everything on the code side and
**verify each step before moving to the next**. Never ask them to paste a
secret key into the chat — have them save it, and you write it into the server
config file yourself (`15-backend-proxy.md` §2).

---

## 0. The order that always applies

1. Pick the platform (`17-payments-by-country.md` — country decides).
2. Create the account and start verification (it takes days — **start it
   first**, then keep working).
3. Create product + recurring price (+ trial if wanted).
4. Get the checkout link → replace the mock buttons.
5. Create the webhook + secret → wire the credit recharge.
6. Test in sandbox with a test card, end to end.
7. Switch to production keys, **recreate the catalog in live mode**, remove the
   `MODO DEMO` badge.
8. One real purchase with a real card. Refund it. Then it's live.

**The universal gotcha:** sandbox and production are separate worlds in ALL
four platforms. Products, prices, webhooks and keys created in test **do not
exist** in live. Plan for recreating them — it's 10 minutes, but it surprises
everyone.

---

## A) Polar.sh — the recommended default

Why: it's the only one that **grants credits automatically each billing cycle**
without you writing recharge logic, and it's Merchant of Record (it handles
VAT). Fees: 5% + 50¢ on the free plan.

**Setup (their browser):**
1. `polar.sh` → **Create Organization** (the slug becomes their public URL).
2. **Finance → Payout Account → Connect Stripe** → identity (ID + selfie),
   business details, IBAN.
3. **Products → New Product** → name, price, **Recurring** (monthly/yearly).
   Optional **Enable trial period**. ⚠️ **The billing cycle and price type
   cannot be changed later** — get it right or create a new product.
4. **Meters → Create Meter**: name it `creditos`, aggregation `sum` over the
   event property you'll send.
5. **Benefits → + New Benefit → Credits**: units per cycle + the meter +
   optional **Rollover unused credits**. This is what recharges automatically.
6. **Checkout Links → New Link** → pick the product, set **Success URL** to
   `https://<dominio>/cuenta.html?ok=1&checkout_id={CHECKOUT_ID}`. The link is
   permanent — this is what goes in the pricing buttons.
7. **Settings → Webhooks → Add Endpoint**: URL `https://<dominio>/api/webhook`,
   format **Raw**, generate a **Secret**.
8. **Settings → Organization Access Tokens** → create a token (server-side
   only).

**Sandbox:** `sandbox.polar.sh` is a *completely separate account* — new user,
new organization, API base `sandbox-api.polar.sh`. Test cards are Stripe's
(`4242 4242 4242 4242`). Going live means recreating products, meters,
benefits and webhooks by hand.

**Server side (what you write):**
- Send the user to the checkout link with `?customer_email=<su email>` and
  `metadata` carrying your internal user id.
- On every AI use, after charging locally, report consumption:
  `POST /v1/events/ingest` with `{ name, external_customer_id, metadata }`.
- To read plan + balance in one call:
  `GET /v1/customers/external/{external_id}/state` → `activeSubscriptions[]`
  (`active`/`trialing`) and `activeMeters[].balance`.
- Webhook events to handle: **`subscription.active`** (grant access),
  **`subscription.revoked`** (remove access — NOT `canceled`, which only means
  "will end later"), **`order.paid`** (renewal), or simply
  **`customer.state_changed`** and rewrite your local state from it.
- Verify the signature (Standard Webhooks). Node: `validateEvent()` from
  `@polar-sh/sdk/webhooks`. PHP: HMAC over the raw body with the base64 secret.
  Reply **202** fast; 10 consecutive failures disable the endpoint.
- ⚠️ **Polar does not block usage at zero balance** — your server does
  (`15` §4).

**Customer portal:** `polar.sh/<slug>/portal`, email-code login, cancel and
invoices included. Point `cuenta.html` at it and delete your mock cancel code.

**Approval:** identity + business review before the first payout, **up to 14
days**. Sales work meanwhile; payouts are held. They may ask for a demo of the
purchase flow — a 100%-discount code or a video.

## B) Paddle — the alternative Merchant of Record

Choose when Polar isn't available or they want Paddle's invoicing. Note: **AI
products are a "restricted" category** → extra due diligence, and consulting/
coaching or physical goods are forbidden.

**Setup:** sandbox at `sandbox-vendors.paddle.com`. In live: **Checkout →
Request domain approval** (up to 5-7 working days — request it on day one),
**Business Verification** (2-4 days) and **Identity Verification** (1-3 days).
Then **Catalog → Products → New product** → inside it **New price** (billing
period + trial). Checkout via Paddle.js overlay or the default payment link.
Webhooks in **Developer tools → Notifications**; keys in **Developer tools →
Authentication**.

**Server side:** `@paddle/paddle-node-sdk`. Active =
`['active','trialing','past_due'].includes(sub.status)`. **Paddle has no credit
ledger** — their own AI-company guide says to sell prepaid credits and track
the balance in your app, so credits stay in your JSON/SQLite. Webhooks:
`subscription.created` + `subscription.updated` (covers renewals and changes),
`transaction.completed` to recharge (use `transaction.id` for idempotency).
Signature: `Paddle-Signature` header over the **raw** body.
Portal: exists, magic-link login, zero code. Minimum payout 100 €.

## C) Stripe — when they want the standard and don't mind VAT

Not Merchant of Record: **the owner handles VAT** (Stripe Tax is a separate
paid add-on). Available in Spain, Mexico and Brazil; **not** in Argentina,
Chile, Colombia or Peru.

**Setup:** register → activate the account (business, tax ID, ID document,
IBAN) → **More → Product catalog → Add product** → *Recurring* + billing period
→ **Payment links → New** (gives a `buy.stripe.com/...` URL) → **Workbench →
Webhooks → Create an event destination** → keys in `/apikeys` (use **restricted
keys `rk_`**). Test mode is now **Sandboxes**; products need **Copy to live
mode**.

**Server side:** `stripe` npm package. Active:
`subscriptions.list({customer, status:'active'})`. Credits: `billing.creditGrants`
+ `billing.creditBalanceSummary`, but ⚠️ **grants only apply to metered
subscription prices and do NOT auto-renew** — you must create a new grant on
every `invoice.paid`. Webhooks: `checkout.session.completed` (grant),
`customer.subscription.updated/deleted`, **`invoice.paid`** (recharge),
`invoice.payment_failed`. Signature: `stripe.webhooks.constructEvent` with the
**raw** body — a global `express.json()` breaks it (the classic bug).
Portal: **Settings → Billing → Customer portal**, activate and copy the
`billing.stripe.com/p/login/...` link.

## D) Mercado Pago — LatAm in local currency

The realistic option in Argentina, Chile, Colombia, Peru and Uruguay. Local
currency only (**no USD**), and the payer needs a Mercado Pago account in the
link flow.

**Setup:** Mercado Pago account → **Tus integraciones → Crear aplicación** →
product **Suscripciones**. **No-code path:** in the account, **Planes de
suscripción** → create plan (amount, frequency, free trial) → it gives a
payment link and an HTML button. By API: `POST /preapproval_plan` →
`POST /preapproval` → `init_point`. Credentials: **Credenciales de prueba** and
**de producción** (production requires the site URL). Webhooks: **Tus
integraciones → Webhooks → Configurar notificaciones** (separate test/prod
URLs; saving generates the secret).

**Server side:** `mercadopago` v2. `PreApproval.get({id})` → status
`authorized` = active. **No credit system** — credits stay in your database.
Webhook topics: `subscription_preapproval` (start/stop),
**`subscription_authorized_payment`** (recharge). Signature: `x-signature`
(`ts`, `v1`) + `x-request-id`, manifest
`id:<data.id lowercase>;request-id:<x-request-id>;ts:<ts>;` → HMAC-SHA256, or
the SDK's `WebhookSignatureValidator`. **Reply 200 within 22 s** or it retries.
Make recharges idempotent by `data.id` — duplicates are common.
Cancellation: the user cancels at `mercadopago.com.<país>/subscriptions`; the
seller uses `PUT /preapproval/{id}` with `status: cancelled`.

**Test:** test accounts (up to 15). The payment result is forced by the
**cardholder name**: `APRO` (approved), `OTHE` (rejected), `FUND`, `SECU`…
Cards: Visa `4509 9535 6623 3704`, CVV `123`, exp `11/30`.

---

## The migration checklist (what changes in the code)

Same for every platform — the mock was designed so this is small:

- [ ] Pricing buttons: `href="#"` → the real checkout link (+ `customer_email`
      and your user id in metadata).
- [ ] `POST /api/checkout`: instead of marking the plan paid, **redirect** to
      the checkout link.
- [ ] `POST /api/cancelar`: instead of downgrading, **open the customer portal**.
- [ ] `POST /api/webhook`: implement signature verification + the platform's
      events → activate/deactivate plan, recharge credits (idempotent by event
      id).
- [ ] Credits source of truth: Polar → their meter balance; everyone else →
      your own ledger, recharged on the renewal event.
- [ ] **Remove the `MODO DEMO` badge** everywhere (`16` §4).
- [ ] Legal pages filled with real data (name/company, tax ID, contact,
      refund and cancellation policy) — platforms check these.
- [ ] Gemini tier reviewed (`05` §3): image archetypes and anything handling
      personal data on the **paid** tier before real customers arrive; free
      tier is fine for the rest, with the rate limits in place.

## Verify before declaring it live

1. Sandbox purchase with a test card → webhook received → credits appear in
   the account → plan shows correctly.
2. Simulate a failed payment → access is not granted.
3. Cancel from the portal → the webhook removes access at the right moment.
4. Replay the same webhook twice → credits do **not** double (idempotency).
5. One real charge with a real card, then refund it from the dashboard.
6. Re-check that no AI key (Claude `sk-ant-…` / Gemini) is in any public file.

Only after all six: tell the user it's live, and remind them of what remains
theirs — invoicing obligations, taxes if the platform isn't Merchant of
Record, and responding to platform support within their SLA.
