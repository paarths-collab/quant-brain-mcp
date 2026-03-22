'use client'

export default function GlobalMarketsPage() {
  const regions = [
    { region: 'Americas', indices: [
      { name: 'S&P 500', value: '5,842.47', change: '+0.40%', up: true },
      { name: 'NASDAQ', value: '20,378.92', change: '+0.43%', up: true },
      { name: 'Dow Jones', value: '43,192.05', change: '-0.10%', up: false },
      { name: 'Brazil Bovespa', value: '127,842', change: '+0.62%', up: true },
    ]},
    { region: 'Europe', indices: [
      { name: 'FTSE 100', value: '8,274.65', change: '+0.28%', up: true },
      { name: 'DAX', value: '18,402.30', change: '-0.15%', up: false },
      { name: 'CAC 40', value: '8,012.75', change: '+0.09%', up: true },
      { name: 'Euro Stoxx 50', value: '5,124.88', change: '-0.22%', up: false },
    ]},
    { region: 'Asia Pacific', indices: [
      { name: 'Nifty 50', value: '22,402.40', change: '+0.50%', up: true },
      { name: 'Nikkei 225', value: '38,902.15', change: '+1.12%', up: true },
      { name: 'Hang Seng', value: '18,041.00', change: '-0.73%', up: false },
      { name: 'ASX 200', value: '7,814.30', change: '+0.18%', up: true },
    ]},
  ]

  const fx = [
    { pair: 'EUR/USD', rate: '1.0842', change: '+0.12%', up: true },
    { pair: 'USD/JPY', rate: '149.72', change: '-0.24%', up: false },
    { pair: 'GBP/USD', rate: '1.2634', change: '+0.08%', up: true },
    { pair: 'USD/INR', rate: '83.47', change: '-0.05%', up: false },
    { pair: 'USD/CNY', rate: '7.2314', change: '+0.03%', up: true },
    { pair: 'AUD/USD', rate: '0.6581', change: '-0.11%', up: false },
  ]

  return (
    <div className="space-y-8 font-inter">
      <div>
        <h1 className="font-dm-mono text-[28px] font-medium text-white tracking-tight">Global Markets</h1>
        <p className="font-inter text-[13px] text-white/30 mt-1">Major indices across Americas, Europe & Asia Pacific</p>
      </div>

      {regions.map(r => (
        <section key={r.region}>
          <div className="flex items-center gap-3 mb-4">
            <div className="w-5 h-[1px] bg-indigo-500/40" />
            <span className="font-dm-mono text-[10px] text-white/25 uppercase tracking-[0.3em]">{r.region}</span>
          </div>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            {r.indices.map(idx => (
              <div key={idx.name} className="p-4 rounded-xl border border-white/[0.07] bg-white/[0.03] backdrop-blur-xl hover:bg-white/[0.05] hover:border-white/[0.12] transition-all">
                <div className="font-inter text-[11px] text-white/30 mb-2 font-medium truncate">{idx.name}</div>
                <div className="font-dm-mono text-[18px] font-medium text-white tabular-nums tracking-tight">{idx.value}</div>
                <div className={`font-dm-mono text-[12px] mt-1 ${idx.up ? 'text-indigo-400' : 'text-white/30'}`}>{idx.change}</div>
              </div>
            ))}
          </div>
        </section>
      ))}

      <section>
        <div className="flex items-center gap-3 mb-4">
          <div className="w-5 h-[1px] bg-indigo-500/40" />
          <span className="font-dm-mono text-[10px] text-white/25 uppercase tracking-[0.3em]">FX Rates</span>
        </div>
        <div className="rounded-2xl border border-white/[0.07] bg-white/[0.03] backdrop-blur-xl overflow-hidden">
          <div className="grid grid-cols-3 lg:grid-cols-6">
            {fx.map((f, i) => (
              <div key={f.pair} className={`p-4 ${i < fx.length - 1 ? 'border-r border-white/[0.04]' : ''}`}>
                <div className="font-dm-mono text-[10px] text-white/25 mb-1.5 tracking-wider">{f.pair}</div>
                <div className="font-dm-mono text-[16px] font-medium text-white tabular-nums">{f.rate}</div>
                <div className={`font-dm-mono text-[11px] mt-0.5 ${f.up ? 'text-indigo-400' : 'text-white/30'}`}>{f.change}</div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  )
}
