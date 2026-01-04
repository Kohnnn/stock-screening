"""
FastAPI Backend for VnStock Screener.

Provides REST API for the React frontend and manages data updates.
"""

import asyncio
import shutil
from datetime import datetime
from typing import Optional, List
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from loguru import logger

from config import settings
from database import Database, get_database
from vnstock_collector import get_collector
from update_scheduler import get_scheduler
from circuit_breaker import get_circuit_breaker
from rate_limiter import get_rate_limiter
from ssi_iboard_collector import get_ssi_collector


# ============================================
# Logging Configuration
# ============================================

logger.add(
    settings.LOG_FILE,
    rotation=settings.LOG_ROTATION,
    retention=settings.LOG_RETENTION,
    level=settings.LOG_LEVEL,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
)


# ============================================
# Lifespan Events
# ============================================

def copy_initial_database_if_missing():
    """
    Copy initial_database.db to runtime location if runtime DB doesn't exist.
    This ensures new deployments have baseline data.
    """
    data_dir = Path(__file__).parent / "data"
    initial_db = data_dir / "initial_database.db"
    runtime_db = Path(settings.DATABASE_PATH)
    
    if initial_db.exists() and not runtime_db.exists():
        logger.info(f"📦 Copying initial database to {runtime_db}")
        runtime_db.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(initial_db, runtime_db)
        logger.info(f"✅ Database initialized from initial_database.db")
        return True
    elif not runtime_db.exists() and not initial_db.exists():
        logger.warning("⚠️ No initial_database.db found - starting with empty database")
    return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("🚀 VnStock Screener API starting...")
    
    # Copy initial database if needed
    copy_initial_database_if_missing()
    
    # Initialize database
    db = await get_database()
    logger.info(f"✅ Database initialized: {settings.DATABASE_PATH}")
    
    # Check data freshness
    freshness = await db.get_data_freshness()
    logger.info(f"📊 Data freshness: {freshness}")
    
    # Run data freshness check with new system
    try:
        from data_freshness import DataFreshnessChecker
        checker = DataFreshnessChecker(settings.DATABASE_PATH)
        summary = checker.get_update_summary()
        logger.info(f"📊 Data freshness summary:")
        for dtype, stats in summary.items():
            logger.info(f"   {dtype}: {stats['percent_fresh']}% fresh ({stats['fresh']}/{stats['total']})")
    except Exception as e:
        logger.warning(f"⚠️ New freshness check not available: {e}")
    
    # Run startup data check with update registry
    try:
        from update_registry import get_update_registry
        registry = await get_update_registry(db)
        update_summary = await registry.startup_data_check()
        logger.info(
            f"📊 Data check: {update_summary['totals']['symbols_tracked']} symbols, "
            f"Health: {update_summary['health_status']}"
        )
        if update_summary.get('recommendations'):
            for rec in update_summary['recommendations'][:3]:
                logger.info(f"  ⚡ {rec['priority'].upper()}: {rec['message']}")
    except Exception as e:
        logger.warning(f"⚠️ Startup data check failed: {e}")
    
    yield
    
    # Shutdown
    logger.info("👋 VnStock Screener API shutting down...")


# ============================================
# FastAPI App
# ============================================

