# causal-graph

A Cloudflare Worker that provides lightweight causal reasoning over Cloudflare KV. Nodes represent causes, effects, and contributing factors; directed edges represent causal relationships with strength weights. Used for failure diagnosis and propagation analysis across the Cocapn fleet.

## What It Does

- Stores causal **nodes** (cause, effect, or factor) with descriptions and confidence scores
- Stores directed **edges** between nodes with strength weights
- Traces causal chains upstream and downstream from any node
- Detects conflicting explanations in the graph
- Persists everything in Cloudflare KV

## API

### Create a node

```bash
curl -X POST https://causal-graph.example.com/api/node \
  -H "Content-Type: application/json" \
  -d '{"id":"cpu_spike","type":"cause","description":"CPU utilization >95%","confidence":0.9}'
```

### Create an edge

```bash
curl -X POST https://causal-graph.example.com/api/edge \
  -H "Content-Type: application/json" \
  -d '{"source":"cpu_spike","target":"latency_increase","strength":0.8,"description":"High CPU causes request queuing"}'
```

### Trace a node

```bash
curl https://causal-graph.example.com/api/trace/cpu_spike
```

### Health check

```bash
curl https://causal-graph.example.com/health
```

## Deploy

Requires a KV namespace bound as `CAUSAL_KV` in `wrangler.toml`.

```bash
npx wrangler deploy
```

## License

MIT

---

Part of the [Cocapn fleet](https://github.com/Lucineer/the-fleet). Built with [Cocapn](https://github.com/Lucineer/cocapn-ai).
