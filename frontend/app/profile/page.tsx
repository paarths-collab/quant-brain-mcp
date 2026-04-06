'use client'

const CARD = "relative p-6 rounded-2xl border border-slate-400 bg-white/[0.03] backdrop-blur-xl"

export default function ProfilePage() {
  const stats = [
    { label: 'Account Type', value: 'Pro Analyst' },
    { label: 'Member Since', value: 'Mar 2024' },
    { label: 'Data Access', value: 'Level 3 — Full' },
    { label: 'API Calls (today)', value: '1,482 / 10,000' },
    { label: 'Agent Runs (30d)', value: '214' },
    { label: 'Subscription', value: 'Enterprise Annual' },
  ]

  return (
    <div className="space-y-8 font-inter max-w-2xl">
      <div>
        <h1 className="font-dm-mono text-[28px] font-medium text-slate-200 tracking-tight">Profile</h1>
        <p className="font-inter text-[13px] text-slate-400 mt-1">Account details & usage statistics</p>
      </div>

      {/* Avatar & name */}
      <div className={CARD + " flex items-center gap-6"}>
        <div className="w-16 h-16 rounded-2xl bg-indigo-500/15 border border-indigo-500/25 flex items-center justify-center shrink-0">
          <span className="font-dm-mono text-[22px] font-medium text-indigo-400">PG</span>
        </div>
        <div>
          <div className="font-dm-mono text-[20px] font-medium text-slate-200">Paarth Gala</div>
          <div className="font-inter text-[13px] text-slate-400 mt-1">paarth@bloomberg-quant.io</div>
          <div className="inline-flex items-center gap-1.5 mt-2 px-2.5 py-1 rounded-full border border-indigo-500/25 bg-indigo-500/8">
            <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" />
            <span className="font-dm-mono text-[9px] text-indigo-400 tracking-widest">ACTIVE SUBSCRIPTION</span>
          </div>
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 gap-3">
        {stats.map(s => (
          <div key={s.label} className="p-4 rounded-xl border border-slate-400 bg-white/[0.02]">
            <div className="font-inter text-[10px] text-slate-400 uppercase tracking-[0.18em] mb-1.5 font-medium">{s.label}</div>
            <div className="font-dm-mono text-[15px] font-medium text-slate-200">{s.value}</div>
          </div>
        ))}
      </div>

      {/* Danger zone */}
      <div className="p-5 rounded-xl border border-slate-400 bg-white/[0.01]">
        <div className="font-inter text-[11px] text-slate-400 uppercase tracking-[0.2em] mb-4 font-medium">Session</div>
        <button className="font-dm-mono text-[11px] px-4 py-2 rounded-lg border border-slate-400 text-slate-300 hover:text-white hover:border-slate-300 transition-all tracking-widest uppercase">
          Sign Out
        </button>
      </div>
    </div>
  )
}
