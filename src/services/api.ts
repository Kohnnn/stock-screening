/**
 * API Service for VnStock Screener
 * Connects frontend to FastAPI backend
 */

// Empty string default = relative paths (works with nginx proxy in Docker)
const API_BASE_URL = import.meta.env.VITE_API_URL || '';

// Types matching backend response
export interface Stock {
    symbol: string;
    company_name: string | null;
    exchange: string | null;
    sector: string | null;
    industry: string | null;
    current_price: number | null;
    price_change: number | null;
    percent_change: number | null;
    volume: number | null;
    market_cap: number | null;
    pe_ratio: number | null;
    pb_ratio: number | null;
    roe: number | null;
    roa: number | null;
    eps: number | null;
    updated_at: string | null;
}

export interface StockListResponse {
    stocks: Stock[];
    total: number;
    page: number;
    page_size: number;
}

export interface StockFilters {
    exchange?: string;
    sector?: string;
    pe_min?: number;
    pe_max?: number;
    pb_min?: number;
    pb_max?: number;
    roe_min?: number;
    market_cap_min?: number;
    // Technical filters
    rsi_min?: number;
    rsi_max?: number;
    trend?: string;
    adx_min?: number;
    search?: string;
    page?: number;
    page_size?: number;
}

export interface DatabaseStatus {
    status: string;
    stocks_count: number;
    stocks_with_prices: number;
    last_update: string | null;
    database_size_mb: number | null;
    is_updating: boolean;
}

export interface HealthStatus {
    status: string;
    timestamp: string;
    database: string;
    circuit_breaker: string;
    rate_limiter: {
        total_requests: number;
        total_failures: number;
        current_tokens: number;
    };
}

class ApiService {
    private baseUrl: string;

    constructor(baseUrl: string = API_BASE_URL) {
        this.baseUrl = baseUrl;
    }

    private async fetchJson<T>(endpoint: string, options?: RequestInit): Promise<T> {
        const response = await fetch(`${this.baseUrl}${endpoint}`, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options?.headers,
            },
        });

        if (!response.ok) {
            throw new Error(`API Error: ${response.status} ${response.statusText}`);
        }

        return response.json();
    }

    /**
     * Get stocks with optional filters (using screener endpoint)
     */
    async getStocks(filters?: StockFilters): Promise<StockListResponse> {
        const params = new URLSearchParams();

        if (filters) {
            if (filters.exchange) params.append('exchange', filters.exchange);
            if (filters.sector) params.append('sector', filters.sector);
            if (filters.pe_min !== undefined) params.append('pe_min', filters.pe_min.toString());
            if (filters.pe_max !== undefined) params.append('pe_max', filters.pe_max.toString());
            if (filters.pb_min !== undefined) params.append('pb_min', filters.pb_min.toString());
            if (filters.pb_max !== undefined) params.append('pb_max', filters.pb_max.toString());
            if (filters.roe_min !== undefined) params.append('roe_min', filters.roe_min.toString());
            if (filters.market_cap_min !== undefined) params.append('market_cap_min', filters.market_cap_min.toString());

            // Technical filters
            if (filters.rsi_min !== undefined) params.append('rsi_min', filters.rsi_min.toString());
            if (filters.rsi_max !== undefined) params.append('rsi_max', filters.rsi_max.toString());
            if (filters.trend) params.append('trend', filters.trend);
            if (filters.adx_min !== undefined) params.append('adx_min', filters.adx_min.toString());

            if (filters.search) params.append('search', filters.search);
            if (filters.page) params.append('page', filters.page.toString());
            if (filters.page_size) params.append('page_size', filters.page_size.toString());
        }

        const query = params.toString();
        // Use screener endpoint which handles all filters + technicals
        return this.fetchJson<StockListResponse>(`/api/stocks/screener${query ? `?${query}` : ''}`);
    }

    /**
     * Get single stock details
     */
    async getStock(symbol: string): Promise<Stock> {
        return this.fetchJson<Stock>(`/api/stocks/${symbol}`);
    }

    /**
     * Get available sectors
     */
    async getSectors(): Promise<{ sectors: string[] }> {
        return this.fetchJson<{ sectors: string[] }>('/api/sectors');
    }

    /**
     * Get database status
     */
    async getDatabaseStatus(): Promise<DatabaseStatus> {
        return this.fetchJson<DatabaseStatus>('/api/database/status');
    }

    /**
     * Trigger data update
     */
    async triggerUpdate(taskName?: string, force: boolean = true): Promise<{ message: string; task: string; status: string }> {
        const params = new URLSearchParams();
        if (taskName) params.append('task_name', taskName);
        if (force) params.append('force', 'true');
        const query = params.toString();
        return this.fetchJson(`/api/database/update${query ? `?${query}` : ''}`, { method: 'POST' });
    }

    /**
     * Get health status
     */
    async getHealth(): Promise<HealthStatus> {
        return this.fetchJson<HealthStatus>('/api/health');
    }

    /**
     * Check if API is available
     */
    async isAvailable(): Promise<boolean> {
        try {
            await this.fetchJson('/');
            return true;
        } catch {
            return false;
        }
    }
}

// Export singleton instance
export const api = new ApiService();
export default api;
