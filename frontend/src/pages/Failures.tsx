import { ChevronRight, Search, X } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Empty, ErrorBox, PageHeader } from '../components/Chrome'
import { useApi } from '../hooks/useApi'
import { api } from '../services/api'
import type { Failure } from '../types'

export function Failures({ params }: { params: URLSearchParams }) {
  const { data: runs } = useApi(api.runs)
  const initialRun = params.get('run')
  const [runId, setRunId] = useState(initialRun ?? '')
  const selectedRun = runId || runs?.[0]?.id || ''
  const { data, error } = useApi(() => selectedRun ? api.failures(selectedRun) : Promise.resolve([]), [selectedRun])
  const [search,setSearch]=useState('')
  const [category,setCategory]=useState(params.get('category') ?? '')
  const [detail,setDetail]=useState<Failure|null>(null)
  const failures = useMemo(()=>data?.filter(item => (!category || item.category===category) && (!search || `${item.input} ${item.response} ${item.test_case_id}`.toLowerCase().includes(search.toLowerCase()))) ?? [],[data,category,search])
  if (error) return <ErrorBox message={error}/>
  const categories=[...new Set(data?.map(item=>item.category) ?? [])]
  return <><PageHeader title="Failure explorer" description="Move from a failed metric to the exact evidence, output, and scoring decision."/>
    <div className="mb-4 flex flex-wrap gap-2"><select className="input" value={selectedRun} onChange={e=>setRunId(e.target.value)}>{runs?.map(run=><option key={run.id} value={run.id}>{run.name}</option>)}</select><div className="input flex min-w-[260px] items-center gap-2"><Search size={15} className="text-slate-400"/><input className="w-full" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search inputs or outputs"/></div><select className="input" value={category} onChange={e=>setCategory(e.target.value)}><option value="">All categories</option>{categories.map(item=><option value={item} key={item}>{item.replaceAll('_',' ')}</option>)}</select></div>
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(420px,.85fr)]"><section className="panel overflow-hidden">{!failures.length?<Empty message="No failures match these filters."/>:failures.map(item=><button onClick={()=>setDetail(item)} key={item.id} className={`flex w-full items-center gap-4 border-b border-slate-100 px-5 py-4 text-left last:border-0 hover:bg-slate-50 ${detail?.id===item.id?'bg-slate-50':''}`}><span className={`h-2 w-2 rounded-full ${item.severity==='high'?'bg-red-500':'bg-amber-500'}`}/><div className="min-w-0 flex-1"><div className="mb-1 flex items-center gap-2"><span className="font-mono text-[10px] text-slate-400">{item.test_case_id}</span><span className="badge bg-red-50 text-red-700">{item.category.replaceAll('_',' ')}</span></div><div className="truncate text-sm font-medium">{item.input}</div><div className="mt-1 truncate text-xs text-slate-500">{item.reason}</div></div><ChevronRight size={16} className="text-slate-300"/></button>)}</section>
      <FailureDetail item={detail ?? failures[0]}/></div></>
}

function FailureDetail({item}:{item?:Failure}) { if(!item)return <aside className="panel grid min-h-96 place-items-center text-sm text-slate-400">Select a failure</aside>
  return <aside className="panel max-h-[calc(100vh-145px)] overflow-y-auto"><div className="sticky top-0 flex items-center justify-between border-b border-slate-200 bg-white px-5 py-4"><div><div className="text-[10px] font-semibold uppercase tracking-wider text-red-600">{item.category.replaceAll('_',' ')}</div><h2 className="mt-1 font-semibold">{item.test_case_id} · {item.model}</h2></div><X size={16} className="text-slate-400"/></div><div className="space-y-6 p-5">{[['Input',item.input],['Expected behavior',item.expected_behavior],['Model output',item.response],['Reference answer',item.reference_answer]].map(([label,value])=><section key={label}><h3 className="metric-label mb-2">{label}</h3><div className={`rounded-md border p-3 text-sm leading-6 ${label==='Model output'?'border-red-100 bg-red-50/40':'border-slate-200 bg-slate-50/60'}`}>{value||'Unavailable'}</div></section>)}<section><h3 className="metric-label mb-2">Rule-based scores</h3><div className="space-y-2">{item.scores.map(score=><div key={score.scorer} className="flex items-start justify-between gap-4 rounded-md border border-slate-200 p-3 text-xs"><div><div className="font-medium">{score.scorer.replaceAll('_',' ')}</div><div className="mt-1 text-slate-500">{score.reason}</div></div><span className={`font-semibold ${score.passed?'text-emerald-600':'text-red-600'}`}>{(score.value*100).toFixed(0)}%</span></div>)}</div></section><section className="grid grid-cols-3 gap-3">{[['Latency',item.latency_ms==null?'—':`${item.latency_ms.toFixed(1)} ms`],['Tokens',String(item.total_tokens??'—')],['Cost',item.estimated_cost==null?'—':`$${item.estimated_cost.toFixed(5)}`]].map(([k,v])=><div key={k} className="rounded-md bg-slate-50 p-3"><div className="metric-label">{k}</div><div className="mt-1 text-sm font-semibold">{v}</div></div>)}</section></div></aside> }
