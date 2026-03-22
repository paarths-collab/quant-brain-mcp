'use client'

import { useState } from 'react'

type ToggleProps = { label: string; description: string; defaultOn?: boolean }

function Toggle({ label, description, defaultOn = false }: ToggleProps) {
  const [on, setOn] = useState(defaultOn)
  return (
    <div className="flex items-center justify-between py-4 border-b border-white/[0.04] last:border-0">
      <div>
        <div className="font-inter text-[14px] text-white/75 font-medium">{label}</div>
        <div className="font-inter text-[12px] text-white/25 mt-0.5">{description}</div>
      </div>
      <button
        onClick={() => setOn(!on)}
        className={`relative w-10 h-5 rounded-full border transition-all duration-200 ${on ? 'bg-indigo-500/30 border-indigo-500/50' : 'bg-white/[0.05] border-white/[0.1]'}`}
      >
        <div className={`absolute top-0.5 w-4 h-4 rounded-full transition-all duration-200 ${on ? 'left-5 bg-indigo-400' : 'left-0.5 bg-white/25'}`} />
      </button>
    </div>
  )
}

export default function SettingsPage() {
  const [theme, setTheme] = useState('dark')
  const [defaultMarket, setDefaultMarket] = useState('us')

  return (
    <div className="space-y-8 font-inter max-w-2xl">
      <div>
        <h1 className="font-dm-mono text-[28px] font-medium text-white tracking-tight">Settings</h1>
        <p className="font-inter text-[13px] text-white/30 mt-1">Preferences & terminal configuration</p>
      </div>

      {/* Appearance */}
      <div className="rounded-2xl border border-white/[0.07] bg-white/[0.03] backdrop-blur-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-white/[0.05]">
          <span className="font-inter text-[11px] text-white/30 uppercase tracking-[0.2em] font-medium">Appearance</span>
        </div>
        <div className="px-6">
          <div className="flex items-center justify-between py-4 border-b border-white/[0.04]">
            <div>
              <div className="font-inter text-[14px] text-white/75 font-medium">Default Market</div>
              <div className="font-inter text-[12px] text-white/25 mt-0.5">Sets currency & index data on load</div>
            </div>
            <div className="flex items-center border border-white/[0.07] rounded-lg overflow-hidden font-dm-mono text-[11px] tracking-widest">
              {['us', 'india'].map(m => (
                <button key={m} onClick={() => setDefaultMarket(m)} className={`px-3 py-1.5 transition-all ${defaultMarket === m ? 'bg-indigo-500/15 text-white' : 'text-white/25 hover:text-white/50'}`}>
                  {m === 'us' ? '$ US' : '₹ INDIA'}
                </button>
              ))}
            </div>
          </div>
          <Toggle label="Compact Mode" description="Reduce padding for denser data display" />
          <Toggle label="Monospace Numbers" description="Use DM Mono for all numeric values" defaultOn={true} />
          <Toggle label="Animate Charts" description="Enable sparkline and chart animations" defaultOn={true} />
        </div>
      </div>

      {/* Notifications */}
      <div className="rounded-2xl border border-white/[0.07] bg-white/[0.03] backdrop-blur-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-white/[0.05]">
          <span className="font-inter text-[11px] text-white/30 uppercase tracking-[0.2em] font-medium">Notifications</span>
        </div>
        <div className="px-6">
          <Toggle label="Price Alerts" description="Notify when watchlist moves ±2%" defaultOn={true} />
          <Toggle label="Agent Summaries" description="Daily AI-generated market digest" defaultOn={true} />
          <Toggle label="News Flash" description="Breaking news for tracked tickers" />
        </div>
      </div>

      {/* API */}
      <div className="rounded-2xl border border-white/[0.07] bg-white/[0.03] backdrop-blur-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-white/[0.05]">
          <span className="font-inter text-[11px] text-white/30 uppercase tracking-[0.2em] font-medium">API & Data</span>
        </div>
        <div className="px-6 py-5 space-y-4">
          <div>
            <div className="font-inter text-[11px] text-white/25 uppercase tracking-[0.18em] mb-2 font-medium">API Key</div>
            <div className="flex items-center gap-3">
              <div className="flex-1 px-4 py-2.5 rounded-lg border border-white/[0.07] bg-black font-dm-mono text-[12px] text-white/30 tracking-wider">
                bq_live_•••••••••••••••••••••••••••••
              </div>
              <button className="px-3 py-2.5 rounded-lg border border-white/[0.07] font-dm-mono text-[10px] text-white/30 hover:text-white/60 hover:border-white/[0.15] transition-all tracking-widest uppercase">COPY</button>
            </div>
          </div>
          <Toggle label="Stream Mode" description="Use WebSocket for real-time data (vs polling)" defaultOn={true} />
        </div>
      </div>
    </div>
  )
}
