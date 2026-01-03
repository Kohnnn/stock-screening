import { useState, useEffect, useMemo, useCallback } from 'react';
import { TradingViewChart } from './TradingViewChart';

// API Base URL
const API_BASE_URL = import.meta.env.VITE_API_URL || '';

// Types
interface Stock {
    symbol: string;
    companyName: string;
    exchange: string;
    sector?: string;
    industry?: string;
    currentPrice?: number;
    priceChangePercent?: number;
    marketCap?: number;
    pe?: number;
    pb?: number;
    ps?: number;
    roe?: number;
    roa?: number;
    eps?: number;
    bookValue?: number;
    totalDebt?: number;
    ownerEquity?: number;
    totalAssets?: number;
    debtToEquity?: number;
    cash?: number;
    foreignOwnership?: number;
    updatedAt?: string;
    dataSource?: string;
}

interface DataBrowserProps {
    onAnalyzeStock?: (symbol: string) => void;
}

export function DataBrowser({ onAnalyzeStock }: DataBrowserProps) {
    const [stocks, setStocks] = useState<Stock[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
    const [search, setSearch] = useState('');
    const [activeTab, setActiveTab] = useState<'chart' | 'financials' | 'profile'>('chart');

    // Fetch stocks on mount
    const fetchStocks = useCallback(async () => {
        setLoading(true);
        try {
            const res = await fetch(`${API_BASE_URL}/api/stocks/screener?page_size=500`);
            if (res.ok) {
                const data = await res.json();
                const mapped = data.stocks.map((s: any) => ({
                    symbol: s.symbol,
                    companyName: s.company_name || s.symbol,
                    exchange: s.exchange || 'HOSE',
                    sector: s.sector,
                    industry: s.industry,
                    currentPrice: s.current_price,
                    priceChangePercent: s.percent_change,
                    marketCap: s.market_cap ? s.market_cap / 1_000_000_000 : undefined,
                    pe: s.pe_ratio,
                    pb: s.pb_ratio,
                    ps: s.ps_ratio,
                    roe: s.roe ? s.roe * 100 : undefined,
                    roa: s.roa ? s.roa * 100 : undefined,
                    eps: s.eps,
                    bookValue: s.book_value,
                    totalDebt: s.total_debt,
                    ownerEquity: s.owner_equity,
                    totalAssets: s.total_assets,
                    debtToEquity: s.debt_to_equity,
                    cash: s.cash,
                    foreignOwnership: s.foreign_ownership,
                    dataSource: s.data_source,
                }));
                setStocks(mapped);
                if (mapped.length > 0 && !selectedSymbol) {
                    setSelectedSymbol(mapped[0].symbol);
                }
            }
        } catch (err) {
            console.error('Failed to fetch stocks:', err);
        } finally {
            setLoading(false);
        }
    }, [selectedSymbol]);

    useEffect(() => {
        fetchStocks();
    }, []);

    // Filter stocks
    const filteredStocks = useMemo(() => {
        if (!search) return stocks;
        const q = search.toLowerCase();
        return stocks.filter(s =>
            s.symbol.toLowerCase().includes(q) ||
            (s.companyName && s.companyName.toLowerCase().includes(q))
        );
    }, [stocks, search]);

    const selectedStock = useMemo(() =>
        stocks.find(s => s.symbol === selectedSymbol),
        [stocks, selectedSymbol]
    );

    // Format large numbers
    const formatBillion = (val?: number) => val ? val.toLocaleString(undefined, { maximumFractionDigits: 1 }) : '-';
    const formatPercent = (val?: number) => val !== undefined ? `${val.toFixed(1)}%` : '-';
    const formatNumber = (val?: number, decimals = 1) => val !== undefined ? val.toFixed(decimals) : '-';

    return (
        <div className="data-browser">
            {/* Sidebar: Stock List */}
            <div className="browser-sidebar">
                <div className="browser-search">
                    <input
                        type="text"
                        placeholder="🔍 Tìm kiếm mã..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="form-input"
                    />
                </div>
                <div className="browser-stats">
                    <span>📊 {stocks.length} cổ phiếu</span>
                </div>
                <div className="stock-list">
                    {loading ? (
                        <div className="p-4 text-center">⏳ Đang tải...</div>
                    ) : (
                        filteredStocks.map(stock => (
                            <div
                                key={stock.symbol}
                                className={`stock-item ${selectedSymbol === stock.symbol ? 'active' : ''}`}
                                onClick={() => setSelectedSymbol(stock.symbol)}
                            >
                                <div className="stock-item-header">
                                    <span className="stock-symbol">{stock.symbol}</span>
                                    <span className={`stock-price ${stock.priceChangePercent && stock.priceChangePercent > 0 ? 'text-up' : 'text-down'}`}>
                                        {stock.currentPrice?.toLocaleString()}
                                    </span>
                                </div>
                                <div className="stock-name">{stock.companyName}</div>
                            </div>
                        ))
                    )}
                </div>
            </div>

            {/* Main Content */}
            <div className="browser-main">
                {selectedStock ? (
                    <>
                        {/* Header with AI Button */}
                        <div className="browser-header">
                            <div className="header-info">
                                <h1>{selectedStock.symbol}</h1>
                                <div className="header-badges">
                                    <span className={`exchange-badge exchange-${selectedStock.exchange.toLowerCase()}`}>
                                        {selectedStock.exchange}
                                    </span>
                                    <span className="sector-badge">{selectedStock.industry || selectedStock.sector || 'N/A'}</span>
                                    {selectedStock.dataSource && (
                                        <span className="source-badge">{selectedStock.dataSource}</span>
                                    )}
                                </div>
                                <h2>{selectedStock.companyName}</h2>
                            </div>
                            <div className="header-actions">
                                <div className="header-price">
                                    <div className="big-price">
                                        {selectedStock.currentPrice?.toLocaleString()} VND
                                    </div>
                                    <div className={`price-change ${selectedStock.priceChangePercent && selectedStock.priceChangePercent > 0 ? 'text-up' : 'text-down'}`}>
                                        {selectedStock.priceChangePercent?.toFixed(2)}%
                                    </div>
                                </div>
                                {onAnalyzeStock && (
                                    <button
                                        className="btn btn-primary ai-analyze-btn"
                                        onClick={() => onAnalyzeStock(selectedStock.symbol)}
                                    >
                                        🤖 Phân tích AI
                                    </button>
                                )}
                            </div>
                        </div>

                        {/* Tabs */}
                        <div className="browser-tabs">
                            <button
                                className={`browser-tab ${activeTab === 'chart' ? 'active' : ''}`}
                                onClick={() => setActiveTab('chart')}
                            >
                                📊 Biểu đồ
                            </button>
                            <button
                                className={`browser-tab ${activeTab === 'financials' ? 'active' : ''}`}
                                onClick={() => setActiveTab('financials')}
                            >
                                💰 Tài chính
                            </button>
                            <button
                                className={`browser-tab ${activeTab === 'profile' ? 'active' : ''}`}
                                onClick={() => setActiveTab('profile')}
                            >
                                🏢 Hồ sơ
                            </button>
                        </div>

                        {/* Tab Content */}
                        <div className="browser-content">
                            {activeTab === 'chart' && (
                                <div className="chart-container">
                                    <TradingViewChart
                                        symbol={selectedStock.symbol}
                                        exchange={selectedStock.exchange}
                                        height={500}
                                    />
                                </div>
                            )}

                            {activeTab === 'financials' && (
                                <div className="financials-grid">
                                    <div className="metric-card">
                                        <h3>Định giá</h3>
                                        <div className="metric-row"><span>P/E</span> <strong>{formatNumber(selectedStock.pe)}</strong></div>
                                        <div className="metric-row"><span>P/B</span> <strong>{formatNumber(selectedStock.pb)}</strong></div>
                                        <div className="metric-row"><span>P/S</span> <strong>{formatNumber(selectedStock.ps)}</strong></div>
                                        <div className="metric-row"><span>EPS</span> <strong>{formatNumber(selectedStock.eps, 0)} VND</strong></div>
                                        <div className="metric-row"><span>Book Value</span> <strong>{formatBillion(selectedStock.bookValue)}</strong></div>
                                    </div>
                                    <div className="metric-card">
                                        <h3>Hiệu quả</h3>
                                        <div className="metric-row"><span>ROE</span> <strong>{formatPercent(selectedStock.roe)}</strong></div>
                                        <div className="metric-row"><span>ROA</span> <strong>{formatPercent(selectedStock.roa)}</strong></div>
                                    </div>
                                    <div className="metric-card">
                                        <h3>Quy mô</h3>
                                        <div className="metric-row"><span>Vốn hóa</span> <strong>{formatBillion(selectedStock.marketCap)} tỷ</strong></div>
                                        <div className="metric-row"><span>Tổng tài sản</span> <strong>{formatBillion(selectedStock.totalAssets)} tỷ</strong></div>
                                        <div className="metric-row"><span>Vốn CSH</span> <strong>{formatBillion(selectedStock.ownerEquity)} tỷ</strong></div>
                                    </div>
                                    <div className="metric-card">
                                        <h3>Tài chính</h3>
                                        <div className="metric-row"><span>Nợ</span> <strong>{formatBillion(selectedStock.totalDebt)} tỷ</strong></div>
                                        <div className="metric-row"><span>Nợ/VCSH</span> <strong>{formatPercent(selectedStock.debtToEquity)}</strong></div>
                                        <div className="metric-row"><span>Tiền mặt</span> <strong>{formatBillion(selectedStock.cash)} tỷ</strong></div>
                                        <div className="metric-row"><span>NN sở hữu</span> <strong>{formatPercent(selectedStock.foreignOwnership)}</strong></div>
                                    </div>
                                </div>
                            )}

                            {activeTab === 'profile' && (
                                <div className="profile-section">
                                    <div className="profile-grid">
                                        <div className="profile-item">
                                            <label>Mã CK</label>
                                            <value>{selectedStock.symbol}</value>
                                        </div>
                                        <div className="profile-item">
                                            <label>Sàn</label>
                                            <value>{selectedStock.exchange}</value>
                                        </div>
                                        <div className="profile-item">
                                            <label>Ngành</label>
                                            <value>{selectedStock.sector || 'N/A'}</value>
                                        </div>
                                        <div className="profile-item">
                                            <label>Nhóm ngành</label>
                                            <value>{selectedStock.industry || 'N/A'}</value>
                                        </div>
                                        <div className="profile-item full-width">
                                            <label>Tên công ty</label>
                                            <value>{selectedStock.companyName}</value>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    </>
                ) : (
                    <div className="empty-state">👈 Chọn một cổ phiếu để xem chi tiết</div>
                )}
            </div>
        </div>
    );
}

