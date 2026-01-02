-- VnStock Screener Database Schema
-- SQLite database for Vietnamese stock market data

-- ============================================
-- Stocks Table (Master list)
-- ============================================
CREATE TABLE IF NOT EXISTS stocks (
    symbol TEXT PRIMARY KEY,
    company_name TEXT,
    exchange TEXT,  -- HOSE, HNX, UPCOM, or NULL

    sector TEXT,
    industry TEXT,
    listing_date TEXT,
    shares_outstanding INTEGER,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_stocks_exchange ON stocks(exchange);
CREATE INDEX IF NOT EXISTS idx_stocks_sector ON stocks(sector);

-- ============================================
-- Stock Prices (Current/Latest)
-- ============================================
CREATE TABLE IF NOT EXISTS stock_prices (
    symbol TEXT PRIMARY KEY,
    current_price REAL,
    price_change REAL,
    percent_change REAL,
    open_price REAL,
    high_price REAL,
    low_price REAL,
    close_price REAL,
    volume INTEGER,
    market_cap REAL,
    pe_ratio REAL,
    pb_ratio REAL,
    eps REAL,
    bvps REAL,
    roe REAL,
    roa REAL,
    revenue REAL,
    profit REAL,
    data_source TEXT DEFAULT 'vnstock',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (symbol) REFERENCES stocks(symbol)
);

CREATE INDEX IF NOT EXISTS idx_stock_prices_pe ON stock_prices(pe_ratio);
CREATE INDEX IF NOT EXISTS idx_stock_prices_pb ON stock_prices(pb_ratio);
CREATE INDEX IF NOT EXISTS idx_stock_prices_roe ON stock_prices(roe);
CREATE INDEX IF NOT EXISTS idx_stock_prices_market_cap ON stock_prices(market_cap);

-- ============================================
-- Price History (OHLCV)
-- ============================================
CREATE TABLE IF NOT EXISTS price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    date TEXT NOT NULL,
    open_price REAL,
    high_price REAL,
    low_price REAL,
    close_price REAL,
    volume INTEGER,
    adjusted_close REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, date),
    FOREIGN KEY (symbol) REFERENCES stocks(symbol)
);

CREATE INDEX IF NOT EXISTS idx_price_history_symbol ON price_history(symbol);
CREATE INDEX IF NOT EXISTS idx_price_history_date ON price_history(date);
CREATE INDEX IF NOT EXISTS idx_price_history_symbol_date ON price_history(symbol, date);

-- ============================================
-- Financial Metrics (Detailed)
-- ============================================
CREATE TABLE IF NOT EXISTS financial_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    period TEXT,
    period_type TEXT CHECK (period_type IN ('annual', 'quarterly')),
    fiscal_year INTEGER,
    fiscal_quarter INTEGER,
    
    -- Income Statement
    revenue REAL,
    gross_profit REAL,
    operating_profit REAL,
    net_profit REAL,
    
    -- Balance Sheet
    total_assets REAL,
    total_liabilities REAL,
    total_equity REAL,
    current_assets REAL,
    current_liabilities REAL,
    cash_and_equivalents REAL,
    
    -- Ratios
    pe_ratio REAL,
    pb_ratio REAL,
    ps_ratio REAL,
    debt_to_equity REAL,
    current_ratio REAL,
    roe REAL,
    roa REAL,
    gross_margin REAL,
    operating_margin REAL,
    net_margin REAL,
    
    -- Growth
    revenue_growth_yoy REAL,
    profit_growth_yoy REAL,
    
    -- Per Share
    earnings_per_share REAL,
    book_value_per_share REAL,
    
    data_source TEXT DEFAULT 'vnstock',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, period),
    FOREIGN KEY (symbol) REFERENCES stocks(symbol)
);

CREATE INDEX IF NOT EXISTS idx_financial_metrics_symbol ON financial_metrics(symbol);
CREATE INDEX IF NOT EXISTS idx_financial_metrics_period ON financial_metrics(period);

-- ============================================
-- Update Logs (For monitoring)
-- ============================================
CREATE TABLE IF NOT EXISTS update_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    update_type TEXT NOT NULL,
    status TEXT CHECK (status IN ('started', 'running', 'completed', 'failed', 'cancelled')),
    records_processed INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds REAL
);

CREATE INDEX IF NOT EXISTS idx_update_logs_type ON update_logs(update_type);
CREATE INDEX IF NOT EXISTS idx_update_logs_status ON update_logs(status);
CREATE INDEX IF NOT EXISTS idx_update_logs_started_at ON update_logs(started_at);

-- ============================================
-- Rate Limit Statistics
-- ============================================
CREATE TABLE IF NOT EXISTS rate_limit_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    requests_made INTEGER DEFAULT 0,
    requests_throttled INTEGER DEFAULT 0,
    circuit_breaker_trips INTEGER DEFAULT 0,
    avg_response_time_ms REAL,
    period_start TIMESTAMP,
    period_end TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_rate_limit_stats_timestamp ON rate_limit_stats(timestamp);

