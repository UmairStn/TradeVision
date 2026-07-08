import React from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';
import type { StockQuote } from '../types/stock';

interface MarqueeTickerProps {
  items: StockQuote[];
}

export const MarqueeTicker: React.FC<MarqueeTickerProps> = ({ items }) => {
  if (!items || items.length === 0) return null;

  return (
    <div className="w-full bg-secondary border-y border-border overflow-hidden py-2 relative">
      <div className="flex w-max animate-marquee hover:pause whitespace-nowrap">
        {/* Render items twice for infinite loop effect */}
        {[...items, ...items].map((quote, idx) => {
          const isPositive = quote.change >= 0;
          return (
            <div
              key={`${quote.ticker}-${idx}`}
              className="flex items-center space-x-3 px-8 border-r border-border last:border-r-0"
            >
              <span className="font-semibold text-text-primary">{quote.ticker}</span>
              <span className="text-text-primary">Rs {quote.price.toFixed(2)}</span>
              <div className={`flex items-center text-sm font-medium ${isPositive ? 'text-accent-green' : 'text-accent-red'}`}>
                {isPositive ? <TrendingUp className="w-3 h-3 mr-1" /> : <TrendingDown className="w-3 h-3 mr-1" />}
                <span>{quote.changePercent.toFixed(2)}%</span>
              </div>
            </div>
          );
        })}
      </div>
      <style>{`
        @keyframes marquee {
          0% { transform: translateX(0); }
          100% { transform: translateX(-50%); }
        }
        .animate-marquee {
          animation: marquee 30s linear infinite;
        }
        .animate-marquee:hover {
          animation-play-state: paused;
        }
      `}</style>
    </div>
  );
};
