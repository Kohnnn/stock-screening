import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';

// ============================================
// Types
// ============================================

type Language = 'vi' | 'en';

interface LanguageContextType {
    language: Language;
    setLanguage: (lang: Language) => void;
    t: (key: string) => string;
    formatCurrency: (value: number) => string;
    formatNumber: (value: number, decimals?: number) => string;
    formatPercent: (value: number, decimals?: number) => string;
}

// ============================================
// Translations
// ============================================

const translations: Record<Language, Record<string, string>> = {
    vi: {
        // App
        'app.title': 'VnStock Screener',
        'app.subtitle': 'Công cụ sàng lọc cổ phiếu Việt Nam',

        // Navigation
        'nav.screener': 'Sàng lọc',
        'nav.comparison': 'So sánh',
        'nav.database': 'Cơ sở dữ liệu',
        'nav.settings': 'Cài đặt',

        // Screener
        'screener.title': 'Sàng lọc cổ phiếu',
        'screener.filters': 'Bộ lọc',
        'screener.results': 'Kết quả',
        'screener.noResults': 'Không tìm thấy cổ phiếu nào',
        'screener.loading': 'Đang tải...',
        'screener.applyFilters': 'Áp dụng',
        'screener.clearFilters': 'Xóa bộ lọc',
        'screener.activeFilters': 'Bộ lọc đang áp dụng',

        // Filters
        'filter.exchange': 'Sàn giao dịch',
        'filter.exchange.all': 'Tất cả sàn',
        'filter.sector': 'Ngành',
        'filter.sector.all': 'Tất cả ngành',
        'filter.pe': 'P/E',
        'filter.pe.min': 'P/E tối thiểu',
        'filter.pe.max': 'P/E tối đa',
        'filter.pb': 'P/B',
        'filter.pb.min': 'P/B tối thiểu',
        'filter.pb.max': 'P/B tối đa',
        'filter.roe': 'ROE (%)',
        'filter.roe.min': 'ROE tối thiểu',
        'filter.marketCap': 'Vốn hóa (tỷ VND)',
        'filter.marketCap.min': 'Vốn hóa tối thiểu',
        'filter.marketCap.max': 'Vốn hóa tối đa',
        'filter.rsi': 'RSI',
        'filter.rsi.min': 'RSI tối thiểu',
        'filter.rsi.max': 'RSI tối đa',
        'filter.trend': 'Xu hướng',
        'filter.trend.uptrend': 'Tăng giá',
        'filter.trend.downtrend': 'Giảm giá',
        'filter.adx': 'ADX (Sức mạnh xu hướng)',
        'filter.adx.min': 'ADX tối thiểu',

        // Table Headers
        'table.symbol': 'Mã CK',
        'table.companyName': 'Tên công ty',
        'table.exchange': 'Sàn',
        'table.price': 'Giá',
        'table.change': 'Thay đổi',
        'table.volume': 'Khối lượng',
        'table.marketCap': 'Vốn hóa',
        'table.pe': 'P/E',
        'table.pb': 'P/B',
        'table.roe': 'ROE',
        'table.sector': 'Ngành',
        'table.actions': 'Thao tác',

        // Comparison
        'comparison.title': 'So sánh cổ phiếu',
        'comparison.select': 'Chọn cổ phiếu để so sánh',
        'comparison.max': 'Tối đa 5 cổ phiếu',
        'comparison.clear': 'Xóa tất cả',

        // Database
        'database.title': 'Quản lý cơ sở dữ liệu',
        'database.status': 'Trạng thái',
        'database.lastUpdate': 'Cập nhật lần cuối',
        'database.totalStocks': 'Tổng số cổ phiếu',
        'database.updateNow': 'Cập nhật ngay',
        'database.updating': 'Đang cập nhật...',
        'database.fresh': 'Dữ liệu mới',
        'database.stale': 'Dữ liệu cũ',
        'database.outdated': 'Dữ liệu đã lỗi thời',

        // Common
        'common.loading': 'Đang tải...',
        'common.error': 'Đã xảy ra lỗi',
        'common.retry': 'Thử lại',
        'common.cancel': 'Hủy',
        'common.save': 'Lưu',
        'common.export': 'Xuất file',
        'common.exportCSV': 'Xuất CSV',
        'common.exportExcel': 'Xuất Excel',
        'common.search': 'Tìm kiếm',
        'common.noData': 'Không có dữ liệu',

        // Theme
        'theme.light': 'Sáng',
        'theme.dark': 'Tối',

        // Language
        'language.vi': 'Tiếng Việt',
        'language.en': 'English',

        // Units
        'unit.billion': 'tỷ',
        'unit.million': 'triệu',
        'unit.thousand': 'K',
    },

    en: {
        // App
        'app.title': 'VnStock Screener',
        'app.subtitle': 'Vietnamese Stock Screening Tool',

        // Navigation
        'nav.screener': 'Screener',
        'nav.comparison': 'Comparison',
        'nav.database': 'Database',
        'nav.settings': 'Settings',

        // Screener
        'screener.title': 'Stock Screener',
        'screener.filters': 'Filters',
        'screener.results': 'Results',
        'screener.noResults': 'No stocks found',
        'screener.loading': 'Loading...',
        'screener.applyFilters': 'Apply',
        'screener.clearFilters': 'Clear Filters',
        'screener.activeFilters': 'Active Filters',

        // Filters
        'filter.exchange': 'Exchange',
        'filter.exchange.all': 'All Exchanges',
        'filter.sector': 'Sector',
        'filter.sector.all': 'All Sectors',
        'filter.pe': 'P/E Ratio',
        'filter.pe.min': 'Min P/E',
        'filter.pe.max': 'Max P/E',
        'filter.pb': 'P/B Ratio',
        'filter.pb.min': 'Min P/B',
        'filter.pb.max': 'Max P/B',
        'filter.roe': 'ROE (%)',
        'filter.roe.min': 'Min ROE',
        'filter.marketCap': 'Market Cap (bil VND)',
        'filter.marketCap.min': 'Min Market Cap',
        'filter.marketCap.max': 'Max Market Cap',
        'filter.rsi': 'RSI',
        'filter.rsi.min': 'Min RSI',
        'filter.rsi.max': 'Max RSI',
        'filter.trend': 'Trend',
        'filter.trend.uptrend': 'Uptrend',
        'filter.trend.downtrend': 'Downtrend',
        'filter.adx': 'ADX (Trend Strength)',
        'filter.adx.min': 'Min ADX',

        // Table Headers
        'table.symbol': 'Symbol',
        'table.companyName': 'Company Name',
        'table.exchange': 'Exchange',
        'table.price': 'Price',
        'table.change': 'Change',
        'table.volume': 'Volume',
        'table.marketCap': 'Market Cap',
        'table.pe': 'P/E',
        'table.pb': 'P/B',
        'table.roe': 'ROE',
        'table.sector': 'Sector',
        'table.actions': 'Actions',

        // Comparison
        'comparison.title': 'Stock Comparison',
        'comparison.select': 'Select stocks to compare',
        'comparison.max': 'Maximum 5 stocks',
        'comparison.clear': 'Clear All',

        // Database
        'database.title': 'Database Management',
        'database.status': 'Status',
        'database.lastUpdate': 'Last Update',
        'database.totalStocks': 'Total Stocks',
        'database.updateNow': 'Update Now',
        'database.updating': 'Updating...',
        'database.fresh': 'Fresh Data',
        'database.stale': 'Stale Data',
        'database.outdated': 'Outdated Data',

        // Common
        'common.loading': 'Loading...',
        'common.error': 'An error occurred',
        'common.retry': 'Retry',
        'common.cancel': 'Cancel',
        'common.save': 'Save',
        'common.export': 'Export',
        'common.exportCSV': 'Export CSV',
        'common.exportExcel': 'Export Excel',
        'common.search': 'Search',
        'common.noData': 'No data available',

        // Theme
        'theme.light': 'Light',
        'theme.dark': 'Dark',

        // Language
        'language.vi': 'Tiếng Việt',
        'language.en': 'English',

        // Units
        'unit.billion': 'B',
        'unit.million': 'M',
        'unit.thousand': 'K',
    },
};

