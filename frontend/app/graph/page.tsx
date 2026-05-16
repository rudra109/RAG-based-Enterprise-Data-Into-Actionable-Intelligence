'use client';

import React, { useState, useRef } from 'react';
import useSWR from 'swr';
import { 
  Network, 
  Search, 
  ZoomIn, 
  ZoomOut, 
  Maximize, 
  Download, 
  FileText, 
  ExternalLink,
  Info,
  Database,
  Share2
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { 
  Sheet, 
  SheetContent, 
  SheetHeader, 
  SheetTitle, 
  SheetDescription 
} from '@/components/ui/sheet';
import KnowledgeGraph from '@/components/KnowledgeGraph';
import { KGSubgraph, GraphNode } from '@/types/kg';
import { cn } from '@/lib/utils';
import { useStore } from '@/store/useStore';

const fetcher = (url: string) => fetch(url).then(res => res.json());

export default function KnowledgeGraphViewer() {
  const { selectedWorkspace } = useStore();
  const [query, setQuery] = useState('');
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const cyRef = useRef<any>(null);

  const { data: subgraph, mutate, isLoading } = useSWR<KGSubgraph>(
    `/v1/kg/subgraph?graph_id=${encodeURIComponent(selectedWorkspace)}`,
    fetcher
  );

  const handleQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    try {
      const response = await fetch('/v1/kg/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, mode: 'nl', workspace: selectedWorkspace }),
      });
      if (response.ok) {
        const newData = await response.json();
        mutate(newData, false);
      }
    } catch (err) {
      console.error('KG Query error:', err);
    }
  };

  const handleExportPNG = () => {
    if (cyRef.current) {
      const png64 = cyRef.current.png({ full: true, bg: '#020617' });
      const link = document.createElement('a');
      link.href = png64;
      link.download = `knowledge-graph-${Date.now()}.png`;
      link.click();
    }
  };

  return (
    <div className="flex flex-col h-full bg-[#020617] text-slate-200">
      {/* Header / Query Bar */}
      <div className="p-6 border-b border-slate-800 bg-[#020617]/50 backdrop-blur-xl flex flex-col md:flex-row gap-6 items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-indigo-600/20 flex items-center justify-center border border-indigo-500/20">
            <Network className="w-6 h-6 text-indigo-500" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight">Knowledge Explorer</h1>
            <p className="text-[10px] text-slate-500 uppercase tracking-widest font-bold">{selectedWorkspace} Relationship Graph</p>
          </div>
        </div>

        <form onSubmit={handleQuery} className="flex-1 max-w-2xl relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-600" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask about connections... (e.g. How is Project X related to Elon Musk?)"
            className="w-full bg-slate-900 border border-slate-800 rounded-2xl py-3 pl-12 pr-4 text-white placeholder:text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all shadow-lg"
          />
        </form>

        <div className="flex items-center gap-2">
          <Button variant="outline" className="bg-slate-900 border-slate-800 text-slate-400 hover:bg-slate-800 hover:text-white" onClick={handleExportPNG}>
            <Download className="w-4 h-4 mr-2" />
            Export PNG
          </Button>
          <Button className="bg-indigo-600 hover:bg-indigo-500 text-white">
            <Share2 className="w-4 h-4 mr-2" />
            Share
          </Button>
        </div>
      </div>

      {/* Graph Area */}
      <div className="flex-1 relative overflow-hidden p-6">
        {isLoading ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-[#020617] z-10">
            <Network className="w-12 h-12 text-indigo-500 animate-pulse mb-4" />
            <p className="text-slate-500 font-medium">Synthesizing relationships...</p>
          </div>
        ) : subgraph && (
          <KnowledgeGraph 
            data={subgraph} 
            setCy={(cy) => cyRef.current = cy}
            onNodeClick={(data) => {
              setSelectedNode(data);
              setIsDetailOpen(true);
            }} 
          />
        )}

        {/* Floating Controls */}
        <div className="absolute bottom-12 right-12 flex flex-col gap-2 bg-slate-900/80 backdrop-blur-md p-2 rounded-2xl border border-slate-800 shadow-2xl">
          <Button variant="ghost" size="icon" className="w-10 h-10 text-slate-400 hover:text-white" onClick={() => cyRef.current?.zoom(cyRef.current.zoom() * 1.2)}>
            <ZoomIn className="w-5 h-5" />
          </Button>
          <Button variant="ghost" size="icon" className="w-10 h-10 text-slate-400 hover:text-white" onClick={() => cyRef.current?.zoom(cyRef.current.zoom() * 0.8)}>
            <ZoomOut className="w-5 h-5" />
          </Button>
          <div className="h-px bg-slate-800 mx-2" />
          <Button variant="ghost" size="icon" className="w-10 h-10 text-slate-400 hover:text-white" onClick={() => cyRef.current?.fit()}>
            <Maximize className="w-5 h-5" />
          </Button>
        </div>

        {/* Legend */}
        <div className="absolute bottom-12 left-12 bg-slate-900/80 backdrop-blur-md p-4 rounded-2xl border border-slate-800 shadow-2xl space-y-3">
          <div className="text-[10px] uppercase font-bold tracking-widest text-slate-500 mb-1">Entity Map</div>
          <div className="flex items-center gap-3">
            <div className="w-3 h-3 rounded-full bg-blue-500" />
            <span className="text-xs text-slate-300">Person</span>
          </div>
          <div className="flex items-center gap-3">
            <div className="w-3 h-3 bg-green-500" />
            <span className="text-xs text-slate-300">Organization</span>
          </div>
          <div className="flex items-center gap-3">
            <div className="w-3 h-3 bg-yellow-500 rotate-45" />
            <span className="text-xs text-slate-300">Product</span>
          </div>
        </div>
      </div>

      {/* Detail Side Panel */}
      <Sheet open={isDetailOpen} onOpenChange={setIsDetailOpen}>
        <SheetContent className="w-full sm:max-w-md bg-[#020617] border-l border-slate-800 p-0 overflow-hidden flex flex-col shadow-2xl">
          <SheetHeader className="p-8 border-b border-slate-800 shrink-0">
            <div className="w-12 h-12 rounded-2xl bg-slate-900 flex items-center justify-center border border-slate-800 mb-4">
              <Database className="w-6 h-6 text-indigo-500" />
            </div>
            <SheetTitle className="text-2xl font-bold text-white mb-2">{selectedNode?.label}</SheetTitle>
            <SheetDescription className="flex items-center gap-2">
              <span className={cn(
                "px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-widest",
                selectedNode?.type === 'PERSON' ? "bg-blue-500/10 text-blue-500" :
                selectedNode?.type === 'ORG' ? "bg-green-500/10 text-green-500" : "bg-yellow-500/10 text-yellow-500"
              )}>
                {selectedNode?.type}
              </span>
              <span className="text-slate-600">•</span>
              <span className="text-slate-500">System Entity ID: {selectedNode?.id}</span>
            </SheetDescription>
          </SheetHeader>

          <div className="flex-1 overflow-y-auto p-8 space-y-8">
            <section className="space-y-4">
              <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest flex items-center gap-2">
                <Info className="w-4 h-4" />
                Properties
              </h3>
              <div className="grid gap-3">
                {selectedNode && Object.entries(selectedNode.properties).map(([key, val]) => (
                  <div key={key} className="bg-slate-900/50 p-4 rounded-xl border border-slate-800/50 group hover:border-indigo-500/30 transition-all">
                    <div className="text-[10px] text-slate-600 uppercase font-bold mb-1">{key.replace(/_/g, ' ')}</div>
                    <div className="text-sm text-slate-200">{String(val)}</div>
                  </div>
                ))}
              </div>
            </section>

            {selectedNode?.sourceDocument && (
              <section className="space-y-4">
                <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest flex items-center gap-2">
                  <FileText className="w-4 h-4" />
                  Source Evidence
                </h3>
                <a 
                  href={selectedNode.sourceDocument.url} 
                  target="_blank" 
                  className="block p-4 bg-indigo-600/10 rounded-2xl border border-indigo-500/20 group hover:bg-indigo-600/20 transition-all"
                >
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-sm font-bold text-white group-hover:text-indigo-400 transition-colors">
                      {selectedNode.sourceDocument.name}
                    </span>
                    <ExternalLink className="w-4 h-4 text-indigo-500" />
                  </div>
                  <p className="text-xs text-slate-400">View source document for verification</p>
                </a>
              </section>
            )}
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
