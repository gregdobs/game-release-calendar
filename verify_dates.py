"""Cross-check Game Informer release dates against Steam's own release_date
for the highest-profile titles. Writes verify_report.txt."""
import json, re, time, urllib.request
from datetime import datetime

games = json.load(open('gi_parsed.json', encoding='utf-8'))
steam = json.load(open('steam_cache.json', encoding='utf-8'))
import hype

dated = [g for g in games['dated'] if steam.get(g['name'])]
for g in dated:
    g['steam'] = steam[g['name']]
    g['score'] = hype.heuristic(g)
top = sorted(dated, key=lambda g: -g['score'])[:45]
print(f"verifying {len(top)} highest-profile dated titles against Steam\n")

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) GameCal/1.0"}
rows = []
for g in top:
    appid = g['steam']['appid']
    url = (f"https://store.steampowered.com/api/appdetails?appids={appid}"
           "&cc=US&l=en&filters=release_date")
    sd, note = None, ""
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            node = json.loads(r.read().decode("utf-8", "replace")).get(str(appid)) or {}
        if node.get("success"):
            rd = node["data"].get("release_date") or {}
            sd = (rd.get("date") or "").strip()
    except Exception as e:
        note = f"lookup failed ({getattr(e,'code',e)})"

    gi = g['date']
    status = "?"
    if sd:
        try:
            p = datetime.strptime(sd, "%b %d, %Y").strftime("%Y-%m-%d")
            delta = abs((datetime.strptime(p, "%Y-%m-%d")
                         - datetime.strptime(gi, "%Y-%m-%d")).days)
            status = "MATCH" if delta == 0 else (f"±{delta}d" if delta <= 2 else "DIFFER")
        except ValueError:
            status = "vague"          # e.g. "Q1 2026" / "Coming soon"
    elif not note:
        status = "no date"
    rows.append((status, g['name'], gi, sd or note or "-"))
    time.sleep(0.4)

order = {"DIFFER":0, "±1d":1, "±2d":1, "vague":2, "no date":3, "MATCH":4, "?":5}
rows.sort(key=lambda r: (order.get(r[0], 5), r[1]))

out = ["Game Informer vs Steam release dates (top 45 by hype score)", "="*70]
for s, n, gi, sd in rows:
    out.append(f"{s:7} {n[:38]:40} GI:{gi}  Steam:{sd}")
from collections import Counter
c = Counter(r[0] for r in rows)
out += ["", "summary: " + ", ".join(f"{k}={v}" for k, v in c.most_common())]
txt = "\n".join(out)
open('verify_report.txt', 'w', encoding='utf-8').write(txt)
print(txt.encode("ascii","replace").decode())
