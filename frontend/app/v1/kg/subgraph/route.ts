import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

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

// ── Simple Helper Functions ──
function capitalize(str: string): string {
  return str.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
}

function round(value: number, places = 1) {
  const factor = 10 ** places;
  return Math.round(value * factor) / factor;
}

// ── Pure TS CSV Parser ──
function parseCSV(content: string): Record<string, string>[] {
  const lines = content.split(/\r?\n/);
  if (lines.length < 2) return [];

  const headers = parseCSVLine(lines[0]);
  const records: Record<string, string>[] = [];

  for (let i = 1; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;
    const values = parseCSVLine(line);
    const record: Record<string, string> = {};
    headers.forEach((header, index) => {
      record[header] = values[index] || '';
    });
    records.push(record);
  }
  return records;
}

function parseCSVLine(line: string): string[] {
  const result: string[] = [];
  let current = '';
  let inQuotes = false;
  
  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    if (char === '"') {
      inQuotes = !inQuotes;
    } else if (char === ',' && !inQuotes) {
      result.push(current.trim());
      current = '';
    } else {
      current += char;
    }
  }
  result.push(current.trim());
  return result;
}

// ── Local CSV Resolver ──
function findLocalCSV(workspaceName: string): { filepath: string; filename: string } | null {
  const parentDir = path.join(process.cwd(), '..');
  if (!fs.existsSync(parentDir)) return null;

  const files = fs.readdirSync(parentDir);
  const csvFiles = files.filter(f => f.endsWith('.csv'));
  if (csvFiles.length === 0) return null;

  // Try to find a match with the workspace name
  const cleanWorkspace = workspaceName.toLowerCase().replace(/[^a-z0-9]/g, '');
  for (const file of csvFiles) {
    const cleanFile = file.toLowerCase().replace(/\.csv$/, '').replace(/[^a-z0-9]/g, '');
    if (cleanWorkspace.includes(cleanFile) || cleanFile.includes(cleanWorkspace)) {
      return { filepath: path.join(parentDir, file), filename: file };
    }
  }

  // Map default workspaces
  if (workspaceName === 'Enterprise Workspace') {
    const target = csvFiles.find(f => f.includes('large_ecommerce_sales') || f.includes('ecommerce'));
    if (target) return { filepath: path.join(parentDir, target), filename: target };
  } else if (workspaceName === 'R&D Lab') {
    const target = csvFiles.find(f => f.includes('large_server_metrics') || f.includes('server') || f.includes('iot'));
    if (target) return { filepath: path.join(parentDir, target), filename: target };
  } else if (workspaceName === 'Marketing Cloud') {
    const target = csvFiles.find(f => f.includes('large_marketing_campaigns') || f.includes('marketing'));
    if (target) return { filepath: path.join(parentDir, target), filename: target };
  }

  return { filepath: path.join(parentDir, csvFiles[0]), filename: csvFiles[0] };
}

// ── Static Fallback Default Graph ──
function getDefaultFallbackGraph(workspace: string): MockKnowledgeGraph {
  return {
    nodes: [
      { id: 'custom-n1', label: workspace, type: 'ORG', properties: { status: 'new workspace', data_sources: 0 } },
      { id: 'custom-n2', label: 'Connect data source', type: 'PRODUCT', properties: { next_step: 'Create pipeline or upload documents' } },
    ],
    edges: [
      { id: 'custom-e1', source: 'custom-n1', target: 'custom-n2', label: 'NEEDS' },
    ],
  };
}

