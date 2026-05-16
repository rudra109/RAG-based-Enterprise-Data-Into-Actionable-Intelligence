import { NextResponse } from 'next/server';
import type { ChartType } from '@/types/agent';

type WorkspaceSource = {
  id?: string;
  name: string;
  records: number;
  addedAt?: string;
};

type WorkspaceStats = {
  dataPoints?: number;
  activeQueries?: number;
  activeUsers?: number;
  sources?: WorkspaceSource[];
} | null;

type AgentRequest = {
  query?: string;
  workspace?: string;
  workspaceStats?: WorkspaceStats;
};

type AgentResponse = {
  sql: string;
  explanation: string;
  chart_suggestion: ChartType;
  data: Record<string, string | number>[];
};

const MONTHS = ['January', 'February', 'March', 'April', 'May'];

function normalize(value: string) {
  return value.toLowerCase().replace(/[^a-z0-9\s]/g, ' ').replace(/\s+/g, ' ').trim();
}

function includesAny(query: string, terms: string[]) {
  return terms.some((term) => query.includes(term));
}

function escapeSql(value: string) {
  return value.replace(/'/g, "''");
}

function getSources(workspaceStats: WorkspaceStats) {
  return Array.isArray(workspaceStats?.sources) ? workspaceStats.sources : [];
}

function getTotalRecords(workspaceStats: WorkspaceStats, sources: WorkspaceSource[]) {
  return workspaceStats?.dataPoints || sources.reduce((sum, source) => sum + source.records, 0);
}

function buildSourceRows(sources: WorkspaceSource[]) {
  return sources.map((source) => ({
    source_name: source.name,
    records: source.records,
  }));
}

function buildPipelineRows(sources: WorkspaceSource[]) {
  if (sources.length === 0) {
    return [
      { pipeline: 'Sales Data Sync', records_processed: 12500, success_rate: 99.1 },
      { pipeline: 'Anomaly Detector', records_processed: 50000, success_rate: 98.6 },
      { pipeline: 'Log Aggregator', records_processed: 4500, success_rate: 94.2 },
      { pipeline: 'User Profile Enrichment', records_processed: 120, success_rate: 71.8 },
    ];
  }

  return sources
    .map((source, index) => ({
      pipeline: `${source.name} Ingestion`,
      records_processed: source.records,
      success_rate: Number(Math.max(82, 99.5 - index * 2.1).toFixed(1)),
    }))
    .sort((a, b) => b.records_processed - a.records_processed)
    .slice(0, 5);
}

function buildErrorRows(sources: WorkspaceSource[]) {
  const baseSources = sources.length > 0
    ? sources
    : [
      { name: 'Sales Data Sync', records: 12500 },
      { name: 'Log Aggregator', records: 10000 },
      { name: 'User Profile Enrichment', records: 1000 },
      { name: 'Anomaly Detector', records: 50000 },
    ];

  return baseSources.map((source, index) => {
    const errorRate = Number((0.4 + (index % 4) * 0.35 + Math.min(source.records / 50000, 1.2)).toFixed(2));
    return {
      source_name: source.name,
      error_rate_percent: errorRate,
      failed_records: Math.max(1, Math.round(source.records * (errorRate / 100))),
    };
  });
}

function buildResourceForecast(totalRecords: number) {
  const baseline = Math.max(20, Math.round(totalRecords / 400));

  return Array.from({ length: 6 }).map((_, index) => ({
    period: `Day ${index * 5 + 5}`,
    cpu_units: baseline + index * 8,
    storage_gb: Number((Math.max(2, totalRecords / 1200) + index * 1.4).toFixed(1)),
  }));
}

function buildGrowthRows(totalRecords: number, activeUsers: number) {
  const baseUsers = Math.max(1, Math.round(activeUsers || totalRecords / 1500 || 1));

  return MONTHS.map((month, index) => ({
    month,
    users: baseUsers + index * Math.max(1, Math.round(baseUsers * 0.16)),
    records: Math.round((totalRecords || 12000) * ((index + 1) / MONTHS.length)),
  }));
}

function buildRevenueRows() {
  return [
    { region: 'North America', total_revenue: 450000 },
    { region: 'EMEA', total_revenue: 320000 },
    { region: 'APAC', total_revenue: 280000 },
    { region: 'LATAM', total_revenue: 150000 },
  ];
}

function buildWorkspaceSourceAnswer(workspace: string, workspaceStats: WorkspaceStats, sources: WorkspaceSource[]): AgentResponse {
  const totalRecords = getTotalRecords(workspaceStats, sources);
  const rows = buildSourceRows(sources).sort((a, b) => Number(b.records) - Number(a.records));
  const largest = rows[0];

  return {
    sql: `SELECT source_name, records
FROM workspace_sources
WHERE workspace = '${escapeSql(workspace)}'
ORDER BY records DESC;`,
    explanation: sources.length > 0
      ? `${workspace} has ${totalRecords.toLocaleString()} records across ${sources.length} connected source(s). The largest source is ${largest.source_name} with ${Number(largest.records).toLocaleString()} records.`
      : `${workspace} does not have connected analytics sources yet. Add data on the dashboard or upload documents before asking source-level questions.`,
    chart_suggestion: 'bar',
    data: rows.length > 0 ? rows : [{ source_name: 'No connected sources', records: 0 }],
  };
}

function buildPipelineAnswer(workspace: string, sources: WorkspaceSource[]): AgentResponse {
  const rows = buildPipelineRows(sources);
  const top = rows[0];

  return {
    sql: `SELECT pipeline, records_processed, success_rate
FROM pipeline_runs
WHERE workspace = '${escapeSql(workspace)}'
ORDER BY records_processed DESC
LIMIT 5;`,
    explanation: `${top.pipeline} is the top performing pipeline by processed records. Use this to compare ingestion volume and success rate across pipeline jobs.`,
    chart_suggestion: 'bar',
    data: rows,
  };
}

function buildErrorAnswer(workspace: string, sources: WorkspaceSource[]): AgentResponse {
  const rows = buildErrorRows(sources);
  const highest = [...rows].sort((a, b) => Number(b.error_rate_percent) - Number(a.error_rate_percent))[0];

  return {
    sql: `SELECT source_name, error_rate_percent, failed_records
FROM pipeline_quality
WHERE workspace = '${escapeSql(workspace)}'
ORDER BY error_rate_percent DESC;`,
    explanation: `${highest.source_name} currently has the highest estimated error rate at ${highest.error_rate_percent}%. Check validation rules and malformed rows for that source first.`,
    chart_suggestion: 'bar',
    data: rows,
  };
}

function buildResourceAnswer(workspace: string, totalRecords: number): AgentResponse {
  const rows = buildResourceForecast(totalRecords);
  const final = rows[rows.length - 1];

  return {
    sql: `SELECT forecast_day, cpu_units, storage_gb
FROM resource_forecast
WHERE workspace = '${escapeSql(workspace)}'
  AND forecast_day <= CURRENT_DATE + INTERVAL '30 days'
ORDER BY forecast_day;`,
    explanation: `Resource usage is projected to rise over the next 30 days. By ${final.period}, estimated demand reaches ${final.cpu_units} CPU units and ${final.storage_gb} GB of storage.`,
    chart_suggestion: 'line',
    data: rows,
  };
}

function buildGrowthAnswer(workspace: string, workspaceStats: WorkspaceStats, totalRecords: number): AgentResponse {
  const rows = buildGrowthRows(totalRecords, workspaceStats?.activeUsers || 0);
  const first = rows[0];
  const last = rows[rows.length - 1];

  return {
    sql: `SELECT month, users, records
FROM workspace_growth
WHERE workspace = '${escapeSql(workspace)}'
  AND month >= 'January'
ORDER BY month;`,
    explanation: `${workspace} growth is trending upward from ${first.users} users in January to ${last.users} users in May. Records also grow as more workspace data is connected.`,
    chart_suggestion: 'line',
    data: rows,
  };
}

function buildRevenueAnswer(): AgentResponse {
  const rows = buildRevenueRows();

  return {
    sql: `SELECT region, SUM(revenue) AS total_revenue
FROM sales_data
WHERE date >= '2026-01-01'
GROUP BY region
ORDER BY total_revenue DESC;`,
    explanation: 'North America is currently leading revenue, followed by EMEA and APAC. This answer is based on the enterprise sales demo dataset.',
    chart_suggestion: 'bar',
    data: rows,
  };
}

function buildMarketingAnswer(): AgentResponse {
  return {
    sql: `SELECT channel, SUM(conversions) AS conversions
FROM marketing_attribution
WHERE date >= '2026-01-01'
GROUP BY channel
ORDER BY conversions DESC;`,
    explanation: 'Paid Search is leading total conversions, while Lifecycle Email remains a strong secondary channel.',
    chart_suggestion: 'bar',
    data: [
      { channel: 'Paid Search', conversions: 18400 },
      { channel: 'Lifecycle Email', conversions: 13200 },
      { channel: 'Partner Campaigns', conversions: 9100 },
      { channel: 'Organic Social', conversions: 7600 },
    ],
  };
}

function buildResearchAnswer(): AgentResponse {
  return {
    sql: `SELECT experiment_type, AVG(latency_ms) AS avg_latency
FROM rd_experiment_metrics
WHERE date >= '2026-01-01'
GROUP BY experiment_type
ORDER BY avg_latency DESC;`,
    explanation: 'Embedding trials have the highest average latency, while retrieval evaluations are trending down after the latest optimization batch.',
    chart_suggestion: 'bar',
    data: [
      { experiment_type: 'Embedding Trials', avg_latency: 840 },
      { experiment_type: 'Retrieval Evals', avg_latency: 520 },
      { experiment_type: 'Fine-tune Jobs', avg_latency: 430 },
    ],
  };
}

function buildUnsupportedAnswer(workspace: string): AgentResponse {
  return {
    sql: `SELECT metric_name, availability
FROM analytics_catalog
WHERE workspace = '${escapeSql(workspace)}';`,
    explanation: `I do not have a reliable dataset for that exact question in ${workspace}. Try asking about records by source, top pipelines, error rates, resource usage, monthly growth, or revenue by region.`,
    chart_suggestion: 'bar',
    data: [
      { metric_name: 'Records by source', availability: 1 },
      { metric_name: 'Pipeline performance', availability: 1 },
      { metric_name: 'Error rates', availability: 1 },
      { metric_name: 'Resource forecast', availability: 1 },
      { metric_name: 'Monthly growth', availability: 1 },
    ],
  };
}

function answerQuery(query: string, workspace: string, workspaceStats: WorkspaceStats): AgentResponse {
  const normalizedQuery = normalize(query);
  const sources = getSources(workspaceStats);
  const totalRecords = getTotalRecords(workspaceStats, sources);

  if (workspace === 'R&D Lab' && includesAny(normalizedQuery, ['latency', 'experiment', 'embedding', 'retrieval', 'research'])) {
    return buildResearchAnswer();
  }

  if (workspace === 'Marketing Cloud' && includesAny(normalizedQuery, ['campaign', 'marketing', 'conversion', 'channel', 'attribution'])) {
    return buildMarketingAnswer();
  }

  if (includesAny(normalizedQuery, ['pipeline', 'performing', 'ingestion', 'top 5', 'top five'])) {
    return buildPipelineAnswer(workspace, sources);
  }

  if (includesAny(normalizedQuery, ['error', 'errors', 'failed', 'failure', 'invalid', 'quality'])) {
    return buildErrorAnswer(workspace, sources);
  }

  if (includesAny(normalizedQuery, ['resource', 'usage', 'forecast', 'predict', 'next 30', 'cpu', 'storage'])) {
    return buildResourceAnswer(workspace, totalRecords);
  }

  if (includesAny(normalizedQuery, ['growth', 'monthly', 'users', 'since january', 'january'])) {
    return buildGrowthAnswer(workspace, workspaceStats, totalRecords);
  }

  if (includesAny(normalizedQuery, ['source', 'sources', 'record', 'records', 'largest', 'data points', 'uploaded', 'connected'])) {
    return buildWorkspaceSourceAnswer(workspace, workspaceStats, sources);
  }

  if (includesAny(normalizedQuery, ['sales', 'revenue', 'region', 'quarter'])) {
    if (workspace !== 'Enterprise Workspace') {
      return {
        sql: `SELECT dataset_name, status
FROM analytics_catalog
WHERE workspace = '${escapeSql(workspace)}'
  AND dataset_name IN ('sales_data', 'regional_revenue');`,
        explanation: `${workspace} does not currently have a connected sales or regional revenue dataset. Add a sales CSV/source first, then I can answer revenue questions for this workspace.`,
        chart_suggestion: 'bar',
        data: [
          { dataset_name: 'sales_data', status: 'not_connected' },
          { dataset_name: 'regional_revenue', status: 'not_connected' },
        ],
      };
    }

    return buildRevenueAnswer();
  }

  if (workspace !== 'Enterprise Workspace' && sources.length > 0) {
    return buildWorkspaceSourceAnswer(workspace, workspaceStats, sources);
  }

  return buildUnsupportedAnswer(workspace);
}

export async function POST(req: Request) {
  const {
    query = '',
    workspace = 'Enterprise Workspace',
    workspaceStats = null,
  } = await req.json() as AgentRequest;

  await new Promise((resolve) => setTimeout(resolve, 300));

  return NextResponse.json(answerQuery(query, workspace, workspaceStats));
}
