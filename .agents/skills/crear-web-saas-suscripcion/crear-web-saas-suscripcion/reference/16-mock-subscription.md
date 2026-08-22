# The Mockup Subscription System — real product, simulated money

The goal: the owner can test the ENTIRE funnel end to end (signup → free
credits → run out → upgrade → recharge → cancel) without having a payment
account yet, and later swap in the real gateway by changing a handful of lines
(`18-go-live-playbooks.md`).

**What is real:** accounts, sessions, credits, the AI work, the limits.
**What is simulated:** only the money. And it must SAY so on screen.

---

## 1. Data model (keep it this simple)

One JSON file, **one level above `public_html`** so a redeploy never erases your
customers — resolve its path with `ruta_db()` (`15-backend-proxy.md` §2). This is
not optional: a DB inside the served folder is wiped on every publish.

```json
{
  "usuarios": {
    "ana@ejemplo.com": {
      "hash": "<password_hash bcrypt>",
      "plan": "gratis",
      "creditos": 5,
      "renovacion": "2026-08-01",
      "creado": "2026-07-22",
      "historial": [
        { "fecha": "2026-07-22T10:31:00Z", "accion": "censurar-pdf", "coste": 8 }
      ]
    }
  },
  "sesiones": { "<token>": { "email": "ana@ejemplo.com", "expira": "…" } }
}
```

Write with an exclusive lock (`flock` in PHP / a queue in Node) — two
simultaneous requests must never both read-modify-write. If the archetype
expects real volume, use SQLite instead: same shape, one table per key.
**Migration note:** when the real gateway arrives, this file gains a
`customer_id` field per user and nothing else changes.

## 2. Endpoints (identical names in mockup and production)

| Endpoint | Does |
|---|---|
| `POST /api/registro` | email + password → creates account with the free plan's credits |
| `POST /api/login` | → session cookie (HttpOnly, SameSite=Lax, Secure) |
| `POST /api/logout` | kills the session |
| `GET  /api/yo` | plan, credits, renewal date, history |
| `POST /api/usar` | **the important one**: checks credits → calls Gemini → decrements → returns result |
| `POST /api/checkout` | **mockup**: marks the plan as paid and recharges credits. **Production**: redirects to the real checkout |
| `POST /api/cancelar` | **mockup**: back to free. **Production**: opens the customer portal |
| `POST /api/webhook` | **mockup**: does nothing. **Production**: receives payment events |

Keeping the names identical is the whole trick: going live rewrites the
INSIDE of `checkout`, `cancelar` and `webhook`, and the frontend never changes.

## 3. Password and session rules (not optional, even in mockup)

- Hash with bcrypt/argon (`password_hash()` in PHP, `bcrypt` in Node). **Never**
  store a plain password — the owner will reuse this code in production.
- Session token: 32 random bytes, hex. Cookie `HttpOnly; SameSite=Lax; Secure`.
  Expiry 30 days, refreshed on use.
- Rate-limit login (5 attempts / 15 min per IP) — three lines, prevents the
  most obvious abuse.
- No email verification in mockup mode (it needs a mail service); leave the
  hook and a TODO comment for it.

## 4. The `MODO DEMO` badge

While the mockup is active, the app shows a fixed, unmissable badge:

> ⚠️ MODO DEMO — los pagos son simulados, no se cobra nada

Put it in the pricing table, in the checkout modal and in the account page.
`18-go-live-playbooks.md` removes it as the last step of going live. A demo
that looks like a real charge is how people get scammed by accident.

## 5. The simulated checkout

Clicking a plan opens a modal that: names the plan and price, shows the demo
warning, has a fake card form (pre-filled `4242 4242 4242 4242`, non-editable
or ignored), and a «Simular pago» button. On confirm: `POST /api/checkout` →
plan updated, credits set to the plan's monthly amount, renewal date = today +
30 days, a line added to history. Then a success screen showing the new credit
balance.

Monthly renewal in mockup mode: on any `/api/yo` call, if `renovacion` is in
the past and the plan is paid, top the credits back up and move the date
forward. That's the same behavior the real webhook will produce.

## 6. The test account (deliverable, not optional)

At the end of the build, create ONE test account and hand it to the user with
its credentials, plus the exact click-path to verify everything:

```
Cuenta de prueba: prueba@<dominio>  ·  contraseña: <generada>
1. Entra en /app.html y usa la herramienta una vez → verás bajar los créditos
2. Gástalos todos → aparecerá la ventana de mejorar plan
3. Simula el pago del plan Pro → los créditos se recargan
4. Ve a /cuenta.html → verás el plan, el historial y el botón de cancelar
5. Cancela → vuelves al plan gratis
```

Run this path yourself before handing it over. If any step breaks, the SaaS
isn't done — regardless of how good the AI part is.

## 7. What NOT to build in mockup mode

Password recovery by email, invoices, VAT numbers, coupons, teams, referrals.
All of that either comes free with the real gateway (invoices, taxes, portal)
or is premature. Leave TODO comments where they'll plug in and move on.
