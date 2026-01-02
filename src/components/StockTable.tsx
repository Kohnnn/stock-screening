import React, { useState, useMemo } from 'react';
import { useLanguage } from '../contexts/LanguageContext';
import { Stock, SortConfig, SortDirection } from '../types';

// ============================================
// Props
// ============================================

interface StockTableProps {
    stocks: Stock[];
    loading?: boolean;
    onSelectStock?: (stock: Stock) => void;
    selectedStocks?: string[];
    onToggleSelect?: (symbol: string) => void;
}

// ============================================
// Sort Icon Component
// ============================================

function SortIcon({ direction }: { direction?: SortDirection }) {
    if (!direction) return <span className="sort-icon">↕</span>;
    return <span className="sort-icon">{direction === 'asc' ? '↑' : '↓'}</span>;
}

// ============================================
// Component
// ============================================

export function StockTable({
    stocks,
    loading,
    onSelectStock,
    selectedStocks = [],
    onToggleSelect,
}: StockTableProps) {
    const { t, formatCurrency, formatNumber, formatPercent } = useLanguage();
    const [sortConfig, setSortConfig] = useState<SortConfig | null>(null);

    // Sort stocks
    const sortedStocks = useMemo(() => {
        if (!sortConfig) return stocks;

        return [...stocks].sort((a, b) => {
            const aValue = a[sortConfig.key];
            const bValue = b[sortConfig.key];

            if (aValue === undefined || aValue === null) return 1;
            if (bValue === undefined || bValue === null) return -1;

            if (typeof aValue === 'string' && typeof bValue === 'string') {
                return sortConfig.direction === 'asc'
                    ? aValue.localeCompare(bValue)
                    : bValue.localeCompare(aValue);
            }

            if (typeof aValue === 'number' && typeof bValue === 'number') {
                return sortConfig.direction === 'asc'
                    ? aValue - bValue
                    : bValue - aValue;
            }

            return 0;
        });
    }, [stocks, sortConfig]);

    const handleSort = (key: keyof Stock) => {
        setSortConfig((prev) => {
            if (prev?.key === key) {
                if (prev.direction === 'asc') return { key, direction: 'desc' };
                if (prev.direction === 'desc') return null;
            }
            return { key, direction: 'asc' };
        });
    };

    const getExchangeClass = (exchange: string) => {
        switch (exchange) {
            case 'HOSE': return 'exchange-badge exchange-hose';
            case 'HNX': return 'exchange-badge exchange-hnx';
            case 'UPCOM': return 'exchange-badge exchange-upcom';
            default: return 'exchange-badge';
        }
    };

    const getPriceChangeClass = (change?: number) => {
        if (!change) return 'price-neutral';
        return change > 0 ? 'price-up' : 'price-down';
    };

    const formatPriceChange = (change?: number, percent?: number) => {
        if (change === undefined) return '-';
        const sign = change >= 0 ? '+' : '';
        const percentStr = percent !== undefined ? ` (${sign}${percent.toFixed(2)}%)` : '';
        return `${sign}${formatNumber(change, 0)}${percentStr}`;
    };

    const formatMarketCap = (value?: number) => {
        if (!value) return '-';
        if (value >= 1000) {
            return `${formatNumber(value / 1000, 1)} nghìn tỷ`;
        }
        return `${formatNumber(value, 0)} tỷ`;
    };

    if (loading) {
        return (
            <div className="loading-overlay">
                <div className="spinner"></div>
                <span>{t('common.loading')}</span>
            </div>
        );
    }

    if (stocks.length === 0) {
        return (
            <div className="empty-state">
                <div className="empty-state-icon">📊</div>
                <div className="empty-state-title">{t('screener.noResults')}</div>
            </div>
        );
    }

    return (
        <div className="table-container">
            <table className="table">
                <thead>
                    <tr>
                        {onToggleSelect && (
                            <th style={{ width: '40px' }}></th>
                        )}
                        <th
                            className="sortable"
                            onClick={() => handleSort('symbol')}
                        >
                            {t('table.symbol')}
                            {sortConfig?.key === 'symbol' && <SortIcon direction={sortConfig.direction} />}
                        </th>
                        <th
                            className="sortable"
                            onClick={() => handleSort('companyName')}
                        >
                            {t('table.companyName')}
                            {sortConfig?.key === 'companyName' && <SortIcon direction={sortConfig.direction} />}
                        </th>
                        <th>{t('table.exchange')}</th>
                        <th
                            className="sortable text-right"
                            onClick={() => handleSort('currentPrice')}
                        >
                            {t('table.price')}
                            {sortConfig?.key === 'currentPrice' && <SortIcon direction={sortConfig.direction} />}
                        </th>
                        <th className="text-right">{t('table.change')}</th>
                        <th
                            className="sortable text-right"
                            onClick={() => handleSort('marketCap')}
                        >
                            {t('table.marketCap')}
                            {sortConfig?.key === 'marketCap' && <SortIcon direction={sortConfig.direction} />}
                        </th>
                        <th
                            className="sortable text-right"
                            onClick={() => handleSort('pe')}
                        >
                            {t('table.pe')}
                            {sortConfig?.key === 'pe' && <SortIcon direction={sortConfig.direction} />}
                        </th>
                        <th
                            className="sortable text-right"
                            onClick={() => handleSort('pb')}
                        >
                            {t('table.pb')}
                            {sortConfig?.key === 'pb' && <SortIcon direction={sortConfig.direction} />}
                        </th>
                        <th
                            className="sortable text-right"
                            onClick={() => handleSort('roe')}
                        >
                            {t('table.roe')}
                            {sortConfig?.key === 'roe' && <SortIcon direction={sortConfig.direction} />}
                        </th>
                        <th>{t('table.sector')}</th>
                    </tr>
                </thead>
                <tbody>
                    {sortedStocks.map((stock) => (
                        <tr
                            key={stock.symbol}
                            onClick={() => onSelectStock?.(stock)}
                            style={{ cursor: onSelectStock ? 'pointer' : 'default' }}
                        >
                            {onToggleSelect && (
                                <td>
                                    <input
                                        type="checkbox"
                                        checked={selectedStocks.includes(stock.symbol)}
                                        onChange={() => onToggleSelect(stock.symbol)}
                                        onClick={(e) => e.stopPropagation()}
                                    />
                                </td>
                            )}
                            <td>
                                <strong>{stock.symbol}</strong>
                            </td>
                            <td className="text-muted text-sm">
                                {stock.companyName}
                            </td>
                            <td>
                                <span className={getExchangeClass(stock.exchange)}>
                                    {stock.exchange}
                                </span>
                            </td>
                            <td className="text-right font-bold">
                                {formatCurrency(stock.currentPrice || 0)}
                            </td>
                            <td className={`text-right ${getPriceChangeClass(stock.priceChange)}`}>
                                {formatPriceChange(stock.priceChange, stock.priceChangePercent)}
                            </td>
                            <td className="text-right">
                                {formatMarketCap(stock.marketCap)}
                            </td>
                            <td className="text-right">
                                {stock.pe ? formatNumber(stock.pe, 1) : '-'}
                            </td>
                            <td className="text-right">
                                {stock.pb ? formatNumber(stock.pb, 2) : '-'}
                            </td>
                            <td className="text-right">
                                {stock.roe ? `${formatNumber(stock.roe, 1)}%` : '-'}
                            </td>
                            <td className="text-muted text-sm">
                                {stock.sector || '-'}
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

export default StockTable;
