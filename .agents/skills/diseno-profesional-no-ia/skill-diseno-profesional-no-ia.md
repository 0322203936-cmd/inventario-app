---
name: diseno-profesional-anti-ia
description: Úsalo siempre que generes o modifiques componentes de interfaz (botones, segmentadores, tarjetas, inputs, modales, navegación, etc.) para que el resultado se vea como diseño profesional hecho por un diseñador senior, no como el look genérico y plano típico de interfaces generadas por IA.
---

# Diseño de UI profesional (anti "look de IA")

## Por qué existe este skill
Los modelos de IA, por defecto, convergen en un mismo estilo: fondos planos, bordes redondeados uniformes (8px en todo), sombras inexistentes o una sola `box-shadow` genérica, degradados morado-azul, iconos de una sola librería sin variación de peso, y espaciados que no respetan ninguna jerarquía real. Este documento define reglas concretas para evitar eso en CADA componente que generes, no solo en la página como conjunto.

Antes de escribir código de cualquier componente, revisa esta lista. Si tu primer instinto coincide con algo de la sección "Señales de que se ve a IA", cámbialo.

## Señales de que se ve a IA (evítalas)
- Sombra única y plana tipo `box-shadow: 0 2px 4px rgba(0,0,0,0.1)` en todos los elementos sin variar según la elevación real del componente.
- `border-radius` idéntico (ej. 8px o 12px) en botones, tarjetas, inputs y modales sin razón de jerarquía.
- Degradados morado→azul o violeta→rosa como "toque de color" por defecto.
- Botones sin estados reales (hover, active, focus, disabled) o donde el único cambio es opacidad.
- Espaciado con múltiplos arbitrarios (ej. 13px, 17px) en vez de una escala consistente (4/8px).
- Iconos todos del mismo grosor y tamaño sin relación con el peso tipográfico del texto que acompañan.
- Contraste de color insuficiente compensado con "más padding" en vez de jerarquía visual real.
- Todo centrado y simétrico sin ninguna asimetría intencional.

## Sistema de elevación (sombras que sí se ven profesionales)
No uses una sola sombra genérica. Define una escala de elevación con AL MENOS 3-4 niveles, y compón cada sombra con dos o tres capas (una sombra ambiental difusa + una de contacto más definida):

```css
:root {
  --shadow-xs: 0 1px 2px rgba(15, 15, 15, 0.06);
  --shadow-sm: 0 1px 2px rgba(15,15,15,0.04), 0 2px 4px rgba(15,15,15,0.06);
  --shadow-md: 0 2px 4px rgba(15,15,15,0.04), 0 8px 16px rgba(15,15,15,0.08);
  --shadow-lg: 0 4px 8px rgba(15,15,15,0.05), 0 16px 32px rgba(15,15,15,0.12);
  --shadow-inset: inset 0 1px 2px rgba(15,15,15,0.08);
}
```

Reglas de uso:
- Un botón en reposo casi no necesita sombra (o solo `--shadow-xs`); la sombra crece al hacer hover y se aplana (o se vuelve `inset`) al hacer click, para simular presión física real.
- Un segmentador (segmented control) usa `--shadow-inset` en el track y una sombra pequeña (`--shadow-sm`) en el "thumb" o pastilla activa, para que se sienta como una pieza física deslizante, no un fondo de color plano.
- Tarjetas usan `--shadow-sm` en reposo y `--shadow-md` al hacer hover si son interactivas. Modales usan `--shadow-lg`.
- Ajusta el color de la sombra según el fondo: sobre fondos oscuros usa sombras con `rgba(0,0,0,0.4-0.6)` y más difusión; nunca uses negro puro sobre fondos claros (usa un gris muy oscuro con baja opacidad).

## Botones: anatomía completa, no solo color de fondo
Un botón profesional tiene TODOS estos estados definidos explícitamente, no inferidos:
1. **Reposo**: color base, borde sutil (1px, a menudo un tono más oscuro que el fondo, no negro puro), sombra xs/sm.
2. **Hover**: cambio de fondo (más oscuro/claro un 6-10%, no un color distinto), sombra que crece ligeramente, quizás un `translateY(-1px)`.
3. **Active/pressed**: `translateY(0)` o `1px`, sombra que se reduce o se vuelve inset, transición rápida (80-120ms).
4. **Focus-visible**: anillo de foco visible y con buen contraste (no solo el outline por defecto del navegador, pero tampoco lo elimines sin reemplazo).
5. **Disabled**: reducción real de contraste (no solo opacity: 0.5 sobre un color vibrante — eso se ve descuidado), cursor `not-allowed`.
6. **Loading** (si aplica): spinner o skeleton coherente con el tamaño del botón, texto que cambia de forma predecible.

