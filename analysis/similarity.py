"""
Player-similarity engine for the CoD era-adjusted major-wins project.

One canonical dissimilarity feeds everything:
  - a Gower-style, group-weighted, robustly-scaled composite distance in [0, 1].
  - robust scaling (median / IQR) so a few all-time greats don't set the scale.
  - each per-feature distance is CAPPED and BOUNDED, so adding a new feature can
    never blow up the scale -> the metric is extensible by design.
  - missing values are MASKED (averaged over shared features), not imputed.

On top of that distance:
  - comps(name, k)        -> nearest-neighbour comparables (a la Bill James).
  - pam(k)                -> k-medoids; each cluster's centre is a REAL player.
  - ward / average linkage-> hierarchical dendrogram (the narrative view).
  - silhouette / bootstrap-> validation (is the structure real?).

Only numpy + scipy required (`pip install -r requirements.txt`; use a venv on
PEP 668 Pythons). Run `python analysis/similarity.py` for a report — it also
rewrites site/similarity.js, which tests/test_generated_artifacts.py checks
against site/data.js so a stale regeneration can't ship silently.
"""
from __future__ import annotations
import json, os
import numpy as np
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import squareform

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# Co-win Jaccard above this = "basically teammates" — used everywhere a comp list
# skips teammates (here, cluster_map.py, and mirrored in site/player.html's `mate`).
TEAMMATE_COWIN_THR = 0.15


# --------------------------------------------------------------------------- #
# Data loading
# --------------------------------------------------------------------------- #
def load_players(data_json=None):
    """Per-player resume records from site/data.json — the pure-JSON twin of
    data.js that build_data.write() emits for non-browser consumers."""
    data_json = data_json or os.path.join(ROOT, "site", "data.json")
    return json.load(open(data_json))["leaderboard"]


def load_registry(path=None):
    path = path or os.path.join(HERE, "features.json")
    return json.load(open(path))


def merge_path_features(players, path_json=None):
    """Inject career-path features (analysis/path_features.py output) into each
    player record, matched case-insensitively. Missing players just keep NaN on
    those features and the distance masks them out — so the engine stays valid
    even if the path source doesn't cover everyone."""
    path_json = path_json or os.path.join(HERE, "out", "path_features.json")
    if not os.path.exists(path_json):
        return players, 0
    extra = json.load(open(path_json))
    hit = 0
    for p in players:
        pf = extra.get(p["name"].lower())
        if pf:
            hit += 1
            for k, v in pf.items():
                if v is not None:
                    p.setdefault(k, v)
        # era-neutral tenure: YEARS per team (not majors/team, which is era-biased)
        dt, sp = p.get("distinct_teams"), p.get("careerSpan")
        if dt and sp is not None:
            p["tenure_years"] = round(sp / dt, 2)
    return players, hit


def cowin_matrix(names, wins_json=None):
    """Co-win Jaccard between every pair: |events both won| / |events either won|.

    This is the *confound* — every feature is a team outcome, so two players who
    won the same tournaments look similar largely because they were teammates.
    We measure it here so comps can surface the nearest NON-teammate, and so
    clusters can be flagged as "basically one roster." Keys are lower-cased
    because the wins file and the leaderboard disagree on case (ABeZy vs aBeZy).
    """
    from collections import defaultdict
    wins_json = wins_json or os.path.join(ROOT, "player_event_wins.json")
    won = defaultdict(set)
    for r in json.load(open(wins_json)):
        won[r["Player"].lower()].add(r["Event"])
    n = len(names)
    C = np.zeros((n, n))
    sets = [won.get(nm.lower(), set()) for nm in names]
    for i in range(n):
        for k in range(i + 1, n):
            u = sets[i] | sets[k]
            C[i, k] = C[k, i] = (len(sets[i] & sets[k]) / len(u)) if u else 0.0
    return C


