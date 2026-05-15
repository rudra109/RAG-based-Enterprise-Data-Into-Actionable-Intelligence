'use client';

import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Dot,
} from 'recharts';
import { MetricPoint } from '@/types/anomaly';

interface AnomalyChartProps {
  data: MetricPoint[];
  onAnomalyClick?: (id: string) => void;
}

const CustomDot = (props: any) => {
  const { cx, cy, payload } = props;

  if (payload.isAnomaly) {
    return (
      <Dot 
        cx={cx} 
        cy={cy} 
        r={5} 
        fill="#ef4444" 
        stroke="#7f1d1d" 
        strokeWidth={2} 
        className="cursor-pointer hover:r-7 transition-all"
      />
    );
  }

  return null;
};

export default function AnomalyChart({ data, onAnomalyClick }: AnomalyChartProps) {
  return (
    <div className="w-full h-[400px] bg-slate-900/30 p-6 rounded-3xl border border-slate-800/50 shadow-2xl">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <defs>
            <linearGradient id="lineGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#6366f1" stopOpacity={0.1}/>
              <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
          <XAxis 
            dataKey="timestamp" 
            stroke="#64748b" 
            fontSize={11} 
            tickLine={false} 
            axisLine={false}
            tickFormatter={(str) => {
              const date = new Date(str);
              return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            }}
          />
          <YAxis 
            stroke="#64748b" 
            fontSize={11} 
            tickLine={false} 
            axisLine={false}
            tickFormatter={(val) => val.toLocaleString()}
          />
          <Tooltip
            contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '12px', boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)' }}
            itemStyle={{ color: '#e2e8f0' }}
            labelStyle={{ color: '#64748b', marginBottom: '4px', fontSize: '11px' }}
            cursor={{ stroke: '#334155', strokeWidth: 2 }}
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke="#6366f1"
            strokeWidth={3}
            dot={<CustomDot />}
            activeDot={{ r: 6, fill: '#818cf8', strokeWidth: 2, stroke: '#020617' }}
            animationDuration={1500}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
