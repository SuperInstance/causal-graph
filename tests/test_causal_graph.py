"""Tests for causal_graph package."""

import json
import math
import pytest

from causal_graph import (
    CausalGraph,
    CausalInference,
    InterventionEngine,
    Node,
    Edge,
    NodeType,
    PCAlgorithm,
    discover_from_data,
    render_ascii,
    render_dot,
)
from causal_graph.discovery import DataSet, _pearson_r, _partial_correlation


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def simple_graph() -> CausalGraph:
    """Rain → Wet → Slip"""
    g = CausalGraph()
    g.add_node("rain", NodeType.CAUSE, "Rainfall")
    g.add_node("sprinkler", NodeType.CAUSE, "Sprinkler on")
    g.add_node("wet", NodeType.EFFECT, "Wet ground")
    g.add_node("slip", NodeType.OUTCOME, "Person slips")
    g.add_edge("rain", "wet", strength=0.8)
    g.add_edge("sprinkler", "wet", strength=0.6)
    g.add_edge("wet", "slip", strength=0.5)
    return g


@pytest.fixture
def confounded_graph() -> CausalGraph:
    """Z → X → Y, Z → Y (Z confounds X and Y)"""
    g = CausalGraph()
    g.add_node("Z", NodeType.FACTOR)
    g.add_node("X", NodeType.CAUSE)
    g.add_node("Y", NodeType.EFFECT)
    g.add_edge("Z", "X", strength=0.9)
    g.add_edge("Z", "Y", strength=0.7)
    g.add_edge("X", "Y", strength=0.6)
    return g


@pytest.fixture
def mediation_graph() -> CausalGraph:
    """X → M → Y with direct X → Y"""
    g = CausalGraph()
    g.add_node("X", NodeType.CAUSE)
    g.add_node("M", NodeType.FACTOR)
    g.add_node("Y", NodeType.EFFECT)
    g.add_edge("X", "M", strength=0.8)
    g.add_edge("M", "Y", strength=0.7)
    g.add_edge("X", "Y", strength=0.3)
    return g


# ── Graph core ───────────────────────────────────────────────────────


class TestNode:
    def test_node_creation(self):
        n = Node(id="test", type=NodeType.CAUSE, description="A test node")
        assert n.id == "test"
        assert n.type == NodeType.CAUSE

    def test_node_hash_equality(self):
        n1 = Node(id="x")
        n2 = Node(id="x")
        assert n1 == n2
        assert hash(n1) == hash(n2)

    def test_node_eq_string(self):
        n = Node(id="x")
        assert n == "x"


class TestCausalGraphBasic:
    def test_add_node(self):
        g = CausalGraph()
        n = g.add_node("A", NodeType.CAUSE)
        assert "A" in g
        assert g.get_node("A") is not None
        assert len(g) == 1

    def test_add_node_string_type(self):
        g = CausalGraph()
        g.add_node("A", "cause")
        assert g.get_node("A").type == NodeType.CAUSE

    def test_remove_node(self):
        g = CausalGraph()
        g.add_node("A")
        g.add_node("B")
        g.add_edge("A", "B")
        assert g.remove_node("A")
        assert "A" not in g
        assert len(g.edges) == 0

    def test_remove_nonexistent_node(self):
        g = CausalGraph()
        assert not g.remove_node("Z")

    def test_add_edge(self, simple_graph):
        assert len(simple_graph.edges) == 3

    def test_add_edge_nonexistent_node(self):
        g = CausalGraph()
        g.add_node("A")
        with pytest.raises(ValueError, match="does not exist"):
            g.add_edge("A", "B")

    def test_add_edge_self_loop(self):
        g = CausalGraph()
        g.add_node("A")
        with pytest.raises(ValueError, match="Self-loop"):
            g.add_edge("A", "A")

    def test_add_edge_cycle(self, simple_graph):
        with pytest.raises(ValueError, match="cycle"):
            simple_graph.add_edge("slip", "rain")

    def test_remove_edge(self, simple_graph):
        assert simple_graph.remove_edge("rain", "wet")
        assert len(simple_graph.edges) == 2
        assert not simple_graph.remove_edge("rain", "wet")

    def test_repr(self, simple_graph):
        r = repr(simple_graph)
        assert "nodes=4" in r
        assert "edges=3" in r


