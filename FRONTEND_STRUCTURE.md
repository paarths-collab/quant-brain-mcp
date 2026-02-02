# Boomerang - Complete Project Structure

## 📁 Full Directory Structure

```
Boomerang/
│
├── frontend/                          # Frontend Application
│   ├── index.html                    # Landing page with subscriptions
│   ├── dashboard.html                # Market overview dashboard
│   ├── technical.html                # Technical analysis page
│   ├── backtest.html                 # Backtesting interface
│   ├── research.html                 # AI research agent
│   │
│   ├── css/                          # Stylesheets
│   │   ├── style.css                 # Base styles & theme variables
│   │   ├── landing.css               # Landing page styles
│   │   ├── dashboard.css             # Dashboard styles
│   │   ├── technical.css             # Technical analysis styles
│   │   ├── backtest.css              # Backtesting styles
│   │   └── research.css              # Research agent styles
│   │
│   ├── js/                           # JavaScript files
│   │   ├── config.js                 # API configuration
│   │   ├── theme.js                  # Theme toggle functionality
│   │   ├── api.js                    # API helper functions
│   │   ├── charts.js                 # D3.js chart utilities
│   │   ├── landing.js                # Landing page scripts
│   │   ├── dashboard.js              # Dashboard logic
│   │   ├── technical.js              # Technical analysis logic
│   │   ├── backtest.js               # Backtesting logic
│   │   └── research.js               # Research agent logic
│   │
│   └── README.md                     # Frontend documentation
│
├── backend/                          # Backend API
│   ├── main.py                       # FastAPI application
│   ├── config.py                     # Configuration settings
│   ├── requirements.txt              # Python dependencies
│   │
│   ├── routes/                       # API Routes
│   │   ├── market.py                 # Market data endpoints
│   │   ├── fundamentals.py           # Fundamentals endpoints
│   │   ├── macro.py                  # Macro data endpoints
│   │   ├── eia_routes.py             # Energy data endpoints
│   │   ├── backtest.py               # Backtesting endpoints
│   │   ├── research.py               # Research agent endpoints
│   │   ├── peers.py                  # Peer comparison
│   │   ├── sectors.py                # Sector analysis
│   │   ├── social.py                 # Social sentiment
│   │   ├── insights_routes.py        # Market insights
│   │   ├── reports_routes.py         # Report generation
│   │   └── network.py                # Network analysis
│   │
│   ├── services/                     # Business Logic
│   │   ├── market_data_service.py    # Market data processing
│   │   ├── fundamentals_service.py   # Fundamentals analysis
│   │   ├── macro_service.py          # Macro economics
│   │   ├── eia_service.py            # Energy data
│   │   ├── backtest_service.py       # Backtesting engine
│   │   ├── research_service.py       # AI research
│   │   ├── peers_service.py          # Peer analysis
│   │   ├── sector_service.py         # Sector analysis
│   │   ├── social_service.py         # Social sentiment
│   │   └── ...
│   │
│   ├── agents/                       # AI Agents
│   │   ├── orchestrator.py           # Main orchestrator
│   │   ├── analyst_agent.py          # Stock analyst
│   │   ├── macro_agent.py            # Macro analyst
│   │   ├── risk_agent.py             # Risk assessment
│   │   ├── sector_agent.py           # Sector analysis
│   │   ├── yfinance_agent.py         # Yahoo Finance data
│   │   ├── web_research.py           # Web scraping
│   │   └── ...
│   │
│   ├── long_term/                    # Long-term Strategies
│   │   ├── dca.py                    # Dollar-cost averaging
│   │   ├── value.py                  # Value investing
│   │   ├── growth.py                 # Growth investing
│   │   ├── dividend.py               # Dividend investing
│   │   └── index_etf.py              # Index/ETF strategies
│   │
│   └── data/                         # Data Files
│       ├── nifty500.csv              # Indian stocks
│       └── us_stocks.csv             # US stocks
│
├── DOCUMENTATION.md                  # Project documentation
├── PROJECT_ANALYSIS.md               # Analysis & architecture
└── README.md                         # Main readme
```

## 🎯 Page Flow

```
┌─────────────────┐
│  Landing Page   │  ← Start here (index.html)
│  (Subscriptions)│
└────────┬────────┘
         │
         ↓
    [Select Plan]
         │
         ↓
┌─────────────────┐
│   Dashboard     │  ← Market overview
│                 │
└────────┬────────┘
         │
         ├──→ Technical Analysis  (Charting & indicators)
         │
         ├──→ Backtesting        (Strategy testing)
         │
         ├──→ Research Agent     (AI analysis)
         │
         └──→ Long Term          (Coming soon)
```

## 🔌 API Endpoints Mapping

### Frontend → Backend Connection

| Page | API Endpoints Used | Purpose |
|------|-------------------|---------|
| **Dashboard** | `/api/market/overview` | Market indices |
| | `/api/macro/prices` | Bonds, Oil, Gold |
| | `/api/eia/reserves/oil` | Oil reserves |
| | `/api/eia/petroleum/summary` | Petroleum data |
| **Technical** | `/api/market/candles/{symbol}` | OHLCV data |
| | `/api/market/indicators/{symbol}` | Technical indicators |
| | `/api/fundamentals/summary/{symbol}` | Company fundamentals |
| **Backtest** | `/api/backtest/run` | Run strategy backtest |
| **Research** | `/api/research/analyze` | AI stock analysis |
| | `/api/peers/{symbol}` | Peer comparison |
| | `/api/social/sentiment/{symbol}` | Sentiment analysis |

