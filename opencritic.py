"""OpenCritic review scores for released titles.

OpenCritic's only sanctioned API is the RapidAPI listing (api.opencritic.com
itself answers 400 to anything without a RapidAPI proxy secret):

  https://rapidapi.com/opencritic-opencritic-default/api/opencritic-api

Subscribe to the free tier, copy the X-RapidAPI-Key, then:

  setx OPENCRITIC_API_KEY "your-key"
  python opencritic.py            # fetch what's missing, then exit
  python opencritic.py --limit 20 # cap requests (default 190; free plan is
                                  # 200 requests + 25 searches per day)
  python build_data.py            # bake the scores into index.html

Only titles whose release date has passed are queried - unreleased games
have no reviews. Results land in opencritic_cache.json; titles that had no
reviews yet are re-checked after RECHECK_DAYS, because reviews arrive after
launch. Each new title costs two requests (search + game). A 429 stops the
run and keeps everything fetched so far.

opencritic_manual.json overrides the cache, keyed by the exact title:
  {"Hades II": {"id": 14921}}                 pin the right OpenCritic page
  {"Some Game": {"score": 81, "tier": "Strong", "url": "https://..."}}
  {"Wrong Match": null}                       never show a score
Manual scores need no key at all.
"""
import json, os, re, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import date
from difflib import SequenceMatcher

HERE = os.path.dirname(os.path.abspath(__file__))
P = lambda *a: os.path.join(HERE, *a)
HOST = "opencritic-api.p.rapidapi.com"
CACHE = P("opencritic_cache.json")
MANUAL = P("opencritic_manual.json")
RECHECK_DAYS = 7
MIN_MATCH = 0.82
SEARCH_CAP = 25   # free plan: 25 searches + 200 requests per day


class RateLimited(Exception):
    pass


