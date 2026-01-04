import React from 'react';

interface Stock {
    symbol: string;
    current_price: number;
    percent_change: number;
    volume: number;
}

interface SmartBoardColumnProps {
    title: string;
    titleColor?: string;
    stocks: Stock[];
    loading?: boolean;
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

const SmartBoardColumn: React.FC<SmartBoardColumnProps> = ({ title, titleColor = 'smart-board-title-default', stocks, loading }) => {
    const getChangeClass = (change: number) => {
        if (change > 0) return 'price-up';
        if (change < 0) return 'price-down';
        return 'price-neutral';
    };

    return (
        <div className="smart-board-column">
            {/* Header - only show if title is provided */}
            {title && (
                <div className="smart-board-column-header">
                    <h3 className={`smart-board-column-title ${titleColor}`}>{title}</h3>
                </div>
            )}

            {/* Column Headers */}
            <div className="smart-board-table-header">
                <div>Mã</div>
                <div className="text-right">Giá</div>
                <div className="text-right">+/-</div>
                <div className="text-right">KL</div>
            </div>

            {/* Content */}
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
                                <div key={stock.symbol} className="smart-board-stock-row">
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
                                </div>
                            );
                        })}

                        {stocks.length === 0 && (
                            <div className="smart-board-empty">
                                Chưa có dữ liệu
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};

export default SmartBoardColumn;
