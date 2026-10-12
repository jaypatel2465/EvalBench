import { Activity, AlertTriangle, BarChart3, Braces, Database, GitCompare, Gauge, Menu, Scale, Settings, X } from 'lucide-react'
import { useState, type ReactNode } from 'react'

const items = [
  ['Overview', '/', Gauge], ['Runs', '/runs', Activity], ['Compare', '/compare', GitCompare], ['Datasets', '/datasets', Database],
  ['Failures', '/failures', AlertTriangle], ['Judge Reliability', '/judge', Scale], ['Regression Analysis', '/regressions', BarChart3],
  ['Models', '/models', Braces], ['Settings', '/settings', Settings],
] as const

export function Chrome({ path, children }: { path: string; children: ReactNode }) {
  const [open, setOpen] = useState(false)
  return <div className="min-h-screen bg-[#f7f8fa] text-slate-900">
    <aside className={`fixed inset-y-0 left-0 z-30 w-64 border-r border-slate-200 bg-white transition-transform lg:translate-x-0 ${open ? 'translate-x-0' : '-translate-x-full'}`}>
      <div className="flex h-16 items-center justify-between border-b border-slate-200 px-5">
        <a href="#/" className="flex items-center gap-2.5"><span className="grid h-8 w-8 place-items-center rounded-lg bg-slate-950 text-sm font-semibold text-white">E</span><span className="font-semibold tracking-tight">EvalBench</span></a>
        <button className="lg:hidden" onClick={() => setOpen(false)} aria-label="Close navigation"><X size={18}/></button>
      </div>
      <div className="px-3 py-4"><p className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-[.18em] text-slate-400">Workspace</p>
        <nav className="space-y-0.5">{items.map(([label, href, Icon]) => {
          const active = path === href || (href !== '/' && path.startsWith(href))
          return <a key={href} href={`#${href}`} onClick={() => setOpen(false)} className={`flex items-center gap-3 rounded-md px-3 py-2 text-sm transition ${active ? 'bg-slate-100 font-medium text-slate-950' : 'text-slate-600 hover:bg-slate-50 hover:text-slate-950'}`}><Icon size={16}/>{label}</a>
        })}</nav>
      </div>
      <div className="absolute inset-x-3 bottom-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900"><div className="mb-1 font-semibold">Offline demo data</div>Mock runs are labeled and isolated from hosted-provider runs.</div>
    </aside>
    <div className="lg:pl-64"><header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-slate-200 bg-white/95 px-5 backdrop-blur lg:px-8">
      <button onClick={() => setOpen(true)} className="lg:hidden" aria-label="Open navigation"><Menu size={20}/></button>
      <div className="hidden items-center gap-2 text-xs text-slate-500 lg:flex"><span className="h-2 w-2 rounded-full bg-emerald-500"/>API connected</div>
      <div className="flex items-center gap-3"><span className="rounded-md border border-slate-200 px-2.5 py-1 text-xs font-medium text-slate-600">SEC QA · v1</span><div className="grid h-8 w-8 place-items-center rounded-full bg-slate-200 text-xs font-semibold">JD</div></div>
    </header><main className="mx-auto max-w-[1500px] px-5 py-7 lg:px-8">{children}</main></div>
  </div>
}

export function PageHeader({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return <div className="mb-7 flex flex-col justify-between gap-4 sm:flex-row sm:items-end"><div><h1 className="text-2xl font-semibold tracking-tight">{title}</h1><p className="mt-1 text-sm text-slate-500">{description}</p></div>{action}</div>
}

export function Empty({ message }: { message: string }) { return <div className="rounded-lg border border-dashed border-slate-300 bg-white p-10 text-center text-sm text-slate-500">{message}</div> }
export function ErrorBox({ message }: { message: string }) { return <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">{message}. Start the backend or check its logs.</div> }