def _get(path, key):
    req = urllib.request.Request("https://" + HOST + path, headers={
        "X-RapidAPI-Key": key, "X-RapidAPI-Host": HOST,
        "User-Agent": "GameCal/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        if e.code == 429:
            raise RateLimited()
        if e.code in (401, 403):
            raise SystemExit("OpenCritic/RapidAPI rejected the key (HTTP %d). "
                             "Check OPENCRITIC_API_KEY and that you're subscribed." % e.code)
        raise


def _norm(s):
    s = re.sub(r"\s*\(\d{4}\)\s*$", "", s)  # "Star Fox (2026)" is "Star Fox" there
    s = s.lower().replace("é", "e").replace("ō", "o")
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


_NUM = re.compile(r"^(\d+|i{1,3}|iv|v|vi{0,3}|ix|x)$")


def _nums(s):
    """Sequel numbers in a title: 'Slay the Spire 2' and 'Slay the Spire' differ."""
    return {t for t in _norm(s).split() if _NUM.match(t)}


def same_game(a, b):
    return _nums(a) == _nums(b) and SequenceMatcher(None, _norm(a), _norm(b)).ratio() >= MIN_MATCH


def tier_of(score):
    return "Mighty" if score >= 84 else "Strong" if score >= 75 else "Fair" if score >= 65 else "Weak"


def _slug(name):
    return re.sub(r"[^a-z0-9]+", "-", _norm(name)).strip("-")


def _record(g):
    """Reduce an OpenCritic game object to what the calendar uses."""
    sc = g.get("topCriticScore")
    rec = {"id": g.get("id"), "ocName": g.get("name"),
           "url": g.get("url") or "https://opencritic.com/game/%s/%s" % (g.get("id"), _slug(g.get("name") or "")),
           "checked": date.today().isoformat()}
    if sc is not None and sc >= 0 and (g.get("numTopCriticReviews") or g.get("numReviews") or 0) > 0:
        rec["score"] = round(sc, 1)
        rec["tier"] = g.get("tier") or tier_of(sc)
        rec["reviews"] = g.get("numReviews") or g.get("numTopCriticReviews")
        if g.get("percentRecommended") is not None and g["percentRecommended"] >= 0:
            rec["pct"] = round(g["percentRecommended"])
    return rec


def lookup(name, key, pinned_id=None):
    gid = pinned_id
    if gid is None:
        q = re.sub(r"\s*\(\d{4}\)\s*$", "", name)
        hits = _get("/game/search?criteria=" + urllib.parse.quote(q), key) or []
        tgt, best, bs = _norm(name), None, 0.0
        for h in hits:
            if _nums(h.get("name") or "") != _nums(name):
                continue
            s = SequenceMatcher(None, tgt, _norm(h.get("name") or "")).ratio()
            if s > bs:
                best, bs = h, s
        if not best or bs < MIN_MATCH:
            return {"miss": 1, "checked": date.today().isoformat()}
        gid = best["id"]
    return _record(_get("/game/%d" % int(gid), key))


def load_cache():
    return json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}


def load_manual():
    return json.load(open(MANUAL, encoding="utf-8")) if os.path.exists(MANUAL) else {}


def _due(entry, today):
    if not entry:
        return True
    if entry.get("score") is not None:
        return False
    checked = entry.get("checked")
    return not checked or (today - date.fromisoformat(checked)).days >= RECHECK_DAYS


def fetch(games, key, limit=None, search_cap=SEARCH_CAP):
    """Fill opencritic_cache.json for released titles. Returns requests used.

    The free plan allows SEARCH_CAP searches a day; titles pinned by id in
    opencritic_manual.json skip the search and only cost a game lookup."""
    cache, manual, today = load_cache(), load_manual(), date.today()
    names, seen = [], set()
    # most anticipated first, so a capped run spends quota where it matters
    for g in sorted(games, key=lambda g: -(g.get("score") or 0)):
        n = g["name"]
        if n in seen or not g.get("date") or date.fromisoformat(g["date"]) > today:
            continue
        seen.add(n)
        m = manual.get(n, "absent")
        if m is None or (isinstance(m, dict) and m.get("score") is not None):
            continue  # manual entry wins, no request needed
        if _due(cache.get(n), today):
            names.append(n)
    used = searches = skipped = 0
    print(f"  OpenCritic: {len(names)} released titles to check")
    try:
        for n in names:
            if limit is not None and used + 2 > limit:
                print(f"  stopped at --limit {limit}")
                break
            pinned = (manual.get(n) or {}).get("id") if isinstance(manual.get(n), dict) else None
            if not pinned:
                if searches >= search_cap:
                    skipped += 1
                    continue
                searches += 1
            try:
                try:
                    cache[n] = lookup(n, key, pinned)
                except RateLimited:
                    time.sleep(10)  # usually a short burst limit; retry once
                    cache[n] = lookup(n, key, pinned)
                got = cache[n].get("ocName")
                if pinned and got and not same_game(n, got):
                    print(f"  check pinned id for {n!r}: OpenCritic calls it {got!r}")
            except RateLimited:
                print("  rate limited by RapidAPI - progress saved, run again later")
                break
            except Exception as e:
                print(f"  {n}: {e}")
                continue
            used += 1 if pinned else 2
            if used % 20 == 0:
                json.dump(cache, open(CACHE, "w", encoding="utf-8"), indent=1)
            time.sleep(0.6)
    finally:
        json.dump(cache, open(CACHE, "w", encoding="utf-8"), indent=1)
    scored = sum(1 for c in cache.values() if c and c.get("score") is not None)
    print(f"  OpenCritic: {scored} titles with scores, ~{used} requests, {searches} searches used")
    if skipped:
        print(f"  {skipped} unpinned titles left for another day (search cap {search_cap})")
    return used


def scores():
    """name -> {score, tier, url, reviews, pct} merged from cache + manual."""
    out = {}
    for n, c in load_cache().items():
        if c and c.get("score") is not None:
            out[n] = c
    for n, m in load_manual().items():
        if m is None:
            out.pop(n, None)
        elif m.get("score") is not None:
            m = dict(m)
            m.setdefault("tier", tier_of(m["score"]))
            out[n] = m
    return out


if __name__ == "__main__":
    key = os.environ.get("OPENCRITIC_API_KEY")
    if not key:
        raise SystemExit("set OPENCRITIC_API_KEY first (see the docstring at the top of opencritic.py)")
    lim = 190  # stay under the free plan's 200 requests/day
    if "--limit" in sys.argv:
        lim = int(sys.argv[sys.argv.index("--limit") + 1])
    cap = SEARCH_CAP  # lower it with --searches N on a second run the same day
    if "--searches" in sys.argv:
        cap = int(sys.argv[sys.argv.index("--searches") + 1])
    import hype, schedule
    games = schedule.load()
    for g in games:
        g["score"] = hype.heuristic(g)
    fetch(games, key, lim, cap)
