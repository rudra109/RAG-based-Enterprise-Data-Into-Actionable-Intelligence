'use client';

import React, { useState, useMemo } from 'react';
import { 
  Download, 
  ArrowUpDown, 
  Search
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface DataTableProps {
  data: any[];
}

export default function DataTable({ data }: DataTableProps) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const [filter, setFilter] = useState('');

  const columns = useMemo(() => {
    if (!data || data.length === 0) return [];
    return Object.keys(data[0]);
  }, [data]);

  const sortedData = useMemo(() => {
    let result = [...data];
    
    if (filter) {
      result = result.filter(row => 
        Object.values(row).some(val => 
          String(val).toLowerCase().includes(filter.toLowerCase())
        )
      );
    }

    if (sortKey) {
      result.sort((a, b) => {
        const aVal = a[sortKey];
        const bVal = b[sortKey];
        if (aVal < bVal) return sortOrder === 'asc' ? -1 : 1;
        if (aVal > bVal) return sortOrder === 'asc' ? 1 : -1;
        return 0;
      });
    }
    return result;
  }, [data, sortKey, sortOrder, filter]);

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortOrder('asc');
    }
  };

  const exportToCSV = () => {
    const headers = columns.join(',');
    const rows = sortedData.map(row => 
      columns.map(col => `"${row[col]}"`).join(',')
    ).join('\n');
    
    const csvContent = `data:text/csv;charset=utf-8,${headers}\n${rows}`;
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `analytics_data_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (!data || data.length === 0) return null;

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mt-8">
        <div className="relative w-full sm:w-64">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input
            type="text"
            placeholder="Filter results..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="w-full bg-slate-900 border border-slate-800 rounded-lg py-2 pl-10 pr-4 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
          />
        </div>
        <Button 
          variant="outline" 
          onClick={exportToCSV}
          className="bg-slate-900 border-slate-800 text-slate-300 hover:bg-slate-800 gap-2 whitespace-nowrap"
        >
          <Download className="w-4 h-4" />
          Export to CSV
        </Button>
      </div>

      <div className="bg-slate-900/50 border border-slate-800 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-900 border-b border-slate-800">
                {columns.map(col => (
                  <th 
                    key={col}
                    onClick={() => handleSort(col)}
                    className="px-6 py-4 text-xs font-bold text-slate-400 uppercase tracking-widest cursor-pointer hover:bg-slate-800 transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      {col.replace(/_/g, ' ')}
                      <ArrowUpDown className={cn("w-3 h-3", sortKey === col ? "text-indigo-400" : "text-slate-600")} />
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sortedData.map((row, i) => (
                <tr key={i} className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors">
                  {columns.map(col => (
                    <td key={col} className="px-6 py-4 text-sm text-slate-300 tabular-nums">
                      {typeof row[col] === 'number' ? row[col].toLocaleString() : row[col]}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {sortedData.length === 0 && (
          <div className="py-20 text-center text-slate-500">
            No matching data found
          </div>
        )}
      </div>
    </div>
  );
}
