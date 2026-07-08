export interface StockPrice {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface StockQuote {
  ticker: string;
  name: string;
  price: number;
  change: number;
  changePercent: number;
  volume: number;
  marketCap: string;
}

export interface MarketSummary {
  gainers: StockQuote[];
  losers: StockQuote[];
  mostActive: StockQuote[];
}

export interface WatchlistItem {
  ticker: string;
  name: string;
  targetPrice: number | null;
  alertEnabled: boolean;
}

export interface PortfolioHolding {
  ticker: string;
  name: string;
  shares: number;
  avgCost: number;
  currentPrice: number;
}

export interface UserPortfolio {
  holdings: PortfolioHolding[];
  totalValue: number;
  dayChange: number;
  dayChangePercent: number;
}

export interface PredictionResult {
  ticker: string;
  nextDayPrice: number;
  confidence: number;
  trend: 'up' | 'down' | 'neutral';
  generatedAt: string;
}
