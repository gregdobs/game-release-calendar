# Game Release Calendar 2026

A single-file, offline-capable calendar of 2026 video game releases.
Open **`index.html`** by double-clicking it. No server, no install, no build step.

875 titles — 717 with confirmed dates, 158 undated/TBA.

---

## Using it

| | |
|---|---|
| **Opens on the current month** | Today's cell is ringed in green and badged `TODAY`; past days are dimmed. |
| **Up next strip** | The six highest-profile upcoming releases. Click one to jump to its month. |
| **Platform chips** | PC · PlayStation · Xbox · Nintendo · Mobile · VR. Click to combine; click again to clear. |
| **Hover a game** | Detail card appears — art, exact date, countdown, platforms, Metascore, Steam price. |
| **Click a game** | Pins the card so you can reach the store buttons. `Esc` or click away closes it. |
| **Search** | Searches all 875 titles across the whole year and swaps the grid for a result list. |
| **Undated & 2027** | Collapsible shelf at the bottom for announced-but-undated titles. |
| **Ranking** | Switch between editorial hype scores and live RAWG data (see below). |

Games within each day are ordered **most-anticipated first**. A left edge in
amber marks a major release, blue a notable one.

### Storefront links

Every card links to Steam, PS Store, Nintendo, Xbox, Amazon, and the Game
Informer page — but only for platforms that game actually ships on. Steam links
go to the **exact verified app page** for the 543 titles matched to a real Steam
listing; everything else opens a pre-filled search.

---

## Ranking: how "expected popularity" is computed

Ships with a **curated hype score** (0–100) blending three signals:

1. A franchise/publisher prior for ~160 known franchises (`hype.py`)
2. Platform reach — simultaneous multi-platform launches signal a bigger push
3. Metascore, where Steam has one

### Switching to live RAWG data

Click **Ranking** in the toolbar. No Python, no rebuild.

1. Register at <https://rawg.io/apidocs> — free, no card.
2. Copy the key from your RAWG profile page.
3. Paste it into the panel and press **Save & test**. It validates against RAWG
   immediately and tells you if the key is wrong.
4. Press **Fetch live ranking**. About a minute for all 875 titles, with a
   progress bar; it's resumable and safe to interrupt.

Scores switch to RAWG's `added` metric (how many users track the game),
log-normalised to 0–100. The dot on the Ranking button turns green, cards gain a
**RAWG tracking** figure, and anything RAWG can't match keeps its editorial
score. **Use editorial scores** reverts; **Clear** wipes key and cache.

The key is stored in `localStorage` only — never written into `index.html`, so
rebuilding or sharing the file cannot leak it. Results cache locally, so you pay
the fetch once and reloads are instant.

> RAWG's free tier is 20,000 requests/month. A full pass costs ~875, so roughly
> 22 full refreshes per month.

**Build-time alternative.** To bake ranking into `index.html` for everyone —
e.g. sending the file to someone who has no key — set the key and rebuild:
>
> ```bash
> setx RAWG_API_KEY "your-key-here"
> python build_data.py
> ```

#### Why errors say what they say

RAWG returns CORS headers on success but **not** on error responses. A browser
therefore can't read a `401` at all — a rejected key surfaces as an opaque
"Failed to fetch", indistinguishable from being offline. The page resolves this
by probing RAWG's keyless root endpoint: if that answers, the key is bad; if it
doesn't, the connection is. During a bulk fetch, 8 consecutive failures abort the
run rather than burn quota.

---

## Refreshing the data

```bash
python build_data.py --refresh
```

Re-downloads the Game Informer schedule, re-resolves Steam, and regenerates
`index.html`. Without `--refresh` it just rebuilds from the local caches (instant).

---

## Date verification

Game Informer is the primary schedule; every high-profile date was
cross-checked against Steam's own `release_date`. Re-run with
`python verify_dates.py` (writes `verify_report.txt`).

Result for the top 45 titles: **25 exact matches, 19 off by exactly one day, 1 outlier.**

- The one-day gaps are a **systematic timezone artifact, not disagreement** —
  Steam was earlier in all 19 cases and later in zero, because Steam renders
  dates in store-local time while Game Informer lists the nominal launch day.
- The single outlier is **Enshrouded**: Steam reports Jan 24 2024 (its Early
  Access launch) where Game Informer lists Oct 15 2026 (the 1.0 / PS5 release).
  Both are correct about different events.

Game Informer's date is used as canonical throughout.

### A note on apparent duplicates

Some titles appear on two or three different dates. These are **not duplicates** —
they are staggered per-platform launches, and every repeated entry has a
disjoint platform set. Forza Horizon 6 is Xbox/PC on May 19 with PS5 still TBA;
The Relic: First Guardian lands on PS5/PC, Xbox, and Switch 2 on three separate
dates. Cards for these titles carry an **"Other platform dates"** panel listing
the sibling releases. 88 titles are cross-linked this way.

---

## Files

| File | Purpose |
|---|---|
| `index.html` | **The deliverable.** Self-contained; data inlined. |
| `app_template.html` | UI source. Edit this, then rebuild — never edit `index.html` directly. |
| `build_data.py` | Merges sources, scores, writes `index.html`. |
| `parse_gi.py` | Parses the Game Informer schedule. |
| `steam.py` | Resolves Steam app IDs, Metascores, prices, capsule art. |
| `hype.py` | Curated franchise weighting. |
| `steam_details.py` | Optional richer pass: full-size art, genres, blurbs. |
| `verify_dates.py` | Cross-checks dates against Steam. |
| `gi2026.html`, `*_cache.json`, `gi_parsed.json` | Cached source data. |

> Edit `app_template.html`, not `index.html` — the latter is regenerated on
> every build and your changes would be overwritten.

### Genres and blurbs (optional, partial)

422 of the 577 Steam-matched titles also carry genre tags, a short description,
and full-size 460×215 header art, from `steam_details.py`. That endpoint is
rate-limited (~0.7s per app), so the cache is **incomplete by design** — it
stopped partway. Cards without it simply omit those fields.

To finish the remaining ~140 (takes a few minutes, resumable, safe to interrupt):

```bash
python steam_details.py
python build_data.py
```

## Known limits

- Art and images load from Steam's CDN, so cards show placeholders offline.
  Everything else works with no connection.
- 59 PC titles have no Steam page yet (Crimson Desert, Hytale, WoW: Midnight and
  other non-Steam releases); those fall back to a Steam search link.
- Amazon has no public catalogue API, so Amazon links are always searches.
- Late-2026 months are sparse (Nov: 14, Dec: 6) because publishers haven't
  announced those dates yet — re-run `--refresh` periodically.
