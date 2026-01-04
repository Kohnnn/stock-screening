import React, { useState, useEffect, useRef } from 'react';
import SmartBoardColumn from './SmartBoardColumn';
import WatchlistColumn from './WatchlistColumn';

interface Stock {
    symbol: string;
    current_price: number;
    percent_change: number;
    volume: number;
}

interface HighlightGroup {
    id: string;
    name: string;
    stocks: Stock[];
}

interface MarketIndex {
    index_code: string;
    value: number;
    change_value: number;
    change_percent: number;
    advances: number;
    declines: number;
    unchanged: number;
}

interface IndicesData {
    indices: MarketIndex[];
    from_database: boolean;
    updated_at: string;
}

const SECTORS_TO_SHOW = [
    { id: 'VN30', name: 'VN30', color: 'smart-board-title-white' },
    { id: 'Ngân hàng', name: 'Ngân hàng', color: 'smart-board-title-yellow' },
    { id: 'Bất động sản', name: 'Bất động sản', color: 'smart-board-title-red' },
    { id: 'Chứng khoán', name: 'Chứng khoán', color: 'smart-board-title-blue' },
    { id: 'Thép', name: 'Thép', color: 'smart-board-title-gray' },
    { id: 'Dầu khí', name: 'Dầu khí', color: 'smart-board-title-orange' },
    { id: 'Công nghệ', name: 'Công nghệ', color: 'smart-board-title-purple' },
    { id: 'Bán lẻ', name: 'Bán lẻ', color: 'smart-board-title-pink' },
];

