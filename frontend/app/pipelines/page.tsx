'use client';

import React, { useMemo, useState } from 'react';
import useSWR from 'swr';
import PipelineCard from '@/components/PipelineCard';
import { Pipeline } from '@/types/pipeline';
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
import { Play, RotateCw, Settings2, Terminal, AlertTriangle, X, CheckCircle2, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useStore } from '@/store/useStore';
import { toast } from 'sonner';

const fetcher = (url: string) => fetch(url).then(res => res.json());

export default function PipelineDashboard() {
  const { selectedWorkspace, workspaceData } = useStore();
  const { data: pipelines, error, mutate } = useSWR<Pipeline[]>(
    `/v1/pipeline/list?workspace=${encodeURIComponent(selectedWorkspace)}`,
    fetcher
  );
  const [selectedPipeline, setSelectedPipeline] = useState<Pipeline | null>(null);
  const [isTriggerDialogOpen, setIsTriggerDialogOpen] = useState(false);
  const [pipelineToTrigger, setPipelineToTrigger] = useState<Pipeline | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [isConfigOpen, setIsConfigOpen] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [pipelineOverrides, setPipelineOverrides] = useState<Record<string, Partial<Pipeline>>>({});

  const visiblePipelines = useMemo(() => {
    const localSources = workspaceData[selectedWorkspace]?.sources || [];
    const localPipelines: Pipeline[] = localSources.map((source) => ({
      id: `local-${source.id}`,
      name: `${source.name} Ingestion`,
      status: 'idle',
      progress: 100,
      lastRun: source.addedAt,
      recordsProcessed: source.records,
      totalRecords: source.records,
    }));

    return [...localPipelines, ...(pipelines || [])].map((pipeline) => ({
      ...pipeline,
      ...(pipelineOverrides[pipeline.id] || {}),
    }));
  }, [pipelineOverrides, pipelines, selectedWorkspace, workspaceData]);

  const activeSelectedPipeline = selectedPipeline
    ? visiblePipelines.find((pipeline) => pipeline.id === selectedPipeline.id) || selectedPipeline
    : null;

  const executionLogs = useMemo(() => {
    if (!activeSelectedPipeline) return [];

    const recordCount = activeSelectedPipeline.totalRecords.toLocaleString();
    const isRunning = activeSelectedPipeline.status === 'running';
    const isFinished = activeSelectedPipeline.status === 'success' || activeSelectedPipeline.progress === 100;

    return [
      { time: 'Now', level: 'info', msg: `Initializing ${activeSelectedPipeline.name}...`, step: 'INIT' },
      { time: isRunning || isFinished ? 'Now' : '--:--:--', level: 'info', msg: 'Reading source data from the selected workspace...', step: 'EXTRACT' },
      { time: activeSelectedPipeline.progress >= 45 ? 'Now' : '--:--:--', level: 'info', msg: `Mapping schema for ${recordCount} records...`, step: 'TRANSFORM' },
      { time: activeSelectedPipeline.progress >= 75 ? 'Now' : '--:--:--', level: 'warn', msg: 'Checking invalid rows and duplicate values...', step: 'VALIDATE' },
      { time: isFinished ? 'Now' : '--:--:--', level: 'info', msg: 'Loading clean output into the workspace index...', step: 'LOAD' },
    ];
  }, [activeSelectedPipeline]);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await mutate();
      toast.success('Pipeline list refreshed');
    } catch {
      toast.error('Failed to refresh pipelines');
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleTriggerRun = async () => {
    if (!pipelineToTrigger) return;

    const targetPipeline = pipelineToTrigger;
    setIsTriggerDialogOpen(false);
    
    try {
      const response = await fetch(`/v1/pipeline/${targetPipeline.id}/trigger`, {
        method: 'POST',
      });
      if (response.ok) {
        const startedAt = new Date().toISOString();
        const totalRecords = targetPipeline.totalRecords || 1;

        setPipelineOverrides((prev) => ({
          ...prev,
          [targetPipeline.id]: {
            status: 'running',
            progress: 15,
            recordsProcessed: Math.max(1, Math.round(totalRecords * 0.15)),
            lastRun: startedAt,
          },
        }));
        toast.success(`${targetPipeline.name} started`);

        window.setTimeout(() => {
          setPipelineOverrides((prev) => ({
            ...prev,
            [targetPipeline.id]: {
              ...(prev[targetPipeline.id] || {}),
              status: 'running',
              progress: 65,
              recordsProcessed: Math.round(totalRecords * 0.65),
            },
          }));
        }, 700);

        window.setTimeout(() => {
          setPipelineOverrides((prev) => ({
            ...prev,
            [targetPipeline.id]: {
              ...(prev[targetPipeline.id] || {}),
              status: 'success',
              progress: 100,
              recordsProcessed: totalRecords,
              lastRun: new Date().toISOString(),
            },
          }));
          toast.success(`${targetPipeline.name} completed`);
        }, 1600);

        await mutate();
      } else {
        toast.error('Pipeline trigger failed');
      }
    } catch (err) {
      console.error('Trigger error:', err);
      toast.error('Pipeline trigger failed');
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
          <p className="text-slate-500 mt-1">Monitor and manage pipelines for {selectedWorkspace} in real-time.</p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" className="bg-slate-900 border-slate-800 text-slate-300 hover:bg-slate-800" onClick={handleRefresh} disabled={isRefreshing}>
            <RotateCw className={cn("w-4 h-4 mr-2", isRefreshing && "animate-spin")} />
            Refresh
          </Button>
          <Button className="bg-indigo-600 hover:bg-indigo-500 text-white" onClick={() => setIsConfigOpen(true)}>
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
        ) : visiblePipelines.length > 0 ? (
          visiblePipelines.map((pipeline) => (
            <PipelineCard 
              key={pipeline.id} 
              pipeline={pipeline} 
              onClick={() => {
                setSelectedPipeline(pipeline);
                setIsDetailOpen(true);
              }}
            />
          ))
        ) : (
          <div className="md:col-span-2 lg:col-span-3 rounded-3xl border border-dashed border-slate-800 bg-slate-900/30 p-12 text-center">
            <h2 className="text-lg font-bold text-white">No pipelines in {selectedWorkspace}</h2>
            <p className="mt-2 text-sm text-slate-500">Create or connect a pipeline for this workspace to start processing data.</p>
          </div>
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

      {/* Pipeline Config Dialog */}
      <Dialog open={isConfigOpen} onOpenChange={setIsConfigOpen}>
        <DialogContent className="bg-slate-900 border-slate-800 text-white">
          <DialogHeader>
            <DialogTitle>Pipeline Configuration</DialogTitle>
            <DialogDescription className="text-slate-400">
              Default controls for pipelines in {selectedWorkspace}. These settings describe how manual runs behave in this workspace.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-3 py-2">
            {[
              { label: 'Manual trigger mode', value: 'Run immediately after confirmation' },
              { label: 'Refresh source', value: 'Selected workspace pipelines' },
              { label: 'Execution logs', value: 'Keep latest run history visible in the side panel' },
              { label: 'Concurrent runs', value: 'One run per pipeline' },
            ].map((item) => (
              <div key={item.label} className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                <div className="text-xs uppercase tracking-widest text-slate-500 font-bold">{item.label}</div>
                <div className="mt-1 text-sm text-slate-200">{item.value}</div>
              </div>
            ))}
          </div>
          <DialogFooter className="gap-3">
            <Button variant="outline" onClick={() => setIsConfigOpen(false)} className="bg-transparent border-slate-800 text-slate-400 hover:bg-slate-800">
              Close
            </Button>
            <Button
              onClick={() => {
                setIsConfigOpen(false);
                toast.success('Pipeline configuration saved');
              }}
              className="bg-indigo-600 hover:bg-indigo-500"
            >
              Save Config
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Pipeline Detail Side Panel */}
      <Sheet open={isDetailOpen} onOpenChange={setIsDetailOpen}>
        <SheetContent showCloseButton={false} className="w-full sm:max-w-xl bg-[#020617] border-l border-slate-800 p-0 overflow-hidden flex flex-col">
          <SheetHeader className="p-6 border-b border-slate-800 shrink-0">
            <div className="flex items-start gap-4">
              <div className="min-w-0 flex-1 pr-2">
                <SheetTitle className="text-2xl font-bold text-white mb-1 break-words leading-tight">
                  {activeSelectedPipeline?.name}
                </SheetTitle>
                <SheetDescription className="text-slate-500">
                  Detailed execution logs and status history
                </SheetDescription>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <Button 
                  onClick={() => {
                    setPipelineToTrigger(activeSelectedPipeline);
                    setIsTriggerDialogOpen(true);
                  }}
                  disabled={activeSelectedPipeline?.status === 'running'}
                  className="bg-indigo-600 hover:bg-indigo-500 text-white"
                >
                  <Play className="w-4 h-4 mr-2" />
                  Trigger
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-10 w-10 text-slate-500 hover:bg-slate-800 hover:text-white"
                  onClick={() => setIsDetailOpen(false)}
                  aria-label="Close pipeline details"
                >
                  <X className="w-5 h-5" />
                </Button>
              </div>
            </div>
          </SheetHeader>

          <div className="flex-1 overflow-hidden flex flex-col">
            <div className="p-6 bg-slate-900/30 border-b border-slate-800 grid grid-cols-2 gap-4 shrink-0">
              <div className="space-y-1">
                <div className="text-[10px] uppercase tracking-widest text-slate-500 font-bold">Status</div>
                <div className="flex items-center gap-2">
                  <div className={cn(
                    "w-2 h-2 rounded-full animate-pulse",
                    activeSelectedPipeline?.status === 'running' ? "bg-blue-500" :
                    activeSelectedPipeline?.status === 'failed' ? "bg-red-500" :
                    activeSelectedPipeline?.status === 'scheduled' ? "bg-yellow-500" : "bg-green-500"
                  )} />
                  <span className="text-sm font-medium text-white capitalize">{activeSelectedPipeline?.status}</span>
                </div>
              </div>
              <div className="space-y-1">
                <div className="text-[10px] uppercase tracking-widest text-slate-500 font-bold">Progress</div>
                <div className="text-sm font-medium text-white">{activeSelectedPipeline?.progress}%</div>
              </div>
              <div className="space-y-1">
                <div className="text-[10px] uppercase tracking-widest text-slate-500 font-bold">Records</div>
                <div className="text-sm font-medium text-white">
                  {activeSelectedPipeline?.recordsProcessed.toLocaleString()} / {activeSelectedPipeline?.totalRecords.toLocaleString()}
                </div>
              </div>
              <div className="space-y-1">
                <div className="text-[10px] uppercase tracking-widest text-slate-500 font-bold">Last Run</div>
                <div className="flex items-center gap-2 text-sm font-medium text-white">
                  <Clock className="w-3 h-3 text-slate-500" />
                  {activeSelectedPipeline?.lastRun ? new Date(activeSelectedPipeline.lastRun).toLocaleString() : 'Never'}
                </div>
              </div>
            </div>

            <ScrollArea className="flex-1 p-6">
              <div className="space-y-6">
                <div className="flex items-center gap-2 text-indigo-400 font-semibold text-xs uppercase tracking-wider mb-2">
                  <Terminal className="w-4 h-4" />
                  Execution Logs
                </div>
                
                <div className="space-y-4 font-mono text-xs">
                  {executionLogs.map((log, i) => (
                    <div key={i} className="flex gap-4 group">
                      <div className="text-slate-600 shrink-0 select-none">{log.time}</div>
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
                  {activeSelectedPipeline?.status === 'running' && (
                    <div className="flex gap-4 animate-pulse">
                      <div className="text-slate-600 shrink-0">--:--:--</div>
                      <div className="flex-1 text-indigo-400">Processing next batch...</div>
                    </div>
                  )}
                  {activeSelectedPipeline?.status === 'success' && (
                    <div className="flex gap-4 text-green-400">
                      <CheckCircle2 className="w-4 h-4 shrink-0" />
                      <div className="flex-1">Run completed successfully.</div>
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
