# causal-graph

A pure Python library for **causal graph analysis and reasoning**. Build causal DAGs, discover structure from data, compute interventions, and visualize results — with zero external dependencies beyond pytest.

## Features

- **Causal DAGs** — Typed nodes (`cause`, `effect`, `factor`, `latent`, `outcome`), weighted directed edges, cycle detection
- **Causal discovery** — PC algorithm and score-based structure learning from observational data
- **Causal inference** — d-separation, backdoor/frontdoor criteria, do-operator (mutilated graphs)
- **Interventions & counterfactuals** — Propagate interventions, compute ATE, simplified counterfactual reasoning
- **Visualization** — ASCII art and Graphviz DOT output
- **Serialization** — JSON round-trip (to_json / from_json)
- **Pure Python** — Uses dataclasses and type hints, no numpy/pandas/scipy required

## Install

```bash
pip install causal-graph
```

Or from source:

```bash
git clone https://github.com/SuperInstance/causal-graph.git
cd causal-graph
pip install -e ".[dev]"
```

## Quick Start

### Build a Causal Graph

```python
from causal_graph import CausalGraph, NodeType

g = CausalGraph()
g.add_node("smoking", NodeType.CAUSE, "Smoking habit")
g.add_node("tar", NodeType.FACTOR, "Lung tar accumulation")
g.add_node("cancer", NodeType.OUTCOME, "Lung cancer")
g.add_node("genetics", NodeType.FACTOR, "Genetic predisposition")

g.add_edge("smoking", "tar", strength=0.9)
g.add_edge("tar", "cancer", strength=0.7)
g.add_edge("genetics", "cancer", strength=0.3)

print(g)  # CausalGraph(nodes=4, edges=3)
```

### Structural Analysis

```python
# Topological sort
print(g.topological_sort())  # ['smoking', 'genetics', 'tar', 'cancer']

# Find roots and leaves
print(g.roots())   # {'smoking', 'genetics'}
print(g.leaves())  # {'cancer'}

# Find confounders and mediators
print(g.find_confounders("smoking", "cancer"))  # set()
print(g.find_mediators("smoking", "cancer"))    # {'tar'}

# All paths
print(g.find_all_paths("smoking", "cancer"))
# [['smoking', 'tar', 'cancer']]
```

### Causal Inference

```python
from causal_graph import CausalInference

ci = CausalInference(g)

# d-separation test
print(ci.d_separated("smoking", "genetics"))  # True

# Backdoor criterion — find adjustment set
print(ci.backdoor_criterion("smoking", "cancer"))

# Do-operator: create mutilated graph (remove incoming edges)
mutilated = ci.do_intervention("smoking", "cancer")
```

### Interventions

```python
from causal_graph import InterventionEngine
from causal_graph.intervention import Intervention

engine = InterventionEngine(g)

# What does do(smoking=0) affect?
intv = Intervention("smoking", 0)
print(engine.affected_variables(intv))  # {'tar', 'cancer'}

# Average treatment effect
ate = engine.average_treatment_effect("smoking", "cancer", 1.0, 0.0)
print(f"ATE: {ate:.3f}")

# Counterfactual
from causal_graph.intervention import Counterfactual
cf = Counterfactual(
    target="cancer",
    intervention=Intervention("smoking", 0),
    evidence={"smoking": 1.0, "genetics": 0.5},
)
result = engine.counterfactual(cf)
```

### Causal Discovery from Data

```python
from causal_graph import discover_from_data
from causal_graph.discovery import DataSet

# Create observational data
data = DataSet()
data.add_column("temperature", [20.1, 22.3, 18.5, ...])
data.add_column("ice_cream_sales", [100, 150, 80, ...])
data.add_column("drowning", [2, 5, 1, ...])

# Discover causal structure using PC algorithm
graph = discover_from_data(data, method="pc", alpha=0.05)

# Or score-based method
graph = discover_from_data(data, method="score")
```

### Visualization

```python
from causal_graph import render_ascii, render_dot

# ASCII art
print(render_ascii(g, title="Smoking → Cancer"))

# Graphviz DOT (save to file and render with `dot`)
dot = render_dot(g, title="Causal Model")
with open("causal.dot", "w") as f:
    f.write(dot)
# Then: dot -Tpng causal.dot -o causal.png
```

### Serialization

```python
# To JSON
json_str = g.to_json()
print(json_str)

# From JSON
g2 = CausalGraph.from_json(json_str)
assert len(g2) == len(g)
```

## Architecture

```
causal_graph/
├── __init__.py          # Public API
├── graph.py             # CausalGraph, Node, Edge, NodeType
├── inference.py         # d-separation, backdoor/frontdoor, do-operator
├── discovery.py         # PC algorithm, score-based discovery
├── intervention.py      # Interventions, counterfactuals, ATE
└── visualization.py     # ASCII and Graphviz DOT rendering

tests/
└── test_causal_graph.py # Comprehensive test suite (56 tests)
```

## Also Included

This repo also contains a [Cloudflare Worker](./src/worker.ts) for lightweight causal reasoning over KV, used for failure diagnosis in production systems. See the [Worker README section](#cloudflare-worker) below.

## License

MIT
