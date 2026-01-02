# VnStock Screener Backend

Python FastAPI backend for the VnStock Screener application. Handles data collection from vnstock library, SQLite storage, and REST API.

## Quick Start

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env

# Run server
python main.py
```

Server runs at http://localhost:8000

## API Documentation

Interactive docs available at `/docs` when running.

### Stock Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/stocks` | GET | List stocks with filters |
| `/api/stocks/{symbol}` | GET | Stock details |
| `/api/stocks/{symbol}/history` | GET | Price history |
| `/api/sectors` | GET | Available sectors |

**Query Parameters for `/api/stocks`:**
- `exchange` - HOSE, HNX, UPCOM
- `sector` - Filter by sector
- `pe_min/pe_max` - P/E ratio range
- `pb_min/pb_max` - P/B ratio range
- `roe_min` - Minimum ROE
- `market_cap_min` - Minimum market cap
- `search` - Search by symbol/name
- `page`, `page_size` - Pagination

### Data Management Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/database/status` | GET | Database stats |
| `/api/database/update` | POST | Trigger update |
| `/api/database/scheduler` | GET | Scheduler status |
| `/api/data/update-status` | GET | Update registry status |
| `/api/data/force-update/{symbol}` | POST | Force symbol update |
| `/api/data/dividends/{symbol}` | GET | Dividend history |
| `/api/data/ratings/{symbol}` | GET | Company ratings |
| `/api/data/indices` | GET | Market indices |

### Health Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/health/collector` | GET | Collector status |
| `/api/health/circuit-breaker` | GET | Circuit breaker status |

## Database Schema

SQLite database with tables for:
- `stocks` - Company information
- `stock_prices` - Daily price data
- `price_history` - Historical OHLCV
- `financial_data` - Financial statements
- `dividend_history` - Dividend records
- `update_registry` - Data freshness tracking

Schema file: `database_schema.sql`

## Configuration

See `.env.example` for all options. Key settings:

| Variable | Description |
|----------|-------------|
| `DATABASE_PATH` | SQLite file path |
| `VNSTOCK_RATE_LIMIT` | API rate limit |
| `DAILY_UPDATE_TIME` | Update schedule |
| `CIRCUIT_BREAKER_*` | Failure handling |

## Architecture

```
main.py              # FastAPI app & routes
├── config.py        # Environment settings
├── database.py      # SQLite operations
├── vnstock_collector.py  # Data collection
├── update_scheduler.py   # Scheduled jobs
├── update_registry.py    # Freshness tracking
├── rate_limiter.py       # Rate limiting
└── circuit_breaker.py    # Failure protection
```

## Data Collection

The backend uses intelligent data collection:

1. **Rate Limiting** - Token bucket algorithm, configurable requests/minute
2. **Circuit Breaker** - Stops requests after repeated failures
3. **Update Registry** - Tracks what data needs refreshing
4. **Scheduler** - Runs updates after market close (18:00)

## Running with Docker

From project root:

```bash
docker compose up backend
```

Or build standalone:

```bash
docker build -t vnstock-backend -f backend/Dockerfile backend/
docker run -p 8000:8000 -v ./data:/app/data vnstock-backend
```
