"use client";

import { type FormEvent, useState } from "react";
import { 
  Activity, 
  Users, 
  Database, 
  ShieldCheck,
  ArrowUpRight,
  ArrowDownRight,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Cpu,
  MemoryStick,
  Network
} from "lucide-react";
import { useStore } from "@/store/useStore";

const workspaceDashboards = {
  "Enterprise Workspace": {
    subtitle: "Executive overview across all production workspaces.",
    stats: [
      { name: "Active Queries", value: "1,284", change: "+12.5%", trend: "up", icon: Activity },
      { name: "Data Points", value: "4.2M", change: "+3.2%", trend: "up", icon: Database },
      { name: "Anomalies", value: "12", change: "-25%", trend: "down", icon: ShieldCheck },
      { name: "Active Users", value: "854", change: "+1.2%", trend: "up", icon: Users },
    ],
    performance: [
      { label: "00:00", latency: 42, throughput: 58 },
      { label: "02:00", latency: 38, throughput: 62 },
      { label: "04:00", latency: 45, throughput: 55 },
      { label: "06:00", latency: 51, throughput: 69 },
      { label: "08:00", latency: 44, throughput: 76 },
      { label: "10:00", latency: 36, throughput: 81 },
      { label: "12:00", latency: 32, throughput: 78 },
      { label: "14:00", latency: 39, throughput: 84 },
      { label: "16:00", latency: 35, throughput: 88 },
      { label: "18:00", latency: 31, throughput: 91 },
    ],
    anomalies: [
      { metric: "CPU Usage", severity: "critical", time: "Now", value: "95.2%", expected: "45.0%", score: "98%", icon: Cpu },
      { metric: "Memory Latency", severity: "warning", time: "1h ago", value: "120 ms", expected: "30 ms", score: "75%", icon: MemoryStick },
      { metric: "Network Ingress", severity: "critical", time: "2h ago", value: "5,000 rps", expected: "1,200 rps", score: "92%", icon: Network },
    ],
  },
  "R&D Lab": {
    subtitle: "Research workloads, model experiments, and sandbox datasets.",
    stats: [
      { name: "Active Queries", value: "342", change: "+28.4%", trend: "up", icon: Activity },
      { name: "Data Points", value: "860K", change: "+9.1%", trend: "up", icon: Database },
      { name: "Anomalies", value: "4", change: "-12%", trend: "down", icon: ShieldCheck },
      { name: "Active Users", value: "96", change: "+6.8%", trend: "up", icon: Users },
    ],
    performance: [
      { label: "00:00", latency: 55, throughput: 42 },
      { label: "02:00", latency: 49, throughput: 48 },
      { label: "04:00", latency: 58, throughput: 44 },
      { label: "06:00", latency: 47, throughput: 57 },
      { label: "08:00", latency: 39, throughput: 66 },
      { label: "10:00", latency: 44, throughput: 72 },
      { label: "12:00", latency: 36, throughput: 76 },
      { label: "14:00", latency: 41, throughput: 79 },
      { label: "16:00", latency: 37, throughput: 83 },
      { label: "18:00", latency: 34, throughput: 86 },
    ],
    anomalies: [
      { metric: "Embedding Latency", severity: "warning", time: "18m ago", value: "840 ms", expected: "420 ms", score: "71%", icon: Cpu },
      { metric: "Experiment Queue", severity: "warning", time: "52m ago", value: "38 jobs", expected: "14 jobs", score: "69%", icon: MemoryStick },
    ],
  },
  "Marketing Cloud": {
    subtitle: "Campaign analytics, customer segmentation, and attribution data.",
    stats: [
      { name: "Active Queries", value: "618", change: "+7.3%", trend: "up", icon: Activity },
      { name: "Data Points", value: "1.7M", change: "+4.6%", trend: "up", icon: Database },
      { name: "Anomalies", value: "2", change: "-40%", trend: "down", icon: ShieldCheck },
      { name: "Active Users", value: "214", change: "+3.4%", trend: "up", icon: Users },
    ],
    performance: [
      { label: "00:00", latency: 35, throughput: 61 },
      { label: "02:00", latency: 33, throughput: 65 },
      { label: "04:00", latency: 37, throughput: 63 },
      { label: "06:00", latency: 34, throughput: 70 },
      { label: "08:00", latency: 31, throughput: 78 },
      { label: "10:00", latency: 29, throughput: 82 },
      { label: "12:00", latency: 34, throughput: 75 },
      { label: "14:00", latency: 32, throughput: 84 },
      { label: "16:00", latency: 28, throughput: 87 },
      { label: "18:00", latency: 30, throughput: 89 },
    ],
    anomalies: [
      { metric: "Conversion Drop", severity: "critical", time: "27m ago", value: "2.1%", expected: "4.8%", score: "89%", icon: Network },
      { metric: "Attribution Delay", severity: "warning", time: "1h ago", value: "74 min", expected: "20 min", score: "73%", icon: Cpu },
    ],
  },
};

