import { useState, useEffect } from 'react';
import { PriceChart } from './PriceChart';
import { CompanyProfile } from './CompanyProfile';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

interface DataBrowserProps {
    onAnalyzeStock?: (symbol: string) => void;
}

export function DataBrowser({ onAnalyzeStock }: DataBrowserProps) {
    const [stocks, setStocks] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState<'chart' | 'financials' | 'profile' | 'shareholders'>('financials');
    const [searchQuery, setSearchQuery] = useState('');

    useEffect(() => {
        fetch(`${API_BASE_URL}/api/stocks/screener?page_size=1500`)
            .then(res => res.json())
            .then(data => {
                if (data.stocks) {
                    setStocks(data.stocks);
                    if (data.stocks.length > 0) setSelectedSymbol(data.stocks[0].symbol);
                } else {
                    setStocks([]);
                }
                setLoading(false);
            })
            .catch(err => {
                console.error(err);
                setError(err.message);
                setLoading(false);
            });
    }, []);

    const filteredStocks = stocks.filter(s =>
        s.symbol?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        s.company_name?.toLowerCase().includes(searchQuery.toLowerCase())
    );

    const selectedStock = stocks.find(s => s.symbol === selectedSymbol);

    if (loading) return <div className="p-4">Loading data...</div>;
    if (error) return <div className="p-4 text-red-500">Error: {error}</div>;

    return (
        <div className="flex h-full">
            {/* Sidebar */}
            <div className="w-1/4 border-r overflow-auto p-2 bg-base-200">
                <h2 className="font-bold p-2 sticky top-0 bg-base-200 z-10">Stocks ({filteredStocks.length}/{stocks.length})</h2>
                <input
                    type="text"
                    placeholder="Search stock..."
                    className="input input-sm input-bordered w-full mb-2 sticky top-10 bg-base-200 z-10"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                />
                <div className="max-h-[calc(100vh-200px)] overflow-y-auto">
                    {filteredStocks.map(s => (
                        <div
                            key={s.symbol}
                            className={`p-2 cursor-pointer hover:bg-base-300 ${selectedSymbol === s.symbol ? 'bg-primary text-primary-content' : ''}`}
                            onClick={() => setSelectedSymbol(s.symbol)}
                        >
                            <div className="font-bold">{s.symbol}</div>
                            <div className="text-xs truncate">{s.company_name}</div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Main Content */}
            <div className="w-3/4 flex flex-col h-full bg-base-100">
                {selectedStock ? (
                    <>
                        <div className="p-4 border-b flex justify-between items-center bg-base-100">
                            <div>
                                <h1 className="text-2xl font-bold">{selectedStock.symbol}</h1>
                                <div>{selectedStock.company_name}</div>
                            </div>
                            <div className="tabs tabs-boxed">
                                <a className={`tab ${activeTab === 'chart' ? 'tab-active' : ''}`} onClick={() => setActiveTab('chart')}>Chart</a>
                                <a className={`tab ${activeTab === 'financials' ? 'tab-active' : ''}`} onClick={() => setActiveTab('financials')}>Financials</a>
                                <a className={`tab ${activeTab === 'profile' ? 'tab-active' : ''}`} onClick={() => setActiveTab('profile')}>Profile</a>
                            </div>
                        </div>
                        <div className="p-4 overflow-auto flex-1">
                            {activeTab === 'financials' && (
                                <div>
                                    <h3 className="font-bold mb-4">Key Metrics</h3>
                                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                                        <div className="stat bg-base-200 rounded p-4">
                                            <div className="stat-title">Price</div>
                                            <div className="stat-value text-lg">{selectedStock.current_price ? selectedStock.current_price.toLocaleString() : '-'}</div>
                                        </div>
                                        <div className="stat bg-base-200 rounded p-4">
                                            <div className="stat-title">Change %</div>
                                            <div className={`stat-value text-lg ${selectedStock.percent_change > 0 ? 'text-green-500' : selectedStock.percent_change < 0 ? 'text-red-500' : ''}`}>
                                                {selectedStock.percent_change ? `${selectedStock.percent_change > 0 ? '+' : ''}${selectedStock.percent_change.toFixed(2)}%` : '-'}
                                            </div>
                                        </div>
                                        <div className="stat bg-base-200 rounded p-4">
                                            <div className="stat-title">P/E</div>
                                            <div className="stat-value text-lg">{selectedStock.pe_ratio?.toFixed(2) || '-'}</div>
                                        </div>
                                        <div className="stat bg-base-200 rounded p-4">
                                            <div className="stat-title">P/B</div>
                                            <div className="stat-value text-lg">{selectedStock.pb_ratio?.toFixed(2) || '-'}</div>
                                        </div>
                                        <div className="stat bg-base-200 rounded p-4">
                                            <div className="stat-title">EPS</div>
                                            <div className="stat-value text-lg">{selectedStock.eps?.toLocaleString() || '-'}</div>
                                        </div>
                                        <div className="stat bg-base-200 rounded p-4">
                                            <div className="stat-title">Market Cap</div>
                                            <div className="stat-value text-lg">{selectedStock.market_cap ? `${(selectedStock.market_cap).toFixed(0)} B` : '-'}</div>
                                        </div>
                                        <div className="stat bg-base-200 rounded p-4">
                                            <div className="stat-title">ROE</div>
                                            <div className="stat-value text-lg">{selectedStock.roe ? `${selectedStock.roe.toFixed(2)}%` : '-'}</div>
                                        </div>
                                        <div className="stat bg-base-200 rounded p-4">
                                            <div className="stat-title">Volume</div>
                                            <div className="stat-value text-lg">{selectedStock.volume?.toLocaleString() || '-'}</div>
                                        </div>
                                    </div>
                                    <h3 className="font-bold mt-6 mb-4">Financial Data</h3>
                                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                                        <div className="stat bg-base-200 rounded p-4">
                                            <div className="stat-title">Revenue (B)</div>
                                            <div className="stat-value text-lg">{selectedStock.revenue ? (selectedStock.revenue / 1e9).toFixed(0) : '-'}</div>
                                        </div>
                                        <div className="stat bg-base-200 rounded p-4">
                                            <div className="stat-title">Profit (B)</div>
                                            <div className="stat-value text-lg">{selectedStock.profit ? (selectedStock.profit / 1e9).toFixed(0) : '-'}</div>
                                        </div>
                                        <div className="stat bg-base-200 rounded p-4">
                                            <div className="stat-title">Total Assets (B)</div>
                                            <div className="stat-value text-lg">{selectedStock.total_assets ? (selectedStock.total_assets / 1e9).toFixed(0) : '-'}</div>
                                        </div>
                                        <div className="stat bg-base-200 rounded p-4">
                                            <div className="stat-title">Equity (B)</div>
                                            <div className="stat-value text-lg">{selectedStock.owner_equity ? (selectedStock.owner_equity / 1e9).toFixed(0) : '-'}</div>
                                        </div>
                                        <div className="stat bg-base-200 rounded p-4">
                                            <div className="stat-title">Gross Margin</div>
                                            <div className="stat-value text-lg">{selectedStock.gross_margin ? `${selectedStock.gross_margin.toFixed(2)}%` : '-'}</div>
                                        </div>
                                        <div className="stat bg-base-200 rounded p-4">
                                            <div className="stat-title">Net Margin</div>
                                            <div className="stat-value text-lg">{selectedStock.net_margin ? `${selectedStock.net_margin.toFixed(2)}%` : '-'}</div>
                                        </div>
                                        <div className="stat bg-base-200 rounded p-4">
                                            <div className="stat-title">Rev. Growth</div>
                                            <div className={`stat-value text-lg ${selectedStock.revenue_growth_1y > 0 ? 'text-green-500' : selectedStock.revenue_growth_1y < 0 ? 'text-red-500' : ''}`}>
                                                {selectedStock.revenue_growth_1y ? `${selectedStock.revenue_growth_1y > 0 ? '+' : ''}${selectedStock.revenue_growth_1y.toFixed(2)}%` : '-'}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )}
                            {activeTab === 'chart' && (
                                <div className="h-96">
                                    <PriceChart symbol={selectedStock.symbol} height={400} showVolume={true} />
                                </div>
                            )}
                            {activeTab === 'profile' && (
                                <div className="h-full overflow-y-auto">
                                    <CompanyProfile symbol={selectedStock.symbol} />
                                </div>
                            )}
                        </div>
                    </>
                ) : (
                    <div className="p-10 text-center">Select a stock</div>
                )}
            </div>
        </div>
    );
}

