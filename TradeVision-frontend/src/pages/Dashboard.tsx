import React, { useEffect, useState } from 'react';
import type { UserPortfolio, WatchlistItem } from '../types/stock';
import { fetchPortfolio, fetchWatchlist } from '../services/api';
import { Wallet, TrendingUp, TrendingDown, Layers, Bell, LogOut } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export const Dashboard: React.FC = () => {
  const [portfolio, setPortfolio] = useState<UserPortfolio | null>(null);
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const navigate = useNavigate();

  useEffect(() => {
    fetchPortfolio().then(setPortfolio);
    fetchWatchlist().then(setWatchlist);
  }, []);

  const handleLogout = () => {
    navigate('/login');
  };

  if (!portfolio) {
    return (
      <div className="flex items-center justify-center min-h-[calc(100vh-64px)]">
        <div className="animate-pulse h-8 w-8 bg-accent-green rounded-full"></div>
      </div>
    );
  }

  const isDayPositive = portfolio.dayChange >= 0;

  return (
    <div className="flex h-[calc(100vh-64px)] overflow-hidden">
      
      {/* Sidebar */}
      <aside className="w-64 flex-shrink-0 border-r border-border bg-primary hidden md:flex flex-col">
        <div className="p-6 border-b border-border text-center">
          <div className="w-16 h-16 mx-auto bg-gradient-to-tr from-accent-green to-emerald-400 rounded-full flex items-center justify-center text-white text-xl font-bold shadow-md">
            KP
          </div>
          <h2 className="mt-4 font-bold text-text-primary text-lg">Kasun Perera</h2>
          <p className="text-sm text-text-secondary">Premium Member</p>
        </div>
        
        <nav className="flex-1 overflow-y-auto p-4 space-y-2">
          <button className="w-full flex items-center space-x-3 px-4 py-3 bg-secondary text-text-primary rounded-xl font-medium transition-colors">
            <Layers className="w-5 h-5 text-accent-green" />
            <span>Overview</span>
          </button>
          <button className="w-full flex items-center space-x-3 px-4 py-3 text-text-secondary hover:bg-secondary hover:text-text-primary rounded-xl font-medium transition-colors">
            <Wallet className="w-5 h-5" />
            <span>Portfolio</span>
          </button>
          <button className="w-full flex items-center space-x-3 px-4 py-3 text-text-secondary hover:bg-secondary hover:text-text-primary rounded-xl font-medium transition-colors">
            <Bell className="w-5 h-5" />
            <span>Alerts</span>
          </button>
        </nav>
        
        <div className="p-4 border-t border-border">
          <button 
            onClick={handleLogout}
            className="w-full flex items-center space-x-3 px-4 py-3 text-accent-red hover:bg-accent-red/10 rounded-xl font-medium transition-colors"
          >
            <LogOut className="w-5 h-5" />
            <span>Logout</span>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto p-4 sm:p-8 bg-secondary/30">
        <h1 className="text-2xl font-bold text-text-primary mb-6">Portfolio Dashboard</h1>
        
        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-primary p-6 rounded-2xl border border-border shadow-sm">
            <p className="text-sm text-text-secondary mb-2">Total Value (LKR)</p>
            <p className="text-3xl font-bold text-text-primary">Rs {portfolio.totalValue.toLocaleString()}</p>
          </div>
          <div className="bg-primary p-6 rounded-2xl border border-border shadow-sm">
            <p className="text-sm text-text-secondary mb-2">Today's P&L</p>
            <p className={`text-3xl font-bold flex items-center ${isDayPositive ? 'text-accent-green' : 'text-accent-red'}`}>
              {isDayPositive ? <TrendingUp className="w-6 h-6 mr-2" /> : <TrendingDown className="w-6 h-6 mr-2" />}
              {isDayPositive ? '+' : ''}{portfolio.dayChange.toLocaleString()} 
              <span className="text-lg ml-2 opacity-80">({isDayPositive ? '+' : ''}{portfolio.dayChangePercent}%)</span>
            </p>
          </div>
          <div className="bg-primary p-6 rounded-2xl border border-border shadow-sm flex flex-col justify-center">
            <p className="text-sm text-text-secondary mb-2">Active Holdings</p>
            <p className="text-3xl font-bold text-text-primary">{portfolio.holdings.length}</p>
          </div>
        </div>

        {/* Portfolio Holdings Section */}
        <div className="bg-primary border border-border rounded-2xl shadow-sm overflow-hidden mb-8">
          <div className="p-6 border-b border-border flex justify-between items-center">
            <h2 className="text-lg font-bold text-text-primary">My Holdings</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="bg-secondary/50 text-text-secondary text-sm border-b border-border">
                <tr>
                  <th className="px-6 py-3 font-medium">Symbol</th>
                  <th className="px-6 py-3 font-medium text-right">Shares</th>
                  <th className="px-6 py-3 font-medium text-right">Avg. Cost</th>
                  <th className="px-6 py-3 font-medium text-right">Current Price</th>
                  <th className="px-6 py-3 font-medium text-right">Total Value</th>
                  <th className="px-6 py-3 font-medium text-right">Return</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {portfolio.holdings.map(item => {
                  const totalValue = item.shares * item.currentPrice;
                  const totalCost = item.shares * item.avgCost;
                  const returnAbs = totalValue - totalCost;
                  const returnPct = (returnAbs / totalCost) * 100;
                  const isPositive = returnAbs >= 0;

                  return (
                    <tr key={item.ticker} className="hover:bg-secondary/30">
                      <td className="px-6 py-4">
                        <div className="font-bold text-text-primary">{item.ticker}</div>
                        <div className="text-xs text-text-secondary">{item.name}</div>
                      </td>
                      <td className="px-6 py-4 text-right text-text-primary font-medium">
                        {item.shares.toLocaleString()}
                      </td>
                      <td className="px-6 py-4 text-right text-text-secondary">
                        Rs {item.avgCost.toFixed(2)}
                      </td>
                      <td className="px-6 py-4 text-right text-text-primary font-medium">
                        Rs {item.currentPrice.toFixed(2)}
                      </td>
                      <td className="px-6 py-4 text-right text-text-primary font-bold">
                        Rs {totalValue.toLocaleString()}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <span className={`inline-flex items-center text-sm font-medium ${isPositive ? 'text-accent-green' : 'text-accent-red'}`}>
                          {isPositive ? '+' : ''}{returnAbs.toLocaleString()} ({isPositive ? '+' : ''}{returnPct.toFixed(2)}%)
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Watchlist Section */}
        <div className="bg-primary border border-border rounded-2xl shadow-sm overflow-hidden mb-8">
          <div className="p-6 border-b border-border flex justify-between items-center">
            <h2 className="text-lg font-bold text-text-primary">My Watchlist</h2>
            <button className="text-sm font-medium text-accent-green hover:underline">Add Symbol +</button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="bg-secondary/50 text-text-secondary text-sm border-b border-border">
                <tr>
                  <th className="px-6 py-3 font-medium">Symbol</th>
                  <th className="px-6 py-3 font-medium text-right">Target Price</th>
                  <th className="px-6 py-3 font-medium text-center">Alerts</th>
                  <th className="px-6 py-3 font-medium text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {watchlist.map(item => (
                  <tr key={item.ticker} className="hover:bg-secondary/30">
                    <td className="px-6 py-4">
                      <div className="font-bold text-text-primary">{item.ticker}</div>
                      <div className="text-xs text-text-secondary">{item.name}</div>
                    </td>
                    <td className="px-6 py-4 text-right text-text-primary font-medium">
                      {item.targetPrice !== null ? `Rs ${item.targetPrice.toFixed(2)}` : '-'}
                    </td>
                    <td className="px-6 py-4 text-center">
                      <button className={`p-2 rounded-full transition-colors ${item.alertEnabled ? 'bg-accent-green/10 text-accent-green' : 'bg-secondary text-text-secondary'}`}>
                        <Bell className="w-4 h-4" />
                      </button>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button 
                        onClick={() => navigate(`/analyzer?ticker=${item.ticker}`)}
                        className="text-sm text-text-secondary hover:text-accent-green"
                      >
                        Trade
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

      </main>
    </div>
  );
};
