"""
FastAPI Backend for VnStock Screener.

Provides REST API for the React frontend and manages data updates.
"""

import asyncio
from datetime import datetime
from typing import Optional, List
from contextlib import asynccontextmanager

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

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("🚀 VnStock Screener API starting...")
    
    # Initialize database
    db = await get_database()
    logger.info(f"✅ Database initialized: {settings.DATABASE_PATH}")
    
    # Check data freshness
    freshness = await db.get_data_freshness()
    logger.info(f"📊 Data freshness: {freshness}")
    
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
    # Basic filters
    exchange: Optional[str] = Query(None, description="Filter by exchange"),
    sector: Optional[str] = Query(None, description="Filter by sector"),
    # Financial filters
    pe_min: Optional[float] = Query(None, ge=0, description="Minimum P/E ratio"),
    pe_max: Optional[float] = Query(None, ge=0, description="Maximum P/E ratio"),
    pb_min: Optional[float] = Query(None, ge=0, description="Minimum P/B ratio"),
    pb_max: Optional[float] = Query(None, ge=0, description="Maximum P/B ratio"),
    roe_min: Optional[float] = Query(None, description="Minimum ROE (%)"),
    market_cap_min: Optional[float] = Query(None, ge=0, description="Minimum market cap"),
    # Technical filters
    rsi_min: Optional[float] = Query(None, ge=0, le=100, description="Minimum RSI (0-100)"),
    rsi_max: Optional[float] = Query(None, ge=0, le=100, description="Maximum RSI (0-100)"),
    trend: Optional[str] = Query(None, description="Stock trend filter"),
    adx_min: Optional[float] = Query(None, ge=0, description="Minimum ADX (trend strength)"),
    # Pagination
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
):
    """
    Advanced stock screener with technical indicators.
    
    Technical trend options: 'strong_uptrend', 'uptrend', 'sideways', 'downtrend', 'strong_downtrend'
    """
    db = await get_database()
    
    # Get stocks with metrics
    stocks = await db.get_stocks_with_metrics(
        rsi_min=rsi_min,
        rsi_max=rsi_max,
        trend=trend,
        adx_min=adx_min,
        limit=page_size * page,
    )
    
    # Apply additional filters
    filtered = []
    for stock in stocks:
        if exchange and stock.get('exchange') != exchange:
            continue
        if sector and stock.get('sector') != sector:
            continue
        
        pe = stock.get('pe_ratio')
        if pe_min is not None and (pe is None or pe < pe_min):
            continue
        if pe_max is not None and (pe is None or pe > pe_max):
            continue
        
        pb = stock.get('pb_ratio')
        if pb_min is not None and (pb is None or pb < pb_min):
            continue
        if pb_max is not None and (pb is None or pb > pb_max):
            continue
        
        roe = stock.get('roe')
        if roe_min is not None and (roe is None or roe < roe_min):
            continue
        
        market_cap = stock.get('market_cap')
        if market_cap_min is not None and (market_cap is None or market_cap < market_cap_min):
            continue
        
        filtered.append(stock)
    
    # Paginate
    start = (page - 1) * page_size
    end = start + page_size
    paginated = filtered[start:end]
    
    return {
        "stocks": paginated,
        "total": len(filtered),
        "page": page,
        "page_size": page_size,
        "filters_applied": {
            "rsi": {"min": rsi_min, "max": rsi_max},
            "trend": trend,
            "adx_min": adx_min,
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


@app.get("/api/stocks/{symbol}/metrics")
async def get_stock_metrics(symbol: str):
    """Get calculated technical metrics for a stock."""
    db = await get_database()
    metrics = await db.get_stock_metrics(symbol)
    
    if not metrics:
        raise HTTPException(status_code=404, detail=f"No metrics for {symbol}")
    
    return metrics


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


# ============================================
# AI Analysis Endpoints
# ============================================

class AIAnalysisRequestModel(BaseModel):
    """Request model for AI stock analysis."""
    api_key: str
    model: str = "gemini-2.0-flash-exp"
    custom_prompt: Optional[str] = None
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
