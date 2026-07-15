#!/usr/bin/env python3
"""Compare legacy codcompstats aggregate pages against current PlayerStats rows."""

from __future__ import annotations

import json
import re
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import build_data  # noqa: E402

API = "https://cod-esports.fandom.com/api.php"
UA = "Mozilla/5.0 cod_stats legacy stats investigation"
REPORT_PATH = ROOT / "analysis" / "legacy_player_stats_backfill.md"
SOURCE_PATH = ROOT / "legacy_player_event_stats.json"
BATCH_SIZE = 50


@dataclass(frozen=True)
class LegacyPage:
    player: str
    game: str
    title: str
    url: str
    schema: str


DISCOVERY_GAMES = {
    "Ghosts": {"title": "Ghosts", "schema": "ghosts"},
    "Advanced Warfare": {"title": "Advanced Warfare", "schema": "advanced_warfare"},
}


ALIASES = {
    "call of duty championship 2014 us regional final": "call of duty championship 2014/us regional final",
    "call of duty championship 2015 na regional finals": "call of duty championship 2015/north america regional final",
    "call of duty championship 2015 na regional final": "call of duty championship 2015/north america regional final",
    "gfinity spring masters 1": "gfinity spring masters 2015",
    "mlg championship anaheim": "mlg anaheim 2014/international playoffs",
    "mlg cod league season 2": "mlg cod league/2014 season/season 2",
    "mlg cod league season 3": "mlg cod league/2014 season/season 3",
    "mlg pro circuit season 1 playoffs": "mlg cod league/2014 season/season 1/playoffs",
    "mlg pro league season 1 playoffs": "mlg pro league/2015 season/season 1/playoffs",
    "mlg pro league season 1 regular season": "mlg pro league/2015 season/season 1",
    "mlg pro league season 2 playoffs": "mlg pro league/2015 season/season 2/playoffs",
    "mlg pro league season 2 regular season": "mlg pro league/2015 season/season 2",
    "mlg pro league season 3 playoffs": "mlg pro league/2015 season/season 3/playoffs",
    "mlg pro league season 3 regular season": "mlg pro league/2015 season/season 3",
    "mlg world finals": "mlg world finals 2015",
    "season 1 playoffs": "mlg cod league/2014 season/season 1/playoffs",
    "season 3": "mlg cod league/2014 season/season 3",
    "season 3 playoffs": "mlg cod league/2014 season/season 3/playoffs",
    "umg washington d c 2015": "umg washington dc 2015",
    "umg washington dc 2015": "umg washington dc 2015",
}


def clean_wiki_text(value: str) -> str:
    value = value.strip()
    value = re.sub(r"^\|\s*", "", value)
    value = re.sub(r"^(?:align|style|class)=\"[^\"]*\"\s*\|\s*", "", value)
    value = re.sub(r"^(?:[A-Za-z-]+=(?:\"[^\"]*\"|[^|\s]+)\s*)+\|\s*", "", value)
    value = value.replace("'''", "").replace("\t", " ")
    value = re.sub(r"\{\{team\|([^|}]+).*?\}\}", r"\1", value)
    value = re.sub(r"<[^>]+>", "", value)
    return re.sub(r"\s+", " ", value).strip()


def wiki_link(value: str) -> tuple[str, str | None]:
    match = re.search(r"\[\[([^|\]]+)(?:\|([^\]]+))?\]\]", value)
    if not match:
        return clean_wiki_text(value), None
    target = match.group(1).strip().replace("_", " ")
    label = match.group(2) or match.group(1)
    return clean_wiki_text(label), clean_wiki_text(target)


def number(value: str) -> float | int | None:
    value = clean_wiki_text(value)
    if value in {"", "-", "N/A"}:
        return None
    try:
        n = float(value)
    except ValueError:
        return None
    return int(n) if n.is_integer() else n