## 🎨 Color Scheme

### Dark Theme (Default)
```
Background:     #0a0e17 (Primary)
                #121825 (Secondary)
                #1a2332 (Tertiary)

Accent:         #00ff88 (Green - Primary)
                #00cc6f (Green - Secondary)

Text:           #e8eaed (Primary)
                #9aa0a6 (Secondary)
                #5f6368 (Tertiary)

Status:
  Success:      #00ff88
  Danger:       #ff4444
  Warning:      #ffaa00
  Info:         #00aaff
```

### Light Theme
```
Background:     #ffffff (Primary)
                #f8f9fa (Secondary)

Text:           #212529 (Primary)
                #495057 (Secondary)

[Same accent colors as dark theme]
```

## 🚀 Quick Start Guide

### 1. Backend Setup

```bash
# Navigate to backend
cd backend

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export FMP_API_KEY="your_key"
export EIA_API_KEY="your_key"

# Run server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend Setup

```bash
# Navigate to frontend
cd frontend

# Option 1: Python SimpleHTTPServer
python -m http.server 8080

# Option 2: Node http-server
npx http-server -p 8080

# Option 3: Open directly in browser
# Open index.html in your browser
```

### 3. Configure Connection

Edit `frontend/js/config.js`:
```javascript
const API_BASE_URL = 'http://localhost:8000';
```

### 4. Test Connection

1. Open `http://localhost:8080/index.html`
2. Navigate to Dashboard
3. Check if market data loads
4. Try different features

## 📊 Data Flow

```
User Action (Frontend)
    ↓
JavaScript Event Handler
    ↓
API Helper Function (api.js)
    ↓
Fetch Request
    ↓
Backend FastAPI Route
    ↓
Service Layer (Processing)
    ↓
External APIs / Database
    ↓
Response Processing
    ↓
JSON Response
    ↓
Frontend Processing
    ↓
D3.js Chart Rendering
    ↓
Display to User
```

## 🔧 Configuration Files

### Frontend Config (`js/config.js`)
- API base URL
- Endpoint definitions
- Timeout settings

### Backend Config (`config.py`)
- API keys
- Database connections
- Service configurations

## 🎯 Feature Status

| Feature | Status | Page |
|---------|--------|------|
| Landing Page | ✅ Complete | index.html |
| Dashboard | ✅ Complete | dashboard.html |
| Market Indices | ✅ Complete | dashboard.html |
| Macro Assets | ✅ Complete | dashboard.html |
| Technical Analysis | ✅ Complete | technical.html |
| Candlestick Charts | ✅ Complete | technical.html |
| Indicators (RSI, MACD) | ✅ Complete | technical.html |
| Backtesting | ✅ Complete | backtest.html |
| Strategy Selection | ✅ Complete | backtest.html |
| Performance Metrics | ✅ Complete | backtest.html |
| Research Agent | ✅ Complete | research.html |
| AI Analysis | ✅ Complete | research.html |
| Peer Comparison | ✅ Complete | research.html |
| Theme Toggle | ✅ Complete | All pages |
| Long Term Investment | 🔜 Coming Soon | - |

## 📱 Responsive Design

### Breakpoints
- **Desktop**: > 1024px (Full sidebar, multi-column grids)
- **Tablet**: 768px - 1024px (Collapsible sidebar, 2-column grids)
- **Mobile**: < 768px (Hidden sidebar, single column)

### Mobile Optimizations
- Touch-friendly buttons (44px min)
- Swipeable charts
- Collapsible sections
- Bottom navigation (optional)

## 🔒 Security Checklist

- [ ] HTTPS in production
- [ ] CORS properly configured
- [ ] API key management
- [ ] Input sanitization
- [ ] Rate limiting
- [ ] Authentication (if needed)
- [ ] Data encryption

## 📈 Performance Tips

1. **Lazy Load Charts** - Load only visible charts
2. **Debounce API Calls** - Prevent excessive requests
3. **Cache Static Data** - Use localStorage wisely
4. **Optimize D3.js** - Reuse SVG elements
5. **Minify Assets** - Compress CSS/JS in production

## 🐛 Common Issues

### Issue: Charts not rendering
**Solution**: Check D3.js CDN, verify data format

### Issue: API errors
**Solution**: Check CORS, verify backend is running

### Issue: Theme not saving
**Solution**: Check localStorage permissions

### Issue: Slow performance
**Solution**: Limit data points, optimize chart rendering

## 📞 Support Resources

- Frontend README: `frontend/README.md`
- Backend docs: `backend/README.md`
- API documentation: `/docs` (when backend running)
- Project analysis: `PROJECT_ANALYSIS.md`

---

**Next Steps:**
1. Start backend server
2. Open frontend in browser
3. Test all features
4. Customize theme colors
5. Add authentication (optional)
6. Deploy to production

Happy Trading! 🚀📊
