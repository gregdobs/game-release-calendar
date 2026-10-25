"""Curated franchise weighting used to rank releases by expected popularity.

Scores are editorial priors on pre-release attention (0-100). They are the
default ranking and the fallback whenever live RAWG data is unavailable.
Matching is longest-key-first so "Call of Duty: Modern Warfare" beats "Call of Duty",
and whole-word only, so "stray" doesn't hit "Astray" nor "hades" "Shades".

A franchise prior describes a franchise's *new* release. Ports, remasters,
later platform launches and spin-offs of the same franchise are pulled back
toward the unknown-title baseline (see `_damping`).
"""
import re
from datetime import date, datetime

# Tier S - system sellers / franchise events
TIER = {
    "grand theft auto": 100, "resident evil requiem": 98, "marvel's wolverine": 97,
    "the legend of zelda": 96, "call of duty: modern warfare": 95, "elden ring": 95,
    "pokemon": 94, "pokémon": 94, "minecraft": 93, "elder scrolls": 93,

    # Tier A - major AAA
    "gears of war": 91, "halo": 91, "forza horizon": 90, "god of war": 92,
    "final fantasy": 89, "monster hunter": 89, "crimson desert": 88,
    "death stranding": 88, "silent hill": 87, "metal gear": 87,
    "star wars": 87, "diablo": 87, "world of warcraft": 88, "marathon": 84,
    "super mario": 90, "mario": 86, "fire emblem": 85, "xenoblade": 84,
    "splatoon": 87, "star fox": 85, "onimusha": 83, "007": 86,
    "phantom blade zero": 84, "dune: awakening": 82, "nioh": 82,
    "hades": 88, "subnautica": 83, "hollow knight": 88, "palworld": 85,
    "call of duty": 90, "assassin's creed": 86, "kingdom hearts": 83,
    "dragon quest": 82, "yakuza": 81, "persona": 86, "sonic": 80,
    "tekken": 82, "street fighter": 82, "borderlands": 84, "starfield": 82,
    "avowed": 78, "indiana jones": 81, "dragon's dogma": 82,
    "pragmata": 78, "code vein": 74, "invincible vs": 75,
    "mina the hollower": 76, "high on life": 72, "slay the spire": 84,
    "enshrouded": 76, "stray": 80, "octopath traveler": 78,
    "castlevania": 79, "life is strange": 75, "south of midnight": 72,
    "the legend of heroes": 72, "trails": 70, "hytale": 80,
    "deltarune": 84, "rune factory": 71, "fatal frame": 70,
    "front mission": 68, "legacy of kain": 70, "scott pilgrim": 68,
    "gothic": 72, "gears": 85, "gran turismo": 86, "horizon": 84,
    "gotham knights": 68, "gearbox": 70, "gta": 100,

    # Annualised sports - reliably huge sellers
    "nba 2k": 88, "madden nfl": 87, "ea sports fc": 88, "ea sports college football": 84,
    "mlb the show": 78, "wwe 2k": 76, "f1 ": 75, "nhl ": 70,

    # Notable mid-tier / high-buzz indies
    "hollow": 74, "moonlighter": 66, "trine": 66, "jackbox": 68,
    "super meat boy": 66, "goat simulator": 66, "content warning": 68,
    "mouse: p.i.": 72, "mixtape": 68, "solarpunk": 66, "big walk": 66,
    "lies of p": 78, "blue prince": 78, "citizen sleeper": 68,
    "sea of stars": 74, "kena": 70, "tales of the shire": 66,
    "disney dreamlight": 68, "roblox": 82, "once human": 70,
    "aliens: fireteam": 68, "mortal shell": 66, "beast of reincarnation": 70,
    "marvel tokon": 76, "marvel tōkon": 76, "2xko": 78, "granblue": 70,
    "shinobi": 72, "dawn of war": 74, "blood of dawnwalker": 76,
    "warhammer 40,000": 78, "warhammer": 72, "pathologic": 66,
    "animal crossing": 90, "mario tennis": 78, "yoshi": 76,
    "kingdom come": 82, "dynasty warriors": 70, "ace combat": 76,
    "rayman": 72, "prince of persia": 74, "no rest for the wicked": 72,
    "stellar blade": 80, "fantasy life": 70, "little kitty": 68,
    "space marine 2": 82, "winter burrow": 62, "professor layton": 74,
    "rhythm heaven": 74, "bomberman": 68, "carmageddon": 62,
    # Spin-offs / smaller entries: matched before their parent key (longest-first)
    "minecraft dungeons": 66, "minecraft legends": 60,
    "monster hunter stories": 71, "mario tennis": 78, "mario party": 80,
    "mario kart": 92, "mario strikers": 70, "dr. mario": 62,
    "final fantasy vii": 90, "pokemon champions": 80, "pokémon champions": 80,
    "pokemon pokopia": 82, "pokémon pokopia": 82,
    "zelda: echoes": 78, "call of duty: black ops": 88,
    "halo: campaign evolved": 82, "star wars zero company": 74,
    "diablo iv": 84, "warcraft rumble": 58,
    "assassin's creed black flag": 78,
    "lego batman": 72, "lego ": 62,
    "silksong": 92, "nightreign": 84, "helldivers": 84,
}

