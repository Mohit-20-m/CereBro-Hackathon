import { useEffect } from 'react'
import { Check, Minus, ShieldCheck, X } from 'lucide-react'
import Avatar from './Avatar'
import Timeline from './Timeline'
import { ROLE_LABELS, SEVERITY_STYLES, gapLabel, getSignals, severityThresholds } from '../utils/analysis'

const roleTone = {
  question: 'bg-sky',
  unrelated: 'bg-mint',
  followup: 'bg-sage',
  repeat: 'bg-blush',
  deflection: 'bg-blush/60',
  resolution: 'bg-cream ring-1 ring-moss/40',
}

export default function EvidencePanel({ gap, messages, onClose }) {
  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const byId = new Map(messages.map((m) => [m.id, m]))
  const signals = getSignals()
  const thresholds = severityThresholds()

  return (
    <div className="absolute inset-0 z-30 flex justify-end">
      <button
        type="button"
        aria-label="Close evidence"
        onClick={onClose}
        className="absolute inset-0 animate-fadeIn bg-ink/25"
      />
      <aside
        role="dialog"
        aria-label="Gap evidence"
        className="relative flex h-full w-full animate-slideIn flex-col gap-5 overflow-y-auto bg-cream p-5 shadow-2xl sm:w-[27rem]"
      >
        <header className="flex items-start justify-between gap-3">
          <div>
            <h2 className="font-display text-2xl font-semibold leading-tight">{gapLabel(gap.type)}</h2>
            <p className="mt-1 text-sm">
              <span className="font-semibold">{gap.topic}</span>, raised by {gap.raisedBy}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white/70 text-moss transition-colors duration-300 hover:bg-coral hover:text-white"
          >
            <X className="h-5 w-5" />
          </button>
        </header>

        <div className="flex flex-wrap gap-2">
          <span className={`rounded-full px-3 py-1 text-xs font-semibold ${SEVERITY_STYLES[gap.severity.key]}`}>
            {gap.severity.label}
          </span>
          <span
            className={`rounded-full px-3 py-1 text-xs font-semibold ${
              gap.resolved ? 'bg-mint text-moss' : 'bg-blush/70 text-coral'
            }`}
          >
            {gap.resolved ? 'Resolved' : 'Unresolved'}
          </span>
          <span className="rounded-full bg-white/80 px-3 py-1 text-xs font-semibold">Confidence {gap.confidence}%</span>
          {gap.isFinal && gap.critic?.verdict === 'confirmed' && (
            <span className="flex items-center gap-1 rounded-full bg-mint px-3 py-1 text-xs font-semibold text-moss" title={gap.critic.reason || ''}>
              <ShieldCheck className="h-3.5 w-3.5" />
              Critic confirmed
            </span>
          )}
        </div>

        {gap.isFinal && gap.summary && <p className="text-[15px] leading-relaxed">{gap.summary}</p>}

        <section aria-labelledby="why-heading" className="rounded-2xl bg-white/70 p-4">
          <h3 id="why-heading" className="font-display text-base font-semibold">
            Why this was flagged
          </h3>
          <ul className="mt-2 space-y-1.5">
            {gap.reasons.map((r) => (
              <li key={r} className="flex items-start gap-2 text-sm">
                <Check className="mt-0.5 h-4 w-4 shrink-0 text-moss" />
                {r}
              </li>
            ))}
          </ul>
        </section>

        <section aria-labelledby="evidence-heading" className="space-y-2.5">
          <h3 id="evidence-heading" className="font-display text-base font-semibold">
            Evidence from the conversation
          </h3>
          {gap.evidence.map((e) => {
            const m = byId.get(e.id)
            if (!m) return null
            return (
              <div key={e.id} className="rounded-2xl bg-white/80 p-3.5 transition-shadow duration-300 hover:shadow-md">
                <div className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-2 text-sm font-semibold">
                    <Avatar name={m.sender} size="sm" />
                    {m.sender}
                    <span className="text-xs font-normal text-moss">{m.time}</span>
                  </span>
                  <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${roleTone[e.role]}`}>
                    {ROLE_LABELS[e.role]}
                  </span>
                </div>
                <p className="mt-2 whitespace-pre-wrap text-[15px] leading-snug">“{m.text}”</p>
                {m.normalized && <p className="mt-1 text-xs italic text-moss">Read as: {m.normalized}</p>}
                {e.note && <p className="mt-1.5 text-xs text-moss">{e.note}</p>}
              </div>
            )
          })}
        </section>

        <section aria-labelledby="timeline-heading" className="space-y-2.5">
          <h3 id="timeline-heading" className="font-display text-base font-semibold">
            How the gap developed
          </h3>
          <Timeline gap={gap} />
        </section>

        <section aria-labelledby="score-heading" className="rounded-2xl bg-white/70 p-4">
          <div className="flex items-baseline justify-between">
            <h3 id="score-heading" className="font-display text-base font-semibold">
              Gap score
            </h3>
            <span className="font-display text-2xl font-semibold">{gap.score.toFixed(2)}</span>
          </div>
          <ul className="mt-2 space-y-1.5">
            {signals.map((s) => {
              const on = Boolean(gap.signals[s.key])
              return (
                <li key={s.key} className={`flex items-center justify-between text-sm ${on ? '' : 'text-moss/80'}`}>
                  <span className="flex items-center gap-2">
                    {on ? <Check className="h-4 w-4 text-moss" /> : <Minus className="h-4 w-4" />}
                    {s.label}
                  </span>
                  <span className={on ? 'font-semibold' : ''}>{on ? `+${s.weight.toFixed(2)}` : s.weight.toFixed(2)}</span>
                </li>
              )
            })}
          </ul>
          <div className="relative mt-3 h-2.5 overflow-hidden rounded-full bg-sage/60">
            <div
              className={`h-full rounded-full transition-all duration-700 ${
                gap.severity.key === 'strong' ? 'bg-coral' : 'bg-amber'
              }`}
              style={{ width: `${Math.min(gap.score, 1) * 100}%` }}
            />
          </div>
          <div className="mt-1 flex justify-between text-[11px] text-moss">
            <span>{thresholds.possible.toFixed(2)} possible</span>
            <span>{thresholds.strong.toFixed(2)} strong</span>
          </div>
        </section>
      </aside>
    </div>
  )
}
