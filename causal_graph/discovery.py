"""Causal discovery from observational data — PC algorithm and score-based methods."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from causal_graph.graph import CausalGraph, NodeType


@dataclass
class DataColumn:
    """A column of observational data for a single variable."""

    name: str
    values: List[float]


@dataclass
class DataSet:
    """A simple columnar dataset for causal discovery."""

    columns: Dict[str, List[float]] = field(default_factory=dict)
    n: int = 0

    def add_column(self, name: str, values: List[float]) -> None:
        self.columns[name] = values
        self.n = len(values)

    def get_column(self, name: str) -> List[float]:
        return self.columns[name]

    @property
    def variable_names(self) -> List[str]:
        return list(self.columns.keys())

    @property
    def num_observations(self) -> int:
        return self.n


# ── Correlation / partial correlation (no numpy) ────────────────────


def _mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _pearson_r(x: List[float], y: List[float]) -> float:
    """Pearson correlation coefficient."""
    n = len(x)
    if n < 2:
        return 0.0
    mx, my = _mean(x), _mean(y)
    dx = [xi - mx for xi in x]
    dy = [yi - my for yi in y]
    num = sum(a * b for a, b in zip(dx, dy))
    den = math.sqrt(sum(a * a for a in dx) * sum(b * b for b in dy))
    return num / den if den > 0 else 0.0


def _partial_correlation(
    x: str, y: str, z: Set[str], data: DataSet
) -> float:
    """Compute partial correlation of x and y given z using recursive formula."""
    if not z:
        return _pearson_r(data.get_column(x), data.get_column(y))

    # Recursive: ρ(x,y|Z) using first-order recursion
    # For simplicity, use the matrix inversion approach for small conditioning sets
    z_list = sorted(z)
    if len(z_list) == 1:
        z_var = z_list[0]
        rxy = _pearson_r(data.get_column(x), data.get_column(y))
        rxz = _pearson_r(data.get_column(x), data.get_column(z_var))
        ryz = _pearson_r(data.get_column(y), data.get_column(z_var))
        denom = math.sqrt((1 - rxz**2) * (1 - ryz**2))
        return (rxy - rxz * ryz) / denom if abs(denom) > 1e-10 else 0.0

    # For larger conditioning sets, use recursive formula
    z1 = z_list[0]
    z_rest = set(z_list[1:])
    rxy_z1 = _partial_correlation(x, y, {z1}, data)
    rxz_rest = _partial_correlation(x, z1, z_rest, data)
    ryz_rest = _partial_correlation(y, z1, z_rest, data)
    denom = math.sqrt((1 - rxz_rest**2) * (1 - ryz_rest**2))
    return (rxy_z1 - rxz_rest * ryz_rest) / denom if abs(denom) > 1e-10 else 0.0


def _fisher_z_test(r: float, n: int, alpha: float = 0.05) -> bool:
    """Fisher's z-test for independence. Returns True if independent."""
    if n < 4:
        return True
    z = 0.5 * math.log((1 + r) / (1 - r + 1e-10))
    z_stat = abs(z) * math.sqrt(n - 3)
    # Two-sided test at alpha; critical value ~1.96 for alpha=0.05
    critical = 1.96 if alpha == 0.05 else 1.645  # simplified
    return z_stat < critical


# ── PC Algorithm ─────────────────────────────────────────────────────


class PCAlgorithm:
    """PC (Peter-Clark) algorithm for causal structure discovery.

    Learns a CPDAG (completed partially directed acyclic graph) from
    observational data using conditional independence tests.

    Parameters:
        alpha: Significance level for independence tests (default 0.05)
        max_cond_set: Maximum conditioning set size (default unlimited)

    Example::

        data = DataSet()
        data.add_column("X", [...])
        data.add_column("Y", [...])
        data.add_column("Z", [...])

        pc = PCAlgorithm(alpha=0.05)
        graph = pc.discover(data)
    """

    def __init__(self, alpha: float = 0.05, max_cond_set: int = 10) -> None:
        self.alpha = alpha
        self.max_cond_set = max_cond_set

    def discover(self, data: DataSet) -> CausalGraph:
        """Run PC algorithm on the dataset. Returns a CausalGraph with
        directed edges where orientation is determined, and undirected
        associations otherwise (represented as bidirectional edges)."""
        variables = data.variable_names
        n_vars = len(variables)
        if n_vars == 0:
            return CausalGraph()

        # Step 1: Start with complete undirected graph
        # adjacency[i] = set of neighbors of variable i
        adj: Dict[str, Set[str]] = {v: set(variables) - {v} for v in variables}
        # sep_set records which variables are conditionally independent given which sets
        sep_set: Dict[Tuple[str, str], Set[str]] = {}

        # Step 2: Remove edges based on conditional independence tests
        depth = 0
        while True:
            removed_any = False
            for x in variables:
                for y in list(adj[x]):
                    if y not in adj[x]:
                        continue
                    # Find candidate conditioning sets from neighbors of x (excluding y)
                    neighbors = sorted(adj[x] - {y})
                    if len(neighbors) < depth:
                        continue
                    # Try all conditioning sets of size `depth`
                    for cond in self._combinations(neighbors, depth):
                        cond_set = set(cond)
                        r = _partial_correlation(x, y, cond_set, data)
                        if _fisher_z_test(r, data.num_observations, self.alpha):
                            # Remove edge x-y
                            adj[x].discard(y)
                            adj[y].discard(x)
                            sep_set[(x, y)] = cond_set
                            sep_set[(y, x)] = cond_set
                            removed_any = True
                            break
                    if y not in adj[x]:
                        continue
            depth += 1
            if not removed_any or depth > self.max_cond_set:
                break

        # Step 3: Orient edges using v-structures (colliders)
        # For each triple X - Z - Y where X and Y are not adjacent,
        # if Z is NOT in sep_set(X,Y), orient as X -> Z <- Y
        orientations: Set[Tuple[str, str]] = set()  # directed edges (a, b) means a -> b

        for z in variables:
            neighbors_z = sorted(adj[z])
            for i in range(len(neighbors_z)):
                for j in range(i + 1, len(neighbors_z)):
                    x, y = neighbors_z[i], neighbors_z[j]
                    # X and Y not adjacent?
                    if y in adj[x]:
                        continue
                    # Z not in sep_set(X, Y)?
                    ss = sep_set.get((x, y), set())
                    if z not in ss:
                        orientations.add((x, z))
                        orientations.add((y, z))

        # Step 4: Apply orientation rules (Meek's rules simplified)
        changed = True
        while changed:
            changed = False
            for x in variables:
                for y in sorted(adj[x]):
                    if (x, y) in orientations:
                        continue
                    if (y, x) in orientations:
                        continue
                    # Rule 1: If z -> x - y and z not adjacent to y, orient x -> y
                    for z in variables:
                        if (z, x) in orientations and y not in adj[z]:
                            orientations.add((x, y))
                            changed = True
                            break

        # Build the graph
        graph = CausalGraph()
        for v in variables:
            graph.add_node(v, NodeType.FACTOR)

        added_edges: Set[Tuple[str, str]] = set()
        for x in variables:
            for y in adj[x]:
                if (y, x) in added_edges:
                    continue
                if (x, y) in orientations:
                    try:
                        graph.add_edge(x, y)
                        added_edges.add((x, y))
                    except ValueError:
                        graph.add_edge_unsafe(x, y)
                        added_edges.add((x, y))
                elif (y, x) not in orientations:
                    # Undirected — add both directions (or just one as "undirected")
                    graph.add_edge_unsafe(x, y)
                    added_edges.add((x, y))

        return graph

    @staticmethod
    def _combinations(items: List[str], k: int) -> List[List[str]]:
        """Generate combinations of items of size k."""
        if k == 0:
            return [[]]
        if k > len(items):
            return []
        result: List[List[str]] = []

        def _combo(start: int, current: List[str]) -> None:
            if len(current) == k:
                result.append(current[:])
                return
            for i in range(start, len(items)):
                current.append(items[i])
                _combo(i + 1, current)
                current.pop()

        _combo(0, [])
        return result


