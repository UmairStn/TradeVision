import React from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts';
import type { StockPrice } from '../types/stock';
import { useTheme } from '../context/ThemeContext';

interface LiveChartProps {
  data: StockPrice[];
  ticker: string;
}

export const LiveChart: React.FC<LiveChartProps> = ({ data, ticker }) => {
  const { theme } = useTheme();
  
  if (!data || data.length === 0) return null;

  // Determine trend based on first and last data points
  const firstPrice = data[0].close;
  const lastPrice = data[data.length - 1].close;
  const isPositive = lastPrice >= firstPrice;
  
  const strokeColor = isPositive ? 'var(--accent-green)' : 'var(--accent-red)';
  const gridColor = theme === 'dark' ? '#334155' : '#e2e8f0'; // matches border-color roughly
  const textColor = theme === 'dark' ? '#94a3b8' : '#64748b'; // text-secondary

  return (
    <div className="h-[400px] w-full mt-4">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={data}
          margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
        >
          <defs>
            <linearGradient id={`colorGradient-${ticker}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={strokeColor} stopOpacity={0.3} />
              <stop offset="95%" stopColor={strokeColor} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={gridColor} />
          <XAxis 
            dataKey="timestamp" 
            tickFormatter={(tick) => {
              const d = new Date(tick);
              return `${d.getDate()} ${d.toLocaleString('default', { month: 'short' })}`;
            }}
            stroke={textColor}
            tick={{ fill: textColor, fontSize: 12 }}
            tickMargin={10}
            axisLine={false}
          />
          <YAxis 
            domain={['auto', 'auto']}
            stroke={textColor}
            tick={{ fill: textColor, fontSize: 12 }}
            tickFormatter={(val) => `Rs ${val}`}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip 
            contentStyle={{ 
              backgroundColor: theme === 'dark' ? '#1e293b' : '#ffffff',
              borderColor: theme === 'dark' ? '#334155' : '#e2e8f0',
              borderRadius: '8px',
              color: theme === 'dark' ? '#f8fafc' : '#0f172a'
            }}
            itemStyle={{ color: strokeColor }}
            labelStyle={{ color: textColor, marginBottom: '4px' }}
          />
          <Area 
            type="monotone" 
            dataKey="close" 
            stroke={strokeColor} 
            strokeWidth={2}
            fillOpacity={1} 
            fill={`url(#colorGradient-${ticker})`} 
            animationDuration={1000}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};