-- ============================================
-- Scheduler State (For persistence)
-- ============================================
CREATE TABLE IF NOT EXISTS scheduler_state (
    task_name TEXT PRIMARY KEY,
    last_run TIMESTAMP,
    next_run TIMESTAMP,
    run_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    last_status TEXT,
    last_error TEXT,
    is_enabled INTEGER DEFAULT 1,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- Data Update Tracker (Per-symbol, per-type tracking)
-- ============================================
CREATE TABLE IF NOT EXISTS data_update_tracker (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    data_type TEXT NOT NULL,  -- 'price', 'financials', 'dividends', 'ratings', 'history'
    last_update TIMESTAMP,
    next_update_due TIMESTAMP,
    update_count INTEGER DEFAULT 0,
    last_status TEXT CHECK (last_status IN ('success', 'failed', 'pending', 'skipped')),
    error_message TEXT,
    priority INTEGER DEFAULT 3,  -- 1=highest, 5=lowest
    data_hash TEXT,  -- For detecting if data actually changed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, data_type)
);

CREATE INDEX IF NOT EXISTS idx_update_tracker_symbol ON data_update_tracker(symbol);
CREATE INDEX IF NOT EXISTS idx_update_tracker_type ON data_update_tracker(data_type);
CREATE INDEX IF NOT EXISTS idx_update_tracker_next_due ON data_update_tracker(next_update_due);
CREATE INDEX IF NOT EXISTS idx_update_tracker_status ON data_update_tracker(last_status);

-- ============================================
-- Dividend History
-- ============================================
CREATE TABLE IF NOT EXISTS dividend_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    ex_date TEXT,
    record_date TEXT,
    payment_date TEXT,
    cash_dividend REAL,
    stock_dividend REAL,
    dividend_yield REAL,
    fiscal_year INTEGER,
    data_source TEXT DEFAULT 'vnstock',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, ex_date),
    FOREIGN KEY (symbol) REFERENCES stocks(symbol)
);

CREATE INDEX IF NOT EXISTS idx_dividend_symbol ON dividend_history(symbol);
CREATE INDEX IF NOT EXISTS idx_dividend_ex_date ON dividend_history(ex_date);

-- ============================================
-- Company Ratings
-- ============================================
CREATE TABLE IF NOT EXISTS company_ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    rating_type TEXT NOT NULL,  -- 'general', 'business_model', 'business_operation', 'financial_health', 'valuation'
    rating_value REAL,
    rating_grade TEXT,  -- A, B, C, D, F
    criteria_scores TEXT,  -- JSON of individual criteria
    rating_date TEXT,
    data_source TEXT DEFAULT 'vnstock',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, rating_type),
    FOREIGN KEY (symbol) REFERENCES stocks(symbol)
);

CREATE INDEX IF NOT EXISTS idx_ratings_symbol ON company_ratings(symbol);
CREATE INDEX IF NOT EXISTS idx_ratings_type ON company_ratings(rating_type);

-- ============================================
-- Intraday Prices (Real-time tracking)
-- ============================================
CREATE TABLE IF NOT EXISTS intraday_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    price REAL,
    volume INTEGER,
    bid_price REAL,
    ask_price REAL,
    total_volume INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, timestamp),
    FOREIGN KEY (symbol) REFERENCES stocks(symbol)
);

CREATE INDEX IF NOT EXISTS idx_intraday_symbol ON intraday_prices(symbol);
CREATE INDEX IF NOT EXISTS idx_intraday_timestamp ON intraday_prices(timestamp);
CREATE INDEX IF NOT EXISTS idx_intraday_symbol_time ON intraday_prices(symbol, timestamp);

-- ============================================
-- Market Indices
-- ============================================
CREATE TABLE IF NOT EXISTS market_indices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    index_code TEXT NOT NULL,  -- 'VNINDEX', 'HNX', 'UPCOM', 'VN30'
    timestamp TIMESTAMP NOT NULL,
    value REAL,
    change_value REAL,
    change_percent REAL,
    volume INTEGER,
    total_value REAL,
    advances INTEGER,
    declines INTEGER,
    unchanged INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(index_code, timestamp)
);

CREATE INDEX IF NOT EXISTS idx_indices_code ON market_indices(index_code);
CREATE INDEX IF NOT EXISTS idx_indices_timestamp ON market_indices(timestamp);

