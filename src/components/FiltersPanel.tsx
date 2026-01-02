import React from 'react';
import { useLanguage } from '../contexts/LanguageContext';
import { StockFilters, ActiveFilter } from '../types';

// ============================================
// Props
// ============================================

interface FiltersPanelProps {
    filters: StockFilters;
    onFiltersChange: (filters: StockFilters) => void;
    onApply: () => void;
    onClear: () => void;
}

// ============================================
// Exchange Options
// ============================================

const EXCHANGES = [
    { value: '', label: 'filter.exchange.all' },
    { value: 'HOSE', label: 'HOSE' },
    { value: 'HNX', label: 'HNX' },
    { value: 'UPCOM', label: 'UPCOM' },
];

const SECTORS = [
    { value: '', labelVi: 'Tất cả ngành', labelEn: 'All Sectors' },
    { value: 'Ngân hàng', labelVi: 'Ngân hàng', labelEn: 'Banking' },
    { value: 'Bất động sản', labelVi: 'Bất động sản', labelEn: 'Real Estate' },
    { value: 'Thép', labelVi: 'Thép', labelEn: 'Steel' },
    { value: 'Dầu khí', labelVi: 'Dầu khí', labelEn: 'Oil & Gas' },
    { value: 'Hàng tiêu dùng', labelVi: 'Hàng tiêu dùng', labelEn: 'Consumer Goods' },
    { value: 'Điện', labelVi: 'Điện', labelEn: 'Utilities' },
    { value: 'Thực phẩm', labelVi: 'Thực phẩm', labelEn: 'Food & Beverage' },
    { value: 'Công nghệ', labelVi: 'Công nghệ', labelEn: 'Technology' },
    { value: 'Bán lẻ', labelVi: 'Bán lẻ', labelEn: 'Retail' },
];

// ============================================
// Component
// ============================================

