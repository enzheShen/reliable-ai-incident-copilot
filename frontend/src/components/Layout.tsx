import { Activity, BookOpenCheck, Gauge, History, Menu, ShieldCheck, X } from 'lucide-react'
import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'

const links = [
  { to: '/', label: 'Analyse Incident', icon: Activity },
  { to: '/history', label: 'Incident History', icon: History },
  { to: '/reliability', label: 'Reliability Dashboard', icon: Gauge },
  { to: '/architecture', label: 'Architecture & SLO', icon: BookOpenCheck },
]

export function Layout() {
  const [open, setOpen] = useState(false)
  return (
    <div className="min-h-screen bg-canvas">
      <header className="sticky top-0 z-40 border-b border-ink/10 bg-canvas/90 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-[1500px] items-center justify-between px-4 sm:px-6 lg:px-8">
          <NavLink to="/" className="flex items-center gap-3" onClick={() => setOpen(false)}>
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-ink text-white"><ShieldCheck size={19} /></span>
            <span><span className="block text-sm font-bold tracking-tight">Incident Copilot</span><span className="block text-[10px] uppercase tracking-[.2em] text-ink/50">Reliable AI systems</span></span>
          </NavLink>
          <button className="rounded-lg p-2 lg:hidden" onClick={() => setOpen((value) => !value)} aria-label="Toggle navigation">{open ? <X /> : <Menu />}</button>
          <nav className={`${open ? 'flex' : 'hidden'} absolute left-4 right-4 top-[72px] flex-col gap-1 rounded-2xl border border-ink/10 bg-white p-2 shadow-card lg:static lg:flex lg:flex-row lg:border-0 lg:bg-transparent lg:p-0 lg:shadow-none`}>
            {links.map(({ to, label, icon: Icon }) => (
              <NavLink key={to} to={to} end={to === '/'} onClick={() => setOpen(false)} className={({ isActive }) => `flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium transition ${isActive ? 'bg-ink text-white' : 'text-ink/60 hover:bg-white hover:text-ink'}`}><Icon size={16} />{label}</NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-[1500px] px-4 py-8 sm:px-6 lg:px-8 lg:py-12"><Outlet /></main>
      <footer className="mx-auto max-w-[1500px] border-t border-ink/10 px-6 py-6 text-xs text-ink/50">Synthetic incident data only · Mock mode requires no paid API key</footer>
    </div>
  )
}