def norm(value: str | None) -> str:
    if not value:
        return ""
    value = value.replace("_", " ").replace("&", "and").lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    tokens = re.sub(r"\s+", " ", value).strip().split()
    collapsed = []
    for token in tokens:
        if collapsed and collapsed[-1] == token:
            continue
        collapsed.append(token)
    return " ".join(collapsed)


def canonical_key(value: str | None) -> str:
    n = norm(value)
    return norm(ALIASES.get(n, n))


def fetch_wikitext(title: str) -> str:
    params = {
        "action": "query",
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
        "format": "json",
        "titles": title,
    }
    url = f"{API}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as response:
        payload = json.load(response)
    page = next(iter(payload["query"]["pages"].values()))
    return page["revisions"][0]["slots"]["main"]["*"]


def fetch_existing_pages(players: dict[str, str]) -> list[tuple[LegacyPage, str]]:
    candidates = []
    for display_name, wiki_name in players.items():
        for game, meta in DISCOVERY_GAMES.items():
            title = f"{wiki_name}/Statistics/{meta['title']}"
            page = LegacyPage(
                player=display_name,
                game=game,
                title=title,
                url=f"https://cod-esports.fandom.com/wiki/{title.replace(' ', '_')}",
                schema=meta["schema"],
            )
            candidates.append(page)

    found = []
    for i in range(0, len(candidates), BATCH_SIZE):
        batch = candidates[i : i + BATCH_SIZE]
        params = {
            "action": "query",
            "prop": "revisions",
            "rvprop": "content",
            "rvslots": "main",
            "format": "json",
            "titles": "|".join(page.title for page in batch),
        }
        url = f"{API}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as response:
            payload = json.load(response)
        by_title = {page.title: page for page in batch}
        normalized = {
            item["to"]: by_title[item["from"]]
            for item in payload["query"].get("normalized", [])
            if item.get("from") in by_title
        }
        for result in payload["query"]["pages"].values():
            if "missing" in result:
                continue
            source_page = by_title.get(result["title"]) or normalized.get(result["title"])
            if not source_page:
                continue
            content = result["revisions"][0]["slots"]["main"]["*"]
            if "codcompstats.com" not in content and "wikitable" not in content:
                continue
            actual_title = result["title"]
            actual_page = LegacyPage(
                player=source_page.player,
                game=source_page.game,
                title=actual_title,
                url=f"https://cod-esports.fandom.com/wiki/{actual_title.replace(' ', '_')}",
                schema=source_page.schema,
            )
            found.append((actual_page, content))
    return sorted(found, key=lambda item: (item[0].game, item[0].player))


def parse_rows(wikitext: str, page: LegacyPage) -> list[dict]:
    rows = []
    for raw in re.split(r"\n\|-\n", wikitext):
        if not raw.lstrip().startswith("|"):
            continue
        cells = row_cells(raw)
        if len(cells) < 6:
            continue
        if page.schema == "ghosts":
            parsed = parse_ghosts_row(cells)
        else:
            parsed = parse_aw_row(cells)
        if parsed and parsed.get("event"):
            parsed.update(
                {
                    "player": page.player,
                    "game": page.game,
                    "sourceUrl": page.url,
                    "sourcePage": page.title,
                }
            )
            rows.append(parsed)
    return rows


def row_cells(raw: str) -> list[str]:
    raw = raw.strip()
    if "||" in raw:
        return [cell.strip() for cell in raw.split("||")]
    cells = []
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("|") and not line.startswith("|}"):
            cells.append(line)
    return cells


def parse_generic_aggregate_row(cells: list[str]) -> dict | None:
    event_index = next((i for i, cell in enumerate(cells) if "[[" in cell), None)
    if event_index is None or len(cells) <= event_index + 4:
        return None
    event, target = wiki_link(cells[event_index])
    date = clean_wiki_text(cells[0]) if event_index == 1 else None
    return {
        "event": event,
        "eventTarget": target,
        "date": date or None,
        "team": clean_wiki_text(cells[event_index + 1]),
        "placing": None,
        "maps": number(cells[event_index + 2]),
        "kd": number(cells[event_index + 3]),
        "kPerRespawn": number(cells[event_index + 4]),
        "modeMaps": {},
        "modeKd": {},
    }


