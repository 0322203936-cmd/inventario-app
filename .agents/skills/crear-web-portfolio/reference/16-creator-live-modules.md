# Creator / live-proof modules — optional showpieces

Optional, high-impact modules for a portfolio whose owner has a **real public
audience or body of published work** — a YouTuber, streamer, podcaster, TikToker,
newsletter author, open-source dev. They turn "trust me, I'm big" into **live,
verifiable proof** right on the page. Most relevant for the `trayectoria`
(personal-brand/creator) niche, but the odometer and the "latest content"
carousel also fit `dev` (GitHub releases), `musica` (latest tracks) and `foto`
(latest series).

## When to use — and the honesty rule

- Use a module **only if the fact is real and public.** A live subscriber count
  is credibility; a fabricated one is a lie the visitor can check in one click.
- **Never invent counts, channels or feeds** (portfolio invariant 1). No channel
  → no live counter. No public feed → ship the static fallback, clearly the
  person's real items, or drop the carousel. A placeholder number is only ever a
  clearly-marked placeholder to swap, never a claim.
- These are **garnish, not the meal.** The work is still the hero. One live
  counter band + one "latest" carousel is plenty; don't stack five widgets.
- All code below is classic `<script defer>` + IIFE friendly, no build, no keys,
  and degrades gracefully (see `04-critical-gotchas.md`). Wrap each init in
  `safe()` (gotcha D.1).

---

## Module 1 — Rolling "odometer" counter (scoreboard digits)

A number whose digits roll like a sports scoreboard instead of snapping. Pure
CSS + vanilla JS. Each digit is a column clipped to `1em` that holds `0-9`
stacked; you slide the strip `translateY(-Ne m)` to show digit N.

**HTML** — just the number, the JS builds the columns:

```html
<b class="bignum od" data-live="subs" data-channel="UCxxxxxxxxxxxxxxxxxxxxxx">3.995.000</b>
<span class="bignum-label"><i class="dot"></i>Suscriptores en directo</span>
```

**CSS** — the digit-clip mechanism:

```css
.od{display:inline-flex;align-items:flex-start;font-variant-numeric:tabular-nums;line-height:1;white-space:nowrap}
.od-col{display:inline-block;height:1em;line-height:1em;overflow:hidden;vertical-align:top}
.od-strip{display:block;transform:translateY(0);transition:transform .6s cubic-bezier(.16,1,.3,1);will-change:transform}
.od-instant .od-strip{transition:none}          /* set a start value with no animation */
.od-strip>span{display:block;height:1em;line-height:1em;text-align:center}
.od-sep{display:inline-block;height:1em;line-height:1em;vertical-align:top}  /* the . or , thousands sep */
```

> ⚠️ **The #1 way this breaks (specificity trap — gotcha B.13).** The odometer is
> made of many nested `<span>`s. A broad rule that styles a *sibling label*, like
> `.counter span{display:flex;font-size:.7rem}`, has specificity (0,1,1) and will
> silently override the digit `<span>`s, scattering them horizontally and
> shrinking them. **Always scope label/inner rules to a direct child or a class**
> — `.counter>span` or `.counter .label` — never a bare descendant `span`. This
> exact bug cost real debugging time; measure with `getComputedStyle` (zoom-
> independent) if digits ever look wrong, not screenshots.

**JS** — build + set, plus a scoreboard "spin-up" on first view:

