'use client'

const CARD = "relative p-6 rounded-2xl border border-white/[0.07] bg-white/[0.03] backdrop-blur-xl overflow-hidden"

export default function SectorsPage() {
  const sectors = [
    { name: 'Technology', weight: 28.4, change: 1.2, ytd: 14.3 },
    { name: 'Financials', weight: 14.1, change: -0.4, ytd: 8.7 },
    { name: 'Healthcare', weight: 12.8, change: 0.6, ytd: 5.1 },
    { name: 'Consumer Disc.', weight: 10.2, change: 2.1, ytd: 19.4 },
    { name: 'Industrials', weight: 8.9, change: -0.2, ytd: 6.2 },
    { name: 'Communication', weight: 8.5, change: 0.9, ytd: 11.8 },
    { name: 'Energy', weight: 4.3, change: -1.1, ytd: -2.4 },
    { name: 'Materials', weight: 3.8, change: 0.3, ytd: 4.9 },
    { name: 'Utilities', weight: 2.6, change: -0.7, ytd: -1.2 },
    { name: 'Real Estate', weight: 2.4, change: -0.5, ytd: -3.1 },
    { name: 'Cons. Staples', weight: 4.0, change: 0.1, ytd: 2.3 },
  ]

  return (
    <div className="space-y-8 font-inter">
      <div>
        <h1 className="font-dm-mono text-[28px] font-medium text-white tracking-tight">Sectors</h1>
        <p className="font-inter text-[13px] text-white/30 mt-1">S&P 500 Sector Performance & Weights</p>
      </div>

      <div className="rounded-2xl border border-white/[0.07] bg-white/[0.03] backdrop-blur-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-white/[0.05]">
          <span className="font-inter text-[11px] text-white/30 uppercase tracking-[0.2em] font-medium">Real-time Sector Map</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-white/[0.04]">
                {['Sector', 'Weight', 'Day Change', 'YTD'].map(h => (
                  <th key={h} className="px-6 py-3 text-left font-inter text-[10px] text-white/20 uppercase tracking-[0.2em] font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sectors.map(s => {
                const up = s.change >= 0
                return (
                  <tr key={s.name} className="border-b border-white/[0.025] hover:bg-white/[0.025] transition-colors cursor-default">
                    <td className="px-6 py-4 font-inter text-[14px] text-white/80 font-medium">{s.name}</td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-[80px] h-1 rounded-full bg-white/[0.06] overflow-hidden">
                          <div className="h-full bg-indigo-500/50 rounded-full" style={{ width: `${s.weight / 30 * 100}%` }} />
                        </div>
                        <span className="font-dm-mono text-[13px] text-white/60 tabular-nums">{s.weight}%</span>
                      </div>
                    </td>
                    <td className={`px-6 py-4 font-dm-mono text-[13px] tabular-nums ${up ? 'text-indigo-400' : 'text-white/35'}`}>
                      {up ? '+' : ''}{s.change.toFixed(2)}%
                    </td>
                    <td className={`px-6 py-4 font-dm-mono text-[13px] tabular-nums font-medium ${s.ytd >= 0 ? 'text-white/70' : 'text-white/30'}`}>
                      {s.ytd >= 0 ? '+' : ''}{s.ytd.toFixed(1)}%
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
