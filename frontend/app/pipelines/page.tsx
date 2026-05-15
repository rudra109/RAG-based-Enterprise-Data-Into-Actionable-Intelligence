'use client';

import React, { useState, useEffect } from 'react';
import useSWR from 'swr';
import PipelineCard from '@/components/PipelineCard';
import { Pipeline, PipelineStatus } from '@/types/pipeline';
import { 
  Dialog, 
  DialogContent, 
  DialogHeader, 
  DialogTitle, 
  DialogDescription, 
  DialogFooter 
} from '@/components/ui/dialog';
import { 
  Sheet, 
  SheetContent, 
  SheetHeader, 
  SheetTitle, 
  SheetDescription 
} from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Play, RotateCw, Settings2, Terminal, Info, AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/utils';

const fetcher = (url: string) => fetch(url).then(res => res.json());

export default function PipelineDashboard() {
  const { data: pipelines, error, mutate } = useSWR<Pipeline[]>('/v1/pipeline/list', fetcher);
  const [selectedPipeline, setSelectedPipeline] = useState<Pipeline | null>(null);
  const [isTriggerDialogOpen, setIsTriggerDialogOpen] = useState(false);
  const [pipelineToTrigger, setPipelineToTrigger] = useState<Pipeline | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);

  // WebSocket for real-time updates
  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const socket = new WebSocket(`${protocol}//${window.location.host}/ws/events`);

    socket.onmessage = (event) => {
      const update = JSON.parse(event.data);
      if (update.type === 'PIPELINE_UPDATE') {
        mutate(prev => prev?.map(p => 
          p.id === update.pipelineId 
            ? { ...p, ...update.data } 
            : p
        ), false);
      }
    };

    return () => socket.close();
  }, [mutate]);

  const handleTriggerRun = async () => {
    if (!pipelineToTrigger) return;
    
    try {
      const response = await fetch(`/v1/pipeline/${pipelineToTrigger.id}/trigger`, {
        method: 'POST',
      });
      if (response.ok) {
        setIsTriggerDialogOpen(false);
        mutate(); // Refresh list
      }
    } catch (err) {
      console.error('Trigger error:', err);
    }
  };

  if (error) return (
    <div className="flex flex-col items-center justify-center min-h-[400px] text-red-400">
      <AlertTriangle className="w-12 h-12 mb-4" />
      <p>Failed to load pipelines. Please try again later.</p>
    </div>
  );

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 animate-in fade-in duration-500">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight">Pipeline Control</h1>
          <p className="text-slate-500 mt-1">Monitor and manage your data processing pipelines in real-time.</p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" className="bg-slate-900 border-slate-800 text-slate-300 hover:bg-slate-800" onClick={() => mutate()}>
            <RotateCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
          <Button className="bg-indigo-600 hover:bg-indigo-500 text-white">
            <Settings2 className="w-4 h-4 mr-2" />
            Config
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {!pipelines ? (
          Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-48 bg-slate-900/50 border border-slate-800 rounded-2xl animate-pulse" />
          ))
        ) : (
          pipelines.map((pipeline) => (
            <PipelineCard 
              key={pipeline.id} 
              pipeline={pipeline} 
              onClick={() => {
                setSelectedPipeline(pipeline);
                setIsDetailOpen(true);
              }}
            />
          ))
        )}
      </div>

      {/* Trigger Confirmation Dialog */}
      <Dialog open={isTriggerDialogOpen} onOpenChange={setIsTriggerDialogOpen}>
        <DialogContent className="bg-slate-900 border-slate-800 text-white">
          <DialogHeader>
            <DialogTitle>Trigger Pipeline Run</DialogTitle>
            <DialogDescription className="text-slate-400">
              Are you sure you want to trigger a manual run for <span className="font-semibold text-white">{pipelineToTrigger?.name}</span>? 
              This will start processing records immediately.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-3">
            <Button variant="outline" onClick={() => setIsTriggerDialogOpen(false)} className="bg-transparent border-slate-800 text-slate-400 hover:bg-slate-800">
              Cancel
            </Button>
            <Button onClick={handleTriggerRun} className="bg-indigo-600 hover:bg-indigo-500">
              Trigger Now
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Pipeline Detail Side Panel */}
      <Sheet open={isDetailOpen} onOpenChange={setIsDetailOpen}>
        <SheetContent className="w-full sm:max-w-xl bg-[#020617] border-l border-slate-800 p-0 overflow-hidden flex flex-col">
          <SheetHeader className="p-6 border-b border-slate-800 shrink-0">
            <div className="flex justify-between items-start">
              <div>
                <SheetTitle className="text-2xl font-bold text-white mb-1">
                  {selectedPipeline?.name}
                </SheetTitle>
                <SheetDescription className="text-slate-500">
                  Detailed execution logs and status history
                </SheetDescription>
              </div>
              <Button 
                onClick={() => {
                  setPipelineToTrigger(selectedPipeline);
                  setIsTriggerDialogOpen(true);
                }}
                disabled={selectedPipeline?.status === 'running'}
                className="bg-indigo-600 hover:bg-indigo-500 text-white"
              >
                <Play className="w-4 h-4 mr-2" />
                Trigger
              </Button>
            </div>
          </SheetHeader>

          <div className="flex-1 overflow-hidden flex flex-col">
            <div className="p-6 bg-slate-900/30 border-b border-slate-800 grid grid-cols-2 gap-4 shrink-0">
              <div className="space-y-1">
                <div className="text-[10px] uppercase tracking-widest text-slate-500 font-bold">Status</div>
                <div className="flex items-center gap-2">
                  <div className={cn(
                    "w-2 h-2 rounded-full animate-pulse",
                    selectedPipeline?.status === 'running' ? "bg-blue-500" : "bg-green-500"
                  )} />
                  <span className="text-sm font-medium text-white capitalize">{selectedPipeline?.status}</span>
                </div>
              </div>
              <div className="space-y-1">
                <div className="text-[10px] uppercase tracking-widest text-slate-500 font-bold">Progress</div>
                <div className="text-sm font-medium text-white">{selectedPipeline?.progress}%</div>
              </div>
            </div>

            <ScrollArea className="flex-1 p-6">
              <div className="space-y-6">
                <div className="flex items-center gap-2 text-indigo-400 font-semibold text-xs uppercase tracking-wider mb-2">
                  <Terminal className="w-4 h-4" />
                  Execution Logs
                </div>
                
                {/* Simulated Logs */}
                <div className="space-y-4 font-mono text-xs">
                  {[
                    { time: '2026-05-13 23:00:01', level: 'info', msg: 'Initializing pipeline environment...', step: 'INIT' },
                    { time: '2026-05-13 23:00:05', level: 'info', msg: 'Fetching source data from S3 bucket...', step: 'EXTRACT' },
                    { time: '2026-05-13 23:01:12', level: 'info', msg: 'Mapping schema for 10,240 records...', step: 'TRANSFORM' },
                    { time: '2026-05-13 23:02:45', level: 'warn', msg: 'Detected 12 invalid rows, skipping...', step: 'TRANSFORM' },
                    { time: '2026-05-13 23:05:00', level: 'info', msg: 'Pushing clean data to vector database...', step: 'LOAD' },
                  ].map((log, i) => (
                    <div key={i} className="flex gap-4 group">
                      <div className="text-slate-600 shrink-0 select-none">{log.time.split(' ')[1]}</div>
                      <div className="flex-1">
                        <span className={cn(
                          "mr-3 px-1.5 py-0.5 rounded text-[10px] font-bold uppercase",
                          log.level === 'info' ? "bg-blue-500/10 text-blue-500" : "bg-yellow-500/10 text-yellow-500"
                        )}>
                          {log.step}
                        </span>
                        <span className="text-slate-300">{log.msg}</span>
                      </div>
                    </div>
                  ))}
                  {selectedPipeline?.status === 'running' && (
                    <div className="flex gap-4 animate-pulse">
                      <div className="text-slate-600 shrink-0">--:--:--</div>
                      <div className="flex-1 text-indigo-400">Processing next batch...</div>
                    </div>
                  )}
                </div>
              </div>
            </ScrollArea>
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
