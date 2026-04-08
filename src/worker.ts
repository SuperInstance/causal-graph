export interface Env {
  CAUSAL_KV: KVNamespace;
}

interface Node {
  id: string;
  type: 'cause' | 'effect' | 'factor';
  description: string;
  created: number;
  confidence?: number;
}

interface Edge {
  id: string;
  source: string;
  target: string;
  strength: number;
  description: string;
  created: number;
}

const HTML_TEMPLATE = `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="default-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self' https://fonts.gstatic.com;">
    <title>Causal Graph</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', sans-serif;
            background: #0a0a0f;
            color: #e2e8f0;
            line-height: 1.6;
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        header {
            border-bottom: 2px solid #1e293b;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }
        h1 {
            color: #f97316;
            font-weight: 700;
            font-size: 2.5rem;
            margin-bottom: 8px;
        }
        .subtitle {
            color: #94a3b8;
            font-size: 1.1rem;
            font-weight: 400;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 25px;
            margin-bottom: 40px;
        }
        .card {
            background: #15151f;
            border-radius: 12px;
            padding: 25px;
            border-left: 4px solid #f97316;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        }
        h2 {
            color: #f97316;
            margin-bottom: 15px;
            font-size: 1.5rem;
        }
        .endpoint {
            background: #1e1e2d;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 15px;
            border: 1px solid #2d3748;
        }
        .method {
            display: inline-block;
            background: #f97316;
            color: #0a0a0f;
            padding: 4px 12px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 0.9rem;
            margin-right: 10px;
        }
        .path {
            font-family: 'Courier New', monospace;
            color: #63b3ed;
        }
        .desc {
            margin-top: 10px;
            color: #cbd5e1;
            font-size: 0.95rem;
        }
        .example {
            background: #1a1a26;
            padding: 15px;
            border-radius: 8px;
            margin-top: 15px;
            overflow-x: auto;
        }
        code {
            font-family: 'Courier New', monospace;
            color: #68d391;
        }
        footer {
            text-align: center;
            margin-top: 50px;
            padding-top: 20px;
            border-top: 1px solid #1e293b;
            color: #64748b;
            font-size: 0.9rem;
        }
        .fleet {
            color: #f97316;
            font-weight: 600;
        }
        .health {
            display: inline-block;
            width: 12px;
            height: 12px;
            background: #10b981;
            border-radius: 50%;
            margin-right: 8px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Causal Graph</h1>
            <p class="subtitle">Lightweight in‑KV causal reasoning for failure diagnosis</p>
        </header>
        
        <div class="grid">
            <div class="card">
                <h2>What</h2>
                <p>Nodes represent causes, effects, and factors. Edges represent causal relationships with strength weights.</p>
                <div class="example">
                    <strong>Node types:</strong><br>
                    <code>cause</code> – root failure source<br>
                    <code>effect</code> – observed symptom<br>
                    <code>factor</code> – contributing condition
                </div>
            </div>
            
            <div class="card">
                <h2>How</h2>
                <p>Trace causal chains, predict downstream effects, detect conflicting explanations.</p>
                <div class="example">
                    <strong>Operations:</strong><br>
                    • Trace upstream/downstream from any node<br>
                    • Predict failure propagation<br>
                    • Identify conflicting evidence
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>API Endpoints</h2>
            
            <div class="endpoint">
                <span class="method">POST</span><span class="path">/api/node</span>
                <div class="desc">Create or update a causal node</div>
                <div class="example">
                    <code>{"id":"cpu_spike","type":"cause","description":"CPU utilization >95%"}</code>
                </div>
            </div>
            
            <div class="endpoint">
                <span class="method">POST</span><span class="path">/api/edge</span>
                <div class="desc">Create a directed causal edge</div>
                <div class="example">
                    <code>{"source":"cpu_spike","target":"latency_increase","strength":0.8}</code>
                </div>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span><span class="path">/api/trace/:id</span>
                <div class="desc">Trace all causes and effects for a node</div>
                <div class="example">
                    <code>GET /api/trace/cpu_spike</code>
                </div>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span><span class="path">/health</span>
                <div class="desc">Health check endpoint</div>
                <div class="example">
                    <code>{"status":"ok"}</code>
                </div>
            </div>
        </div>
        
        <footer>
            <p><span class="health"></span> System operational • Causal Graph <span class="fleet">Fleet</span> • Orange accent #f97316</p>
        </footer>
    </div>
</body>
</html>
`;

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);
    const path = url.pathname;
    const method = request.method;

    // Set security headers
    const headers = {
      'Content-Type': 'application/json',
      'X-Frame-Options': 'DENY',
      'Access-Control-Allow-Origin': '*',
    };

    // Health endpoint
    if (path === '/health' && method === 'GET') {
      return new Response(JSON.stringify({ status: 'ok' }), { headers });
    }

    // Serve HTML interface at root
    if (path === '/' && method === 'GET') {
      return new Response(HTML_TEMPLATE, {
        headers: { 'Content-Type': 'text/html;charset=UTF-8', 'X-Frame-Options': 'DENY' },
      });
    }

    // API: Create/update node
    if (path === '/api/node' && method === 'POST') {
      try {
        const node = (await request.json()) as Node;
        if (!node.id || !node.type || !node.description) {
          return new Response(JSON.stringify({ error: 'Missing required fields' }), {
            status: 400,
            headers,
          });
        }
        node.created = Date.now();
        await env.CAUSAL_KV.put(`node:${node.id}`, JSON.stringify(node));
        return new Response(JSON.stringify({ success: true, node }), { headers });
      } catch (e) {
        return new Response(JSON.stringify({ error: 'Invalid JSON' }), { status: 400, headers });
      }
    }

    // API: Create edge
    if (path === '/api/edge' && method === 'POST') {
      try {
        const edge = (await request.json()) as Edge;
        if (!edge.id || !edge.source || !edge.target || edge.strength == null) {
          return new Response(JSON.stringify({ error: 'Missing required fields' }), {
            status: 400,
            headers,
          });
        }
        edge.created = Date.now();
        await env.CAUSAL_KV.put(`edge:${edge.id}`, JSON.stringify(edge));
        return new Response(JSON.stringify({ success: true, edge }), { headers });
      } catch (e) {
        return new Response(JSON.stringify({ error: 'Invalid JSON' }), { status: 400, headers });
      }
    }

    // API: Trace node
    if (path.startsWith('/api/trace/') && method === 'GET') {
      const nodeId = path.split('/api/trace/')[1];
      if (!nodeId) {
        return new Response(JSON.stringify({ error: 'Missing node ID' }), { status: 400, headers });
      }

      // Get the target node
      const nodeJson = await env.CAUSAL_KV.get(`node:${nodeId}`);
      if (!nodeJson) {
        return new Response(JSON.stringify({ error: 'Node not found' }), { status: 404, headers });
      }

      // Get all edges
      const edges: Edge[] = [];
      const edgeList = await env.CAUSAL_KV.list({ prefix: 'edge:' });
      for (const key of edgeList.keys) {
        const edgeJson = await env.CAUSAL_KV.get(key.name);
        if (edgeJson) edges.push(JSON.parse(edgeJson));
      }

      // Find upstream (causes) and downstream (effects)
      const upstream: Node[] = [];
      const downstream: Node[] = [];

      // Helper to recursively find causes
      const findCauses = async (currentId: string, visited: Set<string>) => {
        if (visited.has(currentId)) return;
        visited.add(currentId);

        const incomingEdges = edges.filter((e) => e.target === currentId);
        for (const edge of incomingEdges) {
          const nodeJson = await env.CAUSAL_KV.get(`node:${edge.source}`);
          if (nodeJson) {
            const node = JSON.parse(nodeJson);
            upstream.push(node);
            await findCauses(edge.source, visited);
          }
        }
      };

      // Helper to recursively find effects
      const findEffects = async (currentId: string, visited: Set<string>) => {
        if (visited.has(currentId)) return;
        visited.add(currentId);

        const outgoingEdges = edges.filter((e) => e.source === currentId);
        for (const edge of outgoingEdges) {
          const nodeJson = await env.CAUSAL_KV.get(`node:${edge.target}`);
          if (nodeJson) {
            const node = JSON.parse(nodeJson);
            downstream.push(node);
            await findEffects(edge.target, visited);
          }
        }
      };

      await findCauses(nodeId, new Set());
      await findEffects(nodeId, new Set());

      // Detect potential conflicts (multiple causes for same effect)
      const conflicts: string[] = [];
      const effectMap = new Map<string, string[]>();
      for (const edge of edges) {
        if (!effectMap.has(edge.target)) effectMap.set(edge.target, []);
        effectMap.get(edge.target)!.push(edge.source);
      }
      for (const [effect, causes] of effectMap.entries()) {
        if (causes.length > 1) {
          conflicts.push(`Effect "${effect}" has ${causes.length} possible causes: ${causes.join(', ')}`);
        }
      }

      return new Response(
        JSON.stringify({
          node: JSON.parse(nodeJson),
          upstream: [...new Map(upstream.map((n) => [n.id, n])).values()], // Deduplicate
          downstream: [...new Map(downstream.map((n) => [n.id, n])).values()],
          conflicts,
        }),
        { headers }
      );
    }

    // 404 for unknown routes
    return new Response(JSON.stringify({ error: 'Not found' }), { status: 404, headers });
  },
};