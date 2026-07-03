"""
Build the data for the interactive similarity MAP (window.CLUSTERS -> site/clusters.js).

Same era-clean distance the comps use. Projects all players to 2D with classical
MDS (so on-screen distance approximates résumé distance), assigns k-medoid
clusters (archetypes = real players), and ships per-player display stats + top
comps so the map is self-contained and works offline.

Run: python analysis/cluster_map.py    (after analysis/similarity.py has the data)
Needs numpy/scipy — `pip install -r requirements.txt` (venv on PEP 668 Pythons).
Deterministic: same inputs reproduce site/clusters.js byte-for-byte, and
tests/test_generated_artifacts.py fails if the committed output drifts from
site/data.js (stale regeneration, flipped axis, renamed fields).
"""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import similarity as S

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
K = 4  # best silhouette + stability on the era-clean set
# Display names for the K clusters, indexed by the success-ordered id the build
# assigns (0 = lowest mean adjAll .. K-1 = highest). Authored here — next to the
# clustering — so the map page never has to hardcode them against generated ids.
LABELS = ["The field", "Steady winners", "Decorated veterans", "Dynasty peaks"]


def mds_2d(D):
    """Classical MDS. Returns (coords, kept) where kept is the share of the
    distance structure (positive eigenvalue mass) the 2D projection preserves —
    shipped so the map page's prose can quote it instead of hardcoding it."""
    n = len(D)
    D2 = D ** 2
    J = np.eye(n) - np.ones((n, n)) / n
    B = -0.5 * J @ D2 @ J
    w, V = np.linalg.eigh(B)
    order = np.argsort(w)[::-1]
    w, V = w[order], V[:, order]
    kept = float(w[:2].sum() / w[w > 0].sum())
    return V[:, :2] * np.sqrt(np.maximum(w[:2], 0)), kept


def main():
    players, _, fs, D, C = S.build_space()
    names = fs.names
    rec = {p["name"]: p for p in players}

    X, kept = mds_2d(D)
    # orient both axes so the map page's static annotations stay true across
    # regenerations (eigenvector signs are arbitrary): x-axis = overall success
    # (adjAll) increases rightward, y-axis = long/well-traveled careers point
    # DOWN (matching the "efficient · peak-heavy ↑ / ↓ long · well-traveled"
    # axis notes). Then scale to [-1,1].
    adj = np.array([rec[n].get("adjAll", 0) for n in names], float)
    span = np.array([rec[n].get("careerSpan", 0) for n in names], float)
    if np.corrcoef(X[:, 0], adj)[0, 1] < 0:
        X[:, 0] *= -1
    if np.corrcoef(X[:, 1], span)[0, 1] > 0:
        X[:, 1] *= -1
    X = X / np.abs(X).max(0)

    med, lab = S.pam(D, K)
    _, stab = S.bootstrap_stability(fs, D, K, n_boot=150)

    # order clusters left->right by mean success so colors read intuitively
    order = sorted(range(K), key=lambda c: np.mean(adj[lab == c]))
    remap = {c: i for i, c in enumerate(order)}

    def comps(i, k=4):
        out = []
        for j, _ in S.nearest(D, i, C, exclude_teammates=True):
            out.append({"name": names[j], "score": round(100 * (1 - D[i, j]))})
            if len(out) == k:
                break
        return out

    players_out = []
    for i, n in enumerate(names):
        r = rec[n]
        players_out.append({
            "name": n, "x": round(float(X[i, 0]), 4), "y": round(float(X[i, 1]), 4),
            "cluster": remap[int(lab[i])],
            "adj": round(r.get("adjAll", 0), 1), "raw": r.get("raw"),
            "champs": r.get("champs", 0), "titles": r.get("titlesAll"),
            # participation-based career fields (first major ENTERED, years
            # competing) — the same definitions Signatures and the player pages
            # use, not the older first-win/win-span ones
            "span": r.get("careerSpan"), "debut": r.get("firstPlayed"),
            "teams": r.get("distinct_teams"),
            "comps": comps(i),
        })

    clusters_out = []
    for c in order:
        members = np.where(lab == c)[0]
        clusters_out.append({
            "id": remap[c],
            "label": LABELS[remap[c]],
            "archetype": names[med[c]],
            "size": int(len(members)),
            "stability": round(float(stab[c]), 2),
            "profile": S.describe_cluster(fs, members),
        })

    # stats quoted by the map page's prose, recomputed every build so they can't
    # go stale: rAdj = corr(x, adjAll); kept = distance structure preserved in 2D
    stats = {"rAdj": round(float(np.corrcoef(X[:, 0], adj)[0, 1]), 3),
             "kept": round(kept, 3)}

    payload = {"players": players_out, "clusters": clusters_out, "k": K, "stats": stats}
    path = os.path.join(ROOT, "site", "clusters.js")
    with open(path, "w") as fh:
        fh.write("window.CLUSTERS=" + json.dumps(payload, separators=(",", ":")) + ";\n")
    print(f"Wrote {path}  ({len(players_out)} players, k={K})")
    for cl in clusters_out:
        print(f"  cluster {cl['id']}: {cl['archetype']:9s} n={cl['size']:2d} "
              f"stab={cl['stability']}  {cl['profile']}")


if __name__ == "__main__":
    main()
