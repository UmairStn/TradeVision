import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { BrainCircuit, BellRing, PieChart, ArrowRight } from 'lucide-react';
import { MarqueeTicker } from '../components/MarqueeTicker';
import { TradingViewWidget } from '../components/TradingViewWidget';
import { useStockContext } from '../context/StockContext';
import type { StockQuote } from '../types/stock';
import { searchStocks } from '../services/api';

export const Home: React.FC = () => {
  const { marketSummary } = useStockContext();
  const [tickerItems, setTickerItems] = useState<StockQuote[]>([]);

  useEffect(() => {
    // Load a few stocks for the ticker
    searchStocks('').then(setTickerItems);
  }, []);

  return (
    <div className="flex flex-col min-h-[calc(100vh-64px)]">
      {/* Hero Section */}
      <section className="relative overflow-hidden bg-primary py-20 lg:py-32 flex-grow flex flex-col justify-center">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-accent-green/10 via-primary to-primary pointer-events-none" />
        
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h1 className="text-5xl md:text-6xl font-extrabold text-text-primary tracking-tight mb-6">
            Predict the Future of <br className="hidden md:block" />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-accent-green to-emerald-500">
              Sri Lankan Stocks
            </span>
          </h1>
          <p className="mt-4 max-w-2xl mx-auto text-xl text-text-secondary mb-10">
            Advanced AI-powered analysis for the Colombo Stock Exchange. 
            Make smarter decisions with real-time predictions and portfolio tracking.
          </p>
          
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              to="/register"
              className="inline-flex justify-center items-center px-8 py-4 border border-transparent text-lg font-medium rounded-xl text-white bg-accent-green hover:bg-accent-green/90 shadow-lg shadow-accent-green/30 transition-all duration-300"
            >
              Get Started
              <ArrowRight className="ml-2 w-5 h-5" />
            </Link>
            <Link
              to="/top-stocks"
              className="inline-flex justify-center items-center px-8 py-4 border-2 border-border text-lg font-medium rounded-xl text-text-primary hover:border-text-secondary transition-all duration-300 bg-secondary/50 backdrop-blur"
            >
              Explore Stocks
            </Link>
          </div>
        </div>
      </section>

      {/* Live Ticker */}
      <MarqueeTicker items={tickerItems} />

      {/* Live Chart Section */}
      <section className="py-16 bg-primary border-t border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-10">
            <h2 className="text-3xl font-bold text-text-primary tracking-tight">
              Live Market Tracking
            </h2>
            <p className="mt-4 text-lg text-text-secondary max-w-2xl mx-auto">
              Stay ahead of the market with our live, interactive chart for Colombo Stock Exchange's leading stocks.
            </p>
          </div>
          
          <div className="bg-secondary rounded-2xl border border-border p-4 shadow-xl shadow-secondary/50 h-[500px] md:h-[600px] overflow-hidden flex flex-col">
            <TradingViewWidget />
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 bg-secondary">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-text-primary">Why Choose TradeVision?</h2>
            <p className="mt-4 text-text-secondary">Powerful tools designed for the modern investor.</p>
          </div>
          
          <div className="grid md:grid-cols-3 gap-8">
            {/* Feature 1 */}
            <div className="bg-primary p-8 rounded-2xl border border-border hover:shadow-xl transition-shadow duration-300">
              <div className="w-14 h-14 bg-accent-green/10 rounded-xl flex items-center justify-center mb-6">
                <BrainCircuit className="w-8 h-8 text-accent-green" />
              </div>
              <h3 className="text-xl font-bold text-text-primary mb-3">AI Predictions</h3>
              <p className="text-text-secondary">
                Our models analyze historical data and market sentiment to forecast short-term price movements with high confidence.
              </p>
            </div>

            {/* Feature 2 */}
            <div className="bg-primary p-8 rounded-2xl border border-border hover:shadow-xl transition-shadow duration-300">
              <div className="w-14 h-14 bg-blue-500/10 rounded-xl flex items-center justify-center mb-6">
                <BellRing className="w-8 h-8 text-blue-500" />
              </div>
              <h3 className="text-xl font-bold text-text-primary mb-3">Smart Alerts</h3>
              <p className="text-text-secondary">
                Never miss an opportunity. Set custom price targets and get instant notifications when your conditions are met.
              </p>
            </div>

            {/* Feature 3 */}
            <div className="bg-primary p-8 rounded-2xl border border-border hover:shadow-xl transition-shadow duration-300">
              <div className="w-14 h-14 bg-purple-500/10 rounded-xl flex items-center justify-center mb-6">
                <PieChart className="w-8 h-8 text-purple-500" />
              </div>
              <h3 className="text-xl font-bold text-text-primary mb-3">Portfolio Tracking</h3>
              <p className="text-text-secondary">
                Monitor your investments in real-time. View detailed performance metrics and balance your portfolio effectively.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Stats Bar */}
      <section className="py-12 border-t border-border bg-primary">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 md:grid-cols-3 gap-8 text-center divide-x divide-border">
            <div>
              <p className="text-4xl font-extrabold text-text-primary mb-2">250+</p>
              <p className="text-text-secondary font-medium">Stocks Tracked</p>
            </div>
            <div>
              <p className="text-4xl font-extrabold text-text-primary mb-2">98%</p>
              <p className="text-text-secondary font-medium">System Uptime</p>
            </div>
            <div className="col-span-2 md:col-span-1 border-t md:border-t-0 md:border-l border-border pt-8 md:pt-0">
              <p className="text-4xl font-extrabold text-text-primary mb-2">5,000+</p>
              <p className="text-text-secondary font-medium">Active Users</p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};