# ── Score-based discovery (BIC) ─────────────────────────────────────


def _compute_mutual_info(x: List[float], y: List[float], bins: int = 10) -> float:
    """Compute discretized mutual information between two continuous variables."""
    n = len(x)
    if n == 0:
        return 0.0
    # Discretize into bins
    x_min, x_max = min(x), max(x)
    y_min, y_max = min(y), max(y)
    x_range = x_max - x_min if x_max > x_min else 1.0
    y_range = y_max - y_min if y_max > y_min else 1.0

    # Joint and marginal histograms
    joint: Dict[Tuple[int, int], int] = {}
    mx: Dict[int, int] = {}
    my: Dict[int, int] = {}
    for i in range(n):
        bx = min(int((x[i] - x_min) / x_range * bins), bins - 1)
        by = min(int((y[i] - y_min) / y_range * bins), bins - 1)
        joint[(bx, by)] = joint.get((bx, by), 0) + 1
        mx[bx] = mx.get(bx, 0) + 1
        my[by] = my.get(by, 0) + 1

    mi = 0.0
    for (bx, by), count in joint.items():
        pxy = count / n
        px = mx.get(bx, 0) / n
        py = my.get(by, 0) / n
        if px > 0 and py > 0 and pxy > 0:
            mi += pxy * math.log(pxy / (px * py))
    return mi


def discover_from_data(
    data: DataSet,
    method: str = "pc",
    alpha: float = 0.05,
) -> CausalGraph:
    """Discover causal structure from observational data.

    Args:
        data: The dataset to analyze.
        method: Discovery method — "pc" (PC algorithm) or "score" (greedy score-based).
        alpha: Significance level (for PC algorithm).

    Returns:
        A CausalGraph with discovered structure.
    """
    if method == "pc":
        pc = PCAlgorithm(alpha=alpha)
        return pc.discover(data)
    elif method == "score":
        return _score_based_discovery(data)
    else:
        raise ValueError(f"Unknown discovery method: {method}")


def _score_based_discovery(data: DataSet) -> CausalGraph:
    """Simple score-based discovery using mutual information and BIC-like penalty."""
    variables = data.variable_names
    n = data.num_observations
    graph = CausalGraph()

    for v in variables:
        graph.add_node(v, NodeType.FACTOR)

    # Compute pairwise mutual information
    mi_matrix: Dict[Tuple[str, str], float] = {}
    for i, x in enumerate(variables):
        for j, y in enumerate(variables):
            if i < j:
                mi = _compute_mutual_info(data.get_column(x), data.get_column(y))
                mi_matrix[(x, y)] = mi
                mi_matrix[(y, x)] = mi

    # Greedy: add edges where MI is above threshold (BIC penalty)
    threshold = math.log(n) / (2 * n) if n > 0 else 0.1

    edges_to_add: List[Tuple[float, str, str]] = []
    for (x, y), mi in mi_matrix.items():
        if x < y and mi > threshold:
            edges_to_add.append((mi, x, y))

    edges_to_add.sort(reverse=True)

    for mi, x, y in edges_to_add:
        # Try both directions, pick the one that doesn't create a cycle
        # Simple heuristic: if x comes before y in the variable order, x -> y
        try:
            graph.add_edge(x, y)
        except ValueError:
            try:
                graph.add_edge(y, x)
            except ValueError:
                pass  # Skip — would create cycle

    return graph
