import React, { useState, useCallback, useMemo } from 'react';
import { useLanguage } from '../contexts/LanguageContext';
import { useTheme } from '../contexts/ThemeContext';
import { useWatchlist } from '../hooks/useWatchlist';
import { Stock, StockFilters } from '../types';
import { FilterPresets } from './FilterPresets';
import { downloadCSV } from '../utils/csvExport';

// ============================================
// Constants & Types
// ============================================

const EXCHANGES = [
    { value: '', label: 'Tất cả sàn' },
    { value: 'HOSE', label: 'HOSE' },
    { value: 'HNX', label: 'HNX' },
    { value: 'UPCOM', label: 'UPCOM' },
];

type ViewType = 'overview' | 'financial' | 'technical';

interface ColumnDef {
    key: keyof Stock | string;
    label: string;
    align?: 'left' | 'right' | 'center';
    render?: (stock: Stock) => React.ReactNode;
    sortable?: boolean;
    width?: string;
}

// ============================================
// Helper Components (Filters)
// ============================================

function FilterSection({ title, children, defaultOpen = false }: { title: string; children: React.ReactNode; defaultOpen?: boolean }) {
    const [isOpen, setIsOpen] = useState(defaultOpen);
    return (
        <div className="filter-section">
            <div className="filter-section-header" onClick={() => setIsOpen(!isOpen)}>
                <span>{isOpen ? '▼' : '▶'} {title}</span>
            </div>
            {isOpen && <div className="filter-section-content">{children}</div>}
        </div>
    );
}

function FilterInput({ label, tooltip, children }: { label: string; tooltip: string; children: React.ReactNode }) {
    return (
        <div className="form-group" title={tooltip}>
            <label className="form-label">
                {label}
                {tooltip && <span className="tooltip-icon" title={tooltip}>ⓘ</span>}
            </label>
            {children}
        </div>
    );
}

function RangeFilter({
    label, tooltip, minValue, maxValue, onMinChange, onMaxChange, minPlaceholder = "Min", maxPlaceholder = "Max",
}: {
    label: string; tooltip: string; minValue?: number; maxValue?: number;
    onMinChange: (v: number | undefined) => void; onMaxChange: (v: number | undefined) => void;
    minPlaceholder?: string; maxPlaceholder?: string;
}) {
    return (
        <div className="range-filter" title={tooltip}>
            <label className="range-filter-label">
                {label}
                {tooltip && <span className="tooltip-icon" title={tooltip}>ⓘ</span>}
            </label>
            <div className="range-inputs">
                <input type="number" className="range-input" placeholder={minPlaceholder} value={minValue ?? ''}
                    onChange={(e) => onMinChange(e.target.value ? parseFloat(e.target.value) : undefined)} />
                <span className="range-separator">-</span>
                <input type="number" className="range-input" placeholder={maxPlaceholder} value={maxValue ?? ''}
                    onChange={(e) => onMaxChange(e.target.value ? parseFloat(e.target.value) : undefined)} />
            </div>
        </div>
    );
}

// ============================================
// Main Component
// ============================================