def _fold(s):
    return (s.lower().replace("é", "e").replace("ō", "o").replace("’", "'")
            .replace("®", "").replace("™", "").strip())


# Franchise keys that are also ordinary words: match only at the start of a
# title ("Horizon Forbidden West", not "Windward Horizon"), or as the whole
# title ("Stray", not "Stray Children").
_START_ONLY = {"horizon", "hollow", "trails", "gears", "halo", "sonic", "marathon",
               "persona", "gothic", "hades", "mixtape", "big walk", "solarpunk"}
_WHOLE_ONLY = {"stray"}


def _pattern(key):
    k = _fold(key)
    if k in _WHOLE_ONLY:
        return re.compile("^" + re.escape(k) + "$")
    # word boundaries that also work around punctuation ("mouse: p.i.", "007")
    return re.compile(("^" if k in _START_ONLY else r"(?<![a-z0-9])") + re.escape(k) + r"(?![a-z0-9])")


_ORDER = [(_pattern(k), v) for k, v in sorted(TIER.items(), key=lambda kv: -len(kv[0].strip()))]

# Platform reach: consoles+PC simultaneous implies a bigger commercial push
_REACH = {"PS5": 3.0, "Xbox Series": 2.6, "Switch 2": 3.0, "PC": 2.4,
          "Switch": 1.6, "PS4": 0.8, "Xbox One": 0.7, "Mac": 0.3,
          "iOS": 0.4, "Android": 0.4, "Quest": 0.2, "PSVR2": 0.2}

BASELINE = 40.0          # prior for a title with no known franchise

# Re-release markers in the title itself. Remakes are deliberately absent:
# a ground-up remake (FF7 Remake, Gothic 1 Remake) is a new game.
_RERELEASE = re.compile(
    r"remaster|\bcollection\b|\bedition\b|\bhd\b|\btrilogy\b|anniversary|\bclassic\b|"
    r"director'?s cut|intergrade|\bre ?mind\b|\bremix\b|\breloaded\b|\bgoty\b|game of the year",
    re.I)

# Existing games arriving on new platforms, whose names carry no marker and
# that may lack a Steam page to date them: name -> year of the original
# release. Only entries after that year count as re-releases. Normalised
# exact names; a trailing "*" matches as a prefix (expansions).
KNOWN_RERELEASES = {
    "minecraft": 2011, "animal crossing: new horizons": 2020, "roblox": 2006,
    "hollow knight": 2017, "xenoblade chronicles 2": 2017, "xenoblade chronicles 3": 2022,
    "pokemon firered": 2004, "pokemon leafgreen": 2004, "final fantasy xiv*": 2013,
    "final fantasy vii rebirth": 2024, "hades ii": 2025, "call of duty: black ops": 2010,
    "call of duty: black ops ii": 2012, "starfield": 2023, "avowed": 2025,
    "indiana jones and the great circle": 2024, "stellar blade": 2024,
    "death stranding 2: on the beach": 2025, "kingdom come: deliverance": 2018,
    "dune: awakening": 2025, "octopath traveler": 2018, "octopath traveler ii": 2023,
    "stray": 2022, "subnautica": 2018, "subnautica: below zero": 2021,
    "sonic frontiers": 2022, "blue prince": 2025, "warhammer 40,000: space marine 2": 2024,
    "lies of p": 2023, "kingdom hearts 2.8 final chapter prologue": 2017,
    # Switch 2 launch-window and cross-platform ports seen on the 2025 page
    "the legend of zelda: breath of the wild": 2017, "the legend of zelda: tears of the kingdom": 2023,
    "super mario party jamboree": 2024, "super mario galaxy": 2007, "super mario galaxy 2": 2010,
    "super mario galaxy + super mario galaxy 2": 2007, "forza horizon 5": 2021,
    "final fantasy xvi": 2023, "silent hill 2": 2024, "persona 3 reload": 2024,
    "street fighter 6": 2023, "yakuza kiwami": 2016, "yakuza kiwami 2": 2017,
    "deltarune: chapter 1": 2018, "deltarune: chapter 2": 2021, "deltarune: chapter 3 & 4": 2025,
    "helldivers 2": 2024, "star wars outlaws": 2024, "cyberpunk 2077": 2020,
}