# --------------------------------------------------------------------------- #
# Feature matrix + weights
# --------------------------------------------------------------------------- #
class FeatureSpace:
    """Turns raw player records + the registry into a scaled matrix and weights."""

    def __init__(self, players, registry):
        self.players = players
        self.names = [p["name"] for p in players]
        self.reg = registry
        self.cap = float(registry.get("cap", 4.0))

        # flatten groups -> ordered feature list with per-feature weight
        self.feats, self.weights, self.logs, self.labels = [], [], [], []
        for gname, g in registry["groups"].items():
            fs = g["features"]
            w_each = g["weight"] / len(fs)
            for fname, meta in fs.items():
                self.feats.append(fname)
                self.weights.append(w_each)
                self.logs.append(bool(meta.get("log", False)))
                self.labels.append(meta.get("label", fname))
        self.weights = np.array(self.weights, float)
        self.weights /= self.weights.sum()  # normalise to 1

        self._build()

    def _build(self):
        n, m = len(self.players), len(self.feats)
        raw = np.full((n, m), np.nan)
        for i, p in enumerate(self.players):
            for j, f in enumerate(self.feats):
                v = p.get(f, None)
                if v is not None:
                    raw[i, j] = v
        # optional log1p for skewed counts
        for j, is_log in enumerate(self.logs):
            if is_log:
                raw[:, j] = np.log1p(raw[:, j])
        # robust scale: (x - median) / IQR, ignoring NaNs
        self.scaled = np.full_like(raw, np.nan)
        self.center = np.zeros(m)
        self.spread = np.ones(m)
        for j in range(m):
            col = raw[:, j]
            ok = ~np.isnan(col)
            med = np.median(col[ok])
            q1, q3 = np.percentile(col[ok], [25, 75])
            iqr = (q3 - q1) or 1.0
            self.center[j], self.spread[j] = med, iqr
            self.scaled[:, j] = (col - med) / iqr
        self.present = ~np.isnan(self.scaled)

    # --- the one canonical dissimilarity ---------------------------------- #
    def pair_distance(self, i, k):
        """Composite [0,1] distance between players i and k (mask-aware)."""
        both = self.present[i] & self.present[k]
        if not both.any():
            return 1.0
        diff = np.abs(self.scaled[i, both] - self.scaled[k, both])
        d = np.minimum(diff / self.cap, 1.0)          # bounded per-feature
        w = self.weights[both]
        return float((w * d).sum() / w.sum())         # weighted, renormalised

    def distance_matrix(self):
        n = len(self.players)
        D = np.zeros((n, n))
        for i in range(n):
            for k in range(i + 1, n):
                D[i, k] = D[k, i] = self.pair_distance(i, k)
        return D

    def contributions(self, i, k):
        """Per-feature share of the distance between i and k (for explanations)."""
        both = self.present[i] & self.present[k]
        if not both.any():
            return []
        diff = np.abs(self.scaled[i, both] - self.scaled[k, both])
        d = np.minimum(diff / self.cap, 1.0)
        contrib = np.zeros_like(self.weights)
        contrib[both] = self.weights[both] * d
        tot = contrib.sum() or 1.0
        order = np.argsort(-contrib)
        return [(self.labels[j], round(float(contrib[j] / tot), 3))
                for j in order if both[j]]

    # weighted Euclidean coords for Ward (Ward needs a Euclidean embedding)
    def ward_coords(self):
        X = np.nan_to_num(self.scaled, nan=0.0)
        return X * np.sqrt(self.weights)


# --------------------------------------------------------------------------- #
# Comps
# --------------------------------------------------------------------------- #
def nearest(D, i, C=None, exclude_teammates=False, teammate_thr=TEAMMATE_COWIN_THR):
    """Yield (index, cowin) over the players nearest to i — the one walk order
    every comp list (this report, similarity.js, clusters.js) shares, so the
    self-skip and teammate-skip rules can't drift between consumers."""
    for j in np.argsort(D[i]):
        if j == i:
            continue
        cw = float(C[i, j]) if C is not None else None
        if exclude_teammates and cw is not None and cw > teammate_thr:
            continue
        yield int(j), cw


def comps(fs: FeatureSpace, D, name, k=5, C=None,
          exclude_teammates=False, teammate_thr=TEAMMATE_COWIN_THR):
    """Nearest-neighbour comps. If C (co-win matrix) is given, each comp carries
    its overlap; with exclude_teammates=True, comps whose overlap exceeds
    teammate_thr are skipped so you get the nearest player you DIDN'T win with."""
    i = fs.names.index(name)
    out = []
    for j, cw in nearest(D, i, C, exclude_teammates, teammate_thr):
        rec = {
            "name": fs.names[j],
            "score": round(100 * (1 - D[i, j]), 1),
            "drivers": fs.contributions(i, j)[:3],   # what separates them most
        }
        if cw is not None:
            rec["cowin"] = round(cw, 2)
        out.append(rec)
        if len(out) == k:
            break
    return out


