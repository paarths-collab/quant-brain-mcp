# Database Setup with Docker

This guide explains how to set up the PostgreSQL database for storing FRED API data.
It also covers the Sector Intelligence cache tables used for sector-level news + LLM snapshots.

## Quick Start

### 1. Start PostgreSQL with Docker

```bash
cd backend
docker-compose up -d
```

This will start:
- **PostgreSQL** on port `5432`
- **pgAdmin** (optional) on port `5050` for database management UI

### 2. Verify Database is Running

```bash
docker-compose ps
```

You should see `boomerang-db` with status `Up (healthy)`.

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Environment Variables

Copy `.env.example` to `.env` and add your FRED API key:

```bash
cp .env.example .env
```

Edit `.env`:
```env
DATABASE_URL=postgresql://boomerang:boomerang_secret@127.0.0.1:5435/boomerang_db
FRED_API_KEY=your_actual_fred_api_key
```

### 5. Start the Backend

```bash
uvicorn backend.main:app --reload
```

## Database Schema

### fred_data Table
Stores time series data from FRED API.

| Column | Type | Description |
|--------|------|-------------|
| series_id | VARCHAR(50) | FRED series identifier (e.g., SP500, DGS10) |
| series_type | VARCHAR(30) | Type: index, rate, economic, commodity |
| date | DATE | Data point date |
| value | DOUBLE PRECISION | The actual value |
| created_at | TIMESTAMP | When record was created |
| updated_at | TIMESTAMP | When record was last updated |

**Primary Key:** (series_id, date)

### fred_series_metadata Table
Stores metadata about each FRED series.

| Column | Type | Description |
|--------|------|-------------|
| series_id | VARCHAR(50) | FRED series identifier |
| series_type | VARCHAR(30) | Type category |
| title | VARCHAR(200) | Human-readable title |
| frequency | VARCHAR(20) | Data frequency (Daily, Monthly, etc.) |
| units | VARCHAR(100) | Unit of measurement |
| last_updated | TIMESTAMP | When last synced |

### sector_news_item Table
Raw news headlines stored per sector.

| Column | Type | Description |
|--------|------|-------------|
| sector | VARCHAR(120) | Sector name (e.g., Technology) |
| market | VARCHAR(10) | Market code (US/IN) |
| title | VARCHAR(600) | Headline |
| url | VARCHAR(1200) | Article URL |
| source | VARCHAR(200) | Publisher |
| published_at | TIMESTAMP | Published date |
| snippet | TEXT | Short summary |
| hash | VARCHAR(64) | Dedupe hash |

### sector_snapshot Table
LLM-generated snapshot for each sector.

| Column | Type | Description |
|--------|------|-------------|
| sector | VARCHAR(120) | Sector name |
| market | VARCHAR(10) | Market code (US/IN) |
| as_of | TIMESTAMP | Snapshot time |
| sector_summary | TEXT | LLM summary |
| momentum | VARCHAR(40) | bullish/neutral/bearish |
| risk_notes | TEXT | Key risks |
| who_should_invest | TEXT | Suitable audience |
| suitable_profiles | JSONB | Structured suitability |
| top_stocks | JSONB | LLM-selected stock list |
| score | DOUBLE PRECISION | 0-100 sector score |

### sector_score Table
Numeric score and suitability profile.

| Column | Type | Description |
|--------|------|-------------|
| sector | VARCHAR(120) | Sector name |
| market | VARCHAR(10) | Market code (US/IN) |
| as_of | TIMESTAMP | Snapshot time |
| score | DOUBLE PRECISION | 0-100 |
| suitable_profiles | JSONB | Structured suitability |
| rationale | TEXT | Short rationale |

## API Endpoints

### Sync Endpoints (Fetch from FRED & Store)

```bash
# Sync a single series
POST /api/fred/sync/series
{
  "series_id": "SP500",
  "series_type": "index",
  "days": 365
}

# Sync all default indices (SP500, DJIA, NASDAQ100, etc.)
POST /api/fred/sync/indices

# Sync all interest rates
POST /api/fred/sync/rates

# Sync everything
POST /api/fred/sync/all
```

### Query Endpoints (Read from Cache)

