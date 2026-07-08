import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Search, Brain, TrendingUp, TrendingDown, Loader2, AlertCircle } from 'lucide-react';
import { StockCard } from '../components/StockCard';
import { LiveChart } from '../components/LiveChart';
import type { StockQuote, StockPrice, PredictionResult } from '../types/stock';
import { searchStocks, fetchStockQuote, fetchStockHistory, fetchPrediction } from '../services/api';

export const StockAnalyzer: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<StockQuote[]>([]);
  const [selectedStock, setSelectedStock] = useState<StockQuote | null>(null);
  const [chartData, setChartData] = useState<StockPrice[]>([]);
  const [prediction, setPrediction] = useState<PredictionResult | null>(null);
  
  const [isSearching, setIsSearching] = useState(false);
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);
  const [timeRange, setTimeRange] = useState<number>(30); // days

  // Handle Search
  useEffect(() => {
    const timer = setTimeout(() => {
      if (searchQuery.trim().length > 0) {
        setIsSearching(true);
        searchStocks(searchQuery).then(results => {
          setSearchResults(results);
          setIsSearching(false);
        });
      } else {
        // Load default popular stocks when search is empty
        searchStocks('').then(setSearchResults);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Handle Selection & Data Fetching
  const loadStockDetails = async (ticker: string) => {
    setIsLoadingDetails(true);
    try {
      const [quote, history, pred] = await Promise.all([
        fetchStockQuote(ticker),
        fetchStockHistory(ticker, timeRange),
        fetchPrediction(ticker)
      ]);
      setSelectedStock(quote);
      setChartData(history);
      setPrediction(pred);
    } catch (error) {
      console.error("Failed to load stock details", error);
    } finally {
      setIsLoadingDetails(false);
    }
  };

  useEffect(() => {
    const tickerParam = searchParams.get('ticker') || 'JKH.N0000';
    loadStockDetails(tickerParam);
  }, [searchParams, timeRange]);

  // loadStockDetails was moved up

  const handleSelectStock = (ticker: string) => {
    setSearchParams({ ticker });
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 h-[calc(100vh-64px)] flex flex-col md:flex-row gap-6">
      
      {/* Left Sidebar - Search & List */}
      <div className="w-full md:w-1/3 lg:w-1/4 flex flex-col h-full bg-primary border border-border rounded-2xl overflow-hidden shadow-sm">
        <div className="p-4 border-b border-border bg-secondary/50">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-secondary" />
            <input
              type="text"
              placeholder="Search CSE stocks..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-primary border border-border rounded-xl text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-green focus:border-transparent transition-all"
            />
          </div>
        </div>
        
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {isSearching ? (
            <div className="flex justify-center p-8">
              <Loader2 className="w-6 h-6 animate-spin text-text-secondary" />
            </div>
          ) : searchResults.length > 0 ? (
            searchResults.map(quote => (
              <StockCard
                key={quote.ticker}
                quote={quote}
                selected={selectedStock?.ticker === quote.ticker}
                onClick={() => handleSelectStock(quote.ticker)}
              />
            ))
          ) : (
            <p className="text-center text-text-secondary mt-8">No stocks found.</p>
          )}
        </div>
      </div>

      {/* Right Main Content - Chart & Prediction */}
      <div className="w-full md:w-2/3 lg:w-3/4 flex flex-col h-full space-y-6 overflow-y-auto pb-8">
        
        {/* Main Chart Card */}
        <div className="bg-primary border border-border rounded-2xl p-6 shadow-sm">
          {isLoadingDetails || !selectedStock ? (
            <div className="h-[500px] flex items-center justify-center">
              <Loader2 className="w-8 h-8 animate-spin text-accent-green" />
            </div>
          ) : (
            <>
              {/* Header */}
              <div className="flex justify-between items-start mb-6">
                <div>
                  <h1 className="text-3xl font-bold text-text-primary">{selectedStock.name}</h1>
                  <p className="text-text-secondary">{selectedStock.ticker} • CSE</p>
                </div>
                <div className="text-right">
                  <p className="text-3xl font-bold text-text-primary">Rs {selectedStock.price.toFixed(2)}</p>
                  <p className={`font-medium text-lg flex items-center justify-end ${selectedStock.change >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
                    {selectedStock.change >= 0 ? <TrendingUp className="w-5 h-5 mr-1" /> : <TrendingDown className="w-5 h-5 mr-1" />}
                    {Math.abs(selectedStock.change).toFixed(2)} ({Math.abs(selectedStock.changePercent).toFixed(2)}%)
                  </p>
                </div>
              </div>

              {/* Time Range Selector */}
              <div className="flex space-x-2 mb-4">
                {[7, 30, 90].map(days => (
                  <button
                    key={days}
                    onClick={() => setTimeRange(days)}
                    className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                      timeRange === days 
                        ? 'bg-text-primary text-primary' 
                        : 'bg-secondary text-text-secondary hover:bg-border'
                    }`}
                  >
                    {days === 7 ? '1W' : days === 30 ? '1M' : '3M'}
                  </button>
                ))}
              </div>

              {/* Chart */}
              <LiveChart data={chartData} ticker={selectedStock.ticker} />
            </>
          )}
        </div>

        {/* AI Prediction Panel */}
        {prediction && !isLoadingDetails && (
          <div className="bg-gradient-to-br from-primary to-secondary border border-border rounded-2xl p-6 shadow-sm relative overflow-hidden">
            <div className="absolute top-0 right-0 w-32 h-32 bg-accent-green/5 rounded-full -translate-y-1/2 translate-x-1/2 pointer-events-none blur-2xl" />
            
            <div className="flex items-center space-x-2 mb-6">
              <Brain className="w-6 h-6 text-accent-green" />
              <h2 className="text-xl font-bold text-text-primary">AI Prediction Analysis</h2>
              <span className="ml-4 px-2 py-1 text-xs font-medium bg-blue-500/10 text-blue-500 rounded-md flex items-center">
                <AlertCircle className="w-3 h-3 mr-1" /> Prototype Estimate
              </span>
            </div>

            <div className="grid md:grid-cols-3 gap-6">
              <div className="bg-primary/50 p-4 rounded-xl border border-border">
                <p className="text-sm text-text-secondary mb-1">Next Day Predicted Price</p>
                <p className="text-2xl font-bold text-text-primary">Rs {prediction.nextDayPrice.toFixed(2)}</p>
                <p className={`text-sm mt-1 ${prediction.trend === 'up' ? 'text-accent-green' : 'text-accent-red'}`}>
                  {prediction.trend === 'up' ? 'Expected Uptrend' : 'Expected Downtrend'}
                </p>
              </div>

              <div className="bg-primary/50 p-4 rounded-xl border border-border md:col-span-2">
                <div className="flex justify-between items-end mb-2">
                  <p className="text-sm text-text-secondary">Model Confidence Score</p>
                  <p className="text-xl font-bold text-text-primary">{prediction.confidence}%</p>
                </div>
                <div className="w-full h-3 bg-border rounded-full overflow-hidden">
                  <div 
                    className={`h-full rounded-full transition-all duration-1000 ${
                      prediction.confidence > 75 ? 'bg-accent-green' : 
                      prediction.confidence > 50 ? 'bg-yellow-500' : 'bg-accent-red'
                    }`}
                    style={{ width: `${prediction.confidence}%` }}
                  />
                </div>
                <p className="text-xs text-text-secondary mt-2">
                  Generated based on technical indicators and historical volatility at {new Date(prediction.generatedAt).toLocaleTimeString()}.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

    </div>
  );
};
