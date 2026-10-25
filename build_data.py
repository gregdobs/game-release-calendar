"""Build the Game Release Calendar into a single self-contained index.html.

Sources
  gameinformer.com/2026 ... release dates + platforms (primary schedule)
  Steam storesearch API .. verified app IDs, Metascore, price, capsule art
  RAWG API (optional) .... live popularity ranking, needs RAWG_API_KEY
  OpenCritic (optional) .. review scores for released titles, needs
                           OPENCRITIC_API_KEY (RapidAPI); see opencritic.py

  python build_data.py               # rebuild from cached sources
  python build_data.py --refresh     # re-download Game Informer + Steam first
  python build_data.py --opencritic  # also check OpenCritic for new reviews
"""
import json, os, re, sys, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher
import hype
import opencritic
import schedule

HERE = os.path.dirname(os.path.abspath(__file__))
P = lambda *a: os.path.join(HERE, *a)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) GameCal/1.0"}


def get(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


# ---------------------------------------------------------------- RAWG
def rawg_enrich(games, key):
    """Attach live RAWG popularity (`added` = users who tracked the game)."""
    cache_path = P("rawg_cache.json")
    cache = json.load(open(cache_path, encoding="utf-8")) if os.path.exists(cache_path) else {}

    def one(g):
        n = g["name"]
        if n in cache:
            return
        url = ("https://api.rawg.io/api/games?key=" + key + "&search="
               + urllib.parse.quote(n) + "&page_size=5")
        try:
            items = json.loads(get(url, 25)).get("results", [])
        except Exception as e:
            cache[n] = None
            return
        tgt = re.sub(r"[^a-z0-9]+", " ", n.lower()).strip()
        best, bs = None, 0.0
        for it in items:
            cand = re.sub(r"[^a-z0-9]+", " ", (it.get("name") or "").lower()).strip()
            sc = SequenceMatcher(None, tgt, cand).ratio()
            if sc > bs:
                best, bs = it, sc
        cache[n] = ({"added": best.get("added") or 0,
                     "ratings": best.get("ratings_count") or 0,
                     "metacritic": best.get("metacritic"),
                     "rawgName": best.get("name")} if best and bs >= 0.82 else None)
        time.sleep(0.15)

    with ThreadPoolExecutor(max_workers=6) as ex:
        list(ex.map(one, games))
    json.dump(cache, open(cache_path, "w", encoding="utf-8"), indent=1)

    hits = [c["added"] for c in cache.values() if c and c["added"]]
    print(f"  RAWG matched {sum(1 for c in cache.values() if c)}/{len(cache)}")
    if not hits:
        return
    hi = max(hits)
    import math
    for g in games:
        c = cache.get(g["name"])
        if c and c.get("added"):
            # log-normalise: `added` is heavily long-tailed
            g["rawgAdded"] = c["added"]
            g["score"] = round(1 + 99 * math.log1p(c["added"]) / math.log1p(hi), 1)
            g["scoreSrc"] = "rawg"


# ---------------------------------------------------------------- links
def links(g):
    q = urllib.parse.quote(g["name"])
    out = {}
    st = g.get("steam")
    if st:
        out["steam"] = f"https://store.steampowered.com/app/{st['appid']}/"
    elif "PC" in g["platforms"]:
        out["steam"] = f"https://store.steampowered.com/search/?term={q}"
    if {"PS5", "PS4", "PSVR2"} & set(g["platforms"]):
        out["psn"] = f"https://store.playstation.com/en-us/search/{q}"
    if {"Switch 2", "Switch"} & set(g["platforms"]):
        out["nintendo"] = f"https://www.nintendo.com/us/search/#q={q}&p=1&cat=gme"
    if {"Xbox Series", "Xbox One"} & set(g["platforms"]):
        out["xbox"] = f"https://www.xbox.com/en-US/Search/Results?q={q}"
    out["amazon"] = f"https://www.amazon.com/s?k={q}&i=videogames"
    out["gi"] = g["gi"]
    return out


def main():
    refresh = "--refresh" in sys.argv

    if refresh:
        for y in schedule.YEARS:
            print(f"downloading Game Informer {y} schedule...")
            open(P(f"gi{y}.html"), "w", encoding="utf-8").write(get(f"https://gameinformer.com/{y}", 60))
            os.system(f'"{sys.executable}" "{P("parse_gi.py")}" {y}')

    games = schedule.load()
    steam = json.load(open(P("steam_cache.json"), encoding="utf-8"))
    # Optional richer pass (full-size header art, genres, blurb). Partial files
    # are fine - anything missing falls back to the search-capsule data.
    dpath = P("steam_details.json")
    details = json.load(open(dpath, encoding="utf-8")) if os.path.exists(dpath) else {}
    for y in schedule.YEARS:
        gy = [g for g in games if g["year"] == y]
        print(f"{y}: {len(gy)} games ({sum(1 for g in gy if g['date'])} dated)")

    # A title can appear several times with disjoint platforms. The earliest
    # dated entry is the launch; later or still-TBA siblings are ports.
    first = {}
    for g in games:
        k = g["name"].lower()
        if g["date"] and (k not in first or g["date"] < first[k]):
            first[k] = g["date"]
    for g in games:
        f = first.get(g["name"].lower())
        if f and (g["date"] or "9999") > f:
            g["laterPlatform"] = True

    oc_key = os.environ.get("OPENCRITIC_API_KEY")
    for g in games:
        s = steam.get(g["name"])
        if s:
            g["steam"] = s
            srd = (details.get(str(s.get("appid"))) or {}).get("srd")
            if srd:
                g["steamReleased"] = srd
    if oc_key and (refresh or "--opencritic" in sys.argv):
        print("OpenCritic key found - checking released titles...")
        for g in games:
            g["score"] = hype.heuristic(g)
        opencritic.fetch(games, oc_key)
    ocs = opencritic.scores()
    for g in games:
        o = ocs.get(g["name"])
        if o:
            g["oc"], g["ocInfo"] = o["score"], o
        g["score"] = hype.heuristic(g)
        g["scoreSrc"] = "curated"
    print(f"  OpenCritic scores: {sum(1 for g in games if g.get('oc'))}"
          + ("" if oc_key else " (no OPENCRITIC_API_KEY - cache/manual only)"))

    key = os.environ.get("RAWG_API_KEY")
    if key:
        print("RAWG key found - pulling live popularity...")
        rawg_enrich(games, key)
    else:
        print("no RAWG_API_KEY set - using curated/heuristic ranking")

    out = []
    for g in games:
        st = g.get("steam") or {}
        rec = {"n": g["name"], "d": g["date"], "y": g["year"], "p": g["platforms"],
               "s": g["score"], "src": g["scoreSrc"], "l": links(g)}
        if g.get("earlyAccess"):
            rec["ea"] = 1
        det = details.get(str(st.get("appid"))) or {}
        # prefer the 460x215 header over the 231x87 search capsule
        if det.get("img"):
            rec["img"] = det["img"]
        elif st.get("img"):
            rec["img"] = st["img"]
        if det.get("gen"):
            rec["gen"] = det["gen"]
        if det.get("desc"):
            rec["desc"] = det["desc"]
        if st.get("metascore"):
            rec["mc"] = st["metascore"]
        if st.get("priceCents") is not None:
            rec["pr"] = st["priceCents"]
        if g.get("rawgAdded"):
            rec["ra"] = g["rawgAdded"]
        if g.get("oc"):
            o = g["ocInfo"]
            rec["oc"] = o["score"]
            rec["ocTier"] = o.get("tier") or opencritic.tier_of(o["score"])
            if o.get("url"):
                rec["ocUrl"] = o["url"]
            if o.get("reviews"):
                rec["ocN"] = o["reviews"]
        if g.get("rankNotes"):
            rec["rn"] = g["rankNotes"]
        out.append(rec)

    # A title may appear several times with disjoint platforms (e.g. Forza
    # Horizon 6: Xbox/PC in May, PS5 TBA). Link siblings so the card can say so.
    from collections import defaultdict
    fam = defaultdict(list)
    for r in out:
        fam[r["n"].lower()].append(r)
    for sibs in fam.values():
        if len(sibs) < 2:
            continue
        for r in sibs:
            r["alt"] = [{"d": o["d"], "p": o["p"]} for o in sibs if o is not r]

    out.sort(key=lambda r: (r["d"] or "9999", -r["s"]))
    payload = {"generated": time.strftime("%Y-%m-%d"), "years": schedule.YEARS, "games": out}

    tpl = open(P("app_template.html"), encoding="utf-8").read()
    html = tpl.replace("/*__DATA__*/null",
                       json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    open(P("index.html"), "w", encoding="utf-8").write(html)

    kb = os.path.getsize(P("index.html")) / 1024
    print(f"\nwrote index.html ({kb:.0f} KB)")
    print(f"  steam links: {sum(1 for r in out if 'img' in r)} with art, "
          f"{sum(1 for r in out if 'gen' in r)} with genres, "
          f"{sum(1 for r in out if 'desc' in r)} with blurbs")
    print("\ntop 15 by score:")
    for r in sorted(out, key=lambda r: -r["s"])[:15]:
        print(f"   {r['s']:5.1f}  {r['d'] or 'TBA ':10}  {r['n'][:44]}")


if __name__ == "__main__":
    main()
