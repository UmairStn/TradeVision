import React from 'react';
import {
  BarChart,
  Bar,
  Cell,
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

  const gridColor = theme === 'dark' ? '#334155' : '#e2e8f0'; // matches border-color roughly
  const textColor = theme === 'dark' ? '#94a3b8' : '#64748b'; // text-secondary

  // Calculate min and max for Y-axis scaling to make bars look reasonable
  const minPrice = Math.min(...data.map(d => d.low || d.close));
  const maxPrice = Math.max(...data.map(d => d.high || d.close));
  const padding = (maxPrice - minPrice) * 0.1;

  return (
    <div className="h-[400px] w-full mt-4 animate-fade-in-up">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
        >
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
            domain={[Math.max(0, minPrice - padding), maxPrice + padding]}
            stroke={textColor}
            tick={{ fill: textColor, fontSize: 12 }}
            tickFormatter={(val) => `Rs ${val.toFixed(2)}`}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip 
            contentStyle={{ 
              backgroundColor: theme === 'dark' ? '#1e293b' : '#ffffff',
              borderColor: theme === 'dark' ? '#334155' : '#e2e8f0',
              borderRadius: '8px',
              color: theme === 'dark' ? '#f8fafc' : '#0f172a',
              boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)'
            }}
            itemStyle={{ color: 'var(--text-primary)' }}
            labelStyle={{ color: textColor, marginBottom: '4px' }}
            cursor={{ fill: theme === 'dark' ? '#334155' : '#e2e8f0', opacity: 0.4 }}
          />
          <Bar 
            dataKey="close" 
            animationDuration={1000}
            radius={[4, 4, 0, 0]}
          >
            {data.map((entry, index) => {
              // Determine color: Green if close >= open, Red if close < open
              const isPositive = entry.close >= entry.open;
              // Use a darker green and red for a more premium, professional financial look
              const darkGreen = theme === 'dark' ? '#16a34a' : '#15803d'; // green-600 / green-700
              const darkRed = theme === 'dark' ? '#dc2626' : '#b91c1c';   // red-600 / red-700
              
              return (
                <Cell 
                  key={`cell-${index}`} 
                  fill={isPositive ? darkGreen : darkRed} 
                />
              );
            })}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};
