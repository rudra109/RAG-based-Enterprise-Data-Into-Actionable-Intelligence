'use client';

import React from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Anomaly, AnomalySeverity } from '@/types/anomaly';
import { cn } from '@/lib/utils';
import { AlertCircle, Clock, CheckCircle2, ShieldAlert } from 'lucide-react';

interface AnomalyListProps {
  anomalies: Anomaly[];
  onAcknowledge: (id: string) => void;
}

const severityConfig: Record<AnomalySeverity, { color: string; icon: React.ReactNode }> = {
  critical: { color: 'bg-red-500/10 text-red-500 border-red-500/20', icon: <ShieldAlert className="w-3.5 h-3.5" /> },
  warning: { color: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20', icon: <AlertCircle className="w-3.5 h-3.5" /> },
  info: { color: 'bg-blue-500/10 text-blue-500 border-blue-500/20', icon: <AlertCircle className="w-3.5 h-3.5" /> },
};

export default function AnomalyList({ anomalies, onAcknowledge }: AnomalyListProps) {
  return (
    <div className="bg-slate-900/50 border border-slate-800 rounded-3xl overflow-hidden flex flex-col h-full shadow-2xl">
      <div className="p-6 border-b border-slate-800 bg-slate-950/50 backdrop-blur-md">
        <h2 className="text-lg font-bold text-white flex items-center gap-2">
          <AlertCircle className="w-5 h-5 text-indigo-500" />
          Recent Anomalies
        </h2>
        <p className="text-xs text-slate-500 mt-1 uppercase tracking-widest font-semibold">
          {anomalies.length} Unresolved Issues
        </p>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-4 space-y-3">
          {anomalies.map((anomaly) => {
            const config = severityConfig[anomaly.severity];
            return (
              <div 
                key={anomaly.id}
                className={cn(
                  "group p-4 rounded-2xl border transition-all duration-300",
                  anomaly.isAcknowledged 
                    ? "bg-slate-950/20 border-slate-900 opacity-50" 
                    : "bg-slate-900 border-slate-800 hover:border-indigo-500/30 hover:bg-slate-800/50"
                )}
              >
                <div className="flex justify-between items-start mb-3">
                  <Badge variant="outline" className={cn("px-2 py-0.5 flex items-center gap-1.5 text-[10px] uppercase font-bold tracking-wider", config.color)}>
                    {config.icon}
                    {anomaly.severity}
                  </Badge>
                  <div className="flex items-center gap-1.5 text-[10px] text-slate-500 font-medium">
                    <Clock className="w-3 h-3" />
                    {new Date(anomaly.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </div>
                </div>

                <div className="mb-4">
                  <h3 className="text-sm font-bold text-white mb-1 group-hover:text-indigo-400 transition-colors">
                    {anomaly.metricName}
                  </h3>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Detected value <span className="text-white font-mono">{anomaly.value}</span> vs expected <span className="text-slate-500 font-mono">{anomaly.expectedValue}</span>.
                  </p>
                </div>

                <div className="flex items-center justify-between">
                  <div className="text-[10px] text-slate-600 font-bold uppercase tracking-tighter">
                    Score: {(anomaly.score * 100).toFixed(1)}%
                  </div>
                  {!anomaly.isAcknowledged && (
                    <Button 
                      size="sm" 
                      onClick={() => onAcknowledge(anomaly.id)}
                      className="h-8 bg-slate-950 border border-slate-800 text-slate-300 hover:bg-indigo-600 hover:text-white hover:border-indigo-600 transition-all rounded-lg text-[11px] font-bold"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5 mr-1.5" />
                      Acknowledge
                    </Button>
                  )}
                </div>
              </div>
            );
          })}
          {anomalies.length === 0 && (
            <div className="py-20 text-center space-y-4 opacity-50">
              <CheckCircle2 className="w-12 h-12 mx-auto text-green-500/20" />
              <p className="text-slate-500 text-sm">All clear! No new anomalies detected.</p>
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
