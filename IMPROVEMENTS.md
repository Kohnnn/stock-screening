# VnStock Screener - Improvement Roadmap

## ✅ Recently Completed

| Feature | Status |
|---------|--------|
| Technical Indicators (RSI, MACD, EMA, ADX) | ✅ Done |
| Advanced Screener API with filters | ✅ Done |
| Automated metrics calculation | ✅ Done |
| Update registry for data freshness | ✅ Done |
| Frontend technical indicator filters | ✅ Done |

---

## 🎯 High Priority (Next Sprint)

### 1. Dark Mode Toggle
- **Effort:** Low (2-4 hours)
- **Impact:** High user satisfaction
- CSS variables already support theming
- Add toggle in header, persist in localStorage

### 2. Export to Excel/CSV
- **Effort:** Low (4-6 hours)
- **Impact:** High utility
- Add download button in screener toolbar
- Use `xlsx` library for Excel, native for CSV

### 3. Screener Presets
- **Effort:** Medium (1 day)
- **Impact:** High retention
- Save filter combinations to localStorage/DB
- Pre-built presets: "Oversold Stocks", "High RSI Growth", "Value Picks"

### 4. Watchlist (Basic)
- **Effort:** Medium (1-2 days)
- **Impact:** Core feature
- Add/remove stocks to personal watchlist
- Persist in localStorage initially

---

## 🔧 Medium Priority

### 5. Interactive Price Charts
- Candlestick charts with zoom/pan
- Technical indicator overlays
- Time range selector (1M, 3M, 6M, 1Y)

### 6. Stock Comparison View
- Side-by-side metrics comparison
- Overlaid normalized price charts
- Relative strength visualization

### 7. Dividend Calendar
- Ex-dividend date tracking
- Dividend yield rankings
- Historical dividend trends

### 8. WebSocket Live Prices
- Real-time price updates during market hours
- Live VN30 index tracking
- Push notifications for alerts

---

## 🚀 Future Enhancements

### AI Features
- Natural language stock queries
- AI-generated analysis summaries
- Sentiment analysis from news

### Portfolio Tracking
- Holdings management
- P&L tracking
- Performance vs benchmark

### Mobile Optimization
- Responsive design improvements
- PWA support for offline access
- Touch-optimized interactions

---

## 🏗️ Technical Debt

- [ ] Add comprehensive error boundaries in React
- [ ] Implement proper loading skeletons
- [ ] Add unit tests for technical_indicators.py
- [ ] Create API documentation (Swagger/OpenAPI)
- [ ] Add database migration system (Alembic)
- [ ] Implement proper logging rotation

---

## Priority Matrix

| Priority | Feature | Effort | Impact |
|----------|---------|--------|--------|
| 🟢 | Dark Mode | Low | High |
| 🟢 | Export CSV/Excel | Low | High |
| 🟢 | Screener Presets | Medium | High |
| 🟡 | Watchlist | Medium | High |
| 🟡 | Price Charts | Medium | Medium |
| 🟡 | WebSocket Updates | High | Medium |
| 🔴 | AI Features | High | Medium |
| 🔴 | Portfolio | High | Medium |
