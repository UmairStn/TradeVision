import React, { createContext, useContext, useEffect, useState } from 'react';
import type { MarketSummary } from '../types/stock';
import { fetchMarketSummary } from '../services/api';

interface StockContextType {
  selectedTicker: string;
  setSelectedTicker: (ticker: string) => void;
  marketSummary: MarketSummary | null;
  isLoading: boolean;
  error: string | null;
}

const StockContext = createContext<StockContextType | undefined>(undefined);

export const StockProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [selectedTicker, setSelectedTicker] = useState<string>('JKH.N0000');
  const [marketSummary, setMarketSummary] = useState<MarketSummary | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadMarketSummary = async () => {
      try {
        setIsLoading(true);
        const data = await fetchMarketSummary();
        setMarketSummary(data);
      } catch (err) {
        setError('Failed to fetch market summary');
      } finally {
        setIsLoading(false);
      }
    };

    loadMarketSummary();
  }, []);

  return (
    <StockContext.Provider value={{ selectedTicker, setSelectedTicker, marketSummary, isLoading, error }}>
      {children}
    </StockContext.Provider>
  );
};

export const useStockContext = () => {
  const context = useContext(StockContext);
  if (context === undefined) {
    throw new Error('useStockContext must be used within a StockProvider');
  }
  return context;
};