class TestGraphQueries:
    def test_has_path(self, simple_graph):
        assert simple_graph.has_path("rain", "wet")
        assert simple_graph.has_path("rain", "slip")
        assert not simple_graph.has_path("slip", "rain")

    def test_children_parents(self, simple_graph):
        assert simple_graph.children("wet") == {"slip"}
        assert simple_graph.parents("wet") == {"rain", "sprinkler"}

    def test_ancestors_descendants(self, simple_graph):
        assert simple_graph.ancestors("slip") == {"wet", "rain", "sprinkler"}
        assert simple_graph.descendants("rain") == {"wet", "slip"}

    def test_roots_leaves(self, simple_graph):
        assert simple_graph.roots() == {"rain", "sprinkler"}
        assert simple_graph.leaves() == {"slip"}

    def test_find_all_paths(self, simple_graph):
        paths = simple_graph.find_all_paths("rain", "slip")
        assert len(paths) == 1
        assert paths[0] == ["rain", "wet", "slip"]

    def test_find_all_paths_multiple(self):
        g = CausalGraph()
        for n in "ABCD":
            g.add_node(n)
        g.add_edge("A", "B")
        g.add_edge("A", "C")
        g.add_edge("B", "D")
        g.add_edge("C", "D")
        paths = g.find_all_paths("A", "D")
        assert len(paths) == 2


class TestStructuralAnalysis:
    def test_no_cycles(self, simple_graph):
        assert not simple_graph.has_cycles()

    def test_topological_sort(self, simple_graph):
        order = simple_graph.topological_sort()
        assert order.index("rain") < order.index("wet")
        assert order.index("wet") < order.index("slip")

    def test_topological_sort_cycle_raises(self):
        g = CausalGraph()
        g.add_node("A")
        g.add_node("B")
        g.add_edge("A", "B")
        # Force a cycle with unsafe
        g.add_edge_unsafe("B", "A")
        with pytest.raises(ValueError, match="cycle"):
            g.topological_sort()

    def test_find_confounders(self, confounded_graph):
        conf = confounded_graph.find_confounders("X", "Y")
        assert "Z" in conf

    def test_find_mediators(self, mediation_graph):
        meds = mediation_graph.find_mediators("X", "Y")
        assert "M" in meds

    def test_no_confounders_independent(self):
        g = CausalGraph()
        g.add_node("A")
        g.add_node("B")
        g.add_edge("A", "B")
        assert g.find_confounders("A", "B") == set()


class TestSerialization:
    def test_to_json_roundtrip(self, simple_graph):
        j = simple_graph.to_json()
        data = json.loads(j)
        assert len(data["nodes"]) == 4
        assert len(data["edges"]) == 3

    def test_from_json_roundtrip(self, simple_graph):
        j = simple_graph.to_json()
        g2 = CausalGraph.from_json(j)
        assert len(g2) == len(simple_graph)
        assert len(g2.edges) == len(simple_graph.edges)
        assert "rain" in g2
        assert g2.get_node("rain").description == "Rainfall"

    def test_from_dict(self):
        data = {
            "nodes": [{"id": "X", "type": "cause"}, {"id": "Y", "type": "effect"}],
            "edges": [{"source": "X", "target": "Y", "strength": 0.9}],
        }
        g = CausalGraph.from_dict(data)
        assert len(g) == 2
        assert len(g.edges) == 1
        assert g.edges[0].strength == 0.9


class TestSubgraph:
    def test_subgraph(self, simple_graph):
        sub = simple_graph.subgraph({"rain", "wet"})
        assert len(sub) == 2
        assert len(sub.edges) == 1
        assert "sprinkler" not in sub


# ── Inference ────────────────────────────────────────────────────────


