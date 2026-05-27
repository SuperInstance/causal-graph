"""Visualization of causal graphs — ASCII art and Graphviz DOT format."""

from __future__ import annotations

from typing import Optional

from causal_graph.graph import CausalGraph


def render_ascii(graph: CausalGraph, title: Optional[str] = None) -> str:
    """Render a causal graph as ASCII art.

    Uses a simple layered layout based on topological sort.
    Nodes are placed in layers, edges drawn with arrows.

    Args:
        graph: The causal graph to render.
        title: Optional title for the diagram.

    Returns:
        ASCII string representation of the graph.

    Example::

        >>> g = CausalGraph()
        >>> g.add_node("X")
        >>> g.add_node("Y")
        >>> g.add_edge("X", "Y")
        >>> print(render_ascii(g))
    """
    lines: list[str] = []

    if title:
        lines.append(f"╔══ {title} ══╗")
        lines.append("")

    if not graph.nodes:
        lines.append("(empty graph)")
        return "\n".join(lines)

    try:
        order = graph.topological_sort()
    except ValueError:
        order = list(graph.nodes.keys())

    # Assign layers (topological depth)
    layer_of: dict[str, int] = {}
    for node in order:
        parents = graph.parents(node)
        if not parents:
            layer_of[node] = 0
        else:
            layer_of[node] = max(layer_of.get(p, 0) for p in parents) + 1

    # Group by layer
    layers: dict[int, list[str]] = {}
    for node in order:
        l = layer_of[node]
        layers.setdefault(l, []).append(node)

    max_layer = max(layers.keys()) if layers else 0

    # Build node info
    node_info: dict[str, str] = {}
    for nid, node in graph.nodes.items():
        label = nid
        if node.description:
            short = node.description[:20] + ("…" if len(node.description) > 20 else "")
            label = f"{nid} ({short})"
        node_info[nid] = label

    # Render layers
    for layer_num in range(max_layer + 1):
        nodes_in_layer = layers.get(layer_num, [])
        if not nodes_in_layer:
            continue

        # Node boxes
        node_strs = [f"[{node_info.get(n, n)}]" for n in nodes_in_layer]
        line = "  ".join(node_strs)
        lines.append(line)

        # Edges to next layer
        if layer_num < max_layer:
            next_nodes = layers.get(layer_num + 1, [])
            for src in nodes_in_layer:
                children = graph.children(src) & set(next_nodes)
                for tgt in sorted(children):
                    edges = [e for e in graph.edges if e.source == src and e.target == tgt]
                    strength = edges[0].strength if edges else 1.0
                    strength_label = f" ({strength:.1f})" if strength != 1.0 else ""
                    lines.append(f"  │")
                    lines.append(f"  ▼{strength_label}")
            if not any(
                graph.children(src) & set(layers.get(layer_num + 1, set()))
                for src in nodes_in_layer
            ):
                lines.append("  │")
                lines.append("  ...")

    # Edges within same layer or spanning multiple layers
    extra_edges: list[str] = []
    for edge in graph.edges:
        src_layer = layer_of.get(edge.source, 0)
        tgt_layer = layer_of.get(edge.target, 0)
        if tgt_layer != src_layer + 1:
            strength_label = f" ({edge.strength:.1f})" if edge.strength != 1.0 else ""
            extra_edges.append(
                f"  {edge.source} ──→ {edge.target}{strength_label}"
            )

    if extra_edges:
        lines.append("")
        lines.append("Cross-layer edges:")
        for e in extra_edges:
            lines.append(e)

    # Statistics
    lines.append("")
    lines.append(f"  Nodes: {len(graph.nodes)}  Edges: {len(graph.edges)}")
    roots = graph.roots()
    leaves = graph.leaves()
    if roots:
        lines.append(f"  Roots: {', '.join(sorted(roots))}")
    if leaves:
        lines.append(f"  Leaves: {', '.join(sorted(leaves))}")

    return "\n".join(lines)


def render_dot(
    graph: CausalGraph,
    title: Optional[str] = None,
    engine: str = "dot",
    highlight_nodes: Optional[set[str]] = None,
) -> str:
    """Render a causal graph as a Graphviz DOT string.

    Args:
        graph: The causal graph to render.
        title: Optional graph title.
        engine: Layout engine hint (dot, neato, fdp, etc.).
        highlight_nodes: Optional set of nodes to highlight.

    Returns:
        DOT format string that can be rendered with Graphviz.

    Example::

        >>> g = CausalGraph()
        >>> g.add_node("X")
        >>> g.add_node("Y")
        >>> g.add_edge("X", "Y")
        >>> dot_str = render_dot(g)
        >>> # Save and render: open("graph.dot", "w").write(dot_str)
    """
    highlight = highlight_nodes or set()
    lines: list[str] = []
    lines.append(f"digraph {title or 'CausalGraph'} {{")
    lines.append(f"  layout={engine};")
    lines.append('  node [shape=box, style="rounded,filled", fillcolor="#f0f0f0", fontname="Helvetica"];')
    lines.append('  edge [fontname="Helvetica", fontsize=10];')
    lines.append("")

    # Nodes
    for nid, node in graph.nodes.items():
        attrs: list[str] = []
        label = nid
        if node.description:
            label = f"{nid}\\n{node.description}"
        attrs.append(f'label="{label}"')

        # Color by type
        type_colors = {
            "cause": "#ff9999",
            "effect": "#99ccff",
            "factor": "#f0f0f0",
            "latent": "#dddddd",
            "outcome": "#99ff99",
        }
        fill = type_colors.get(node.type.value, "#f0f0f0")
        if nid in highlight:
            fill = "#ffcc00"
        attrs.append(f'fillcolor="{fill}"')

        lines.append(f'  "{nid}" [{" ".join(attrs)}];')

    lines.append("")

    # Edges
    for edge in graph.edges:
        attrs: list[str] = []
        if edge.strength != 1.0:
            attrs.append(f'label="{edge.strength:.2f}"')
            # Vary pen width by strength
            attrs.append(f"penwidth={max(0.5, edge.strength * 2):.1f}")
        if edge.description:
            desc = edge.description.replace('"', '\\"')
            if edge.strength == 1.0:
                attrs.append(f'label="{desc}"')
            else:
                # Combine
                attrs[-1] = f'label="{edge.strength:.2f}: {desc}"'
        lines.append(f'  "{edge.source}" -> "{edge.target}" [{" ".join(attrs)}];')

    lines.append("}")
    return "\n".join(lines)
