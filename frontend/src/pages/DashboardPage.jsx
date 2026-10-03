import { Bot } from 'lucide-react'
import GapAlert from '../components/GapAlert'
import StatusBanner from '../components/StatusBanner'
import TopicCard from '../components/TopicCard'
import { getSignals, severityThresholds } from '../utils/analysis'

function Stat({ label, value, tone }) {
  return (
    <div className={`rounded-2xl p-4 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-md ${tone}`}>
      <p className="font-display text-4xl font-semibold leading-none">{value}</p>
      <p className="mt-2 text-sm font-medium text-ink/80">{label}</p>
    </div>
  )
}

const agentTone = {
  'Language Analyzer': 'bg-sky/60',
  'Intent Analyzer': 'bg-mint',
  'Topic Analyzer': 'bg-sage/70',
  'Response Matcher': 'bg-cream',
  Investigator: 'bg-blush/70',
  'Gap Detector': 'bg-sky/40',
  Critic: 'bg-blush',
  'Evidence Generator': 'bg-mint',
  Orchestrator: 'bg-white/80',
}

const short = (name) => (name ? name.split('/').pop() : null)

function modelLine(ai) {
  if (ai.mode === 'heuristic') return 'Rule-based mode (models not loaded)'
  const parts = [`Embeddings ${short(ai.embedModel)}`]
  if (ai.nliModel) parts.push(`NLI ${short(ai.nliModel)}`)
  if (ai.llmActive) parts.push(`LLM ${ai.llmModel}`)
  return parts.join(', ')
}

