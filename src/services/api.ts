import type {
  StockPrice,
  StockQuote,
  MarketSummary,
  WatchlistItem,
  UserPortfolio,
  PredictionResult,
} from '../types/stock';

// --- MOCK DATA ---

const mockQuotes: StockQuote[] = [
  { ticker: 'JKH.N0000', name: 'John Keells Holdings', price: 195.5, change: 2.5, changePercent: 1.29, volume: 1540000, marketCap: '250B' },
  { ticker: 'COMB.N0000', name: 'Commercial Bank of Ceylon', price: 98.2, change: -1.1, changePercent: -1.11, volume: 890000, marketCap: '120B' },
  { ticker: 'BIL.N0000', name: 'Bukit Darah PLC', price: 380.0, change: 5.0, changePercent: 1.33, volume: 120000, marketCap: '95B' },
  { ticker: 'EXPO.N0000', name: 'Expolanka Holdings', price: 145.0, change: -3.5, changePercent: -2.36, volume: 2100000, marketCap: '140B' },
  { ticker: 'DIST.N0000', name: 'Distilleries Company of SL', price: 28.5, change: 0.8, changePercent: 2.89, volume: 3500000, marketCap: '130B' },
  { ticker: 'HNB.N0000', name: 'Hatton National Bank', price: 165.0, change: 1.5, changePercent: 0.92, volume: 650000, marketCap: '90B' },
];

const mockMarketSummary: MarketSummary = {
  gainers: [mockQuotes[4], mockQuotes[2], mockQuotes[0]],
  losers: [mockQuotes[3], mockQuotes[1]],
  mostActive: [mockQuotes[4], mockQuotes[3], mockQuotes[0]],
};

const mockWatchlist: WatchlistItem[] = [
  { ticker: 'JKH.N0000', name: 'John Keells Holdings', targetPrice: 200, alertEnabled: true },
  { ticker: 'EXPO.N0000', name: 'Expolanka Holdings', targetPrice: 150, alertEnabled: false },
  { ticker: 'COMB.N0000', name: 'Commercial Bank of Ceylon', targetPrice: null, alertEnabled: true },
];

const mockPortfolio: UserPortfolio = {
  holdings: [
    { ticker: 'JKH.N0000', name: 'John Keells Holdings', shares: 1000, avgCost: 180.0, currentPrice: 195.5 },
    { ticker: 'DIST.N0000', name: 'Distilleries Company of SL', shares: 5000, avgCost: 25.0, currentPrice: 28.5 },
  ],
  totalValue: 195500 + 142500,
  dayChange: 2500 + 4000,
  dayChangePercent: 1.96,
};

// --- HELPER TO GENERATE CHART DATA ---
const generateChartData = (basePrice: number, days: number): StockPrice[] => {
  const data: StockPrice[] = [];
  let currentPrice = basePrice;
  const now = new Date();
  
  for (let i = days; i >= 0; i--) {
    const date = new Date(now);
    date.setDate(date.getDate() - i);
    
    // Random walk
    const change = currentPrice * (Math.random() * 0.06 - 0.03); // -3% to +3%
    const open = currentPrice;
    currentPrice = currentPrice + change;
    const close = currentPrice;
    const high = Math.max(open, close) * (1 + Math.random() * 0.02);
    const low = Math.min(open, close) * (1 - Math.random() * 0.02);
    const volume = Math.floor(Math.random() * 1000000) + 100000;
    
    data.push({
      timestamp: date.toISOString().split('T')[0],
      open,
      high,
      low,
      close,
      volume,
    });
  }
  return data;
};

// --- API METHODS ---

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export const fetchStockHistory = async (ticker: string, days: number): Promise<StockPrice[]> => {
  await delay(200);
  const quote = mockQuotes.find((q) => q.ticker === ticker);
  const basePrice = quote ? quote.price : 100;
  return generateChartData(basePrice, days);
};

export const fetchStockQuote = async (ticker: string): Promise<StockQuote> => {
  await delay(200);
  const quote = mockQuotes.find((q) => q.ticker === ticker);
  if (!quote) throw new Error('Stock not found');
  return quote;
};

export const fetchMarketSummary = async (): Promise<MarketSummary> => {
  await delay(200);
  return mockMarketSummary;
};

export const fetchWatchlist = async (): Promise<WatchlistItem[]> => {
  await delay(200);
  return mockWatchlist;
};

export const fetchPortfolio = async (): Promise<UserPortfolio> => {
  await delay(200);
  return mockPortfolio;
};

export const fetchPrediction = async (ticker: string): Promise<PredictionResult> => {
  await delay(500);
  const quote = mockQuotes.find((q) => q.ticker === ticker);
  const currentPrice = quote ? quote.price : 100;
  
  // Random prediction
  const isUp = Math.random() > 0.5;
  const changePercent = Math.random() * 0.05; // Up to 5% change
  const nextDayPrice = currentPrice * (1 + (isUp ? changePercent : -changePercent));
  
  return {
    ticker,
    nextDayPrice,
    confidence: Math.floor(Math.random() * 30) + 60, // 60-90%
    trend: isUp ? 'up' : 'down',
    generatedAt: new Date().toISOString(),
  };
};

export const searchStocks = async (query: string): Promise<StockQuote[]> => {
  await delay(150);
  const lowerQuery = query.toLowerCase();
  return mockQuotes.filter(
    (q) => q.ticker.toLowerCase().includes(lowerQuery) || q.name.toLowerCase().includes(lowerQuery)
  );
};
