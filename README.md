# causal-graph

**Causal graph analysis and reasoning in pure Python** — build DAGs, discover structure, compute interventions, and visualize. Zero external dependencies.

## What This Gives You

- **Causal DAGs** — typed nodes (cause, effect, factor, latent, outcome) with weighted edges
- **Causal discovery** — PC algorithm and score-based structure learning from data
- **Causal inference** — d-separation, backdoor/frontdoor criteria, do-operator
- **Interventions & counterfactuals** — propagate interventions, compute ATE
- **Visualization** — ASCII art and Graphviz DOT output
- **Serialization** — JSON round-trip

## Installation

```bash
pip install causal-graph
```

## Quick Start

```python
from causal_graph import CausalGraph, NodeType

g = CausalGraph()
g.add_node("smoking", NodeType.CAUSE, "Smoking habit")
g.add_node("tar", NodeType.FACTOR, "Lung tar")
g.add_node("cancer", NodeType.OUTCOME, "Lung cancer")

g.add_edge("smoking", "tar", strength=0.9)
g.add_edge("tar", "cancer", strength=0.7)

# d-separation
print(g.d_separated("smoking", "cancer", given=["tar"]))  # True

# Intervention (do-calculus)
mutilated = g.do_intervention("smoking", value=0)
```

## Testing

```bash
pip install -e ".[dev]"
pytest
```

## How It Fits

Causal reasoning engine for the SuperInstance fleet. Agents use it for root-cause analysis, anomaly explanation, and decision support.

## License

MIT
