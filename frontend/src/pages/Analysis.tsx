import { AlertCircle, CheckCircle2, Info } from 'lucide-react'
import { Tradeoff } from '../components/Charts'
import { Empty, ErrorBox, PageHeader } from '../components/Chrome'
import { useApi } from '../hooks/useApi'
import { api } from '../services/api'

export function Compare({ params }: { params: URLSearchParams }) {
  const { data: runs, error } = useApi(api.runs)
  const selected = params.get('current')
  const ids = selected ? [selected, ...((runs ?? []).filter(r=>r.id!==selected).slice(0,2).map(r=>r.id))] : (runs ?? []).slice(0,4).map(r=>r.id)
  const { data } = useApi(() => ids.length ? api.comparisons(ids) : Promise.resolve({runs:[]}), [ids.join(',')])
  if(error)return <ErrorBox message={error}/>
  const rows=data?.runs ?? []
  const points=rows.flatMap(entry=>Object.entries(entry.metrics.models).map(([label,m])=>({label,cost:(m.cost_per_request??0)*1000,quality:m.pass_rate,latency:m.p95_latency_ms??0})))
  return <><PageHeader title="Model comparison" description="Compare quality, cost, and latency without collapsing trade-offs into one score."/>
    {!rows.length?<Empty message="At least one completed run is needed for comparison."/>:<><section className="panel mb-6 overflow-x-auto"><table className="w-full min-w-[760px] text-sm"><thead><tr className="border-b border-slate-200 bg-slate-50"><th className="px-5 py-3 text-left text-[11px] uppercase tracking-wide text-slate-500">Metric</th>{rows.map(item=><th key={item.run.id} className="px-5 py-3 text-right font-medium">{item.run.name}</th>)}</tr></thead><tbody>{[
      ['Pass rate',(m:typeof rows[number]['metrics'])=>`${(m.pass_rate*100).toFixed(1)}%`],['Quality score',(m:typeof rows[number]['metrics'])=>`${(m.quality_score*100).toFixed(1)}%`],
      ['P95 latency',(m:typeof rows[number]['metrics'])=>m.p95_latency_ms==null?'—':`${m.p95_latency_ms.toFixed(1)} ms`],['Cost / 1K',(m:typeof rows[number]['metrics'])=>m.cost_per_1k==null?'Unavailable':`$${m.cost_per_1k.toFixed(2)}`],
      ['Evaluations',(m:typeof rows[number]['metrics'])=>String(m.total_evaluations)],['Failure rate',(m:typeof rows[number]['metrics'])=>`${(m.failure_rate*100).toFixed(1)}%`],
    ].map(([label,format])=><tr className="border-b border-slate-100 last:border-0" key={label as string}><td className="px-5 py-4 font-medium">{label as string}</td>{rows.map(item=><td className="px-5 py-4 text-right tabular-nums" key={item.run.id}>{(format as (m:typeof item.metrics)=>string)(item.metrics)}</td>)}</tr>)}</tbody></table></section>
      <section className="panel p-6"><h2 className="panel-title">Quality / cost frontier</h2><p className="mb-7 mt-1 text-xs text-slate-500">Each point is one model configuration from the selected runs.</p><Tradeoff points={points}/></section></>}
  </>
}

export function Regressions() {
  const {data:runs,error}=useApi(api.runs)
  const baseline=runs?.[1]?.id,current=runs?.[0]?.id
  const {data}=useApi(()=>baseline&&current?api.regressions(current,baseline):Promise.resolve([]),[baseline,current])
  if(error)return <ErrorBox message={error}/>
  const result=data?.[0] as Record<string,number|string|null>|undefined
  const cls=String(result?.classification??'insufficient_data')
  return <><PageHeader title="Regression analysis" description="Absolute thresholds plus bootstrap uncertainty around observed quality changes."/>
    {!result?<Empty message="Two completed runs are required to estimate a regression."/>:<div className="grid gap-6 lg:grid-cols-[1.3fr_.7fr]"><section className="panel p-6"><div className="mb-6 flex items-center gap-3">{cls==='regression_detected'?<AlertCircle className="text-red-600"/>:cls==='improvement'?<CheckCircle2 className="text-emerald-600"/>:<Info className="text-amber-600"/>}<div><div className="metric-label">Classification</div><div className="mt-1 text-lg font-semibold capitalize">{cls.replaceAll('_',' ')}</div></div></div><div className="grid grid-cols-2 gap-4 sm:grid-cols-4">{[['Baseline',`${(Number(result.baseline)*100).toFixed(1)}%`],['Current',`${(Number(result.current)*100).toFixed(1)}%`],['Difference',`${(Number(result.absolute_change)*100).toFixed(1)} pp`],['Samples',String(result.samples)]].map(([k,v])=><div className="rounded-md bg-slate-50 p-4" key={k}><div className="metric-label">{k}</div><div className="mt-2 text-lg font-semibold">{v}</div></div>)}</div><div className="mt-5 rounded-md border border-slate-200 p-4"><div className="metric-label">95% bootstrap interval</div><div className="mt-2 font-mono text-sm">[{result.ci_low==null?'unavailable':`${(Number(result.ci_low)*100).toFixed(1)} pp`}, {result.ci_high==null?'unavailable':`${(Number(result.ci_high)*100).toFixed(1)} pp`}]</div></div></section><aside className="panel p-6"><h2 className="panel-title">Interpretation</h2><p className="mt-3 text-sm leading-6 text-slate-600">A threshold crossing is operational evidence, not proof of causality. EvalBench labels intervals that overlap zero as inconclusive and keeps the raw paired work visible for review.</p><div className="mt-5 rounded-md bg-amber-50 p-3 text-xs leading-5 text-amber-900">Bootstrap intervals are unstable for small datasets. Segment-level conclusions need adequate cases per category.</div></aside></div>}
  </>
}

export function JudgeReliability() {
  const {data,error}=useApi(api.reliability)
  if(error)return <ErrorBox message={error}/>
  const n=Number(data?.samples??0)
  return <><PageHeader title="Judge reliability" description="Measure the judge against a human-rated validation subset before trusting it as a quality signal."/>
    {!n?<Empty message="No paired human and judge ratings yet. The demo corpus marks a validation subset; add reviewed human ratings to enable this analysis."/>:<><div className="panel mb-6 grid grid-cols-2 divide-x divide-slate-200 lg:grid-cols-5">{[['Agreement',Number(data?.exact_agreement)],['Disagreement',Number(data?.disagreement_rate)],['Mean abs. error',Number(data?.mean_absolute_error)],['Cohen’s κ',Number(data?.cohens_kappa)],['Mean bias',Number(data?.mean_bias)]].map(([k,v])=><div className="p-5" key={String(k)}><div className="metric-label">{String(k)}</div><div className="mt-2 text-xl font-semibold">{Number(v).toFixed(2)}</div></div>)}</div><section className="panel p-5"><h2 className="panel-title">Limitations</h2><p className="mt-2 text-sm text-slate-600">{String(data?.limitations)}</p>{Boolean(data?.insufficient_sample)&&<div className="mt-4 rounded-md bg-amber-50 p-3 text-xs text-amber-900">Fewer than 30 labeled examples: do not claim statistical significance.</div>}</section></>}
  </>
}