# --------------------------------------------------------------------------- #
# k-medoids (PAM): build + swap. Cluster centre = a real player.
# --------------------------------------------------------------------------- #
def pam(D, k, max_iter=100):
    n = len(D)
    medoids = [int(np.argmin(D.sum(1)))]
    while len(medoids) < k:
        nearest = D[:, medoids].min(1)
        gains = np.maximum(0, nearest[:, None] - D).sum(0)
        gains[medoids] = -1
        medoids.append(int(np.argmax(gains)))
    for _ in range(max_iter):
        labels = np.argmin(D[:, medoids], axis=1)
        cur = D[np.arange(n), [medoids[l] for l in labels]].sum()
        improved = False
        for mi in range(k):
            for h in range(n):
                if h in medoids:
                    continue
                trial = medoids.copy()
                trial[mi] = h
                lab = np.argmin(D[:, trial], axis=1)
                cost = D[np.arange(n), [trial[l] for l in lab]].sum()
                if cost < cur - 1e-12:
                    medoids, cur, improved = trial, cost, True
        if not improved:
            break
    labels = np.argmin(D[:, medoids], axis=1)
    return medoids, labels


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #
def silhouette(D, labels):
    n = len(D)
    labels = np.asarray(labels)
    uniq = set(labels.tolist())
    if len(uniq) < 2:
        return 0.0
    sil = np.zeros(n)
    for i in range(n):
        same = labels == labels[i]
        same[i] = False
        if same.sum() == 0:
            sil[i] = 0.0
            continue
        a = D[i, same].mean()
        b = min(D[i, labels == c].mean() for c in uniq if c != labels[i])
        sil[i] = (b - a) / max(a, b) if max(a, b) > 0 else 0.0
    return float(sil.mean())


def bootstrap_stability(fs, D, k, n_boot=200, seed=0):
    """Hennig-style Jaccard stability per reference cluster."""
    rng = np.random.default_rng(seed)
    n = len(D)
    _, ref = pam(D, k)
    ref_sets = [set(np.where(ref == c)[0]) for c in range(k)]
    acc = np.zeros(k)
    for _ in range(n_boot):
        idx = np.unique(rng.integers(0, n, n))
        sub = D[np.ix_(idx, idx)]
        _, lab = pam(sub, k)
        boot_sets = [set(idx[np.where(lab == c)[0]]) for c in range(k)]
        for ci, rs in enumerate(ref_sets):
            rs_s = rs & set(idx)
            best = 0.0
            for bs in boot_sets:
                union = rs_s | bs
                if union:
                    best = max(best, len(rs_s & bs) / len(union))
            acc[ci] += best
    return ref, acc / n_boot


# --------------------------------------------------------------------------- #
# Auto-labelling a cluster from its average z-profile (for readability)
# --------------------------------------------------------------------------- #
# short UI labels + display format per feature (order defines table rows)
SITE_GROUPS = [
    ("Success", [("adjAll", "Adjusted wins", "dec1"), ("champs", "World champs", "int"),
                 ("win_conversion", "Win conversion", "pct")]),
    ("Peak", [("peakAll", "Peak season", "dec1")]),
    ("Placement", [("finals_rate", "Finals rate", "pct"),
                   ("deep_run_rate", "Deep-run rate", "pct")]),
    ("Longevity", [("titlesAll", "Distinct titles", "int"),
                   ("careerSpan", "Career span", "int")]),
    ("Path", [("distinct_teams", "Teams played for", "int"),
              ("tenure_years", "Avg tenure (yrs)", "dec1")]),
]


def shared_percentiles(col):
    """0-100 percentile ranks where equal raw values share one rank.

    Using the average rank for ties keeps identical displayed metrics from
    being classified differently in the player-page comparison table.
    """
    ok = ~np.isnan(col)
    vals = col[ok]
    out = np.full(len(col), np.nan)
    n = len(vals)
    if n == 0:
        return out
    if n == 1:
        out[np.where(ok)[0][0]] = 100.0
        return out
    order = np.argsort(vals, kind="mergesort")
    sorted_vals = vals[order]
    ranks = np.empty(n)
    start = 0
    while start < n:
        end = start + 1
        while end < n and sorted_vals[end] == sorted_vals[start]:
            end += 1
        ranks[order[start:end]] = (start + end - 1) / 2
        start = end
    out[np.where(ok)[0]] = ranks / (n - 1) * 100
    return out


