import React, { useState, useCallback } from 'react';
import { useLanguage } from '../contexts/LanguageContext';
import { api, StockListResponse } from '../services/api';
import { FiltersPanel } from './FiltersPanel';
import { StockTable } from './StockTable';
import { Stock, StockFilters } from '../types';

// ============================================
// Component
// ============================================

export function StockScreener() {
    const { t } = useLanguage();

    // Filters state
    const [filters, setFilters] = useState<StockFilters>({});
    const [appliedFilters, setAppliedFilters] = useState<StockFilters>({});
    const [showFilters, setShowFilters] = useState(true);

    // Data state
    const [stocksData, setStocksData] = useState<StockListResponse>({
        stocks: [],
        total: 0,
        page: 1,
        pageSize: 50
    });
    const [loading, setLoading] = useState(false);

    // Selection state for comparison
    const [selectedStocks, setSelectedStocks] = useState<string[]>([]);

    // Fetch stocks when applied filters change
    React.useEffect(() => {
        const fetchStocks = async () => {
            try {
                setLoading(true);
                const data = await api.getStocks(appliedFilters);
                setStocksData(data);
            } catch (error) {
                console.error('Failed to fetch stocks:', error);
            } finally {
                setLoading(false);
            }
        };

        // Debounce slightly to prevent rapid API calls usually not needed as we trigger on apply
        fetchStocks();
    }, [appliedFilters]);

    const handleApplyFilters = useCallback(() => {
        setAppliedFilters({ ...filters });
    }, [filters]);

    const handleClearFilters = useCallback(() => {
        setFilters({});
        setAppliedFilters({});
    }, []);

    const handleToggleSelect = useCallback((symbol: string) => {
        setSelectedStocks((prev) => {
            if (prev.includes(symbol)) {
                return prev.filter((s) => s !== symbol);
            }
            if (prev.length >= 5) {
                // Max 5 stocks for comparison
                return prev;
            }
            return [...prev, symbol];
        });
    }, []);

    const handleSelectStock = useCallback((stock: Stock) => {
        console.log('Selected stock:', stock);
    }, []);

    return (
        <div className="stock-screener">
            {/* Toolbar */}
            <div className="screener-toolbar">
                <div className="flex items-center gap-md">
                    <h2 className="card-title">{t('screener.title')}</h2>
                    <span className="badge badge-info">
                        {stocksData.total} {t('screener.results').toLowerCase()}
                    </span>
                </div>

                <div className="flex gap-sm">
                    <button
                        className={`btn ${showFilters ? 'btn-primary' : 'btn-secondary'}`}
                        onClick={() => setShowFilters(!showFilters)}
                    >
                        🔍 {t('screener.filters')}
                    </button>
                    <button className="btn btn-secondary">
                        📥 {t('common.exportCSV')}
                    </button>
                </div>
            </div>

            {/* Filters Panel */}
            {showFilters && (
                <FiltersPanel
                    filters={filters}
                    onFiltersChange={setFilters}
                    onApply={handleApplyFilters}
                    onClear={handleClearFilters}
                />
            )}

            {/* Selected stocks for comparison */}
            {selectedStocks.length > 0 && (
                <div className="comparison-bar">
                    <span className="text-sm text-muted">
                        {t('comparison.select')}: {selectedStocks.length}/5
                    </span>
                    <div className="flex gap-sm">
                        {selectedStocks.map((symbol) => (
                            <span key={symbol} className="filter-chip">
                                {symbol}
                                <button onClick={() => handleToggleSelect(symbol)}>×</button>
                            </span>
                        ))}
                    </div>
                    <button
                        className="btn btn-secondary btn-sm"
                        onClick={() => setSelectedStocks([])}
                    >
                        {t('comparison.clear')}
                    </button>
                </div>
            )}

            {/* Results Table */}
            <div className="card mt-md">
                <StockTable
                    stocks={stocksData.stocks}
                    loading={false}
                    onSelectStock={handleSelectStock}
                    selectedStocks={selectedStocks}
                    onToggleSelect={handleToggleSelect}
                />
            </div>
        </div>
    );
}

export default StockScreener;