class TestCausalInference:
    def test_d_separated_independent(self):
        g = CausalGraph()
        for n in "XYZ":
            g.add_node(n)
        g.add_edge("X", "Z")
        g.add_edge("Y", "Z")
        ci = CausalInference(g)
        # X and Y are d-separated without conditioning on Z
        assert ci.d_separated("X", "Y")

    def test_d_separated_collider(self):
        g = CausalGraph()
        for n in "XYZ":
            g.add_node(n)
        g.add_edge("X", "Z")
        g.add_edge("Y", "Z")
        ci = CausalInference(g)
        # X and Y are NOT d-separated when conditioning on collider Z
        assert not ci.d_separated("X", "Y", {"Z"})

    def test_d_separated_chain(self):
        g = CausalGraph()
        for n in "XYZ":
            g.add_node(n)
        g.add_edge("X", "Y")
        g.add_edge("Y", "Z")
        ci = CausalInference(g)
        # X and Z NOT d-separated
        assert not ci.d_separated("X", "Z")
        # X and Z ARE d-separated when conditioning on Y (chain mediator)
        assert ci.d_separated("X", "Z", {"Y"})

    def test_identify_confounders(self, confounded_graph):
        ci = CausalInference(confounded_graph)
        conf = ci.identify_confounders("X", "Y")
        assert "Z" in conf

    def test_identify_mediators(self, mediation_graph):
        ci = CausalInference(mediation_graph)
        meds = ci.identify_mediators("X", "Y")
        assert "M" in meds

    def test_do_intervention(self, confounded_graph):
        ci = CausalInference(confounded_graph)
        mutilated = ci.do_intervention("X", "Y")
        # Should remove edges into X
        assert len(mutilated.edges) == 2  # X->Y and Z->Y remain
        parents_x = mutilated.parents("X")
        assert len(parents_x) == 0  # Z->X removed

    def test_backdoor_criterion(self, confounded_graph):
        ci = CausalInference(confounded_graph)
        adj = ci.backdoor_criterion("X", "Y")
        assert adj is not None
        assert "Z" in adj

    def test_frontdoor_criterion(self):
        """X → M → Y with unobserved confounder U → X, U → Y."""
        g = CausalGraph()
        g.add_node("X")
        g.add_node("M")
        g.add_node("Y")
        g.add_edge("X", "M")
        g.add_edge("M", "Y")
        ci = CausalInference(g)
        fd = ci.frontdoor_criterion("X", "Y")
        assert fd is not None
        assert "M" in fd


# ── Intervention ─────────────────────────────────────────────────────


class TestInterventionEngine:
    def test_intervene_removes_parents(self, simple_graph):
        engine = InterventionEngine(simple_graph)
        from causal_graph.intervention import Intervention
        intv = Intervention("wet", True)
        mutilated = engine.intervene(intv)
        assert len(mutilated.parents("wet")) == 0
        assert len(mutilated.edges) == 1  # Only wet->slip remains

    def test_affected_variables(self, simple_graph):
        engine = InterventionEngine(simple_graph)
        from causal_graph.intervention import Intervention
        intv = Intervention("rain", True)
        affected = engine.affected_variables(intv)
        assert "wet" in affected
        assert "slip" in affected

    def test_causal_effect_path(self, simple_graph):
        engine = InterventionEngine(simple_graph)
        from causal_graph.intervention import Intervention
        intv = Intervention("rain", True)
        paths = engine.causal_effect_path(intv, "slip")
        assert len(paths) >= 1

    def test_propagate_intervention(self):
        g = CausalGraph()
        g.add_node("X")
        g.add_node("Y")
        g.add_edge("X", "Y", strength=0.8)
        engine = InterventionEngine(g)
        from causal_graph.intervention import Intervention
        intv = Intervention("X", 2.0)
        result = engine.propagate_intervention(intv, {})
        assert result["X"] == 2.0
        assert result["Y"] > 0  # Y should be influenced by X

    def test_average_treatment_effect(self):
        g = CausalGraph()
        g.add_node("X")
        g.add_node("Y")
        g.add_edge("X", "Y", strength=0.5)
        engine = InterventionEngine(g)
        ate = engine.average_treatment_effect("X", "Y", 1.0, 0.0)
        assert ate > 0  # Treatment should have positive effect

    def test_counterfactual(self):
        g = CausalGraph()
        g.add_node("X")
        g.add_node("Y")
        g.add_edge("X", "Y", strength=0.6)
        engine = InterventionEngine(g)
        from causal_graph.intervention import Counterfactual, Intervention
        cf = Counterfactual(
            target="Y",
            intervention=Intervention("X", 5.0),
            evidence={"X": 1.0},
        )
        result = engine.counterfactual(cf)
        assert "Y" in result


# ── Discovery ────────────────────────────────────────────────────────


