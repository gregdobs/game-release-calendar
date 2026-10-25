"""Game Informer release schedules, one page per year.

  gameinformer.com/<year>  ->  gi<year>.html  ->  gi_parsed_<year>.json

Every game carries "year": the schedule page it came from. A TBA entry is
dropped when a later year's page lists the same title - the 2026 page's
"2027 / TBA" tail is the 2027 page's job once that page exists.
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
P = lambda *a: os.path.join(HERE, *a)
YEARS = [2025, 2026, 2027]


def parsed_path(year):
    return P(f"gi_parsed_{year}.json")


def load(years=YEARS):
    by_year = {}
    for y in years:
        if os.path.exists(parsed_path(y)):
            d = json.load(open(parsed_path(y), encoding="utf-8"))
            by_year[y] = [dict(g, year=y) for g in d["dated"] + d["tba"]]
    out = []
    for y, games in by_year.items():
        later = {g["name"].lower() for y2, gs in by_year.items() if y2 > y for g in gs}
        out += [g for g in games if g["date"] or g["name"].lower() not in later]
    return out
