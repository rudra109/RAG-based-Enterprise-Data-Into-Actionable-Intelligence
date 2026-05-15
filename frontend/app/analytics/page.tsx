'use client';

import React, { useState } from 'react';
import { 
  Sparkles, 
  Send, 
  History as HistoryIcon, 
  Trash2, 
  Loader2,
  Database,
  Lightbulb,
  ChevronRight,
  Clock
} from 'lucide-react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Button } from '@/components/ui/button';
import { useAgentStore } from '@/stores/agentStore';
import { QueryResult } from '@/types/agent';
import ChartRenderer from '@/components/ChartRenderer';
import DataTable from '@/components/DataTable';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';

const EXAMPLES = [
  'Show me total sales by region last quarter',
  'What are the top 5 performing pipelines?',
  'Analyze error rates across all workspaces',
  'Predict resource usage for the next 30 days',
  'Show monthly user growth since January'
];

export default function AnalyticsAgent() {
  const [query, setQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [currentResult, setCurrentResult] = useState<QueryResult | null>(null);
  const { history, addHistoryItem, clearHistory } = useAgentStore();

  const handleQuery = async (e?: React.FormEvent, customQuery?: string) => {
    e?.preventDefault();
    const finalQuery = customQuery || query;
    if (!finalQuery.trim() || isLoading) return;

    setIsLoading(true);
    try {
      const response = await fetch('/v1/agent/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: finalQuery }),
      });

      if (!response.ok) throw new Error('Query failed');
      
      const data = await response.json();
      const result: QueryResult = {
        id: Date.now().toString(),
        query: finalQuery,
        sql: data.sql,
        explanation: data.explanation,
        chartSuggestion: data.chart_suggestion,
        data: data.data,
        timestamp: Date.now(),
      };

      setCurrentResult(result);
      addHistoryItem(result);
      setQuery('');
    } catch (err) {
      console.error('Agent error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-full bg-[#020617] text-slate-200">
      {/* Main content */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-5xl mx-auto p-8 space-y-10 pb-20">
          {/* Header */}
          <div>
            <h1 className="text-4xl font-bold text-white tracking-tight flex items-center gap-3">
              <Sparkles className="w-8 h-8 text-indigo-500" />
              Analytics Agent
            </h1>
            <p className="text-slate-500 mt-2 text-lg">
              Ask any question about your data using natural language.
            </p>
          </div>

          {/* Input Section */}
          <div className="bg-slate-900/50 border border-slate-800 rounded-3xl p-6 shadow-2xl">
            <form onSubmit={handleQuery} className="relative">
              <textarea
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleQuery();
                  }
                }}
                placeholder="Type your question here... (e.g. Show me the correlation between latency and record volume)"
                className="w-full bg-slate-950/50 border border-slate-800 rounded-2xl py-4 pl-4 pr-16 text-lg text-white placeholder:text-slate-700 min-h-[120px] focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all resize-none"
              />
              <Button
                type="submit"
                disabled={!query.trim() || isLoading}
                className="absolute bottom-4 right-4 h-10 w-10 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl shadow-lg shadow-indigo-600/20"
              >
                {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
              </Button>
            </form>

            {/* Example Chips */}
            <div className="flex flex-wrap gap-2 mt-4">
              {EXAMPLES.map((example) => (
                <button
                  key={example}
                  onClick={() => handleQuery(undefined, example)}
                  className="px-3 py-1.5 rounded-full bg-slate-950 border border-slate-800 text-[11px] font-medium text-slate-500 hover:text-indigo-400 hover:border-indigo-500/50 transition-all"
                >
                  {example}
                </button>
              ))}
            </div>
          </div>

          {/* Results Section */}
          {currentResult ? (
            <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
              {/* Explanation Card */}
              <div className="bg-indigo-600/10 border border-indigo-500/20 rounded-2xl p-6 flex gap-4">
                <Lightbulb className="w-6 h-6 text-indigo-400 shrink-0 mt-1" />
                <div>
                  <h3 className="text-sm font-bold text-indigo-400 uppercase tracking-widest mb-2">Agent Insight</h3>
                  <p className="text-lg text-slate-200 leading-relaxed">
                    {currentResult.explanation}
                  </p>
                </div>
              </div>

              {/* Visualization & SQL */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <div className="lg:col-span-2 space-y-4 min-w-0">
                  <div className="flex items-center justify-between">
                    <h2 className="text-xl font-bold text-white flex items-center gap-2">
                      <ChevronRight className="w-5 h-5 text-indigo-500" />
                      Visualization
                    </h2>
                    <div className="text-xs text-slate-500 uppercase tracking-tighter">
                      Suggestion: {currentResult.chartSuggestion}
                    </div>
                  </div>
                  <ChartRenderer type={currentResult.chartSuggestion} data={currentResult.data} />
                </div>

                <div className="space-y-4">
                  <h2 className="text-xl font-bold text-white flex items-center gap-2">
                    <Database className="w-5 h-5 text-indigo-500" />
                    Generated SQL
                  </h2>
                  <div className="bg-slate-950 rounded-2xl overflow-hidden border border-slate-800 h-[350px]">
                    <ScrollArea className="h-full">
                      <SyntaxHighlighter
                        language="sql"
                        style={vscDarkPlus}
                        customStyle={{
                          margin: 0,
                          padding: '1.5rem',
                          fontSize: '13px',
                          background: 'transparent',
                        }}
                      >
                        {currentResult.sql}
                      </SyntaxHighlighter>
                    </ScrollArea>
                  </div>
                </div>
              </div>

              {/* Data Table */}
              <div className="space-y-4">
                <h2 className="text-xl font-bold text-white flex items-center gap-2">
                  <ChevronRight className="w-5 h-5 text-indigo-500" />
                  Raw Dataset
                </h2>
                <DataTable data={currentResult.data} />
              </div>
            </div>
          ) : !isLoading && (
            <div className="py-20 text-center space-y-4 opacity-50">
              <HistoryIcon className="w-12 h-12 mx-auto text-slate-700" />
              <p className="text-slate-500 max-w-sm mx-auto">
                Waiting for your query. Try one of the examples above to see the agent in action.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* History Sidebar */}
      <div className="w-80 border-l border-slate-800 bg-[#020617]/50 backdrop-blur-xl hidden xl:flex flex-col">
        <div className="p-6 border-b border-slate-800 flex justify-between items-center">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <HistoryIcon className="w-5 h-5 text-slate-500" />
            History
          </h2>
          {history.length > 0 && (
            <Button variant="ghost" size="icon" onClick={clearHistory} className="text-slate-500 hover:text-red-400">
              <Trash2 className="w-4 h-4" />
            </Button>
          )}
        </div>
        <ScrollArea className="flex-1">
          <div className="p-4 space-y-2">
            {history.map((item) => (
              <button
                key={item.id}
                onClick={() => setCurrentResult(item)}
                className={cn(
                  "w-full text-left p-3 rounded-xl transition-all group",
                  currentResult?.id === item.id 
                    ? "bg-indigo-600/10 border border-indigo-500/20" 
                    : "hover:bg-slate-900 border border-transparent"
                )}
              >
                <p className={cn(
                  "text-sm line-clamp-2 mb-2",
                  currentResult?.id === item.id ? "text-indigo-400" : "text-slate-400"
                )}>
                  {item.query}
                </p>
                <div className="flex items-center justify-between text-[10px] text-slate-600 uppercase font-bold tracking-widest">
                  <div className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </div>
                  <ChevronRight className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>
              </button>
            ))}
            {history.length === 0 && (
              <div className="py-20 text-center text-slate-600 text-sm">
                No recent queries
              </div>
            )}
          </div>
        </ScrollArea>
      </div>
    </div>
  );
}
