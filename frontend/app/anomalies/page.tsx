'use client';

import React, { useMemo, useState } from 'react';
import useSWR from 'swr';
import { toast } from 'sonner';
import { Slider } from '@/components/ui/slider';
import { 
  ShieldAlert, 
  AlertTriangle, 
  Activity, 
  TrendingUp,
  Settings,
  Bell,
  RefreshCw
} from 'lucide-react';
import AnomalyChart from '@/components/AnomalyChart';
import AnomalyList from '@/components/AnomalyList';
import { Anomaly, MetricPoint, AnomalySummary } from '@/types/anomaly';
import { cn } from '@/lib/utils';
import { useStore } from '@/store/useStore';

const fetcher = (url: string) => fetch(url).then(res => res.json());
const MOCK_METRIC_START = Date.UTC(2026, 0, 1, 0, 0, 0);
const RANGE_CONFIG: Record<string, { points: number; stepMs: number; label: string }> = {
  '1h': { points: 50, stepMs: 60_000, label: 'last hour' },
  '6h': { points: 60, stepMs: 6 * 60_000, label: 'last 6 hours' },
  '24h': { points: 72, stepMs: 20 * 60_000, label: 'last 24 hours' },
  '7d': { points: 84, stepMs: 2 * 60 * 60_000, label: 'last 7 days' },
};

function createMetricData(workspace: string, range: string, sensitivity: number): MetricPoint[] {
  const config = RANGE_CONFIG[range] || RANGE_CONFIG['1h'];
  const workspaceOffset = workspace === 'R&D Lab' ? 24 : workspace === 'Marketing Cloud' ? 12 : 0;
  const isCustomWorkspace = !['Enterprise Workspace', 'R&D Lab', 'Marketing Cloud'].includes(workspace);
  const threshold = 170 - sensitivity * 0.45;

  return Array.from({ length: config.points }).map((_, i) => {
    const timestamp = new Date(MOCK_METRIC_START + i * config.stepMs).toISOString();
    const spike = i % 17 === 0 || i % 29 === 0 ? 78 : 0;
    const value = 96 + workspaceOffset + ((i * 17) % 45) - (i % 5) * 3 + spike;

    return {
      timestamp,
      value,
      isAnomaly: !isCustomWorkspace && value >= threshold,
      anomalyId: value >= threshold ? `metric-${range}-${i}` : undefined,
    };
  });
}

const mockMetricData: MetricPoint[] = Array.from({ length: 50 }).map((_, i) => {
  const timestamp = new Date(MOCK_METRIC_START + i * 60000).toISOString();
  const isAnomaly = i % 11 === 0;
  return {
    timestamp,
    value: 100 + ((i * 17) % 50) + (isAnomaly ? 80 : 0),
    isAnomaly,
    anomalyId: isAnomaly ? `a-${i}` : undefined
  };
});

