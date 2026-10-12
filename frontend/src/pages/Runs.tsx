import { ArrowLeft, GitCompare, Search } from 'lucide-react'
import { Empty, ErrorBox, PageHeader } from '../components/Chrome'
import { useApi } from '../hooks/useApi'
import { api } from '../services/api'
import type { Run as EvalRun } from '../types'

const pct = (n: number) => `${(n*100).toFixed(1)}%`
export function Runs({ id }: { id?: string }) {
  const { data, error } = useApi<EvalRun | EvalRun[]>(() => id ? api.run(id) : api.runs(), [id])
  if (error) return <ErrorBox message={error}/>
  if (id) {
    const run = data as EvalRun | null
    if (!run) return <Empty message="Loading run…"/>
    const m = run.metrics
    return <><a href="#/runs" className="mb-5 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-900"><ArrowLeft size={15}/>All runs</a>
      <PageHeader title={run.name} description={`${run.dataset?.name ?? 'Dataset'} · ${run.dataset?.version ?? ''}`} action={<a href={`#/compare?current=${id}`} className="button-secondary"><GitCompare size={15}/>Compare with previous</a>}/>
      <div className="panel mb-6 grid grid-cols-2 divide-x divide-y divide-slate-200 lg:grid-cols-5 lg:divide-y-0">{[['Pass rate', pct(m.pass_rate)], ['Quality', pct(m.quality_score)], ['P95 latency', m.p95_latency_ms == null ? '—' : `${m.p95_latency_ms.toFixed(1)} ms`], ['Cost / 1K', m.cost_per_1k == null ? '—' : `$${m.cost_per_1k.toFixed(2)}`], ['Failures', String(Math.round(m.failure_rate*m.completed))]].map(([label,value]) => <div className="p-5" key={label}><div className="metric-label">{label}</div><div className="mt-2 text-xl font-semibold">{value}</div></div>)}</div>
      <div className="grid gap-6 lg:grid-cols-2"><section className="panel p-5"><h2 className="panel-title mb-4">Run provenance</h2><dl className="space-y-3 text-sm">{[['Run ID',run.id],['Commit',run.git_sha ?? 'Not captured'],['Status',run.status],['Mode',run.is_mock ? 'Mock Provider / Offline Demo' : 'Production provider'],['Started',new Date(run.created_at).toLocaleString()]].map(([k,v])=><div className="grid grid-cols-[110px_1fr]" key={k}><dt className="text-slate-500">{k}</dt><dd className="break-all font-mono text-xs">{v}</dd></div>)}</dl></section>
      <section className="panel overflow-hidden"><div className="border-b border-slate-200 px-5 py-4"><h2 className="panel-title">Failure distribution</h2></div>{Object.entries(m.failures_by_category).length ? Object.entries(m.failures_by_category).sort((a,b)=>b[1]-a[1]).map(([name,count])=><a href={`#/failures?run=${id}&category=${name}`} key={name} className="flex justify-between border-b border-slate-100 px-5 py-3 text-sm last:border-0 hover:bg-slate-50"><span className="capitalize">{name.replaceAll('_',' ')}</span><span className="font-semibold">{count}</span></a>):<Empty message="No scored failures in this run."/>}</section></div>
    </>
  }
  const runs = data as EvalRun[] | null
  return <><PageHeader title="Evaluation runs" description="Reproducible quality snapshots across commits and configurations." action={<button className="button">New evaluation</button>}/>
    <div className="panel overflow-hidden"><div className="flex items-center border-b border-slate-200 p-3"><Search size={15} className="ml-1 text-slate-400"/><input className="w-full px-3 py-1 text-sm" placeholder="Search runs, commits, datasets…"/></div>
    {!runs?.length ? <Empty message="No runs yet."/> : <div className="overflow-x-auto"><table className="w-full min-w-[850px] text-left text-sm"><thead className="bg-slate-50 text-[11px] uppercase tracking-wide text-slate-500"><tr>{['Run','Status','Dataset','Pass rate','P95 latency','Evaluations','Created'].map(h=><th className="px-5 py-3 font-medium" key={h}>{h}</th>)}</tr></thead><tbody>{runs.map(run=><tr className="border-t border-slate-100 hover:bg-slate-50" key={run.id}><td className="px-5 py-4"><a className="font-medium text-slate-950 hover:underline" href={`#/runs/${run.id}`}>{run.name}</a><div className="mt-0.5 font-mono text-[10px] text-slate-400">{run.id.slice(0,8)} · {run.git_sha?.slice(0,7) ?? 'no commit'}</div></td><td className="px-5"><span className="badge bg-emerald-50 text-emerald-700">{run.status}</span></td><td className="px-5 text-slate-600">{run.dataset_version}</td><td className="px-5 font-semibold">{pct(run.metrics.pass_rate)}</td><td className="px-5 text-slate-600">{run.metrics.p95_latency_ms?.toFixed(1) ?? '—'} ms</td><td className="px-5 text-slate-600">{run.metrics.total_evaluations}</td><td className="px-5 text-slate-500">{new Date(run.created_at).toLocaleDateString()}</td></tr>)}</tbody></table></div>}</div></>
}
