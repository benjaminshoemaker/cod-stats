#!/usr/bin/env python3
"""Fetch Fandom standard team-logo URLs used on player roster rows.

This is intentionally optional: `build_data.py` reads the cached
team_logos.json when present, but the ranking build never calls the network.
The wiki's tournament tables use files named like "Atlanta FaZelogo std.png";
teams without a matching standard file simply fall back to text on the site.
"""
import hashlib, json, os, re, sys, time, unicodedata, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import build_data

UA = "Mozilla/5.0 (compatible; cod-stats-source-fetch/1.0; +https://cod-stats-one.vercel.app)"
API = "https://cod-esports.fandom.com/api.php"
BATCH = 40
PAUSE = 3
LOGO_DIR = os.path.join(HERE, "site", "assets", "team-logos")


def relevant_teams():
    _, _, _, _, ppart, _ = build_data.load_sources()
    top = {build_data.mkey(n) for n, _ in build_data.PUBLISHED}
    _, part_rows = build_data.index_participation(ppart, top)
    teams = {r.get("team") for rows in part_rows.values() for r in rows.values() if r.get("team")}
    return sorted(teams)


def image_title(team):
    return f"File:{team}logo std.png"


def api(params):
    url = API + "?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.load(r)


def fetch_batch(teams):
    titles = "|".join(image_title(t) for t in teams)
    data = api({
        "action": "query",
        "format": "json",
        "titles": titles,
        "prop": "imageinfo",
        "iiprop": "url",
        "iiurlwidth": "48",
    })
    out = {}
    for page in data.get("query", {}).get("pages", {}).values():
        if "missing" in page or not page.get("imageinfo"):
            continue
        title = page.get("title") or ""
        if not title.startswith("File:") or not title.endswith("logo std.png"):
            continue
        team = title.removeprefix("File:").removesuffix("logo std.png")
        info = page["imageinfo"][0]
        out[team] = {
            "remoteSrc": info.get("thumburl") or info.get("url"),
            "page": info.get("descriptionurl", ""),
            "file": title,
        }
    return out


def logo_name(team):
    slug = unicodedata.normalize("NFKD", team).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", slug).strip("-").lower() or "team"
    suffix = hashlib.sha1(team.encode("utf-8")).hexdigest()[:8]
    return f"{slug}-{suffix}.webp"


def download_logo(team, meta):
    src = meta.get("remoteSrc")
    if not src:
        return None
    os.makedirs(LOGO_DIR, exist_ok=True)
    name = logo_name(team)
    rel = f"assets/team-logos/{name}"
    path = os.path.join(LOGO_DIR, name)
    if os.path.exists(path) and os.path.getsize(path):
        return rel
    req = urllib.request.Request(src, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as r:
        content_type = r.headers.get("content-type", "")
        body = r.read()
    if not content_type.startswith("image/") or not body:
        return None
    with open(path, "wb") as f:
        f.write(body)
    return rel


def main():
    teams = relevant_teams()
    logos = {}
    for i in range(0, len(teams), BATCH):
        batch = teams[i:i + BATCH]
        for attempt in range(4):
            try:
                logos.update(fetch_batch(batch))
                break
            except Exception as e:
                print(f"retry {attempt + 1}: {e}", file=sys.stderr)
                time.sleep(12)
        else:
            raise SystemExit("giving up: wiki unreachable / rate-limited — try again later")
        print(f"{min(i + BATCH, len(teams))}/{len(teams)} teams checked, {len(logos)} logos found")
        time.sleep(PAUSE)

    downloaded = 0
    for team, meta in sorted(logos.items()):
        try:
            local = download_logo(team, meta)
        except Exception as e:
            print(f"logo download failed for {team}: {e}", file=sys.stderr)
            local = None
        if local:
            meta["src"] = local
            downloaded += 1
        else:
            meta["src"] = meta.get("remoteSrc", "")

    path = os.path.join(HERE, "team_logos.json")
    with open(path, "w") as f:
        json.dump(logos, f, indent=2, sort_keys=True)
        f.write("\n")
    print(f"wrote {path} ({len(logos)} logos, {downloaded} local files)")


if __name__ == "__main__":
    main()