def parse_ghosts_row(cells: list[str]) -> dict | None:
    generic = parse_generic_aggregate_row(cells)
    if len(cells) < 17:
        return generic
    event, target = wiki_link(cells[1])
    return {
        "event": event,
        "eventTarget": target,
        "date": None,
        "team": clean_wiki_text(cells[2]),
        "placing": number(cells[3]),
        "maps": number(cells[4]),
        "kd": number(cells[5]),
        "kPerRespawn": number(cells[6]),
        "modeMaps": {
            "Domination": number(cells[7]),
            "Blitz": number(cells[10]),
            "Search and Destroy": number(cells[13]),
        },
        "modeKd": {
            "Domination": number(cells[8]),
            "Blitz": number(cells[11]),
            "Search and Destroy": number(cells[14]),
        },
    }


def parse_aw_row(cells: list[str]) -> dict | None:
    generic = parse_generic_aggregate_row(cells)
    if len(cells) < 21:
        return generic
    event, target = wiki_link(cells[1])
    return {
        "event": event,
        "eventTarget": target,
        "date": clean_wiki_text(cells[0]) or None,
        "team": clean_wiki_text(cells[2]),
        "placing": None,
        "maps": number(cells[3]),
        "kd": number(cells[4]),
        "kPerRespawn": number(cells[5]),
        "modeMaps": {
            "Hardpoint": number(cells[6]),
            "Search and Destroy": number(cells[10]),
            "Uplink": number(cells[14]),
            "Capture the Flag": number(cells[17]),
        },
        "modeKd": {
            "Hardpoint": number(cells[7]),
            "Search and Destroy": number(cells[11]),
            "Uplink": number(cells[15]),
            "Capture the Flag": number(cells[18]),
        },
    }


def load_current_rows() -> dict[tuple[str, str], dict[str, dict]]:
    (
        events_all,
        _events,
        pwins,
        _champs_rows,
        ppart,
        _tpart,
        accolades,
        player_stats,
        _player_stats_participants,
        event_pages,
    ) = build_data.load_sources()
    registry = build_data.build_event_registry(events_all, event_pages, pwins, ppart, [], player_stats, accolades)
    current = defaultdict(dict)
    for row in player_stats:
        player = row.get("Player")
        game = row.get("Game")
        if not player or not game:
            continue
        event_id = build_data.event_id_for(row, registry)
        event_name = build_data.event_name_for(row, registry)
        key = canonical_key(event_id) or canonical_key(event_name)
        if not key:
            continue
        bucket = current[(player, game)].setdefault(
            key,
            {
                "event": event_name,
                "eventId": event_id,
                "maps": 0,
                "kills": 0,
                "deaths": 0,
            },
        )
        bucket["maps"] += 1
        bucket["kills"] += int(row.get("Kills") or 0)
        bucket["deaths"] += int(row.get("Deaths") or 0)
    for events in current.values():
        for bucket in events.values():
            bucket["kd"] = round(bucket["kills"] / bucket["deaths"], 3) if bucket["deaths"] else None
    return current


def load_major_keys() -> set[tuple[str, str]]:
    rows = json.loads((ROOT / "major_events.json").read_text())
    keys = set()
    for row in rows:
        game = row.get("Game")
        event = row.get("Event")
        if game and event:
            keys.add((game, canonical_key(event)))
    return keys


def load_major_index() -> dict[tuple[str, str], dict]:
    rows = json.loads((ROOT / "major_events.json").read_text())
    out = {}
    for row in rows:
        game = row.get("Game")
        event = row.get("Event")
        if game and event:
            out[(game, canonical_key(event))] = row
    return out


