import { useState } from 'react'
import { TriangleAlert } from 'lucide-react'
import Avatar from './Avatar'

export default function MessageBubble({ msg, flagged, highlighted }) {
  const [showMeaning, setShowMeaning] = useState(false)
  const mine = Boolean(msg.mine)
  const ring = highlighted ? 'ring-2 ring-coral' : flagged ? 'ring-2 ring-blush' : ''

  return (
    <div id={`msg-${msg.id}`} className={`flex animate-pop items-end gap-2 ${mine ? 'justify-end' : 'justify-start'}`}>
      {!mine && <Avatar name={msg.sender} size="sm" />}
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-2.5 shadow-sm transition-shadow duration-300 hover:shadow-md md:max-w-[62%] ${msg.pending ? 'opacity-70' : ''} ${
          mine ? 'rounded-br-md bg-sky' : 'rounded-bl-md bg-white/90'
        } ${ring}`}
      >
        {!mine && <p className="mb-0.5 text-xs font-semibold text-moss">{msg.sender}</p>}
        {mine && msg.sender && <p className="mb-0.5 text-xs font-semibold text-ink/70">{msg.sender}</p>}
        <p className="whitespace-pre-wrap break-words text-[15px] leading-snug">{msg.text}</p>
        {msg.normalized && showMeaning && (
          <p className="mt-1.5 border-t border-sage pt-1.5 text-xs italic text-moss">Read as: {msg.normalized}</p>
        )}
        <div className="mt-1 flex items-center justify-end gap-2 text-[11px] text-moss">
          {msg.lang && msg.normalized && (
            <button
              type="button"
              onClick={() => setShowMeaning((v) => !v)}
              aria-pressed={showMeaning}
              title="Show how the agents read this message"
              className="rounded-full bg-mint px-2 py-0.5 font-medium transition-colors duration-300 hover:bg-sky hover:text-ink"
            >
              {msg.lang} {showMeaning ? '(hide)' : '(read as)'}
            </button>
          )}
          {msg.lang && !msg.normalized && <span className="rounded-full bg-mint px-2 py-0.5 font-medium">{msg.lang}</span>}
          {flagged && <TriangleAlert className="h-3.5 w-3.5 text-coral" aria-label="Part of a communication gap" />}
          <span>{msg.pending ? 'Sending…' : msg.time}</span>
        </div>
      </div>
    </div>
  )
}

export function TypingBubble({ name }) {
  return (
    <div className="flex animate-fadeIn items-end gap-2" role="status" aria-label={`${name} is typing`}>
      <Avatar name={name} size="sm" />
      <div className="flex items-center gap-1.5 rounded-2xl rounded-bl-md bg-white/90 px-4 py-3.5 shadow-sm">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="h-2 w-2 animate-dot rounded-full bg-moss"
            style={{ animationDelay: `${i * 0.18}s` }}
          />
        ))}
      </div>
    </div>
  )
}