class TestDiscovery:
    def test_pearson_r_perfect(self):
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [2.0, 4.0, 6.0, 8.0, 10.0]
        r = _pearson_r(x, y)
        assert abs(r - 1.0) < 0.01

    def test_pearson_r_uncorrelated(self):
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [5.0, 1.0, 4.0, 2.0, 3.0]
        r = _pearson_r(x, y)
        assert abs(r) < 0.8

    def test_pc_algorithm(self):
        """Test PC discovery on clearly causal data."""
        import random
        random.seed(42)

        n = 200
        x = [random.gauss(0, 1) for _ in range(n)]
        y = [0.8 * xi + random.gauss(0, 0.3) for xi in x]
        z = [0.6 * yi + random.gauss(0, 0.3) for yi in y]

        data = DataSet()
        data.add_column("X", x)
        data.add_column("Y", y)
        data.add_column("Z", z)

        pc = PCAlgorithm(alpha=0.05)
        graph = pc.discover(data)

        # Should discover at least some edges
        assert len(graph.nodes) == 3
        assert len(graph.edges) >= 1

    def test_discover_from_data(self):
        import random
        random.seed(42)

        n = 100
        a = [random.gauss(0, 1) for _ in range(n)]
        b = [0.5 * ai + random.gauss(0, 0.5) for ai in a]

        data = DataSet()
        data.add_column("A", a)
        data.add_column("B", b)

        g = discover_from_data(data, method="pc")
        assert len(g.nodes) == 2

    def test_score_based_discovery(self):
        import random
        random.seed(42)

        n = 100
        a = [random.gauss(0, 1) for _ in range(n)]
        b = [0.7 * ai + random.gauss(0, 0.2) for ai in a]

        data = DataSet()
        data.add_column("A", a)
        data.add_column("B", b)

        g = discover_from_data(data, method="score")
        assert len(g.nodes) == 2

    def test_empty_data(self):
        data = DataSet()
        g = discover_from_data(data)
        assert len(g) == 0

    def test_invalid_method(self):
        data = DataSet()
        data.add_column("X", [1.0])
        with pytest.raises(ValueError, match="Unknown"):
            discover_from_data(data, method="bogus")


# ── Visualization ────────────────────────────────────────────────────


class TestVisualization:
    def test_render_ascii(self, simple_graph):
        text = render_ascii(simple_graph, title="Test Graph")
        assert "rain" in text
        assert "sprinkler" in text
        assert "Nodes: 4" in text
        assert "Edges: 3" in text

    def test_render_ascii_empty(self):
        g = CausalGraph()
        text = render_ascii(g)
        assert "empty" in text

    def test_render_dot(self, simple_graph):
        dot = render_dot(simple_graph, title="TestCausal")
        assert "digraph" in dot
        assert '"rain"' in dot
        assert "->" in dot

    def test_render_dot_highlight(self, simple_graph):
        dot = render_dot(simple_graph, highlight_nodes={"rain"})
        assert "#ffcc00" in dot  # highlight color

    def test_render_dot_edge_labels(self):
        g = CausalGraph()
        g.add_node("A")
        g.add_node("B")
        g.add_edge("A", "B", strength=0.75, description="causes")
        dot = render_dot(g)
        assert "0.75" in dot
        assert "causes" in dot


# ── Integration ──────────────────────────────────────────────────────


class TestIntegration:
    def test_full_workflow(self):
        """Build a graph, analyze it, visualize, serialize."""
        g = CausalGraph()
        g.add_node("smoking", NodeType.CAUSE, "Smoking habit")
        g.add_node("tar", NodeType.FACTOR, "Lung tar accumulation")
        g.add_node("cancer", NodeType.OUTCOME, "Lung cancer")
        g.add_node("genetics", NodeType.FACTOR, "Genetic predisposition")
        g.add_edge("smoking", "tar", strength=0.9)
        g.add_edge("tar", "cancer", strength=0.7)
        g.add_edge("genetics", "cancer", strength=0.3)

        # Structural analysis
        assert not g.has_cycles()
        order = g.topological_sort()
        assert len(order) == 4

        # Inference
        ci = CausalInference(g)
        conf = ci.identify_confounders("smoking", "cancer")
        meds = ci.identify_mediators("smoking", "cancer")
        assert "tar" in meds

        # Intervention
        engine = InterventionEngine(g)
        from causal_graph.intervention import Intervention
        intv = Intervention("smoking", 0)
        affected = engine.affected_variables(intv)
        assert "tar" in affected
        assert "cancer" in affected

        # Visualization
        ascii_out = render_ascii(g)
        assert "smoking" in ascii_out
        dot_out = render_dot(g)
        assert "digraph" in dot_out

        # Serialization roundtrip
        j = g.to_json()
        g2 = CausalGraph.from_json(j)
        assert len(g2) == 4
        assert len(g2.edges) == 3
