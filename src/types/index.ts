// ============================================
// Stock Types
// ============================================

export interface Stock {
    symbol: string;
    companyName: string;
    exchange: string;
    sector?: string;
    industry?: string;
    currentPrice?: number;
    priceChange?: number;
    priceChangePercent?: number;
    volume?: number;
    marketCap?: number;
    pe?: number;
    pb?: number;
    roe?: number;
    eps?: number;
    isActive: boolean;
    updatedAt?: string;

    // Technical Signals
    rsi?: number;
    macdHistogram?: number;
    stockRating?: number;
    relativeStrength?: number;
    uptrend?: number | boolean; // support both
    breakout?: number | boolean;

    // Financial Details
    grossMargin?: number;
    netMargin?: number;
    revenueGrowth?: number;
    npatGrowth?: number;
    dividendYield?: number;
}

export interface StockFilters {
    // Basic filters
    exchange?: 'HOSE' | 'HNX' | 'UPCOM' | '';
    sector?: string;
    industry?: string;
    search?: string;

    // General metrics
    marketCapMin?: number;
    marketCapMax?: number;
    priceMin?: number;
    priceMax?: number;
    priceChangeMin?: number;
    priceChangeMax?: number;
    adtvValueMin?: number;
    volumeVsAdtvMin?: number;

    // Technical signals
    stockRatingMin?: number;
    rsMin?: number;
    rsMax?: number;
    rsiMin?: number;
    rsiMax?: number;
    priceVsSma20Min?: number;
    priceVsSma20Max?: number;
    macdHistogramMin?: number;
    stockTrend?: string;
    priceReturn1mMin?: number;
    priceReturn1mMax?: number;

    // Financial indicators
    peMin?: number;
    peMax?: number;
    pbMin?: number;
    pbMax?: number;
    roeMin?: number;
    roeMax?: number;
    revenueGrowthMin?: number;
    npatGrowthMin?: number;
    netMarginMin?: number;
    grossMarginMin?: number;
    dividendYieldMin?: number;

    // Additional value metrics
    epsMin?: number;
    epsMax?: number;
    bookValueMin?: number;
    bookValueMax?: number;
    psMin?: number;
    psMax?: number;
}

export interface ActiveFilter {
    key: keyof StockFilters;
    label: string;
    value: string | number;
}

// ============================================
// API Response Types
// ============================================

export interface StockListResponse {
    stocks: Stock[];
    total: number;
    page: number;
    pageSize: number;
}

export interface ScreeningResponse {
    stocks: Stock[];
    total: number;
    filters: StockFilters;
}

export interface DatabaseStatus {
    status: 'fresh' | 'stale' | 'outdated';
    lastUpdate: string;
    totalStocks: number;
    stocksWithFinancials: number;
    stocksWithPrices: number;
    databaseSize: string;
    isUpdating: boolean;
}

export interface UpdateProgress {
    phase: string;
    current: number;
    total: number;
    percentage: number;
    message: string;
}

// ============================================
// Sorting Types
// ============================================

export type SortDirection = 'asc' | 'desc';

export interface SortConfig {
    key: keyof Stock;
    direction: SortDirection;
}

// ============================================
// Pagination Types
// ============================================

export interface Pagination {
    page: number;
    pageSize: number;
    total: number;
    totalPages: number;
}

// ============================================
// Comparison Types
// ============================================

export interface FinancialMetrics {
    revenue?: number;
    profit?: number;
    grossMargin?: number;
    netMargin?: number;
    roe?: number;
    roa?: number;
    debtToEquity?: number;
}

export interface PriceHistory {
    date: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
}

export interface ComparisonStock extends Stock {
    financials?: FinancialMetrics;
    priceHistory?: PriceHistory[];
}
