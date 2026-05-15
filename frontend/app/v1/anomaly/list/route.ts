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

export async function GET() {
  return NextResponse.json(MOCK_ANOMALIES);
}