Tipografía del botón: peso medium o semibold (500-600), nunca bold completo salvo CTAs muy grandes; letter-spacing ligeramente positivo (0.01-0.02em) en botones con texto en mayúsculas o muy cortos.

Jerarquía de botones: define al menos 3 niveles visuales (primario sólido, secundario con borde/outline, terciario tipo texto/ghost) y no uses el mismo radio de esquina que las tarjetas si quieres que se perciban como una familia distinta de componente.

## Segmentadores (segmented controls) — detalle específico
Esto suele ser lo que más delata a la IA porque se hace como "3 botones pegados". Un segmentador real:
- Tiene un **track** con fondo ligeramente hundido (`--shadow-inset` sutil o un tono de fondo un 4-6% más oscuro que el contenedor).
- Tiene un **thumb** (la pastilla que indica la opción activa) que se anima deslizándose (`transform: translateX()`, nunca recreando el elemento), con `transition: transform 200ms cubic-bezier(0.2, 0.8, 0.2, 1)`.
- El thumb tiene su propia sombra pequeña para "levantarse" sobre el track.
- El texto de la opción activa cambia de color/peso (no solo el fondo cambia).
- Padding interno del track de 2-4px alrededor de las opciones, nunca 0.
- Radio de esquina del thumb ligeramente menor que el del track (ej. track 10px, thumb 8px) para que encaje visualmente, no que se vea flotando.

## Color: evita el reflejo automático a morado/violeta
- Elige un acento derivado del dominio/marca del proyecto, no el default. Si no hay marca, prueba con acentos menos usados por IA: verde salvia, terracota apagado, azul petróleo, ámbar tostado — y solo si encajan con el contenido real.
- Nunca uses degradados como sustituto de jerarquía; un botón primario sólido con buen contraste es más profesional que un degradado sin motivo.
- Usa una escala de neutros con 8-10 pasos (no solo blanco/negro/un gris) para fondos, bordes y texto secundario. Los bordes casi nunca deberían ser negro puro ni gris medio genérico: deriva el borde del mismo hue que el fondo, un poco más oscuro/claro.

## Espaciado y radios: crea un sistema, no números sueltos
- Escala de espaciado en base 4: 4, 8, 12, 16, 24, 32, 48, 64.
- Escala de radios con jerarquía: ej. inputs/botones pequeños 6-8px, tarjetas 12-16px, modales 16-20px, elementos "pill" (badges, segmentadores) radio completo (9999px). No uses el mismo radio en todo.
- Los bordes de 1px deben usar `rgba` sobre el color de fondo, no un gris fijo, para que se integren en modo claro y oscuro.

## Micro-interacciones (con moderación)
- Transiciones de 100-200ms para hover/active, 200-300ms para apariciones/desapariciones de overlays.
- Usa curvas de easing con ligero rebote solo en elementos pequeños y lúdicos (toggles, thumbs); usa `ease-out` simple en la mayoría de transiciones de opacidad/posición para que se sienta pulido y no juguetón en exceso.
- No animes todo. Si cada elemento tiene una animación de entrada, se ve a plantilla de IA. Reserva el movimiento más notorio para 1-2 momentos clave (ej. el thumb del segmentador, la apertura de un modal).

## Checklist final antes de entregar el componente
- [ ] ¿Tiene al menos 2 niveles de sombra distintos en toda la interfaz (no la misma en todo)?
- [ ] ¿Los radios de esquina varían según el tipo de componente?
- [ ] ¿Cada botón/control interactivo tiene hover, active, focus-visible y disabled definidos explícitamente?
- [ ] ¿Evité degradado morado/azul por defecto?
- [ ] ¿Los bordes usan un tono derivado del fondo en vez de un gris fijo?
- [ ] ¿El segmentador tiene track hundido + thumb con sombra + animación de deslizamiento?
- [ ] ¿El espaciado sigue una escala consistente (base 4/8) en vez de números arbitrarios?
- [ ] ¿Hay al menos una decisión de diseño "de autor" (un detalle específico del producto) y no solo defaults?

Si al revisar el componente terminado se parece a los primeros wireframes que imaginarías para "botón genérico" o "toggle genérico", vuelve a pasarlo por esta lista antes de entregarlo.
