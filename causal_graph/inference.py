"""Causal inference: do-calculus operations, backdoor/frontdoor criteria."""

from __future__ import annotations

from typing import FrozenSet, List, Optional, Set

from causal_graph.graph import CausalGraph


class CausalInference:
    """Structural causal inference on a CausalGraph.

    Implements:
    - Backdoor criterion identification
    - Front-door criterion identification
    - d-separation testing
    - Adjustment set computation
    """

    def __init__(self, graph: CausalGraph) -> None:
        self.graph = graph

    # ── d-separation ─────────────────────────────────────────────────

    def d_separated(self, x: str, y: str, z: Optional[Set[str]] = None) -> bool:
        """Test whether X ⊥ Y | Z (X is d-separated from Y given Z).

        Uses the Bayes-Ball algorithm. Returns True if X and Y are
        conditionally independent given Z.
        """
        if z is None:
            z = set()

        # Phase 1: find all ancestors of Z
        ancestors_of_z: Set[str] = set()
        for node in z:
            ancestors_of_z.add(node)
            ancestors_of_z |= self.graph.ancestors(node)

        # Phase 2: traverse using Bayes-Ball rules
        # (node, direction) where direction is "up" (from child) or "down" (from parent)
        visited: Set[tuple] = set()
        reachable: Set[str] = set()
        queue: List[tuple] = [(x, "up")]

        while queue:
            current, direction = queue.pop(0)
            if (current, direction) in visited:
                continue
            visited.add((current, direction))

            if current != x:
                reachable.add(current)

            # Rule: arriving via parent ("up")
            if direction == "up" and current not in z:
                # Not blocked: continue up to parents and down to children
                for parent in self.graph.parents(current):
                    queue.append((parent, "up"))
                for child in self.graph.children(current):
                    queue.append((child, "down"))
            # Rule: arriving via child ("down")
            elif direction == "down":
                # If not in Z: continue down to children
                if current not in z:
                    for child in self.graph.children(current):
                        queue.append((child, "down"))
                # If in Z or ancestor of Z: continue up to parents
                if current in ancestors_of_z:
                    for parent in self.graph.parents(current):
                        queue.append((parent, "up"))

        return y not in reachable

    # ── Backdoor criterion ───────────────────────────────────────────

    def backdoor_criterion(self, treatment: str, outcome: str) -> Optional[Set[str]]:
        """Find a minimal adjustment set satisfying the backdoor criterion.

        The backdoor criterion requires a set Z such that:
        1. No node in Z is a descendant of treatment
        2. Z blocks all backdoor paths (non-causal paths from treatment to outcome)

        Returns the adjustment set, or None if no valid set exists.
        """
        descendants_of_treatment = self.graph.descendants(treatment)

        # Get all non-descendants of treatment (candidate adjustment variables)
        candidates = set(self.graph.nodes.keys()) - descendants_of_treatment - {treatment, outcome}

        # Find all backdoor paths (paths that start with an edge INTO treatment)
        backdoor_paths = self._find_backdoor_paths(treatment, outcome)

        if not backdoor_paths:
            return set()  # No confounding — no adjustment needed

        # Try to find minimal blocking set via greedy approach
        # A set Z blocks a path if at least one non-collider on the path is in Z
        # or all colliders on the path (or their descendants) are NOT in Z
        adjustment = set()

        for path in backdoor_paths:
            if self._is_path_blocked(path, adjustment):
                continue
            # Find a variable to add that blocks this path
            blocked = False
            for node in path:
                if node in {treatment, outcome}:
                    continue
                if node not in descendants_of_treatment and node not in {treatment, outcome}:
                    test_set = adjustment | {node}
                    if self._is_path_blocked(path, test_set):
                        adjustment.add(node)
                        blocked = True
                        break
            if not blocked:
                # Check all subsets of candidates (brute force for small graphs)
                for node in sorted(candidates - adjustment):
                    test_set = adjustment | {node}
                    if self._is_path_blocked(path, test_set):
                        adjustment.add(node)
                        break

        # Verify the adjustment set doesn't contain descendants of treatment
        adjustment -= descendants_of_treatment
        return adjustment if adjustment is not None else None

    def _find_backdoor_paths(self, treatment: str, outcome: str) -> List[List[str]]:
        """Find all backdoor paths (non-directed paths from treatment to outcome)."""
        # Backdoor paths go through parents of treatment first
        backdoor_paths: List[List[str]] = []
        for parent in self.graph.parents(treatment):
            paths = self._find_undirected_paths(parent, outcome, {treatment})
            for path in paths:
                backdoor_paths.append([treatment] + path)
        return backdoor_paths

    def _find_undirected_paths(
        self, start: str, end: str, forbidden: Set[str]
    ) -> List[List[str]]:
        """Find all paths ignoring edge direction (moral graph traversal)."""
        paths: List[List[str]] = []

        def dfs(current: str, path: List[str], visited: Set[str]) -> None:
            if current == end:
                paths.append(path[:])
                return
            # Neighbors in both directions
            neighbors = self.graph.children(current) | self.graph.parents(current)
            for neighbor in neighbors:
                if neighbor not in visited and neighbor not in forbidden:
                    visited.add(neighbor)
                    path.append(neighbor)
                    dfs(neighbor, path, visited)
                    path.pop()
                    visited.discard(neighbor)

        dfs(start, [start], {start} | forbidden)
        return paths

    def _is_path_blocked(self, path: List[str], conditioning_set: Set[str]) -> bool:
        """Check if a path is blocked given a conditioning set (d-separation rules)."""
        # A path is blocked if there exists a non-collider that is conditioned on,
        # or a collider that is NOT conditioned on (and none of its descendants are).
        for i in range(1, len(path) - 1):
            prev_node = path[i - 1]
            curr_node = path[i]
            next_node = path[i + 1]

            # Determine if curr_node is a collider on this path
            # Collider: both edges point into curr_node
            prev_to_curr = curr_node in self.graph.children(prev_node)
            curr_to_next = next_node in self.graph.children(curr_node)

            is_collider = (not prev_to_curr) and (not curr_to_next)
            # More precisely: prev→curr and next→curr
            is_collider = (curr_node in self.graph.children(prev_node)) and (
                curr_node in self.graph.children(next_node)
            )

            if is_collider:
                # Blocked if collider and none of its descendants are in conditioning set
                if curr_node not in conditioning_set and not (
                    self.graph.descendants(curr_node) & conditioning_set
                ):
                    return True  # Blocked by collider
            else:
                # Non-collider: blocked if conditioned on
                if curr_node in conditioning_set:
                    return True
        return False

    # ── Front-door criterion ─────────────────────────────────────────

    def frontdoor_criterion(self, treatment: str, outcome: str) -> Optional[Set[str]]:
        """Find a set satisfying the front-door criterion.

        The front-door criterion requires a set Z such that:
        1. Treatment → Z (treatment blocks all directed paths to Z)
        2. Z → Outcome (no unblocked backdoor path from treatment to Z)
        3. No backdoor path from Z to outcome that isn't blocked by treatment

        Returns the mediator set, or None if front-door criterion cannot be satisfied.
        """
        # Find mediators on causal paths
        mediators = self.graph.find_mediators(treatment, outcome)

        # Check each mediator for front-door criterion
        valid: Set[str] = set()
        for med in mediators:
            # Condition 1: all directed paths from treatment to mediator
            if not self.graph.has_path(treatment, med):
                continue

            # Condition 2: no unblocked backdoor from treatment to mediator
            # (should be no common causes)
            confounders_tm = self.graph.find_confounders(treatment, med)
            if confounders_tm:
                continue

            # Condition 3: all directed paths from mediator to outcome
            if not self.graph.has_path(med, outcome):
                continue

            valid.add(med)

        return valid if valid else None

    # ── Intervention (do-operator, structural) ───────────────────────

    def do_intervention(self, treatment: str, outcome: str) -> CausalGraph:
        """Apply the do-operator: create a mutilated graph where all edges
        into the treatment node are removed (simulates intervention).

        Returns a new CausalGraph with incoming edges to treatment removed.
        """
        mutilated = CausalGraph()
        # Copy all nodes
        for nid, node in self.graph.nodes.items():
            mutilated.add_node(
                node_id=node.id,
                node_type=node.type,
                description=node.description,
                confidence=node.confidence,
                metadata=dict(node.metadata),
            )
        # Copy all edges EXCEPT those into treatment
        for edge in self.graph.edges:
            if edge.target != treatment:
                mutilated.add_edge_unsafe(
                    source=edge.source,
                    target=edge.target,
                    strength=edge.strength,
                    description=edge.description,
                    metadata=dict(edge.metadata),
                )
        return mutilated

    # ── Summary ──────────────────────────────────────────────────────

    def identify_confounders(self, cause: str, effect: str) -> Set[str]:
        """Identify potential confounders between cause and effect."""
        return self.graph.find_confounders(cause, effect)

    def identify_mediators(self, cause: str, effect: str) -> Set[str]:
        """Identify mediators on causal paths from cause to effect."""
        return self.graph.find_mediators(cause, effect)
