import { useState, useEffect } from 'react';
import {
  Settings as SettingsIcon, Monitor, Bell, Database,
  Key, Globe2, Save, Check, AlertTriangle,
} from 'lucide-react';

function Toggle({ enabled, onChange, label }: { enabled: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <button onClick={() => onChange(!enabled)} className="flex items-center justify-between w-full py-3 group">
      <span className="text-sm text-white/70 group-hover:text-white transition-colors">{label}</span>
      <div className={`w-10 h-5 rounded-full relative transition-colors duration-200 ${enabled ? 'bg-purple-600' : 'bg-white/10'}`}>
        <div className="absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform duration-200"
          style={{ left: 2, transform: enabled ? 'translateX(20px)' : 'translateX(0)' }} />
      </div>
    </button>
  );
}

function Section({ icon: Icon, title, description, children }: { icon: any; title: string; description: string; children: React.ReactNode }) {
  return (
    <div className="bg-white/[0.02] border border-white/[0.06] rounded-2xl p-6">
      <div className="flex items-center gap-3 mb-1">
        <div className="w-8 h-8 rounded-lg bg-purple-500/10 flex items-center justify-center"><Icon size={16} className="text-purple-400" /></div>
        <div><h3 className="text-sm font-bold text-white">{title}</h3><p className="text-[11px] text-white/30">{description}</p></div>
      </div>
      <div className="mt-5 space-y-1 divide-y divide-white/[0.04]">{children}</div>
    </div>
  );
}

function APIKeyInput({ label, envKey, placeholder }: { label: string; envKey: string; placeholder: string }) {
  const [value, setValue] = useState('');
  const [saved, setSaved] = useState(false);
  const [visible, setVisible] = useState(false);
  const handleSave = () => { localStorage.setItem(`api_key_${envKey}`, value); setSaved(true); setTimeout(() => setSaved(false), 2000); };
  useEffect(() => { const stored = localStorage.getItem(`api_key_${envKey}`); if (stored) setValue(stored); }, [envKey]);
  return (
    <div className="py-3">
      <div className="flex items-center justify-between mb-1.5">
        <label className="text-sm text-white/70">{label}</label>
        <span className="text-[10px] text-white/20 font-mono">{envKey}</span>
      </div>
      <div className="flex gap-2">
        <div className="relative flex-1">
          <input type={visible ? 'text' : 'password'} value={value} onChange={(e) => setValue(e.target.value)} placeholder={placeholder}
            className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white font-mono focus:outline-none focus:border-purple-500/40" />
          <button onClick={() => setVisible(!visible)} className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] text-white/30 hover:text-white/50">
            {visible ? 'HIDE' : 'SHOW'}
          </button>
        </div>
        <button onClick={handleSave} disabled={!value.trim()}
          className="px-4 py-2.5 bg-purple-600/20 hover:bg-purple-600/30 disabled:opacity-20 text-purple-400 text-sm rounded-xl transition-colors flex items-center gap-2">
          {saved ? <Check size={14} /> : <Save size={14} />}
        </button>
      </div>
    </div>
  );
}

