import { NextResponse } from 'next/server';

const MOCK_KG = {
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

export async function GET() {
  return NextResponse.json(MOCK_KG);
}
