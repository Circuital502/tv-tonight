#!/usr/bin/env python3
"""Builds index.html: tonight's primetime (8-11 PM ET) on ABC, NBC, CBS, FOX and The CW.
Data: TVmaze public API (https://www.tvmaze.com), licensed CC BY-SA. No API key needed."""
import html, json, re, sys, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
NETWORKS = {"abc": "ABC", "nbc": "NBC", "cbs": "CBS", "fox": "FOX", "the cw": "CW", "cw": "CW"}
ORDER = ["ABC", "CBS", "CW", "FOX", "NBC"]
START_HOUR, END_HOUR = 20, 23  # shows starting from 8:00 PM up to (not including) 11:00 PM ET

today = datetime.now(ET).date()
url = f"https://api.tvmaze.com/schedule?country=US&date={today.isoformat()}"
req = urllib.request.Request(url, headers={"User-Agent": "tv-tonight-page/1.0"})
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        episodes = json.load(r)
except Exception as e:
    print("Could not fetch schedule:", e, file=sys.stderr)
    sys.exit(1)

def clean(text, limit=200):
    text = html.unescape(re.sub(r"<[^>]+>", "", text or "")).strip()
    if len(text) <= limit:
        return text
    out = ""
    for sent in re.split(r"(?<=[.!?])\s+", text):
        if len(out) + len(sent) + 1 > limit:
            break
        out = (out + " " + sent).strip()
    if out:
        return out
    return text[:limit].rsplit(" ", 1)[0].rstrip(",;:") + "…"

slots, seen = {}, set()
for ep in episodes:
    show = ep.get("show") or {}
    net = (show.get("network") or {}).get("name", "")
    key = NETWORKS.get(net.strip().lower())
    if not key or not ep.get("airstamp"):
        continue
    start = datetime.fromisoformat(ep["airstamp"]).astimezone(ET)
    mins = int(round((start.hour * 60 + start.minute) / 30.0)) * 30  # 8:31 -> 8:30, 9:02 -> 9:00
    hour, minute = divmod(mins, 60)
    if start.date() != today or not (START_HOUR <= hour < END_HOUR):
        continue
    ident = (key, show.get("name"), mins)
    if ident in seen:
        continue
    seen.add(ident)
    label = datetime(2000, 1, 1, hour, minute).strftime("%I:%M %p").lstrip("0")
    slots.setdefault((hour, minute), (label, []))[1].append((key, show.get("name", "?"), ep))

def esc(s):
    return html.escape(s or "", quote=False)

blocks = []
for hm in sorted(slots):
    label, items = slots[hm]
    items.sort(key=lambda i: (ORDER.index(i[0]), i[1]))
    rows = []
    for key, name, ep in items:
        epname = ep.get("name") or ""
        se = f"S{ep['season']} E{ep['number']}" if ep.get("season") and ep.get("number") else ""
        sub = " · ".join(x for x in (epname, se) if x)
        sub_html = f' – <span class="ep">{esc(sub)}</span>' if sub else ""
        new_html = '<span class="new">New</span>' if ep.get("airdate") == today.isoformat() else ""
        desc = clean(ep.get("summary"))
        d_html = f'<p class="d">{esc(desc)}</p>' if desc else ""
        rows.append(f'<div class="show"><span class="net {key.lower()}">{key}</span>'
                    f'<span class="t">{esc(name)}</span>{sub_html}{new_html}{d_html}</div>')
    blocks.append(f'<section class="slot"><h2>{label}</h2>\n' + "\n".join(rows) + "\n</section>")

body = "\n\n".join(blocks) or ('<section class="slot"><div class="show"><p class="d">No listings found for tonight. '
                              'TVmaze may not have today’s schedule yet.</p></div></section>')
pretty = f"{today.strftime('%A, %B')} {today.day}, {today.year}"
generated = datetime.now(ET).strftime("%I:%M %p ET").lstrip("0")

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>On TV Tonight – Primetime</title>
<style>
:root{--bg:#fffdf6;--card:#fff;--ink:#1b1b1b;--muted:#555;--line:#ddd6c3;--hl:#fff3a8;--accent:#c8102e}
@media (prefers-color-scheme:dark){:root{--bg:#17160f;--card:#201f17;--ink:#f1eedf;--muted:#b5b09b;--line:#3a3827;--hl:#5a4f00;--accent:#ff6b81}}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.45 Arial,Helvetica,sans-serif}
main{max-width:680px;margin:0 auto;padding:16px}
h1{font:700 30px/1.1 Georgia,"Times New Roman",serif;margin:8px 0 2px}
h1 span{background:linear-gradient(transparent 60%,var(--hl) 60%)}
.date{color:var(--muted);margin:0 0 14px}
.note{border-left:4px solid var(--accent);padding:6px 12px;margin:12px 0;color:var(--muted);font-size:14px}
#stale{display:none;background:var(--hl);padding:8px 12px;border-radius:6px;margin:12px 0;font-size:14px}
.slot{background:var(--card);border:1px solid var(--line);border-radius:6px;margin:14px 0;padding:4px 16px 8px}
.slot h2{font-size:17px;margin:12px 0 4px}
.show{padding:10px 0;border-top:1px solid var(--line)}
.show:first-of-type{border-top:0}
.net{display:inline-block;min-width:44px;text-align:center;font-weight:700;font-size:12px;letter-spacing:.5px;color:#fff;border-radius:4px;padding:2px 6px;margin-right:8px;vertical-align:2px}
.abc{background:#111}.nbc{background:#7a3fb5}.cbs{background:#0a3d91}.fox{background:#c0392b}.cw{background:#1e8c4a}
.t{font-weight:700;font-size:17px}.ep{font-style:italic}
.new{background:var(--hl);font-size:12px;padding:0 5px;border-radius:3px;margin-left:4px}
.d{color:var(--muted);font-size:14px;margin:3px 0 0}
footer{color:var(--muted);font-size:13px;margin:20px 0}
a{color:inherit}
</style>
</head>
<body>
<main>
<h1><span>On TV Tonight</span></h1>
<p class="date">Primetime on ABC · CBS · The CW · FOX · NBC<br>@@PRETTY@@ — all times Eastern (Central: one hour earlier)</p>
<div id="stale">This listing is for @@PRETTY@@ and may be out of date.</div>

@@BODY@@

<p class="note">Listings come from a community database and mainly cover scheduled episodes. Live sports, specials and repeats may be missing, and times can change.</p>
<footer>Updated @@GENERATED@@. Listings data from <a href="https://www.tvmaze.com">TVmaze.com</a> (CC BY-SA).</footer>
</main>
<script>
try{var n=new Date(),k=n.getFullYear()+"-"+(n.getMonth()+1)+"-"+n.getDate();if(k!=="@@JS@@")document.getElementById("stale").style.display="block";}catch(e){}
</script>
</body>
</html>
"""

out = PAGE
for token, value in {"PRETTY": pretty, "BODY": body, "GENERATED": generated,
                     "JS": f"{today.year}-{today.month}-{today.day}"}.items():
    out = out.replace(f"@@{token}@@", value)
with open("index.html", "w", encoding="utf-8") as f:
    f.write(out)
print(f"Wrote index.html with {sum(len(v[1]) for v in slots.values())} listings for {today}")
