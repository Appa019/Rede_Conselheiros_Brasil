"""Network metrics computation using NetworKit (C++ parallel) + NetworkX."""

import logging
import math
import time
from concurrent.futures import ThreadPoolExecutor
from itertools import combinations
from typing import Any

import networkx as nx
import networkit as nk
from networkit import centrality as nk_centrality
import numpy as np
from community import community_louvain  # python-louvain package
from scipy import stats

from app.graph.neo4j_client import Neo4jClient
from app.graph import queries

logger = logging.getLogger(__name__)


def _nx_to_nk(G: nx.Graph) -> tuple[nk.Graph, dict[str, int], dict[int, str]]:
    """Convert NetworkX graph to NetworKit, returning the graph and ID mappings."""
    nodes = list(G.nodes())
    nx2nk_map = {n: i for i, n in enumerate(nodes)}
    nk2nx_map = {i: n for n, i in nx2nk_map.items()}

    nk_g = nk.Graph(len(nodes), weighted=True)
    for u, v, data in G.edges(data=True):
        nk_g.addEdge(nx2nk_map[u], nx2nk_map[v], data.get("weight", 1.0))

    return nk_g, nx2nk_map, nk2nx_map


def _nk_scores_to_dict(
    scores: list[float], nk2nx_map: dict[int, str]
) -> dict[str, float]:
    """Map NetworKit score array back to {node_id: score} dict."""
    return {nk2nx_map[i]: s for i, s in enumerate(scores)}

# In-memory cache for the NetworkX graph (avoids rebuilding per request)
_graph_cache: dict[str, Any] = {"graph": None, "timestamp": 0, "ttl": 300}


