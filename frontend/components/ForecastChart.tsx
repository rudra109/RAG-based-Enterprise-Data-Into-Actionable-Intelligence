'use client';

import React from 'react';
import {
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { ForecastPoint } from '@/types/forecast';

interface ForecastChartProps {
  data: ForecastPoint[];
  forecastStartDate: string;
}

export default function ForecastChart({ data, forecastStartDate }: ForecastChartProps) {
  return (
    <div className="w-full h-[450px] bg-slate-900/30 p-6 rounded-3xl border border-slate-800/50 shadow-2xl">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data}>
          <defs>
            <linearGradient id="actualGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.1}/>
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
            </linearGradient>
            <linearGradient id="predictionGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#22c55e" stopOpacity={0.1}/>
              <stop offset="95%" stopColor="#22c55e" stopOpacity={0}/>
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
              return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
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
            contentStyle={{ 
              backgroundColor: '#0f172a', 
              border: '1px solid #1e293b', 
              borderRadius: '12px',
              boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)'
            }}
            itemStyle={{ color: '#e2e8f0', fontSize: '12px' }}
            labelStyle={{ color: '#64748b', marginBottom: '4px', fontSize: '11px' }}
            cursor={{ stroke: '#334155', strokeWidth: 2 }}
          />

          {/* Confidence Band */}
          <Area
            type="monotone"
            dataKey="upper_bound"
            stroke="none"
            fill="#3b82f6"
            fillOpacity={0.05}
          />
          <Area
            type="monotone"
            dataKey="lower_bound"
            stroke="none"
            fill="#020617" // Masking the bottom
            fillOpacity={1}
          />
          
          {/* Historical Data (Actuals) */}
          <Line
            type="monotone"
            dataKey="actual_value"
            stroke="#3b82f6"
            strokeWidth={3}
            dot={false}
            activeDot={{ r: 6, fill: '#3b82f6', strokeWidth: 2, stroke: '#020617' }}
          />
          
          {/* Predictions */}
          <Line
            type="monotone"
            dataKey="predicted_value"
            stroke="#22c55e"
            strokeWidth={3}
            strokeDasharray="5 5"
            dot={false}
            activeDot={{ r: 6, fill: '#22c55e', strokeWidth: 2, stroke: '#020617' }}
          />

          {/* Forecast Start Indicator */}
          <ReferenceLine 
            x={forecastStartDate} 
            stroke="#ef4444" 
            strokeDasharray="3 3"
            label={{ 
              value: 'Forecast Start', 
              position: 'top', 
              fill: '#ef4444', 
              fontSize: 10,
              fontWeight: 'bold',
              offset: 10
            }} 
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
