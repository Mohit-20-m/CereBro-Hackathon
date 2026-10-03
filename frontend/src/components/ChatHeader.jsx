import { ArrowLeft, PanelRight, Play, RefreshCw, Square, TriangleAlert } from 'lucide-react'
import Avatar from './Avatar'

function AnalysisPill({ analysis, onRetry }) {
  if (!analysis) return null
  if (analysis.status === 'running' || analysis.status === 'queued') {
    return (
      <span className="flex items-center gap-1.5 rounded-full bg-mint px-2.5 py-1 text-[11px] font-semibold text-moss" role="status">
        <span className="flex gap-0.5" aria-hidden="true">
          {[0, 1, 2].map((i) => (
            <span key={i} className="h-1.5 w-1.5 animate-dot rounded-full bg-moss" style={{ animationDelay: `${i * 0.18}s` }} />
          ))}
        </span>
        {analysis.status === 'queued' ? 'Waiting for agents' : analysis.stage || 'Agents analyzing'}
      </span>
    )
  }
  if (analysis.status === 'error') {
    return (
      <button
        type="button"
        onClick={onRetry}
        title={analysis.error || 'Analysis failed'}
        className="flex items-center gap-1.5 rounded-full bg-blush px-2.5 py-1 text-[11px] font-semibold text-coral transition-colors duration-300 hover:bg-coral hover:text-white"
      >
        <TriangleAlert className="h-3.5 w-3.5" />
        Analysis failed, retry
      </button>
    )
  }
  return null
}

export default function ChatHeader({
  conv,
  typingName,
  replaying,
  gapCount,
  onBack,
  onReplay,
  onStop,
  onReanalyze,
  onToggleInsights,
}) {
  const hasMessages = conv.messages.length > 0
  const working = ['running', 'queued'].includes(conv.analysis?.status)

  return (
    <header className="flex items-center gap-3 border-b border-white/50 bg-white/40 px-4 py-3">
      <button
        type="button"
        onClick={onBack}
        aria-label="Back to chats"
        className="flex h-9 w-9 items-center justify-center rounded-xl text-moss transition-colors duration-300 hover:bg-sky hover:text-ink lg:hidden"
      >
        <ArrowLeft className="h-5 w-5" />
      </button>
      <Avatar name={conv.name} group={conv.type === 'group'} size="lg" />
      <div className="min-w-0 flex-1">
        <div className="flex min-w-0 items-center gap-2">
          <h2 className="truncate font-display text-lg font-semibold leading-tight">{conv.name}</h2>
          <AnalysisPill analysis={conv.analysis} onRetry={onReanalyze} />
        </div>
        <p className="truncate text-xs text-moss" aria-live="polite">
          {typingName ? (
            <span className="font-medium text-ink">{typingName} is typing…</span>
          ) : (
            conv.members.join(', ') || 'No members yet'
          )}
        </p>
      </div>

      <button
        type="button"
        onClick={onReanalyze}
        disabled={working}
        aria-label="Run the agents again"
        title="Run the agents again"
        className="hidden h-10 w-10 items-center justify-center rounded-xl bg-white/70 text-moss transition-colors duration-300 hover:bg-sky hover:text-ink disabled:cursor-not-allowed disabled:opacity-50 sm:flex"
      >
        <RefreshCw className={`h-4 w-4 ${working ? 'animate-spin' : ''}`} />
      </button>

      {hasMessages &&
        (replaying ? (
          <button
            type="button"
            onClick={onStop}
            className="flex items-center gap-2 rounded-2xl bg-blush px-4 py-2 text-sm font-semibold text-ink transition-all duration-300 hover:bg-coral hover:text-white"
          >
            <Square className="h-4 w-4" />
            <span className="hidden sm:inline">Stop replay</span>
          </button>
        ) : (
          <button
            type="button"
            onClick={onReplay}
            className="flex items-center gap-2 rounded-2xl bg-moss px-4 py-2 text-sm font-semibold text-cream transition-all duration-300 hover:-translate-y-0.5 hover:bg-sky hover:text-ink hover:shadow-md"
          >
            <Play className="h-4 w-4" />
            <span className="hidden sm:inline">Replay conversation</span>
            <span className="sm:hidden">Replay</span>
          </button>
        ))}

      <button
        type="button"
        onClick={onToggleInsights}
        aria-label="Open insights"
        className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-white/70 text-moss transition-colors duration-300 hover:bg-sky hover:text-ink xl:hidden"
      >
        <PanelRight className="h-5 w-5" />
        {gapCount > 0 && (
          <span className="absolute -right-1 -top-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-coral px-1 text-[11px] font-semibold text-white">
            {gapCount}
          </span>
        )}
      </button>
    </header>
  )
}
