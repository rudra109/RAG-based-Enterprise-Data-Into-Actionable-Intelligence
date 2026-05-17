import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

// ── Helper Functions ──
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

// ── Statistical Calculation helper ──
function getStats(values: number[]): { mean: number; stdDev: number } {
  const count = values.length;
  if (count === 0) return { mean: 0, stdDev: 0 };
  const mean = values.reduce((sum, v) => sum + v, 0) / count;
  const variance = values.reduce((sum, v) => sum + Math.pow(v - mean, 2), 0) / count;
  const stdDev = Math.sqrt(variance);
  return { mean, stdDev };
}

// ── GET Endpoint ──
export async function GET(req: Request) {
  const workspace = new URL(req.url).searchParams.get('workspace') || 'Enterprise Workspace';
  
  const csvMatch = findLocalCSV(workspace);
  if (!csvMatch) {
    return NextResponse.json([]);
  }

  try {
    const csvContent = fs.readFileSync(csvMatch.filepath, 'utf-8');
    const records = parseCSV(csvContent);
    if (records.length === 0) {
      return NextResponse.json([]);
    }

    const headers = Object.keys(records[0]);

    // Find date/timestamp column
    const dateCol = headers.find(h => h.toLowerCase() === 'timestamp' || h.toLowerCase() === 'date' || h.toLowerCase() === 'time') || headers[0];

    // Find numeric columns
    const numericCols = headers.filter(h => {
      if (h === dateCol) return false;
      const parsed = parseFloat(records[0][h]);
      return !isNaN(parsed) && isFinite(parsed);
    });

    const anomalies: any[] = [];

    // Detect statistical anomalies for each numeric column
    numericCols.forEach(col => {
      const parsedData = records.map((r, idx) => ({
        val: parseFloat(r[col]),
        date: r[dateCol] || new Date().toISOString(),
        idx
      })).filter(d => !isNaN(d.val) && isFinite(d.val));

      const vals = parsedData.map(d => d.val);
      const { mean, stdDev } = getStats(vals);

      if (stdDev === 0) return; // Skip constants

      parsedData.forEach(d => {
        const diff = Math.abs(d.val - mean);
        const zScore = diff / stdDev;

        // Deviances greater than 2.5 standard deviations flag an anomaly
        if (zScore > 2.5) {
          const score = Math.min(0.99, 0.5 + (zScore - 2.5) / 5);
          const severity = zScore > 3.5 ? 'critical' : 'warning';

          anomalies.push({
            id: `anomaly-${col}-${d.idx}`,
            timestamp: new Date(d.date).toISOString(),
            metricName: capitalize(col),
            value: round(d.val, 2),
            expectedValue: round(mean, 2),
            severity,
            score: round(score, 2),
            isAcknowledged: false
          });
        }
      });
    });

    // Sort anomalies: Critical severity first, then highest outlier score, then newest timestamp
    anomalies.sort((a, b) => {
      if (a.severity === 'critical' && b.severity !== 'critical') return -1;
      if (a.severity !== 'critical' && b.severity === 'critical') return 1;
      if (b.score !== a.score) return b.score - a.score;
      return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
    });

    // Return the top 15 anomalies to prevent UI latency and keep loading smooth
    const topAnomalies = anomalies.slice(0, 15);

    return NextResponse.json(topAnomalies);
  } catch (err) {
    console.error('Dynamic anomaly check failed:', err);
    return NextResponse.json([]);
  }
}
