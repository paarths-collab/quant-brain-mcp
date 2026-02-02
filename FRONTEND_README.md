# 🚀 Boomerang - Premium Financial Analytics Platform

A full-stack financial analytics platform with AI-powered research, technical analysis, and backtesting capabilities. Built with a premium black-themed UI with green accents.

![Status](https://img.shields.io/badge/status-active-success.svg)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)
![D3.js](https://img.shields.io/badge/D3.js-v7-orange.svg)

## ✨ Features

### 📊 Dashboard
- **Real-time Market Data** - Live indices, stocks, and commodities
- **Macro Assets Tracking** - Bonds, Oil, Gold, and more
- **Energy Market Analysis** - Oil reserves and petroleum data
- **Interactive Visualizations** - D3.js powered charts

### 📈 Technical Analysis
- **Advanced Charting** - Interactive candlestick charts
- **20+ Technical Indicators**
  - Moving Averages (SMA, EMA)
  - Bollinger Bands
  - RSI, MACD, Stochastic
  - Volume Analysis
- **Real-time Price Updates**
- **Fundamental Metrics**
- **Customizable Timeframes**

### 🎯 Backtesting Engine
- **Multiple Strategies**
  - EMA Crossover
  - RSI Mean Reversion
  - Bollinger Breakout
  - MACD Divergence
- **Performance Metrics**
  - Total Return, Win Rate
  - Sharpe Ratio, Sortino Ratio
  - Max Drawdown, Profit Factor
- **Visual Analytics**
  - Equity Curves
  - Drawdown Charts
  - Monthly Returns Heatmap
  - Trade History

### 🤖 AI Research Agent
- **Comprehensive Analysis**
  - Fundamental Analysis
  - Technical Analysis
  - Market Sentiment
  - Peer Comparison
- **AI-Powered Insights**
- **Exportable Reports**
- **Watchlist Management**

### 💎 Long-term Investment (Coming Soon)
- Dollar-Cost Averaging
- Value Investing
- Dividend Growth
- Index/ETF Strategies

## 🎨 Design Features

- ✅ **Premium Black Theme** with customizable green accents
- ✅ **Light/Dark Mode Toggle** for user preference
- ✅ **Fully Responsive** - Mobile, Tablet, Desktop optimized
- ✅ **Smooth Animations** - Professional transitions and effects
- ✅ **Interactive Charts** - D3.js powered visualizations
- ✅ **Modern UI Components** - Cards, gradients, glassmorphism

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Modern web browser
- API Keys:
  - Financial Modeling Prep (FMP)
  - Energy Information Administration (EIA)

### Installation

#### Option 1: Automated Start (Recommended)

**Windows:**
```bash
# Simply double-click or run:
start.bat
```

**Linux/Mac:**
```bash
chmod +x start.sh
./start.sh
```

This will:
1. Create virtual environment
2. Install dependencies
3. Start backend server (port 8000)
4. Start frontend server (port 8080)
5. Open browser automatically

#### Option 2: Manual Start

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set environment variables
export FMP_API_KEY="your_fmp_key"
export EIA_API_KEY="your_eia_key"

# Start server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend:**
```bash
cd frontend
python -m http.server 8080
# Or use: npx http-server -p 8080
```

### Access the Application

- 🌐 **Frontend**: http://localhost:8080
- 📡 **Backend API**: http://localhost:8000
- 📚 **API Documentation**: http://localhost:8000/docs

## 📁 Project Structure

```
Boomerang/
├── frontend/              # Frontend application
│   ├── *.html            # HTML pages
│   ├── css/              # Stylesheets
│   └── js/               # JavaScript files
│
├── backend/              # Backend API
│   ├── main.py           # FastAPI app
│   ├── routes/           # API endpoints
│   ├── services/         # Business logic
│   ├── agents/           # AI agents
│   └── long_term/        # Investment strategies
│
├── start.bat             # Windows startup script
├── start.sh              # Linux/Mac startup script
└── README.md             # This file
```

See [FRONTEND_STRUCTURE.md](FRONTEND_STRUCTURE.md) for detailed structure.

## 🔌 API Endpoints

### Market Data
- `GET /api/market/overview` - Market indices overview
- `GET /api/market/candles/{symbol}` - OHLCV candlestick data
- `GET /api/market/indicators/{symbol}` - Technical indicators

### Fundamentals
- `GET /api/fundamentals/summary/{symbol}` - Company fundamentals

### Macro Economics
- `GET /api/macro/prices` - Macro asset prices
- `GET /api/eia/reserves/oil` - Oil reserves data
- `GET /api/eia/petroleum/summary` - Petroleum summary

### Analysis
- `POST /api/backtest/run` - Run strategy backtest
- `POST /api/research/analyze` - AI stock analysis

See full API documentation at http://localhost:8000/docs

## 🎯 Usage Guide

### 1. Landing Page
- Select your subscription plan (Free, Pro, Enterprise)
- Review features and pricing
- Start your journey

### 2. Dashboard
- View real-time market indices
- Track macro assets (Gold, Oil, Bonds)
- Monitor energy market data
- Quick market overview

### 3. Technical Analysis
1. Enter stock symbol (e.g., AAPL, TSLA)
2. Select timeframe and interval
3. Enable desired indicators
4. Analyze charts and metrics
5. View fundamental data

### 4. Backtesting
1. Choose stock symbol
2. Select time period
3. Pick trading strategy
4. Configure parameters
5. Run backtest
6. Analyze results and metrics

### 5. Research Agent
1. Enter stock symbol
2. Wait for AI analysis
3. Review comprehensive report
4. Check fundamental, technical, sentiment tabs
5. Export report or add to watchlist

## 🎨 Theme Customization

### Color Variables

Edit `frontend/css/style.css`:

```css
:root {
    /* Primary Colors */
    --bg-primary: #0a0e17;
    --accent-primary: #00ff88;
    
    /* Customize to your preference */
    --accent-primary: #00aaff;  /* Blue accent */
    --accent-primary: #ff6b6b;  /* Red accent */
    --accent-primary: #9b59b6;  /* Purple accent */
}
```

### Toggle Theme
Click the sun/moon icon in the sidebar to switch between dark and light themes.

## 🛠️ Development

### Adding New Features

1. **Frontend**: Create HTML, CSS, and JS files
2. **Backend**: Add routes and services
3. **Integration**: Update API configuration
4. **Testing**: Test all functionality

### Tech Stack

**Frontend:**
- HTML5, CSS3, JavaScript (ES6+)
- D3.js v7 for charts
- Responsive design
- No frameworks (vanilla JS)

**Backend:**
- FastAPI (Python web framework)
- Pandas (Data processing)
- yfinance (Market data)
- Various APIs (FMP, EIA)

## 📊 Chart Features

All charts powered by D3.js:

- **Candlestick Charts** - OHLCV visualization
- **Line Charts** - Trends with gradients
- **Bar Charts** - Volume and histograms
- **Heatmaps** - Monthly returns
- **Area Charts** - Equity curves

Interactive features:
- Hover tooltips
- Zoom and pan
- Crosshair cursor
- Responsive scaling

## 🔒 Security

- CORS properly configured
- API key management via environment variables
- Input sanitization
- HTTPS recommended for production
- No sensitive data in localStorage

## 📱 Responsive Design

Optimized for all devices:
- **Desktop** (> 1024px): Full sidebar, multi-column layout
- **Tablet** (768-1024px): Collapsible sidebar, 2-column layout
- **Mobile** (< 768px): Hidden sidebar, single column

## 🐛 Troubleshooting

### Charts Not Displaying
- Check browser console for errors
- Verify D3.js CDN is loaded
- Ensure backend is running

### API Connection Errors
- Verify backend is running on port 8000
- Check CORS configuration
- Review API endpoint URLs in `js/config.js`

### Theme Not Persisting
- Check browser localStorage is enabled
- Clear cache and try again

### Backend Errors
- Verify API keys are set
- Check Python dependencies installed
- Review backend logs

## 📈 Performance

Optimizations implemented:
- Lazy loading for charts
- Debounced API calls
- Efficient D3.js rendering
- Minimal dependencies
- CSS animations over JS

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make your changes
4. Test thoroughly
5. Submit pull request

## 📄 License

This project is part of the Boomerang financial analytics platform.

## 📞 Support

- Documentation: See `FRONTEND_STRUCTURE.md`
- API Docs: http://localhost:8000/docs
- Issues: Check GitHub issues

## 🎯 Roadmap

- [x] Landing page with subscriptions
- [x] Market dashboard
- [x] Technical analysis with charts
- [x] Backtesting engine
- [x] AI research agent
- [x] Theme toggle (dark/light)
- [ ] Long-term investment strategies
- [ ] User authentication
- [ ] Portfolio tracking
- [ ] Alerts and notifications
- [ ] Mobile app
- [ ] Social features

## 🙏 Acknowledgments

- D3.js for amazing visualizations
- FastAPI for the backend framework
- Financial data providers (FMP, EIA)
- Open source community

---

**Built with ❤️ for serious investors**

🌟 Star this repo if you find it useful!

📧 Contact: [Your contact info]

🌐 Website: [Your website]

---

## Quick Links

- 📖 [Frontend Documentation](frontend/README.md)
- 🏗️ [Project Structure](FRONTEND_STRUCTURE.md)
- 📊 [API Documentation](http://localhost:8000/docs)
- 🎨 [Design System](frontend/css/style.css)

---

**Happy Trading! 🚀📊💰**
