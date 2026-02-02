-- Initialize FRED data table for storing index prices
CREATE TABLE IF NOT EXISTS fred_data (
    series_id VARCHAR(50) NOT NULL,
    series_type VARCHAR(30) NOT NULL,
    date DATE NOT NULL,
    value DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
    series_id VARCHAR(50) PRIMARY KEY,
    series_type VARCHAR(30) NOT NULL,
    title VARCHAR(200),
    frequency VARCHAR(20),
    units VARCHAR(100),
    last_updated TIMESTAMP
);

-- Common index series
INSERT INTO fred_series_metadata (series_id, series_type, title, frequency, units) VALUES
    ('SP500', 'index', 'S&P 500', 'Daily', 'Index'),
    ('DJIA', 'index', 'Dow Jones Industrial Average', 'Daily', 'Index'),
    ('NASDAQ100', 'index', 'NASDAQ 100 Index', 'Daily', 'Index'),
    ('WILL5000IND', 'index', 'Wilshire 5000 Total Market Index', 'Daily', 'Index'),
    ('VIXCLS', 'index', 'CBOE Volatility Index: VIX', 'Daily', 'Index'),
    ('DGS10', 'rate', '10-Year Treasury Constant Maturity Rate', 'Daily', 'Percent'),
    ('DGS2', 'rate', '2-Year Treasury Constant Maturity Rate', 'Daily', 'Percent'),
    ('FEDFUNDS', 'rate', 'Federal Funds Effective Rate', 'Daily', 'Percent'),
    ('CPIAUCSL', 'economic', 'Consumer Price Index for All Urban Consumers', 'Monthly', 'Index'),
    ('UNRATE', 'economic', 'Unemployment Rate', 'Monthly', 'Percent'),
    ('GDP', 'economic', 'Gross Domestic Product', 'Quarterly', 'Billions of Dollars'),
    ('DCOILWTICO', 'commodity', 'Crude Oil Prices: WTI', 'Daily', 'Dollars per Barrel'),
    ('GOLDAMGBD228NLBM', 'commodity', 'Gold Fixing Price', 'Daily', 'Dollars per Troy Ounce')
ON CONFLICT (series_id) DO NOTHING;

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for auto-updating updated_at
DROP TRIGGER IF EXISTS update_fred_data_updated_at ON fred_data;
CREATE TRIGGER update_fred_data_updated_at
    BEFORE UPDATE ON fred_data
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
