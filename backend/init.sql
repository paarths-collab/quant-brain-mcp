-- Initialize FRED data table for storing index prices
CREATE TABLE IF NOT EXISTS fred_data (
    series_id TEXT NOT NULL,
    series_type TEXT NOT NULL,
    date TEXT NOT NULL,
    value REAL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (series_id, date)
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_fred_series_type ON fred_data(series_type);
CREATE INDEX IF NOT EXISTS idx_fred_date ON fred_data(date);
CREATE INDEX IF NOT EXISTS idx_fred_series_date ON fred_data(series_id, date DESC);

-- Common FRED series types for reference:
-- 'index' - Stock market indices (SP500, DJIA, NASDAQ100)
-- 'rate' - Interest rates (DGS10, DGS2, FEDFUNDS)
-- 'economic' - Economic indicators (GDP, CPIAUCSL, UNRATE)
-- 'currency' - Exchange rates (DEXUSEU, DEXJPUS)
-- 'commodity' - Commodity prices (DCOILWTICO, GOLDAMGBD228NLBM)

-- Insert some metadata about common series
CREATE TABLE IF NOT EXISTS fred_series_metadata (
    series_id TEXT PRIMARY KEY,
    series_type TEXT NOT NULL,
    title TEXT,
    frequency TEXT,
    units TEXT,
    last_updated TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Common index series
INSERT OR IGNORE INTO fred_series_metadata (series_id, series_type, title, frequency, units, last_updated) VALUES
    ('SP500', 'index', 'S&P 500', 'Daily', 'Index', CURRENT_TIMESTAMP),
    ('DJIA', 'index', 'Dow Jones Industrial Average', 'Daily', 'Index', CURRENT_TIMESTAMP),
    ('NASDAQ100', 'index', 'NASDAQ 100 Index', 'Daily', 'Index', CURRENT_TIMESTAMP),
    ('WILL5000IND', 'index', 'Wilshire 5000 Total Market Index', 'Daily', 'Index', CURRENT_TIMESTAMP),
    ('VIXCLS', 'index', 'CBOE Volatility Index: VIX', 'Daily', 'Index', CURRENT_TIMESTAMP),
    ('DGS10', 'rate', '10-Year Treasury Constant Maturity Rate', 'Daily', 'Percent', CURRENT_TIMESTAMP),
    ('DGS2', 'rate', '2-Year Treasury Constant Maturity Rate', 'Daily', 'Percent', CURRENT_TIMESTAMP),
    ('FEDFUNDS', 'rate', 'Federal Funds Effective Rate', 'Daily', 'Percent', CURRENT_TIMESTAMP),
    ('CPIAUCSL', 'economic', 'Consumer Price Index for All Urban Consumers', 'Monthly', 'Index', CURRENT_TIMESTAMP),
    ('UNRATE', 'economic', 'Unemployment Rate', 'Monthly', 'Percent', CURRENT_TIMESTAMP),
    ('GDP', 'economic', 'Gross Domestic Product', 'Quarterly', 'Billions of Dollars', CURRENT_TIMESTAMP),
    ('DCOILWTICO', 'commodity', 'Crude Oil Prices: WTI', 'Daily', 'Dollars per Barrel', CURRENT_TIMESTAMP),
    ('GOLDAMGBD228NLBM', 'commodity', 'Gold Fixing Price', 'Daily', 'Dollars per Troy Ounce', CURRENT_TIMESTAMP);

-- SQLite trigger for auto-updating updated_at on fred_data
DROP TRIGGER IF EXISTS update_fred_data_updated_at;
CREATE TRIGGER update_fred_data_updated_at
    AFTER UPDATE ON fred_data
    FOR EACH ROW
    BEGIN
        UPDATE fred_data SET updated_at = CURRENT_TIMESTAMP WHERE rowid = NEW.rowid;
    END;

-- =====================================================
-- SECTOR INTELLIGENCE (NEWS + SNAPSHOTS)
-- =====================================================

CREATE TABLE IF NOT EXISTS sector_news_item (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sector TEXT NOT NULL,
    market TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT,
    source TEXT,
    published_at TEXT,
    snippet TEXT,
    hash TEXT NOT NULL,
    ingested_at TEXT DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_sector_news_hash UNIQUE (market, sector, hash)
);

CREATE INDEX IF NOT EXISTS idx_sector_news_market_sector_date
    ON sector_news_item (market, sector, published_at);

CREATE TABLE IF NOT EXISTS sector_snapshot (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sector TEXT NOT NULL,
    market TEXT NOT NULL,
    as_of TEXT NOT NULL,
    news_item_ids TEXT,
    sector_summary TEXT,
    momentum TEXT,
    risk_notes TEXT,
    who_should_invest TEXT,
    suitable_profiles TEXT,
    top_stocks TEXT,
    score REAL,
    llm_model TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sector_snapshot_market_sector_asof
    ON sector_snapshot (market, sector, as_of);

CREATE TABLE IF NOT EXISTS sector_score (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sector TEXT NOT NULL,
    market TEXT NOT NULL,
    as_of TEXT NOT NULL,
    score REAL,
    suitable_profiles TEXT,
    rationale TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sector_score_market_sector_asof
    ON sector_score (market, sector, as_of);

-- =====================================================
-- USER PROFILES
-- =====================================================

CREATE TABLE IF NOT EXISTS user_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT UNIQUE NOT NULL DEFAULT 'default',
    name TEXT,
    age INTEGER,
    monthly_income REAL,
    monthly_savings REAL,
    risk_tolerance TEXT DEFAULT 'moderate',
    horizon_years INTEGER DEFAULT 5,
    primary_goal TEXT,
    existing_investments TEXT,
    market TEXT DEFAULT 'US',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON user_profiles(user_id);

-- SQLite trigger for auto-updating updated_at on user_profiles
DROP TRIGGER IF EXISTS update_user_profiles_updated_at;
CREATE TRIGGER update_user_profiles_updated_at
    AFTER UPDATE ON user_profiles
    FOR EACH ROW
    BEGIN
        UPDATE user_profiles SET updated_at = CURRENT_TIMESTAMP WHERE rowid = NEW.rowid;
    END;