```js
function makeOdometer(el, value){
  el.classList.add("od"); el.innerHTML=""; var strips=[], curLen=-1;
  function fmt(n){ return Math.round(n).toLocaleString("es-ES"); }   // 3.995.000
  function render(n){
    var str=fmt(n), i, ch;
    if(str.length!==curLen){
      el.innerHTML=""; strips=[];
      for(i=0;i<str.length;i++){ ch=str.charAt(i);
        if(ch>="0"&&ch<="9"){
          var col=document.createElement("span"); col.className="od-col";
          var strip=document.createElement("span"); strip.className="od-strip";
          for(var d=0;d<10;d++){ var sp=document.createElement("span"); sp.textContent=d; strip.appendChild(sp); }
          col.appendChild(strip); el.appendChild(col); strips.push(strip);
        } else { var sep=document.createElement("span"); sep.className="od-sep"; sep.textContent=ch; el.appendChild(sep); }
      }
      curLen=str.length;
    }
    var si=0;
    for(i=0;i<str.length;i++){ ch=str.charAt(i);
      if(ch>="0"&&ch<="9"){ strips[si].style.transform="translateY(-"+parseInt(ch,10)+"em)"; si++; } }
  }
  render(value); return { set: render };
}
// scoreboard start: jump ~2% below (no transition), then ease up to the real value
function spin(od, target){
  var el=od._el, start=Math.max(0, target-Math.floor(target*0.02)-40);
  el.classList.add("od-instant"); od.set(start);
  void el.offsetWidth;                       // force reflow so the transition re-arms
  el.classList.remove("od-instant");
  var t0=performance.now(), dur=1500;
  (function up(t){ var p=Math.min((t-t0)/dur,1), e=1-Math.pow(1-p,3);
    od.set(Math.round(start+(target-start)*e)); if(p<1) requestAnimationFrame(up); else od.set(target); })(t0);
}
```

Trigger `spin()` from an `IntersectionObserver` (threshold ~0.3) so it animates
when it scrolls into view, and only once.

---

## Module 2 — Real live subscriber / follower count