# Same franchise, much smaller game: board-game tie-ins, party compilations.
_SPINOFF = re.compile(r"monopoly|pinball|solitaire|pico park|\btrivia\b|pok[eé]mon friends", re.I)

# How far a franchise prior is pulled back toward BASELINE (1 = full prior).
DAMP = {"rerelease": 0.55, "later_platform": 0.7, "spinoff": 0.5, "mobile_only": 0.75}


def base_score(name):
    """Curated franchise prior, or None when the title isn't a known franchise."""
    low = _fold(name)
    for pat, val in _ORDER:
        if pat.search(low):
            return val
    return None


def _steam_date(s):
    for fmt in ("%b %d, %Y", "%d %b, %Y", "%B %d, %Y", "%b %Y"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except (ValueError, AttributeError):
            pass
    return None


def is_rerelease(game):
    name = _fold(game["name"])
    if _RERELEASE.search(name):
        return True
    year = int(game["date"][:4]) if game.get("date") else game.get("year", 9999)
    for k, orig in KNOWN_RERELEASES.items():
        if (name.startswith(k[:-1]) if k.endswith("*") else name == k) and year > orig:
            return True
    # Steam already lists an earlier launch: a port or a 1.0 of an old EA game.
    first = _steam_date(game.get("steamReleased") or "")
    if first and game.get("date"):
        launch = date.fromisoformat(game["date"])
        if first.year < launch.year or ((launch - first).days > 60 and "PC" not in game["platforms"]):
            return True
    return False


def _damping(game):
    reasons = []
    if is_rerelease(game):
        reasons.append("rerelease")
    if game.get("laterPlatform"):
        reasons.append("later_platform")
    if _SPINOFF.search(game["name"]):
        reasons.append("spinoff")
    plats = set(game["platforms"])
    if plats and plats <= {"iOS", "Android"}:
        reasons.append("mobile_only")
    return min([DAMP[r] for r in reasons], default=1.0), reasons


def critic_score(oc=None, mc=None):
    """OpenCritic (60%) + Metacritic (40%) over whichever exist; None if neither."""
    parts = [(oc, 0.6), (mc, 0.4)]
    parts = [(v, w) for v, w in parts if v]
    if not parts:
        return None
    return sum(v * w for v, w in parts) / sum(w for _, w in parts)


def heuristic(game):
    """Blend curated prior, platform reach and critic reception into 0-100."""
    curated = base_score(game["name"])
    factor, reasons = _damping(game)
    game["rankNotes"] = reasons
    if curated is None:
        score = BASELINE
    else:
        score = BASELINE + (curated - BASELINE) * factor

    reach = sum(_REACH.get(p, 0) for p in game["platforms"])
    score += min(reach, 11.0) * (0.9 if curated is None else 0.45)

    crit = critic_score(game.get("oc"), (game.get("steam") or {}).get("metascore"))
    if crit:
        score += (crit - 75) * 0.5

    if game.get("earlyAccess"):
        score -= 4
    if not game.get("steam") and "PC" in game["platforms"]:
        score -= 3   # no Steam page yet = little public footprint

    return max(1.0, min(100.0, round(score, 1)))
