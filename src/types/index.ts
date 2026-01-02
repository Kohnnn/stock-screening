// ============================================
// Stock Types
// ============================================

export interface Stock {
    symbol: string;
    companyName: string;
    exchange: 'HOSE' | 'HNX' | 'UPCOM';
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
}

export interface FinancialMetrics {
    symbol: string;
    period: string;
    peRatio?: number;
    pbRatio?: number;
    psRatio?: number;
    marketCap?: number;
    roe?: number;
    roa?: number;
    debtToEquity?: number;
    currentRatio?: number;
    revenueGrowthYoy?: number;
    npatGrowthYoy?: number;
}

export interface PriceHistory {
    symbol: string;
    date: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
    adjustedClose?: number;
}

// ============================================
// Filter Types
// ============================================

export interface StockFilters {
    exchange?: 'HOSE' | 'HNX' | 'UPCOM' | '';
    sector?: string;
    peMin?: number;
    peMax?: number;
    pbMin?: number;
    pbMax?: number;
    roeMin?: number;
    marketCapMin?: number;
    marketCapMax?: number;
    // Technical filters
    rsiMin?: number;
    rsiMax?: number;
    trend?: string;
    adxMin?: number;
    search?: string;
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

export interface ComparisonStock extends Stock {
    financials?: FinancialMetrics;
    priceHistory?: PriceHistory[];
}
