"""causal-graph — Causal graph analysis and reasoning in pure Python."""

from causal_graph.graph import CausalGraph, Node, Edge, NodeType
from causal_graph.inference import CausalInference
from causal_graph.discovery import PCAlgorithm, discover_from_data
from causal_graph.intervention import InterventionEngine
from causal_graph.visualization import render_ascii, render_dot

__version__ = "0.2.0"
__all__ = [
    "CausalGraph",
    "Node",
    "Edge",
    "NodeType",
    "CausalInference",
    "PCAlgorithm",
    "discover_from_data",
    "InterventionEngine",
    "render_ascii",
    "render_dot",
]
