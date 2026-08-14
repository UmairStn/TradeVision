import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import type { MarketSummary } from '../types/stock';
import { fetchMarketSummary } from '../services/api';

/** Live CSE data goes stale within a session, so poll while the tab is open. */
const REFRESH_MS = 60_000;

interface StockContextType {
  selectedTicker: string;
  setSelectedTicker: (ticker: string) => void;
  marketSummary: MarketSummary | null;
  isLoading: boolean;
  error: string | null;
  refresh: () => void;
}

const StockContext = createContext<StockContextType | undefined>(undefined);

export const StockProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [selectedTicker, setSelectedTicker] = useState<string>('JKH.N0000');
  const [marketSummary, setMarketSummary] = useState<MarketSummary | null>(null);
  // Starts true, so the initial load never has to set it — which also keeps the
  // effect below free of a synchronous setState.
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Promise callbacks rather than async/await, so every setState provably happens
  // after the fetch resolves. Nothing runs synchronously when the effect below
  // calls this on mount.
  const load = useCallback(
    (isInitial: boolean) =>
      fetchMarketSummary()
        .then((data) => {
          setMarketSummary(data);
          setError(null);
        })
        .catch((e: unknown) => {
          // Surface the backend's actual message — "Cannot reach the TradeVision
          // API" and "CSE unavailable" need different responses from the user.
          setError(e instanceof Error ? e.message : 'Failed to fetch market summary');
        })
        .finally(() => {
          // Only the first load drives the page-level spinner. A background
          // refresh keeps the current table on screen, because swapping to a
          // skeleton every minute would be worse than showing data that is
          // seconds old.
          if (isInitial) setIsLoading(false);
        }),
    []
  );

  useEffect(() => {
    void load(true);
    const timer = setInterval(() => void load(false), REFRESH_MS);
    return () => clearInterval(timer);
  }, [load]);

  const refresh = useCallback(() => void load(false), [load]);

  return (
    <StockContext.Provider
      value={{ selectedTicker, setSelectedTicker, marketSummary, isLoading, error, refresh }}
    >
      {children}
    </StockContext.Provider>
  );
};

// Hook is co-located with its provider by design; the rule only affects the
// granularity of dev-server fast refresh, not runtime behaviour.
// eslint-disable-next-line react-refresh/only-export-components
export const useStockContext = () => {
  const context = useContext(StockContext);
  if (context === undefined) {
    throw new Error('useStockContext must be used within a StockProvider');
  }
  return context;
};
