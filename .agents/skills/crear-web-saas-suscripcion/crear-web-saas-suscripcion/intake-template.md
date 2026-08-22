# Intake — two questions, once

A SaaS build needs exactly two answers: **what it does** and **how it charges**.
Everything else you decide. Ask both in ONE message, with defaults they can
accept by saying "vale".

## First, route (don't ask yet)

Connect, publish, edit, go-live and verify asks need **no** intake. Reserve the
questions for a build.

## The two questions

**1. What service does it offer?**
If they named it, skip this. If not, offer 2-3 archetypes matched to their
situation (`02-saas-catalog.md` §Choosing) — never the whole list. Settle the
niche and language here too if they aren't obvious.

**2. What subscription model?**
Propose a default and let them edit it. The default that works for most
document archetypes:

> - **Gratis**: 5 créditos (para probarlo una vez)
> - **Pro**: 19 €/mes con 200 créditos
> - **Empresa**: 59 €/mes con 1.000 créditos
> - 1 crédito = 1 página / 1 documento / 1 imagen

For image archetypes, run the arithmetic first (`05-gemini-api.md` §7) and
propose numbers that don't lose money — then show the maths in one line so they
understand the constraint:

> «Cada imagen te cuesta ~0,06 €, así que 200 imágenes al mes son 12 € de coste:
> por eso el plan Pro va a 29 € y no a 19 €.»

Template (Spanish — translate to the user's language):

> Para montarlo necesito dos cosas:
> 1. **Qué hace exactamente** tu SaaS (y para quién, si tienes un público
>    concreto en mente).
> 2. **Los planes**: te propongo gratis con 5 créditos, Pro 19 €/mes con 200
>    créditos y Empresa 59 €/mes con 1.000. ¿Lo dejamos así o lo cambiamos?
>
> El diseño, la parte técnica y el sistema de cuentas los decido yo. Los pagos
> irán de maqueta hasta que lo tengas probado — al final te guío para
> conectarlos de verdad.

## Never ask

Palette, fonts, layout, which model, PHP vs Node, how sessions work, what
library, where the key goes, payment platform (that comes at go-live, and the
country decides it). If they volunteer a preference, honor it; don't solicit
one.

## The two things to SAY (not ask) during the build

1. **Billing on Google:** the AI needs a paid Gemini key before real users
   touch it, because the free tier trains on submitted content (`05` §3).
   Mention it once, plainly, when the AI part starts.
2. **Payments are a labelled mockup** until they say otherwise, and there'll be
   a test account at the end.

## After they reply

Acknowledge in one line, then build. Gaps → defaults: Spanish, one archetype,
the proposed plans, mock payments, PHP server. Announce milestones (✅), and
hand over the test account when done.
