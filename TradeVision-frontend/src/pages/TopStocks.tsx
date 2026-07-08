import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, TrendingUp, TrendingDown, Activity } from 'lucide-react';
import { useStockContext } from '../context/StockContext';
import type { StockQuote } from '../types/stock';

type Tab = 'gainers' | 'losers' | 'active';

export const TopStocks: React.FC = () => {
  const { marketSummary, isLoading } = useStockContext();
  const [activeTab, setActiveTab] = useState<Tab>('gainers');
  const navigate = useNavigate();

  if (isLoading || !marketSummary) {
    return (
      <div className="flex items-center justify-center min-h-[calc(100vh-64px)]">
        <div className="animate-pulse flex space-x-4">
          <div className="h-12 w-12 bg-border rounded-full"></div>
          <div className="space-y-3">
            <div className="h-4 w-40 bg-border rounded"></div>
            <div className="h-4 w-24 bg-border rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  const getActiveData = (): StockQuote[] => {
    switch (activeTab) {
      case 'gainers': return marketSummary.gainers;
      case 'losers': return marketSummary.losers;
      case 'active': return marketSummary.mostActive;
      default: return [];
    }
  };

  const tabs = [
    { id: 'gainers', label: 'Top Gainers', icon: TrendingUp, color: 'text-accent-green' },
    { id: 'losers', label: 'Top Losers', icon: TrendingDown, color: 'text-accent-red' },
    { id: 'active', label: 'Most Active', icon: Activity, color: 'text-blue-500' },
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-text-primary">Market Overview</h1>
        <p className="text-text-secondary mt-2">Track the top moving stocks on the Colombo Stock Exchange today.</p>
      </div>

      {/* Tabs */}
      <div className="flex space-x-1 bg-secondary p-1 rounded-xl w-fit mb-8 border border-border">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as Tab)}
            className={`flex items-center space-x-2 px-6 py-2.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === tab.id
                ? 'bg-primary text-text-primary shadow-sm'
                : 'text-text-secondary hover:text-text-primary hover:bg-primary/50'
            }`}
          >
            <tab.icon className={`w-4 h-4 ${activeTab === tab.id ? tab.color : ''}`} />
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Data Table */}
      <div className="bg-primary border border-border rounded-2xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-secondary/50 text-text-secondary text-sm border-b border-border">
                <th className="px-6 py-4 font-medium">Rank</th>
                <th className="px-6 py-4 font-medium">Symbol & Name</th>
                <th className="px-6 py-4 font-medium text-right">Price (LKR)</th>
                <th className="px-6 py-4 font-medium text-right">Change</th>
                <th className="px-6 py-4 font-medium text-right">Volume</th>
                <th className="px-6 py-4 font-medium text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {getActiveData().map((quote, index) => {
                const isPositive = quote.change >= 0;
                return (
                  <tr key={quote.ticker} className="hover:bg-secondary/30 transition-colors">
                    <td className="px-6 py-4 text-text-secondary font-medium">
                      #{index + 1}
                    </td>
                    <td className="px-6 py-4">
                      <div className="font-bold text-text-primary">{quote.ticker}</div>
                      <div className="text-sm text-text-secondary">{quote.name}</div>
                    </td>
                    <td className="px-6 py-4 font-medium text-right text-text-primary">
                      {quote.price.toFixed(2)}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <span className={`inline-flex items-center px-2.5 py-1 rounded-md text-sm font-medium ${
                        isPositive ? 'bg-accent-green/10 text-accent-green' : 'bg-accent-red/10 text-accent-red'
                      }`}>
                        {isPositive ? '+' : ''}{quote.change.toFixed(2)} ({isPositive ? '+' : ''}{quote.changePercent.toFixed(2)}%)
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right text-text-secondary font-mono text-sm">
                      {quote.volume.toLocaleString()}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button 
                        onClick={() => navigate(`/analyzer?ticker=${quote.ticker}`)}
                        className="inline-flex items-center text-sm font-medium text-text-secondary hover:text-accent-green transition-colors"
                      >
                        Analyze <ArrowRight className="ml-1 w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
