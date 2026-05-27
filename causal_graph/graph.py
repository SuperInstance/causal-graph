"""Core causal graph data structure with DAG validation."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple


class NodeType(Enum):
    """Semantic type of a causal node."""

    CAUSE = "cause"
    EFFECT = "effect"
    FACTOR = "factor"
    LATENT = "latent"
    OUTCOME = "outcome"


@dataclass
class Node:
    """A node in the causal graph."""

    id: str
    type: NodeType = NodeType.FACTOR
    description: str = ""
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Node):
            return self.id == other.id
        if isinstance(other, str):
            return self.id == other
        return NotImplemented


@dataclass
class Edge:
    """A directed edge between two nodes."""

    source: str
    target: str
    strength: float = 1.0
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self) -> int:
        return hash((self.source, self.target))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Edge):
            return self.source == other.source and self.target == other.target
        return NotImplemented


class CausalGraph:
    """A directed acyclic graph for causal reasoning.

    Supports typed nodes, weighted directed edges, cycle detection,
    path queries, serialization, and structural analysis.

    Example::

        g = CausalGraph()
        g.add_node("rain", NodeType.CAUSE)
        g.add_node("wet_ground", NodeType.EFFECT)
        g.add_edge("rain", "wet_ground", strength=0.9)
        assert g.has_path("rain", "wet_ground")
    """

    def __init__(self) -> None:
        self._nodes: Dict[str, Node] = {}
        self._edges: List[Edge] = []
        self._adj: Dict[str, Set[str]] = {}  # adjacency: src -> {targets}
        self._rev: Dict[str, Set[str]] = {}  # reverse: target -> {sources}

    # ── Node operations ──────────────────────────────────────────────

    def add_node(
        self,
        node_id: str,
        node_type: NodeType | str = NodeType.FACTOR,
        description: str = "",
        confidence: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Node:
        """Add a node to the graph. Returns the created Node."""
        if isinstance(node_type, str):
            node_type = NodeType(node_type)
        node = Node(
            id=node_id,
            type=node_type,
            description=description,
            confidence=confidence,
            metadata=metadata or {},
        )
        self._nodes[node_id] = node
        if node_id not in self._adj:
            self._adj[node_id] = set()
        if node_id not in self._rev:
            self._rev[node_id] = set()
        return node

    def get_node(self, node_id: str) -> Optional[Node]:
        """Get a node by ID, or None."""
        return self._nodes.get(node_id)

    def remove_node(self, node_id: str) -> bool:
        """Remove a node and all its edges. Returns True if node existed."""
        if node_id not in self._nodes:
            return False
        del self._nodes[node_id]
        # Remove edges involving this node
        self._edges = [
            e for e in self._edges if e.source != node_id and e.target != node_id
        ]
        # Clean adjacency
        for target in list(self._adj.get(node_id, set())):
            self._rev.get(target, set()).discard(node_id)
        self._adj.pop(node_id, None)
        for source in list(self._rev.get(node_id, set())):
            self._adj.get(source, set()).discard(node_id)
        self._rev.pop(node_id, None)
        return True

    @property
    def nodes(self) -> Dict[str, Node]:
        """All nodes keyed by ID."""
        return dict(self._nodes)

    # ── Edge operations ──────────────────────────────────────────────

    def add_edge(
        self,
        source: str,
        target: str,
        strength: float = 1.0,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Edge:
        """Add a directed edge. Raises ValueError if it would create a cycle."""
        if source not in self._nodes:
            raise ValueError(f"Source node '{source}' does not exist")
        if target not in self._nodes:
            raise ValueError(f"Target node '{target}' does not exist")
        if source == target:
            raise ValueError(f"Self-loop on '{source}' is not allowed in a DAG")
        # Cycle check: would adding source->target create a cycle?
        if self.has_path(target, source):
            raise ValueError(
                f"Edge '{source}' -> '{target}' would create a cycle"
            )
        edge = Edge(
            source=source,
            target=target,
            strength=strength,
            description=description,
            metadata=metadata or {},
        )
        self._edges.append(edge)
        self._adj.setdefault(source, set()).add(target)
        self._rev.setdefault(target, set()).add(source)
        return edge

    def add_edge_unsafe(
        self,
        source: str,
        target: str,
        strength: float = 1.0,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Edge:
        """Add edge without cycle check. Useful for loading / non-DAG graphs."""
        if source not in self._nodes:
            self.add_node(source)
        if target not in self._nodes:
            self.add_node(target)
        edge = Edge(
            source=source,
            target=target,
            strength=strength,
            description=description,
            metadata=metadata or {},
        )
        self._edges.append(edge)
        self._adj.setdefault(source, set()).add(target)
        self._rev.setdefault(target, set()).add(source)
        return edge

    def remove_edge(self, source: str, target: str) -> bool:
        """Remove an edge. Returns True if it existed."""
        before = len(self._edges)
        self._edges = [
            e for e in self._edges if not (e.source == source and e.target == target)
        ]
        if len(self._edges) < before:
            self._adj.get(source, set()).discard(target)
            self._rev.get(target, set()).discard(source)
            return True
        return False

    @property
    def edges(self) -> List[Edge]:
        """All edges."""
        return list(self._edges)

    # ── Graph queries ────────────────────────────────────────────────

    def has_path(self, source: str, target: str) -> bool:
        """Check if a directed path exists from source to target (BFS)."""
        if source == target:
            return False  # no self-path in a DAG
        visited: Set[str] = set()
        queue = [source]
        while queue:
            current = queue.pop(0)
            if current == target:
                return True
            if current in visited:
                continue
            visited.add(current)
            for neighbor in self._adj.get(current, set()):
                if neighbor not in visited:
                    queue.append(neighbor)
        return False

    def children(self, node_id: str) -> Set[str]:
        """Direct successors of a node."""
        return set(self._adj.get(node_id, set()))

    def parents(self, node_id: str) -> Set[str]:
        """Direct predecessors of a node."""
        return set(self._rev.get(node_id, set()))

    def ancestors(self, node_id: str) -> Set[str]:
        """All ancestors (transitive parents) of a node."""
        result: Set[str] = set()
        stack = list(self._rev.get(node_id, set()))
        while stack:
            n = stack.pop()
            if n not in result:
                result.add(n)
                stack.extend(self._rev.get(n, set()) - result)
        return result

    def descendants(self, node_id: str) -> Set[str]:
        """All descendants (transitive children) of a node."""
        result: Set[str] = set()
        stack = list(self._adj.get(node_id, set()))
        while stack:
            n = stack.pop()
            if n not in result:
                result.add(n)
                stack.extend(self._adj.get(n, set()) - result)
        return result

    def roots(self) -> Set[str]:
        """Nodes with no parents (root causes)."""
        return {nid for nid in self._nodes if not self._rev.get(nid)}

    def leaves(self) -> Set[str]:
        """Nodes with no children (final effects/outcomes)."""
        return {nid for nid in self._nodes if not self._adj.get(nid)}

    # ── Structural analysis ──────────────────────────────────────────

    def has_cycles(self) -> bool:
        """Check if the graph contains any directed cycle (should be False for DAG)."""
        WHITE, GRAY, BLACK = 0, 1, 2
        color: Dict[str, int] = {nid: WHITE for nid in self._nodes}

        def dfs(node: str) -> bool:
            color[node] = GRAY
            for neighbor in self._adj.get(node, set()):
                if color[neighbor] == GRAY:
                    return True  # back edge → cycle
                if color[neighbor] == WHITE and dfs(neighbor):
                    return True
            color[node] = BLACK
            return False

        for nid in self._nodes:
            if color[nid] == WHITE:
                if dfs(nid):
                    return True
        return False

    def topological_sort(self) -> List[str]:
        """Return nodes in topological order. Raises ValueError if graph has cycles."""
        in_degree: Dict[str, int] = {nid: 0 for nid in self._nodes}
        for edge in self._edges:
            in_degree[edge.target] = in_degree.get(edge.target, 0) + 1

        queue = sorted(nid for nid in self._nodes if in_degree[nid] == 0)
        order: List[str] = []

        while queue:
            node = queue.pop(0)
            order.append(node)
            for child in sorted(self._adj.get(node, set())):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)

        if len(order) != len(self._nodes):
            raise ValueError("Graph contains a cycle; topological sort impossible")
        return order

    def find_confounders(self, cause: str, effect: str) -> Set[str]:
        """Find common ancestors of cause and effect (potential confounders)."""
        cause_ancestors = self.ancestors(cause)
        effect_ancestors = self.ancestors(effect)
        return cause_ancestors & effect_ancestors

    def find_mediators(self, cause: str, effect: str) -> Set[str]:
        """Find nodes on any directed path from cause to effect."""
        cause_desc = self.descendants(cause)
        effect_anc = self.ancestors(effect)
        mediators = (cause_desc & effect_anc) - {cause, effect}
        return mediators

    def find_all_paths(self, source: str, target: str) -> List[List[str]]:
        """Find all directed paths from source to target."""
        paths: List[List[str]] = []

        def dfs(current: str, path: List[str]) -> None:
            if current == target:
                paths.append(path[:])
                return
            for neighbor in self._adj.get(current, set()):
                if neighbor not in path:
                    path.append(neighbor)
                    dfs(neighbor, path)
                    path.pop()

        dfs(source, [source])
        return paths

    # ── Subgraph / copy ──────────────────────────────────────────────

    def subgraph(self, node_ids: Set[str]) -> "CausalGraph":
        """Return a subgraph containing only the specified nodes and their edges."""
        g = CausalGraph()
        for nid in node_ids:
            node = self._nodes.get(nid)
            if node:
                g._nodes[nid] = Node(
                    id=node.id,
                    type=node.type,
                    description=node.description,
                    confidence=node.confidence,
                    metadata=dict(node.metadata),
                )
                g._adj[nid] = set()
                g._rev[nid] = set()
        for edge in self._edges:
            if edge.source in node_ids and edge.target in node_ids:
                e = Edge(
                    source=edge.source,
                    target=edge.target,
                    strength=edge.strength,
                    description=edge.description,
                    metadata=dict(edge.metadata),
                )
                g._edges.append(e)
                g._adj[edge.source].add(edge.target)
                g._rev[edge.target].add(edge.source)
        return g

    # ── Serialization ────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """Serialize graph to a dictionary."""
        return {
            "nodes": [
                {
                    "id": n.id,
                    "type": n.type.value,
                    "description": n.description,
                    "confidence": n.confidence,
                    "metadata": n.metadata,
                }
                for n in self._nodes.values()
            ],
            "edges": [
                {
                    "source": e.source,
                    "target": e.target,
                    "strength": e.strength,
                    "description": e.description,
                    "metadata": e.metadata,
                }
                for e in self._edges
            ],
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize graph to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CausalGraph":
        """Deserialize graph from a dictionary."""
        g = cls()
        for nd in data.get("nodes", []):
            g.add_node(
                node_id=nd["id"],
                node_type=NodeType(nd.get("type", "factor")),
                description=nd.get("description", ""),
                confidence=nd.get("confidence", 1.0),
                metadata=nd.get("metadata"),
            )
        for ed in data.get("edges", []):
            g.add_edge_unsafe(
                source=ed["source"],
                target=ed["target"],
                strength=ed.get("strength", 1.0),
                description=ed.get("description", ""),
                metadata=ed.get("metadata"),
            )
        return g

    @classmethod
    def from_json(cls, json_str: str) -> "CausalGraph":
        """Deserialize graph from JSON string."""
        return cls.from_dict(json.loads(json_str))

    # ── Builtins ─────────────────────────────────────────────────────

    def __len__(self) -> int:
        return len(self._nodes)

    def __contains__(self, node_id: str) -> bool:
        return node_id in self._nodes

    def __iter__(self) -> Iterator[str]:
        return iter(self._nodes)

    def __repr__(self) -> str:
        return f"CausalGraph(nodes={len(self._nodes)}, edges={len(self._edges)})"