async def build_networkx_graph(client: Neo4jClient, year: int | None = None) -> nx.Graph:
    """Build a NetworkX graph from Neo4j CO_MEMBER edges."""
    # Get all co-member relationships
    query = """
    MATCH (p1:Person)-[co:CO_MEMBER]-(p2:Person)
    WHERE p1.id < p2.id
    RETURN p1.id AS source, p2.id AS target, co.weight AS weight
    """
    records = await client.execute_read(query)

    G = nx.Graph()
    for record in records:
        G.add_edge(record["source"], record["target"], weight=record["weight"])

    # Add isolated nodes
    isolated_query = """
    MATCH (p:Person)
    WHERE NOT (p)-[:CO_MEMBER]-()
    RETURN p.id AS id
    """
    isolated = await client.execute_read(isolated_query)
    for record in isolated:
        G.add_node(record["id"])

    logger.info(f"Built NetworkX graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    return G


def compute_centrality_metrics(G: nx.Graph) -> dict[str, dict[str, float]]:
    """Compute all centrality metrics using NetworKit (C++ parallel).

    NetworKit automatically uses all available threads for betweenness,
    closeness, eigenvector, and PageRank — ~10-50x faster than NetworkX.
    """
    logger.info(
        "Computing centrality metrics with NetworKit (%d threads)...",
        nk.getMaxNumberOfThreads(),
    )

    nk_g, nx2nk_map, nk2nx_map = _nx_to_nk(G)
    metrics: dict[str, dict[str, float]] = {}

    # Degree centrality (NetworKit, normalized)
    logger.info("  degree centrality...")
    dc = nk_centrality.DegreeCentrality(nk_g, normalized=True)
    dc.run()
    metrics["degree_centrality"] = _nk_scores_to_dict(dc.scores(), nk2nx_map)

    # Betweenness centrality (NetworKit, parallel — the big win)
    logger.info("  betweenness centrality (parallel)...")
    bc = nk_centrality.Betweenness(nk_g, normalized=True)
    bc.run()
    metrics["betweenness"] = _nk_scores_to_dict(bc.scores(), nk2nx_map)

    # Closeness centrality (NetworKit)
    logger.info("  closeness centrality...")
    cc = nk_centrality.Closeness(nk_g, True, nk_centrality.ClosenessVariant.GENERALIZED)
    cc.run()
    metrics["closeness"] = _nk_scores_to_dict(cc.scores(), nk2nx_map)

    # Eigenvector centrality (NetworKit)
    logger.info("  eigenvector centrality...")
    try:
        ec = nk_centrality.EigenvectorCentrality(nk_g)
        ec.run()
        metrics["eigenvector"] = _nk_scores_to_dict(ec.scores(), nk2nx_map)
    except Exception:
        logger.warning("NetworKit eigenvector failed, falling back to NetworkX")
        try:
            metrics["eigenvector"] = nx.eigenvector_centrality(G, max_iter=1000, weight="weight")
        except nx.PowerIterationFailedConvergence:
            metrics["eigenvector"] = nx.eigenvector_centrality_numpy(G, weight="weight")

    # PageRank (NetworKit)
    logger.info("  pagerank...")
    pr = nk_centrality.PageRank(nk_g)
    pr.run()
    metrics["page_rank"] = _nk_scores_to_dict(pr.scores(), nk2nx_map)

    # Clustering coefficient (NetworKit)
    logger.info("  clustering coefficient...")
    lcc = nk_centrality.LocalClusteringCoefficient(nk_g)
    lcc.run()
    metrics["clustering_coeff"] = _nk_scores_to_dict(lcc.scores(), nk2nx_map)

    # K-core decomposition (NetworKit)
    logger.info("  k-core decomposition...")
    core = nk_centrality.CoreDecomposition(nk_g)
    core.run()
    metrics["k_core"] = {
        nk2nx_map[i]: int(s) for i, s in enumerate(core.scores())
    }

    logger.info("All centrality metrics computed")
    return metrics


def compute_communities(G: nx.Graph) -> tuple[dict[str, int], float]:
    """Detect communities using the Louvain method. Returns (partition, modularity)."""
    logger.info("Detecting communities with Louvain...")
    partition = community_louvain.best_partition(G, weight="weight")
    num_communities = len(set(partition.values()))
    modularity = community_louvain.modularity(partition, G, weight="weight")
    logger.info(f"Found {num_communities} communities (modularity={modularity:.4f})")
    return partition, modularity


def compute_structural_holes(G: nx.Graph) -> dict[str, float]:
    """Compute Burt's constraint (structural holes measure)."""
    logger.info("Computing structural holes (Burt constraint)...")
    constraint = nx.constraint(G, weight="weight")
    return {node: val for node, val in constraint.items() if not np.isnan(val)}


def compute_concentration_metrics(
    G: nx.Graph, metrics: dict[str, dict[str, float]]
) -> dict[str, float]:
    """Compute concentration/inequality metrics."""
    logger.info("Computing concentration metrics...")

    # Gini coefficient of degree centrality
    degrees = sorted(metrics["degree_centrality"].values())
    n = len(degrees)
    if n > 0:
        numerator = 2 * sum(i * d for i, d in enumerate(degrees, 1))
        denominator = n * sum(degrees)
        gini = (numerator / denominator - (n + 1) / n) if denominator > 0 else 0
    else:
        gini = 0

    # HHI of seats (concentration per company)
    degree_values = list(dict(G.degree()).values())
    total_seats = sum(degree_values)
    if total_seats > 0:
        shares = [d / total_seats for d in degree_values]
        hhi = sum(s**2 for s in shares)
    else:
        hhi = 0

    # Interlocking index approximated by graph density
    density = nx.density(G) if G.number_of_nodes() > 1 else 0

    return {
        "gini_centrality": round(gini, 4),
        "hhi_seats": round(hhi, 6),
        "interlocking_index": round(density, 4),
        "network_density": round(density, 4),
    }


async def get_cached_graph(client: Neo4jClient) -> nx.Graph:
    """Return a cached NetworkX graph, rebuilding if TTL expired."""
    now = time.time()
    if _graph_cache["graph"] is None or (now - _graph_cache["timestamp"]) > _graph_cache["ttl"]:
        _graph_cache["graph"] = await build_networkx_graph(client)
        _graph_cache["timestamp"] = now
    return _graph_cache["graph"]


def invalidate_graph_cache() -> None:
    """Force cache invalidation (call after ETL/metrics recomputation)."""
    _graph_cache["graph"] = None
    _graph_cache["timestamp"] = 0


def _compute_random_graph_cl(n: int, m: int, seed: int) -> tuple[float, float]:
    """Generate a random graph and return (transitivity, avg_shortest_path)."""
    R = nx.gnm_random_graph(n, m, seed=seed)
    c = nx.transitivity(R)
    # Use largest connected component for path length
    if R.number_of_nodes() > 1:
        largest_cc = max(nx.connected_components(R), key=len)
        Rh = R.subgraph(largest_cc)
        if Rh.number_of_nodes() > 1:
            l_val = nx.average_shortest_path_length(Rh)
        else:
            l_val = float("inf")
    else:
        l_val = float("inf")
    return c, l_val


def _compute_small_world_sigma(
    H: nx.Graph, c_real: float, l_real: float, n_random: int = 5
) -> dict[str, Any]:
    """Compute small-world sigma via ensemble of random graph comparisons.

    Args:
        H: Largest connected component subgraph.
        c_real: Real transitivity of H.
        l_real: Real average shortest path length of H.
        n_random: Number of random reference graphs to generate.

    Returns:
        Dict with small_world_sigma, CI bounds, and is_small_world flag.
    """
    n = H.number_of_nodes()
    m = H.number_of_edges()
    _null: dict[str, Any] = {
        "small_world_sigma": None,
        "small_world_sigma_ci_low": None,
        "small_world_sigma_ci_high": None,
        "is_small_world": False,
    }

    try:
        with ThreadPoolExecutor(max_workers=n_random) as executor:
            futures = [
                executor.submit(_compute_random_graph_cl, n, m, seed=42 + i)
                for i in range(n_random)
            ]
            random_results = [f.result() for f in futures]

        c_randoms = [r[0] for r in random_results]
        l_randoms = [r[1] for r in random_results if r[1] != float("inf")]

        c_random = np.mean(c_randoms) if c_randoms else 0
        l_random = np.mean(l_randoms) if l_randoms else float("inf")

        if c_random <= 0 or l_random <= 0 or l_real <= 0 or l_random == float("inf"):
            return _null

        sigmas = [
            (c_real / c_r) / (l_real / l_r)
            for c_r, l_r in random_results
            if c_r > 0 and l_r > 0 and l_r != float("inf")
        ]
        sigma = (c_real / c_random) / (l_real / l_random)

        return {
            "small_world_sigma": round(sigma, 4),
            "is_small_world": sigma > 1,
            "small_world_sigma_ci_low": round(float(np.percentile(sigmas, 2.5)), 4) if len(sigmas) >= 3 else None,
            "small_world_sigma_ci_high": round(float(np.percentile(sigmas, 97.5)), 4) if len(sigmas) >= 3 else None,
        }
    except Exception as exc:
        logger.warning("Small-world computation failed: %s", exc)
        return _null


def _compute_rich_club(G: nx.Graph) -> dict[str, Any]:
    """Compute rich-club coefficients (raw and normalized) for top 5% of degrees.

    Returns:
        Dict with rich_club_top and rich_club_normalized.
    """
    result: dict[str, Any] = {}

    try:
        rc = nx.rich_club_coefficient(G, normalized=False)
        sorted_keys = sorted(rc.keys())
        n_keys = max(5, min(20, int(len(sorted_keys) * 0.05)))
        top_keys = sorted_keys[-n_keys:] if len(sorted_keys) > n_keys else sorted_keys
        result["rich_club_top"] = {k: round(rc[k], 4) for k in top_keys}
    except Exception:
        logger.warning("Rich-club (unnormalized) computation failed, using empty dict", exc_info=True)
        result["rich_club_top"] = {}

    try:
        rc_norm = nx.rich_club_coefficient(G, normalized=True)
        sorted_keys = sorted(rc_norm.keys())
        n_keys = max(5, min(20, int(len(sorted_keys) * 0.05)))
        top_keys = sorted_keys[-n_keys:] if len(sorted_keys) > n_keys else sorted_keys
        result["rich_club_normalized"] = {k: round(rc_norm[k], 4) for k in top_keys}
    except Exception:
        logger.warning("Normalized rich-club computation failed, using empty dict")
        result["rich_club_normalized"] = {}

    return result


def compute_advanced_metrics(G: nx.Graph) -> dict[str, Any]:
    """Compute advanced structural metrics: assortativity, transitivity, small-world, etc."""
    logger.info("Computing advanced metrics...")
    result: dict[str, Any] = {}

    # Assortativity
    try:
        result["assortativity"] = round(nx.degree_assortativity_coefficient(G), 4)
    except Exception:
        logger.warning("Assortativity computation failed, defaulting to 0.0", exc_info=True)
        result["assortativity"] = 0.0

    # Transitivity (global clustering)
    result["transitivity"] = round(nx.transitivity(G), 4)

    # Path-based metrics on the largest connected component
    _path_null = {
        "avg_shortest_path": None,
        "diameter": None,
        "small_world_sigma": None,
        "small_world_sigma_ci_low": None,
        "small_world_sigma_ci_high": None,
        "is_small_world": False,
    }

    if G.number_of_nodes() > 0:
        largest_cc = max(nx.connected_components(G), key=len)
        H = G.subgraph(largest_cc).copy()

        if H.number_of_nodes() > 1:
            avg_path = round(nx.average_shortest_path_length(H), 4)
            result["avg_shortest_path"] = avg_path
            result["diameter"] = nx.diameter(H)
            result.update(_compute_small_world_sigma(H, nx.transitivity(H), avg_path))
        else:
            result.update(_path_null)
    else:
        result.update(_path_null)

    result.update(_compute_rich_club(G))
    return result


def _fit_power_law(arr: np.ndarray, xmin: int) -> tuple[float, float]:
    """MLE power-law fit for a given xmin. Returns (alpha, ks_distance)."""
    tail = arr[arr >= xmin]
    if len(tail) < 10:
        return float("inf"), float("inf")
    alpha = 1 + len(tail) / np.sum(np.log(tail / (xmin - 0.5)))
    # KS distance between empirical and fitted CDF
    sorted_tail = np.sort(tail)
    n = len(sorted_tail)
    empirical_cdf = np.arange(1, n + 1) / n
    fitted_cdf = 1 - (xmin / sorted_tail) ** (alpha - 1)
    ks_d = float(np.max(np.abs(empirical_cdf - fitted_cdf)))
    return float(alpha), ks_d


def _bootstrap_power_law_ci(
    tail: np.ndarray, xmin: int, n_bootstrap: int = 50
) -> tuple[float | None, float | None]:
    """Bootstrap confidence interval for the power-law alpha exponent.

    Args:
        tail: Degree values in the tail (>= xmin).
        xmin: Lower bound for the power-law fit.
        n_bootstrap: Number of bootstrap resamples.

    Returns:
        (ci_low, ci_high) at 95% level, or (None, None) if insufficient data.
    """
    rng = np.random.default_rng(42)
    boot_alphas = []
    for _ in range(n_bootstrap):
        boot_sample = rng.choice(tail, size=len(tail), replace=True)
        boot_alpha = 1 + len(boot_sample) / np.sum(np.log(boot_sample / (xmin - 0.5)))
        if np.isfinite(boot_alpha):
            boot_alphas.append(boot_alpha)

    if len(boot_alphas) >= 10:
        return (
            round(float(np.percentile(boot_alphas, 2.5)), 4),
            round(float(np.percentile(boot_alphas, 97.5)), 4),
        )
    return None, None


def _compute_lognormal_vs_pl(
    tail: np.ndarray, alpha: float, xmin: int
) -> tuple[float | None, float | None]:
    """Log-likelihood ratio test (Vuong) comparing log-normal vs power-law fit.

    Args:
        tail: Degree values in the tail (>= xmin).
        alpha: Fitted power-law exponent.
        xmin: Lower bound used for the power-law fit.

    Returns:
        (ratio, vuong_p_value), or (None, None) on failure.
    """
    try:
        log_tail = np.log(tail)
        mu_ln = float(np.mean(log_tail))
        sigma_ln = float(np.std(log_tail))

        if sigma_ln <= 0:
            return None, None

        ll_pl = (
            len(tail) * np.log(alpha - 1)
            - len(tail) * np.log(xmin)
            - alpha * np.sum(np.log(tail / xmin))
        )
        ll_ln = float(np.sum(stats.lognorm.logpdf(tail, s=sigma_ln, scale=np.exp(mu_ln))))

        ratio = float(ll_pl - ll_ln)
        n_tail = len(tail)
        std_ratio = float(np.std([
            np.log((alpha - 1) / xmin) - alpha * np.log(d / xmin)
            - stats.lognorm.logpdf(d, s=sigma_ln, scale=np.exp(mu_ln))
            for d in tail
        ]))
        vuong_p = (
            2 * (1 - stats.norm.cdf(abs(ratio) / (std_ratio * np.sqrt(n_tail))))
            if std_ratio > 0
            else 1.0
        )
        return round(ratio, 4), round(float(vuong_p), 4)
    except Exception:
        return None, None


def compute_degree_distribution(G: nx.Graph) -> dict[str, Any]:
    """Compute degree distribution statistics and power-law fit (Clauset et al. 2009)."""
    logger.info("Computing degree distribution...")
    degrees = [d for _, d in G.degree() if d > 0]

    if not degrees:
        return {
            "mean": 0, "median": 0, "std": 0, "skewness": 0,
            "power_law_alpha": None, "power_law_alpha_ci_low": None,
            "power_law_alpha_ci_high": None, "power_law_xmin": None,
            "power_law_p_value": None, "is_power_law": False,
            "logn_vs_pl_ratio": None, "logn_vs_pl_p_value": None,
        }

    arr = np.array(degrees, dtype=float)
    result: dict[str, Any] = {
        "mean": round(float(np.mean(arr)), 4),
        "median": round(float(np.median(arr)), 4),
        "std": round(float(np.std(arr)), 4),
        "skewness": round(float(stats.skew(arr)), 4),
    }

    # Power-law MLE with optimal xmin (Clauset et al. 2009)
    try:
        unique_degrees = sorted(set(int(d) for d in arr if d >= 1))
        if len(unique_degrees) < 3:
            raise ValueError("Too few unique degree values")

        # Find xmin that minimizes KS distance
        best_xmin, best_ks, best_alpha = unique_degrees[0], float("inf"), float("inf")
        for xm in unique_degrees:
            alpha, ks_d = _fit_power_law(arr, xm)
            if ks_d < best_ks:
                best_ks, best_xmin, best_alpha = ks_d, xm, alpha

        tail = arr[arr >= best_xmin]
        if len(tail) < 10 or best_alpha == float("inf"):
            raise ValueError("Insufficient tail data for power-law fit")

        p_value = float(stats.kstest(
            tail,
            lambda x: 1 - (best_xmin / x) ** (best_alpha - 1),
        ).pvalue)

        result["power_law_alpha"] = round(best_alpha, 4)
        result["power_law_xmin"] = int(best_xmin)
        result["power_law_p_value"] = round(p_value, 4)
        result["is_power_law"] = p_value > 0.05

        ci_low, ci_high = _bootstrap_power_law_ci(tail, best_xmin)
        result["power_law_alpha_ci_low"] = ci_low
        result["power_law_alpha_ci_high"] = ci_high

        ratio, vuong_p = _compute_lognormal_vs_pl(tail, best_alpha, best_xmin)
        result["logn_vs_pl_ratio"] = ratio
        result["logn_vs_pl_p_value"] = vuong_p

    except Exception as exc:
        logger.warning("Power-law fit failed: %s", exc)
        result.update({
            "power_law_alpha": None, "power_law_alpha_ci_low": None,
            "power_law_alpha_ci_high": None, "power_law_xmin": None,
            "power_law_p_value": None, "is_power_law": False,
            "logn_vs_pl_ratio": None, "logn_vs_pl_p_value": None,
        })

    return result


def compute_centrality_correlations(
    G: nx.Graph, metrics_dict: dict[str, dict[str, float]]
) -> list[dict[str, Any]]:
    """Compute Spearman correlations between centrality metrics with Bonferroni correction."""
    logger.info("Computing centrality correlations...")
    metric_names = ["degree_centrality", "betweenness", "closeness", "eigenvector", "page_rank"]
    available = [m for m in metric_names if m in metrics_dict]

    nodes = list(G.nodes())
    pairs = list(combinations(available, 2))
    n_comparisons = len(pairs)
    results: list[dict[str, Any]] = []

    for a, b in pairs:
        vals_a = [metrics_dict[a].get(n, 0) for n in nodes]
        vals_b = [metrics_dict[b].get(n, 0) for n in nodes]
        rho, p_val = stats.spearmanr(vals_a, vals_b)
        if np.isnan(rho) or np.isnan(p_val):
            rho, p_val = 0.0, 1.0
        p_corrected = min(float(p_val) * n_comparisons, 1.0)
        results.append({
            "metric_a": a,
            "metric_b": b,
            "spearman_rho": round(float(rho), 4),
            "p_value": round(float(p_val), 6),
            "p_value_corrected": round(p_corrected, 6),
            "is_significant": p_corrected < 0.05,
        })

    return results


def _random_removal_run(G: nx.Graph, percentages: list[float], seed: int) -> list[dict[str, Any]]:
    """Single run of random node removal for resilience baseline."""
    rng = np.random.default_rng(seed)
    total_nodes = G.number_of_nodes()
    nodes = list(G.nodes())
    rng.shuffle(nodes)

    H = G.copy()
    removed_so_far = 0
    points = []

    for pct in percentages:
        n_remove = max(1, int(total_nodes * pct))
        to_remove = nodes[removed_so_far:n_remove]
        H.remove_nodes_from(to_remove)
        removed_so_far = n_remove

        if H.number_of_nodes() > 0:
            largest = len(max(nx.connected_components(H), key=len)) / total_nodes
        else:
            largest = 0

        points.append({
            "removal_percentage": pct,
            "remaining_largest_component": round(largest, 4),
            "nodes_removed": n_remove,
        })

    return points


def compute_resilience(G: nx.Graph) -> dict[str, Any]:
    """Compute network resilience to targeted removal of top-PageRank nodes with random baseline."""
    logger.info("Computing resilience analysis...")
    if G.number_of_nodes() == 0:
        return {"points": [], "random_points": [], "vulnerability_ratio": None, "is_fragile": False}

    pr = nx.pagerank(G, weight="weight")
    sorted_nodes = sorted(pr, key=pr.get, reverse=True)
    total_nodes = G.number_of_nodes()

    # Baseline largest component
    if total_nodes > 0:
        baseline = len(max(nx.connected_components(G), key=len)) / total_nodes
    else:
        baseline = 0

    percentages = [0.01, 0.02, 0.05, 0.10]
    points = []
    is_fragile = False

    H = G.copy()
    removed_so_far = 0

    for pct in percentages:
        n_remove = max(1, int(total_nodes * pct))
        to_remove = sorted_nodes[removed_so_far:n_remove]
        H.remove_nodes_from(to_remove)
        removed_so_far = n_remove

        if H.number_of_nodes() > 0:
            largest = len(max(nx.connected_components(H), key=len)) / total_nodes
        else:
            largest = 0

        points.append({
            "removal_percentage": pct,
            "remaining_largest_component": round(largest, 4),
            "nodes_removed": n_remove,
        })

        if pct == 0.05 and largest < baseline * 0.5:
            is_fragile = True

    # Random removal baseline (average of 3 runs)
    n_random_runs = 3
    random_runs = [_random_removal_run(G, percentages, seed=42 + i) for i in range(n_random_runs)]

    random_points = []
    for idx, pct in enumerate(percentages):
        avg_remaining = np.mean([run[idx]["remaining_largest_component"] for run in random_runs])
        random_points.append({
            "removal_percentage": pct,
            "remaining_largest_component": round(float(avg_remaining), 4),
            "nodes_removed": points[idx]["nodes_removed"],
        })

    # Vulnerability ratio at 5% removal
    vulnerability_ratio = None
    targeted_5 = next((p for p in points if p["removal_percentage"] == 0.05), None)
    random_5 = next((p for p in random_points if p["removal_percentage"] == 0.05), None)
    if targeted_5 and random_5:
        drop_targeted = baseline - targeted_5["remaining_largest_component"]
        drop_random = baseline - random_5["remaining_largest_component"]
        if drop_random > 0:
            vulnerability_ratio = round(drop_targeted / drop_random, 4)

    return {
        "points": points,
        "random_points": random_points,
        "vulnerability_ratio": vulnerability_ratio,
        "is_fragile": is_fragile,
    }


async def compute_sector_interlocking(client: Neo4jClient) -> list[dict[str, Any]]:
    """Query cross-sector interlocking through shared board members."""
    query = """
    MATCH (p:Person)-[:MEMBER_OF]->(c1:Company)-[:BELONGS_TO]->(s1:Sector)
    MATCH (p)-[:MEMBER_OF]->(c2:Company)-[:BELONGS_TO]->(s2:Sector)
    WHERE s1.nome < s2.nome AND c1.cd_cvm <> c2.cd_cvm
    WITH s1.nome AS sector_a, s2.nome AS sector_b, count(DISTINCT p) AS shared_members
    WHERE shared_members > 0
    RETURN sector_a, sector_b, shared_members
    ORDER BY shared_members DESC
    LIMIT 50
    """
    records = await client.execute_read(query)
    return [
        {"sector_a": r["sector_a"], "sector_b": r["sector_b"], "shared_members": r["shared_members"]}
        for r in records
    ]


async def compute_and_save_metrics(
    client: Neo4jClient, year: int | None = None, on_progress: Any = None
) -> dict[str, Any]:
    """Full metrics computation pipeline: build graph, compute, save back to Neo4j.

    CPU-bound computations (centrality, communities, concentration) are offloaded
    to a thread via asyncio.to_thread so the event loop stays responsive for
    polling requests.
    """
    import asyncio

    def progress(pct: float, msg: str) -> None:
        if on_progress:
            on_progress(pct, msg)

    # 1. Project CO_MEMBER edges
    progress(5, "Projetando arestas CO_MEMBER...")
    logger.info("Projecting CO_MEMBER edges...")
    result = await client.execute_write(queries.PROJECT_CO_MEMBERS, {"year": year})
    edges_created = result[0]["edges_created"] if result else 0
    logger.info(f"Projected {edges_created} CO_MEMBER edges")

    # 2. Build NetworkX graph
    progress(15, "Construindo grafo NetworkX...")
    G = await build_networkx_graph(client, year)

    if G.number_of_nodes() == 0:
        logger.warning("Empty graph, skipping metrics computation")
        return {"status": "empty_graph"}

    # 3. Compute metrics (CPU-bound — run in thread to avoid blocking event loop)
    progress(30, "Calculando centralidades (degree, betweenness, pagerank)...")
    centrality = await asyncio.to_thread(compute_centrality_metrics, G)
    progress(55, "Detectando comunidades (Louvain)...")
    communities, modularity = await asyncio.to_thread(compute_communities, G)
    progress(70, "Calculando concentracao (Gini, HHI)...")
    concentration = await asyncio.to_thread(compute_concentration_metrics, G, centrality)

    # 4. Prepare batch for saving
    progress(75, "Preparando dados para salvar...")
    node_ids = list(G.nodes())
    batch = []
    for node_id in node_ids:
        row = {
            "id": node_id,
            "page_rank": centrality["page_rank"].get(node_id, 0),
            "betweenness": centrality["betweenness"].get(node_id, 0),
            "degree_centrality": centrality["degree_centrality"].get(node_id, 0),
            "eigenvector": centrality["eigenvector"].get(node_id, 0),
            "closeness": centrality["closeness"].get(node_id, 0),
            "clustering_coeff": centrality["clustering_coeff"].get(node_id, 0),
            "community_id": communities.get(node_id, -1),
            "k_core": centrality["k_core"].get(node_id, 0),
        }
        batch.append(row)

    # 5. Save in batches of 500
    progress(80, "Salvando metricas no Neo4j...")
    batch_size = 500
    total_batches = math.ceil(len(batch) / batch_size)
    for i in range(0, len(batch), batch_size):
        chunk = batch[i : i + batch_size]
        await client.execute_write(queries.SAVE_PERSON_METRICS, {"batch": chunk})
        batch_num = i // batch_size + 1
        save_pct = 80 + (batch_num / total_batches) * 15
        progress(save_pct, f"Salvando metricas... ({batch_num}/{total_batches})")

    # Save network-level metrics
    await client.execute_write(
        queries.SAVE_NETWORK_META, {"modularity": round(modularity, 4)}
    )

    progress(98, "Finalizando...")
    logger.info(f"Saved metrics for {len(batch)} nodes")

    return {
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "communities": len(set(communities.values())),
        "modularity": round(modularity, 4),
        "concentration": concentration,
    }
