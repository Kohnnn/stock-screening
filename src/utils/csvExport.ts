/**
 * CSV Export Utility for VnStock Screener
 */

export interface ExportableStock {
    symbol: string;
    companyName?: string;
    exchange?: string;
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
    roa?: number;
    eps?: number;
}

/**
 * Convert stocks array to CSV string
 */
export function stocksToCSV(stocks: ExportableStock[]): string {
    const headers = [
        'Symbol',
        'Company Name',
        'Exchange',
        'Sector',
        'Industry',
        'Price',
        'Change %',
        'Volume',
        'Market Cap (Bn)',
        'P/E',
        'P/B',
        'ROE (%)',
        'ROA (%)',
        'EPS',
    ];

    const rows = stocks.map(stock => [
        stock.symbol || '',
        `"${(stock.companyName || '').replace(/"/g, '""')}"`, // Escape quotes
        stock.exchange || '',
        stock.sector || '',
        stock.industry || '',
        stock.currentPrice?.toFixed(0) || '',
        stock.priceChangePercent?.toFixed(2) || '',
        stock.volume?.toString() || '',
        stock.marketCap ? (stock.marketCap / 1_000_000_000).toFixed(2) : '',
        stock.pe?.toFixed(2) || '',
        stock.pb?.toFixed(2) || '',
        stock.roe ? (stock.roe * 100).toFixed(2) : '',
        stock.roa ? (stock.roa * 100).toFixed(2) : '',
        stock.eps?.toFixed(0) || '',
    ]);

    const csvContent = [
        headers.join(','),
        ...rows.map(row => row.join(','))
    ].join('\n');

    return csvContent;
}

/**
 * Download CSV file
 */
export function downloadCSV(stocks: ExportableStock[], filename?: string): void {
    const csv = stocksToCSV(stocks);
    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' }); // BOM for Excel UTF-8
    const url = URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', filename || `vnstock-screener-${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    URL.revokeObjectURL(url);
}
