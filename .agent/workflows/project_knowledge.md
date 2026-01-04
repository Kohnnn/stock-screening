---
description: Comprehensive overview of the VnStock Screener project, its architecture, and operation.
---

# VnStock Screener - Project Knowledge Base

## 1. Project Overview
VnStock Screener is a full-stack web application designed for screening and analyzing Vietnamese stocks. It combines real-time data, detailed financial metrics, technical analysis, and AI-powered insights into a modern dashboard.

**Core Features:**
- **Smart Board:** Real-time market tracking (VN30, Banks, Gainers, etc.).
- **Screener:** Filter 1400+ stocks by 80+ metrics (P/E, ROE, Technicals).
- **Stock Comparison:** Side-by-side comparison of multiple tickers.
- **Data Browser:** Deep dive into individual stock data (Financials, Profile, Chart).
- **AI Analysis:** Integrated Gemini AI for generating analyzing reports.

## 2. Technology Stack

### Backend
- **Framework:** FastAPI (Python)
- **Database:** SQLite (with specialized schema for financial data)
- **Data Sources:**
  - `vnstock`: Primary library for market data (prices, profile, financials).
  - `ssi_iboard`: Real-time price snapshots.
  - `cafef`, `vietstock`: Supplemental financial details.
- **AI:** Google Gemini 2.0 Flash (via `ai_service.py`).
- **Key Modules:**
  - `collect_data.py`: Main data orchestration.
  - `calculate_metrics.py`: Computes derived metrics (RSI, signals).
  - `database.py`: Async database wrapper.

### Frontend
- **Framework:** React (Vite)
- **Language:** TypeScript
- **Styling:** Vanilla CSS + TailwindCSS (minimal usage).
- **Components:**
  - `SmartBoard.tsx`: The main dashboard view.
  - `StockScreener.tsx`: The filtering interface.
  - `AIAnalysis.tsx`: Interface for AI interaction.
  - `TradingViewChart.tsx` / `PriceChart.tsx`: Charting components.

### Infrastructure
- **Docker:** Fully containerized (Backend + Nginx serving Frontend).
- **Nginx:** Reverse proxy handling API requests (`/api`) and serving static assets.

## 3. Directory Structure
```
vnstock-screener/
├── backend/                # FastAPI Application
│   ├── data/               # SQLite database storage (vnstock_data.db)
│   ├── docs/               # Documentation for scrapers/APIs
│   ├── main.py             # App entry point
│   ├── ai_service.py       # Gemini integration
│   ├── collect_data.py     # Data collection job
│   └── ...
├── src/                    # React Application
│   ├── components/         # UI Components
│   ├── contexts/           # State management (Theme, Language)
│   ├── App.tsx             # Main routing/layout
│   └── ...
├── docker-compose.yml      # Service orchestration
└── nginx.conf              # Web server config
```

## 4. Key Workflows

### Data Update System
The system is designed to run automatically.
1. **Listings Update:** Fetches all available stock symbols.
2. **Screener Update:** Fetches real-time price & basic metrics for all stocks.
3. **Financials Update:** Fetches quarterly financial statements.
4. **Metrics Calculation:** Computes RSI, MACD, and other signals based on new data.

**Manual Trigger:**
You can trigger updates via the "Database" tab in the UI or via API:
`POST /api/database/update?task_name=daily_screener`

### AI Analysis Flow
1. User selects a stock in "AI Analysis" tab.
2. Frontend sends request to `/api/ai/analyze/{symbol}`.
3. Backend aggregates ALL known data for that stock (Prices, Financials, Ratings, Technicals).
4. Backend formats this data into a prompt for Gemini.
5. Gemini (with Google Search Grounding) helps generate a comprehensive report.
6. Result is streamed/returned to Frontend and rendered in Markdown.

## 5. Troubleshooting & Maintenance

- **Charts not showing:** If TradingView widget fails, the system falls back to `PriceChart.tsx` which uses local data.
- **Data missing:** Check `backend/logs/vnstock_updater.log`.
- **Database Locked:** Ensure only one write process is running. The `Database` class handles connection pooling.
- **AI Errors:** Check API Key in settings. Ensure you have quota for Gemini Flash.

## 6. Commands
- **Start Dev:** `npm run dev` (Frontend), `uvicorn main:app --reload` (Backend)
- **Docker Start:** `docker-compose up -d --build`
- **View Logs:** `docker-compose logs -f backend`
