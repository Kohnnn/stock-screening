import React, { useState, useEffect } from 'react';

// Using Unicode icons instead of lucide-react
const PlusIcon = () => <span style={{ fontSize: '14px' }}>➕</span>;
const TrashIcon = () => <span style={{ fontSize: '12px' }}>🗑️</span>;

interface Stock {
    symbol: string;
    current_price: number;
    percent_change: number;
    volume: number;
}

const formatVolume = (vol: number) => {
    if (vol >= 1000000) return `${(vol / 1000000).toFixed(1)}m`;
    if (vol >= 1000) return `${(vol / 1000).toFixed(1)}k`;
    return vol.toString();
};

const formatPrice = (price: number) => {
    if (!price) return '-';
    return price.toLocaleString('vi-VN');
};

const WatchlistColumn: React.FC = () => {
    const [watchlist, setWatchlist] = useState<string[]>([]);
    const [stocks, setStocks] = useState<Stock[]>([]);
    const [loading, setLoading] = useState(false);
    const [showAdd, setShowAdd] = useState(false);
    const [newSymbol, setNewSymbol] = useState('');

    // Load watchlist from local storage
    useEffect(() => {
        const saved = localStorage.getItem('vnstock_watchlist');
        if (saved) {
            setWatchlist(JSON.parse(saved));
        } else {
            // Default stocks if empty
            const defaults = ['VCB', 'HPG', 'FPT', 'SSI'];
            setWatchlist(defaults);
            localStorage.setItem('vnstock_watchlist', JSON.stringify(defaults));
        }
    }, []);

    // Fetch data for watchlist
    useEffect(() => {
        const fetchData = async () => {
            if (watchlist.length === 0) {
                setStocks([]);
                return;
            }

            setLoading(true);
            try {
                const baseUrl = import.meta.env.VITE_API_URL || '';
                const promises = watchlist.map(symbol =>
                    fetch(`${baseUrl}/api/stocks/${symbol}`)
                        .then(res => res.ok ? res.json() : null)
                        .catch(() => null)
                );

                const results = await Promise.all(promises);
                const validStocks = results.filter(s => s !== null).map(s => ({
                    symbol: s.symbol,
                    current_price: s.current_price || 0,
                    percent_change: s.percent_change || 0,
                    volume: s.volume || 0
                }));

                setStocks(validStocks);
            } catch (error) {
                console.error('Error fetching watchlist:', error);
            } finally {
                setLoading(false);
            }
        };

        if (watchlist.length > 0) {
            fetchData();
            const interval = setInterval(fetchData, 10000); // Refresh every 10s
            return () => clearInterval(interval);
        }
    }, [watchlist]);

    const handleAddToken = (e: React.FormEvent) => {
        e.preventDefault();
        if (newSymbol && !watchlist.includes(newSymbol.toUpperCase())) {
            const updated = [...watchlist, newSymbol.toUpperCase()];
            setWatchlist(updated);
            localStorage.setItem('vnstock_watchlist', JSON.stringify(updated));
            setNewSymbol('');
            setShowAdd(false);
        }
    };

    const handleRemove = (symbol: string) => {
        const updated = watchlist.filter(s => s !== symbol);
        setWatchlist(updated);
        localStorage.setItem('vnstock_watchlist', JSON.stringify(updated));
    };

    const getChangeClass = (change: number) => {
        if (change > 0) return 'price-up';
        if (change < 0) return 'price-down';
        return 'price-neutral';
    };

    return (
        <div className="smart-board-column">
            <div className="smart-board-column-header smart-board-header-watchlist">
                <div className="smart-board-column-title-wrapper">
                    <span className="smart-board-column-icon">⚓</span>
                    <h3 className="smart-board-column-title smart-board-title-blue">Quan tâm</h3>
                </div>
                <button
                    onClick={() => setShowAdd(!showAdd)}
                    className="smart-board-add-btn"
                    title="Thêm mã"
                >
                    <PlusIcon />
                </button>
            </div>

            {showAdd && (
                <form onSubmit={handleAddToken} className="smart-board-add-form">
                    <input
                        type="text"
                        value={newSymbol}
                        onChange={(e) => setNewSymbol(e.target.value)}
                        placeholder="Nhập mã CP..."
                        className="smart-board-add-input"
                        autoFocus
                    />
                </form>
            )}

            {watchlist.length === 0 ? (
                <div className="smart-board-empty-watchlist">
                    <p>Bạn chưa có danh mục cổ phiếu quan tâm nào!</p>
                    <button
                        onClick={() => setShowAdd(true)}
                        className="smart-board-create-btn"
                    >
                        <PlusIcon /> Tạo mới ngay
                    </button>
                </div>
            ) : (
                <>
                    <div className="smart-board-table-header">
                        <div>Mã</div>
                        <div className="text-right">Giá</div>
                        <div className="text-right">+/-</div>
                        <div className="text-right">KL</div>
                    </div>
                    <div className="smart-board-column-content">
                        {loading ? (
                            <div className="smart-board-loading">
                                <div className="spinner"></div>
                            </div>
                        ) : (
                            <div className="smart-board-stock-list">
                                {stocks.map((stock) => {
                                    const changeClass = getChangeClass(stock.percent_change);

                                    return (
                                        <div key={stock.symbol} className="smart-board-stock-row smart-board-stock-row-hoverable">
                                            <div className={`smart-board-symbol ${changeClass}`}>
                                                {stock.symbol}
                                            </div>
                                            <div className={`smart-board-price ${changeClass}`}>
                                                {formatPrice(stock.current_price)}
                                            </div>
                                            <div className={`smart-board-change ${changeClass}`}>
                                                <span className="smart-board-change-badge">
                                                    {stock.percent_change > 0 ? '+' : ''}{(stock.percent_change || 0).toFixed(1)}%
                                                </span>
                                            </div>
                                            <div className="smart-board-volume">
                                                {formatVolume(stock.volume || 0)}
                                            </div>

                                            {/* Delete button on hover */}
                                            <button
                                                onClick={(e) => { e.stopPropagation(); handleRemove(stock.symbol); }}
                                                className="smart-board-delete-btn"
                                                title="Xóa"
                                            >
                                                <TrashIcon />
                                            </button>
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </div>
                </>
            )}
        </div>
    );
};

export default WatchlistColumn;
