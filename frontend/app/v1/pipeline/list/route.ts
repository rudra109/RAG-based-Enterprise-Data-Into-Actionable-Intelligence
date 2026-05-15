import { NextResponse } from 'next/server';

const MOCK_PIPELINES = [
  { id: 'p1', name: 'Sales Data Sync', status: 'idle', progress: 100, lastRun: '2026-05-13T10:00:00Z', recordsProcessed: 12500, totalRecords: 12500 },
  { id: 'p2', name: 'Log Aggregator', status: 'running', progress: 45, lastRun: '2026-05-13T23:45:00Z', recordsProcessed: 4500, totalRecords: 10000 },
  { id: 'p3', name: 'User Profile Enrichment', status: 'failed', progress: 12, lastRun: '2026-05-13T15:30:00Z', recordsProcessed: 120, totalRecords: 1000 },
  { id: 'p4', name: 'Anomaly Detector', status: 'idle', progress: 100, lastRun: '2026-05-13T12:00:00Z', recordsProcessed: 50000, totalRecords: 50000 },
];

export async function GET() {
  return NextResponse.json(MOCK_PIPELINES);
}
