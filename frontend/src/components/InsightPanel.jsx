import { LayoutDashboard, X } from 'lucide-react'
import GapAlert from './GapAlert'
import TopicCard from './TopicCard'

function Stat({ label, value, tone }) {
  return (
    <div className={`rounded-2xl p-3 transition-transform duration-300 hover:-translate-y-0.5 ${tone}`}>
      <p className="font-display text-3xl font-semibold leading-none">{value}</p>
      <p className="mt-1.5 text-xs font-medium text-ink/80">{label}</p>
    </div>
  )
}

export default function InsightPanel({
  insights,
  gaps,
  topics,
  evidenceGapId,
  onViewEvidence,
  onOpenDashboard,
  onClose,
  className = '',
}) {
  return (
    <aside className={`min-h-0 flex-col gap-4 overflow-y-auto border-l border-white/50 bg-white/30 p-4 ${className}`}>
      <div className="flex items-center justify-between">
        <h2 className="font-display text-xl font-semibold">Insights</h2>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close insights"
          className="flex h-9 w-9 items-center justify-center rounded-xl text-moss transition-colors duration-300 hover:bg-sky hover:text-ink xl:hidden"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      <div className="grid grid-cols-2 gap-2.5">
        <Stat label="Questions" value={insights.questions} tone="bg-sky/60" />
        <Stat label="Unanswered" value={insights.unanswered} tone="bg-blush/70" />
        <Stat label="Requests" value={insights.requests} tone="bg-mint" />
        <Stat label="Unresolved topics" value={insights.unresolvedTopics} tone="bg-cream" />
      </div>

      <section aria-labelledby="gaps-heading" className="space-y-2.5">
        <h3 id="gaps-heading" className="font-display text-base font-semibold">
          Communication gaps
        </h3>
        {gaps.length === 0 ? (
          <p className="rounded-2xl bg-white/60 p-4 text-sm text-moss">
            No gaps found. Keep chatting, or replay the conversation to watch the agents work.
          </p>
        ) : (
          gaps.map((g) => (
            <GapAlert key={g.id} gap={g} active={g.id === evidenceGapId} onViewEvidence={onViewEvidence} />
          ))
        )}
      </section>

      {topics.length > 0 && (
        <section aria-labelledby="topics-heading" className="space-y-2.5">
          <h3 id="topics-heading" className="font-display text-base font-semibold">
            Topics
          </h3>
          <ul className="space-y-1.5">
            {topics.map((t) => (
              <TopicCard key={t.key} topic={t} />
            ))}
          </ul>
        </section>
      )}

      <button
        type="button"
        onClick={onOpenDashboard}
        className="mt-auto flex items-center justify-center gap-2 rounded-2xl bg-blush px-4 py-2.5 text-sm font-semibold text-ink transition-all duration-300 hover:bg-moss hover:text-cream"
      >
        <LayoutDashboard className="h-4 w-4" />
        Open full dashboard
      </button>
    </aside>
  )
}
