import { useState } from 'react';
import { 
  User, Moon, Bell, Shield, Globe, 
  Palette, Volume2, Eye, Save
} from 'lucide-react';
import './Settings.css';

function Settings() {
  const [settings, setSettings] = useState({
    username: 'John Doe',
    email: 'john.doe@example.com',
    theme: 'dark',
    language: 'en',
    notifications: {
      email: true,
      push: true,
      priceAlerts: true,
      news: false
    },
    privacy: {
      twoFactor: true,
      sessionTimeout: '30'
    }
  });

  const handleToggle = (category, key) => {
    setSettings(prev => ({
      ...prev,
      [category]: {
        ...prev[category],
        [key]: !prev[category][key]
      }
    }));
  };

  return (
    <div className="settings-page">
      <h1 className="page-title">Settings</h1>

      {/* Profile Section */}
      <div className="settings-section glass-card">
        <div className="section-header">
          <User size={20} />
          <h2>Profile</h2>
        </div>
        <div className="settings-grid">
          <div className="setting-item">
            <label>Username</label>
            <input 
              type="text" 
              value={settings.username}
              onChange={(e) => setSettings({...settings, username: e.target.value})}
            />
          </div>
          <div className="setting-item">
            <label>Email</label>
            <input 
              type="email" 
              value={settings.email}
              onChange={(e) => setSettings({...settings, email: e.target.value})}
            />
          </div>
        </div>
      </div>

      {/* Appearance Section */}
      <div className="settings-section glass-card">
        <div className="section-header">
          <Palette size={20} />
          <h2>Appearance</h2>
        </div>
        <div className="settings-grid">
          <div className="setting-item">
            <label>Theme</label>
            <div className="toggle-group">
              <button 
                className={settings.theme === 'dark' ? 'active' : ''}
                onClick={() => setSettings({...settings, theme: 'dark'})}
              >
                <Moon size={16} /> Dark
              </button>
              <button 
                className={settings.theme === 'light' ? 'active' : ''}
                onClick={() => setSettings({...settings, theme: 'light'})}
              >
                <Eye size={16} /> Light
              </button>
            </div>
          </div>
          <div className="setting-item">
            <label>Language</label>
            <select 
              value={settings.language}
              onChange={(e) => setSettings({...settings, language: e.target.value})}
            >
              <option value="en">English</option>
              <option value="es">Español</option>
              <option value="fr">Français</option>
              <option value="de">Deutsch</option>
            </select>
          </div>
        </div>
      </div>

      {/* Notifications Section */}
      <div className="settings-section glass-card">
        <div className="section-header">
          <Bell size={20} />
          <h2>Notifications</h2>
        </div>
        <div className="toggle-list">
          <div className="toggle-item">
            <div className="toggle-info">
              <span className="toggle-label">Email Notifications</span>
              <span className="toggle-desc">Receive updates via email</span>
            </div>
            <button 
              className={`toggle-switch ${settings.notifications.email ? 'on' : ''}`}
              onClick={() => handleToggle('notifications', 'email')}
            >
              <span className="toggle-knob"></span>
            </button>
          </div>
          <div className="toggle-item">
            <div className="toggle-info">
              <span className="toggle-label">Push Notifications</span>
              <span className="toggle-desc">Receive browser notifications</span>
            </div>
            <button 
              className={`toggle-switch ${settings.notifications.push ? 'on' : ''}`}
              onClick={() => handleToggle('notifications', 'push')}
            >
              <span className="toggle-knob"></span>
            </button>
          </div>
          <div className="toggle-item">
            <div className="toggle-info">
              <span className="toggle-label">Price Alerts</span>
              <span className="toggle-desc">Get notified on price changes</span>
            </div>
            <button 
              className={`toggle-switch ${settings.notifications.priceAlerts ? 'on' : ''}`}
              onClick={() => handleToggle('notifications', 'priceAlerts')}
            >
              <span className="toggle-knob"></span>
            </button>
          </div>
          <div className="toggle-item">
            <div className="toggle-info">
              <span className="toggle-label">Market News</span>
              <span className="toggle-desc">Daily market updates</span>
            </div>
            <button 
              className={`toggle-switch ${settings.notifications.news ? 'on' : ''}`}
              onClick={() => handleToggle('notifications', 'news')}
            >
              <span className="toggle-knob"></span>
            </button>
          </div>
        </div>
      </div>

      {/* Security Section */}
      <div className="settings-section glass-card">
        <div className="section-header">
          <Shield size={20} />
          <h2>Security</h2>
        </div>
        <div className="toggle-list">
          <div className="toggle-item">
            <div className="toggle-info">
              <span className="toggle-label">Two-Factor Authentication</span>
              <span className="toggle-desc">Extra layer of security</span>
            </div>
            <button 
              className={`toggle-switch ${settings.privacy.twoFactor ? 'on' : ''}`}
              onClick={() => handleToggle('privacy', 'twoFactor')}
            >
              <span className="toggle-knob"></span>
            </button>
          </div>
          <div className="setting-item full-width">
            <label>Session Timeout (minutes)</label>
            <select 
              value={settings.privacy.sessionTimeout}
              onChange={(e) => setSettings({
                ...settings, 
                privacy: {...settings.privacy, sessionTimeout: e.target.value}
              })}
            >
              <option value="15">15 minutes</option>
              <option value="30">30 minutes</option>
              <option value="60">1 hour</option>
              <option value="120">2 hours</option>
            </select>
          </div>
        </div>
      </div>

      {/* Save Button */}
      <button className="save-btn">
        <Save size={18} />
        Save Changes
      </button>
    </div>
  );
}

export default Settings;