export function StockScreener() {
    const { t, formatCurrency, formatNumber } = useLanguage();
    const { watchlist, toggleWatchlist } = useWatchlist();

    // State
    const [filters, setFilters] = useState<StockFilters>({});
    const [appliedFilters, setAppliedFilters] = useState<StockFilters>({});
    const [showFilters, setShowFilters] = useState(true);
    const [stocks, setStocks] = useState<Stock[]>([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);
    const [usingMockData, setUsingMockData] = useState(false);
    const [currentView, setCurrentView] = useState<ViewType>('overview');
    const [sortConfig, setSortConfig] = useState<{ key: keyof Stock | string; direction: 'asc' | 'desc' } | null>(null);

    // API Base URL
    const API_BASE_URL = import.meta.env.VITE_API_URL || '';

    // --------------------------------------------------------------------------
    // Data Fetching
    // --------------------------------------------------------------------------

    const fetchStocks = useCallback(async (currentFilters: StockFilters, currentSort: typeof sortConfig) => {
        setLoading(true);
        try {
            const params = new URLSearchParams();
            // Basic
            if (currentFilters.exchange) params.set('exchange', currentFilters.exchange);
            if (currentFilters.search) params.set('search', currentFilters.search);
            // General
            if (currentFilters.marketCapMin !== undefined) params.set('market_cap_min', String(currentFilters.marketCapMin));
            if (currentFilters.marketCapMax !== undefined) params.set('market_cap_max', String(currentFilters.marketCapMax));
            if (currentFilters.priceMin !== undefined) params.set('price_min', String(currentFilters.priceMin));
            if (currentFilters.priceMax !== undefined) params.set('price_max', String(currentFilters.priceMax));
            if (currentFilters.adtvValueMin !== undefined) params.set('adtv_value_min', String(currentFilters.adtvValueMin));
            // Technical
            if (currentFilters.rsiMin !== undefined) params.set('rsi_min', String(currentFilters.rsiMin));
            if (currentFilters.rsiMax !== undefined) params.set('rsi_max', String(currentFilters.rsiMax));
            if (currentFilters.rsMin !== undefined) params.set('rs_min', String(currentFilters.rsMin));
            if (currentFilters.priceVsSma20Min !== undefined) params.set('price_vs_sma20_min', String(currentFilters.priceVsSma20Min));
            if (currentFilters.stockTrend) params.set('stock_trend', currentFilters.stockTrend);
            // Financial
            if (currentFilters.peMin !== undefined) params.set('pe_min', String(currentFilters.peMin));
            if (currentFilters.peMax !== undefined) params.set('pe_max', String(currentFilters.peMax));
            if (currentFilters.pbMin !== undefined) params.set('pb_min', String(currentFilters.pbMin));
            if (currentFilters.pbMax !== undefined) params.set('pb_max', String(currentFilters.pbMax));
            if (currentFilters.roeMin !== undefined) params.set('roe_min', String(currentFilters.roeMin));
            if (currentFilters.revenueGrowthMin !== undefined) params.set('revenue_growth_min', String(currentFilters.revenueGrowthMin));
            if (currentFilters.npatGrowthMin !== undefined) params.set('npat_growth_min', String(currentFilters.npatGrowthMin));
            if (currentFilters.netMarginMin !== undefined) params.set('net_margin_min', String(currentFilters.netMarginMin));

            // Sorting
            if (currentSort) {
                params.set('sort_by', currentSort.key as string);
                params.set('order', currentSort.direction);
            }

            params.set('page_size', '300');

            const response = await fetch(`${API_BASE_URL}/api/stocks/screener?${params.toString()}`);
            if (!response.ok) throw new Error(`API Error: ${response.status}`);
            const data = await response.json();

            const mappedStocks: Stock[] = data.stocks.map((s: any) => ({
                symbol: s.symbol,
                companyName: s.company_name || s.symbol,
                exchange: s.exchange || 'HOSE',
                sector: s.sector,
                industry: s.industry,
                currentPrice: s.current_price,
                priceChange: s.price_change,
                priceChangePercent: s.percent_change,
                volume: s.volume,
                marketCap: s.market_cap,
                pe: s.pe_ratio,
                pb: s.pb_ratio,
                roe: s.roe,
                eps: s.eps,
                isActive: true,
                updatedAt: s.screener_updated_at || s.updated_at,
                rsi: s.rsi,
                macdHistogram: s.macd_histogram,
                stockRating: s.stock_rating,
                relativeStrength: s.tc_rs, // Map from backend 'tc_rs' (RS Rating)
                grossMargin: s.gross_margin,
                netMargin: s.net_margin,
                revenueGrowth: s.revenue_growth_1y,
                npatGrowth: s.npat_growth,
                uptrend: s.uptrend,
                breakout: s.breakout,
            }));

            setStocks(mappedStocks);
            setTotal(data.total);
            setUsingMockData(false);
        } catch (err) {
            console.warn('API unavailable, using mock data:', err);
            setUsingMockData(true);
            setStocks([]);
        } finally {
            setLoading(false);
        }
    }, [API_BASE_URL]);

    React.useEffect(() => {
        fetchStocks(appliedFilters, sortConfig);
    }, [appliedFilters, sortConfig, fetchStocks]);

    // --------------------------------------------------------------------------
    // Handlers
    // --------------------------------------------------------------------------

    const handleApplyFilters = useCallback(() => setAppliedFilters({ ...filters }), [filters]);
    const handleClearFilters = useCallback(() => { setFilters({}); setAppliedFilters({}); }, []);

    const handleSort = (key: keyof Stock | string) => {
        let direction: 'asc' | 'desc' = 'desc'; // Default to desc for most metrics
        if (sortConfig && sortConfig.key === key && sortConfig.direction === 'desc') {
            direction = 'asc';
        }
        setSortConfig({ key, direction });
    };

    // Use server-side sorted stocks directly since API handles it
    const sortedStocks = stocks;

    const handleChange = (key: keyof StockFilters, value: string | number | undefined) => {
        setFilters(prev => ({ ...prev, [key]: value === '' ? undefined : value }));
    };

    // --------------------------------------------------------------------------
    // Column Definitions
    // --------------------------------------------------------------------------

    const getColumns = (): ColumnDef[] => {
        const common: ColumnDef[] = [
            {
                key: 'symbol', label: t('table.symbol'),
                render: (s) => <strong>{s.symbol}</strong>,
                sortable: true
            },
            {
                key: 'companyName', label: t('table.companyName'),
                render: (s) => <span className="text-muted text-sm truncate block max-w-[150px]" title={s.companyName}>{s.companyName}</span>,
                sortable: true
            },
        ];

        const getPriceChangeClass = (val?: number) => val ? (val > 0 ? 'text-stock-up' : 'text-stock-down') : 'text-gray-500';

        if (currentView === 'overview') {
            return [
                ...common,
                { key: 'exchange', label: 'Sàn', render: (s) => <span className={`exchange-badge exchange-${s.exchange.toLowerCase()}`}>{s.exchange}</span> },
                {
                    key: 'currentPrice', label: t('table.price'), align: 'right', sortable: true,
                    render: (s) => <span className="font-bold font-mono">{formatCurrency(s.currentPrice || 0)}</span>
                },
                {
                    key: 'priceChangePercent', label: '% Thay đổi', align: 'right', sortable: true,
                    render: (s) => <span className={`font-mono ${getPriceChangeClass(s.priceChangePercent)}`}>{s.priceChangePercent ? `${s.priceChangePercent > 0 ? '+' : ''}${s.priceChangePercent.toFixed(1)}%` : '-'}</span>
                },
                {
                    key: 'marketCap', label: t('table.marketCap'), align: 'right', sortable: true,
                    render: (s) => s.marketCap ? `${formatNumber(s.marketCap, 0)} B` : '-'
                },
                {
                    key: 'volume', label: 'Vol', align: 'right', sortable: true,
                    render: (s) => s.volume ? formatNumber(s.volume, 0) : '-'
                },
                { key: 'sector', label: t('table.sector'), sortable: true, render: (s) => s.sector || '-' },
            ];
        }
        else if (currentView === 'financial') {
            return [
                ...common,
                { key: 'pe', label: 'P/E', align: 'right', sortable: true, render: (s) => s.pe ? s.pe.toFixed(1) : '-' },
                { key: 'pb', label: 'P/B', align: 'right', sortable: true, render: (s) => s.pb ? s.pb.toFixed(1) : '-' },
                { key: 'roe', label: 'ROE %', align: 'right', sortable: true, render: (s) => s.roe ? `${s.roe.toFixed(1)}%` : '-' },
                { key: 'grossMargin', label: 'Gross Marg %', align: 'right', sortable: true, render: (s) => s.grossMargin ? `${s.grossMargin.toFixed(1)}%` : '-' },
                { key: 'netMargin', label: 'Net Marg %', align: 'right', sortable: true, render: (s) => s.netMargin ? `${s.netMargin.toFixed(1)}%` : '-' },
                { key: 'revenueGrowth', label: 'Rev Growth %', align: 'right', sortable: true, render: (s) => s.revenueGrowth ? `${s.revenueGrowth.toFixed(1)}%` : '-' },
                { key: 'npatGrowth', label: 'Profit Growth %', align: 'right', sortable: true, render: (s) => s.npatGrowth ? `${s.npatGrowth.toFixed(1)}%` : '-' },
            ];
        }
        else { // Technical
            return [
                ...common,
                { key: 'rsi', label: 'RSI (14)', align: 'right', sortable: true, render: (s) => s.rsi ? s.rsi.toFixed(1) : '-' },
                { key: 'relativeStrength', label: 'RS Rating', align: 'right', sortable: true, render: (s) => s.relativeStrength ? s.relativeStrength.toFixed(0) : '-' },
                { key: 'macdHistogram', label: 'MACD Hist', align: 'right', sortable: true, render: (s) => s.macdHistogram ? s.macdHistogram.toFixed(2) : '-' },
                {
                    key: 'priceVsSma20', label: 'vs SMA20', align: 'right',
                    // Note: Not available in type yet, need to verify API returns it or calculate
                    render: (s) => '-'
                },
                {
                    key: 'trend', label: 'Trend', align: 'center',
                    render: (s) => s.uptrend ? '📈 Uptrend' : (s.breakout ? '🚀 Breakout' : '-')
                }
            ];
        }
    };

    const columns = getColumns();

    // --------------------------------------------------------------------------
    // Render
    // --------------------------------------------------------------------------

    return (
        <div className="flex h-[calc(100vh-80px)] overflow-hidden">
            {/* Sidebar Filters */}
            {showFilters && (
                <div className="w-[300px] flex-shrink-0 bg-base-200 border-r border-base-300 overflow-y-auto p-4 custom-scrollbar">
                    <div className="flex justify-between items-center mb-4">
                        <h3 className="font-bold text-lg">{t('screener.filters')}</h3>
                        <button className="btn btn-sm btn-ghost" onClick={handleClearFilters}>Reset</button>
                    </div>

                    <FilterPresets currentFilters={filters} onLoadPreset={(preset) => setFilters(preset as StockFilters)} />

                    <div className="flex flex-col gap-4 mt-4">
                        <div className="form-group">
                            <label className="form-label">{t('filter.exchange')}</label>
                            <select className="form-select" value={filters.exchange || ''} onChange={(e) => handleChange('exchange', e.target.value)}>
                                {EXCHANGES.map((ex) => <option key={ex.value} value={ex.value}>{ex.label}</option>)}
                            </select>
                        </div>

                        <div className="form-group">
                            <label className="form-label">{t('common.search')}</label>
                            <input type="text" className="form-input" placeholder="Symbol, Name..." value={filters.search || ''} onChange={(e) => handleChange('search', e.target.value)} />
                        </div>

                        <FilterSection title="📊 Tổng Quan" defaultOpen>
                            <div className="flex flex-col gap-2">
                                <RangeFilter label="Vốn hóa (tỷ)" tooltip="Market Cap" minValue={filters.marketCapMin} maxValue={filters.marketCapMax} onMinChange={(v) => handleChange('marketCapMin', v)} onMaxChange={(v) => handleChange('marketCapMax', v)} />
                                <RangeFilter label="Giá (VND)" tooltip="Price" minValue={filters.priceMin} maxValue={filters.priceMax} onMinChange={(v) => handleChange('priceMin', v)} onMaxChange={(v) => handleChange('priceMax', v)} />
                                <FilterInput label="GTGD TB (tỷ)" tooltip="Avg Value">
                                    <input type="number" className="form-input" placeholder="Min" value={filters.adtvValueMin ?? ''} onChange={(e) => handleChange('adtvValueMin', e.target.value ? parseFloat(e.target.value) : undefined)} />
                                </FilterInput>
                            </div>
                        </FilterSection>

                        <FilterSection title="💰 Tài Chính">
                            <div className="flex flex-col gap-2">
                                <RangeFilter label="P/E" tooltip="Price/Earnings" minValue={filters.peMin} maxValue={filters.peMax} onMinChange={(v) => handleChange('peMin', v)} onMaxChange={(v) => handleChange('peMax', v)} />
                                <RangeFilter label="P/B" tooltip="Price/Book" minValue={filters.pbMin} maxValue={filters.pbMax} onMinChange={(v) => handleChange('pbMin', v)} onMaxChange={(v) => handleChange('pbMax', v)} />
                                <RangeFilter label="ROE %" tooltip="Return on Equity" minValue={filters.roeMin} maxValue={filters.roeMax} onMinChange={(v) => handleChange('roeMin', v)} onMaxChange={(v) => handleChange('roeMax', v)} />
                                <RangeFilter label="Net Margin %" tooltip="Net Profit Margin" minValue={filters.netMarginMin} onMinChange={(v) => handleChange('netMarginMin', v)} onMaxChange={() => { }} />
                            </div>
                        </FilterSection>

                        <FilterSection title="📈 Kỹ Thuật">
                            <div className="flex flex-col gap-2">
                                <RangeFilter label="RSI" tooltip="Relative Strength Index" minValue={filters.rsiMin} maxValue={filters.rsiMax} onMinChange={(v) => handleChange('rsiMin', v)} onMaxChange={(v) => handleChange('rsiMax', v)} />
                                <FilterInput label="Trend" tooltip="Market Trend">
                                    <select className="form-select" value={filters.stockTrend || ''} onChange={(e) => handleChange('stockTrend', e.target.value)}>
                                        <option value="">All</option>
                                        <option value="uptrend">Uptrend</option>
                                        <option value="breakout">Breakout</option>
                                    </select>
                                </FilterInput>
                            </div>
                        </FilterSection>

                        <button className="btn btn-primary mt-4 w-full" onClick={handleApplyFilters}>Apply Filters</button>
                    </div>
                </div>
            )}

            {/* Main Content */}
            <div className="flex-1 flex flex-col min-w-0 bg-base-100">
                {/* Toolbar */}
                <div className="h-14 border-b border-base-300 flex items-center px-4 justify-between bg-base-100">
                    <div className="flex items-center gap-4">
                        <button className={`btn btn-sm btn-square ${!showFilters && 'btn-active'}`} onClick={() => setShowFilters(!showFilters)} title="Toggle Filters">
                            🔍
                        </button>
                        <div className="join">
                            <button className={`join-item btn btn-sm ${currentView === 'overview' ? 'btn-active' : ''}`} onClick={() => setCurrentView('overview')}>Tổng quan</button>
                            <button className={`join-item btn btn-sm ${currentView === 'financial' ? 'btn-active' : ''}`} onClick={() => setCurrentView('financial')}>Tài chính</button>
                            <button className={`join-item btn btn-sm ${currentView === 'technical' ? 'btn-active' : ''}`} onClick={() => setCurrentView('technical')}>Kỹ thuật</button>
                        </div>
                        <span className="text-sm text-gray-500">{total} results</span>
                    </div>

                    <button className="btn btn-sm btn-ghost" onClick={() => downloadCSV(sortedStocks)}>📥 Export</button>
                </div>

                {/* Table Area */}
                <div className="flex-1 overflow-auto relative custom-scrollbar">
                    {loading ? (
                        <div className="flex items-center justify-center h-full">
                            <div className="loading loading-spinner loading-lg text-primary"></div>
                        </div>
                    ) : (
                        <table className="table table-pin-rows w-full">
                            <thead>
                                <tr className="bg-base-200">
                                    {/* Watchlist Star Column */}
                                    <th className="w-10 text-center">⭐</th>

                                    {columns.map((col, idx) => (
                                        <th
                                            key={col.key as string}
                                            className={`
                         whitespace-nowrap px-4 py-3 bg-base-200 text-xs font-semibold uppercase tracking-wider text-base-content/70
                         ${col.align === 'right' ? 'text-right' : col.align === 'center' ? 'text-center' : 'text-left'}
                         ${col.sortable ? 'cursor-pointer hover:bg-base-300 select-none' : ''}
                       `}
                                            onClick={() => col.sortable && handleSort(col.key as string)}
                                            style={{ width: col.width }}
                                        >
                                            <div className={`flex items-center gap-1 ${col.align === 'right' ? 'justify-end' : col.align === 'center' ? 'justify-center' : ''}`}>
                                                {col.label}
                                                {sortConfig?.key === col.key && (
                                                    <span>{sortConfig.direction === 'asc' ? '▲' : '▼'}</span>
                                                )}
                                            </div>
                                        </th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody className="bg-base-100 divide-y divide-base-300">
                                {sortedStocks.length === 0 ? (
                                    <tr><td colSpan={columns.length + 1} className="text-center py-10">No results found</td></tr>
                                ) : (
                                    sortedStocks.map(stock => (
                                        <tr key={stock.symbol} className="hover:bg-base-200/50 transition-colors group">
                                            <td className="text-center">
                                                <button
                                                    onClick={() => toggleWatchlist(stock.symbol)}
                                                    className={`text-lg transition-transform active:scale-95 ${watchlist.includes(stock.symbol) ? 'text-warning' : 'text-base-content/20 group-hover:text-base-content/50'}`}
                                                >
                                                    {watchlist.includes(stock.symbol) ? '★' : '☆'}
                                                </button>
                                            </td>
                                            {columns.map((col) => (
                                                <td
                                                    key={`${stock.symbol}-${col.key as string}`}
                                                    className={`
                            px-4 py-2 whitespace-nowrap text-sm border-r border-base-200 last:border-0
                            ${col.align === 'right' ? 'text-right' : col.align === 'center' ? 'text-center' : 'text-left'}
                          `}
                                                >
                                                    {col.render ? col.render(stock) : ((stock as any)[col.key as string])}
                                                </td>
                                            ))}
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    )}
                </div>
            </div>
        </div>
    );
}
