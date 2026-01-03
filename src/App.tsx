import React, { useState, useMemo, useCallback } from 'react';
import { LanguageProvider, useLanguage } from './contexts/LanguageContext';
import { ThemeProvider, useTheme } from './contexts/ThemeContext';
import { PriceChart } from './components/PriceChart';
import { AIAnalysis } from './components/AIAnalysis';
import { DataBrowser } from './components/DataBrowser';
import { TradingViewChart } from './components/TradingViewChart';
import { FilterPresets } from './components/FilterPresets';
import './index.css';

// API Base URL - empty string uses relative paths (works with nginx proxy in Docker)
const API_BASE_URL = import.meta.env.VITE_API_URL || '';

// ============================================
// Types (Inline to avoid module resolution issues)
// ============================================

interface Stock {
  symbol: string;
  companyName: string;
  exchange: string;
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
  eps?: number;
  isActive: boolean;
  updatedAt?: string;
}

interface StockFilters {
  // Basic filters
  exchange?: 'HOSE' | 'HNX' | 'UPCOM' | '';
  sector?: string;
  industry?: string;
  search?: string;

  // General metrics (Nhóm Tổng Quan)
  marketCapMin?: number;
  marketCapMax?: number;
  priceMin?: number;
  priceMax?: number;
  priceChangeMin?: number;
  priceChangeMax?: number;
  adtvValueMin?: number;
  volumeVsAdtvMin?: number;

  // Technical signals (Nhóm Tín Hiệu Kỹ Thuật)
  stockRatingMin?: number;
  rsMin?: number;
  rsMax?: number;
  rsiMin?: number;
  rsiMax?: number;
  priceVsSma20Min?: number;
  priceVsSma20Max?: number;
  macdHistogramMin?: number;
  stockTrend?: string;
  priceReturn1mMin?: number;
  priceReturn1mMax?: number;

  // Financial indicators (Nhóm Chỉ Số Tài Chính)
  peMin?: number;
  peMax?: number;
  pbMin?: number;
  pbMax?: number;
  roeMin?: number;
  roeMax?: number;
  revenueGrowthMin?: number;
  npatGrowthMin?: number;
  netMarginMin?: number;
  grossMarginMin?: number;
  dividendYieldMin?: number;
}

// ============================================
// Mock Data
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

function getMockStocks(filters?: StockFilters) {
  let filteredStocks = [...MOCK_STOCKS];

  if (filters?.exchange) {
    filteredStocks = filteredStocks.filter(s => s.exchange === filters.exchange);
  }
  if (filters?.sector) {
    filteredStocks = filteredStocks.filter(s => s.sector === filters.sector);
  }
  if (filters?.peMin !== undefined) {
    filteredStocks = filteredStocks.filter(s => s.pe && s.pe >= filters.peMin!);
  }
  if (filters?.peMax !== undefined) {
    filteredStocks = filteredStocks.filter(s => s.pe && s.pe <= filters.peMax!);
  }
  if (filters?.roeMin !== undefined) {
    filteredStocks = filteredStocks.filter(s => s.roe && s.roe >= filters.roeMin!);
  }
  if (filters?.search) {
    const search = filters.search.toLowerCase();
    filteredStocks = filteredStocks.filter(s =>
      s.symbol.toLowerCase().includes(search) ||
      s.companyName.toLowerCase().includes(search)
    );
  }

  return {
    stocks: filteredStocks,
    total: filteredStocks.length,
  };
}

// ============================================
// Tab Types
// ============================================

type TabId = 'screener' | 'comparison' | 'database' | 'ai-analysis';

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
// Filters Panel Component
// ============================================

const EXCHANGES = [
  { value: '', label: 'Tất cả sàn' },
  { value: 'HOSE', label: 'HOSE' },
  { value: 'HNX', label: 'HNX' },
  { value: 'UPCOM', label: 'UPCOM' },
];

interface FiltersPanelProps {
  filters: StockFilters;
  onFiltersChange: (filters: StockFilters) => void;
  onApply: () => void;
  onClear: () => void;
}

// Collapsible section component
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

// Tooltip wrapper for single inputs
function FilterInput({
  label,
  tooltip,
  children
}: {
  label: string;
  tooltip: string;
  children: React.ReactNode
}) {
  return (
    <div className="form-group" title={tooltip}>
      <label className="form-label">
        {label}
        <span className="tooltip-icon" title={tooltip}>ⓘ</span>
      </label>
      {children}
    </div>
  );
}

