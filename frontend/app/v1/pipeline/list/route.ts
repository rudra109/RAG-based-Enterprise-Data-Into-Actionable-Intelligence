import { NextResponse } from 'next/server';

const MOCK_PIPELINES = [
  { id: 'p1', name: 'Sales Data Sync', status: 'idle', progress: 100, lastRun: '2026-05-13T10:00:00Z', recordsProcessed: 12500, totalRecords: 12500 },
  { id: 'p2', name: 'Log Aggregator', status: 'running', progress: 45, lastRun: '2026-05-13T23:45:00Z', recordsProcessed: 4500, totalRecords: 10000 },
  { id: 'p3', name: 'User Profile Enrichment', status: 'failed', progress: 12, lastRun: '2026-05-13T15:30:00Z', recordsProcessed: 120, totalRecords: 1000 },
  { id: 'p4', name: 'Anomaly Detector', status: 'idle', progress: 100, lastRun: '2026-05-13T12:00:00Z', recordsProcessed: 50000, totalRecords: 50000 },
];

const WORKSPACE_PIPELINES: Record<string, typeof MOCK_PIPELINES> = {
  "Enterprise Workspace": MOCK_PIPELINES,
  "R&D Lab": [
    { id: 'rd-p1', name: 'Experiment Telemetry Sync', status: 'running', progress: 68, lastRun: '2026-05-15T09:30:00Z', recordsProcessed: 6800, totalRecords: 10000 },
    { id: 'rd-p2', name: 'Embedding Batch Builder', status: 'idle', progress: 100, lastRun: '2026-05-15T07:10:00Z', recordsProcessed: 24000, totalRecords: 24000 },
  ],
  "Marketing Cloud": [
    { id: 'mk-p1', name: 'Campaign Attribution Load', status: 'running', progress: 52, lastRun: '2026-05-15T10:00:00Z', recordsProcessed: 52000, totalRecords: 100000 },
    { id: 'mk-p2', name: 'Audience Segment Refresh', status: 'idle', progress: 100, lastRun: '2026-05-15T06:45:00Z', recordsProcessed: 180000, totalRecords: 180000 },
    { id: 'mk-p3', name: 'Conversion Quality Check', status: 'scheduled', progress: 0, lastRun: '2026-05-14T23:00:00Z', recordsProcessed: 0, totalRecords: 75000 },
  ],
};

export async function GET(req: Request) {
  const workspace = new URL(req.url).searchParams.get('workspace') || 'Enterprise Workspace';
  return NextResponse.json(WORKSPACE_PIPELINES[workspace] || []);
}