A counter that shows the **actual current** number, refreshed live. For YouTube
there is a keyless, CORS-open endpoint (`socialcounts.org`) — no API key, no
backend. Seed the HTML with the last-known number (so it's correct before JS),
then let the fetch correct it and a gentle timer nudge it.

```js
function fetchSubs(channelId, od){
  if(!channelId) return;
  fetch("https://api.socialcounts.org/youtube-live-subscriber-count/"+channelId, { cache:"no-store" })
    .then(function(r){ return r.json(); })
    .then(function(d){
      var c=d&&d.counters, n=c&&((c.estimation&&c.estimation.subscriberCount)||(c.api&&c.api.subscriberCount));
      if(n&&n>0) od.set(n);                        // real number wins
    })["catch"](function(){});                     // offline → keep the seeded value
}
// call once on load, then setInterval(..., 45000) while the band is visible
```

- **Views / other metrics** have no free live source — animate them upward from a
  **real seed** the owner gives you (e.g. `+8..+34` every ~420 ms) and label them
  honestly ("visualizaciones acumuladas"). Never seed a fake starting point.
- **Other platforms** (Twitch, TikTok, Instagram, GitHub stars) each need their
  own source; if there's no keyless one, use a real seed + the static approach,
  or a same-origin PHP proxy like Module 4. Don't hardcode a stale big number and
  pretend it's live.
- Channel id / handle is intake, not invention — ask for it, or read it off the
  URL they give you.

---

## Module 3 — "Platform search" reveal (signature animation)

A mock search bar (YouTube/Spotify/Google style) that **types the person's name
and reveals their result card** — a memorable, on-brand showpiece. It's a
*recreation* of the platform UI, not an embed, so you control the composition and
it never fails to load. Fire it from an `IntersectionObserver` (once), with a
timeout fallback so it always plays.

Composition rules learned building it (match the real platform):

- **The channel/result header is ONE line:** `[avatar] Name [verified] ····
  [Subscribe]`. Lay it out with `display:flex; align-items:center; gap:10px` and
  push the button with `margin-left:auto`. Put the meta line (`@handle · N
  subscribers`) and the description **below**, full width.
  > ⚠️ Because of the global reset `img,svg,canvas{display:block}`, the verified
  > `<svg>` will drop to its own line the instant its flex parent loses `flex`
  > (e.g. a stray `.meta span{display:block}` rule overriding it — gotcha
  > B.13/B.14). Keep the row `display:flex` and scope sibling rules to a class.
- **A video result is horizontal**, YouTube-style: `grid-template-columns:
  minmax(170px,40%) 1fr`, thumbnail left, title/stats/channel right.
- **Duration badge** sits inside the thumbnail, real YouTube style:
  `position:absolute; right:8px; bottom:8px; padding:1px 4px;
  background:rgba(0,0,0,.8); border-radius:4px; font-size:.72rem; color:#fff`.
- Sequence: type query → reveal channel card → reveal "latest" label → reveal
  video (staggered `.show` classes) → move a fake cursor to Subscribe → flip to
  "Subscribed" → fill the video progress bar. See the full `seq()` in the
  reference build; each step is a `setTimeout` adding a class.

Reveal transition per card: `opacity:0; transform:translateY(10px)` →
`.show{opacity:1;transform:none}` with a `.55s var(--exp)` transition.

---

## Module 4 — "Latest content" carousel (auto-updating)

A horizontal, scroll-snap carousel of the person's **latest videos/posts/tracks**
that refreshes itself. Three-layer strategy so it's always populated and never
hangs on a flaky proxy:

1. **Static fallback first** — a bundled `lib/latest-fallback.js` sets
   `window.__LATEST__ = [{id,t},…]` (last ~12 items). Renders instantly, works
   with zero network.
2. **Same-origin PHP proxy** (reliable on Hostinger) — `api/yt-latest.php` fetches
   the channel RSS server-side (no CORS problem) and returns JSON. Primary refresh.
3. **External CORS proxy** (`allorigins.win/raw`) as a last resort if PHP is
   absent or fails, with an `AbortController` timeout.

**`api/yt-latest.php`** (drop in `api/`, needs PHP — Hostinger has it):

```php
<?php
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Cache-Control: public, max-age=1800');
$cid = 'UCxxxxxxxxxxxxxxxxxxxxxx';            // the channel id (intake)
$url = 'https://www.youtube.com/feeds/videos.xml?channel_id=' . $cid;
$xml = false;
if (function_exists('curl_init')) {
  $ch = curl_init($url);
  curl_setopt_array($ch, [CURLOPT_RETURNTRANSFER=>true, CURLOPT_TIMEOUT=>8,
    CURLOPT_FOLLOWLOCATION=>true, CURLOPT_USERAGENT=>'Mozilla/5.0 (compatible; portfolio/1.0)']);
  $xml = curl_exec($ch); curl_close($ch);
}
if ($xml === false || $xml === '') { $xml = @file_get_contents($url); }
$out = [];
if ($xml && preg_match_all('/<entry>(.*?)<\/entry>/s', $xml, $m)) {
  foreach ($m[1] as $e) {
    if (preg_match('/<yt:videoId>([^<]+)/', $e, $a) && preg_match('/<title>([^<]*)<\/title>/', $e, $b)) {
      $out[] = ['id'=>$a[1], 't'=>html_entity_decode($b[1], ENT_QUOTES, 'UTF-8')];
      if (count($out) >= 10) break;
    }
  }
}
echo json_encode($out, JSON_UNESCAPED_UNICODE);
```

**JS** — render fallback, then refresh (PHP → external proxy):

```js
function initReel(){
  var track=document.getElementById("reel-track"); if(!track) return;
  var CID="UCxxxxxxxxxxxxxxxxxxxxxx";
  function esc(s){ return String(s==null?"":s).replace(/[&<>"]/g,function(c){return({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"})[c];}); }
  function render(list){
    if(!list||!list.length) return;
    track.innerHTML=list.slice(0,10).map(function(v){ var id=encodeURIComponent(v.id);
      return '<a class="reel-card" href="https://www.youtube.com/watch?v='+id+'" target="_blank" rel="noopener">'
        +'<div class="reel-thumb"><img src="https://i.ytimg.com/vi/'+id+'/hqdefault.jpg" alt="" loading="lazy"></div>'
        +'<div class="reel-info"><div class="reel-title">'+esc(v.t)+'</div></div></a>'; }).join("");
  }
  render(window.__LATEST__||[]);                                   // 1) instant
  function fromRSS(){                                              // 3) external proxy
    var rss="https://www.youtube.com/feeds/videos.xml?channel_id="+CID;
    var url="https://api.allorigins.win/raw?url="+encodeURIComponent(rss);
    var ctrl=("AbortController" in window)?new AbortController():null;
    if(ctrl) setTimeout(function(){ try{ctrl.abort();}catch(e){} },6000);
    fetch(url, ctrl?{signal:ctrl.signal}:{}).then(function(r){return r.text();}).then(function(xml){
      var doc=new DOMParser().parseFromString(xml,"text/xml"), en=doc.getElementsByTagName("entry"), out=[], j;
      for(j=0;j<en.length&&out.length<10;j++){
        var idEl=en[j].getElementsByTagName("yt:videoId")[0]||en[j].getElementsByTagNameNS("*","videoId")[0];
        var tEl=en[j].getElementsByTagName("title")[0];
        if(idEl&&tEl&&idEl.textContent) out.push({id:idEl.textContent,t:tEl.textContent}); }
      if(out.length) render(out);
    })["catch"](function(){});
  }
  fetch("api/yt-latest.php",{cache:"no-store"})                    // 2) same-origin PHP
    .then(function(r){ if(!r.ok) throw 0; return r.json(); })
    .then(function(list){ if(list&&list.length) render(list); else fromRSS(); })
    ["catch"](function(){ fromRSS(); });
}
```

**Carousel CSS essentials** (and heed gotcha B.1 — horizontal scroll needs
`overflow-y` room for shadows/badges):

```css
.reel{overflow-x:auto;overflow-y:hidden;scroll-snap-type:x mandatory;scrollbar-width:none;
  -webkit-mask-image:linear-gradient(90deg,transparent,#000 2%,#000 98%,transparent);
          mask-image:linear-gradient(90deg,transparent,#000 2%,#000 98%,transparent)}
.reel::-webkit-scrollbar{display:none}
.reel-track{display:flex;gap:1.2rem;padding:.5rem .2rem 1rem}
.reel-card{flex:0 0 clamp(240px,26vw,320px);scroll-snap-align:start;opacity:0;transform:translateY(14px)}
.reel-card.in{opacity:1;transform:none;transition:opacity .6s var(--exp),transform .6s var(--exp)}
.reel-thumb{position:relative;aspect-ratio:16/9;border-radius:12px;overflow:hidden;border:1px solid var(--line)}
.reel-thumb img{width:100%;height:100%;object-fit:cover;transition:transform .6s var(--exp)}
.reel-card:hover .reel-thumb img{transform:scale(1.05)}
```

Prev/next buttons just `scrollBy({left: ±cardWidth*2, behavior:"smooth"})` on the
`.reel` element.

---

## Wiring checklist

- [ ] The fact is **real and public** — else drop the module (invariant 1).
- [ ] Channel id / handle / feed URL came from **intake**, not invention.
- [ ] Counter seeded with a real last-known value in the HTML (correct pre-JS).
- [ ] Label/inner rules scoped to a **class or `>` child**, never bare `span` (B.13).
- [ ] Search-result rows stay `display:flex` so the verified `<svg>` doesn't wrap (B.14).
- [ ] Carousel has `overflow-y` room (B.1) and a static `window.__LATEST__` fallback.
- [ ] PHP proxy only where PHP exists (Hostinger ✓); otherwise fallback + external proxy.
- [ ] Each `init*` wrapped in `safe()`; observers use threshold ≤ 0.3 + a timeout.
