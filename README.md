# 📈 VnStock Screener

> A comprehensive Vietnamese stock market screening application with real-time data collection, advanced filtering, AI-powered analysis, and financial insights.

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](docker-compose.yml)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](backend/requirements.txt)
[![React](https://img.shields.io/badge/react-19.2-61dafb.svg)](package.json)

---

## ✨ Features

### 📊 **Advanced Stock Screening**
- Filter Vietnamese stocks by **exchange** (HOSE, HNX, UPCOM)
- Filter by **sector**, **P/E ratio**, **P/B ratio**, **ROE**, **market cap**
- Search by **symbol** or **company name**
- **84+ financial metrics** from vnstock Screener API
- Real-time **VN30 index tracking**
- **Filter presets** - save and load custom filter configurations

### 🌐 **Dual Data Sources**
- Primary: **cophieu68.vn** web scraper (polite rate limiting)
- Fallback: **vnstock** library
- Automatic data freshness checking
- Metrics: P/E, P/B, P/S, ROE, ROA, EPS, debt, assets, cash

### 📈 **Price Analysis & Charts**
- Interactive **historical price charts** (Chart.js)
- **OHLCV data** with customizable timeframes
- **Technical indicators** and price trends
- Daily price updates after market close

### 🤖 **AI-Powered Analysis** (Gemini Integration)
- **Stock analysis** with Google Gemini AI
- **Web search integration** for latest news and insights
- **Vietnamese language** analysis output
- Customizable **AI prompts** and model selection
- Structured 9-section analysis format

### 🔄 **Intelligent Data Management**
- **Automatic updates** with smart scheduling (18:00 daily)
- **Rate limiting** with token bucket algorithm
- **Circuit breaker** pattern for API failure protection
- **Update registry** tracking data freshness
- **VN30 priority** collection for key stocks

### 💾 **Comprehensive Database**
- **SQLite** with optimized schema
- Stock information, prices, financial statements
- Dividend history, ratings, market indices
- Screener data (84 metrics), shareholders, officers
- Intraday trading data

### 🎨 **Modern UI/UX**
- **Dark mode** support
- **Responsive design** for all devices
- **CSV export** for screener results
- **Watchlist** functionality
- **Preset filters** save/load

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (Nginx)                       │
│            React + TypeScript + Vite + Chart.js             │
│                         Port 80                             │
└────────────────────────┬────────────────────────────────────┘
                         │ /api/* proxy
┌────────────────────────▼────────────────────────────────────┐
│                   Backend (FastAPI)                         │
│     Python 3.11+ | vnstock 3.3.1 | Google Gemini AI        │
│                       Port 8000                             │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                   Database (SQLite)                         │
│              data/vnstock_data.db (Persistent)              │
└─────────────────────────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                   Data Sources                               │
│     cophieu68.vn (Primary) │ vnstock API (Fallback)         │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start with Docker

### Prerequisites
- **Docker** & **Docker Compose** installed
- **Git**
- (Optional) **Gemini API Key** for AI features

### 1️⃣ Clone Repository

```bash
git clone https://github.com/Kohnnn/stock-screening.git
cd stock-screening
```

### 2️⃣ Configure Environment

```bash
# Copy environment template
cp backend/.env.example backend/.env

# Edit backend/.env and configure:
# - GEMINI_API_KEY (optional, for AI features)
# - CORS_ORIGINS (add your production domain)
# - Other settings as needed
```

### 3️⃣ Build and Run

```bash
# Build and start all services
docker compose up -d

# View logs
docker compose logs -f

# Check status
docker compose ps
```

### 4️⃣ Access Application

- **Frontend**: http://localhost
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health

### 🛑 Stop Services

```bash
docker compose down

# To remove volumes (database will be deleted!)
docker compose down -v
```

---

## 💻 Development Setup

### Frontend Development

```bash
# Install dependencies (using npm or pnpm)
npm install
# or
pnpm install

# Start development server
npm run dev

# Build for production
npm run build
```

Frontend dev server runs at **http://localhost:5173**

### Backend Development

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Run development server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Or use the main script
python main.py
```

Backend runs at **http://localhost:8000**

---

## 🌐 Production Deployment

### Option 1: Docker Compose (Recommended)

1. **Set up your server** (Ubuntu/Debian recommended)
2. **Install Docker & Docker Compose**
3. **Clone repository** and configure `.env`
4. **Update `CORS_ORIGINS`** in `backend/.env` with your domain
5. **Run**: `docker compose up -d`
6. **Configure reverse proxy** (Nginx/Caddy) for HTTPS
7. **Set up SSL certificate** (Let's Encrypt)

### Option 2: Manual Deployment

**Backend:**
```bash
cd backend
pip install -r requirements.txt
gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

**Frontend:**
```bash
npm run build
# Serve the 'dist' folder with Nginx or any static file server
```

### Environment Variables for Production

Update `backend/.env`:
```env
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# CORS - Add your production domain
CORS_ORIGINS=https://yourdomain.com,http://localhost:5173

# Database
DATABASE_PATH=./data/vnstock_data.db

# Data Collection
VNSTOCK_RATE_LIMIT=6
DAILY_UPDATE_TIME=18:00

# AI Features (Optional)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.0-flash-exp

# Circuit Breaker
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_TIMEOUT=300
CIRCUIT_BREAKER_HALF_OPEN_ATTEMPTS=3
```

---

## 📚 API Documentation

### Stock Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/stocks` | GET | List stocks with advanced filters |
| `/api/stocks/{symbol}` | GET | Get detailed stock information |
| `/api/stocks/{symbol}/history` | GET | Get historical price data |
| `/api/stocks/{symbol}/financials` | GET | Get financial statements |
| `/api/sectors` | GET | List available sectors |
| `/api/exchanges` | GET | List exchanges (HOSE, HNX, UPCOM) |

### Data Management Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/database/status` | GET | Database statistics and health |
| `/api/database/update` | POST | Trigger manual data update |
| `/api/database/scheduler` | GET | Scheduler status |
| `/api/data/update-status` | GET | Update registry status |
| `/api/data/force-update/{symbol}` | POST | Force update specific symbol |
| `/api/data/dividends/{symbol}` | GET | Dividend history |
| `/api/data/ratings/{symbol}` | GET | Company ratings |
| `/api/data/indices` | GET | Market indices (VN30, VN100, etc.) |

### AI Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ai/analyze/{symbol}` | POST | AI-powered stock analysis |
| `/api/ai/test-connection` | POST | Test Gemini API connection |

### Health Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Overall health check |
| `/api/health/collector` | GET | Data collector status |
| `/api/health/circuit-breaker` | GET | Circuit breaker status |

**Full interactive API documentation**: http://localhost:8000/docs

---

## 🗂️ Project Structure

```
vnstock-screener/
├── 📁 src/                          # React Frontend
│   ├── 📁 components/               # Reusable UI components
│   │   ├── AISettingsPanel.tsx     # AI configuration
│   │   ├── StockCard.tsx           # Stock display card
│   │   ├── PriceChart.tsx          # Chart.js integration
│   │   └── ...
│   ├── 📁 pages/                    # Page components
│   │   ├── HomePage.tsx            # Main screener page
│   │   ├── StockDetailPage.tsx     # Stock details
│   │   └── ...
│   ├── 📁 hooks/                    # Custom React hooks
│   ├── 📁 types/                    # TypeScript definitions
│   └── App.tsx                     # Main application
│
├── 📁 backend/                      # Python Backend
│   ├── main.py                     # FastAPI application
│   ├── config.py                   # Configuration management
│   ├── database.py                 # Database operations
│   ├── cophieu68_collector.py      # 🆕 Primary data source (polite scraper)
│   ├── vnstock_collector.py        # Fallback data collection
│   ├── build_initial_database.py   # 🆕 Initial database builder
│   ├── ai_service.py               # Gemini AI integration
│   ├── update_scheduler.py         # Automated updates
│   ├── update_registry.py          # Data freshness tracking
│   ├── rate_limiter.py             # API rate limiting
│   ├── circuit_breaker.py          # Failure protection
│   ├── technical_indicators.py     # Technical analysis
│   ├── database_schema.sql         # Database schema
│   ├── requirements.txt            # Python dependencies
│   ├── Dockerfile                  # Backend container
│   └── 📁 docs/                     # API documentation
│
├── docker-compose.yml              # Docker orchestration
├── Dockerfile                      # Frontend container
├── nginx.conf                      # Nginx configuration
├── package.json                    # Node.js dependencies
├── tsconfig.json                   # TypeScript config
├── vite.config.ts                  # Vite configuration
└── README.md                       # This file
```

---

## ⚙️ Configuration

### Backend Configuration (`backend/.env`)

See `backend/.env.example` for all available options.

**Key Settings:**

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_PATH` | `./data/vnstock_data.db` | SQLite database file path |
| `API_HOST` | `0.0.0.0` | API server host |
| `API_PORT` | `8000` | API server port |
| `VNSTOCK_RATE_LIMIT` | `6` | Max requests/minute to vnstock API |
| `DAILY_UPDATE_TIME` | `18:00` | Daily update schedule (HH:MM) |
| `CORS_ORIGINS` | `http://localhost:5173` | Allowed CORS origins (comma-separated) |
| `GEMINI_API_KEY` | _(empty)_ | Google Gemini API key for AI features |
| `GEMINI_MODEL` | `gemini-2.0-flash-exp` | Gemini model to use |
| `CIRCUIT_BREAKER_FAILURE_THRESHOLD` | `5` | Failures before circuit opens |
| `CIRCUIT_BREAKER_TIMEOUT` | `300` | Circuit breaker timeout (seconds) |

---

## 🔧 Troubleshooting

### Docker Issues

**Problem**: `Cannot connect to Docker daemon`
```bash
# Start Docker service
sudo systemctl start docker  # Linux
# Or start Docker Desktop on Windows/Mac
```

**Problem**: Port already in use
```bash
# Change ports in docker-compose.yml
ports:
  - "8080:80"      # Frontend
  - "8001:8000"    # Backend
```

### Database Issues

**Problem**: Database locked or corrupted
```bash
# Stop services
docker compose down

# Remove database (WARNING: deletes all data)
rm backend/data/vnstock_data.db

# Restart services (will create fresh database)
docker compose up -d
```

### Data Collection Issues

**Problem**: No data being collected
```bash
# Check circuit breaker status
curl http://localhost:8000/api/health/circuit-breaker

# Force manual update
curl -X POST http://localhost:8000/api/database/update

# Check logs
docker compose logs backend
```

### AI Features Not Working

**Problem**: AI analysis fails
- Ensure `GEMINI_API_KEY` is set in `backend/.env`
- Check API key is valid at [Google AI Studio](https://aistudio.google.com/apikey)
- Verify model name is correct (e.g., `gemini-2.0-flash-exp`)
- Test connection: http://localhost:8000/docs → `/api/ai/test-connection`

---

## 📖 Additional Documentation

- **Backend API**: See `backend/README.md`
- **VnStock API**: See `backend/docs/vnstock_api_documentation.md`
- **Database Schema**: See `backend/database_schema.sql`
- **Improvements**: See `IMPROVEMENTS.md`

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **[cophieu68.vn](https://www.cophieu68.vn/)** - Vietnamese stock market data
- **[vnstock](https://github.com/thinh-vu/vnstock)** - Vietnamese stock data library
- **[FastAPI](https://fastapi.tiangolo.com/)** - Modern Python web framework
- **[React](https://react.dev/)** - UI library
- **[Google Gemini](https://ai.google.dev/)** - AI analysis capabilities

---

## 📧 Contact

For questions or support, please open an issue on GitHub.

---

**Made with ❤️ for Vietnamese stock market enthusiasts**
