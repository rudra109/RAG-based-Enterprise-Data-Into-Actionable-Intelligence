import { NextResponse } from 'next/server';
import { getDynamicSubgraph } from '../subgraph/route';

export async function POST(req: Request) {
  try {
    const { query, workspace } = await req.json();
    const cleanQuery = (query || '').toLowerCase().trim();
    
    // 1. Load dynamic subgraph for active workspace
    const subgraph = await getDynamicSubgraph(workspace || 'Enterprise Workspace');
    
    if (!cleanQuery) {
      return NextResponse.json(subgraph);
    }

    // 2. Search nodes matching the query
    const matchedNodes = subgraph.nodes.filter(n => 
      n.label.toLowerCase().includes(cleanQuery) || 
      n.type.toLowerCase().includes(cleanQuery) ||
      Object.entries(n.properties).some(([key, val]) => 
        String(val).toLowerCase().includes(cleanQuery) || 
        key.toLowerCase().includes(cleanQuery)
      )
    );

    if (matchedNodes.length === 0) {
      // Return full subgraph if no matched nodes
      return NextResponse.json(subgraph);
    }

    // 3. Include connections between matched nodes and root workspace node
    const matchedNodeIds = new Set(matchedNodes.map(n => n.id));
    
    // Keep root node for connection hierarchy
    const rootNode = subgraph.nodes.find(n => n.id === 'ws-root');
    if (rootNode && !matchedNodeIds.has('ws-root')) {
      matchedNodes.push(rootNode);
      matchedNodeIds.add('ws-root');
    }

    // Filter edges connecting matched nodes
    const matchedEdges = subgraph.edges.filter(e => 
      matchedNodeIds.has(e.source) && matchedNodeIds.has(e.target)
    );

    return NextResponse.json({
      nodes: matchedNodes,
      edges: matchedEdges
    });
  } catch (err) {
    console.error('KG Query error:', err);
    return NextResponse.json({ nodes: [], edges: [] });
  }
}