type WorkspaceName = keyof typeof workspaceDashboards;

function createCustomDashboard(workspace: string, dataPoints = 0, activeQueries = 0, activeUsers = 1) {
  const hasData = dataPoints > 0;
  return {
    subtitle: hasData
      ? "Workspace data is connected and ready for analytics."
      : "New workspace ready for dashboards, pipelines, analytics, and anomaly monitoring.",
    stats: [
      { name: "Active Queries", value: activeQueries.toLocaleString(), change: activeQueries > 0 ? "+100%" : "+0%", trend: "up", icon: Activity },
      { name: "Data Points", value: dataPoints.toLocaleString(), change: dataPoints > 0 ? "+100%" : "+0%", trend: "up", icon: Database },
      { name: "Anomalies", value: "0", change: "+0%", trend: "down", icon: ShieldCheck },
      { name: "Active Users", value: activeUsers.toLocaleString(), change: "+100%", trend: "up", icon: Users },
    ],
    performance: [
      { label: "00:00", latency: 0, throughput: 0 },
      { label: "02:00", latency: 0, throughput: 0 },
      { label: "04:00", latency: 0, throughput: 0 },
      { label: "06:00", latency: 0, throughput: 0 },
      { label: "08:00", latency: 0, throughput: 0 },
      { label: "10:00", latency: 0, throughput: 0 },
      { label: "12:00", latency: 0, throughput: 0 },
      { label: "14:00", latency: 0, throughput: 0 },
      { label: "16:00", latency: 0, throughput: 0 },
      { label: "18:00", latency: 0, throughput: 0 },
    ],
    anomalies: [
      hasData
        ? { metric: `${workspace} data baseline`, severity: "info", time: "Now", value: `${dataPoints.toLocaleString()} records`, expected: "validated source", score: "100%", icon: CheckCircle2 }
        : { metric: `${workspace} is ready`, severity: "info", time: "Now", value: "0 issues", expected: "clean baseline", score: "100%", icon: CheckCircle2 },
    ],
  };
}

