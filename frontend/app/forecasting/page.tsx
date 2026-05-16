'use client';

import React, { useMemo, useState } from 'react';
import useSWR from 'swr';
import { 
  TrendingUp, 
  Sparkles, 
  BarChart3, 
  Info,
  Clock,
  LayoutDashboard,
  Target
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import ForecastChart from '@/components/ForecastChart';
import { ForecastResponse } from '@/types/forecast';
import { cn } from '@/lib/utils';
import { useStore } from '@/store/useStore';

const fetcher = (url: string) => fetch(url).then(res => res.json());

export default function ForecastDashboard() {
  const { selectedWorkspace, workspaceData } = useStore();
  const [horizon, setHorizon] = useState('30d');
  const forecastId = selectedWorkspace.toLowerCase().replace(/[^a-z0-9]+/g, '-');
  const selectedWorkspaceData = workspaceData[selectedWorkspace];
  const forecastUrl = useMemo(() => {
    const params = new URLSearchParams({
      horizon,
      workspace: selectedWorkspace,
      dataPoints: String(selectedWorkspaceData?.dataPoints || 0),
      sources: String(selectedWorkspaceData?.sources?.length || 0),
    });

    return `/v1/forecast/${forecastId}?${params.toString()}`;
  }, [forecastId, horizon, selectedWorkspace, selectedWorkspaceData]);
  const { data, error, isLoading } = useSWR<ForecastResponse>(
    forecastUrl,
    fetcher
  );

  const horizons = [
    { label: '7d', value: '7d' },
    { label: '30d', value: '30d' },
    { label: '90d', value: '90d' },
    { label: '180d', value: '180d' },
  ];

  if (error) return (
    <div className="flex flex-col items-center justify-center min-h-screen text-slate-400">
      <Info className="w-12 h-12 mb-4 text-red-500" />
      <p>Failed to load forecast data.</p>
    </div>
  );

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 animate-in fade-in duration-700 bg-[#020617] min-h-screen text-slate-200">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-2xl bg-indigo-600/20 flex items-center justify-center border border-indigo-500/20">
              <TrendingUp className="w-6 h-6 text-indigo-500" />
            </div>
            <h1 className="text-3xl font-bold text-white tracking-tight">Demand Forecasting</h1>
          </div>
          <p className="text-slate-500 max-w-lg">
            Predictive analytics for {selectedWorkspace} resource requirements and market trends.
          </p>
        </div>

        <div className="flex bg-slate-900/50 p-1 rounded-xl border border-slate-800">
          {horizons.map((h) => (
            <button
              key={h.value}
              onClick={() => setHorizon(h.value)}
              aria-pressed={horizon === h.value}
              className={cn(
                "px-4 py-2 rounded-lg text-sm font-bold transition-all",
                horizon === h.value 
                  ? "bg-indigo-600 text-white shadow-lg shadow-indigo-600/20" 
                  : "text-slate-500 hover:text-white hover:bg-slate-800"
              )}
            >
              {h.label}
            </button>
          ))}
        </div>
      </div>

      {/* Accuracy Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <MetricCard 
          label="Mean Absolute Error (MAE)" 
          value={data?.metrics.mae} 
          icon={<Target className="w-4 h-4 text-blue-400" />}
          badge="Precise"
          testId="forecast-mae-value"
        />
        <MetricCard 
          label="Root Mean Square Error (RMSE)" 
          value={data?.metrics.rmse} 
          icon={<BarChart3 className="w-4 h-4 text-purple-400" />}
          badge="Stable"
          testId="forecast-rmse-value"
        />
        <MetricCard 
          label="Mean Absolute % Error (MAPE)" 
          value={data ? `${data.metrics.mape}%` : undefined} 
          icon={<TrendingUp className="w-4 h-4 text-green-400" />}
          badge="High Accuracy"
          testId="forecast-mape-value"
        />
      </div>

      {/* Main Chart Area */}
      <div className="space-y-4 min-w-0">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <LayoutDashboard className="w-5 h-5 text-indigo-500" />
            Forecast Visualization
          </h2>
          <div className="flex items-center gap-4 text-[10px] uppercase font-bold tracking-widest text-slate-500">
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-0.5 bg-blue-500"></div>
              Actual
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-0.5 bg-green-500 border-t border-dashed border-green-500"></div>
              Predicted
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 bg-blue-500/10 border border-blue-500/20 rounded-sm"></div>
              95% Confidence
            </div>
          </div>
        </div>
        
        {isLoading ? (
          <div className="w-full h-[450px] bg-slate-900/50 border border-slate-800 rounded-3xl animate-pulse flex items-center justify-center">
            <Clock className="w-10 h-10 text-slate-800 animate-spin" />
          </div>
        ) : data && (
          <ForecastChart 
            data={data.points} 
            forecastStartDate={data.forecast_start_date} 
            hasData={data.has_data !== false}
          />
        )}
      </div>

      {/* AI Explanation Card */}
      <div className="bg-slate-900/50 border border-slate-800 rounded-3xl p-8 shadow-2xl relative overflow-hidden group">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-indigo-600/20 flex items-center justify-center border border-indigo-500/20 group-hover:scale-110 transition-transform">
            <Sparkles className="w-5 h-5 text-indigo-500" />
          </div>
          <h2 className="text-xl font-bold text-white">Gemini Insights</h2>
        </div>
        
        <div className="relative z-10">
          {isLoading ? (
            <div className="space-y-3">
              <div className="h-4 bg-slate-800 rounded w-3/4 animate-pulse"></div>
              <div className="h-4 bg-slate-800 rounded w-5/6 animate-pulse"></div>
              <div className="h-4 bg-slate-800 rounded w-2/3 animate-pulse"></div>
            </div>
          ) : (
            <p className="text-lg text-slate-300 leading-relaxed max-w-4xl">
              {data?.explanation || "Analyzing forecast patterns and identifying key drivers for the upcoming period..."}
            </p>
          )}
        </div>

        {/* Decorative elements */}
        <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-600/5 blur-3xl rounded-full -translate-y-1/2 translate-x-1/2"></div>
        <div className="absolute bottom-0 left-0 w-32 h-32 bg-blue-600/5 blur-2xl rounded-full translate-y-1/2 -translate-x-1/2"></div>
      </div>
    </div>
  );
}

function MetricCard({ label, value, icon, badge, testId }: any) {
  return (
    <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-5 hover:bg-slate-900 transition-all group">
      <div className="flex justify-between items-start mb-4">
        <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 group-hover:border-indigo-500/30 transition-colors">
          {icon}
        </div>
        <Badge variant="outline" className="bg-slate-950 border-slate-800 text-[10px] uppercase text-slate-500">
          {badge}
        </Badge>
      </div>
      <div>
        <div className="text-[10px] font-bold text-slate-600 uppercase tracking-widest mb-1">{label}</div>
        <div className="text-2xl font-bold text-white tabular-nums" data-testid={testId}>
          {value ?? <div className="h-8 w-20 bg-slate-800 animate-pulse rounded" />}
        </div>
      </div>
    </div>
  );
}
