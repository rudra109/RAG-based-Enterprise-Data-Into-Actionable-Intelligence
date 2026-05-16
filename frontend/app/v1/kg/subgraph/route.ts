import { NextResponse } from 'next/server';

type MockKnowledgeGraph = {
  nodes: Array<{
    id: string;
    label: string;
    type: string;
    properties: Record<string, string | number>;
  }>;
  edges: Array<{
    id: string;
    source: string;
    target: string;
    label: string;
  }>;
};

const MOCK_KG: MockKnowledgeGraph = {
  nodes: [
    { id: 'n1', label: 'EnterpriseIQ', type: 'PRODUCT', properties: { version: '2.0', status: 'active' } },
    { id: 'n2', label: 'Dhruti Shah', type: 'PERSON', properties: { role: 'Admin', department: 'Engineering' } },
    { id: 'n3', label: 'Google DeepMind', type: 'ORG', properties: { sector: 'AI Research', location: 'London' } },
    { id: 'n4', label: 'Next.js 14', type: 'PRODUCT', properties: { framework: 'React', rendering: 'App Router' } },
  ],
  edges: [
    { id: 'e1', source: 'n2', target: 'n1', label: 'MANAGES' },
    { id: 'e2', source: 'n3', target: 'n1', label: 'DEVELOPED_BY' },
    { id: 'e3', source: 'n1', target: 'n4', label: 'BUILT_WITH' },
  ]
};

const WORKSPACE_GRAPHS: Record<string, MockKnowledgeGraph> = {
  "Enterprise Workspace": MOCK_KG,
  "R&D Lab": {
    nodes: [
      { id: 'rd-n1', label: 'R&D Lab', type: 'ORG', properties: { focus: 'Model evaluation', status: 'active' } },
      { id: 'rd-n2', label: 'Embedding Trials', type: 'PRODUCT', properties: { stage: 'experiment', owner: 'Research' } },
      { id: 'rd-n3', label: 'Evaluation Harness', type: 'PRODUCT', properties: { framework: 'Python', cadence: 'daily' } },
    ],
    edges: [
      { id: 'rd-e1', source: 'rd-n1', target: 'rd-n2', label: 'RUNS' },
      { id: 'rd-e2', source: 'rd-n2', target: 'rd-n3', label: 'VALIDATED_BY' },
    ],
  },
  "Marketing Cloud": {
    nodes: [
      { id: 'mk-n1', label: 'Marketing Cloud', type: 'ORG', properties: { focus: 'Campaign analytics', status: 'active' } },
      { id: 'mk-n2', label: 'Paid Search', type: 'PRODUCT', properties: { channel: 'Acquisition', priority: 'high' } },
      { id: 'mk-n3', label: 'Lifecycle Email', type: 'PRODUCT', properties: { channel: 'Retention', priority: 'medium' } },
      { id: 'mk-n4', label: 'Attribution Model', type: 'PRODUCT', properties: { model: 'multi-touch', version: '1.4' } },
    ],
    edges: [
      { id: 'mk-e1', source: 'mk-n1', target: 'mk-n2', label: 'TRACKS' },
      { id: 'mk-e2', source: 'mk-n1', target: 'mk-n3', label: 'TRACKS' },
      { id: 'mk-e3', source: 'mk-n2', target: 'mk-n4', label: 'FEEDS' },
      { id: 'mk-e4', source: 'mk-n3', target: 'mk-n4', label: 'FEEDS' },
    ],
  },
};

export async function GET(req: Request) {
  const workspace = new URL(req.url).searchParams.get('graph_id') || 'Enterprise Workspace';
  return NextResponse.json(WORKSPACE_GRAPHS[workspace] || {
    nodes: [
      { id: 'custom-n1', label: workspace, type: 'ORG', properties: { status: 'new workspace', data_sources: 0 } },
      { id: 'custom-n2', label: 'Connect data source', type: 'PRODUCT', properties: { next_step: 'Create pipeline or upload documents' } },
    ],
    edges: [
      { id: 'custom-e1', source: 'custom-n1', target: 'custom-n2', label: 'NEEDS' },
    ],
  });
}