// ── Main Dynamically Extracted Knowledge Graph Generator ──
export async function getDynamicSubgraph(workspace: string): Promise<MockKnowledgeGraph> {
  const csvMatch = findLocalCSV(workspace);
  if (!csvMatch) {
    return getDefaultFallbackGraph(workspace);
  }

  try {
    const csvContent = fs.readFileSync(csvMatch.filepath, 'utf-8');
    const records = parseCSV(csvContent);
    if (records.length === 0) {
      return getDefaultFallbackGraph(workspace);
    }

    const headers = Object.keys(records[0]);
    const numRows = records.length;

    // Detect target timestamp column
    const dateCol = headers.find(h => h.toLowerCase() === 'timestamp' || h.toLowerCase() === 'date' || h.toLowerCase() === 'time') || '';

    // Detect categorical slice key
    const categoryCandidates = ['product_category', 'server_id', 'platform', 'ticker', 'department', 'origin', 'destination', 'sensor_id'];
    const catCol = headers.find(h => categoryCandidates.includes(h.toLowerCase())) || '';

    const nodes: any[] = [];
    const edges: any[] = [];

    // 1. Root Workspace Node
    nodes.push({
      id: 'ws-root',
      label: workspace,
      type: 'ORG',
      properties: {
        'status': 'active',
        'data_source': csvMatch.filename,
        'total_records': numRows,
        'detected_category_key': catCol ? capitalize(catCol) : 'None',
      }
    });

    // 2. Add structural Column nodes
    headers.forEach(h => {
      let type = 'CONCEPT';
      if (h === dateCol) type = 'EVENT';
      if (h === catCol) type = 'PRODUCT';

      nodes.push({
        id: `col-${h}`,
        label: capitalize(h),
        type,
        properties: {
          'field_name': h,
          'type_role': h === dateCol ? 'Date Sequence' : h === catCol ? 'Identity Key' : 'Metric Field',
          'first_sample': records[0][h] || 'N/A'
        }
      });

      edges.push({
        id: `edge-ws-col-${h}`,
        source: 'ws-root',
        target: `col-${h}`,
        label: 'HAS_METRIC'
      });
    });

    // 3. Extract unique category instance nodes and compute genuine metrics directly from data!
    if (catCol) {
      const uniqueVals = Array.from(new Set(records.map(r => r[catCol]).filter(Boolean))).slice(0, 6);

      uniqueVals.forEach((val, idx) => {
        const matchingRows = records.filter(r => r[catCol] === val);
        const count = matchingRows.length;

        const properties: Record<string, string | number> = {
          'instance_value': val,
          'metric_count': count,
        };

        // Specific metric computations based on column names
        if (catCol === 'product_category') {
          const totalRev = matchingRows.reduce((sum, r) => sum + (parseFloat(r['total_revenue']) || 0), 0);
          const avgPrice = matchingRows.reduce((sum, r) => sum + (parseFloat(r['price']) || 0), 0) / count;
          properties['total_revenue'] = `$${round(totalRev, 1).toLocaleString()}`;
          properties['average_item_price'] = `$${round(avgPrice, 2)}`;
        }
        else if (catCol === 'server_id') {
          const avgCpu = matchingRows.reduce((sum, r) => sum + (parseFloat(r['cpu_usage_pct']) || 0), 0) / count;
          const avgMem = matchingRows.reduce((sum, r) => sum + (parseFloat(r['memory_usage_mb']) || 0), 0) / count;
          properties['average_cpu_pct'] = `${round(avgCpu, 1)}%`;
          properties['average_memory_mb'] = `${round(avgMem, 0)} MB`;
        }
        else if (catCol === 'platform') {
          const totalSpend = matchingRows.reduce((sum, r) => sum + (parseFloat(r['ad_spend']) || 0), 0);
          const conversions = matchingRows.reduce((sum, r) => sum + (parseFloat(r['conversions']) || 0), 0);
          properties['total_spend'] = `$${round(totalSpend, 1).toLocaleString()}`;
          properties['total_conversions'] = conversions;
        }
        else if (catCol === 'ticker') {
          const avgClose = matchingRows.reduce((sum, r) => sum + (parseFloat(r['close_price']) || 0), 0) / count;
          const volume = matchingRows.reduce((sum, r) => sum + (parseFloat(r['volume']) || 0), 0);
          properties['avg_close_price'] = `$${round(avgClose, 2)}`;
          properties['total_volume'] = volume.toLocaleString();
        }
        else if (catCol === 'origin' || catCol === 'destination') {
          const delayedCount = matchingRows.filter(r => r['is_delayed'] === '1' || r['is_delayed'] === 'true').length;
          properties['delayed_packages'] = delayedCount;
          properties['delay_rate_pct'] = `${round((delayedCount / count) * 100, 1)}%`;
        }

        let entType = 'CONCEPT';
        if (catCol === 'server_id') entType = 'ORG';
        if (catCol === 'platform') entType = 'ORG';
        if (catCol === 'product_category') entType = 'PRODUCT';
        if (catCol === 'ticker') entType = 'PRODUCT';

        const entNodeId = `ent-${catCol}-${val.replace(/[^a-zA-Z0-9]/g, '')}`;

        nodes.push({
          id: entNodeId,
          label: val,
          type: entType,
          properties
        });

        edges.push({
          id: `edge-col-ent-${catCol}-${idx}`,
          source: `col-${catCol}`,
          target: entNodeId,
          label: 'MONITORS'
        });
      });
    }

    return { nodes, edges };
  } catch (err) {
    console.error('Failed to parse dynamic KG:', err);
    return getDefaultFallbackGraph(workspace);
  }
}

// ── GET Endpoint ──
export async function GET(req: Request) {
  const workspace = new URL(req.url).searchParams.get('graph_id') || 'Enterprise Workspace';
  const graph = await getDynamicSubgraph(workspace);
  return NextResponse.json(graph);
}