def emit_site(fs, D, C, players, k_solo=6):
    """Write site/similarity.js (window.SIM) — comps + per-player metric
    percentiles for the player-page 'Similar players' block. Debut year rides
    along as non-scored context (era is excluded from the score by design)."""
    n = len(fs.names)
    # percentiles across players for every scored feature
    raw = np.array([[ (players[i].get(f) if players[i].get(f) is not None else np.nan)
                      for f in fs.feats] for i in range(n)], float)
    pct = np.full_like(raw, np.nan)
    for j in range(raw.shape[1]):
        pct[:, j] = shared_percentiles(raw[:, j])

    def comps_list(i, solo):
        out = []
        for j, cw in nearest(D, i, C, exclude_teammates=solo):
            out.append({"name": fs.names[j], "score": round(100 * (1 - D[i, j])),
                        "cowin": round(cw, 2)})
            if len(out) == k_solo:
                break
        return out

    players_out = {}
    for i, name in enumerate(fs.names):
        metrics = {}
        for j, f in enumerate(fs.feats):
            v = raw[i, j]; p = pct[i, j]
            metrics[f] = {"v": None if np.isnan(v) else round(float(v), 2),
                          "p": None if np.isnan(p) else round(float(p))}
        players_out[name] = {
            # participation-based debut (first major ENTERED), matching the map
            # and Signatures — not firstYear, which is the first WIN
            "debut": players[i].get("firstPlayed"),
            "metrics": metrics,
            "solo": comps_list(i, True),
            "all": comps_list(i, False),
        }
    # teammateThr rides along so player.html's "teammate" pill uses the same
    # cutoff the solo lists were built with, instead of hardcoding its own
    payload = {"config": {"groups": SITE_GROUPS,
                          "teammateThr": TEAMMATE_COWIN_THR},
               "players": players_out}
    path = os.path.join(ROOT, "site", "similarity.js")
    with open(path, "w") as fh:
        fh.write("window.SIM=" + json.dumps(payload, separators=(",", ":")) + ";\n")
    print(f"Wrote {path}  (comps + metrics for {n} players)")


def cluster_cowin(C, members):
    """Mean pairwise co-win overlap inside a cluster — high => 'one roster'."""
    if len(members) < 2:
        return 0.0
    vals = [C[a, b] for x, a in enumerate(members) for b in members[x + 1:]]
    return float(np.mean(vals))


def describe_cluster(fs, members):
    prof = np.nanmean(fs.scaled[members], axis=0)
    order = np.argsort(-np.abs(prof))
    bits = []
    for j in order[:3]:
        hi = prof[j] > 0
        bits.append(("high " if hi else "low ") + fs.labels[j].lower())
    return ", ".join(bits)


def build_space():
    """The one shared recipe for constructing the feature space plus its
    distance and co-win matrices. Both entry points (this report and
    cluster_map.py) go through it, so similarity.js and clusters.js can never
    be built from differently-assembled inputs."""
    players = load_players()
    players, hit = merge_path_features(players)
    fs = FeatureSpace(players, load_registry())
    return players, hit, fs, fs.distance_matrix(), cowin_matrix(fs.names)


# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #
def main():
    players, hit, fs, D, C = build_space()
    n = len(fs.names)
    print(f"# Player-similarity engine — {n} players, {len(fs.feats)} features "
          f"(path features merged for {hit}/{n})")
    print(f"  {', '.join(fs.feats)}\n")

    # ---- comps -------------------------------------------------------------
    print(f"## Comps — nearest overall vs nearest NON-teammate (co-win < {TEAMMATE_COWIN_THR})\n")
    print(f"  {'player':10s}   {'nearest overall (score, cw)':34s} nearest non-teammate")
    marquee = ["Crimsix", "Scump", "Simp", "aBeZy", "Cellium", "Karma",
               "Clayster", "FormaL", "Shotzzy", "Arcitys"]
    for who in marquee:
        if who not in fs.names:
            continue
        o = comps(fs, D, who, k=1, C=C)[0]
        nt = comps(fs, D, who, k=1, C=C, exclude_teammates=True)[0]
        left = f"{o['name']} ({o['score']}, cw={o['cowin']})"
        print(f"  {who:10s}   {left:34s} {nt['name']} ({nt['score']}, cw={nt['cowin']})")
    print()

    # ---- choose k ----------------------------------------------------------
    print("## Choosing k (PAM) — silhouette on the composite distance\n")
    scores = {}
    for k in range(2, 9):
        _, lab = pam(D, k)
        s = silhouette(D, lab)
        scores[k] = s
        print(f"  k={k}: silhouette={s:.3f}")
    best_k = max(scores, key=scores.get)
    print(f"\n  -> best silhouette at k={best_k} ({scores[best_k]:.3f})\n")

    # ---- clusters + validation --------------------------------------------
    print(f"## Clusters at k={best_k}  (medoid = archetype player)\n")
    ref, stab = bootstrap_stability(fs, D, best_k, n_boot=200)
    medoids, labels = pam(D, best_k)
    # order clusters by size desc
    order = sorted(range(best_k), key=lambda c: -(labels == c).sum())
    clusters_out = []
    for rank, c in enumerate(order, 1):
        members = np.where(labels == c)[0]
        arch = fs.names[medoids[c]]
        names = sorted((fs.names[m] for m in members),
                       key=lambda nm: -players[fs.names.index(nm)]["adjAll"])
        tag = "STABLE" if stab[c] >= 0.75 else ("weak" if stab[c] >= 0.5 else "UNSTABLE")
        cw = cluster_cowin(C, list(members))
        roster = "  <- largely ONE ROSTER" if cw >= 0.25 else ""
        print(f"  Cluster {rank}: archetype={arch}  (n={len(members)}, "
              f"Jaccard={stab[c]:.2f} [{tag}], mean co-win={cw:.2f}){roster}")
        print(f"    profile: {describe_cluster(fs, members)}")
        preview = ", ".join(names[:12]) + (" ..." if len(names) > 12 else "")
        print(f"    members: {preview}\n")
        clusters_out.append({
            "archetype": arch, "size": int(len(members)),
            "stability": round(float(stab[c]), 3),
            "mean_cowin": round(cw, 3),
            "profile": describe_cluster(fs, members), "members": names,
        })

    # ---- hierarchical cross-check -----------------------------------------
    cond = squareform(D, checks=False)
    Z_avg = linkage(cond, method="average")
    lab_avg = fcluster(Z_avg, t=best_k, criterion="maxclust")
    Z_ward = linkage(fs.ward_coords(), method="ward")
    lab_ward = fcluster(Z_ward, t=best_k, criterion="maxclust")
    print("## Cross-check: hierarchical silhouettes (same k)\n")
    print(f"  average-linkage (on composite D): {silhouette(D, lab_avg-1):.3f}")
    print(f"  Ward (on weighted-Euclidean coords): {silhouette(D, lab_ward-1):.3f}")
    print("  (PAM is primary; agreement here = the structure is metric-robust.)\n")

    # ---- persist -----------------------------------------------------------
    out = {
        "features": fs.feats,
        "weights": dict(zip(fs.feats, fs.weights.round(4).tolist())),
        "best_k": best_k,
        "silhouette": scores,
        "comps": {who: comps(fs, D, who, k=6, C=C) for who in fs.names},
        "comps_non_teammate": {who: comps(fs, D, who, k=6, C=C,
                                          exclude_teammates=True)
                               for who in fs.names},
        "clusters": clusters_out,
        "linkage_ward": Z_ward.tolist(),
        "labels_order": fs.names,
    }
    outp = os.path.join(HERE, "out", "similarity.json")
    json.dump(out, open(outp, "w"), indent=2)
    print(f"Wrote {outp}  (comps for all {n} players + clusters + dendrogram data)")

    emit_site(fs, D, C, players)

    # ---- dendrogram image (optional) --------------------------------------
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from scipy.cluster.hierarchy import dendrogram
        fig, ax = plt.subplots(figsize=(10, 16))
        dendrogram(Z_ward, labels=fs.names, orientation="right",
                   leaf_font_size=7, color_threshold=0.7 * Z_ward[:, 2].max(),
                   ax=ax)
        ax.set_title("CoD player resumes — Ward hierarchical clustering")
        ax.set_xlabel("merge distance (weighted)")
        plt.tight_layout()
        img = os.path.join(HERE, "out", "dendrogram.png")
        plt.savefig(img, dpi=130)
        print(f"Wrote {img}")
    except Exception as e:  # pragma: no cover
        print(f"(dendrogram skipped: {e})")


if __name__ == "__main__":
    main()