function AgentActivity({ conv, health }) {
  const trace = conv.agentTrace || []
  const ai = health?.ai
  return (
    <section aria-labelledby="dash-agents" className="rounded-3xl bg-white/60 p-6">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 id="dash-agents" className="flex items-center gap-2 font-display text-xl font-semibold">
          <Bot className="h-5 w-5 text-moss" />
          Agent activity
        </h2>
        {ai && <p className="text-xs text-moss">{modelLine(ai)}</p>}
      </div>
      <p className="mt-1 max-w-prose text-sm text-moss">
        What each agent did in the latest LangGraph run for this conversation, in order.
      </p>
      {trace.length === 0 ? (
        <p className="mt-4 rounded-2xl bg-cream/70 p-4 text-sm text-moss">The agents haven't run on this conversation yet.</p>
      ) : (
        <ol className="mt-4 max-h-96 space-y-1.5 overflow-y-auto pr-1">
          {trace.map((t, i) => (
            <li key={`${t.t}-${i}`} className="flex items-start gap-3 rounded-xl bg-white/70 px-3 py-2 text-sm">
              <span className={`shrink-0 rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${agentTone[t.agent] || 'bg-white'}`}>
                {t.agent}
              </span>
              <span className="min-w-0 leading-snug">{t.text}</span>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}

export default function DashboardPage({ convo, onViewEvidence }) {
  const { conversations, active, activeId, insights, gaps, topics, selectConversation, online, health } = convo
  const signals = getSignals()
  const th = severityThresholds()

  if (!active) {
    return (
      <main className="flex min-w-0 flex-1 flex-col">
        <StatusBanner online={online} health={health} />
        <div className="flex flex-1 items-center justify-center p-8 text-center text-moss">
          {conversations.length ? 'Loading conversation…' : 'No conversations yet. Create or import one from the chat screen.'}
        </div>
      </main>
    )
  }

  const stats = [
    ['Messages', insights.messages, 'bg-sky/60'],
    ['Questions', insights.questions, 'bg-mint'],
    ['Answered', insights.answered, 'bg-sage/70'],
    ['Unanswered', insights.unanswered, 'bg-blush/70'],
    ['Requests', insights.requests, 'bg-cream'],
    ['Clarification loops', insights.loops, 'bg-blush/50'],
    ['Resolved topics', insights.resolvedTopics, 'bg-mint'],
    ['Pending topics', insights.pendingTopics, 'bg-cream'],
    ['Unresolved topics', insights.unresolvedTopics, 'bg-sky/40'],
    ['Code-mixed messages', active.insights?.codeMixed ?? 0, 'bg-sage/50'],
  ]

  return (
    <main className="flex min-w-0 flex-1 flex-col overflow-hidden">
      <StatusBanner online={online} health={health} />
      <div className="min-h-0 flex-1 overflow-y-auto p-4 sm:p-8">
        <div className="mx-auto max-w-5xl space-y-8">
          <header className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <h1 className="font-display text-3xl font-semibold tracking-tight sm:text-4xl">Communication dashboard</h1>
              <p className="mt-1 text-moss">What was said, and what was left unanswered in {active.name}.</p>
            </div>
            <div role="tablist" aria-label="Choose a conversation" className="flex max-w-full flex-wrap gap-1.5 rounded-2xl bg-white/50 p-1.5">
              {conversations.map((g) => (
                <button
                  key={g.id}
                  role="tab"
                  type="button"
                  aria-selected={g.id === activeId}
                  onClick={() => selectConversation(g.id)}
                  className={`rounded-xl px-3.5 py-2 text-sm font-semibold transition-all duration-300 ${
                    g.id === activeId ? 'bg-moss text-cream shadow' : 'text-moss hover:bg-sky hover:text-ink'
                  }`}
                >
                  {g.name}
                </button>
              ))}
            </div>
          </header>

          <section aria-label="Summary" className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
            {stats.map(([label, value, tone]) => (
              <Stat key={label} label={label} value={value} tone={tone} />
            ))}
          </section>

          <div className="grid gap-8 lg:grid-cols-5">
            <section aria-labelledby="dash-gaps" className="space-y-3 lg:col-span-3">
              <h2 id="dash-gaps" className="font-display text-xl font-semibold">
                Communication gaps
              </h2>
              {gaps.length === 0 ? (
                <p className="rounded-2xl bg-white/60 p-5 text-sm text-moss">No gaps in this conversation.</p>
              ) : (
                <div className="grid gap-3 sm:grid-cols-2">
                  {gaps.map((g) => (
                    <GapAlert key={g.id} gap={g} onViewEvidence={onViewEvidence} />
                  ))}
                </div>
              )}
            </section>

            <section aria-labelledby="dash-topics" className="space-y-3 lg:col-span-2">
              <h2 id="dash-topics" className="font-display text-xl font-semibold">
                Topics
              </h2>
              {topics.length === 0 ? (
                <p className="rounded-2xl bg-white/60 p-5 text-sm text-moss">No topics detected yet.</p>
              ) : (
                <ul className="space-y-1.5">
                  {topics.map((t) => (
                    <TopicCard key={t.key} topic={t} />
                  ))}
                </ul>
              )}
            </section>
          </div>

          <AgentActivity conv={active} health={health} />

          <section aria-labelledby="dash-score" className="rounded-3xl bg-white/60 p-6">
            <h2 id="dash-score" className="font-display text-xl font-semibold">
              How gap scores work
            </h2>
            <p className="mt-1 max-w-prose text-sm text-moss">
              The models extract meaning; the Gap Detector adds up these signals into a score between 0 and 1. No model decides
              on its own that a gap exists, so every flag can be explained.
            </p>
            <div className="mt-4 grid gap-6 md:grid-cols-2">
              <ul className="space-y-2">
                {signals.map((s) => (
                  <li key={s.key} className="flex items-center justify-between rounded-xl bg-cream/70 px-4 py-2.5 text-sm">
                    <span className="font-medium">{s.label}</span>
                    <span className="font-display text-lg font-semibold">{s.weight.toFixed(2)}</span>
                  </li>
                ))}
              </ul>
              <ul className="space-y-2">
                <li className="flex items-center justify-between rounded-xl bg-mint px-4 py-2.5 text-sm">
                  <span className="font-medium">Normal</span>
                  <span>0.00 to {th.possible.toFixed(2)}</span>
                </li>
                <li className="flex items-center justify-between rounded-xl bg-cream px-4 py-2.5 text-sm ring-1 ring-amber/50">
                  <span className="font-medium">Possible gap</span>
                  <span>{th.possible.toFixed(2)} to {th.strong.toFixed(2)}</span>
                </li>
                <li className="flex items-center justify-between rounded-xl bg-coral px-4 py-2.5 text-sm text-white">
                  <span className="font-medium">Strong gap</span>
                  <span>{th.strong.toFixed(2)} to 1.00</span>
                </li>
              </ul>
            </div>
          </section>
        </div>
      </div>
    </main>
  )
}
