import React, { useEffect, useState } from 'react';
import type { UserPortfolio, WatchlistItem, StockQuote, PortfolioHolding } from '../types/stock';
import { fetchPortfolio, fetchWatchlist, addToPortfolio, addToWatchlist, removeFromPortfolio, removeFromWatchlist, searchStocks } from '../services/api';
import { Wallet, TrendingUp, TrendingDown, Layers, Bell, LogOut, Plus, Trash2, X, List } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../lib/supabase';
import { useStockContext } from '../context/StockContext';

export const Dashboard: React.FC = () => {
  const [portfolio, setPortfolio] = useState<UserPortfolio | null>(null);
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [isWatchlistModalOpen, setIsWatchlistModalOpen] = useState(false);
  const [isPortfolioModalOpen, setIsPortfolioModalOpen] = useState(false);
  const [isDetailsModalOpen, setIsDetailsModalOpen] = useState(false);
  const [selectedHolding, setSelectedHolding] = useState<PortfolioHolding | null>(null);
  const [newSymbol, setNewSymbol] = useState('');
  const [newShares, setNewShares] = useState('');
  const [newPrice, setNewPrice] = useState('');
  const [newDate, setNewDate] = useState(new Date().toISOString().split('T')[0]);
  const [transactionType, setTransactionType] = useState<'buy' | 'sell'>('buy');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [userProfile, setUserProfile] = useState({ name: '', initials: '' });
  const [searchResults, setSearchResults] = useState<StockQuote[]>([]);
  const [showResults, setShowResults] = useState(false);
  const navigate = useNavigate();
  const { marketSummary } = useStockContext();

  const loadData = async () => {
    const { data: { session } } = await supabase.auth.getSession();
    if (!session) {
      navigate('/login');
      return;
    }

    const email = session.user.email || '';
    const name = session.user.user_metadata?.full_name || email.split('@')[0] || 'User';
    const initials = name.substring(0, 2).toUpperCase();
    setUserProfile({ name, initials });
    
    try {
      const [pData, wData] = await Promise.all([
        fetchPortfolio(),
        fetchWatchlist()
      ]);
      setPortfolio(pData);
      setWatchlist(wData);
    } catch (error) {
      console.error('Error loading dashboard data:', error);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    let stale = false;
    if (newSymbol.trim().length > 0 && showResults) {
      searchStocks(newSymbol).then(results => {
        if (!stale) setSearchResults(results);
      });
    } else {
      setSearchResults([]);
    }
    return () => { stale = true; };
  }, [newSymbol, showResults]);

  const handleLogout = () => {
    navigate('/login');
  };

  const handleAddWatchlist = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newSymbol) return;
    setIsSubmitting(true);
    try {
      await addToWatchlist(newSymbol.toUpperCase());
      setIsWatchlistModalOpen(false);
      setNewSymbol('');
      loadData();
    } catch (err) {
      console.error(err);
      alert('Failed to add to watchlist. Maybe it already exists?');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleAddPortfolio = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newSymbol || !newShares || !newPrice) return;
    setIsSubmitting(true);
    try {
      const sharesNum = parseInt(newShares, 10);
      const finalShares = transactionType === 'sell' ? -sharesNum : sharesNum;

      await addToPortfolio(
        newSymbol.toUpperCase(),
        finalShares,
        parseFloat(newPrice),
        newDate
      );
      setIsPortfolioModalOpen(false);
      setNewSymbol('');
      setNewShares('');
      setNewPrice('');
      setNewDate(new Date().toISOString().split('T')[0]);
      setTransactionType('buy');
      loadData();
    } catch (err) {
      console.error(err);
      alert('Failed to add to portfolio.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRemoveWatchlist = async (id: string) => {
    try {
      await removeFromWatchlist(id);
      loadData();
    } catch (err) {
      console.error(err);
    }
  };

  const handleRemoveTransaction = async (id: string, ticker: string) => {
    try {
      await removeFromPortfolio(id);
      
      // Update local state for the modal
      if (selectedHolding) {
        const updatedTransactions = selectedHolding.transactions.filter(t => t.id !== id);
        if (updatedTransactions.length === 0) {
          setIsDetailsModalOpen(false); // Close if empty
        } else {
          setSelectedHolding({
            ...selectedHolding,
            transactions: updatedTransactions
          });
        }
      }
      
      loadData();
    } catch (err) {
      console.error(err);
      alert('Failed to remove transaction.');
    }
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
    <div className="flex min-h-[calc(100vh-64px)]">
      
      {/* Sidebar */}
      <aside className="w-64 flex-shrink-0 border-r border-border bg-primary hidden md:flex flex-col sticky top-16 h-[calc(100vh-64px)]">
        <div className="p-6 border-b border-border text-center">
          <div className="w-16 h-16 mx-auto bg-gradient-to-tr from-accent-green to-emerald-400 rounded-full flex items-center justify-center text-white text-xl font-bold shadow-md">
            {userProfile.initials}
          </div>
          <h2 className="mt-4 font-bold text-text-primary text-lg truncate px-2">{userProfile.name}</h2>
          <p className="text-sm text-text-secondary">TradeVision Member</p>
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
            className="w-full flex items-center justify-center space-x-2 px-4 py-2 text-text-secondary hover:text-accent-red hover:bg-accent-red/10 rounded-lg font-medium transition-colors"
          >
            <LogOut className="w-4 h-4" />
            <span>Log out</span>
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
            <button 
              onClick={() => setIsPortfolioModalOpen(true)}
              className="flex items-center text-sm font-medium text-accent-green hover:underline"
            >
              <Plus className="w-4 h-4 mr-1" /> Add Position
            </button>
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
                  <th className="px-6 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {portfolio.holdings.map(item => {
                  const totalValue = item.totalShares * item.currentPrice;
                  const totalCost = item.totalShares * item.avgCost;
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
                        {item.totalShares.toLocaleString()}
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
                      <td className="px-6 py-4 text-right">
                        <button 
                          onClick={() => {
                            setSelectedHolding(item);
                            setIsDetailsModalOpen(true);
                          }}
                          className="text-text-secondary hover:text-accent-green transition-colors flex items-center justify-end w-full space-x-1"
                        >
                          <List className="w-4 h-4" />
                          <span className="text-xs font-medium">Details</span>
                        </button>
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
            <button 
              onClick={() => setIsWatchlistModalOpen(true)}
              className="flex items-center text-sm font-medium text-accent-green hover:underline"
            >
              <Plus className="w-4 h-4 mr-1" /> Add Symbol
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="bg-secondary/50 text-text-secondary text-sm border-b border-border">
                <tr>
                  <th className="px-6 py-3 font-medium">Symbol</th>
                  <th className="px-6 py-3 font-medium text-right">Current Price</th>
                  <th className="px-6 py-3 font-medium text-right">Day Change</th>
                  <th className="px-6 py-3 font-medium text-center">Alerts</th>
                  <th className="px-6 py-3 font-medium text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {watchlist.map(item => {
                  const currentPrice = item.currentPrice;
                  const dayChange = item.dayChange;
                  const dayChangePct = item.dayChangePct;
                  const isPositive = dayChange ? dayChange >= 0 : false;

                  return (
                    <tr key={item.ticker} className="hover:bg-secondary/30">
                      <td className="px-6 py-4">
                        <div className="font-bold text-text-primary">{item.ticker}</div>
                        <div className="text-xs text-text-secondary">{item.name}</div>
                      </td>
                      <td className="px-6 py-4 text-right text-text-primary font-medium">
                        {currentPrice ? `Rs ${currentPrice.toFixed(2)}` : '-'}
                      </td>
                      <td className="px-6 py-4 text-right">
                        {dayChange && dayChangePct ? (
                          <span className={`inline-flex items-center text-sm font-medium ${isPositive ? 'text-accent-green' : 'text-accent-red'}`}>
                            {isPositive ? '+' : ''}{dayChange.toFixed(2)} ({isPositive ? '+' : ''}{dayChangePct.toFixed(2)}%)
                          </span>
                        ) : '-'}
                      </td>
                      <td className="px-6 py-4 text-center">
                        <button className={`p-2 rounded-full transition-colors ${item.alertEnabled ? 'bg-accent-green/10 text-accent-green' : 'bg-secondary text-text-secondary'}`}>
                          <Bell className="w-4 h-4" />
                        </button>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <div className="flex items-center justify-end space-x-4">
                          <button 
                            onClick={() => navigate(`/analyzer?ticker=${item.ticker}`)}
                            className="text-sm text-text-secondary hover:text-accent-green"
                          >
                            Trade
                          </button>
                          <button 
                            onClick={() => item.id && handleRemoveWatchlist(item.id)}
                            className="text-text-secondary hover:text-accent-red transition-colors"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

      </main>

      {/* Details Modal */}
      {isDetailsModalOpen && selectedHolding && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-primary border border-border rounded-2xl w-full max-w-2xl shadow-xl">
            <div className="p-6 border-b border-border flex justify-between items-center">
              <div>
                <h2 className="text-xl font-bold text-text-primary">{selectedHolding.ticker} Transactions</h2>
                <p className="text-sm text-text-secondary">{selectedHolding.name}</p>
              </div>
              <button onClick={() => setIsDetailsModalOpen(false)} className="text-text-secondary hover:text-text-primary">
                <X className="w-6 h-6" />
              </button>
            </div>
            <div className="p-6 max-h-[60vh] overflow-y-auto">
              <table className="w-full text-left">
                <thead className="text-text-secondary text-sm border-b border-border">
                  <tr>
                    <th className="pb-3 font-medium">Type</th>
                    <th className="pb-3 font-medium">Date</th>
                    <th className="pb-3 font-medium text-right">Shares</th>
                    <th className="pb-3 font-medium text-right">Price</th>
                    <th className="pb-3 font-medium text-right">Total Spent</th>
                    <th className="pb-3 font-medium text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {selectedHolding.transactions.map(t => (
                    <tr key={t.id}>
                      <td className="py-4 text-text-primary">
                        <span className={`inline-block px-2 py-1 text-xs rounded font-bold ${t.shares >= 0 ? 'bg-accent-green/20 text-accent-green' : 'bg-accent-red/20 text-accent-red'}`}>
                          {t.shares >= 0 ? 'Buy' : 'Sell'}
                        </span>
                      </td>
                      <td className="py-4 text-text-primary">{t.dateAcquired}</td>
                      <td className="py-4 text-right text-text-primary">{Math.abs(t.shares).toLocaleString()}</td>
                      <td className="py-4 text-right text-text-secondary">Rs {t.price.toFixed(2)}</td>
                      <td className="py-4 text-right text-text-primary font-medium">Rs {(Math.abs(t.shares) * t.price).toLocaleString()}</td>
                      <td className="py-4 text-right">
                        <button 
                          onClick={() => handleRemoveTransaction(t.id, selectedHolding.ticker)}
                          className="text-text-secondary hover:text-accent-red transition-colors inline-block"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Watchlist Modal */}
      {isWatchlistModalOpen && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-primary border border-border rounded-2xl w-full max-w-md shadow-xl">
            <div className="p-6 border-b border-border flex justify-between items-center">
              <h2 className="text-xl font-bold text-text-primary">Add to Watchlist</h2>
              <button onClick={() => setIsWatchlistModalOpen(false)} className="text-text-secondary hover:text-text-primary">
                <X className="w-6 h-6" />
              </button>
            </div>
            <form onSubmit={handleAddWatchlist} className="p-6">
              <div className="mb-4">
                <label className="block text-sm font-medium text-text-secondary mb-2">Stock Symbol</label>
                <div className="relative">
                  <input
                    type="text"
                    required
                    placeholder="e.g. JKH.N0000"
                    value={newSymbol}
                    onChange={(e) => {
                      setNewSymbol(e.target.value.toUpperCase());
                      setShowResults(true);
                    }}
                    onFocus={() => setShowResults(true)}
                    onBlur={() => setTimeout(() => setShowResults(false), 200)}
                    className="w-full px-4 py-2 bg-secondary border border-border rounded-lg text-text-primary focus:outline-none focus:border-accent-green uppercase"
                  />
                  {showResults && searchResults.length > 0 && (
                    <div className="absolute z-10 w-full mt-1 bg-primary border border-border rounded-lg shadow-lg max-h-48 overflow-y-auto">
                      {searchResults.map(result => (
                        <button
                          key={result.ticker}
                          type="button"
                          onMouseDown={(e) => {
                            e.preventDefault(); // Prevent blur
                            setNewSymbol(result.ticker);
                            setShowResults(false);
                          }}
                          className="w-full text-left px-4 py-2 hover:bg-secondary flex justify-between items-center transition-colors"
                        >
                          <span className="font-bold text-text-primary">{result.ticker}</span>
                          <span className="text-xs text-text-secondary truncate ml-2">{result.name}</span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full py-3 bg-accent-green text-white rounded-lg font-bold hover:bg-accent-green/90 transition-colors disabled:opacity-50"
              >
                {isSubmitting ? 'Adding...' : 'Add Symbol'}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Portfolio Modal */}
      {isPortfolioModalOpen && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-primary border border-border rounded-2xl w-full max-w-md shadow-xl">
            <div className="p-6 border-b border-border flex justify-between items-center">
              <h2 className="text-xl font-bold text-text-primary">Add Portfolio Position</h2>
              <button onClick={() => setIsPortfolioModalOpen(false)} className="text-text-secondary hover:text-text-primary">
                <X className="w-6 h-6" />
              </button>
            </div>
            <form onSubmit={handleAddPortfolio} className="p-6 space-y-4">
              <div className="flex gap-4 mb-2">
                <button
                  type="button"
                  onClick={() => setTransactionType('buy')}
                  className={`flex-1 py-2 rounded-lg font-bold transition-colors ${
                    transactionType === 'buy' 
                      ? 'bg-accent-green text-white' 
                      : 'bg-secondary text-text-secondary hover:bg-secondary/80'
                  }`}
                >
                  Buy
                </button>
                <button
                  type="button"
                  onClick={() => setTransactionType('sell')}
                  className={`flex-1 py-2 rounded-lg font-bold transition-colors ${
                    transactionType === 'sell' 
                      ? 'bg-accent-red text-white' 
                      : 'bg-secondary text-text-secondary hover:bg-secondary/80'
                  }`}
                >
                  Sell
                </button>
              </div>
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-2">Stock Symbol</label>
                <div className="relative">
                  <input
                    type="text"
                    required
                    placeholder="e.g. JKH.N0000"
                    value={newSymbol}
                    onChange={(e) => {
                      setNewSymbol(e.target.value.toUpperCase());
                      setShowResults(true);
                    }}
                    onFocus={() => setShowResults(true)}
                    onBlur={() => setTimeout(() => setShowResults(false), 200)}
                    className="w-full px-4 py-2 bg-secondary border border-border rounded-lg text-text-primary focus:outline-none focus:border-accent-green uppercase"
                  />
                  {showResults && searchResults.length > 0 && (
                    <div className="absolute z-10 w-full mt-1 bg-primary border border-border rounded-lg shadow-lg max-h-48 overflow-y-auto">
                      {searchResults.map(result => (
                        <button
                          key={result.ticker}
                          type="button"
                          onMouseDown={(e) => {
                            e.preventDefault(); // Prevent blur
                            setNewSymbol(result.ticker);
                            if (result.price) {
                              setNewPrice(result.price.toString());
                            }
                            setShowResults(false);
                          }}
                          className="w-full text-left px-4 py-2 hover:bg-secondary flex justify-between items-center transition-colors"
                        >
                          <span className="font-bold text-text-primary">{result.ticker}</span>
                          <span className="text-xs text-text-secondary truncate ml-2">{result.name}</span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-2">Number of Shares</label>
                <input
                  type="number"
                  required
                  min="1"
                  placeholder="100"
                  value={newShares}
                  onChange={(e) => setNewShares(e.target.value)}
                  className="w-full px-4 py-2 bg-secondary border border-border rounded-lg text-text-primary focus:outline-none focus:border-accent-green"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-2">Average Price (Rs)</label>
                <input
                  type="number"
                  required
                  min="0.01"
                  step="0.01"
                  placeholder="150.50"
                  value={newPrice}
                  onChange={(e) => setNewPrice(e.target.value)}
                  className="w-full px-4 py-2 bg-secondary border border-border rounded-lg text-text-primary focus:outline-none focus:border-accent-green"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-2">Purchase Date</label>
                <input
                  type="date"
                  required
                  max={new Date().toISOString().split('T')[0]}
                  value={newDate}
                  onChange={(e) => setNewDate(e.target.value)}
                  className="w-full px-4 py-2 bg-secondary border border-border rounded-lg text-text-primary focus:outline-none focus:border-accent-green"
                />
              </div>
              <button
                type="submit"
                disabled={isSubmitting}
                className={`w-full py-3 text-white rounded-lg font-bold transition-colors disabled:opacity-50 mt-2 ${
                  transactionType === 'buy' ? 'bg-accent-green hover:bg-accent-green/90' : 'bg-accent-red hover:bg-accent-red/90'
                }`}
              >
                {isSubmitting ? (transactionType === 'buy' ? 'Adding...' : 'Selling...') : (transactionType === 'buy' ? 'Add Position' : 'Log Sell')}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
