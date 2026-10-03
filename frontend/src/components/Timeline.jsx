import { ChevronRight } from 'lucide-react'
import { buildTimeline } from '../utils/analysis'

const tone = {
  question: 'bg-sky text-ink',
  unrelated: 'bg-mint text-ink',
  followup: 'bg-sage text-ink',
  repeat: 'bg-blush text-ink',
  deflection: 'bg-blush/60 text-ink',
  gap: 'bg-coral text-white',
  resolution: 'bg-cream text-ink ring-1 ring-moss/40',
  resolved: 'bg-moss text-cream',
}

export default function Timeline({ gap }) {
  const nodes = buildTimeline(gap)
  return (
    <ol className="flex flex-wrap items-center gap-y-2">
      {nodes.map((n, i) => (
        <li key={`${n.role}-${i}`} className="flex items-center">
          <span
            style={{ animationDelay: `${i * 110}ms` }}
            className={`animate-nodeIn rounded-full px-3 py-1.5 text-xs font-semibold ${tone[n.role]}`}
          >
            {n.label}
            {n.count > 1 ? ` ×${n.count}` : ''}
          </span>
          {i < nodes.length - 1 && <ChevronRight className="mx-0.5 h-4 w-4 text-moss" aria-hidden="true" />}
        </li>
      ))}
    </ol>
  )
}
