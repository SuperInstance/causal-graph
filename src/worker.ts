interface Env {
    CAUSAL_KV: KVNamespace;
}

interface Node {
    id: string;
    type: 'event' | 'action' | 'state';
    description: string;
    timestamp: number;
    metadata?: Record<string, any>;
}

interface Edge {
    id: string;
    source: string;
    target: string;
    strength: number;
    description: string;
    timestamp: number;
}

const html = `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Causal Graph</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Inter', sans-serif;
            background: #0a0a0f;
            color: #e4e4e7;
            line-height: 1.6;
            min-height: 100vh;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
        }
        .hero {
            text-align: center;
            padding: 80px 20px;
            background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 100%);
            border-bottom: 1px solid #222233;
        }
        .hero h1 {
            font-size: 3.5rem;
            font-weight: 700;
            background: linear-gradient(90deg, #f97316, #fb923c);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            margin-bottom: 20px;
        }
        .hero p {
            font-size: 1.2rem;
            color: #a1a1aa;
            max-width: 600px;
            margin: 0 auto 40px;
        }
        .questions {
            display: flex;
            justify-content: center;
            gap: 30px;
            flex-wrap: wrap;
            margin-top: 40px;
        }
        .question-card {
            background: #161622;
            border: 1px solid #27272a;
            border-radius: 12px;
            padding: 25px;
            width: 280px;
            transition: transform 0.3s, border-color 0.3s;
        }
        .question-card:hover {
            transform: translateY(-5px);
            border-color: #f97316;
        }
        .question-card h3 {
            color: #f97316;
            margin-bottom: 10px;
            font-size: 1.3rem;
        }
        .question-card p {
            color: #d4d4d8;
            font-size: 0.95rem;
        }
        section {
            padding: 80px 20px;
            border-bottom: 1px solid #222233;
        }
        section:nth-child(even) {
            background: #11111a;
        }
        h2 {
            font-size: 2.5rem;
            color: #f97316;
            margin-bottom: 40px;
            text-align: center;
        }
        .content-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 30px;
            margin-top: 40px;
        }
        .card {
            background: #161622;
            border: 1px solid #27272a;
            border-radius: 12px;
            padding: 30px;
        }
        .card h3 {
            color: #f97316;
            margin-bottom: 15px;
            font-size: 1.5rem;
        }
        .card ul {
            list-style: none;
            padding-left: 0;
        }
        .card li {
            padding: 8px 0;
            color: #d4d4d8;
            border-bottom: 1px solid #27272a;
        }
        .card li:last-child {
            border-bottom: none;
        }
        .api-endpoint {
            background: #1a1a2e;
            border-left: 4px solid #f97316;
            padding: 15px;
            margin: 15px 0;
            border-radius: 0 8px 8px 0;
        }
        .method {
            display: inline-block;
            padding: 4px 12px;
            background: #f97316;
            color: white;
            border-radius: 4px;
            font-weight: 600;
            margin-right: 10px;
        }
        .endpoint {
            font-family: monospace;
            color: #a5b4fc;
        }
        footer {
            text-align: center;
            padding: 40px 20px;
            color: #888;
            font-size: 0.9rem;
        }
        footer a {
            color: #f97316;
            text-decoration: none;
        }
        footer a:hover {
            text-decoration: underline;
        }
        @media (max-width: 768px) {
            .hero h1 {
                font-size: 2.5rem;
            }
            .questions {
                flex-direction: column;
                align-items: center;
            }
            .question-card {
                width: 100%;
                max-width: 400px;
            }
        }
    </style>
</head>
<body>
    <div class="hero">
        <div class="container">
            <h1>Causal Graph</h1>
            <p>Lightweight in-KV causal reasoning for failure diagnosis. Trace root causes, predict failures, and resolve conflicts in distributed systems.</p>
            <div class="questions">
                <div class="question-card">
                    <h3>Why did it fail?</h3>
                    <p>Trace backwards through causal relationships to identify root causes of failures and anomalies.</p>
                </div>
                <div class="question-card">
                    <h3>What breaks next?</h3>
                    <p>Predict forward through the causal graph to anticipate downstream impacts and potential failures.</p>
                </div>
                <div class="question-card">
                    <h3>How to fix it?</h3>
                    <p>Detect conflicts and identify optimal remediation paths through causal analysis.</p>
                </div>
            </div>
        </div>
    </div>

    <section>
        <div class="container">
            <h2>What is a Causal Graph?</h2>
            <div class="content-grid">
                <div class="card">
                    <h3>Nodes</h3>
                    <p>Represent events, actions, or states in your system:</p>
                    <ul>
                        <li><strong>Events:</strong> Timestamped occurrences (e.g., "API call failed")</li>
                        <li><strong>Actions:</strong> Operations performed (e.g., "deploy v1.2.3")</li>
                        <li><strong>States:</strong> System conditions (e.g., "database overloaded")</li>
                    </ul>
                </div>
                <div class="card">
                    <h3>Edges</h3>
                    <p>Represent causal relationships between nodes:</p>
                    <ul>
                        <li><strong>Direction:</strong> Source → Target (cause → effect)</li>
                        <li><strong>Strength:</strong> Confidence score (0.0 to 1.0)</li>
                        <li><strong>Description:</strong> Nature of relationship</li>
                        <li><strong>Temporal:</strong> Timestamped for versioning</li>
                    </ul>
                </div>
            </div>
        </div>
    </section>

    <section>
        <div class="container">
            <h2>How It Works</h2>
            <div class="content-grid">
                <div class="card">
                    <h3>Trace Backwards</h3>
                    <p>Given a failure node, recursively follow incoming edges to discover all contributing causes. Build a complete causal chain to identify root causes.</p>
                </div>
                <div class="card">
                    <h3>Predict Forwards</h3>
                    <p>From any node, follow outgoing edges to predict potential downstream effects. Calculate impact scores based on edge strengths.</p>
                </div>
                <div class="card">
                    <h3>Detect Conflicts</h3>
                    <p>Identify contradictory causal relationships and circular dependencies. Flag inconsistencies for manual review.</p>
                </div>
            </div>
        </div>
    </section>

    <section>
        <div class="container">
            <h2>API Reference</h2>
            <div class="card">
                <div class="api-endpoint">
                    <span class="method">POST</span>
                    <span class="endpoint">/api/node</span>
                    <p>Create or update a node in the causal graph.</p>
                </div>
                <div class="api-endpoint">
                    <span class="method">POST</span>
                    <span class="endpoint">/api/edge</span>
                    <p>Create or update a causal relationship between nodes.</p>
                </div>
                <div class="api-endpoint">
                    <span class="method">GET</span>
                    <span class="endpoint">/api/trace/:id</span>
                    <p>Trace backwards from a node to find root causes.</p>
                </div>
                <div class="api-endpoint">
                    <span class="method">GET</span>
                    <span class="endpoint">/api/predict/:id</span>
                    <p>Predict forward from a node to find potential effects.</p>
                </div>
                <div class="api-endpoint">
                    <span class="method">GET</span>
                    <span class="endpoint">/health</span>
                    <p>Health check endpoint.</p>
                </div>
            </div>
        </div>
    </section>

    <footer>
        <div class="container">
            <i style="color:#888">Built with <a href="https://github.com/Lucineer/cocapn-ai" style="color:#f97316">Cocapn</a></i>
        </div>
    </footer>
</body>
</html>
`;

