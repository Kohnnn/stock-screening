import React, { useState, useCallback } from 'react';
import { LanguageProvider, useLanguage } from './contexts/LanguageContext';
import { ThemeProvider, useTheme } from './contexts/ThemeContext';
import { AIAnalysis } from './components/AIAnalysis';
import { DataBrowser } from './components/DataBrowser';
import { TradingViewChart } from './components/TradingViewChart';
import { StockScreener } from './components/StockScreener';
import SmartBoard from './components/SmartBoard';
import { Stock } from './types';
import './index.css';

// API Base URL - empty string uses relative paths (works with nginx proxy in Docker)
const API_BASE_URL = import.meta.env.VITE_API_URL || '';

// ============================================
// Header Component
// ============================================

function Header() {
  const { language, setLanguage, t } = useLanguage();
  const { toggleTheme, isDark } = useTheme();

  return (
    <header className="header">
      <div className="header-content">
        <div className="header-title">
          <span>🇻🇳</span>
          <span>{t('app.title')}</span>
        </div>
        <div className="header-actions">
          <button
            className="btn btn-icon"
            onClick={() => setLanguage(language === 'vi' ? 'en' : 'vi')}
            title={language === 'vi' ? 'Switch to English' : 'Chuyển sang Tiếng Việt'}
          >
            {language === 'vi' ? '🇻🇳 VI' : '🇺🇸 EN'}
          </button>
          <button
            className="btn btn-icon"
            onClick={toggleTheme}
            title={isDark ? 'Light mode' : 'Dark mode'}
          >
            {isDark ? '☀️' : '🌙'}
          </button>
        </div>
      </div>
    </header>
  );
}

// ============================================
// Mock Data (Kept for StockComparison fallback)
// ============================================

const MOCK_STOCKS: Stock[] = [
  { symbol: 'VCB', companyName: 'Ngân hàng TMCP Ngoại thương Việt Nam', exchange: 'HOSE', sector: 'Ngân hàng', currentPrice: 85000, priceChange: 1500, priceChangePercent: 1.8, volume: 2500000, marketCap: 398000, pe: 12.5, pb: 2.8, roe: 22.5, isActive: true },
  { symbol: 'VIC', companyName: 'Tập đoàn Vingroup', exchange: 'HOSE', sector: 'Bất động sản', currentPrice: 42000, priceChange: -800, priceChangePercent: -1.9, volume: 3200000, marketCap: 176000, pe: 45.2, pb: 1.9, roe: 4.2, isActive: true },
  { symbol: 'VHM', companyName: 'CTCP Vinhomes', exchange: 'HOSE', sector: 'Bất động sản', currentPrice: 38500, priceChange: 500, priceChangePercent: 1.3, volume: 4100000, marketCap: 129000, pe: 8.3, pb: 1.4, roe: 16.8, isActive: true },
  { symbol: 'HPG', companyName: 'CTCP Tập đoàn Hòa Phát', exchange: 'HOSE', sector: 'Thép', currentPrice: 24800, priceChange: 200, priceChangePercent: 0.8, volume: 8500000, marketCap: 116000, pe: 7.2, pb: 1.1, roe: 15.3, isActive: true },
  { symbol: 'TCB', companyName: 'Ngân hàng TMCP Kỹ thương Việt Nam', exchange: 'HOSE', sector: 'Ngân hàng', currentPrice: 23500, priceChange: 300, priceChangePercent: 1.3, volume: 6200000, marketCap: 82000, pe: 5.8, pb: 0.95, roe: 16.5, isActive: true },
  { symbol: 'BID', companyName: 'Ngân hàng TMCP Đầu tư và Phát triển Việt Nam', exchange: 'HOSE', sector: 'Ngân hàng', currentPrice: 43200, priceChange: -200, priceChangePercent: -0.5, volume: 1800000, marketCap: 218000, pe: 14.2, pb: 2.1, roe: 15.1, isActive: true },
  { symbol: 'CTG', companyName: 'Ngân hàng TMCP Công Thương Việt Nam', exchange: 'HOSE', sector: 'Ngân hàng', currentPrice: 28500, priceChange: 400, priceChangePercent: 1.4, volume: 3400000, marketCap: 134000, pe: 8.9, pb: 1.3, roe: 14.8, isActive: true },
  { symbol: 'GAS', companyName: 'Tổng CTCP Khí Việt Nam', exchange: 'HOSE', sector: 'Dầu khí', currentPrice: 75000, priceChange: 1000, priceChangePercent: 1.4, volume: 1200000, marketCap: 143000, pe: 12.8, pb: 2.5, roe: 19.5, isActive: true },
  { symbol: 'MSN', companyName: 'CTCP Tập đoàn Masan', exchange: 'HOSE', sector: 'Hàng tiêu dùng', currentPrice: 72000, priceChange: -500, priceChangePercent: -0.7, volume: 1500000, marketCap: 85000, pe: 28.5, pb: 2.8, roe: 9.8, isActive: true },
  { symbol: 'POW', companyName: 'Tổng CTCP Điện lực Dầu khí Việt Nam', exchange: 'HOSE', sector: 'Điện', currentPrice: 11200, priceChange: 100, priceChangePercent: 0.9, volume: 5600000, marketCap: 26000, pe: 9.5, pb: 0.85, roe: 8.9, isActive: true },
  { symbol: 'VNM', companyName: 'CTCP Sữa Việt Nam', exchange: 'HOSE', sector: 'Thực phẩm', currentPrice: 68500, priceChange: 800, priceChangePercent: 1.2, volume: 2100000, marketCap: 143000, pe: 16.2, pb: 4.2, roe: 26.0, isActive: true },
  { symbol: 'FPT', companyName: 'CTCP FPT', exchange: 'HOSE', sector: 'Công nghệ', currentPrice: 92000, priceChange: 2000, priceChangePercent: 2.2, volume: 3800000, marketCap: 98000, pe: 18.5, pb: 4.8, roe: 26.5, isActive: true },
  { symbol: 'MWG', companyName: 'CTCP Đầu tư Thế Giới Di Động', exchange: 'HOSE', sector: 'Bán lẻ', currentPrice: 45000, priceChange: -300, priceChangePercent: -0.7, volume: 4200000, marketCap: 65000, pe: 11.2, pb: 2.1, roe: 18.8, isActive: true },
  { symbol: 'ACB', companyName: 'Ngân hàng TMCP Á Châu', exchange: 'HNX', sector: 'Ngân hàng', currentPrice: 22800, priceChange: 200, priceChangePercent: 0.9, volume: 5100000, marketCap: 72000, pe: 6.2, pb: 1.05, roe: 17.0, isActive: true },
  { symbol: 'SHB', companyName: 'Ngân hàng TMCP Sài Gòn - Hà Nội', exchange: 'HNX', sector: 'Ngân hàng', currentPrice: 11500, priceChange: -100, priceChangePercent: -0.9, volume: 8200000, marketCap: 38000, pe: 5.5, pb: 0.72, roe: 13.2, isActive: true },
];