-- ============================================
-- Stock Technical Metrics (Calculated Indicators)
-- ============================================
CREATE TABLE IF NOT EXISTS stock_metrics (
    symbol TEXT PRIMARY KEY,
    
    -- Volume Metrics
    adtv_shares REAL,           -- Average Daily Trading Volume (shares)
    adtv_value REAL,            -- Average Daily Trading Value (billion VND)
    volume_vs_adtv REAL,        -- Current volume vs ADTV (%)
    
    -- Technical Indicators
    rsi_14 REAL,                -- RSI 14-period
    macd REAL,                  -- MACD value
    macd_signal REAL,           -- MACD signal line
    macd_histogram REAL,        -- MACD histogram
    adx REAL,                   -- Average Directional Index
    
    -- Moving Averages
    ema_20 REAL,
    ema_50 REAL,
    ema_200 REAL,
    
    -- EMA Relationships (%)
    price_vs_ema20 REAL,        -- Price vs EMA20 (%)
    ema20_vs_ema50 REAL,        -- EMA20 vs EMA50 (%)
    ema50_vs_ema200 REAL,       -- EMA50 vs EMA200 (%)
    
    -- Returns
    price_return_1m REAL,       -- 1 month return (%)
    price_return_3m REAL,       -- 3 month return (%)
    price_fluctuation REAL,     -- 30-day volatility (%)
    
    -- Trend
    stock_trend TEXT,           -- 'strong_uptrend', 'uptrend', 'sideways', 'downtrend', 'strong_downtrend'
    
    -- Financial Indicators (from latest report)
    net_margin REAL,
    gross_margin REAL,
    npat_growth_yoy REAL,
    revenue_growth_yoy REAL,
    
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (symbol) REFERENCES stocks(symbol)
);

CREATE INDEX IF NOT EXISTS idx_metrics_rsi ON stock_metrics(rsi_14);
CREATE INDEX IF NOT EXISTS idx_metrics_trend ON stock_metrics(stock_trend);
CREATE INDEX IF NOT EXISTS idx_metrics_adx ON stock_metrics(adx);

-- ============================================
-- Screener Metrics (84-column TCBS screener data)
-- Most efficient: 1 API call = all stocks
-- ============================================
CREATE TABLE IF NOT EXISTS screener_metrics (
    symbol TEXT PRIMARY KEY,
    exchange TEXT,
    industry TEXT,
    
    -- Fundamental Metrics
    market_cap REAL,
    pe_ratio REAL,
    pb_ratio REAL,
    ev_ebitda REAL,
    eps REAL,
    roe REAL,
    dividend_yield REAL,
    gross_margin REAL,
    net_margin REAL,
    doe REAL,  -- Debt/Equity
    
    -- Growth Metrics
    revenue_growth_1y REAL,
    revenue_growth_5y REAL,
    eps_growth_1y REAL,
    eps_growth_5y REAL,
    last_quarter_revenue_growth REAL,
    last_quarter_profit_growth REAL,
    
    -- Technical Indicators
    rsi14 REAL,
    macd_histogram TEXT,
    price_vs_sma5 TEXT,
    price_vs_sma10 TEXT,
    price_vs_sma20 TEXT,
    price_vs_sma50 TEXT,
    price_vs_sma100 TEXT,
    bolling_band_signal TEXT,
    dmi_signal TEXT,
    rsi14_status TEXT,
    
    -- Volume Analysis
    vol_vs_sma5 REAL,
    vol_vs_sma10 REAL,
    vol_vs_sma20 REAL,
    vol_vs_sma50 REAL,
    avg_trading_value_5d REAL,
    avg_trading_value_10d REAL,
    avg_trading_value_20d REAL,
    
    -- Price Performance
    price_near_realtime REAL,
    price_growth_1w REAL,
    price_growth_1m REAL,
    prev_1d_growth_pct REAL,
    prev_1m_growth_pct REAL,
    prev_1y_growth_pct REAL,
    prev_5y_growth_pct REAL,
    pct_away_from_hist_peak REAL,
    pct_off_hist_bottom REAL,
    pct_1y_from_peak REAL,
    pct_1y_from_bottom REAL,
    
    -- Momentum & Relative Strength
    relative_strength_3d REAL,
    rel_strength_1m REAL,
    rel_strength_3m REAL,
    rel_strength_1y REAL,
    tc_rs REAL,
    alpha REAL,
    beta REAL,
    
    -- TCBS Ratings & Signals
    stock_rating REAL,
    business_operation REAL,
    business_model REAL,
    financial_health REAL,
    tcbs_recommend TEXT,
    tcbs_buy_sell_signal TEXT,
    
    -- Foreign Trading
    foreign_vol_pct REAL,
    foreign_transaction TEXT,
    foreign_buysell_20s REAL,
    
    -- Special Signals
    uptrend TEXT,
    breakout TEXT,
    price_break_out52_week TEXT,
    heating_up TEXT,
    
    -- Continuous Price Movement
    num_increase_continuous_day INTEGER,
    num_decrease_continuous_day INTEGER,
    
    -- Other
    profit_last_4q REAL,
    free_transfer_rate REAL,
    net_cash_per_market_cap REAL,
    net_cash_per_total_assets REAL,
    has_financial_report TEXT,
    
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (symbol) REFERENCES stocks(symbol)
);

