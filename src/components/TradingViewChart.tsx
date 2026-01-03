import { useEffect, useRef, useMemo, useState } from 'react';

declare global {
    interface Window {
        TradingView: any;
    }
}

interface TradingViewChartProps {
    symbol: string;
    exchange?: string;
    height?: number;
    showToolbar?: boolean;
}

// Known VN stocks that work with TradingView (major stocks)
const MAJOR_VN_STOCKS = [
    'VNM', 'VCB', 'VIC', 'HPG', 'FPT', 'MWG', 'VHM', 'VRE', 'MSN', 'TCB',
    'VPB', 'MBB', 'ACB', 'CTG', 'BID', 'SSI', 'VNI', 'GAS', 'SAB', 'PLX',
    'VJC', 'REE', 'PNJ', 'DGW', 'VND', 'HCM', 'GVR', 'DPM', 'PVD', 'POW'
];

export function TradingViewChart({
    symbol,
    exchange = 'HOSE',
    height = 400,
    showToolbar = true
}: TradingViewChartProps) {
    const containerRef = useRef<HTMLDivElement>(null);
    const widgetRef = useRef<any>(null);
    const [hasError, setHasError] = useState(false);

    // Stable container ID - important for TradingView widget
    const containerId = useMemo(() =>
        `tv-chart-${symbol.replace(/[^a-zA-Z0-9]/g, '')}-${Math.random().toString(36).substr(2, 9)}`,
        [symbol]
    );

    // Map exchange to TradingView prefix
    const getTvSymbol = () => {
        const exchangePrefix = exchange?.toUpperCase() || 'HOSE';
        // TradingView uses exchange prefixes for Vietnam stocks
        // HOSE -> HOSE:VCB, HNX -> HNX:ACB, UPCOM -> UPCOM:ABC
        return `${exchangePrefix}:${symbol}`;
    };

    // Check if symbol is likely supported by TradingView
    const isLikelySupported = MAJOR_VN_STOCKS.includes(symbol.toUpperCase());

    useEffect(() => {
        if (!containerRef.current) return;

        setHasError(false);

        // Load TradingView script if not already loaded
        const scriptId = 'tradingview-widget-script';
        let script = document.getElementById(scriptId) as HTMLScriptElement;

        if (!script) {
            script = document.createElement('script');
            script.id = scriptId;
            script.src = 'https://s3.tradingview.com/tv.js';
            script.async = true;
            document.head.appendChild(script);
        }

        const initWidget = () => {
            if (!window.TradingView || !containerRef.current) return;

            // Clear previous widget
            if (widgetRef.current) {
                containerRef.current.innerHTML = '';
            }

            try {
                widgetRef.current = new window.TradingView.widget({
                    symbol: getTvSymbol(),
                    container_id: containerId,
                    width: '100%',
                    height: height,
                    autosize: false,
                    theme: document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light',
                    style: '1', // Candlestick
                    locale: 'vi_VN',
                    toolbar_bg: 'transparent',
                    enable_publishing: false,
                    hide_top_toolbar: !showToolbar,
                    hide_legend: false,
                    save_image: false,
                    studies: ['RSI@tv-basicstudies', 'MASimple@tv-basicstudies'],
                    timezone: 'Asia/Ho_Chi_Minh',
                    withdateranges: true,
                    range: '6M',
                    allow_symbol_change: false,
                    details: true,
                    hotlist: false,
                    calendar: false,
                });

                // Set a timeout to detect if widget failed to load content
                setTimeout(() => {
                    // Check if the iframe has an error indicator
                    const iframe = containerRef.current?.querySelector('iframe');
                    if (!iframe) {
                        setHasError(true);
                    }
                }, 5000);
            } catch (error) {
                console.error('Error initializing TradingView widget:', error);
                setHasError(true);
            }
        };

        if (window.TradingView) {
            initWidget();
        } else {
            script.onload = initWidget;
        }

        return () => {
            if (containerRef.current) {
                containerRef.current.innerHTML = '';
            }
        };
    }, [symbol, exchange, height, showToolbar, containerId]);

    // Show fallback for unsupported or errored symbols
    if (hasError) {
        return (
            <div
                className="fallback-chart"
                style={{
                    height: `${height}px`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background: 'var(--bg-tertiary)',
                    borderRadius: 'var(--radius-md)',
                    flexDirection: 'column',
                    gap: '12px',
                    border: '1px dashed var(--border)',
                }}
            >
                <span style={{ fontSize: '48px', opacity: 0.6 }}>📊</span>
                <div style={{ textAlign: 'center' }}>
                    <div style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>
                        {symbol}
                    </div>
                    <div style={{ fontSize: '13px', color: 'var(--text-disabled)', marginTop: '4px' }}>
                        Mã giao dịch không hợp lệ
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--text-disabled)', marginTop: '8px' }}>
                        Không có mã giao dịch này, vui lòng chọn mã khác.
                    </div>
                </div>
                <button
                    onClick={() => setHasError(false)}
                    style={{
                        marginTop: '8px',
                        padding: '6px 12px',
                        borderRadius: '4px',
                        border: '1px solid var(--border)',
                        background: 'var(--bg-secondary)',
                        cursor: 'pointer',
                        fontSize: '12px'
                    }}
                >
                    Thay đổi mã giao dịch
                </button>
            </div>
        );
    }

    return (
        <div className="tradingview-chart-container">
            <div
                id={containerId}
                ref={containerRef}
                style={{ height: `${height}px`, width: '100%' }}
            />
            {!isLikelySupported && (
                <div style={{
                    position: 'absolute',
                    top: '8px',
                    right: '8px',
                    padding: '4px 8px',
                    background: 'rgba(255, 193, 7, 0.9)',
                    borderRadius: '4px',
                    fontSize: '11px',
                    color: '#333'
                }}>
                    ⚠️ {symbol} có thể không được hỗ trợ
                </div>
            )}
        </div>
    );
}

// Simple fallback chart for when TradingView is not available
export function FallbackChart({ symbol, height = 300 }: { symbol: string; height?: number }) {
    return (
        <div
            className="fallback-chart"
            style={{
                height: `${height}px`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: 'var(--bg-tertiary)',
                borderRadius: 'var(--radius-md)',
                flexDirection: 'column',
                gap: '8px'
            }}
        >
            <span style={{ fontSize: '48px', opacity: 0.5 }}>📈</span>
            <span style={{ color: 'var(--text-secondary)' }}>
                Biểu đồ giá {symbol}
            </span>
            <span style={{ fontSize: '12px', color: 'var(--text-disabled)' }}>
                Đang tải dữ liệu...
            </span>
        </div>
    );
}