async function handleApiRequest(request: Request, env: Env, path: string): Promise<Response> {
    const url = new URL(request.url);
    
    if (path === '/api/node' && request.method === 'POST') {
        try {
            const node: Node = await request.json();
            if (!node.id || !node.type || !node.description) {
                return new Response(JSON.stringify({ error: 'Missing required fields' }), {
                    status: 400,
                    headers: { 'Content-Type': 'application/json' }
                });
            }
            node.timestamp = node.timestamp || Date.now();
            await env.CAUSAL_KV.put(`node:${node.id}`, JSON.stringify(node));
            return new Response(JSON.stringify({ success: true, node }), {
                headers: { 'Content-Type': 'application/json' }
            });
        } catch (error) {
            return new Response(JSON.stringify({ error: 'Invalid JSON' }), {
                status: 400,
                headers: { 'Content-Type': 'application/json' }
            });
        }
    }
    
    if (path === '/api/edge' && request.method === 'POST') {
        try {
            const edge: Edge = await request.json();
            if (!edge.id || !edge.source || !edge.target || !edge.description) {
                return new Response(JSON.stringify({ error: 'Missing required fields' }), {
                    status: 400,
                    headers: { 'Content-Type': 'application/json' }
                });
            }
            edge.strength = Math.max(0, Math.min(1, edge.strength || 0.5));
            edge.timestamp = edge.timestamp || Date.now();
            await env.CAUSAL_KV.put(`edge:${edge.id}`, JSON.stringify(edge));
            
            // Update node adjacency lists
            const sourceEdges = JSON.parse((await env.CAUSAL_KV.get(`edges:${edge.source}`)) || '[]');
            sourceEdges.push(edge.id);
            await env.CAUSAL_KV.put(`edges:${edge.source}`, JSON.stringify(sourceEdges));
            
            return new Response(JSON.stringify({ success: true, edge }), {
                headers: { 'Content-Type': 'application/json' }
            });
        } catch (error) {
            return new Response(JSON.stringify({ error: 'Invalid JSON' }), {
                status: 400,
                headers: { 'Content-Type': 'application/json' }
            });
        }
    }
    
    if (path.startsWith('/api/trace/')) {
        const nodeId = path.substring('/api/trace/'.length);
        const visited = new Set<string>();
        const causes: Node[] = [];
        
        async function traceBackwards(id: string) {
            if (visited.has(id)) return;
            visited.add(id);
            
            const nodeData = await env.CAUSAL_KV.get(`node:${id}`);
            if (nodeData) {
                const node: Node = JSON.parse(nodeData);
                causes.push(node);
            }
            
            // Find edges where this node is the target
            const edgesList = await env.CAUSAL_KV.list({ prefix: 'edge:' });
            for (const key of edgesList.keys) {
                const edgeData = await env.CAUSAL_KV.get(key.name);
                if (edgeData) {
                    const edge: Edge = JSON.parse(edgeData);
                    if (edge.target === id) {
                        await traceBackwards(edge.source);
                    }
                }
            }
        }
        
        await traceBackwards(nodeId);
        return new Response(JSON.stringify({ nodeId, causes }), {
            headers: { 'Content-Type': 'application/json' }
        });
    }
    
    if (path.startsWith('/api/predict/')) {
        const nodeId = path.substring('/api/predict/'.length);
        const visited = new Set<string>();
        const effects: Node[] = [];
        
        async function predictForwards(id: string) {
            if (visited.has(id)) return;
            visited.add(id);
            
            // Get edges where this node is the source
            const edgesList = await env.CAUSAL_KV.list({ prefix: 'edge:' });
            for (const key of edgesList.keys) {
                const edgeData = await env.CAUSAL_KV.get(key.name);
                if (edgeData) {
                    const edge: Edge = JSON.parse(edgeData);
                    if (edge.source === id) {
                        const targetNodeData = await env.CAUSAL_KV.get(`node:${edge.target}`);
                        if (targetNodeData) {
                            const node: Node = JSON.parse(targetNodeData);
                            effects.push(node);
                            await predictForwards(edge.target);
                        }
                    }
                }
            }
        }
        
        await predictForwards(nodeId);
        return new Response(JSON.stringify({ nodeId, effects }), {
            headers: { 'Content-Type': 'application/json' }
        });
    }
    
    if (path === '/health') {
        return new Response(JSON.stringify({ status: 'ok', timestamp: Date.now() }), {
            headers: { 'Content-Type': 'application/json' }
        });
    }
    
    return new Response(JSON.stringify({ error: 'Not found' }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' }
    });
}

export default {
    async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
        const url = new URL(request.url);
        const path = url.pathname;
        
        // Set security headers
        const securityHeaders = {
            'Content-Security-Policy': "default-src 'self'; style-src 'self' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com;",
            'X-Frame-Options': 'DENY',
            'X-Content-Type-Options': 'nosniff',
            'Referrer-Policy': 'strict-origin-when-cross-origin'
        };
        
        // Handle API routes
        if (path.startsWith('/api/')) {
            const response = await handleApiRequest(request, env, path);
            // Add security headers to API responses
            for (const [key, value] of Object.entries(securityHeaders)) {
                response.headers.set(key, value);
            }
            return response;
        }
        
        // Serve HTML for all other routes
        if (path === '/' || !path.startsWith('/api')) {
            return new Response(html, {
                headers: {
                    'Content-Type': 'text/html;charset=UTF-8',
                    ...securityHeaders
                }
            });
        }
        
        // 404 for everything else
        return new Response('Not found', {
            status: 404,
            headers: securityHeaders
        });
    }
};