```bash
# Get data for a specific series
GET /api/fred/series/SP500?start_date=2025-01-01&limit=30

# Get latest value for a series
GET /api/fred/series/SP500/latest

# Get latest values for all series
GET /api/fred/latest

# Get dashboard overview
GET /api/fred/dashboard

# Get list of available series
GET /api/fred/available-series

# Smart endpoint (auto-refreshes if stale)
GET /api/fred/smart/SP500?max_age_hours=24
```

### Sector Intelligence Endpoints

```bash
# Refresh all sectors (US + IN)
POST /api/sector-intel/refresh

# Refresh a single sector
POST /api/sector-intel/refresh
{"market": "US", "sector": "Technology", "force": true}

# List latest snapshots
GET /api/sector-intel/latest?market=US

# Get a specific sector
GET /api/sector-intel/latest?market=IN&sector=Financial%20Services

# Recommend sectors for a user profile
POST /api/sector-intel/recommend
{"market": "US", "risk_score": 6, "time_horizon_years": 5, "goal": "growth", "limit": 5}

# Fetch sector stocks with optional enrichments
GET /api/sector-intel/sector/Technology/stocks?market=US&include_fundamentals=true&include_news=true
```

## Sector Intelligence Worker

Run the background worker to refresh sector snapshots on a schedule:

```bash
python -m backend.tools.sector_intel_worker --loop
```

Optional flags:
- `--once` to run a single cycle
- `--force` to ignore freshness checks
- `--markets=US,IN` to limit markets
- `--interval-minutes=60` to adjust refresh cadence

## Sector Intelligence Environment Variables

```env
SECTOR_INTEL_NEWS_LIMIT=10
SECTOR_INTEL_STOCKS_LIMIT=12
SECTOR_INTEL_PRICE_PERIOD=3mo
SECTOR_INTEL_REFRESH_MINUTES=60
SECTOR_INTEL_SECTOR_GAP_SECONDS=120
SECTOR_INTEL_MARKETS=US,IN
SECTOR_INTEL_LLM_MODEL=llama-3.1-8b-instant
```

## Available FRED Series

### Indices (type: "index")
| Series ID | Title |
|-----------|-------|
| SP500 | S&P 500 |
| DJIA | Dow Jones Industrial Average |
| NASDAQ100 | NASDAQ 100 |
| WILL5000IND | Wilshire 5000 |
| VIXCLS | VIX Volatility Index |

### Interest Rates (type: "rate")
| Series ID | Title |
|-----------|-------|
| DGS10 | 10-Year Treasury Rate |
| DGS2 | 2-Year Treasury Rate |
| DGS30 | 30-Year Treasury Rate |
| FEDFUNDS | Federal Funds Rate |
| DPRIME | Bank Prime Loan Rate |

### Economic Indicators (type: "economic")
| Series ID | Title |
|-----------|-------|
| CPIAUCSL | Consumer Price Index |
| UNRATE | Unemployment Rate |
| GDP | Gross Domestic Product |
| INDPRO | Industrial Production Index |

## Docker Commands

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f postgres

# Stop services
docker-compose down

# Stop and remove data
docker-compose down -v

# Restart
docker-compose restart
```

## pgAdmin Access (Optional)

1. Open http://localhost:5050
2. Login: `admin@boomerang.com` / `admin123`
3. Add server:
   - Host: `postgres` (or `host.docker.internal` on Windows/Mac)
   - Port: `5432`
   - Database: `boomerang_db`
   - Username: `boomerang`
   - Password: `boomerang_secret`

## Example Usage in Python

```python
from backend.database import get_db_session, FredRepository
from backend.services.fred_data_service import FredDataService

# Sync data from FRED API
service = FredDataService()
service.sync_all_indices(days=365)

# Query cached data
with get_db_session() as db:
    repo = FredRepository(db)
    
    # Get latest S&P 500 value
    latest = repo.get_latest("SP500")
    print(f"S&P 500: {latest.value} on {latest.date}")
    
    # Get data as DataFrame
    df = repo.series_to_dataframe("SP500")
    print(df.head())
```

## Troubleshooting

### Database connection refused
- Make sure Docker is running
- Check if port 5432 is not in use: `netstat -an | findstr 5432`
- Restart containers: `docker-compose restart`

### FRED API errors
- Verify your FRED_API_KEY is set correctly
- Check rate limits (120 requests per minute)
- Some series may require special permissions

### No data returned
- Run sync endpoint first to populate the database
- Check if the series ID is correct (case-sensitive)
