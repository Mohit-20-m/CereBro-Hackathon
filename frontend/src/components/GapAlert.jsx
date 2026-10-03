import { CircleCheck, TriangleAlert } from 'lucide-react'
import { SEVERITY_STYLES, gapLabel } from '../utils/analysis'

export default function GapAlert({ gap, active = false, onViewEvidence }) {
  return (
    <article
      className={`rounded-2xl bg-white/80 p-4 shadow-sm transition-all duration-300 hover:-translate-y-0.5 hover:shadow-md ${
        active ? 'ring-2 ring-coral' : ''
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="flex items-center gap-1.5 font-display text-base font-semibold leading-tight">
            {gap.resolved ? (
              <CircleCheck className="h-4 w-4 shrink-0 text-moss" />
            ) : (
              <TriangleAlert className="h-4 w-4 shrink-0 text-coral" />
            )}
            {gapLabel(gap.type)}
          </p>
          <p className="mt-1 text-sm font-medium">{gap.topic}</p>
          <p className="text-xs text-moss">Raised by {gap.raisedBy}</p>
        </div>
        <span className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-semibold ${SEVERITY_STYLES[gap.severity.key]}`}>
          {gap.severity.label}
        </span>
      </div>

      <div className="mt-3">
        <div className="mb-1 flex justify-between text-xs text-moss">
          <span>Confidence</span>
          <span className="font-semibold text-ink">{gap.confidence}%</span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-sage/60">
          <div
            className="h-full rounded-full bg-moss transition-all duration-700"
            style={{ width: `${gap.confidence}%` }}
          />
        </div>
      </div>

      <div className="mt-3 flex items-center justify-between gap-2">
        <span className={`text-xs font-semibold ${gap.resolved ? 'text-moss' : 'text-coral'}`}>
          {gap.resolved ? 'Resolved' : 'Unresolved'}
        </span>
        <button
          type="button"
          onClick={() => onViewEvidence(gap.id)}
          className="rounded-xl bg-moss px-3.5 py-1.5 text-sm font-semibold text-cream transition-all duration-300 hover:bg-sky hover:text-ink"
        >
          View evidence
        </button>
      </div>
    </article>
  )
}