def legacy_match_keys(row: dict) -> list[str]:
    keys = []
    for value in [row.get("eventTarget"), row.get("event")]:
        key = canonical_key(value)
        if key and key not in keys:
            keys.append(key)
        if key and not re.search(r"\b20\d{2}\b", key):
            for year in ("2013", "2014", "2015"):
                year_key = canonical_key(f"{value} {year}")
                if year_key not in keys:
                    keys.append(year_key)
    return keys


def annotate_rows(legacy_rows: list[dict], current: dict, major_keys: set[tuple[str, str]]) -> list[dict]:
    out = []
    for row in legacy_rows:
        current_events = current.get((row["player"], row["game"]), {})
        match = None
        match_key = None
        for key in legacy_match_keys(row):
            if key in current_events:
                match = current_events[key]
                match_key = key
                break
        major = any((row["game"], key) in major_keys for key in legacy_match_keys(row))
        major_key = next(((row["game"], key) for key in legacy_match_keys(row) if (row["game"], key) in major_keys), None)
        annotated = dict(row)
        annotated["matchKey"] = match_key
        annotated["majorKey"] = major_key
        annotated["isMajor"] = major
        annotated["current"] = match
        annotated["status"] = "overlap" if match else "legacy_only"
        if match and isinstance(row.get("maps"), int):
            annotated["mapDelta"] = row["maps"] - match["maps"]
            annotated["kdDelta"] = (
                round(float(row["kd"]) - match["kd"], 3)
                if row.get("kd") is not None and match.get("kd") is not None
                else None
            )
        else:
            annotated["mapDelta"] = None
            annotated["kdDelta"] = None
        out.append(annotated)
    return out


def source_rows(annotated: list[dict], major_index: dict[tuple[str, str], dict]) -> list[dict]:
    rows = []
    seen = set()
    for row in annotated:
        if not row.get("isMajor") or not isinstance(row.get("maps"), int) or row.get("kd") is None:
            continue
        major = major_index.get(tuple(row["majorKey"] or ()))
        if not major:
            continue
        key = (row["player"], major["Game"], major["Event"], row["sourcePage"])
        if key in seen:
            continue
        seen.add(key)
        out = {
            "Player": row["player"],
            "Game": major["Game"],
            "Event": major["Event"],
            "Date": major.get("Date"),
            "Team": row.get("team") or "",
            "Maps": row["maps"],
            "KD": row["kd"],
            "Granularity": "eventAggregate",
            "Source": "codcompstats legacy wiki page",
            "SourcePage": row["sourcePage"],
            "SourceUrl": row["sourceUrl"],
            "LegacyEvent": row.get("event") or "",
        }
        if row.get("date"):
            out["LegacyDate"] = row["date"]
        if row.get("kPerRespawn") is not None:
            out["KPerRespawn"] = row["kPerRespawn"]
        rows.append(out)
    rows.sort(key=lambda r: (r["Game"], r["Date"] or "", r["Event"], r["Player"]))
    return rows


def fmt(value) -> str:
    if value is None:
        return ""
    return str(value)


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(fmt(cell).replace("|", "\\|") for cell in row) + " |")
    return "\n".join(lines)


def load_player_pages() -> dict[str, str]:
    data = build_data.build()
    return {
        name: player.get("wiki") or name
        for name, player in data["players"].items()
        if name in {display for display, _wins in build_data.PUBLISHED}
    }


