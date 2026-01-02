import React, { useState, useCallback, useEffect } from 'react';
import { useLanguage } from '../contexts/LanguageContext';
import { api, StockListResponse } from '../services/api';
import { FiltersPanel } from './FiltersPanel';
import { StockTable } from './StockTable';
import { Stock, StockFilters } from '../types';
import { useWatchlist } from '../hooks/useWatchlist';

// ============================================
// Preset Types & Storage
// ============================================

interface ScreenerPreset {
    name: string;
    filters: StockFilters;
    createdAt: string;
}

const PRESETS_KEY = 'vnstock-screener-presets';

const DEFAULT_PRESETS: ScreenerPreset[] = [
    {
        name: 'Oversold (RSI < 30)',
        filters: { rsiMax: 30 },
        createdAt: new Date().toISOString(),
    },
    {
        name: 'Strong Trend (ADX > 25)',
        filters: { adxMin: 25 },
        createdAt: new Date().toISOString(),
    },
    {
        name: 'Value Stocks (P/E < 15)',
        filters: { peMax: 15 },
        createdAt: new Date().toISOString(),
    },
];

// ============================================
// Helper Functions
// ============================================

function exportToCSV(stocks: Stock[], filename: string = 'stocks-export.csv') {
    if (stocks.length === 0) return;

    const headers = [
        'Symbol', 'Company', 'Exchange', 'Sector', 'Price',
        'Change %', 'Volume', 'Market Cap', 'P/E', 'P/B', 'ROE'
    ];

    const rows = stocks.map(s => [
        s.symbol,
        s.companyName || '',
        s.exchange || '',
        s.sector || '',
        s.currentPrice || '',
        s.priceChangePercent || '',
        s.volume || '',
        s.marketCap || '',
        s.pe || '',
        s.pb || '',
        s.roe || '',
    ]);

    const csvContent = [
        headers.join(','),
        ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    link.click();
    URL.revokeObjectURL(link.href);
}

function loadPresets(): ScreenerPreset[] {
    try {
        const stored = localStorage.getItem(PRESETS_KEY);
        if (stored) {
            return JSON.parse(stored);
        }
    } catch {
        console.error('Failed to load presets');
    }
    return DEFAULT_PRESETS;
}

function savePresets(presets: ScreenerPreset[]) {
    localStorage.setItem(PRESETS_KEY, JSON.stringify(presets));
}

// ============================================
// Component
// ============================================

export function StockScreener() {
    const { t } = useLanguage();
    const { watchlist, toggleWatchlist } = useWatchlist();

    // Filters state
    const [filters, setFilters] = useState<StockFilters>({});
    const [appliedFilters, setAppliedFilters] = useState<StockFilters>({});
    const [showFilters, setShowFilters] = useState(true);

    // Presets state
    const [presets, setPresets] = useState<ScreenerPreset[]>(() => loadPresets());
    const [showPresets, setShowPresets] = useState(false);
    const [newPresetName, setNewPresetName] = useState('');

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
    useEffect(() => {
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
            if (prev.length >= 5) return prev;
            return [...prev, symbol];
        });
    }, []);

    const handleSelectStock = useCallback((stock: Stock) => {
        console.log('Selected stock:', stock);
    }, []);

    // Export handler
    const handleExportCSV = useCallback(() => {
        const timestamp = new Date().toISOString().slice(0, 10);
        exportToCSV(stocksData.stocks as unknown as Stock[], `vnstock-export-${timestamp}.csv`);
    }, [stocksData.stocks]);

    // Preset handlers
    const handleSavePreset = useCallback(() => {
        if (!newPresetName.trim()) return;
        const newPreset: ScreenerPreset = {
            name: newPresetName,
            filters: { ...filters },
            createdAt: new Date().toISOString(),
        };
        const updated = [...presets, newPreset];
        setPresets(updated);
        savePresets(updated);
        setNewPresetName('');
    }, [newPresetName, filters, presets]);

    const handleLoadPreset = useCallback((preset: ScreenerPreset) => {
        setFilters(preset.filters);
        setAppliedFilters(preset.filters);
        setShowPresets(false);
    }, []);

    const handleDeletePreset = useCallback((index: number) => {
        const updated = presets.filter((_, i) => i !== index);
        setPresets(updated);
        savePresets(updated);
    }, [presets]);

    return (
        <div className="stock-screener">
            {/* Toolbar */}
            <div className="screener-toolbar">
                <div className="flex items-center gap-md">
                    <h2 className="card-title">{t('screener.title')}</h2>
                    <span className="badge badge-info">
                        {stocksData.total} {t('screener.results').toLowerCase()}
                    </span>
                    {loading && <span className="spinner" />}
                </div>

                <div className="flex gap-sm">
                    <button
                        className={`btn ${showFilters ? 'btn-primary' : 'btn-secondary'}`}
                        onClick={() => setShowFilters(!showFilters)}
                    >
                        🔍 {t('screener.filters')}
                    </button>
                    <button
                        className={`btn ${showPresets ? 'btn-primary' : 'btn-secondary'}`}
                        onClick={() => setShowPresets(!showPresets)}
                    >
                        💾 Presets
                    </button>
                    <button
                        className="btn btn-secondary"
                        onClick={handleExportCSV}
                        disabled={stocksData.stocks.length === 0}
                    >
                        📥 {t('common.exportCSV')}
                    </button>
                </div>
            </div>

            {/* Presets Panel */}
            {showPresets && (
                <div className="filters-panel">
                    <div className="card-header">
                        <h3 className="card-title">📁 Screener Presets</h3>
                    </div>

                    <div className="flex gap-md mb-md">
                        <input
                            type="text"
                            className="form-input"
                            placeholder="New preset name..."
                            value={newPresetName}
                            onChange={(e) => setNewPresetName(e.target.value)}
                            style={{ flex: 1 }}
                        />
                        <button
                            className="btn btn-primary"
                            onClick={handleSavePreset}
                            disabled={!newPresetName.trim()}
                        >
                            Save Current
                        </button>
                    </div>

                    <div className="flex gap-sm" style={{ flexWrap: 'wrap' }}>
                        {presets.map((preset, idx) => (
                            <div key={idx} className="filter-chip" style={{ padding: '8px 12px' }}>
                                <button
                                    onClick={() => handleLoadPreset(preset)}
                                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit' }}
                                >
                                    {preset.name}
                                </button>
                                <button onClick={() => handleDeletePreset(idx)}>×</button>
                            </div>
                        ))}
                    </div>
                </div>
            )}

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
                    loading={loading}
                    onSelectStock={handleSelectStock}
                    selectedStocks={selectedStocks}
                    onToggleSelect={handleToggleSelect}
                    watchlist={watchlist}
                    onToggleWatchlist={toggleWatchlist}
                />
            </div>
        </div>
    );
}

export default StockScreener;

