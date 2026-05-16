'use client';

import React from 'react';
import { Badge } from '@/components/ui/badge';
import { Pipeline, PipelineStatus } from '@/types/pipeline';
import { cn } from '@/lib/utils';
import { Play, CheckCircle2, XCircle, Clock } from 'lucide-react';

interface PipelineCardProps {
  pipeline: Pipeline;
  onClick: () => void;
}

const statusConfig: Record<PipelineStatus, { color: string; icon: React.ReactNode; label: string }> = {
  running: { 
    color: 'bg-blue-500/10 text-blue-500 border-blue-500/20', 
    icon: <Play className="w-3 h-3 animate-pulse" />, 
    label: 'Running' 
  },
  success: { 
    color: 'bg-green-500/10 text-green-500 border-green-500/20', 
    icon: <CheckCircle2 className="w-3 h-3" />, 
    label: 'Success' 
  },
  failed: { 
    color: 'bg-red-500/10 text-red-500 border-red-500/20', 
    icon: <XCircle className="w-3 h-3" />, 
    label: 'Failed' 
  },
  scheduled: { 
    color: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20', 
    icon: <Clock className="w-3 h-3" />, 
    label: 'Scheduled' 
  },
  idle: {
    color: 'bg-slate-500/10 text-slate-500 border-slate-500/20',
    icon: <Clock className="w-3 h-3" />,
    label: 'Idle'
  },
};

export default function PipelineCard({ pipeline, onClick }: PipelineCardProps) {
  const config = statusConfig[pipeline.status];
  const radius = 32;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (pipeline.progress / 100) * circumference;

  return (
    <div 
      onClick={onClick}
      className="group bg-slate-900/50 border border-slate-800 rounded-2xl p-6 hover:border-indigo-500/50 hover:bg-slate-900 transition-all cursor-pointer relative overflow-hidden"
    >
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-lg font-semibold text-white group-hover:text-indigo-400 transition-colors">
            {pipeline.name}
          </h3>
          <p className="text-xs text-slate-500 mt-1">ID: {pipeline.id}</p>
        </div>
        <Badge variant="outline" className={cn("px-2 py-0.5 flex items-center gap-1.5 font-medium uppercase tracking-wider text-[10px]", config.color)}>
          {config.icon}
          {config.label}
        </Badge>
      </div>

      <div className="flex items-center gap-6">
        {/* Progress Ring */}
        <div className="relative w-20 h-20 shrink-0">
          <svg className="w-full h-full -rotate-90">
            <circle
              cx="40"
              cy="40"
              r={radius}
              stroke="currentColor"
              strokeWidth="6"
              fill="transparent"
              className="text-slate-800"
            />
            <circle
              cx="40"
              cy="40"
              r={radius}
              stroke="currentColor"
              strokeWidth="6"
              fill="transparent"
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              strokeLinecap="round"
              className={cn(
                "transition-all duration-1000 ease-in-out",
                pipeline.status === 'running' ? "text-blue-500" : 
                pipeline.status === 'success' ? "text-green-500" :
                pipeline.status === 'failed' ? "text-red-500" : "text-yellow-500"
              )}
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-sm font-bold text-white">{Math.round(pipeline.progress)}%</span>
          </div>
        </div>

        <div className="flex-1 space-y-3">
          <div>
            <div className="text-xs text-slate-500 uppercase tracking-widest font-semibold mb-1">Processed</div>
            <div className="text-2xl font-bold text-white tabular-nums">
              {pipeline.recordsProcessed?.toLocaleString() || '0'}
              <span className="text-sm text-slate-500 font-normal ml-2">/ {pipeline.totalRecords?.toLocaleString() || '0'}</span>
            </div>
          </div>
          
          <div className="flex items-center gap-2 text-[11px] text-slate-500">
            <Clock className="w-3 h-3" />
            Last run: {pipeline.lastRun || 'Never'}
          </div>
        </div>
      </div>

      {/* Decorative Gradient Background */}
      <div className="absolute -right-4 -bottom-4 w-24 h-24 bg-indigo-600/5 blur-3xl rounded-full group-hover:bg-indigo-600/10 transition-colors"></div>
    </div>
  );
}
