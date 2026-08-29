"""Fetch Steam appdetails for every matched app: real header art, developer,
publisher, genres, short description, and Steam's own release date (used as an
independent cross-check against the Game Informer schedule).

Resumable - progress is written to steam_details.json as it goes.
"""
import json, os, sys, time, urllib.request, threading

HERE = os.path.dirname(os.path.abspath(__file__))
P = lambda *a: os.path.join(HERE, *a)
OUT = P("steam_details.json")

steam = json.load(open(P("steam_cache.json"), encoding="utf-8"))
ids = sorted({v["appid"] for v in steam.values() if v})
done = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
todo = [i for i in ids if str(i) not in done]
print(f"{len(ids)} apps total, {len(done)} cached, {len(todo)} to fetch", flush=True)

lock = threading.Lock()
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) GameCal/1.0"}

def fetch(appid):
    url = (f"https://store.steampowered.com/api/appdetails?appids={appid}"
           "&cc=US&l=en&filters=basic,genres,release_date")
    delay = 2.0
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                body = json.loads(r.read().decode("utf-8", "replace"))
            node = body.get(str(appid)) or {}
            if not node.get("success"):
                return {}
            x = node.get("data") or {}
            rd = x.get("release_date") or {}
            return {
                "img": x.get("header_image"),
                "dev": (x.get("developers") or [None])[0],
                "pub": (x.get("publishers") or [None])[0],
                "gen": [g["description"] for g in (x.get("genres") or [])][:3],
                "desc": (x.get("short_description") or "")[:220],
                "srd": rd.get("date"),
                "soon": bool(rd.get("coming_soon")),
                "free": bool(x.get("is_free")),
            }
        except Exception as e:
            code = getattr(e, "code", None)
            if code in (429, 403):          # rate limited - back off hard
                time.sleep(delay); delay *= 2
            elif attempt == 4:
                return None
            else:
                time.sleep(1.5)
    return None

t0 = time.time()
for n, appid in enumerate(todo, 1):
    res = fetch(appid)
    with lock:
        done[str(appid)] = res if res is not None else {}
    if n % 40 == 0:
        json.dump(done, open(OUT, "w", encoding="utf-8"))
        el = time.time() - t0
        print(f"  {n}/{len(todo)}  ({el:.0f}s, {el/n:.2f}s/req)", flush=True)
    time.sleep(0.7)

json.dump(done, open(OUT, "w", encoding="utf-8"))
ok = sum(1 for v in done.values() if v.get("img"))
print(f"\ndone: {ok}/{len(done)} with art, "
      f"{sum(1 for v in done.values() if v.get('gen'))} with genres")
