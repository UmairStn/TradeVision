import React from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';
import type { StockQuote } from '../types/stock';

interface StockCardProps {
  quote: StockQuote;
  onClick?: () => void;
  selected?: boolean;
}

export const StockCard: React.FC<StockCardProps> = ({ quote, onClick, selected }) => {
  const isPositive = quote.change >= 0;

  return (
    <div
      onClick={onClick}
      className={`p-4 rounded-xl border transition-all duration-200 cursor-pointer 
        ${selected 
          ? 'border-accent-green bg-accent-green/5 shadow-md' 
          : 'border-border bg-secondary hover:border-text-secondary hover:shadow-sm'
        }`}
    >
      <div className="flex justify-between items-start mb-2">
        <div>
          <h3 className="font-bold text-lg text-text-primary">{quote.ticker}</h3>
          <p className="text-xs text-text-secondary truncate max-w-[120px]" title={quote.name}>
            {quote.name}
          </p>
        </div>
        <div className={`p-1.5 rounded-lg ${isPositive ? 'bg-accent-green/10 text-accent-green' : 'bg-accent-red/10 text-accent-red'}`}>
          {isPositive ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
        </div>
      </div>
      
      <div className="mt-4 flex items-end justify-between">
        <div>
          <p className="text-xs text-text-secondary mb-1">Price</p>
          <p className="font-semibold text-xl text-text-primary">
            Rs. {quote.price.toFixed(2)}
          </p>
        </div>
        <div className="text-right">
          <p className={`font-medium ${isPositive ? 'text-accent-green' : 'text-accent-red'}`}>
            {isPositive ? '+' : ''}{quote.change.toFixed(2)} ({isPositive ? '+' : ''}{quote.changePercent.toFixed(2)}%)
          </p>
        </div>
      </div>
    </div>
  );
};
