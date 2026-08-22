# 💳 Which payment platform, by country (verified July 2026)

The owner's **country of residence (or where the company is registered)**
decides what's possible. Not the customer's country — customers can pay from
anywhere on any of these.

**Ask two things and nothing more:** where they live / where the company is
registered, and whether they're an individual (autónomo) or a registered
company. Then give **one recommendation and one alternative**, in two lines,
and move to the playbook (`18-go-live-playbooks.md`).

> ⚠️ **Re-verify before onboarding.** These lists change. Open the platform's
> own supported-countries page with the user as step zero of the playbook. If
> reality contradicts this file, reality wins — and note it back here.

---

## The two things that actually differ

**Merchant of Record (MoR) or not.** An MoR sells to the customer on the
owner's behalf: it charges VAT correctly in every country, files it, and
handles invoices and refunds. Not an MoR (Stripe, Mercado Pago) = the owner
handles VAT/IVA themselves. For a one-person SaaS selling worldwide, MoR is
worth its higher fee — say this plainly, and always add: «para tu caso concreto
confírmalo con tu gestor».

**Native credits or not.** Only **Polar** grants credits automatically each
billing cycle without custom logic. Everyone else: the credit ledger stays in
the app's own database and is topped up on the renewal webhook — which the mock
system already implements (`16`), so it's a small change either way.

## The table

| Country / region | 1st choice | 2nd choice | Why |
|---|---|---|---|
| **España / EU** | **Polar** | Paddle · Stripe | MoR handles EU VAT + OSS; native credits. Stripe only if they already use it and their gestor handles IVA |
| **Estados Unidos** | **Polar** | Stripe · Paddle | Same; Stripe is the local default if they don't need MoR |
| **México** | **Polar** | Stripe (available) · Mercado Pago | Stripe operates for MX sellers; MP if they need local currency/local methods |
| **Colombia** | **Polar** | Paddle · Mercado Pago | Stripe does **not** operate for CO sellers. MP for local currency |
| **Chile** | **Polar** | Paddle · Mercado Pago | Stripe does **not** operate for CL sellers |
| **Perú** | **Polar** | Paddle · Mercado Pago | Stripe does **not** operate for PE sellers |
| **Argentina** | **Polar** | Paddle · Mercado Pago | Stripe does **not** operate for AR sellers. Polar/Paddle pay out abroad (see note) |
| **Uruguay** | **Polar** | Paddle · Mercado Pago | — |
| **Ecuador** | **Polar** | Paddle | MP doesn't cover EC; Payhip would need PayPal |
| **Brasil** | **Polar** | Stripe (available) · Mercado Pago | — |
| **Resto del mundo** | **Paddle** | Polar · 2Checkout | Paddle pays out anywhere except sanctioned countries |
| **Venezuela, Nicaragua, Cuba, países sancionados** | — | — | No MoR accepts sellers there. Be honest: this route is closed; don't improvise workarounds |

**Fees, at a glance:** Polar 5% + $0.50 (free plan; $20/mo → 3.8% + $0.40).
Paddle 5% + $0.50. 2Checkout/Verifone 6% + €0.50 on the MoR tier. Stripe ~2.9%
+ $0.30 but **VAT is the owner's problem** (Stripe Tax costs extra). Mercado
Pago: local rates, local currency only.

## Notes that matter in practice

**Polar** — the default recommendation almost everywhere: MoR, native credits,
hosted customer portal, individuals accepted (payouts via Stripe Connect
Express, so identity verification with ID + selfie). Its supported-seller list
explicitly names the LatAm countries above. Review takes **up to 14 days**
before the first payout — sales work meanwhile. Payout costs: $2/month while
active + 0.25% + $0.25 per withdrawal, plus 0.25-1% FX.

**Paddle** — the fallback with the widest reach (sellers anywhere except
sanctioned countries; only Venezuela, Nicaragua and Cuba appear on its
unsupported list). Sole traders accepted. Two caveats: **AI products are a
"restricted" category** (extra due diligence) and the **domain must be approved
before selling** (up to 5-7 working days) — so request it on day one. Minimum
payout 100 €/$/£. No native credits.

**Stripe** — only where it actually operates for sellers: Spain, EU, US,
Mexico, Brazil. **Not** Argentina, Chile, Colombia or Peru. Cheapest fees,
biggest ecosystem, but not MoR and its credit grants don't auto-renew.

**Mercado Pago** — the realistic local option in LatAm (AR, BR, CL, CO, MX,
PE, UY). **Local currency only, no USD**, and the payer generally needs a
Mercado Pago account. Best when the customers are in the same country; poor
when selling worldwide. No native credits.

**Argentina specifically** — Stripe is out. The workable routes are an MoR
(Polar or Paddle) that pays out abroad, or Mercado Pago for local sales in
pesos. Currency controls affect how and when money actually lands in their
account: say clearly that this part is their bank's and gestor's territory,
not something to guess at.

**Not recommended** (checked and set aside): Fungies (LatAm coverage limited to
Peru and Uruguay), FastSpring (quote-only pricing, no public seller-country
list), PayPro Global and Gumroad (no verifiable seller-country documentation).
2Checkout/Verifone is a valid third option where Polar and Paddle both fail.

## How to present it (the whole script)

> «Como estás en <país>, te recomiendo **<plataforma>**: se encarga del IVA por
> ti y cobra un <fee> por venta. La alternativa sería <otra>, que <diferencia
> en una frase>. ¿Vamos con la primera?»

Then go to `18-go-live-playbooks.md` for that platform. Don't compare five
options, don't paste the table, and don't give tax advice beyond "esta se
encarga del IVA / esta no, consúltalo con tu gestor".
