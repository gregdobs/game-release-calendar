import re, html, json
from collections import Counter

s = open('gi2026.html', encoding='utf-8', errors='replace').read()
entries = re.findall(r'<span class="calendar_entry">(.*?)</span>', s, re.S)

PLAT = {'PC':'PC','Mac':'Mac','PlayStation 5':'PS5','PlayStation 4':'PS4',
        'PlayStation VR2':'PSVR2','Xbox Series X/S':'Xbox Series','Xbox One':'Xbox One',
        'Switch 2':'Switch 2','Switch':'Switch','iOS':'iOS','Android':'Android',
        'Quest':'Quest','Quest 2':'Quest','Quest 3':'Quest'}

def take(raw, plats):
    for p in (x.strip() for x in raw.split(',')):
        if p in PLAT and PLAT[p] not in plats:
            plats.append(PLAT[p])

games, seen = [], set()
for e in entries:
    m = re.search(r'<a href="([^"]+)"[^>]*>(.*?)</a>', e, re.S)
    if not m: continue
    slug = m.group(1)
    name = html.unescape(re.sub(r'<[^>]+>', '', m.group(2))).strip()

    plats = []
    for em in re.findall(r'<em>(.*?)</em>', e, re.S):
        take(html.unescape(re.sub(r'<[^>]+>', '', em)), plats)
    if not plats:  # TBA rows sometimes omit <em>; whitelist filters title-parens noise
        body = html.unescape(re.sub(r'<[^>]+>', '', e.split('</a>')[-1]))
        for grp in re.findall(r'\(([^)]*)\)', body):
            take(grp, plats)

    ea = bool(re.search(r'\(?\bEarly Access\b\)?', name))
    name = re.sub(r'\s*\(?\bEarly Access\b\)?\s*', ' ', name).strip(' -–')

    tm = re.search(r'<time datetime="([\d\-]+)T', e)
    date = tm.group(1) if tm else None

    key = (name.lower(), date)
    if key in seen: continue
    seen.add(key)
    games.append({"name":name,"date":date,"platforms":plats,
                  "earlyAccess":ea,"gi":"https://gameinformer.com"+slug})

dated   = sorted([g for g in games if g["date"]], key=lambda g:(g["date"],g["name"]))
undated = sorted([g for g in games if not g["date"]], key=lambda g:g["name"])
print("dated:",len(dated),"| TBA:",len(undated),
      "| no-platform:",sum(1 for g in games if not g["platforms"]),
      "| earlyAccess:",sum(1 for g in games if g["earlyAccess"]))
print("platforms:",dict(Counter(p for g in games for p in g["platforms"]).most_common()))
json.dump({"dated":dated,"tba":undated}, open('gi_parsed.json','w',encoding='utf-8'), indent=1)
