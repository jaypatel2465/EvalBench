export function Sparkline({ values, color = '#0f766e' }: { values: number[]; color?: string }) {
  if (values.length < 2) return <div className="h-24 grid place-items-center text-xs text-slate-400">More runs needed</div>
  const min = Math.min(...values), max = Math.max(...values), span = max - min || 1
  const points = values.map((v, i) => `${(i / (values.length - 1)) * 100},${90 - ((v - min) / span) * 70}`).join(' ')
  return <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="h-24 w-full" role="img" aria-label="Metric trend"><polyline fill="none" stroke={color} strokeWidth="2" vectorEffect="non-scaling-stroke" points={points}/>{values.map((v, i) => <circle key={i} cx={(i/(values.length-1))*100} cy={90-((v-min)/span)*70} r="1.4" fill={color}/>)}</svg>
}

export function Tradeoff({ points }: { points: { label: string; cost: number; quality: number; latency: number }[] }) {
  if (!points.length) return <div className="h-64 grid place-items-center text-xs text-slate-400">Cost data unavailable</div>
  const maxCost = Math.max(...points.map(p => p.cost), .000001)
  return <div className="relative h-64 border-b border-l border-slate-200">
    <span className="absolute -left-1 top-0 -translate-x-full text-[10px] text-slate-400">Quality ↑</span><span className="absolute bottom-[-24px] right-0 text-[10px] text-slate-400">Cost →</span>
    {points.map(point => <div key={point.label} className="group absolute -translate-x-1/2 translate-y-1/2" style={{ left: `${10 + (point.cost/maxCost)*80}%`, bottom: `${10 + point.quality*80}%` }}>
      <span className="block h-3 w-3 rounded-full bg-teal-600 ring-4 ring-teal-100"/><span className="absolute left-4 top-[-3px] whitespace-nowrap text-[10px] font-medium text-slate-700">{point.label}</span>
    </div>)}
  </div>
}

