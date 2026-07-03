"""
Build the data for the interactive similarity MAP (window.CLUSTERS -> site/clusters.js).

Same era-clean distance the comps use. Projects all players to 2D with classical
MDS (so on-screen distance approximates résumé distance), assigns k-medoid
clusters (archetypes = real players), and ships per-player display stats + top
comps so the map is self-contained and works offline.

Run: python analysis/cluster_map.py    (after analysis/similarity.py has the data)
"""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import similarity as S

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
K = 4  # best silhouette + stability on the era-clean set


def mds_2d(D):
    n = len(D)
    D2 = D ** 2
    J = np.eye(n) - np.ones((n, n)) / n
    B = -0.5 * J @ D2 @ J
    w, V = np.linalg.eigh(B)
    order = np.argsort(w)[::-1]
    w, V = w[order], V[:, order]
    return V[:, :2] * np.sqrt(np.maximum(w[:2], 0))


def main():
    players = S.load_players()
    players, _ = S.merge_path_features(players)
    reg = S.load_registry()
    fs = S.FeatureSpace(players, reg)
    D = fs.distance_matrix()
    C = S.cowin_matrix(fs.names)
    names = fs.names
    idx = {n: i for i, n in enumerate(names)}
    rec = {p["name"]: p for p in players}

    X = mds_2d(D)
    # orient: x-axis = overall success (adjAll), y stable sign, then scale to [-1,1]
    adj = np.array([rec[n].get("adjAll", 0) for n in names], float)
    if np.corrcoef(X[:, 0], adj)[0, 1] < 0:
        X[:, 0] *= -1
    X = X / np.abs(X).max(0)

    med, lab = S.pam(D, K)
    _, stab = S.bootstrap_stability(fs, D, K, n_boot=150)

    # order clusters left->right by mean success so colors read intuitively
    order = sorted(range(K), key=lambda c: np.mean(adj[lab == c]))
    remap = {c: i for i, c in enumerate(order)}

    def comps(i, k=4):
        out = []
        for j in np.argsort(D[i]):
            if j == i or C[i, j] > 0.15:
                continue
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
            "span": r.get("spanAll"), "debut": r.get("firstYear"),
            "teams": r.get("distinct_teams"),
            "comps": comps(i),
        })

    clusters_out = []
    for c in order:
        members = np.where(lab == c)[0]
        clusters_out.append({
            "id": remap[c],
            "archetype": names[med[c]],
            "size": int(len(members)),
            "stability": round(float(stab[c]), 2),
            "profile": S.describe_cluster(fs, members),
        })

    payload = {"players": players_out, "clusters": clusters_out, "k": K}
    path = os.path.join(ROOT, "site", "clusters.js")
    with open(path, "w") as fh:
        fh.write("window.CLUSTERS=" + json.dumps(payload, separators=(",", ":")) + ";\n")
    print(f"Wrote {path}  ({len(players_out)} players, k={K})")
    for cl in clusters_out:
        print(f"  cluster {cl['id']}: {cl['archetype']:9s} n={cl['size']:2d} "
              f"stab={cl['stability']}  {cl['profile']}")


if __name__ == "__main__":
    main()