export default function Settings() {
  const [defaultMarket, setDefaultMarket] = useState(() => localStorage.getItem('default_market') || 'US');
  const [notifications, setNotifications] = useState({ priceAlerts: true, tradeSignals: true, newsDigest: false, weeklyReport: true });
  const [display, setDisplay] = useState({ compactMode: false, animatedCharts: true, showVolume: true, darkCandlesticks: true });

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <div className="flex items-center gap-2 text-xs font-bold tracking-[0.3em] text-purple-400 uppercase mb-2"><SettingsIcon size={14} /> Configuration</div>
        <h1 className="font-display text-3xl font-bold text-white">Settings</h1>
        <p className="text-white/50 mt-1 text-sm">Configure your terminal, API keys, and preferences</p>
      </div>

      <Section icon={Key} title="API Keys" description="Required for LLM-powered analysis">
        <APIKeyInput label="Gemini API Key" envKey="GEMINI_API_KEY" placeholder="AIza..." />
        <APIKeyInput label="Groq API Key" envKey="GROQ_API_KEY" placeholder="gsk_..." />
        <APIKeyInput label="Tavily API Key" envKey="TAVILY_API_KEY" placeholder="tvly-..." />
        <div className="pt-3">
          <div className="bg-amber-500/5 border border-amber-500/10 rounded-xl p-3 flex items-start gap-2">
            <AlertTriangle size={14} className="text-amber-400 shrink-0 mt-0.5" />
            <p className="text-[11px] text-amber-300/60 leading-relaxed">API keys are stored locally. For production, configure them as backend environment variables.</p>
          </div>
        </div>
      </Section>

      <Section icon={Globe2} title="Default Market" description="Choose your primary market region">
        <div className="py-3 flex gap-3">
          {[{ id: 'US', label: 'United States', flag: '🇺🇸', desc: 'NYSE, NASDAQ' }, { id: 'IN', label: 'India', flag: '🇮🇳', desc: 'NSE, BSE' }].map(m => (
            <button key={m.id} onClick={() => { setDefaultMarket(m.id); localStorage.setItem('default_market', m.id); }}
              className={`flex-1 p-4 rounded-xl border transition-all ${defaultMarket === m.id ? 'bg-purple-600/10 border-purple-500/30 text-white' : 'bg-black/20 border-white/5 text-white/50 hover:border-white/10'}`}>
              <div className="text-2xl mb-2">{m.flag}</div>
              <div className="text-sm font-medium">{m.label}</div>
              <div className="text-[10px] text-white/30 mt-0.5">{m.desc}</div>
            </button>
          ))}
        </div>
      </Section>

      <Section icon={Bell} title="Notifications" description="Configure alert preferences">
        <Toggle label="Price Alerts" enabled={notifications.priceAlerts} onChange={(v) => setNotifications(p => ({ ...p, priceAlerts: v }))} />
        <Toggle label="Trade Signals" enabled={notifications.tradeSignals} onChange={(v) => setNotifications(p => ({ ...p, tradeSignals: v }))} />
        <Toggle label="Daily News Digest" enabled={notifications.newsDigest} onChange={(v) => setNotifications(p => ({ ...p, newsDigest: v }))} />
        <Toggle label="Weekly Portfolio Report" enabled={notifications.weeklyReport} onChange={(v) => setNotifications(p => ({ ...p, weeklyReport: v }))} />
      </Section>

      <Section icon={Monitor} title="Display & Charts" description="Visual preferences">
        <Toggle label="Compact Mode" enabled={display.compactMode} onChange={(v) => setDisplay(p => ({ ...p, compactMode: v }))} />
        <Toggle label="Animated Charts" enabled={display.animatedCharts} onChange={(v) => setDisplay(p => ({ ...p, animatedCharts: v }))} />
        <Toggle label="Show Volume Bars" enabled={display.showVolume} onChange={(v) => setDisplay(p => ({ ...p, showVolume: v }))} />
        <Toggle label="Dark Candlestick Theme" enabled={display.darkCandlesticks} onChange={(v) => setDisplay(p => ({ ...p, darkCandlesticks: v }))} />
      </Section>

      <Section icon={Database} title="System" description="Backend connection & diagnostics">
        <div className="py-3 space-y-3">
          <div className="flex justify-between text-sm"><span className="text-white/40">Backend URL</span><span className="font-mono text-white/60">localhost:8001</span></div>
          <div className="flex justify-between text-sm"><span className="text-white/40">WebSocket</span><span className="font-mono text-white/60">ws://localhost:8001/ws/live</span></div>
          <div className="flex justify-between text-sm"><span className="text-white/40">Version</span><span className="font-mono text-white/60">2.0.0-k2</span></div>
          <div className="flex justify-between text-sm"><span className="text-white/40">Pipeline</span><span className="font-mono text-emerald-400">Multi-Agent v3</span></div>
        </div>
      </Section>
    </div>
  );
}
