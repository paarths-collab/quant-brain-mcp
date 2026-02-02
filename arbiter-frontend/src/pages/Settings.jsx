import { useState } from 'react';
import { Settings as SettingsIcon, Moon, Sun, Bell, Shield, Database, Key, Globe, Palette } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import './Settings.css';

function Settings() {
  const { theme, setTheme } = useTheme();
  const [notifications, setNotifications] = useState(true);
  const [defaultMarket, setDefaultMarket] = useState('US');
  const [apiKey, setApiKey] = useState('');

  return (
    <div className="settings-page">
      <div className="settings-header">
        <h1><SettingsIcon size={28} /> Settings</h1>
        <p>Configure your preferences</p>
      </div>

      <div className="settings-grid">
        {/* Appearance */}
        <div className="settings-section">
          <h3><Palette size={18} /> Appearance</h3>

          <div className="setting-item">
            <div className="setting-info">
              <span className="setting-label">Theme</span>
              <span className="setting-desc">Choose your preferred color scheme</span>
            </div>
            <div className="theme-toggle">
              <button
                className={theme === 'dark' ? 'active' : ''}
                onClick={() => setTheme('dark')}
              >
                <Moon size={16} />
                Dark
              </button>
              <button
                className={theme === 'light' ? 'active' : ''}
                onClick={() => setTheme('light')}
              >
                <Sun size={16} />
                Light
              </button>
            </div>
          </div>
        </div>

        {/* Notifications */}
        <div className="settings-section">
          <h3><Bell size={18} /> Notifications</h3>

          <div className="setting-item">
            <div className="setting-info">
              <span className="setting-label">Push Notifications</span>
              <span className="setting-desc">Receive alerts for price movements</span>
            </div>
            <label className="toggle">
              <input
                type="checkbox"
                checked={notifications}
                onChange={(e) => setNotifications(e.target.checked)}
              />
              <span className="slider"></span>
            </label>
          </div>

          <div className="setting-item">
            <div className="setting-info">
              <span className="setting-label">Email Alerts</span>
              <span className="setting-desc">Get daily market summaries</span>
            </div>
            <label className="toggle">
              <input type="checkbox" defaultChecked />
              <span className="slider"></span>
            </label>
          </div>
        </div>

        {/* Market Preferences */}
        <div className="settings-section">
          <h3><Globe size={18} /> Market Preferences</h3>

          <div className="setting-item">
            <div className="setting-info">
              <span className="setting-label">Default Market</span>
              <span className="setting-desc">Your preferred stock market</span>
            </div>
            <select
              value={defaultMarket}
              onChange={(e) => setDefaultMarket(e.target.value)}
            >
              <option value="US">United States ($)</option>
              <option value="IN">India (₹)</option>
              <option value="UK">United Kingdom (£)</option>
              <option value="JP">Japan (¥)</option>
            </select>
          </div>

          <div className="setting-item">
            <div className="setting-info">
              <span className="setting-label">Currency Display</span>
              <span className="setting-desc">Format for displaying prices</span>
            </div>
            <select defaultValue="symbol">
              <option value="symbol">Symbol (₹, $, £)</option>
              <option value="code">Code (INR, USD, GBP)</option>
            </select>
          </div>
        </div>

        {/* API & Data */}
        <div className="settings-section">
          <h3><Key size={18} /> API Configuration</h3>

          <div className="setting-item vertical">
            <div className="setting-info">
              <span className="setting-label">API Key</span>
              <span className="setting-desc">Your personal API key for data access</span>
            </div>
            <input
              type="password"
              placeholder="Enter API key..."
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
            />
          </div>

          <div className="setting-item">
            <div className="setting-info">
              <span className="setting-label">Backend URL</span>
              <span className="setting-desc">API endpoint for data</span>
            </div>
            <input
              type="text"
              defaultValue="http://localhost:8000"
              disabled
            />
          </div>
        </div>

        {/* Security */}
        <div className="settings-section">
          <h3><Shield size={18} /> Security</h3>

          <div className="setting-item">
            <div className="setting-info">
              <span className="setting-label">Two-Factor Authentication</span>
              <span className="setting-desc">Add an extra layer of security</span>
            </div>
            <button className="setup-btn">Setup</button>
          </div>

          <div className="setting-item">
            <div className="setting-info">
              <span className="setting-label">Session Timeout</span>
              <span className="setting-desc">Auto logout after inactivity</span>
            </div>
            <select defaultValue="30">
              <option value="15">15 minutes</option>
              <option value="30">30 minutes</option>
              <option value="60">1 hour</option>
              <option value="never">Never</option>
            </select>
          </div>
        </div>

        {/* Data Management */}
        <div className="settings-section">
          <h3><Database size={18} /> Data Management</h3>

          <div className="setting-item">
            <div className="setting-info">
              <span className="setting-label">Clear Cache</span>
              <span className="setting-desc">Remove locally stored data</span>
            </div>
            <button className="danger-btn">Clear</button>
          </div>

          <div className="setting-item">
            <div className="setting-info">
              <span className="setting-label">Export Data</span>
              <span className="setting-desc">Download your settings and watchlist</span>
            </div>
            <button className="setup-btn">Export</button>
          </div>
        </div>
      </div>

      <div className="settings-footer">
        <button className="save-btn">Save Changes</button>
      </div>
    </div>
  );
}

export default Settings;
