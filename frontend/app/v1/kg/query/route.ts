import { NextResponse } from 'next/server';

export async function POST() {
  // Return the same subgraph for simplicity in mock
  return NextResponse.json({
    nodes: [
      { id: 'n1', label: 'EnterpriseIQ', type: 'PRODUCT', properties: { version: '2.0' } },
      { id: 'n5', label: 'Nexus AI', type: 'PRODUCT', properties: { relationship: 'Competitor' } },
    ],
    edges: [
      { id: 'e4', source: 'n1', target: 'n5', label: 'COMPARED_TO' },
    ]
  });
}