export default function Home() {
  const { selectedWorkspace, workspaceData, addWorkspaceData, addRagDocuments } = useStore();
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const isCustomWorkspace = !(selectedWorkspace in workspaceDashboards);
  const selectedWorkspaceData = workspaceData[selectedWorkspace];
  const dashboard = workspaceDashboards[(selectedWorkspace as WorkspaceName)] || createCustomDashboard(
    selectedWorkspace,
    selectedWorkspaceData?.dataPoints || 0,
    selectedWorkspaceData?.activeQueries || 0,
    selectedWorkspaceData?.activeUsers || 1,
  );
  const criticalCount = dashboard.anomalies.filter((anomaly) => anomaly.severity === "critical").length;

  const handleAddData = async (event: FormEvent) => {
    event.preventDefault();
    if (!file) return;

    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("corpus_id", selectedWorkspace);

      // Post the file to the backend's ingest endpoint
      const res = await fetch("/v1/rag/ingest", {
        method: "POST",
        body: formData,
      });

      if (res.ok) {
        const ingestData = await res.json();
        const doc_id = ingestData.doc_id;

        addWorkspaceData(selectedWorkspace, {
          name: file.name,
          type: "File Upload",
          records: 1, 
        });
        
        let fileContent = '';
        // Performance Optimization: Only read/sync files smaller than 1MB to the browser's RAG store.
        // Large "Big Ass" CSVs can freeze the UI if stored entirely in memory.
        if (file.size < 1 * 1024 * 1024) {
          try {
            fileContent = await file.text();
          } catch (e) {
            fileContent = 'Could not read file content.';
          }
        } else {
          fileContent = `File too large for browser RAG preview (${(file.size / 1024 / 1024).toFixed(2)} MB). Use the Analytics Agent to query this data mathematically.`;
        }
        
        // Automatically sync the uploaded file to the RAG Chat
        addRagDocuments(selectedWorkspace, [{
          id: doc_id, // Use the real ID from the backend
          workspace: selectedWorkspace,
          corpusId: 'custom-1',
          corpusName: `${selectedWorkspace} Documents`,
          name: file.name,
          type: file.type || 'text/csv',
          size: file.size,
          content: fileContent,
          uploadedAt: new Date().toISOString(),
        }]);

        // Trigger Knowledge Graph Extraction for the new document
        try {
          await fetch("/v1/kg/extract", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              document_ids: [doc_id],
              graph_id: selectedWorkspace,
              doc_texts: { [doc_id]: fileContent }
            })
          });
          console.log("Knowledge Graph extraction triggered for", doc_id);
        } catch (kgErr) {
          console.error("Failed to trigger KG extraction:", kgErr);
        }

        setFile(null);
      } else {
        console.error("Upload failed");
        alert("Upload failed. Ensure backend and ML services are running.");
      }
    } catch (error) {
      console.error(error);
      alert("Error uploading file.");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white">Dashboard Overview</h1>
        <p className="text-slate-400">{selectedWorkspace}: {dashboard.subtitle}</p>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        {dashboard.stats.map((stat) => (
          <div key={stat.name} className="rounded-xl border border-slate-800 bg-slate-900/50 p-6 transition-hover hover:bg-slate-900">
            <div className="flex items-center justify-between">
              <div className="rounded-lg bg-brand-600/10 p-2">
                <stat.icon className="h-6 w-6 text-brand-400" />
              </div>
              <div className={cn(
                "flex items-center gap-0.5 text-sm font-medium",
                stat.trend === "up" ? "text-emerald-500" : "text-rose-500"
              )}>
                {stat.trend === "up" ? <ArrowUpRight className="h-4 w-4" /> : <ArrowDownRight className="h-4 w-4" />}
                {stat.change}
              </div>
            </div>
            <div className="mt-4">
              <h2 className="text-sm font-medium text-slate-400">{stat.name}</h2>
              <p className="text-2xl font-bold text-white">{stat.value}</p>
            </div>
          </div>
        ))}
      </div>

      {isCustomWorkspace && (
        <div className="rounded-xl border border-indigo-500/20 bg-indigo-500/5 p-6">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-xl">
              <h2 className="text-lg font-bold text-white">Add Data to {selectedWorkspace}</h2>
              <p className="mt-1 text-sm text-slate-500">
                Register a data source here. It updates this workspace dashboard, creates a pipeline entry, and gives analytics something to analyze.
              </p>
            </div>
            <form onSubmit={handleAddData} className="grid w-full gap-3 md:grid-cols-[1fr_auto] lg:max-w-xl">
              <input
                type="file"
                accept=".csv,.txt,.json,.pdf,.docx"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                className="rounded-xl border border-slate-800 bg-slate-950 px-4 py-2.5 text-sm text-white outline-none focus:border-indigo-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-indigo-600/20 file:text-indigo-400 hover:file:bg-indigo-600/30 cursor-pointer"
              />
              <button 
                type="submit"
                disabled={!file || isUploading}
                className="rounded-xl bg-indigo-600 px-5 py-3 text-sm font-bold text-white hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isUploading ? "Uploading..." : "Upload File"}
              </button>
            </form>
          </div>
          {selectedWorkspaceData?.sources && selectedWorkspaceData.sources.length > 0 && (
            <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              {selectedWorkspaceData.sources.slice(0, 4).map((source) => (
                <div key={source.id} className="rounded-xl border border-slate-800 bg-slate-950/50 p-4">
                  <div className="text-sm font-semibold text-white">{source.name}</div>
                  <div className="mt-1 text-xs text-slate-500">{source.type} - {source.records.toLocaleString()} records</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="grid gap-6 md:grid-cols-2">
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6">
          <div className="mb-4 flex items-start justify-between gap-4">
            <div>
              <h3 className="text-lg font-medium text-white">System Performance</h3>
              <p className="text-xs text-slate-500">Throughput is rising while query latency remains stable.</p>
            </div>
            <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-3 py-1 text-xs font-semibold text-emerald-400">
              Healthy
            </div>
          </div>

          <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4">
            <PerformanceChart data={dashboard.performance} />
            <div className="mt-4 grid grid-cols-2 gap-3">
              <MetricPill label="Avg Latency" value="36 ms" tone="brand" />
              <MetricPill label="Throughput" value="91%" tone="emerald" />
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6">
          <div className="mb-4 flex items-start justify-between gap-4">
            <div>
              <h3 className="text-lg font-medium text-white">Recent Anomalies</h3>
              <p className="text-xs text-slate-500">Latest detections from the anomaly service.</p>
            </div>
            <div className="rounded-lg border border-rose-500/20 bg-rose-500/10 px-3 py-1 text-xs font-semibold text-rose-400">
              {criticalCount} Critical
            </div>
          </div>

          <div className="space-y-3">
            {dashboard.anomalies.map((anomaly) => (
              <div key={anomaly.metric} className="rounded-lg border border-slate-800 bg-slate-950/40 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-3">
                    <div className={cn(
                      "rounded-lg p-2",
                      anomaly.severity === "critical"
                        ? "bg-rose-500/10 text-rose-400"
                        : anomaly.severity === "warning"
                          ? "bg-amber-500/10 text-amber-400"
                          : "bg-emerald-500/10 text-emerald-400"
                    )}>
                      <anomaly.icon className="h-4 w-4" />
                    </div>
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <h4 className="text-sm font-semibold text-white">{anomaly.metric}</h4>
                        <span className={cn(
                          "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide",
                          anomaly.severity === "critical"
                            ? "border-rose-500/20 bg-rose-500/10 text-rose-400"
                            : anomaly.severity === "warning"
                              ? "border-amber-500/20 bg-amber-500/10 text-amber-400"
                              : "border-emerald-500/20 bg-emerald-500/10 text-emerald-400"
                        )}>
                          <AlertTriangle className="h-3 w-3" />
                          {anomaly.severity}
                        </span>
                      </div>
                      <p className="mt-1 text-xs text-slate-400">
                        Detected {anomaly.value} vs expected {anomaly.expected}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="flex items-center justify-end gap-1 text-[10px] text-slate-500">
                      <Clock className="h-3 w-3" />
                      {anomaly.time}
                    </div>
                    <p className="mt-2 text-xs font-semibold text-slate-300">Score {anomaly.score}</p>
                  </div>
                </div>
              </div>
            ))}

            <div className="flex items-center gap-2 rounded-lg border border-emerald-500/10 bg-emerald-500/5 px-4 py-3 text-xs text-emerald-400">
              <CheckCircle2 className="h-4 w-4" />
              Workspace selection is active. These metrics are scoped to {selectedWorkspace}.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function PerformanceChart({ data }: { data: { label: string; latency: number; throughput: number }[] }) {
  const width = 560;
  const height = 150;
  const padding = 12;

  const toPoints = (key: "latency" | "throughput") =>
    data
      .map((point, index) => {
        const x = padding + (index / (data.length - 1)) * (width - padding * 2);
        const y = height - padding - (point[key] / 100) * (height - padding * 2);
        return `${x},${y}`;
      })
      .join(" ");

  return (
    <div className="h-[190px]">
      <svg viewBox={`0 0 ${width} ${height}`} className="h-full w-full overflow-visible" role="img" aria-label="System latency and throughput trend">
        <defs>
          <linearGradient id="dashboardChartFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#6366f1" stopOpacity="0.18" />
            <stop offset="100%" stopColor="#6366f1" stopOpacity="0" />
          </linearGradient>
        </defs>
        {[25, 50, 75].map((line) => (
          <line
            key={line}
            x1={padding}
            x2={width - padding}
            y1={height - padding - (line / 100) * (height - padding * 2)}
            y2={height - padding - (line / 100) * (height - padding * 2)}
            stroke="#1e293b"
            strokeWidth="1"
          />
        ))}
        <polyline points={`${padding},${height - padding} ${toPoints("throughput")} ${width - padding},${height - padding}`} fill="url(#dashboardChartFill)" stroke="none" />
        <polyline points={toPoints("throughput")} fill="none" stroke="#22c55e" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
        <polyline points={toPoints("latency")} fill="none" stroke="#818cf8" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <div className="mt-2 flex items-center justify-between text-[10px] font-medium text-slate-500">
        <span>{data[0].label}</span>
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-emerald-500" /> Throughput</span>
          <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-brand-400" /> Latency</span>
        </div>
        <span>{data[data.length - 1].label}</span>
      </div>
    </div>
  );
}

function MetricPill({ label, value, tone }: { label: string; value: string; tone: "brand" | "emerald" }) {
  return (
    <div className={cn(
      "rounded-lg border px-3 py-2",
      tone === "brand" ? "border-brand-500/20 bg-brand-500/10" : "border-emerald-500/20 bg-emerald-500/10"
    )}>
      <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      <p className={cn("text-sm font-bold", tone === "brand" ? "text-brand-300" : "text-emerald-400")}>{value}</p>
    </div>
  );
}

function cn(...inputs: any[]) {
  return inputs.filter(Boolean).join(" ");
}