def summarize_rows(rows: list[dict]) -> dict:
    usable = [r for r in rows if isinstance(r.get("maps"), int) and r.get("kd") is not None]
    overlaps = [r for r in usable if r["status"] == "overlap"]
    legacy_only = [r for r in usable if r["status"] == "legacy_only"]
    major_legacy_only = [r for r in legacy_only if r["isMajor"]]
    nonmajor_legacy_only = [r for r in legacy_only if not r["isMajor"]]
    overlap_more_maps = [r for r in overlaps if isinstance(r.get("mapDelta"), int) and r["mapDelta"] > 0]
    major_overlap_more_maps = [r for r in overlap_more_maps if r["isMajor"]]
    return {
        "rows": len(rows),
        "usable": len(usable),
        "overlaps": len(overlaps),
        "legacyOnly": len(legacy_only),
        "majorLegacyOnly": len(major_legacy_only),
        "nonmajorLegacyOnly": len(nonmajor_legacy_only),
        "overlapMoreMaps": len(overlap_more_maps),
        "majorOverlapMoreMaps": len(major_overlap_more_maps),
    }


def build_report(annotated: list[dict], found_pages: list[LegacyPage], candidates_checked: int) -> str:
    lines = [
        "# Legacy Player Stat Backfill Investigation",
        "",
        "Expanded audit for GitHub issue #18. This discovers Ghosts and Advanced Warfare legacy statistics pages for published leaderboard players, parses codcompstats-backed aggregate rows, and compares them against the committed CoD Esports Wiki `PlayerStats` map rows.",
        "",
        "## Summary",
        "",
    ]
    by_page = defaultdict(list)
    for row in annotated:
        by_page[(row["player"], row["game"], row["sourceUrl"])].append(row)

    total = summarize_rows(annotated)
    lines.extend(
        [
            f"- Candidate player/game pages checked: {candidates_checked}",
            f"- Existing legacy pages found: {len(found_pages)}",
            f"- Parsed legacy rows: {total['rows']}",
            f"- Usable aggregate rows with maps and K/D: {total['usable']}",
            f"- Legacy-only usable rows: {total['legacyOnly']} ({total['majorLegacyOnly']} major matches, {total['nonmajorLegacyOnly']} non-major/regular-season rows)",
            f"- Current-row overlaps where legacy has more maps: {total['overlapMoreMaps']} ({total['majorOverlapMoreMaps']} major matches)",
            "",
            "Key finding: the legacy pages are worth an ingestion design pass, but only as source-badged event aggregates. The biggest value is Advanced Warfare: multiple major rows are absent from current map-level `PlayerStats`, and several current overlaps are visibly partial.",
            "",
            "## Game-Level Yield",
            "",
        ]
    )
    game_rows = []
    for game in sorted(DISCOVERY_GAMES):
        game_rows.append([game, *summarize_rows([r for r in annotated if r["game"] == game]).values()])
    lines.append(
        markdown_table(
            [
                "Game",
                "legacy rows",
                "usable rows",
                "overlaps current",
                "legacy-only usable",
                "legacy-only majors",
                "legacy-only non-majors",
                "overlaps with more maps",
                "major overlaps with more maps",
            ],
            game_rows,
        )
    )
    lines.extend(["", "## Page-Level Yield", ""])
    summary_rows = []
    for (player, game, _url), rows in by_page.items():
        summary = summarize_rows(rows)
        summary_rows.append(
            [
                player,
                game,
                summary["rows"],
                summary["usable"],
                summary["overlaps"],
                summary["legacyOnly"],
                summary["majorLegacyOnly"],
                summary["overlapMoreMaps"],
            ]
        )
    summary_rows.sort(key=lambda row: (row[1], row[0]))
    lines.append(
        markdown_table(
            [
                "Player",
                "Game",
                "legacy rows",
                "usable rows",
                "overlaps current",
                "legacy-only usable",
                "legacy-only majors",
                "overlaps with more legacy maps",
            ],
            summary_rows,
        )
    )
    lines.extend(
        [
            "",
            "## Legacy-Only Major Rows",
            "",
            "These are the strongest additive candidates because the row maps to the site's major universe and no current map-level `PlayerStats` aggregate exists for that player/event.",
            "",
        ]
    )
    major_legacy_only = [
        row
        for row in annotated
        if row["status"] == "legacy_only"
        and row["isMajor"]
        and isinstance(row.get("maps"), int)
        and row.get("kd") is not None
    ]
    major_legacy_only.sort(key=lambda r: (r["game"], r["event"], r["player"]))
    lines.append(
        markdown_table(
            ["Player", "Game", "Event", "legacy maps", "legacy K/D", "source"],
            [
                [
                    row["player"],
                    row["game"],
                    row["event"],
                    row.get("maps"),
                    row.get("kd"),
                    row["sourcePage"],
                ]
                for row in major_legacy_only
            ],
        )
    )

    lines.extend(
        [
            "",
            "## Partial Current Major Rows",
            "",
            "These rows already have some map-level `PlayerStats`, but the legacy aggregate has more maps. They are useful for event-level display coverage and for identifying source gaps, not for map-row reconstruction.",
            "",
        ]
    )
    partial_major_rows = [
        row
        for row in annotated
        if row["status"] == "overlap"
        and row["isMajor"]
        and isinstance(row.get("mapDelta"), int)
        and row["mapDelta"] > 0
    ]
    partial_major_rows.sort(key=lambda r: (-r["mapDelta"], r["game"], r["event"], r["player"]))
    lines.append(
        markdown_table(
            [
                "Player",
                "Game",
                "Event",
                "legacy maps",
                "current maps",
                "map delta",
                "legacy K/D",
                "current K/D",
            ],
            [
                [
                    row["player"],
                    row["game"],
                    row["event"],
                    row.get("maps"),
                    (row.get("current") or {}).get("maps"),
                    row.get("mapDelta"),
                    row.get("kd"),
                    (row.get("current") or {}).get("kd"),
                ]
                for row in partial_major_rows
            ],
        )
    )

    lines.extend(
        [
            "## Interpretation",
            "",
            "- The pages are parseable through `api.php?action=query`; direct page HTML may be Cloudflare-challenged.",
            "- Legacy rows are event aggregates with map counts, K/D, K/R, and mode-level aggregate splits. They do not expose per-map kills/deaths, maps, opponents, series IDs, or map results.",
            "- Several Advanced Warfare regular-season rows are non-major or league-stage aggregates. They should not enter the site's major-only skill surface unless the product explicitly adds a broader stat context panel.",
            "- Some overlap deltas are large because current `PlayerStats` has partial map rows for that player/event while codcompstats has a complete event aggregate. That is useful for display coverage but not for KOR, map-win reconstruction, or same-map replacement baselines.",
            "",
            "## Recommended Next Steps",
            "",
            "1. Design `legacy_player_event_stats.json` as a separate event-aggregate source with provenance fields before adding ingestion.",
            "2. Start with Advanced Warfare because this audit found the clearest major-only and partial-current gains there.",
            "3. Keep regular-season and non-major league aggregates quarantined unless a separate broader stat-context UI is explicitly designed.",
            "4. If surfaced in the UI, show source badges such as `Map rows` vs `Legacy aggregate`; do not mix aggregate rows into map-row counts, KOR baselines, same-map validation, or map-win reconstruction.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    player_pages = load_player_pages()
    found = fetch_existing_pages(player_pages)
    current = load_current_rows()
    major_keys = load_major_keys()
    major_index = load_major_index()
    legacy_rows = []
    for page, wikitext in found:
        legacy_rows.extend(parse_rows(wikitext, page))
    annotated = annotate_rows(legacy_rows, current, major_keys)
    report = build_report(
        annotated,
        [page for page, _wikitext in found],
        len(player_pages) * len(DISCOVERY_GAMES),
    )
    REPORT_PATH.write_text(report)
    print(f"Wrote {REPORT_PATH.relative_to(ROOT)}")
    if "--write-source" in sys.argv:
        SOURCE_PATH.write_text(json.dumps(source_rows(annotated, major_index), indent=2) + "\n")
        print(f"Wrote {SOURCE_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
