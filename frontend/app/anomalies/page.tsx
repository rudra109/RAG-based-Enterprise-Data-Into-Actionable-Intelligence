'use client';

import React, { useState, useEffect, useMemo } from 'react';
import useSWR from 'swr';
import { toast } from 'sonner';
import { Toaster } from '@/components/ui/sonner';
import { Slider } from '@/components/ui/slider';
import { 
  ShieldAlert, 
  AlertTriangle, 
  CheckCircle2, 
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

const fetcher = (url: string) => fetch(url).then(res => res.json());

export default function AnomalyDashboard() {
  const datasetId = 'default-stream'; // Example dataset ID
  const { data: anomalies, mutate } = useSWR<Anomaly[]>(`/v1/anomaly/list?dataset_id=${datasetId}`, fetcher, {
    refreshInterval: 30000, // 30 seconds refresh
  });

  const [sensitivity, setSensitivity] = useState([50]); // 0 to 100
  const [metricData, setMetricData] = useState<MetricPoint[]>([]);

  // WebSocket for notifications
  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const socket = new WebSocket(`${protocol}//${window.location.host}/ws/events`);

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'NEW_ANOMALY') {
        toast.error(`New Anomaly Detected: ${data.anomaly.metricName}`, {
          description: `Score: ${(data.anomaly.score * 100).toFixed(1)}% | ${data.anomaly.severity.toUpperCase()}`,
          icon: <ShieldAlert className="w-4 h-4 text-red-500" />,
        });
        mutate(); // Refresh data
      }
    };

    return () => socket.close();
  }, [mutate]);

  // Mock metric data generation (since the request focuses on UI components)
  useEffect(() => {
    const points: MetricPoint[] = Array.from({ length: 50 }).map((_, i) => {
      const timestamp = new Date(Date.now() - (50 - i) * 60000).toISOString();
      const isAnomaly = Math.random() > 0.9;
      return {
        timestamp,
        value: 100 + Math.random() * 50 + (isAnomaly ? 80 : 0),
        isAnomaly,
        anomalyId: isAnomaly ? `a-${i}` : undefined
      };
    });
    setMetricData(points);
  }, []);

  const filteredAnomalies = useMemo(() => {
    if (!anomalies) return [];
    return anomalies.filter(a => (a.score * 100) >= sensitivity[0]);
  }, [anomalies, sensitivity]);

  const summary: AnomalySummary = useMemo(() => {
    if (!anomalies) return { total: 0, critical: 0, unacknowledged: 0, avgScore: 0 };
    return {
      total: anomalies.length,
      critical: anomalies.filter(a => a.severity === 'critical').length,
      unacknowledged: anomalies.filter(a => !a.isAcknowledged).length,
      avgScore: anomalies.reduce((acc, curr) => acc + curr.score, 0) / (anomalies.length || 1),
    };
  }, [anomalies]);

  const handleAcknowledge = async (id: string) => {
    // Optimistic UI update
    mutate(prev => prev?.map(a => a.id === id ? { ...a, isAcknowledged: true } : a), false);
    
    try {
      const response = await fetch(`/v1/anomaly/${id}/acknowledge`, {
        method: 'PATCH',
      });
      if (!response.ok) throw new Error('Failed to acknowledge');
    } catch (err) {
      console.error('Acknowledge error:', err);
      mutate(); // Revert on error
    }
  };

  return (
    <div className="p-8 max-w-[1600px] mx-auto space-y-8 animate-in fade-in duration-700 bg-[#020617] min-h-screen text-slate-200">
      <Toaster position="top-right" theme="dark" richColors />
      
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
            Real-time monitoring of system metrics with automated anomaly detection and alerting.
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
              onValueChange={(val) => setSensitivity(Array.isArray(val) ? val : [val])}
              max={100}
              step={1}
              className="w-48"
            />
          </div>
          <div className="w-px h-10 bg-slate-800 mx-2" />
          <button 
            onClick={() => mutate()}
            className="p-3 hover:bg-slate-800 rounded-xl transition-colors text-slate-400 hover:text-white"
          >
            <RefreshCw className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <SummaryCard 
          label="Total Anomalies" 
          value={summary.total} 
          icon={<AlertTriangle className="w-5 h-5 text-indigo-500" />}
          trend="+12% vs last hour"
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
                  t === '1h' ? "bg-indigo-600 text-white" : "text-slate-500 hover:text-white hover:bg-slate-800"
                )}>{t}</button>
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
