"""Curated franchise weighting used to rank releases by expected popularity.

Scores are editorial priors on pre-release attention (0-100). They are the
default ranking and the fallback whenever live RAWG data is unavailable.
Matching is longest-key-first so "Call of Duty: Modern Warfare" beats "Call of Duty".
"""

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

_ORDER = sorted(TIER.items(), key=lambda kv: -len(kv[0]))

# Platform reach: consoles+PC simultaneous implies a bigger commercial push
_REACH = {"PS5": 3.0, "Xbox Series": 2.6, "Switch 2": 3.0, "PC": 2.4,
          "Switch": 1.6, "PS4": 0.8, "Xbox One": 0.7, "Mac": 0.3,
          "iOS": 0.4, "Android": 0.4, "Quest": 0.2, "PSVR2": 0.2}


def base_score(name):
    """Curated franchise prior, or None when the title isn't a known franchise."""
    low = name.lower()
    for key, val in _ORDER:
        if key in low:
            return val
    return None


def heuristic(game):
    """Blend curated prior, platform reach and Metascore into a 0-100 score."""
    curated = base_score(game["name"])
    score = curated if curated is not None else 40.0

    reach = sum(_REACH.get(p, 0) for p in game["platforms"])
    score += min(reach, 11.0) * (0.9 if curated is None else 0.45)

    ms = (game.get("steam") or {}).get("metascore")
    if ms:
        score += (ms - 75) * 0.25

    if game.get("earlyAccess"):
        score -= 4
    if not game.get("steam") and "PC" in game["platforms"]:
        score -= 3   # no Steam page yet = little public footprint

    return max(1.0, min(100.0, round(score, 1)))
