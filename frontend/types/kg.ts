export type EntityType = 'PERSON' | 'ORG' | 'PRODUCT' | 'OTHER';

export interface GraphNode {
  id: string;
  label: string;
  type: EntityType;
  properties: Record<string, any>;
  sourceDocument?: {
    id: string;
    name: string;
    url: string;
  };
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  label: string; // relationship type
}

export interface KGSubgraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}
