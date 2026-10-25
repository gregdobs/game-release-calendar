import json, re, time, os, sys, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher

import schedule
allg = schedule.load()
pc = [g for g in allg if 'PC' in g['platforms'] or 'Mac' in g['platforms']]
print("PC/Mac titles to resolve:", len(pc), flush=True)

CACHE = schedule.P('steam_cache.json')
cache = json.load(open(CACHE, encoding='utf-8')) if os.path.exists(CACHE) else {}

def norm(s):
    s = s.lower()
    s = s.replace('&', ' and ').replace('’', "'")
    s = re.sub(r'[^a-z0-9]+', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()

# sub-product noise we never want to match a base game to
BAD = re.compile(r'\b(soundtrack|ost|dlc|deluxe kit|season pass|bundle|demo|beta|'
                 r'upgrade|pack|artbook|art book|expansion|costume|skin|pre-?order)\b', re.I)

def fetch(name):
    if name in cache:
        return cache[name]
    url = ('https://store.steampowered.com/api/storesearch/?term='
           + urllib.parse.quote(name) + '&l=en&cc=US')
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=25) as r:
                items = json.loads(r.read().decode()).get('items', [])
            break
        except Exception:
            if attempt == 2:
                cache[name] = None
                return None
            time.sleep(1.5 * (attempt + 1))

    target = norm(name)
    best, bestscore = None, 0.0
    for it in items:
        if it.get('type') != 'app':
            continue
        cand = it.get('name', '')
        if BAD.search(cand) and not BAD.search(name):
            continue
        sc = SequenceMatcher(None, target, norm(cand)).ratio()
        if norm(cand) == target:
            sc = 1.0
        if sc > bestscore:
            best, bestscore = it, sc

    res = None
    if best and bestscore >= 0.82:
        ms = str(best.get('metascore') or '').strip()
        pr = best.get('price') or {}
        # tiny_image is the only capsule URL that resolves for newer app IDs:
        # the legacy /steam/apps/<id>/header.jpg path 404s, and each asset
        # under store_item_assets carries its own hash, so it can't be rewritten.
        res = {"appid": best['id'], "steamName": best['name'],
               "metascore": int(ms) if ms.isdigit() else None,
               "priceCents": pr.get('final'), "match": round(bestscore, 3),
               "img": best.get('tiny_image')}
    cache[name] = res
    time.sleep(0.05)
    return res

with ThreadPoolExecutor(max_workers=10) as ex:
    for i, _ in enumerate(ex.map(lambda g: fetch(g['name']), pc)):
        if i % 100 == 0:
            print(f"  ...{i}/{len(pc)}", flush=True)

json.dump(cache, open(CACHE, 'w', encoding='utf-8'), indent=1)
hits = sum(1 for v in cache.values() if v)
print(f"resolved {hits}/{len(cache)} ({100*hits//max(len(cache),1)}%)")
print("with metascore:", sum(1 for v in cache.values() if v and v.get('metascore')))
