import json
import os


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NO_CACHE = "public, max-age=0, must-revalidate"


def _headers_by_source():
    with open(os.path.join(ROOT, "site", "vercel.json")) as f:
        config = json.load(f)
    return {
        rule["source"]: {h["key"].lower(): h["value"] for h in rule["headers"]}
        for rule in config["headers"]
    }


def test_pages_revalidate_before_reuse():
    headers = _headers_by_source()
    pages = [
        "/",
        "/index.html",
        "/player.html",
        "/games.html",
        "/game.html",
        "/methodology.html",
        "/scatter.html",
        "/trajectory.html",
        "/heatmap.html",
        "/signatures.html",
        "/map.html",
        "/compare.html",
        "/styleguide.html",
        "/changelog.html",
    ]

    for page in pages:
        assert headers[page]["cache-control"] == NO_CACHE


def test_runtime_assets_revalidate_before_reuse():
    headers = _headers_by_source()
    paths = [
        "/vendor/(.*)",
        "/assets/app.js",
        "/assets/nav.js",
        "/assets/rank.js",
        "/assets/style.css",
        "/data.js",
        "/data.json",
        "/participation.json",
        "/similarity.js",
        "/clusters.js",
    ]

    for path in paths:
        cache_control = headers[path]["cache-control"]
        assert cache_control == NO_CACHE
        assert "stale-while-revalidate" not in cache_control


def test_only_hashed_team_logos_are_immutable():
    headers = _headers_by_source()

    assert headers["/assets/team-logos/(.*)"]["cache-control"] == (
        "public, max-age=31536000, immutable"
    )