const SmartBoard: React.FC = () => {
    const [sectorData, setSectorData] = useState<Record<string, Stock[]>>({});
    const [highlights, setHighlights] = useState<HighlightGroup[]>([]);
    const [activeHighlight, setActiveHighlight] = useState(0);
    const [loading, setLoading] = useState(true);
    const [indices, setIndices] = useState<MarketIndex[]>([]);
    const [indicesFromDb, setIndicesFromDb] = useState(false);
    const [lastUpdate, setLastUpdate] = useState<string>('');
    const prevIndicesRef = useRef<MarketIndex[]>([]);

    const fetchIndices = async () => {
        try {
            const baseUrl = import.meta.env.VITE_API_URL || '';
            const res = await fetch(`${baseUrl}/api/smart-board/indices`);
            if (res.ok) {
                const data: IndicesData = await res.json();
                prevIndicesRef.current = indices;
                setIndices(data.indices);
                setIndicesFromDb(data.from_database);
                setLastUpdate(new Date(data.updated_at).toLocaleTimeString('vi-VN', {
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit'
                }));
            }
        } catch (error) {
            console.error("Error fetching indices:", error);
        }
    };

    const fetchData = async () => {
        try {
            const baseUrl = import.meta.env.VITE_API_URL || '';

            // Fetch highlights
            const hRes = await fetch(`${baseUrl}/api/smart-board/highlights`);
            if (hRes.ok) {
                const hData = await hRes.json();
                setHighlights(hData.highlights || []);
            }

            // Fetch sectors
            const newSectorData: Record<string, Stock[]> = {};
            await Promise.all(SECTORS_TO_SHOW.map(async (sector) => {
                try {
                    const res = await fetch(`${baseUrl}/api/smart-board/sector/${encodeURIComponent(sector.id)}`);
                    if (res.ok) {
                        const data = await res.json();
                        newSectorData[sector.id] = data.stocks || [];
                    }
                } catch (e) {
                    console.error(`Failed to fetch sector ${sector.id}`, e);
                }
            }));
            setSectorData(newSectorData);
        } catch (error) {
            console.error("Error fetching Smart Board data:", error);
        } finally {
            setLoading(false);
        }
    };

    // Real-time price updates
    const fetchRealtimePrices = async () => {
        // Collect all visible symbols
        const allSymbols = new Set<string>();

        // Add highlight symbols
        highlights.forEach(group => {
            group.stocks.forEach(s => allSymbols.add(s.symbol));
        });

        // Add sector symbols
        Object.values(sectorData).forEach(stocks => {
            stocks.forEach(s => allSymbols.add(s.symbol));
        });

        if (allSymbols.size === 0) return;

        try {
            const baseUrl = import.meta.env.VITE_API_URL || '';
            // Chunk symbols if too many (API might have limit, but URL length is main concern)
            // For now, just try fetching VN30 + HOSE snapshot basics via 'group' or filtered symbols
            // But getting ALL HOSE/HNX is better via snapshot than URL list if list is huge.
            // Let's rely on the fact that existing sectors are limited (20 per sector).

            const symbolsList = Array.from(allSymbols).join(',');
            const res = await fetch(`${baseUrl}/api/stocks/realtime?symbols=${symbolsList}`);

            if (res.ok) {
                const data = await res.json();
                const updates: Record<string, any> = {};
                data.stocks.forEach((s: any) => {
                    updates[s.symbol] = s;
                });

                // Helper to update stock lists
                const updateStockList = (list: Stock[]) => {
                    return list.map(stock => {
                        const update = updates[stock.symbol];
                        if (update) {
                            return {
                                ...stock,
                                current_price: update.current_price || stock.current_price,
                                percent_change: update.percent_change || stock.percent_change,
                                volume: update.volume || stock.volume,
                            };
                        }
                        return stock;
                    });
                };

                // Update Highlights
                setHighlights(prev => prev.map(group => ({
                    ...group,
                    stocks: updateStockList(group.stocks)
                })));

                // Update Sector Data
                setSectorData(prev => {
                    const next: Record<string, Stock[]> = {};
                    Object.keys(prev).forEach(key => {
                        next[key] = updateStockList(prev[key]);
                    });
                    return next;
                });
            }
        } catch (err) {
            console.error("Realtime update failed:", err);
        }
    };

    useEffect(() => {
        fetchIndices();
        fetchData();

        // Indices refresh every 3 seconds
        const indicesInterval = setInterval(fetchIndices, 3000);
        // Base data refresh (highlights/sectors list) every 30 seconds (less frequent)
        const dataInterval = setInterval(fetchData, 30000);
        // Realtime prices every 3 seconds
        const realtimeInterval = setInterval(fetchRealtimePrices, 3000);

        return () => {
            clearInterval(indicesInterval);
            clearInterval(dataInterval);
            clearInterval(realtimeInterval);
        };
    }, []);

    const getChangeClass = (value: number) => {
        if (value > 0) return 'price-up';
        if (value < 0) return 'price-down';
        return 'price-neutral';
    };

    const getFlashClass = (indexCode: string, currentValue: number) => {
        const prev = prevIndicesRef.current.find(i => i.index_code === indexCode);
        if (!prev) return '';
        if (currentValue > prev.value) return 'price-flash-up';
        if (currentValue < prev.value) return 'price-flash-down';
        return '';
    };

    return (
        <div className="smart-board-container">
            {/* Data Source Indicator */}
            <div className="smart-board-status">
                <span className={`smart-board-status-indicator ${indicesFromDb ? 'status-live' : 'status-fallback'}`}>
                    {indicesFromDb ? '● Live' : '○ Demo'}
                </span>
                {lastUpdate && <span className="smart-board-timestamp">Cập nhật: {lastUpdate}</span>}
            </div>

            {/* Indices Row */}
            <div className="smart-board-indices">
                {indices.map((index) => (
                    <div
                        key={index.index_code}
                        className={`smart-board-index-card ${getFlashClass(index.index_code, index.value)}`}
                    >
                        <div className="smart-board-index-header">
                            <span className="smart-board-index-value">{index.value.toLocaleString('vi-VN', { maximumFractionDigits: 2 })}</span>
                            <span className={`smart-board-index-change ${getChangeClass(index.change_value)}`}>
                                {index.change_value > 0 ? '+' : ''}{index.change_value.toFixed(2)} ({index.change_percent > 0 ? '+' : ''}{index.change_percent.toFixed(2)}%)
                            </span>
                        </div>
                        <div className="smart-board-index-footer">
                            <span className="smart-board-index-name">{index.index_code}</span>
                            <div className="smart-board-index-stats">
                                <span className="price-up">▲{index.advances}</span>
                                <span className="price-neutral">■{index.unchanged}</span>
                                <span className="price-down">▼{index.declines}</span>
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {/* Main Grid */}
            <div className="smart-board-grid">
                <div className="smart-board-columns">
                    {/* Column 1: Watchlist */}
                    <div className="smart-board-column-wrapper">
                        <WatchlistColumn />
                    </div>

                    {/* Column 2: Highlights */}
                    <div className="smart-board-column">
                        <div className="smart-board-column-header smart-board-header-highlight">
                            <div className="smart-board-column-title-wrapper">
                                <span className="smart-board-column-icon">⚡</span>
                                <h3 className="smart-board-column-title smart-board-title-yellow">Nổi bật</h3>
                            </div>
                            <span className="smart-board-column-time">
                                {new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}
                            </span>
                        </div>

                        {/* Toggle Tabs */}
                        <div className="smart-board-tabs">
                            {(highlights.length > 0 ? highlights : [{ id: 'loading', name: 'Đang tải...' }]).map((group, idx) => (
                                <button
                                    key={group.id}
                                    onClick={() => setActiveHighlight(idx)}
                                    className={`smart-board-tab ${activeHighlight === idx ? 'active' : ''}`}
                                    disabled={highlights.length === 0}
                                >
                                    {group.name}
                                </button>
                            ))}
                        </div>

                        {/* Highlight Content */}
                        <div className="smart-board-column-content">
                            <SmartBoardColumn
                                title=""
                                stocks={highlights[activeHighlight]?.stocks || []}
                                loading={loading}
                            />
                        </div>
                    </div>

                    {/* Columns 3+: Sectors */}
                    {SECTORS_TO_SHOW.map((sector) => (
                        <div key={sector.id} className="smart-board-column-wrapper">
                            <SmartBoardColumn
                                title={sector.name}
                                titleColor={sector.color}
                                stocks={sectorData[sector.id] || []}
                                loading={loading}
                            />
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

export default SmartBoard;