// Compact range filter for min-max values
function RangeFilter({
  label,
  tooltip,
  minValue,
  maxValue,
  onMinChange,
  onMaxChange,
  minPlaceholder = "Min",
  maxPlaceholder = "Max",
}: {
  label: string;
  tooltip: string;
  minValue?: number;
  maxValue?: number;
  onMinChange: (v: number | undefined) => void;
  onMaxChange: (v: number | undefined) => void;
  minPlaceholder?: string;
  maxPlaceholder?: string;
}) {
  return (
    <div className="range-filter" title={tooltip}>
      <label className="range-filter-label">
        {label}
        <span className="tooltip-icon" title={tooltip}>ⓘ</span>
      </label>
      <div className="range-inputs">
        <input
          type="number"
          className="range-input"
          placeholder={minPlaceholder}
          value={minValue ?? ''}
          onChange={(e) => onMinChange(e.target.value ? parseFloat(e.target.value) : undefined)}
        />
        <span className="range-separator">-</span>
        <input
          type="number"
          className="range-input"
          placeholder={maxPlaceholder}
          value={maxValue ?? ''}
          onChange={(e) => onMaxChange(e.target.value ? parseFloat(e.target.value) : undefined)}
        />
      </div>
    </div>
  );
}

function FiltersPanel({ filters, onFiltersChange, onApply, onClear }: FiltersPanelProps) {
  const { t } = useLanguage();

  const handleChange = (key: keyof StockFilters, value: string | number | undefined) => {
    onFiltersChange({
      ...filters,
      [key]: value === '' ? undefined : value,
    });
  };

  return (
    <div className="filters-panel">
      <div className="card-header">
        <h3 className="card-title">{t('screener.filters')}</h3>
      </div>

      {/* Filter Presets */}
      <FilterPresets
        currentFilters={filters}
        onLoadPreset={(preset) => onFiltersChange(preset as StockFilters)}
      />

      {/* Basic Filters */}
      <div className="filters-grid filters-basic">
        <div className="form-group">
          <label className="form-label">{t('filter.exchange')}</label>
          <select
            className="form-select"
            value={filters.exchange || ''}
            onChange={(e) => handleChange('exchange', e.target.value)}
          >
            {EXCHANGES.map((ex) => (
              <option key={ex.value} value={ex.value}>{ex.label}</option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label className="form-label">{t('common.search')}</label>
          <input
            type="text"
            className="form-input"
            placeholder={t('common.search')}
            value={filters.search || ''}
            onChange={(e) => handleChange('search', e.target.value)}
          />
        </div>
      </div>

      {/* General Metrics Section */}
      <FilterSection title="📊 Tổng Quan (General)" defaultOpen={true}>
        <div className="filters-compact">
          <RangeFilter
            label="Vốn hóa (tỷ)"
            tooltip="Vốn hóa thị trường: Tổng giá trị thị trường của số cổ phiếu đang lưu hành"
            minValue={filters.marketCapMin}
            maxValue={filters.marketCapMax}
            onMinChange={(v) => handleChange('marketCapMin', v)}
            onMaxChange={(v) => handleChange('marketCapMax', v)}
          />
          <RangeFilter
            label="Giá (VND)"
            tooltip="Thị giá: Mức giá khớp lệnh gần nhất của cổ phiếu"
            minValue={filters.priceMin}
            maxValue={filters.priceMax}
            onMinChange={(v) => handleChange('priceMin', v)}
            onMaxChange={(v) => handleChange('priceMax', v)}
          />
          <FilterInput label="GTGD TB (tỷ)" tooltip="Giá trị giao dịch trung bình ngày trong 20 phiên">
            <input
              type="number"
              className="form-input"
              placeholder="Tối thiểu"
              value={filters.adtvValueMin ?? ''}
              onChange={(e) => handleChange('adtvValueMin', e.target.value ? parseFloat(e.target.value) : undefined)}
            />
          </FilterInput>
        </div>
      </FilterSection>

      {/* Technical Signals Section */}
      <FilterSection title="📈 Kỹ Thuật (Technical)" defaultOpen={false}>
        <div className="filters-compact">
          <RangeFilter
            label="RSI"
            tooltip="Chỉ số sức mạnh tương đối: Dưới 30 = quá bán, Trên 70 = quá mua"
            minValue={filters.rsiMin}
            maxValue={filters.rsiMax}
            onMinChange={(v) => handleChange('rsiMin', v)}
            onMaxChange={(v) => handleChange('rsiMax', v)}
            minPlaceholder="0"
            maxPlaceholder="100"
          />
          <RangeFilter
            label="RS 3 tháng"
            tooltip="Sức mạnh tương quan: So sánh hiệu suất với thị trường"
            minValue={filters.rsMin}
            maxValue={filters.rsMax}
            onMinChange={(v) => handleChange('rsMin', v)}
            onMaxChange={(v) => handleChange('rsMax', v)}
          />
          <RangeFilter
            label="Giá/SMA20 %"
            tooltip="Khoảng cách giá so với đường trung bình 20 ngày"
            minValue={filters.priceVsSma20Min}
            maxValue={filters.priceVsSma20Max}
            onMinChange={(v) => handleChange('priceVsSma20Min', v)}
            onMaxChange={(v) => handleChange('priceVsSma20Max', v)}
          />
          <FilterInput label="Xu hướng" tooltip="Trạng thái xu hướng giá">
            <select
              className="form-select"
              value={filters.stockTrend || ''}
              onChange={(e) => handleChange('stockTrend', e.target.value)}
            >
              <option value="">Tất cả</option>
              <option value="uptrend">📈 Xu hướng tăng</option>
              <option value="breakout">🚀 Breakout</option>
              <option value="heating_up">🔥 Đang nóng</option>
            </select>
          </FilterInput>
        </div>
      </FilterSection>

      {/* Financial Indicators Section */}
      <FilterSection title="💰 Tài Chính (Financial)" defaultOpen={true}>
        <div className="filters-compact">
          <RangeFilter
            label="P/E"
            tooltip="Hệ số giá trên thu nhập: P/E thấp = cổ phiếu rẻ"
            minValue={filters.peMin}
            maxValue={filters.peMax}
            onMinChange={(v) => handleChange('peMin', v)}
            onMaxChange={(v) => handleChange('peMax', v)}
            minPlaceholder="0"
            maxPlaceholder="100"
          />
          <RangeFilter
            label="P/B"
            tooltip="Hệ số giá trên giá trị sổ sách: P/B < 1 = đang rẻ"
            minValue={filters.pbMin}
            maxValue={filters.pbMax}
            onMinChange={(v) => handleChange('pbMin', v)}
            onMaxChange={(v) => handleChange('pbMax', v)}
          />
          <RangeFilter
            label="ROE %"
            tooltip="Tỷ suất lợi nhuận trên vốn chủ sở hữu"
            minValue={filters.roeMin}
            maxValue={filters.roeMax}
            onMinChange={(v) => handleChange('roeMin', v)}
            onMaxChange={(v) => handleChange('roeMax', v)}
          />
          <FilterInput label="Tăng trưởng DT %" tooltip="Tăng trưởng doanh thu năm qua">
            <input
              type="number"
              className="form-input"
              placeholder="Tối thiểu"
              value={filters.revenueGrowthMin ?? ''}
              onChange={(e) => handleChange('revenueGrowthMin', e.target.value ? parseFloat(e.target.value) : undefined)}
            />
          </FilterInput>
          <FilterInput label="Tăng trưởng LN %" tooltip="Tăng trưởng lợi nhuận quý gần nhất">
            <input
              type="number"
              className="form-input"
              placeholder="Tối thiểu"
              value={filters.npatGrowthMin ?? ''}
              onChange={(e) => handleChange('npatGrowthMin', e.target.value ? parseFloat(e.target.value) : undefined)}
            />
          </FilterInput>
          <FilterInput label="Biên LN ròng %" tooltip="Biên lợi nhuận ròng trên doanh thu">
            <input
              type="number"
              className="form-input"
              placeholder="Tối thiểu"
              value={filters.netMarginMin ?? ''}
              onChange={(e) => handleChange('netMarginMin', e.target.value ? parseFloat(e.target.value) : undefined)}
            />
          </FilterInput>
        </div>
      </FilterSection>

      <div className="filters-actions">
        <button className="btn btn-primary" onClick={onApply}>
          {t('screener.applyFilters')}
        </button>
        <button className="btn btn-secondary" onClick={onClear}>
          {t('screener.clearFilters')}
        </button>
      </div>
    </div>
  );
}


// ============================================
// Stock Table Component
// ============================================

interface StockTableProps {
  stocks: Stock[];
}

function StockTable({ stocks }: StockTableProps) {
  const { t, formatCurrency, formatNumber } = useLanguage();

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
            <th>{t('table.symbol')}</th>
            <th>{t('table.companyName')}</th>
            <th>{t('table.exchange')}</th>
            <th className="text-right">{t('table.price')}</th>
            <th className="text-right">{t('table.change')}</th>
            <th className="text-right">{t('table.marketCap')}</th>
            <th className="text-right">{t('table.pe')}</th>
            <th className="text-right">{t('table.pb')}</th>
            <th className="text-right">{t('table.roe')}</th>
            <th>{t('table.sector')}</th>
          </tr>
        </thead>
        <tbody>
          {stocks.map((stock) => (
            <tr key={stock.symbol}>
              <td><strong>{stock.symbol}</strong></td>
              <td className="text-muted text-sm">{stock.companyName}</td>
              <td>
                <span className={getExchangeClass(stock.exchange)}>
                  {stock.exchange}
                </span>
              </td>
              <td className="text-right font-bold">
                {formatCurrency(stock.currentPrice || 0)}
              </td>
              <td className={`text-right ${getPriceChangeClass(stock.priceChange)}`}>
                {stock.priceChange ? `${stock.priceChange > 0 ? '+' : ''}${formatNumber(stock.priceChange, 0)} (${stock.priceChangePercent?.toFixed(1)}%)` : '-'}
              </td>
              <td className="text-right">
                {stock.marketCap ? `${formatNumber(stock.marketCap, 0)} tỷ` : '-'}
              </td>
              <td className="text-right">{stock.pe ? formatNumber(stock.pe, 1) : '-'}</td>
              <td className="text-right">{stock.pb ? formatNumber(stock.pb, 2) : '-'}</td>
              <td className="text-right">{stock.roe ? `${formatNumber(stock.roe, 1)}%` : '-'}</td>
              <td className="text-muted text-sm">{stock.sector || '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ============================================
// Stock Screener Component
// ============================================

function StockScreener() {
  const { t } = useLanguage();
  const [filters, setFilters] = useState<StockFilters>({});
  const [appliedFilters, setAppliedFilters] = useState<StockFilters>({});
  const [showFilters, setShowFilters] = useState(true);
  const [stocks, setStocks] = useState<Stock[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [usingMockData, setUsingMockData] = useState(false);

  // Fetch stocks from API or use mock data as fallback
  const fetchStocks = useCallback(async (currentFilters: StockFilters) => {
    setLoading(true);
    setError(null);

    try {
      // Build query params for comprehensive screener
      const params = new URLSearchParams();

      // Basic filters
      if (currentFilters.exchange) params.set('exchange', currentFilters.exchange);
      if (currentFilters.search) params.set('search', currentFilters.search);

      // General metrics
      if (currentFilters.marketCapMin !== undefined) params.set('market_cap_min', String(currentFilters.marketCapMin));
      if (currentFilters.marketCapMax !== undefined) params.set('market_cap_max', String(currentFilters.marketCapMax));
      if (currentFilters.priceMin !== undefined) params.set('price_min', String(currentFilters.priceMin));
      if (currentFilters.priceMax !== undefined) params.set('price_max', String(currentFilters.priceMax));
      if (currentFilters.adtvValueMin !== undefined) params.set('adtv_value_min', String(currentFilters.adtvValueMin));

      // Technical signals
      if (currentFilters.rsiMin !== undefined) params.set('rsi_min', String(currentFilters.rsiMin));
      if (currentFilters.rsiMax !== undefined) params.set('rsi_max', String(currentFilters.rsiMax));
      if (currentFilters.rsMin !== undefined) params.set('rs_min', String(currentFilters.rsMin));
      if (currentFilters.priceVsSma20Min !== undefined) params.set('price_vs_sma20_min', String(currentFilters.priceVsSma20Min));
      if (currentFilters.stockTrend) params.set('stock_trend', currentFilters.stockTrend);
      if (currentFilters.priceReturn1mMin !== undefined) params.set('price_return_1m_min', String(currentFilters.priceReturn1mMin));

      // Financial indicators
      if (currentFilters.peMin !== undefined) params.set('pe_min', String(currentFilters.peMin));
      if (currentFilters.peMax !== undefined) params.set('pe_max', String(currentFilters.peMax));
      if (currentFilters.pbMin !== undefined) params.set('pb_min', String(currentFilters.pbMin));
      if (currentFilters.pbMax !== undefined) params.set('pb_max', String(currentFilters.pbMax));
      if (currentFilters.roeMin !== undefined) params.set('roe_min', String(currentFilters.roeMin));
      if (currentFilters.revenueGrowthMin !== undefined) params.set('revenue_growth_min', String(currentFilters.revenueGrowthMin));
      if (currentFilters.npatGrowthMin !== undefined) params.set('npat_growth_min', String(currentFilters.npatGrowthMin));
      if (currentFilters.netMarginMin !== undefined) params.set('net_margin_min', String(currentFilters.netMarginMin));

      params.set('page_size', '100');

      const response = await fetch(`${API_BASE_URL}/api/stocks/screener?${params.toString()}`);

      if (!response.ok) {
        throw new Error(`API Error: ${response.status}`);
      }

      const data = await response.json();

      // Map backend response to frontend Stock format (with comprehensive data)
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
        marketCap: s.market_cap ? s.market_cap / 1000000000 : undefined, // Convert to billions
        pe: s.pe_ratio,
        pb: s.pb_ratio,
        roe: s.roe ? s.roe * 100 : undefined, // Convert to percentage
        eps: s.eps,
        isActive: true,
        updatedAt: s.screener_updated_at || s.updated_at,
        // Additional screener data
        rsi: s.rsi,
        macdHistogram: s.macd_histogram,
        stockRating: s.stock_rating,
        relativeStrength: s.relative_strength,
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
      // Fallback to mock data
      const mockResult = getMockStocks(currentFilters);
      setStocks(mockResult.stocks);
      setTotal(mockResult.total);
      setUsingMockData(true);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial fetch and refetch on filter changes
  React.useEffect(() => {
    fetchStocks(appliedFilters);
  }, [appliedFilters, fetchStocks]);

  const handleApplyFilters = useCallback(() => {
    setAppliedFilters({ ...filters });
  }, [filters]);

  const handleClearFilters = useCallback(() => {
    setFilters({});
    setAppliedFilters({});
  }, []);

  return (
    <div>
      <div className="screener-toolbar">
        <div className="flex items-center gap-md">
          <h2 className="card-title">{t('screener.title')}</h2>
          <span className="badge badge-info">
            {total} {t('screener.results').toLowerCase()}
          </span>
          {usingMockData && (
            <span className="badge" style={{ background: '#ff9800', color: 'white' }}>
              Demo Mode
            </span>
          )}
        </div>
        <div className="flex gap-sm">
          <button
            className={`btn ${showFilters ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setShowFilters(!showFilters)}
          >
            🔍 {t('screener.filters')}
          </button>
          <button className="btn btn-secondary">
            📥 {t('common.exportCSV')}
          </button>
        </div>
      </div>

      {showFilters && (
        <FiltersPanel
          filters={filters}
          onFiltersChange={setFilters}
          onApply={handleApplyFilters}
          onClear={handleClearFilters}
        />
      )}

      <div className="card mt-md">
        {loading ? (
          <div className="empty-state">
            <div className="empty-state-icon">⏳</div>
            <div className="empty-state-title">Loading...</div>
          </div>
        ) : (
          <StockTable stocks={stocks} />
        )}
      </div>
    </div>
  );
}

// ============================================
// Stock Comparison Component
// ============================================

function StockComparison() {
  const { t, formatCurrency, formatNumber } = useLanguage();
  const [searchTerm, setSearchTerm] = useState('');
  const [suggestions, setSuggestions] = useState<Stock[]>([]);
  const [selectedStocks, setSelectedStocks] = useState<Stock[]>([]);
  const [loading, setLoading] = useState(false);

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
          companyName: s.company_name || s.symbol,
          exchange: s.exchange || 'HOSE',
          currentPrice: s.current_price,
          priceChange: s.price_change,
          priceChangePercent: s.percent_change,
          volume: s.volume,
          marketCap: s.market_cap ? s.market_cap / 1000000000 : undefined,
          pe: s.pe_ratio,
          pb: s.pb_ratio,
          roe: s.roe ? s.roe * 100 : undefined,
          sector: s.sector,
          isActive: true,
        }));
        setSuggestions(mapped);
      }
    } catch (err) {
      console.error('Search failed:', err);
    }
  }, []);

  React.useEffect(() => {
    const timeout = setTimeout(() => searchStocks(searchTerm), 300);
    return () => clearTimeout(timeout);
  }, [searchTerm, searchStocks]);

  const addStock = (stock: Stock) => {
    if (selectedStocks.length >= 5) return;
    if (selectedStocks.some(s => s.symbol === stock.symbol)) return;
    setSelectedStocks([...selectedStocks, stock]);
    setSearchTerm('');
    setSuggestions([]);
  };

  const removeStock = (symbol: string) => {
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
      {/* Search */}
      <div className="card" style={{ marginBottom: 'var(--spacing-lg)' }}>
        <div className="card-header">
          <h3 className="card-title">📊 {t('comparison.title')}</h3>
        </div>
        <div style={{ padding: 'var(--spacing-md)' }}>
          <div style={{ position: 'relative' }}>
            <input
              type="text"
              className="form-input"
              placeholder="Search stocks to compare (max 5)..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              disabled={selectedStocks.length >= 5}
            />
            {suggestions.length > 0 && (
              <div style={{
                position: 'absolute',
                top: '100%',
                left: 0,
                right: 0,
                background: 'var(--bg-primary)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-md)',
                boxShadow: 'var(--shadow-lg)',
                zIndex: 100,
                maxHeight: '200px',
                overflowY: 'auto',
              }}>
                {suggestions.map(stock => (
                  <div
                    key={stock.symbol}
                    onClick={() => addStock(stock)}
                    style={{
                      padding: 'var(--spacing-sm) var(--spacing-md)',
                      cursor: 'pointer',
                      borderBottom: '1px solid var(--border)',
                    }}
                    onMouseOver={(e) => e.currentTarget.style.background = 'var(--bg-secondary)'}
                    onMouseOut={(e) => e.currentTarget.style.background = 'transparent'}
                  >
                    <strong>{stock.symbol}</strong> - {stock.companyName}
                    {stock.currentPrice && (
                      <span style={{ float: 'right', color: 'var(--primary)' }}>
                        {formatCurrency(stock.currentPrice)}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Selected Stocks Tags */}
          {selectedStocks.length > 0 && (
            <div style={{ marginTop: 'var(--spacing-md)', display: 'flex', gap: 'var(--spacing-sm)', flexWrap: 'wrap' }}>
              {selectedStocks.map(stock => (
                <span
                  key={stock.symbol}
                  className="badge badge-info"
                  style={{ cursor: 'pointer', padding: 'var(--spacing-xs) var(--spacing-sm)' }}
                  onClick={() => removeStock(stock.symbol)}
                >
                  {stock.symbol} ✕
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Comparison Table */}
      {selectedStocks.length > 0 ? (
        <div className="card">
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>Metric</th>
                  {selectedStocks.map(stock => (
                    <th key={stock.symbol} style={{ textAlign: 'center' }}>
                      <div><strong>{stock.symbol}</strong></div>
                      <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)' }}>
                        {stock.exchange}
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {metrics.map(metric => (
                  <tr key={metric.key}>
                    <td><strong>{metric.label}</strong></td>
                    {selectedStocks.map(stock => (
                      <td key={stock.symbol} style={{ textAlign: 'center' }}>
                        {(metric.format as any)((stock as any)[metric.key])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Price Charts */}
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
        <div className="card">
          <div className="empty-state">
            <div className="empty-state-icon">📈</div>
            <div className="empty-state-title">{t('comparison.select')}</div>
            <p className="text-muted">Search and add up to 5 stocks to compare</p>
          </div>
        </div>
      )}
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

interface SchedulerTask {
  enabled: boolean;
  priority: number;
  schedule_time: string;
  last_run: string | null;
  last_status: string | null;
  run_count: number;
  success_count: number;
  failure_count: number;
}

interface SchedulerStatus {
  running: boolean;
  current_task: string | null;
  is_market_hours: boolean;
  can_run_update: boolean;
  tasks: Record<string, SchedulerTask>;
}

function DatabaseManager() {
  const { t } = useLanguage();
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

      if (dbRes.ok) {
        setDbStatus(await dbRes.json());
      }
      if (schedRes.ok) {
        setScheduler(await schedRes.json());
      }
      setError(null);
    } catch (err) {
      setError('Unable to connect to backend');
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, [fetchStatus]);

  const triggerUpdate = async (taskName: string) => {
    setUpdating(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/database/update?task_name=${taskName}`, {
        method: 'POST',
      });
      if (res.ok) {
        setTimeout(fetchStatus, 2000);
      }
    } catch (err) {
      console.error('Update failed:', err);
    } finally {
      setUpdating(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'fresh': return '#10b981';
      case 'stale': return '#f59e0b';
      case 'no_data': return '#ef4444';
      default: return '#6b7280';
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'fresh': return '✅ Fresh';
      case 'stale': return '⚠️ Stale';
      case 'no_data': return '❌ No Data';
      default: return status;
    }
  };

  if (loading) {
    return (
      <div className="card">
        <div className="empty-state">
          <div className="empty-state-icon">⏳</div>
          <div className="empty-state-title">Loading database status...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <div className="empty-state">
          <div className="empty-state-icon">⚠️</div>
          <div className="empty-state-title">{error}</div>
          <button className="btn btn-primary mt-md" onClick={fetchStatus}>
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Status Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 'var(--spacing-md)', marginBottom: 'var(--spacing-lg)' }}>
        <div className="card" style={{ textAlign: 'center', padding: 'var(--spacing-lg)' }}>
          <div style={{ fontSize: '2.5rem', fontWeight: 'bold', color: 'var(--primary)' }}>
            {dbStatus?.stocks_count.toLocaleString() || 0}
          </div>
          <div style={{ color: 'var(--text-secondary)', marginTop: 'var(--spacing-xs)' }}>
            📊 Total Stocks
          </div>
        </div>

        <div className="card" style={{ textAlign: 'center', padding: 'var(--spacing-lg)' }}>
          <div style={{ fontSize: '2.5rem', fontWeight: 'bold', color: '#10b981' }}>
            {dbStatus?.stocks_with_prices.toLocaleString() || 0}
          </div>
          <div style={{ color: 'var(--text-secondary)', marginTop: 'var(--spacing-xs)' }}>
            💰 With Prices
          </div>
        </div>

        <div className="card" style={{ textAlign: 'center', padding: 'var(--spacing-lg)' }}>
          <div style={{ fontSize: '2.5rem', fontWeight: 'bold', color: getStatusColor(dbStatus?.status || '') }}>
            {getStatusLabel(dbStatus?.status || 'unknown')}
          </div>
          <div style={{ color: 'var(--text-secondary)', marginTop: 'var(--spacing-xs)' }}>
            📈 Data Status
          </div>
        </div>

        <div className="card" style={{ textAlign: 'center', padding: 'var(--spacing-lg)' }}>
          <div style={{ fontSize: '2.5rem', fontWeight: 'bold', color: 'var(--text-primary)' }}>
            {dbStatus?.database_size_mb?.toFixed(2) || 0} MB
          </div>
          <div style={{ color: 'var(--text-secondary)', marginTop: 'var(--spacing-xs)' }}>
            💾 Database Size
          </div>
        </div>
      </div>

      {/* Update Controls */}
      <div className="card" style={{ marginBottom: 'var(--spacing-lg)' }}>
        <div className="card-header">
          <h3 className="card-title">🔄 Data Updates</h3>
        </div>
        <div style={{ padding: 'var(--spacing-md)' }}>
          <div style={{ marginBottom: 'var(--spacing-md)', padding: 'var(--spacing-sm)', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)' }}>
            {scheduler?.can_run_update ? (
              <span style={{ color: '#10b981' }}>✅ Updates allowed (outside market hours)</span>
            ) : (
              <span style={{ color: '#f59e0b' }}>⚠️ Market hours - updates not recommended</span>
            )}
          </div>

          <div style={{ display: 'flex', gap: 'var(--spacing-sm)', flexWrap: 'wrap' }}>
            <button
              className="btn btn-primary"
              onClick={() => triggerUpdate('weekly_listings')}
              disabled={updating}
            >
              {updating ? '⏳ Updating...' : '📋 Update Listings'}
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => triggerUpdate('daily_screener')}
              disabled={updating}
            >
              {updating ? '⏳ Updating...' : '💹 Update Prices'}
            </button>
            <button
              className="btn btn-secondary"
              onClick={fetchStatus}
            >
              🔄 Refresh Status
            </button>
          </div>

          {dbStatus?.last_update && (
            <div style={{ marginTop: 'var(--spacing-md)', color: 'var(--text-secondary)', fontSize: 'var(--font-size-sm)' }}>
              Last update: {new Date(dbStatus.last_update).toLocaleString('vi-VN')}
            </div>
          )}
        </div>
      </div>

      {/* Scheduler Tasks */}
      {scheduler && (
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">📅 Scheduled Tasks</h3>
          </div>
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>Task</th>
                  <th>Schedule</th>
                  <th>Priority</th>
                  <th>Runs</th>
                  <th>Success</th>
                  <th>Failed</th>
                  <th>Last Status</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(scheduler.tasks).map(([name, task]) => (
                  <tr key={name}>
                    <td><strong>{name.replace(/_/g, ' ')}</strong></td>
                    <td>{task.schedule_time}</td>
                    <td>{task.priority}</td>
                    <td>{task.run_count}</td>
                    <td style={{ color: '#10b981' }}>{task.success_count}</td>
                    <td style={{ color: task.failure_count > 0 ? '#ef4444' : 'inherit' }}>{task.failure_count}</td>
                    <td>
                      {task.last_status === 'completed' ? '✅' :
                        task.last_status?.startsWith('failed') ? '❌' :
                          task.last_status || '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================
// App Content
// ============================================


function AppContent() {
  const { t } = useLanguage();
  const [activeTab, setActiveTab] = useState<TabId>('screener');

  return (
    <div className="app-container">
      <Header />

      <main className="main-content">
        <div className="tabs">
          <button
            className={`tab ${activeTab === 'screener' ? 'active' : ''}`}
            onClick={() => setActiveTab('screener')}
          >
            📊 {t('nav.screener')}
          </button>
          <button
            className={`tab ${activeTab === 'comparison' ? 'active' : ''}`}
            onClick={() => setActiveTab('comparison')}
          >
            📈 {t('nav.comparison')}
          </button>
          <button
            className={`tab ${activeTab === 'database' ? 'active' : ''}`}
            onClick={() => setActiveTab('database')}
          >
            💾 {t('nav.database')}
          </button>
          <button
            className={`tab ${activeTab === 'ai-analysis' ? 'active' : ''}`}
            onClick={() => setActiveTab('ai-analysis')}
          >
            🤖 AI Analysis
          </button>
        </div>

        {activeTab === 'screener' && <StockScreener />}

        {activeTab === 'comparison' && <StockComparison />}

        {activeTab === 'database' && (
          <div className="database-tab-container">
            <div className="tabs-subnav" style={{ marginBottom: 'var(--spacing-md)', display: 'flex', gap: 'var(--spacing-md)', padding: '0 var(--spacing-lg)' }}>
              {/* Sub-navigation could be here, or just a toggle */}
            </div>

            {/* Show Data Browser by default, but allow access to Manager */}
            {/* For now, let's put Manager below Browser or use a toggle. 
                Let's use a simple toggle state in AppContent or just render DataBrowser 
                and have a button in it to show "System Status" which opens DatabaseManager modal/section 
            */}

            <DataBrowser />

            <div style={{ marginTop: 'var(--spacing-xl)', borderTop: '1px solid var(--border-color)', paddingTop: 'var(--spacing-lg)' }}>
              <h3 onClick={(e) => {
                const content = e.currentTarget.nextElementSibling;
                if (content) content.classList.toggle('hidden');
              }} style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px' }}>
                ⚙️ Database System Status & Management (Click to toggle)
              </h3>
              <div className="hidden" style={{ marginTop: 'var(--spacing-md)' }}>
                <DatabaseManager />
              </div>
            </div>
          </div>
        )}

        {activeTab === 'ai-analysis' && <AIAnalysis />}
      </main>

      <footer style={{
        textAlign: 'center',
        padding: 'var(--spacing-md)',
        color: 'var(--text-secondary)',
        fontSize: 'var(--font-size-sm)'
      }}>
        🇻🇳 VnStock Screener © 2026
      </footer>
    </div>
  );
}

// ============================================
// Main App
// ============================================

function App() {
  return (
    <ThemeProvider>
      <LanguageProvider>
        <AppContent />
      </LanguageProvider>
    </ThemeProvider>
  );
}

export default App;