export function FiltersPanel({ filters, onFiltersChange, onApply, onClear }: FiltersPanelProps) {
    const { t, language } = useLanguage();

    const handleChange = (key: keyof StockFilters, value: string | number | undefined) => {
        onFiltersChange({
            ...filters,
            [key]: value === '' ? undefined : value,
        });
    };

    const handleNumberChange = (key: keyof StockFilters, value: string) => {
        const numValue = value === '' ? undefined : parseFloat(value);
        handleChange(key, numValue);
    };

    // Get active filters for display
    const getActiveFilters = (): ActiveFilter[] => {
        const active: ActiveFilter[] = [];

        if (filters.exchange) {
            active.push({ key: 'exchange', label: t('filter.exchange'), value: filters.exchange });
        }
        if (filters.sector) {
            active.push({ key: 'sector', label: t('filter.sector'), value: filters.sector });
        }
        if (filters.peMin !== undefined) {
            active.push({ key: 'peMin', label: t('filter.pe.min'), value: filters.peMin });
        }
        if (filters.peMax !== undefined) {
            active.push({ key: 'peMax', label: t('filter.pe.max'), value: filters.peMax });
        }
        if (filters.pbMin !== undefined) {
            active.push({ key: 'pbMin', label: t('filter.pb.min'), value: filters.pbMin });
        }
        if (filters.pbMax !== undefined) {
            active.push({ key: 'pbMax', label: t('filter.pb.max'), value: filters.pbMax });
        }
        if (filters.roeMin !== undefined) {
            active.push({ key: 'roeMin', label: t('filter.roe.min'), value: `${filters.roeMin}%` });
        }

        return active;
    };

    const activeFilters = getActiveFilters();

    return (
        <div className="filters-panel">
            <div className="card-header">
                <h3 className="card-title">{t('screener.filters')}</h3>
            </div>

            <div className="filters-grid">
                {/* Exchange Filter */}
                <div className="form-group">
                    <label className="form-label">{t('filter.exchange')}</label>
                    <select
                        className="form-select"
                        value={filters.exchange || ''}
                        onChange={(e) => handleChange('exchange', e.target.value)}
                    >
                        {EXCHANGES.map((ex) => (
                            <option key={ex.value} value={ex.value}>
                                {ex.value === '' ? t(ex.label) : ex.label}
                            </option>
                        ))}
                    </select>
                </div>

                {/* Sector Filter */}
                <div className="form-group">
                    <label className="form-label">{t('filter.sector')}</label>
                    <select
                        className="form-select"
                        value={filters.sector || ''}
                        onChange={(e) => handleChange('sector', e.target.value)}
                    >
                        {SECTORS.map((sec) => (
                            <option key={sec.value} value={sec.value}>
                                {language === 'vi' ? sec.labelVi : sec.labelEn}
                            </option>
                        ))}
                    </select>
                </div>

                {/* P/E Min */}
                <div className="form-group">
                    <label className="form-label">{t('filter.pe.min')}</label>
                    <input
                        type="number"
                        className="form-input"
                        placeholder="0"
                        value={filters.peMin ?? ''}
                        onChange={(e) => handleNumberChange('peMin', e.target.value)}
                        min={0}
                        step={0.1}
                    />
                </div>

                {/* P/E Max */}
                <div className="form-group">
                    <label className="form-label">{t('filter.pe.max')}</label>
                    <input
                        type="number"
                        className="form-input"
                        placeholder="100"
                        value={filters.peMax ?? ''}
                        onChange={(e) => handleNumberChange('peMax', e.target.value)}
                        min={0}
                        step={0.1}
                    />
                </div>

                {/* P/B Min */}
                <div className="form-group">
                    <label className="form-label">{t('filter.pb.min')}</label>
                    <input
                        type="number"
                        className="form-input"
                        placeholder="0"
                        value={filters.pbMin ?? ''}
                        onChange={(e) => handleNumberChange('pbMin', e.target.value)}
                        min={0}
                        step={0.1}
                    />
                </div>

                {/* P/B Max */}
                <div className="form-group">
                    <label className="form-label">{t('filter.pb.max')}</label>
                    <input
                        type="number"
                        className="form-input"
                        placeholder="10"
                        value={filters.pbMax ?? ''}
                        onChange={(e) => handleNumberChange('pbMax', e.target.value)}
                        min={0}
                        step={0.1}
                    />
                </div>

                {/* ROE Min */}
                <div className="form-group">
                    <label className="form-label">{t('filter.roe.min')}</label>
                    <input
                        type="number"
                        className="form-input"
                        placeholder="0"
                        value={filters.roeMin ?? ''}
                        onChange={(e) => handleNumberChange('roeMin', e.target.value)}
                        min={0}
                        step={1}
                    />
                </div>

                {/* Market Cap Min */}
                <div className="form-group">
                    <label className="form-label">{t('filter.marketCap.min')}</label>
                    <input
                        type="number"
                        className="form-input"
                        placeholder="0"
                        value={filters.marketCapMin ?? ''}
                        onChange={(e) => handleNumberChange('marketCapMin', e.target.value)}
                        min={0}
                    />
                </div>

                {/* Technical Indicators Section */}
                <div className="col-span-full mt-sm mb-sm border-t pt-sm">
                    <h4 className="text-sm font-semibold">{t('screener.filters')} (Technical)</h4>
                </div>

                {/* Trend Filter */}
                <div className="form-group">
                    <label className="form-label">{t('filter.trend')}</label>
                    <select
                        className="form-select"
                        value={filters.trend || ''}
                        onChange={(e) => handleChange('trend', e.target.value)}
                    >
                        <option value="">{t('filter.sector.all')}</option>
                        <option value="uptrend">{t('filter.trend.uptrend')}</option>
                        <option value="downtrend">{t('filter.trend.downtrend')}</option>
                        <option value="strong_uptrend">Strong Uptrend</option>
                        <option value="strong_downtrend">Strong Downtrend</option>
                        <option value="sideways">Sideways</option>
                    </select>
                </div>

                {/* ADX Min */}
                <div className="form-group">
                    <label className="form-label">{t('filter.adx.min')}</label>
                    <input
                        type="number"
                        className="form-input"
                        placeholder="25"
                        value={filters.adxMin ?? ''}
                        onChange={(e) => handleNumberChange('adxMin', e.target.value)}
                        min={0}
                        max={100}
                    />
                </div>

                {/* RSI Min */}
                <div className="form-group">
                    <label className="form-label">{t('filter.rsi.min')}</label>
                    <input
                        type="number"
                        className="form-input"
                        placeholder="30"
                        value={filters.rsiMin ?? ''}
                        onChange={(e) => handleNumberChange('rsiMin', e.target.value)}
                        min={0}
                        max={100}
                    />
                </div>

                {/* RSI Max */}
                <div className="form-group">
                    <label className="form-label">{t('filter.rsi.max')}</label>
                    <input
                        type="number"
                        className="form-input"
                        placeholder="70"
                        value={filters.rsiMax ?? ''}
                        onChange={(e) => handleNumberChange('rsiMax', e.target.value)}
                        min={0}
                        max={100}
                    />
                </div>

                {/* Search */}
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

            {/* Active Filters Chips */}
            {activeFilters.length > 0 && (
                <div className="active-filters">
                    {activeFilters.map((filter) => (
                        <span key={filter.key} className="filter-chip">
                            {filter.label}: {filter.value}
                            <button
                                onClick={() => handleChange(filter.key, undefined)}
                                title="Remove"
                            >
                                ×
                            </button>
                        </span>
                    ))}
                </div>
            )}

            {/* Actions */}
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

export default FiltersPanel;
