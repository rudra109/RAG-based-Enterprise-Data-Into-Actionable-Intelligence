import { NextResponse } from 'next/server';

const MOCK_ANOMALIES = [
  { 
    id: 'a1', 
    timestamp: new Date().toISOString(), 
    metricName: 'CPU Usage', 
    value: 95.2, 
    expectedValue: 45.0, 
    severity: 'critical', 
    score: 0.98, 
    isAcknowledged: false 
  },
  { 
    id: 'a2', 
    timestamp: new Date(Date.now() - 3600000).toISOString(), 
    metricName: 'Memory Latency', 
    value: 120, 
    expectedValue: 30, 
    severity: 'warning', 
    score: 0.75, 
    isAcknowledged: true 
  },
  { 
    id: 'a3', 
    timestamp: new Date(Date.now() - 7200000).toISOString(), 
    metricName: 'Network Ingress', 
    value: 5000, 
    expectedValue: 1200, 
    severity: 'critical', 
    score: 0.92, 
    isAcknowledged: false 
  },
];

const WORKSPACE_ANOMALIES: Record<string, typeof MOCK_ANOMALIES> = {
  "Enterprise Workspace": MOCK_ANOMALIES,
  "R&D Lab": [
    {
      id: 'rd-a1',
      timestamp: new Date(Date.now() - 18 * 60000).toISOString(),
      metricName: 'Embedding Latency',
      value: 840,
      expectedValue: 420,
      severity: 'warning',
      score: 0.71,
      isAcknowledged: false,
    },
    {
      id: 'rd-a2',
      timestamp: new Date(Date.now() - 52 * 60000).toISOString(),
      metricName: 'Experiment Queue',
      value: 38,
      expectedValue: 14,
      severity: 'warning',
      score: 0.69,
      isAcknowledged: false,
    },
  ],
  "Marketing Cloud": [
    {
      id: 'mk-a1',
      timestamp: new Date(Date.now() - 27 * 60000).toISOString(),
      metricName: 'Conversion Drop',
      value: 2.1,
      expectedValue: 4.8,
      severity: 'critical',
      score: 0.89,
      isAcknowledged: false,
    },
    {
      id: 'mk-a2',
      timestamp: new Date(Date.now() - 60 * 60000).toISOString(),
      metricName: 'Attribution Delay',
      value: 74,
      expectedValue: 20,
      severity: 'warning',
      score: 0.73,
      isAcknowledged: false,
    },
  ],
};

export async function GET(req: Request) {
  const workspace = new URL(req.url).searchParams.get('workspace') || 'Enterprise Workspace';
  return NextResponse.json(WORKSPACE_ANOMALIES[workspace] || []);
}