// ============================================
// Stock Comparison (Original)
// ============================================

function StockComparisonOriginal() {
  const { t, formatCurrency, formatNumber } = useLanguage();
  const [searchTerm, setSearchTerm] = useState('');
  const [suggestions, setSuggestions] = useState<Stock[]>([]);
  const [selectedStocks, setSelectedStocks] = useState<Stock[]>([]);

  const searchStocks = useCallback(async (query: string) => {
    if (!query.trim() || query.length < 2) {
      setSuggestions([]);
      return;
    }

    try {
      const res = await fetch(`${API_BASE_URL}/api/stocks?search=${query}&page_size=10`);
      if (res.ok) {
        const data = await res.json();
        const mapped = data.stocks.map((s: any) => ({
          symbol: s.symbol,
          companyName: s.company_name,
          exchange: s.exchange,
          currentPrice: s.current_price,
          pe: s.pe_ratio,
          marketCap: s.market_cap,
          sector: s.sector,
          isActive: true
        }));
        setSuggestions(mapped);
      }
    } catch (e) {
      console.error(e);
      // Fallback to local mock data
      const mockMatches = MOCK_STOCKS.filter(s =>
        s.symbol.includes(query.toUpperCase())
      );
      setSuggestions(mockMatches);
    }
  }, []);

  const addToComparison = (stock: Stock) => {
    if (selectedStocks.length >= 5) return;
    if (selectedStocks.some(s => s.symbol === stock.symbol)) return;
    setSelectedStocks([...selectedStocks, stock]);
    setSearchTerm('');
    setSuggestions([]);
  };

  const removeFromComparison = (symbol: string) => {
    setSelectedStocks(selectedStocks.filter(s => s.symbol !== symbol));
  };

  const metrics = [
    { key: 'currentPrice', label: t('table.price'), format: (v: number) => formatCurrency(v || 0) },
    { key: 'priceChangePercent', label: t('table.change'), format: (v: number) => v ? `${v > 0 ? '+' : ''}${v.toFixed(1)}%` : '-' },
    { key: 'volume', label: 'Volume', format: (v: number) => v ? formatNumber(v, 0) : '-' },
    { key: 'marketCap', label: t('table.marketCap'), format: (v: number) => v ? `${formatNumber(v, 0)} tỷ` : '-' },
    { key: 'pe', label: t('table.pe'), format: (v: number) => v ? formatNumber(v, 1) : '-' },
    { key: 'pb', label: t('table.pb'), format: (v: number) => v ? formatNumber(v, 2) : '-' },
    { key: 'roe', label: t('table.roe'), format: (v: number) => v ? `${formatNumber(v, 1)}%` : '-' },
    { key: 'eps', label: 'EPS', format: (v: number) => v ? formatNumber(v, 0) : '-' },
    { key: 'sector', label: t('table.sector'), format: (v: string) => v || '-' },
  ];

  return (
    <div>
      <h2 className="card-title mb-md">{t('comparison.title')}</h2>

      <div className="search-box mb-lg">
        <input
          type="text"
          className="form-input"
          placeholder={t('comparison.addStock')}
          value={searchTerm}
          onChange={(e) => {
            setSearchTerm(e.target.value);
            searchStocks(e.target.value);
          }}
        />
        {suggestions.length > 0 && (
          <div className="suggestions-list">
            {suggestions.map(s => (
              <div
                key={s.symbol}
                className="suggestion-item"
                onClick={() => addToComparison(s)}
              >
                <span><strong>{s.symbol}</strong> - {s.companyName}</span>
                <span>{formatCurrency(s.currentPrice || 0)}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {selectedStocks.length > 0 ? (
        <div className="table-container">
          <table className="table">
            <thead>
              <tr>
                <th>{t('comparison.metric')}</th>
                {selectedStocks.map(s => (
                  <th key={s.symbol}>
                    {s.symbol}
                    <button
                      className="btn-icon-sm ml-sm text-danger"
                      onClick={() => removeFromComparison(s.symbol)}
                    >
                      ×
                    </button>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {metrics.map(m => (
                <tr key={m.key}>
                  <td>{m.label}</td>
                  {selectedStocks.map(s => (
                    <td key={s.symbol} className="text-right">
                      {(m.format as any)((s as any)[m.key])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          <div style={{ marginTop: 'var(--spacing-lg)' }}>
            <h4 style={{ marginBottom: 'var(--spacing-md)' }}>📈 Price Charts (30 days)</h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 'var(--spacing-md)' }}>
              {selectedStocks.map(stock => (
                <div key={stock.symbol} className="card" style={{ padding: 'var(--spacing-md)' }}>
                  <div style={{ marginBottom: 'var(--spacing-sm)', fontWeight: 'bold' }}>{stock.symbol}</div>
                  <TradingViewChart symbol={stock.symbol} exchange={stock.exchange} height={300} showToolbar={false} />
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <div className="empty-state">
          <div className="empty-state-title">{t('comparison.select')}</div>
        </div>
      )}
    </div>
  );
}

// Wrapper to switch between SmartBoard and original comparison
function StockComparison() {
  const [viewMode, setViewMode] = useState<'smartboard' | 'compare'>('smartboard');

  return (
    <div>
      <div className="smart-board-view-toggle">
        <button className={`btn ${viewMode === 'smartboard' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setViewMode('smartboard')}>📊 Bảng điện thông minh</button>
        <button className={`btn ${viewMode === 'compare' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setViewMode('compare')}>📈 So sánh chi tiết</button>
      </div>
      {viewMode === 'smartboard' ? <SmartBoard /> : <StockComparisonOriginal />}
    </div>
  );
}

// ============================================
// Database Manager Component
// ============================================

interface DatabaseStatus {
  status: string;
  stocks_count: number;
  stocks_with_prices: number;
  last_update: string | null;
  database_size_mb: number | null;
  is_updating: boolean;
}

interface SchedulerStatus {
  can_run_update: boolean;
  tasks: Record<string, any>; // Simplified generic
}

function DatabaseManager() {
  const [dbStatus, setDbStatus] = useState<DatabaseStatus | null>(null);
  const [scheduler, setScheduler] = useState<SchedulerStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const [dbRes, schedRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/database/status`),
        fetch(`${API_BASE_URL}/api/database/scheduler`),
      ]);
      if (dbRes.ok) setDbStatus(await dbRes.json());
      if (schedRes.ok) setScheduler(await schedRes.json());
    } catch (err) { setError('Unable to connect'); } finally { setLoading(false); }
  }, []);

  React.useEffect(() => { fetchStatus(); const i = setInterval(fetchStatus, 10000); return () => clearInterval(i); }, [fetchStatus]);

  const triggerUpdate = async (taskName: string) => {
    setUpdating(true);
    try { await fetch(`${API_BASE_URL}/api/database/update?task_name=${taskName}`, { method: 'POST' }); setTimeout(fetchStatus, 2000); }
    catch (e) { console.error(e); } finally { setUpdating(false); }
  };

  const getStatusColor = (s: string) => s === 'fresh' ? '#10b981' : s === 'stale' ? '#f59e0b' : '#ef4444';

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error} <button onClick={fetchStatus}>Retry</button></div>;

  return (
    <div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="card p-4 text-center">
          <div className="text-2xl font-bold text-primary">{dbStatus?.stocks_count || 0}</div>
          <div className="text-sm text-gray-500">Total Stocks</div>
        </div>
        <div className="card p-4 text-center">
          <div className="text-2xl font-bold text-success">{dbStatus?.stocks_with_prices || 0}</div>
          <div className="text-sm text-gray-500">With Prices</div>
        </div>
        <div className="card p-4 text-center">
          <div className="text-2xl font-bold" style={{ color: getStatusColor(dbStatus?.status || '') }}>{dbStatus?.status}</div>
          <div className="text-sm text-gray-500">Status</div>
        </div>
        <div className="card p-4 text-center">
          <div className="text-2xl font-bold">{dbStatus?.database_size_mb?.toFixed(2)} MB</div>
          <div className="text-sm text-gray-500">Size</div>
        </div>
      </div>

      <div className="card p-4">
        <h3 className="card-title mb-4">🔄 Data Updates</h3>
        <div className="flex gap-2 flex-wrap">
          <button className="btn btn-primary" onClick={() => triggerUpdate('weekly_listings')} disabled={updating}>Update Listings</button>
          <button className="btn btn-secondary" onClick={() => triggerUpdate('daily_screener')} disabled={updating}>Update Prices</button>
          <button className="btn btn-ghost" onClick={fetchStatus}>Refresh Status</button>
        </div>
        {dbStatus?.last_update && <div className="mt-2 text-xs text-gray-500">Last update: {new Date(dbStatus.last_update).toLocaleString()}</div>}
      </div>
    </div>
  );
}

// ============================================
// Main Content
// ============================================

type TabId = 'screener' | 'comparison' | 'database' | 'ai-analysis';

function AppContent() {
  const { t } = useLanguage();
  const [activeTab, setActiveTab] = useState<TabId>('screener');
  const [selectedSymbolForAI, setSelectedSymbolForAI] = useState<string | null>(null);

  const handleAnalyzeStock = useCallback((symbol: string) => {
    setSelectedSymbolForAI(symbol);
    setActiveTab('ai-analysis');
  }, []);

  return (
    <div className="app-container">
      <Header />
      <main className="main-content">
        <div className="tabs">
          <button className={`tab ${activeTab === 'screener' ? 'active' : ''}`} onClick={() => setActiveTab('screener')}>🔍 {t('tabs.screener')}</button>
          <button className={`tab ${activeTab === 'comparison' ? 'active' : ''}`} onClick={() => setActiveTab('comparison')}>📊 {t('tabs.comparison')}</button>
          <button className={`tab ${activeTab === 'database' ? 'active' : ''}`} onClick={() => setActiveTab('database')}>💾 {t('tabs.database')}</button>
          <button className={`tab ${activeTab === 'ai-analysis' ? 'active' : ''}`} onClick={() => setActiveTab('ai-analysis')}>🤖 {t('tabs.aiAnalysis')}</button>
        </div>

        <div className="tab-content">
          {activeTab === 'screener' && <StockScreener />}
          {activeTab === 'comparison' && <StockComparison />}
          {activeTab === 'database' && (
            <div className="database-tab-container">
              <DataBrowser onAnalyzeStock={handleAnalyzeStock} />
              <div className="mt-8 pt-4 border-t border-base-300">
                <h3 className="cursor-pointer flex items-center gap-2" onClick={(e) => e.currentTarget.nextElementSibling?.classList.toggle('hidden')}>
                  ⚙️ Database System Status & Management (Click to toggle)
                </h3>
                <div className="hidden mt-4">
                  <DatabaseManager />
                </div>
              </div>
            </div>
          )}
          {activeTab === 'ai-analysis' && <AIAnalysis />}
        </div>
      </main>
      <footer className="footer-copyright">🇻🇳 VnStock Screener © 2026</footer>
    </div>
  );
}

import { AISettingsProvider } from './contexts/AISettingsContext';

export default function App() {
  return (
    <ThemeProvider>
      <LanguageProvider>
        <AISettingsProvider>
          <AppContent />
        </AISettingsProvider>
      </LanguageProvider>
    </ThemeProvider>
  );
}
