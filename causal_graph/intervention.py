"""Intervention and counterfactual computation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from causal_graph.graph import CausalGraph


@dataclass
class Intervention:
    """Represents a do-intervention: setting a variable to a fixed value."""

    variable: str
    value: Any

    def __repr__(self) -> str:
        return f"do({self.variable}={self.value})"


@dataclass
class Counterfactual:
    """A counterfactual query: what would Y be if X had been x, given we observed evidence?"""

    target: str
    intervention: Intervention
    evidence: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        ev = ", ".join(f"{k}={v}" for k, v in self.evidence.items())
        return f"CF: {self.target} | {self.intervention}, given {ev}"


class InterventionEngine:
    """Engine for computing interventions and counterfactuals on a CausalGraph.

    Supports:
    - Tracing causal effects of an intervention
    - Computing the effect of do(X=x) on Y
    - Identifying variables affected by an intervention
    - Simple counterfactual reasoning
    """

    def __init__(self, graph: CausalGraph) -> None:
        self.graph = graph

    def intervene(self, intervention: Intervention) -> CausalGraph:
        """Apply an intervention by creating a mutilated graph.

        The do-operator do(X=x) removes all incoming edges to X
        and fixes X's value, simulating a randomized experiment.

        Args:
            intervention: The intervention to apply.

        Returns:
            A new CausalGraph with incoming edges to the intervened variable removed.
        """
        mutilated = CausalGraph()

        # Copy all nodes
        for nid, node in self.graph.nodes.items():
            n_meta = dict(node.metadata)
            if nid == intervention.variable:
                n_meta["intervened"] = True
                n_meta["intervention_value"] = intervention.value
            mutilated.add_node(
                node_id=node.id,
                node_type=node.type,
                description=node.description,
                confidence=node.confidence,
                metadata=n_meta,
            )

        # Copy edges, removing incoming edges to the intervened variable
        for edge in self.graph.edges:
            if edge.target != intervention.variable:
                mutilated.add_edge_unsafe(
                    source=edge.source,
                    target=edge.target,
                    strength=edge.strength,
                    description=edge.description,
                    metadata=dict(edge.metadata),
                )

        return mutilated

    def affected_variables(self, intervention: Intervention) -> Set[str]:
        """Return the set of variables causally affected by the intervention.

        These are the descendants of the intervened variable in the original graph.
        """
        return self.graph.descendants(intervention.variable)

    def causal_effect_path(
        self, intervention: Intervention, target: str
    ) -> List[List[str]]:
        """Find all causal paths from the intervention to the target variable.

        Args:
            intervention: The do-intervention.
            target: The outcome variable.

        Returns:
            List of paths (each a list of node IDs).
        """
        return self.graph.find_all_paths(intervention.variable, target)

    def propagate_intervention(
        self, intervention: Intervention, values: Dict[str, float]
    ) -> Dict[str, float]:
        """Propagate an intervention through the graph using a simple linear model.

        Each node's value is computed as the weighted sum of its parents' values,
        using edge strengths as weights. Intervened variables use their fixed value.

        This is a simplified causal model — real structural equation models would
        be more complex, but this captures the intuition.

        Args:
            intervention: The intervention to apply.
            values: Initial/fixed values for some variables.

        Returns:
            Updated values for all variables after propagation.
        """
        result = dict(values)
        result[intervention.variable] = float(intervention.value)

        # Topological order ensures we process parents before children
        try:
            order = self.graph.topological_sort()
        except ValueError:
            # Fallback: just use arbitrary order if there are cycles
            order = list(self.graph.nodes.keys())

        for node_id in order:
            if node_id == intervention.variable:
                continue  # Use the intervention value
            parents = self.graph.parents(node_id)
            if parents:
                weighted_sum = 0.0
                total_weight = 0.0
                for parent in parents:
                    edges = [
                        e
                        for e in self.graph.edges
                        if e.source == parent and e.target == node_id
                    ]
                    weight = edges[0].strength if edges else 1.0
                    parent_val = result.get(parent, 0.0)
                    weighted_sum += weight * parent_val
                    total_weight += weight
                if total_weight > 0:
                    result[node_id] = result.get(
                        node_id, weighted_sum / total_weight
                    )
                    # Blend: keep existing value but influence by parents
                    existing = result.get(node_id, 0.0)
                    result[node_id] = 0.5 * existing + 0.5 * (
                        weighted_sum / total_weight
                    )

        return result

    def counterfactual(
        self, query: Counterfactual
    ) -> Dict[str, float]:
        """Compute a simplified counterfactual.

        Given observed evidence and a hypothetical intervention, estimate
        what the target variable would have been.

        This uses the twin-network approach conceptually but with the
        simple linear propagation model.

        Args:
            query: The counterfactual query.

        Returns:
            Estimated values under the counterfactual.
        """
        # Step 1: "Abduction" — use evidence to estimate exogenous values
        # In our simplified model, we just use the evidence as-is
        base_values: Dict[str, float] = {}
        for k, v in query.evidence.items():
            base_values[k] = float(v)

        # Step 2: "Action" — apply the intervention
        result = self.propagate_intervention(query.intervention, base_values)

        # Step 3: "Prediction" — read off the target
        return result

    def average_treatment_effect(
        self,
        treatment: str,
        outcome: str,
        value_treated: float = 1.0,
        value_control: float = 0.0,
        base_values: Optional[Dict[str, float]] = None,
    ) -> float:
        """Compute a simplified Average Treatment Effect (ATE).

        ATE = E[Y | do(X=1)] - E[Y | do(X=0)]

        Uses linear propagation as a simplified structural equation model.

        Args:
            treatment: The treatment variable.
            outcome: The outcome variable.
            value_treated: Treatment value for the treated group.
            value_control: Treatment value for the control group.
            base_values: Base values for other variables.

        Returns:
            Estimated ATE.
        """
        bv = base_values or {}

        # Do(X = treated)
        int_treated = Intervention(treatment, value_treated)
        result_treated = self.propagate_intervention(int_treated, bv)

        # Do(X = control)
        int_control = Intervention(treatment, value_control)
        result_control = self.propagate_intervention(int_control, bv)

        return result_treated.get(outcome, 0.0) - result_control.get(outcome, 0.0)