CREATE INDEX IF NOT EXISTS idx_screener_exchange ON screener_metrics(exchange);
CREATE INDEX IF NOT EXISTS idx_screener_industry ON screener_metrics(industry);
CREATE INDEX IF NOT EXISTS idx_screener_pe ON screener_metrics(pe_ratio);
CREATE INDEX IF NOT EXISTS idx_screener_roe ON screener_metrics(roe);
CREATE INDEX IF NOT EXISTS idx_screener_market_cap ON screener_metrics(market_cap);
CREATE INDEX IF NOT EXISTS idx_screener_rsi ON screener_metrics(rsi14);
CREATE INDEX IF NOT EXISTS idx_screener_rating ON screener_metrics(stock_rating);

-- ============================================
-- Company Shareholders
-- ============================================
CREATE TABLE IF NOT EXISTS shareholders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    shareholder_id TEXT,
    shareholder_name TEXT,
    quantity INTEGER,
    ownership_percent REAL,
    update_date TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, shareholder_id),
    FOREIGN KEY (symbol) REFERENCES stocks(symbol)
);

CREATE INDEX IF NOT EXISTS idx_shareholders_symbol ON shareholders(symbol);
CREATE INDEX IF NOT EXISTS idx_shareholders_ownership ON shareholders(ownership_percent);

-- ============================================
-- Company Officers (Management)
-- ============================================
CREATE TABLE IF NOT EXISTS officers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    officer_id TEXT,
    officer_name TEXT,
    position TEXT,
    position_short TEXT,
    ownership_percent REAL,
    quantity INTEGER,
    status TEXT,  -- 'working', 'resigned'
    update_date TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, officer_id),
    FOREIGN KEY (symbol) REFERENCES stocks(symbol)
);

CREATE INDEX IF NOT EXISTS idx_officers_symbol ON officers(symbol);
CREATE INDEX IF NOT EXISTS idx_officers_status ON officers(status);

-- ============================================
-- Price Board (Real-time bid/ask data)
-- ============================================
CREATE TABLE IF NOT EXISTS price_board (
    symbol TEXT PRIMARY KEY,
    exchange TEXT,
    ceiling REAL,
    floor REAL,
    ref_price REAL,
    prior_close REAL,
    
    -- Match Info
    match_price REAL,
    match_volume INTEGER,
    accumulated_volume INTEGER,
    accumulated_value REAL,
    avg_match_price REAL,
    highest REAL,
    lowest REAL,
    
    -- Foreign Trading
    foreign_buy_volume INTEGER,
    foreign_sell_volume INTEGER,
    current_room INTEGER,
    total_room INTEGER,
    
    -- Bid Levels
    bid_1_price REAL,
    bid_1_volume INTEGER,
    bid_2_price REAL,
    bid_2_volume INTEGER,
    bid_3_price REAL,
    bid_3_volume INTEGER,
    
    -- Ask Levels
    ask_1_price REAL,
    ask_1_volume INTEGER,
    ask_2_price REAL,
    ask_2_volume INTEGER,
    ask_3_price REAL,
    ask_3_volume INTEGER,
    
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (symbol) REFERENCES stocks(symbol)
);

CREATE INDEX IF NOT EXISTS idx_price_board_exchange ON price_board(exchange);

-- ============================================
-- Views for Common Queries
-- ============================================

-- Stocks with latest prices
CREATE VIEW IF NOT EXISTS v_stocks_with_prices AS
SELECT 
    s.symbol,
    s.company_name,
    s.exchange,
    s.sector,
    s.industry,
    sp.current_price,
    sp.price_change,
    sp.percent_change,
    sp.volume,
    sp.market_cap,
    sp.pe_ratio,
    sp.pb_ratio,
    sp.roe,
    sp.roa,
    sp.eps,
    sp.updated_at
FROM stocks s
LEFT JOIN stock_prices sp ON s.symbol = sp.symbol
WHERE s.is_active = 1;

-- Database statistics
CREATE VIEW IF NOT EXISTS v_database_stats AS
SELECT 
    (SELECT COUNT(*) FROM stocks WHERE is_active = 1) as total_stocks,
    (SELECT COUNT(*) FROM stock_prices) as stocks_with_prices,
    (SELECT COUNT(*) FROM financial_metrics) as financial_records,
    (SELECT COUNT(*) FROM price_history) as price_history_records,
    (SELECT MAX(updated_at) FROM stock_prices) as last_price_update,
    (SELECT MAX(updated_at) FROM stocks) as last_stock_update;