// ============================================
// Context
// ============================================

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

// ============================================
// Provider
// ============================================

interface LanguageProviderProps {
    children: ReactNode;
}

export function LanguageProvider({ children }: LanguageProviderProps) {
    const [language, setLanguageState] = useState<Language>(() => {
        const stored = localStorage.getItem('vnstock-language');
        return (stored === 'en' ? 'en' : 'vi') as Language;
    });

    useEffect(() => {
        localStorage.setItem('vnstock-language', language);
        document.documentElement.lang = language;
    }, [language]);

    const setLanguage = useCallback((lang: Language) => {
        setLanguageState(lang);
    }, []);

    const t = useCallback((key: string): string => {
        return translations[language][key] || key;
    }, [language]);

    const formatCurrency = useCallback((value: number): string => {
        if (value === null || value === undefined || isNaN(value)) return '-';

        // Format as plain number with thousands separator (e.g., 29,500)
        // Prices from API are already in VND, no conversion needed
        return new Intl.NumberFormat(language === 'vi' ? 'vi-VN' : 'en-US', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        }).format(value);
    }, [language]);

    const formatNumber = useCallback((value: number, decimals = 2): string => {
        if (value === null || value === undefined || isNaN(value)) return '-';

        return new Intl.NumberFormat(language === 'vi' ? 'vi-VN' : 'en-US', {
            minimumFractionDigits: 0,
            maximumFractionDigits: decimals,
        }).format(value);
    }, [language]);

    const formatPercent = useCallback((value: number, decimals = 2): string => {
        if (value === null || value === undefined || isNaN(value)) return '-';

        return new Intl.NumberFormat(language === 'vi' ? 'vi-VN' : 'en-US', {
            style: 'percent',
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals,
        }).format(value / 100);
    }, [language]);

    const value: LanguageContextType = {
        language,
        setLanguage,
        t,
        formatCurrency,
        formatNumber,
        formatPercent,
    };

    return (
        <LanguageContext.Provider value={value}>
            {children}
        </LanguageContext.Provider>
    );
}

// ============================================
// Hook
// ============================================

export function useLanguage(): LanguageContextType {
    const context = useContext(LanguageContext);
    if (!context) {
        throw new Error('useLanguage must be used within a LanguageProvider');
    }
    return context;
}