app = FastAPI(
    title="VnStock Screener API",
    description="Vietnamese Stock Market Screening API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
origins = settings.CORS_ORIGINS.split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# Response Models
# ============================================

class StockResponse(BaseModel):
    symbol: str
    company_name: Optional[str] = None
    exchange: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    current_price: Optional[float] = None
    price_change: Optional[float] = None
    percent_change: Optional[float] = None
    volume: Optional[int] = None
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    roe: Optional[float] = None
    roa: Optional[float] = None
    eps: Optional[float] = None
    
    # Financials (Added)
    revenue: Optional[float] = None
    profit: Optional[float] = None
    total_assets: Optional[float] = None
    total_debt: Optional[float] = None
    owner_equity: Optional[float] = None
    cash: Optional[float] = None
    debt_to_equity: Optional[float] = None
    foreign_ownership: Optional[float] = None
    gross_margin: Optional[float] = None
    net_margin: Optional[float] = None


class StockListResponse(BaseModel):
    stocks: List[StockResponse]
    total: int
    page: int
    page_size: int


class DatabaseStatusResponse(BaseModel):
    status: str
    stocks_count: int
    stocks_with_prices: int
    last_update: Optional[str] = None
    database_size_mb: Optional[float] = None
    is_updating: bool = False


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    database: str
    circuit_breaker: str
    rate_limiter: dict


# ============================================
# Stock Endpoints
# ============================================

@app.get("/api/stocks", response_model=StockListResponse)
async def get_stocks(
    exchange: Optional[str] = Query(None, description="Filter by exchange (HOSE, HNX, UPCOM)"),
    sector: Optional[str] = Query(None, description="Filter by sector"),
    pe_min: Optional[float] = Query(None, description="Minimum P/E ratio"),
    pe_max: Optional[float] = Query(None, description="Maximum P/E ratio"),
    pb_min: Optional[float] = Query(None, description="Minimum P/B ratio"),
    pb_max: Optional[float] = Query(None, description="Maximum P/B ratio"),
    roe_min: Optional[float] = Query(None, description="Minimum ROE"),
    market_cap_min: Optional[float] = Query(None, description="Minimum market cap"),
    search: Optional[str] = Query(None, description="Search by symbol or name"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Items per page"),
):
    """Get stocks with optional filters."""
    db = await get_database()
    
    offset = (page - 1) * page_size
    
    stocks = await db.get_stocks(
        exchange=exchange,
        sector=sector,
        pe_min=pe_min,
        pe_max=pe_max,
        pb_min=pb_min,
        pb_max=pb_max,
        roe_min=roe_min,
        market_cap_min=market_cap_min,
        search=search,
        limit=page_size,
        offset=offset,
    )
    
    total = await db.get_stock_count(exchange=exchange)
    
    return StockListResponse(
        stocks=[StockResponse(**s) for s in stocks],
        total=total,
        page=page,
        page_size=page_size,
    )


# Note: Static routes must come BEFORE {symbol} routes
@app.get("/api/stocks/screener")
async def screen_stocks(
    # === Basic Filters ===
    exchange: Optional[str] = Query(None, description="Filter by exchange (HOSE, HNX, UPCOM)"),
    sector: Optional[str] = Query(None, description="Filter by sector"),
    industry: Optional[str] = Query(None, description="Filter by industry"),
    search: Optional[str] = Query(None, description="Search by symbol or name"),
    
    # === General Metrics (Nhóm Tổng Quan) ===
    market_cap_min: Optional[float] = Query(None, ge=0, description="Vốn hóa tối thiểu (bn VND)"),
    market_cap_max: Optional[float] = Query(None, ge=0, description="Vốn hóa tối đa (bn VND)"),
    price_min: Optional[float] = Query(None, ge=0, description="Giá tối thiểu (VND)"),
    price_max: Optional[float] = Query(None, ge=0, description="Giá tối đa (VND)"),
    price_change_min: Optional[float] = Query(None, description="Thay đổi giá % tối thiểu"),
    price_change_max: Optional[float] = Query(None, description="Thay đổi giá % tối đa"),
    adtv_value_min: Optional[float] = Query(None, ge=0, description="GTGD trung bình tối thiểu (bn VND)"),
    volume_vs_adtv_min: Optional[float] = Query(None, description="KLGD/KLGD trung bình tối thiểu (%)"),
    
    # === Technical Signals (Nhóm Tín Hiệu Kỹ Thuật) ===
    stock_rating_min: Optional[float] = Query(None, description="Sức mạnh cổ phiếu tối thiểu"),
    rs_min: Optional[float] = Query(None, description="RS (Sức mạnh tương quan) tối thiểu"),
    rs_max: Optional[float] = Query(None, description="RS (Sức mạnh tương quan) tối đa"),
    rsi_min: Optional[float] = Query(None, ge=0, le=100, description="RSI tối thiểu (0-100)"),
    rsi_max: Optional[float] = Query(None, ge=0, le=100, description="RSI tối đa (0-100)"),
    price_vs_sma20_min: Optional[float] = Query(None, description="Giá/SMA20 % tối thiểu"),
    price_vs_sma20_max: Optional[float] = Query(None, description="Giá/SMA20 % tối đa"),
    macd_histogram_min: Optional[float] = Query(None, description="MACD Histogram tối thiểu"),
    stock_trend: Optional[str] = Query(None, description="Xu hướng: uptrend, breakout, heating_up"),
    price_return_1m_min: Optional[float] = Query(None, description="Tỷ suất lợi nhuận 1 tháng tối thiểu (%)"),
    price_return_1m_max: Optional[float] = Query(None, description="Tỷ suất lợi nhuận 1 tháng tối đa (%)"),
    
    # === Financial Indicators (Nhóm Chỉ Số Tài Chính) ===
    pe_min: Optional[float] = Query(None, ge=0, description="P/E tối thiểu"),
    pe_max: Optional[float] = Query(None, ge=0, description="P/E tối đa"),
    pb_min: Optional[float] = Query(None, ge=0, description="P/B tối thiểu"),
    pb_max: Optional[float] = Query(None, ge=0, description="P/B tối đa"),
    roe_min: Optional[float] = Query(None, description="ROE % tối thiểu"),
    roe_max: Optional[float] = Query(None, description="ROE % tối đa"),
    revenue_growth_min: Optional[float] = Query(None, description="Tăng trưởng doanh thu % tối thiểu"),
    npat_growth_min: Optional[float] = Query(None, description="Tăng trưởng LNST % tối thiểu"),
    net_margin_min: Optional[float] = Query(None, description="Biên LN ròng % tối thiểu"),
    gross_margin_min: Optional[float] = Query(None, description="Biên LN gộp % tối thiểu"),
    dividend_yield_min: Optional[float] = Query(None, ge=0, description="Tỷ suất cổ tức % tối thiểu"),
    
    # === Pagination & Sorting ===
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=2000, description="Items per page"),
    sort_by: Optional[str] = Query('market_cap', description="Sort by field"),
    order: Optional[str] = Query('desc', description="Sort order (asc/desc)"),
):
    """
    Advanced stock screener with comprehensive filters.
    
    Supports 25+ filter parameters across 3 categories:
    - General (Tổng Quan): Market Cap, Price, ADTV, Volume
    - Technical (Kỹ Thuật): RSI, MACD, RS, SMA, Trends
    - Financial (Tài Chính): P/E, P/B, ROE, Margins, Growth
    
    Stock trend options: 'uptrend', 'breakout', 'heating_up'
    """
    db = await get_database()
    
    offset = (page - 1) * page_size
    
    # Get stocks with comprehensive screener data
    stocks = await db.get_stocks_with_screener_data(
        # Basic
        exchange=exchange,
        sector=sector,
        industry=industry,
        search=search,
        # General
        market_cap_min=market_cap_min,
        market_cap_max=market_cap_max,
        price_min=price_min,
        price_max=price_max,
        price_change_min=price_change_min,
        price_change_max=price_change_max,
        adtv_value_min=adtv_value_min,
        volume_vs_adtv_min=volume_vs_adtv_min,
        # Technical
        stock_rating_min=stock_rating_min,
        rs_min=rs_min,
        rs_max=rs_max,
        rsi_min=rsi_min,
        rsi_max=rsi_max,
        price_vs_sma20_min=price_vs_sma20_min,
        price_vs_sma20_max=price_vs_sma20_max,
        macd_histogram_min=macd_histogram_min,
        stock_trend=stock_trend,
        price_return_1m_min=price_return_1m_min,
        price_return_1m_max=price_return_1m_max,
        # Financial
        pe_min=pe_min,
        pe_max=pe_max,
        pb_min=pb_min,
        pb_max=pb_max,
        roe_min=roe_min,
        roe_max=roe_max,
        revenue_growth_min=revenue_growth_min,
        npat_growth_min=npat_growth_min,
        net_margin_min=net_margin_min,
        gross_margin_min=gross_margin_min,
        dividend_yield_min=dividend_yield_min,
        # Sort & Paginate
        sort_by=sort_by,
        order=order,
        limit=page_size,
        offset=offset,
    )
    
    # Get total count for pagination
    total = await db.count_stocks_with_screener_data(
        exchange=exchange,
        sector=sector,
        search=search,
        pe_min=pe_min,
        pe_max=pe_max,
        pb_min=pb_min,
        pb_max=pb_max,
        roe_min=roe_min,
        rsi_min=rsi_min,
        rsi_max=rsi_max,
        market_cap_min=market_cap_min,
    )
    
    return {
        "stocks": stocks,
        "total": total,
        "page": page,
        "page_size": page_size,
        "filters_applied": {
            "general": {
                "market_cap": {"min": market_cap_min, "max": market_cap_max},
                "price": {"min": price_min, "max": price_max},
                "price_change": {"min": price_change_min, "max": price_change_max},
                "adtv_value_min": adtv_value_min,
            },
            "technical": {
                "rsi": {"min": rsi_min, "max": rsi_max},
                "stock_rating_min": stock_rating_min,
                "rs": {"min": rs_min, "max": rs_max},
                "price_vs_sma20": {"min": price_vs_sma20_min, "max": price_vs_sma20_max},
                "macd_histogram_min": macd_histogram_min,
                "stock_trend": stock_trend,
            },
            "financial": {
                "pe": {"min": pe_min, "max": pe_max},
                "pb": {"min": pb_min, "max": pb_max},
                "roe": {"min": roe_min, "max": roe_max},
                "margins": {"net_min": net_margin_min, "gross_min": gross_margin_min},
                "growth": {"revenue_min": revenue_growth_min, "npat_min": npat_growth_min},
            },
        }
    }


# Routes with {symbol} path parameter must come AFTER static routes
@app.get("/api/stocks/{symbol}/history")
async def get_stock_history(
    symbol: str,
    days: int = Query(30, ge=1, le=365, description="Number of days of history"),
):
    """Get price history for a specific stock."""
    db = await get_database()
    
    history = await db.get_price_history(symbol, days)
    
    if not history:
        raise HTTPException(status_code=404, detail=f"No history for {symbol}")
    
    return {
        "symbol": symbol,
        "history": history,
        "count": len(history)
    }


@app.get("/api/stocks/realtime")
async def get_realtime_prices(
    group: str = Query("VN30", description="Stock group (VN30, HOSE, HNX, UPCOM)"),
    symbols: Optional[str] = Query(None, description="Comma-separated list of symbols to filter")
):
    """
    Get real-time price snapshot from SSI iBoard.
    Proxies requests to SSI to avoid database bottlenecks for live data.
    """
    collector = await get_ssi_collector()
    
    # Get snapshot for group
    data = await collector.get_market_snapshot(group)
    
    # Filter if symbols provided
    if symbols:
        symbol_list = [s.strip().upper() for s in symbols.split(',')]
        data = [s for s in data if s['symbol'] in symbol_list]
        
    return {"group": group, "stocks": data, "count": len(data)}


@app.get("/api/stocks/{symbol}")
async def get_stock(symbol: str):
    """Get details for a specific stock."""
    db = await get_database()
    
    stocks = await db.get_stocks(search=symbol, limit=1)
    
    if not stocks:
        raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")
    
    return stocks[0]


@app.get("/api/sectors")
async def get_sectors():
    """Get list of available sectors."""
    db = await get_database()
    sectors = await db.get_sectors()
    return {"sectors": sectors}


@app.get("/api/smart-board/sector/{sector_name}")
async def get_smart_board_sector(sector_name: str, limit: int = 20):
    """Get stocks for a specific sector for Smart Board."""
    db = await get_database()
    stocks = await db.get_stocks_by_sector(sector_name, limit)
    return {"sector": sector_name, "stocks": stocks}


@app.get("/api/smart-board/highlights")
async def get_smart_board_highlights():
    """Get highlight lists (Top Gainers, Top Volume)."""
    db = await get_database()
    
    # Get top gainers
    async with db.connection() as conn:
        cursor = await conn.execute("""
            SELECT s.symbol, s.company_name, sp.current_price, sp.price_change, sp.percent_change, sp.volume
            FROM stocks s
            JOIN stock_prices sp ON s.symbol = sp.symbol
            WHERE sp.percent_change > 0 AND sp.volume > 100000
            ORDER BY sp.percent_change DESC
            LIMIT 10
        """)
        gainers = [dict(row) for row in await cursor.fetchall()]
        
        # Get top volume
        cursor = await conn.execute("""
            SELECT s.symbol, s.company_name, sp.current_price, sp.price_change, sp.percent_change, sp.volume
            FROM stocks s
            JOIN stock_prices sp ON s.symbol = sp.symbol
            WHERE sp.volume > 0
            ORDER BY sp.volume DESC
            LIMIT 10
        """)
        active = [dict(row) for row in await cursor.fetchall()]
        
        # Get new highs (mock logic using price vs 52w if available, or just strong uptrend)
        # Using simple gainers for now as "Vượt đỉnh" needs history analysis
        
    return {
        "highlights": [
            {"id": "top-gainers", "name": "Tăng giá mạnh", "stocks": gainers},
            {"id": "top-volume", "name": "Dòng tiền mạnh", "stocks": active}
        ]
    }



@app.get("/api/smart-board/indices")
async def get_smart_board_indices():
    """Get latest market indices for Smart Board display."""
    db = await get_database()
    indices = await db.get_market_indices()
    
    # Default indices structure for fallback
    default_indices = [
        {"index_code": "VNINDEX", "value": 0, "change_value": 0, "change_percent": 0, "advances": 0, "declines": 0, "unchanged": 0},
        {"index_code": "VN30", "value": 0, "change_value": 0, "change_percent": 0, "advances": 0, "declines": 0, "unchanged": 0},
        {"index_code": "HNX", "value": 0, "change_value": 0, "change_percent": 0, "advances": 0, "declines": 0, "unchanged": 0},
        {"index_code": "UPCOM", "value": 0, "change_value": 0, "change_percent": 0, "advances": 0, "declines": 0, "unchanged": 0},
    ]
    
    from_database = False
    if indices:
        from_database = True
        # Update defaults with actual data from database
        # Create a map supporting both exact matches and *INDEX variants
        index_map = {idx.get("index_code"): idx for idx in indices if idx.get("index_code")}
        
        for i, default in enumerate(default_indices):
            code = default["index_code"]
            # Try exact match first, then try with INDEX suffix
            db_index = index_map.get(code) or index_map.get(f"{code}INDEX")
            
            if db_index:
                default_indices[i] = {
                    "index_code": code,  # Keep the display name (HNX, UPCOM)
                    "value": db_index.get("value", 0) or 0,
                    "change_value": db_index.get("change_value", 0) or 0,
                    "change_percent": db_index.get("change_percent", 0) or 0,
                    "advances": db_index.get("advances", 0) or 0,
                    "declines": db_index.get("declines", 0) or 0,
                    "unchanged": db_index.get("unchanged", 0) or 0,
                }
    
    return {
        "indices": default_indices,
        "from_database": from_database,
        "updated_at": datetime.now().isoformat()
    }


# ============================================
# Database Endpoints
# ============================================

@app.get("/api/database/status", response_model=DatabaseStatusResponse)
async def get_database_status():
    """Get database status and statistics."""
    db = await get_database()
    
    stats = await db.get_database_stats()
    freshness = await db.get_data_freshness()
    
    return DatabaseStatusResponse(
        status=freshness,
        stocks_count=stats.get('stocks_count', 0),
        stocks_with_prices=stats.get('stock_prices_count', 0),
        last_update=stats.get('last_price_update'),
        database_size_mb=stats.get('database_size_mb'),
        is_updating=False,  # Would track actual update state
    )


@app.post("/api/database/update")
async def trigger_update(
    background_tasks: BackgroundTasks,
    task_name: Optional[str] = Query(None, description="Specific task to run"),
    force: bool = Query(False, description="Force update even during market hours"),
):
    """Trigger a manual data update."""
    scheduler = await get_scheduler()
    
    if not force and not scheduler.can_run_update():
        return JSONResponse(
            status_code=409,
            content={
                "message": "Cannot run update during market hours",
                "market_hours": scheduler.is_market_hours(),
                "suggestion": "Wait until after 15:00 or set force=true"
            }
        )
    
    async def run_update():
        if task_name:
            await scheduler.run_task_by_name(task_name)
        else:
            # Run screener update (most useful for manual trigger)
            await scheduler.run_task_by_name("daily_screener")
    
    background_tasks.add_task(run_update)
    
    return {
        "message": "Update started",
        "task": task_name or "daily_screener",
        "status": "running"
    }


@app.get("/api/database/scheduler")
async def get_scheduler_status():
    """Get scheduler status and task information."""
    scheduler = await get_scheduler()
    return scheduler.get_status()


# ============================================
# Data Update Status Endpoints
# ============================================

@app.get("/api/data/update-status")
async def get_update_status():
    """Get comprehensive data update status across all data types."""
    from update_registry import get_update_registry
    
    db = await get_database()
    registry = await get_update_registry(db)
    
    return await registry.get_update_summary()


@app.get("/api/data/update-queue")
async def get_update_queue(
    limit: int = Query(50, ge=1, le=200, description="Maximum symbols to return")
):
    """Get prioritized queue of symbols needing updates."""
    from update_registry import get_update_registry
    
    db = await get_database()
    registry = await get_update_registry(db)
    
    queue = await registry.get_priority_update_queue(max_symbols=limit)
    return {"queue": queue, "count": len(queue)}


@app.post("/api/data/force-update/{symbol}")
async def force_update_symbol(
    symbol: str,
    background_tasks: BackgroundTasks,
    data_type: Optional[str] = Query(None, description="Specific data type to update")
):
    """Force update all data for a specific symbol."""
    from update_registry import get_update_registry, DataType
    
    collector = await get_collector()
    db = await get_database()
    registry = await get_update_registry(db)
    
    async def run_symbol_update():
        try:
            # Update price data
            if data_type is None or data_type == "price":
                history = await collector.collect_price_history(symbol)
                if history:
                    latest = history[-1]
                    await db.upsert_stock_prices([{
                        'symbol': symbol,
                        'current_price': latest['close_price'],
                        'open_price': latest['open_price'],
                        'high_price': latest['high_price'],
                        'low_price': latest['low_price'],
                        'close_price': latest['close_price'],
                        'volume': latest['volume'],
                    }])
                    await registry.mark_symbol_updated(symbol, DataType.PRICE, "success")
            
            # Update dividends
            if data_type is None or data_type == "dividends":
                dividends = await collector.collect_dividend_history(symbol)
                if dividends:
                    await db.upsert_dividend_history(dividends)
                    await registry.mark_symbol_updated(symbol, DataType.DIVIDENDS, "success")
            
            # Update financial data
            if data_type is None or data_type == "financials":
                financials = await collector.collect_financial_data(symbol)
                await registry.mark_symbol_updated(symbol, DataType.FINANCIALS, "success")
                
        except Exception as e:
            logger.error(f"Force update failed for {symbol}: {e}")
    
    background_tasks.add_task(run_symbol_update)
    
    return {
        "message": f"Update started for {symbol}",
        "symbol": symbol,
        "data_type": data_type or "all",
        "status": "running"
    }


@app.post("/api/data/clear-failed")
async def clear_failed_updates(
    symbol: Optional[str] = Query(None, description="Specific symbol to clear, or all if not specified")
):
    """Clear failed update status to allow retry."""
    from update_registry import get_update_registry
    
    db = await get_database()
    registry = await get_update_registry(db)
    
    await registry.clear_failed_status(symbol)
    
    return {
        "message": f"Cleared failed status for {'all symbols' if not symbol else symbol}",
        "symbol": symbol
    }


@app.get("/api/data/dividends/{symbol}")
async def get_dividends(
    symbol: str,
    limit: int = Query(10, ge=1, le=100, description="Number of records")
):
    """Get dividend history for a symbol."""
    db = await get_database()
    dividends = await db.get_dividend_history(symbol, limit)
    return {"symbol": symbol, "dividends": dividends, "count": len(dividends)}


@app.get("/api/data/ratings/{symbol}")
async def get_ratings(symbol: str):
    """Get company ratings for a symbol."""
    db = await get_database()
    ratings = await db.get_company_ratings(symbol)
    return {"symbol": symbol, "ratings": ratings}


@app.get("/api/data/indices")
async def get_indices(
    index_code: Optional[str] = Query(None, description="Specific index code")
):
    """Get market index values."""
    db = await get_database()
    indices = await db.get_market_indices(index_code)
    return {"indices": indices}


@app.get("/api/data/shareholders/{symbol}")
async def get_shareholders(
    symbol: str,
    refresh: bool = Query(False, description="Force refresh from API")
):
    """
    Get shareholders for a stock.
    Returns: Ban lãnh đạo, Tổ chức, Nước ngoài, Cổ đông lớn, Cá nhân
    """
    db = await get_database()
    
    # Check if we need to fetch fresh data
    shareholders = await db.get_shareholders(symbol.upper())
    
    if not shareholders or refresh:
        # Fetch from VnStock API
        collector = await get_collector()
        try:
            new_data = await collector.collect_shareholders(symbol.upper())
            if new_data:
                await db.upsert_shareholders(new_data)
                shareholders = await db.get_shareholders(symbol.upper())
        except Exception as e:
            logger.warning(f"Failed to refresh shareholders for {symbol}: {e}")
    
    return {
        "symbol": symbol.upper(),
        "shareholders": shareholders,
        "count": len(shareholders)
    }


@app.get("/api/data/officers/{symbol}")
async def get_officers(
    symbol: str,
    status: str = Query("working", description="Filter: working, resigned, all"),
    refresh: bool = Query(False, description="Force refresh from API")
):
    """
    Get company officers/management for a stock.
    Returns: Ban lãnh đạo with positions and ownership.
    """
    db = await get_database()
    
    officers = await db.get_officers(symbol.upper(), status)
    
    if not officers or refresh:
        collector = await get_collector()
        try:
            new_data = await collector.collect_officers(symbol.upper())
            if new_data:
                await db.upsert_officers(new_data)
                officers = await db.get_officers(symbol.upper(), status)
        except Exception as e:
            logger.warning(f"Failed to refresh officers for {symbol}: {e}")
    
    return {
        "symbol": symbol.upper(),
        "officers": officers,
        "count": len(officers),
        "filter": status
    }


@app.get("/api/data/profile/{symbol}")
async def get_company_profile(
    symbol: str,
    refresh: bool = Query(False, description="Force refresh from API")
):
    """
    Get company profile including sector, industry, and overview.
    """
    db = await get_database()
    
    # Get basic stock info
    stocks = await db.get_stocks(search=symbol.upper(), limit=1)
    profile = stocks[0] if stocks else None
    
    if not profile or refresh or not profile.get('sector'):
        # Fetch full profile from VnStock
        collector = await get_collector()
        try:
            details = await collector.collect_stock_details(symbol.upper())
            if details:
                # Update stock record with sector/industry
                await db.upsert_stocks([details])
                stocks = await db.get_stocks(search=symbol.upper(), limit=1)
                profile = stocks[0] if stocks else None
        except Exception as e:
            logger.warning(f"Failed to refresh profile for {symbol}: {e}")
    
    # Also get shareholders and dividends summary
    shareholders = await db.get_shareholders(symbol.upper())
    dividends = await db.get_dividend_history(symbol.upper(), limit=5)
    
    return {
        "symbol": symbol.upper(),
        "profile": profile,
        "shareholders_count": len(shareholders),
        "recent_dividends": len(dividends),
        "top_shareholders": shareholders[:5] if shareholders else []
    }


# ============================================
# Real-time Market Data (SSI iBoard)
# ============================================

@app.get("/api/realtime/snapshot/{group}")
async def get_realtime_snapshot(
    group: str = "HOSE"
):
    """
    Get real-time price snapshot for a market group.
    
    Groups: VN30, HOSE, HNX, UPCOM, VN100
    Returns: Real-time prices with bid/ask levels
    """
    from ssi_iboard_collector import get_ssi_collector
    
    valid_groups = ['VN30', 'HOSE', 'HNX', 'UPCOM', 'VN100']
    if group.upper() not in valid_groups:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid group. Valid: {valid_groups}"
        )
    
    collector = await get_ssi_collector()
    data = await collector.get_market_snapshot(group.upper())
    
    return {
        "group": group.upper(),
        "stocks": data,
        "count": len(data),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/realtime/all")
async def get_all_realtime():
    """
    Get real-time prices for all markets (HOSE, HNX, UPCOM).
    """
    from ssi_iboard_collector import get_ssi_collector
    
    collector = await get_ssi_collector()
    data = await collector.get_all_markets()
    
    total = sum(len(v) for v in data.values())
    
    return {
        "markets": data,
        "total_stocks": total,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/realtime/symbols")
async def get_ssi_symbols():
    """Get full list of SSI supported symbols."""
    from ssi_iboard_collector import get_ssi_collector
    
    collector = await get_ssi_collector()
    symbols = await collector.get_stock_info()
    
    return {
        "symbols": symbols,
        "count": len(symbols)
    }


# ============================================
# Financial Reports & Orderflow
# ============================================

@app.get("/api/data/bctc/{symbol}")
async def get_financial_reports(
    symbol: str,
    report_type: str = Query("income", description="income, balance, cashflow"),
    quarterly: bool = Query(True, description="Quarterly or yearly")
):
    """
    Get financial statement from CafeF.
    Returns parsed BCTC tables.
    """
    from cafef_scraper import get_cafef_scraper
    
    scraper = await get_cafef_scraper()
    df = await scraper.get_financial_statement(
        symbol.upper(),
        report_type,
        quarterly=quarterly
    )
    
    if df is None:
        return {"symbol": symbol.upper(), "data": None, "message": "No data found"}
    
    # Convert DataFrame to records
    records = df.to_dict('records')
    
    return {
        "symbol": symbol.upper(),
        "report_type": report_type,
        "quarterly": quarterly,
        "rows": len(records),
        "columns": list(df.columns),
        "data": records
    }


@app.get("/api/data/orderflow/{symbol}")
async def get_orderflow_history(
    symbol: str,
    days: int = Query(30, ge=1, le=365, description="Days of history")
):
    """
    Get daily orderflow history for a symbol.
    Includes foreign buy/sell, dư mua/dư bán per session.
    """
    db = await get_database()
    
    query = """
        SELECT * FROM daily_orderflow
        WHERE symbol = ?
        ORDER BY trade_date DESC
        LIMIT ?
    """
    
    async with db.connection() as conn:
        cursor = await conn.execute(query, (symbol.upper(), days))
        rows = await cursor.fetchall()
        data = [dict(row) for row in rows]
    
    return {
        "symbol": symbol.upper(),
        "history": data,
        "count": len(data)
    }


# ============================================
# AI Analysis Endpoints
# ============================================



class AIAnalysisRequestModel(BaseModel):
    """Request model for AI stock analysis."""
    api_key: str
    model: str = "gemini-2.0-flash-exp"
    custom_prompt: Optional[str] = None
    prompt_template: Optional[str] = None
    enable_grounding: bool = True


class AITestConnectionRequest(BaseModel):
    """Request model for testing AI connection."""
    api_key: str
    model: str = "gemini-2.0-flash-exp"


@app.post("/api/ai/analyze/{symbol}")
async def analyze_stock(symbol: str, request: AIAnalysisRequestModel):
    """
    Generate AI-powered investment analysis for a stock.
    
    Uses Google Gemini with optional Google Search grounding for up-to-date information.
    Returns a comprehensive 9-section analysis in Vietnamese.
    """
    from ai_service import AIAnalysisService, AIAnalysisRequest
    
    db = await get_database()
    service = AIAnalysisService(db)
    
    try:
        analysis_request = AIAnalysisRequest(
            symbol=symbol.upper(),
            api_key=request.api_key,
            model=request.model,
            custom_prompt=request.custom_prompt,
            prompt_template=request.prompt_template,
            enable_grounding=request.enable_grounding
        )
        
        result = await service.analyze(analysis_request)
        
        return {
            "success": True,
            "analysis": result.analysis,
            "metadata": {
                "symbol": result.symbol,
                "company_name": result.company_name,
                "model": result.model,
                "grounding_sources": result.grounding_sources,
                "generated_at": result.generated_at,
                "tokens_used": result.tokens_used
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"AI analysis failed for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"AI analysis failed: {str(e)}")


@app.post("/api/ai/test-connection")
async def test_ai_connection(request: AITestConnectionRequest):
    """Test AI API connection with provided credentials."""
    from ai_service import GeminiClient
    
    client = GeminiClient(api_key=request.api_key, model=request.model)
    
    try:
        is_valid = await client.test_connection()
        return {
            "success": is_valid,
            "model": request.model,
            "message": "Connection successful" if is_valid else "Connection failed - invalid response"
        }
    except Exception as e:
        return {
            "success": False,
            "model": request.model,
            "message": str(e)
        }


@app.get("/api/ai/models")
async def get_ai_models():
    """Get list of available AI models."""
    from ai_service import get_available_models
    
    models = get_available_models()
    return {
        "models": [
            {"id": model_id, "name": model_name}
            for model_id, model_name in models.items()
        ],
        "default": "gemini-2.0-flash-exp"
    }


@app.get("/api/ai/default-prompt")
async def get_default_prompt():
    """Get the default AI analysis prompt template."""
    from ai_service import ANALYSIS_PROMPT_TEMPLATE
    return {"template": ANALYSIS_PROMPT_TEMPLATE}


# ============================================
# Health & Monitoring Endpoints
# ============================================

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    db = await get_database()
    circuit_breaker = get_circuit_breaker()
    rate_limiter = get_rate_limiter()
    
    # Check database
    try:
        await db.get_stock_count()
        db_status = "healthy"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return HealthResponse(
        status="healthy" if db_status == "healthy" else "degraded",
        timestamp=datetime.now().isoformat(),
        database=db_status,
        circuit_breaker=circuit_breaker.state.value,
        rate_limiter=rate_limiter.get_stats(),
    )


@app.get("/api/health/collector")
async def get_collector_status():
    """Get data collector status and statistics."""
    collector = await get_collector()
    return collector.get_stats()


@app.get("/api/health/circuit-breaker")
async def get_circuit_breaker_status():
    """Get circuit breaker status."""
    circuit_breaker = get_circuit_breaker()
    return circuit_breaker.get_status()


@app.post("/api/health/circuit-breaker/reset")
async def reset_circuit_breaker():
    """Force reset the circuit breaker."""
    circuit_breaker = get_circuit_breaker()
    await circuit_breaker.force_close()
    return {"message": "Circuit breaker reset", "state": circuit_breaker.state.value}


# ============================================
# Root Endpoint
# ============================================

@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "VnStock Screener API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health",
    }


# ============================================
# Main Entry Point
# ============================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
        log_level=settings.LOG_LEVEL.lower(),
    )