export default function AnomalyDashboard() {
  const { selectedWorkspace } = useStore();
  const datasetId = selectedWorkspace.toLowerCase().replace(/[^a-z0-9]+/g, '-');
  const [sensitivity, setSensitivity] = useState([50]); // 0 to 100
  const [timeRange, setTimeRange] = useState('1h');
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [acknowledgedIds, setAcknowledgedIds] = useState<string[]>([]);
  const { data: anomalies, mutate } = useSWR<Anomaly[]>(
    `/v1/anomaly/list?dataset_id=${datasetId}&workspace=${encodeURIComponent(selectedWorkspace)}`,
    fetcher,
    {
    refreshInterval: 30000, // 30 seconds refresh
    }
  );

  const metricData = useMemo(() => {
    if (selectedWorkspace === 'Enterprise Workspace' && timeRange === '1h' && sensitivity[0] === 50) {
      return mockMetricData;
    }

    return createMetricData(selectedWorkspace, timeRange, sensitivity[0]);
  }, [selectedWorkspace, sensitivity, timeRange]);

  const anomaliesWithLocalState = useMemo(() => (
    (anomalies || []).map((anomaly) => ({
      ...anomaly,
      isAcknowledged: anomaly.isAcknowledged || acknowledgedIds.includes(anomaly.id),
    }))
  ), [acknowledgedIds, anomalies]);

  const filteredAnomalies = useMemo(() => {
    if (!anomaliesWithLocalState) return [];
    return anomaliesWithLocalState
      .filter(a => !a.isAcknowledged)
      .filter(a => (a.score * 100) >= sensitivity[0]);
  }, [anomaliesWithLocalState, sensitivity]);

  const summary: AnomalySummary = useMemo(() => {
    if (!anomaliesWithLocalState) return { total: 0, critical: 0, unacknowledged: 0, avgScore: 0 };
    const visible = anomaliesWithLocalState.filter(a => (a.score * 100) >= sensitivity[0]);
    return {
      total: visible.length,
      critical: visible.filter(a => a.severity === 'critical' && !a.isAcknowledged).length,
      unacknowledged: visible.filter(a => !a.isAcknowledged).length,
      avgScore: visible.reduce((acc, curr) => acc + curr.score, 0) / (visible.length || 1),
    };
  }, [anomaliesWithLocalState, sensitivity]);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await mutate();
      toast.success('Anomaly data refreshed');
    } catch {
      toast.error('Failed to refresh anomaly data');
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleAcknowledge = async (id: string) => {
    setAcknowledgedIds((prev) => prev.includes(id) ? prev : [...prev, id]);
    mutate(prev => prev?.map(a => a.id === id ? { ...a, isAcknowledged: true } : a), false);
    
    try {
      const response = await fetch(`/v1/anomaly/${id}/acknowledge`, {
        method: 'PATCH',
      });
      if (!response.ok) throw new Error('Failed to acknowledge');
      toast.success('Anomaly acknowledged');
    } catch (err) {
      console.error('Acknowledge error:', err);
      setAcknowledgedIds((prev) => prev.filter((item) => item !== id));
      mutate();
      toast.error('Failed to acknowledge anomaly');
    }
  };

  return (
    <div className="p-8 max-w-[1600px] mx-auto space-y-8 animate-in fade-in duration-700 bg-[#020617] min-h-screen text-slate-200">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-2xl bg-indigo-600/20 flex items-center justify-center border border-indigo-500/20">
              <Activity className="w-6 h-6 text-indigo-500" />
            </div>
            <h1 className="text-3xl font-bold text-white tracking-tight">Anomaly Detection</h1>
          </div>
          <p className="text-slate-500 max-w-lg">
            Real-time monitoring of {selectedWorkspace} metrics with automated anomaly detection and alerting.
          </p>
        </div>

        <div className="flex items-center gap-4 bg-slate-900/50 p-2 rounded-2xl border border-slate-800">
          <div className="px-4">
            <div className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mb-2 flex items-center gap-2">
              <Settings className="w-3 h-3" />
              Sensitivity: {sensitivity[0]}%
            </div>
            <Slider
              value={sensitivity}
              onValueChange={(val) => {
                const next = Array.isArray(val) ? val : [val];
                setSensitivity(next);
              }}
              max={100}
              step={1}
              className="w-48"
              aria-label="Anomaly sensitivity"
            />
          </div>
          <div className="w-px h-10 bg-slate-800 mx-2" />
          <button 
            onClick={handleRefresh}
            className="p-3 hover:bg-slate-800 rounded-xl transition-colors text-slate-400 hover:text-white"
            aria-label="Refresh anomalies"
            disabled={isRefreshing}
          >
            <RefreshCw className={cn("w-5 h-5", isRefreshing && "animate-spin")} />
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <SummaryCard 
          label="Total Anomalies" 
          value={summary.total} 
          icon={<AlertTriangle className="w-5 h-5 text-indigo-500" />}
          trend={`${RANGE_CONFIG[timeRange]?.label || 'selected range'}`}
        />
        <SummaryCard 
          label="Critical Issues" 
          value={summary.critical} 
          icon={<ShieldAlert className="w-5 h-5 text-red-500" />}
          className="border-red-500/20 bg-red-500/5"
          valueClassName="text-red-500"
        />
        <SummaryCard 
          label="Unacknowledged" 
          value={summary.unacknowledged} 
          icon={<Bell className="w-5 h-5 text-yellow-500" />}
          className="border-yellow-500/20 bg-yellow-500/5"
          valueClassName="text-yellow-500"
        />
        <SummaryCard 
          label="Avg Confidence" 
          value={`${(summary.avgScore * 100).toFixed(1)}%`} 
          icon={<TrendingUp className="w-5 h-5 text-green-500" />}
        />
      </div>

      {/* Main Content Area */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 h-[600px]">
        <div className="lg:col-span-2 space-y-6 flex flex-col min-w-0">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              <Activity className="w-5 h-5 text-indigo-500" />
              Metric Trends
            </h2>
            <div className="flex gap-2">
              {['1h', '6h', '24h', '7d'].map(t => (
                <button key={t} className={cn(
                  "px-3 py-1 rounded-lg text-xs font-bold transition-all",
                  timeRange === t ? "bg-indigo-600 text-white" : "text-slate-500 hover:text-white hover:bg-slate-800"
                )}
                onClick={() => setTimeRange(t)}
                aria-pressed={timeRange === t}
                >{t}</button>
              ))}
            </div>
          </div>
          <div className="flex-1 min-h-0">
            <AnomalyChart data={metricData} />
          </div>
        </div>

        <div className="h-full min-h-0">
          <AnomalyList 
            anomalies={filteredAnomalies} 
            onAcknowledge={handleAcknowledge} 
          />
        </div>
      </div>
    </div>
  );
}

function SummaryCard({ label, value, icon, trend, className, valueClassName }: any) {
  return (
    <div className={cn("bg-slate-900/50 border border-slate-800 rounded-3xl p-6 shadow-xl relative overflow-hidden group", className)}>
      <div className="flex justify-between items-start mb-4">
        <div className="w-10 h-10 rounded-xl bg-slate-950 flex items-center justify-center border border-slate-800 group-hover:border-indigo-500/50 transition-colors">
          {icon}
        </div>
        {trend && (
          <span className="text-[10px] font-bold text-slate-600 uppercase tracking-tighter">
            {trend}
          </span>
        )}
      </div>
      <div>
        <div className="text-sm font-medium text-slate-500 mb-1">{label}</div>
        <div className={cn("text-3xl font-bold text-white tabular-nums", valueClassName)}>{value}</div>
      </div>
      <div className="absolute -right-4 -bottom-4 w-16 h-16 bg-white/5 blur-2xl rounded-full"></div>
    </div>
  );
}
