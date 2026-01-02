# VnStock Screener

A comprehensive Vietnamese stock market screening application with real-time data collection, advanced filtering, and financial analysis.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)

## Features

- 📊 **Stock Screening** - Filter Vietnamese stocks by exchange, sector, P/E, P/B, ROE, market cap
- 📈 **Price History** - View historical price charts and trends
- 🔄 **Auto Updates** - Intelligent data collection with rate limiting and circuit breaker
- 🏦 **Financial Data** - Access financial statements, ratios, and dividends
- 🎯 **VN30 Focus** - Prioritized tracking of VN30 index stocks

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend                            │
│                  React + TypeScript + Vite                  │
│                        (Port 80)                            │
└─────────────────────────┬───────────────────────────────────┘
                          │ /api proxy
┌─────────────────────────▼───────────────────────────────────┐
│                         Backend                             │
│               Python FastAPI + vnstock                      │
│                      (Port 8000)                            │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                         Database                            │
│                         SQLite                              │
│                   (data/vnstock_data.db)                    │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start with Docker

### Prerequisites
- Docker & Docker Compose installed
- Git

### 1. Clone and Configure

```bash
git clone <your-repo-url>
cd vnstock-screener

# Copy environment template
cp backend/.env.example backend/.env
```

### 2. Build and Run

```bash
# Build and start all services
docker compose up -d

# View logs
docker compose logs -f
```

### 3. Access the Application

- **Frontend**: http://localhost
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health

### Stopping

```bash
docker compose down
```

## Development Setup

### Frontend (React)

```bash
# Install dependencies
npm install

# Start dev server
npm run dev
```

Frontend runs at http://localhost:5173

### Backend (Python)

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Run API server
python main.py
```

Backend runs at http://localhost:8000

## Environment Configuration

Key settings in `backend/.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_PATH` | `./data/vnstock_data.db` | SQLite database location |
| `API_HOST` | `0.0.0.0` | API server host |
| `API_PORT` | `8000` | API server port |
| `VNSTOCK_RATE_LIMIT` | `6` | Requests per minute to vnstock |
| `DAILY_UPDATE_TIME` | `18:00` | When to run daily data updates |
| `CORS_ORIGINS` | `http://localhost:5173,...` | Allowed CORS origins |

See `backend/.env.example` for all configuration options.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/stocks` | GET | List stocks with filters |
| `/api/stocks/{symbol}` | GET | Get stock details |
| `/api/stocks/{symbol}/history` | GET | Get price history |
| `/api/sectors` | GET | List available sectors |
| `/api/database/status` | GET | Database statistics |
| `/api/database/update` | POST | Trigger manual update |
| `/api/health` | GET | Health check |

Full API documentation available at `/docs` when running.

## Data Sources

- **vnstock** - Vietnamese stock data library (TCBS source)
- Supports HOSE, HNX, UPCOM exchanges

## Project Structure

```
vnstock-screener/
├── src/                  # React frontend
│   ├── components/       # UI components
│   ├── pages/            # Page components
│   └── App.tsx           # Main app
├── backend/              # Python backend
│   ├── main.py           # FastAPI app
│   ├── database.py       # SQLite operations
│   ├── vnstock_collector.py  # Data collection
│   ├── update_scheduler.py   # Scheduled updates
│   └── requirements.txt  # Python dependencies
├── docker-compose.yml    # Docker orchestration
├── Dockerfile            # Frontend container
└── nginx.conf            # Nginx configuration
```

## License

MIT License - See LICENSE file for details.
