import { ArrowDownRight, ArrowUpRight, ChevronRight } from 'lucide-react'
import { Sparkline, Tradeoff } from '../components/Charts'
import { Empty, ErrorBox, PageHeader } from '../components/Chrome'
import { useApi } from '../hooks/useApi'
import { api } from '../services/api'

const pct = (value?: number) => `${((value ?? 0) * 100).toFixed(1)}%`
const ms = (value: number | null | undefined) => value == null ? '—' : value < 1000 ? `${value.toFixed(0)} ms` : `${(value/1000).toFixed(2)} s`
const usd = (value: number | null | undefined) => value == null ? 'Unavailable' : `$${value.toFixed(2)}`

export function Overview() {
  const { data: runs, error } = useApi(api.runs)
  if (error) return <ErrorBox message={error}/>
  const latest = runs?.[0], previous = runs?.[1], m = latest?.metrics
  const delta = latest && previous ? latest.metrics.pass_rate - previous.metrics.pass_rate : 0
  const metricCards = [
    ['Current quality', pct(m?.quality_score), 'Composite rules'], ['Pass rate', pct(m?.pass_rate), delta ? `${delta > 0 ? '+' : ''}${pct(delta)} vs previous` : 'No prior comparison'],
    ['Average latency', ms(m?.average_latency_ms), `P95 ${ms(m?.p95_latency_ms)}`], ['Cost / 1K', usd(m?.cost_per_1k), latest?.is_mock ? 'Offline provider' : 'Provider reported'],
    ['Total evaluations', String(m?.total_evaluations ?? 0), `${m?.error_count ?? 0} execution errors`], ['Failure rate', pct(m?.failure_rate), `${Object.keys(m?.failures_by_category ?? {}).length} failure classes`],
  ]
  const points = runs?.flatMap(run => Object.entries(run.metrics.models).map(([label, model]) => ({ label, cost: (model.cost_per_request ?? 0) * 1000, quality: model.pass_rate, latency: model.p95_latency_ms ?? 0 }))) ?? []
  return <>
    <PageHeader title="Quality overview" description="A live read on product quality, speed, and evaluation cost." action={<a className="button" href="#/runs">Inspect latest run <ChevronRight size={15}/></a>}/>
    {!latest ? <Empty message="No evaluations yet. Run `evalbench run` or seed the demo to populate this workspace."/> : <>
      <div className="mb-5 flex items-center gap-3 rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm">
        <span className={`h-2.5 w-2.5 rounded-full ${delta <= -.05 ? 'bg-red-500' : 'bg-emerald-500'}`}/><span className="font-medium">{delta <= -.05 ? 'Regression threshold exceeded' : 'No confirmed regression'}</span>
        <span className="text-slate-400">•</span><span className="text-slate-500">Latest: {latest.name}</span>{latest.is_mock && <span className="badge ml-auto bg-amber-100 text-amber-800">Offline demo</span>}
      </div>
      <section className="panel mb-6 grid divide-y divide-slate-200 sm:grid-cols-2 sm:divide-x sm:divide-y-0 xl:grid-cols-6">
        {metricCards.map(([label, value, note], index) => <div className={`p-4 ${index >= 2 ? 'sm:border-t xl:border-t-0' : ''}`} key={label}><div className="metric-label">{label}</div><div className="mt-2 text-xl font-semibold tracking-tight">{value}</div><div className="mt-1 flex items-center gap-1 text-[11px] text-slate-500">{label === 'Pass rate' && delta !== 0 && (delta > 0 ? <ArrowUpRight className="text-emerald-600" size={12}/> : <ArrowDownRight className="text-red-600" size={12}/>)}{note}</div></div>)}
      </section>
      <div className="grid gap-6 xl:grid-cols-[1.5fr_1fr]">
        <section className="panel p-5"><div className="mb-5 flex justify-between"><div><h2 className="panel-title">Quality trend</h2><p className="mt-1 text-xs text-slate-500">Pass rate across completed runs</p></div><span className="text-xs text-slate-400">Last {runs?.length} runs</span></div><Sparkline values={[...(runs ?? [])].reverse().map(run => run.metrics.pass_rate)}/></section>
        <section className="panel p-5"><h2 className="panel-title">Cost / quality frontier</h2><p className="mb-4 mt-1 text-xs text-slate-500">Configuration-level trade-off</p><Tradeoff points={points}/></section>
        <section className="panel p-5"><h2 className="panel-title">Latency trend</h2><p className="mt-1 text-xs text-slate-500">P95 response latency in milliseconds</p><Sparkline color="#4f46e5" values={[...(runs ?? [])].reverse().map(run => run.metrics.p95_latency_ms ?? 0)}/></section>
        <section className="panel overflow-hidden"><div className="border-b border-slate-200 px-5 py-4"><h2 className="panel-title">Recent runs</h2></div>{runs?.slice(0,4).map(run => <a href={`#/runs/${run.id}`} className="flex items-center gap-3 border-b border-slate-100 px-5 py-3.5 last:border-0 hover:bg-slate-50" key={run.id}><span className={`h-2 w-2 rounded-full ${run.metrics.pass_rate < .9 ? 'bg-amber-500' : 'bg-emerald-500'}`}/><div className="min-w-0 flex-1"><div className="truncate text-sm font-medium">{run.name}</div><div className="text-[11px] text-slate-500">{new Date(run.created_at).toLocaleString()}</div></div><span className="text-sm font-semibold">{pct(run.metrics.pass_rate)}</span></a>)}</section>
      </div>
    </>}
  </>
}

