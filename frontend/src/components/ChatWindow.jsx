import { useEffect, useRef } from 'react'
import { CircleCheck, TriangleAlert } from 'lucide-react'
import MessageBubble, { TypingBubble } from './MessageBubble'

function GapNote({ gap, onView }) {
  const strong = gap.severity.key === 'strong'
  return (
    <div className="flex animate-pop justify-center">
      <div
        className={`flex max-w-full flex-wrap items-center justify-center gap-x-3 gap-y-1 rounded-2xl px-4 py-2 text-sm shadow-sm ${
          strong ? 'bg-blush text-ink' : 'bg-cream text-ink ring-1 ring-amber/50'
        }`}
      >
        <TriangleAlert className="h-4 w-4 shrink-0 text-coral" />
        <span className="font-medium">
          {strong ? 'Communication gap' : 'Possible communication gap'}: {gap.topic}
        </span>
        <button
          type="button"
          onClick={() => onView(gap.id)}
          className="rounded-full bg-moss px-3 py-1 text-xs font-semibold text-cream transition-colors duration-300 hover:bg-sky hover:text-ink"
        >
          View evidence
        </button>
      </div>
    </div>
  )
}

function ResolvedNote({ gap }) {
  return (
    <div className="flex animate-pop justify-center">
      <div className="flex items-center gap-2 rounded-2xl bg-mint px-4 py-2 text-sm font-medium text-moss shadow-sm">
        <CircleCheck className="h-4 w-4" />
        Gap resolved: {gap.topic}
      </div>
    </div>
  )
}

export default function ChatWindow({ conv, messages, gaps, evidenceGap, typingName, onViewEvidence }) {
  const endRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages.length, typingName, gaps.length])

  const flagged = new Set(gaps.flatMap((g) => g.evidence.map((e) => e.id)))
  const highlighted = new Set(evidenceGap ? evidenceGap.evidence.map((e) => e.id) : [])

  if (messages.length === 0 && !typingName) {
    return (
      <div className="flex flex-1 items-center justify-center px-8 text-center">
        <div className="max-w-xs">
          <p className="font-display text-xl font-semibold">
            {conv.messages.length ? 'Replay starting' : 'No messages yet'}
          </p>
          <p className="mt-2 text-sm text-moss">
            {conv.messages.length
              ? 'Messages will arrive one by one, and gaps appear as the agents found them.'
              : 'Pick who you are typing as, then send a message. The agents analyze every new message.'}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-0 flex-1 space-y-3 overflow-y-auto px-4 py-5 sm:px-6" role="log" aria-live="polite">
      {messages.map((m) => (
        <div key={m.id} className="space-y-3">
          <MessageBubble msg={m} flagged={flagged.has(m.id)} highlighted={highlighted.has(m.id)} />
          {gaps
            .filter((g) => g.latestAt === m.id)
            .map((g) => (
              <GapNote key={`${g.id}-${m.id}`} gap={g} onView={onViewEvidence} />
            ))}
          {gaps
            .filter((g) => g.resolved && g.resolvedAt === m.id)
            .map((g) => (
              <ResolvedNote key={`${g.id}-done`} gap={g} />
            ))}
        </div>
      ))}
      {typingName && <TypingBubble name={typingName} />}
      <div ref={endRef} />
    </div>
  )
}
