import { useMemo, useState } from 'react'
import { FileUp, Plus, Search } from 'lucide-react'
import Avatar from './Avatar'

function Row({ conv, selected, onSelect }) {
  const last = conv.lastMessage
  const preview = last ? `${last.sender}: ${last.text}` : 'No messages yet'
  const analyzing = ['queued', 'running'].includes(conv.analysis?.status)

  return (
    <li>
      <button
        type="button"
        onClick={() => onSelect(conv.id)}
        aria-current={selected ? 'true' : undefined}
        className={`group flex w-full items-center gap-3 rounded-2xl px-3 py-2.5 text-left transition-all duration-300 hover:bg-mint hover:shadow-sm ${
          selected ? 'bg-white/90 shadow-sm' : ''
        }`}
      >
        <Avatar name={conv.name} group={conv.type === 'group'} />
        <span className="min-w-0 flex-1">
          <span className="flex items-baseline justify-between gap-2">
            <span className="truncate text-sm font-semibold">{conv.name}</span>
            <span className="shrink-0 text-[11px] text-moss">{last?.time}</span>
          </span>
          <span className="flex items-center justify-between gap-2">
            <span className="truncate text-xs text-moss">{analyzing ? 'Agents analyzing…' : preview}</span>
            {conv.openGaps > 0 && (
              <span
                className="flex h-5 min-w-5 shrink-0 items-center justify-center rounded-full bg-coral px-1.5 text-[11px] font-semibold text-white"
                title={`${conv.openGaps} open communication gap${conv.openGaps > 1 ? 's' : ''}`}
              >
                {conv.openGaps}
              </span>
            )}
          </span>
        </span>
      </button>
    </li>
  )
}

export default function ConversationList({ conversations, activeId, onSelect, onNewGroup, onImport, className = '' }) {
  const [query, setQuery] = useState('')
  const filtered = useMemo(
    () => conversations.filter((c) => c.name.toLowerCase().includes(query.trim().toLowerCase())),
    [conversations, query],
  )
  const groups = filtered.filter((c) => c.type === 'group')
  const people = filtered.filter((c) => c.type !== 'group')

  return (
    <aside className={`min-h-0 flex-col gap-3 border-r border-white/50 bg-white/30 p-4 ${className}`}>
      <div className="px-1">
        <h1 className="font-display text-2xl font-semibold tracking-tight">ANVAYA</h1>
        <p className="text-xs text-moss">Connecting context. Detecting gaps.</p>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <button
          type="button"
          onClick={onNewGroup}
          className="flex items-center justify-center gap-1.5 rounded-2xl bg-moss px-3 py-2 text-sm font-semibold text-cream transition-all duration-300 hover:bg-sky hover:text-ink"
        >
          <Plus className="h-4 w-4" />
          New group
        </button>
        <button
          type="button"
          onClick={onImport}
          className="flex items-center justify-center gap-1.5 rounded-2xl bg-white/80 px-3 py-2 text-sm font-semibold text-ink transition-all duration-300 hover:bg-blush"
        >
          <FileUp className="h-4 w-4" />
          Import chat
        </button>
      </div>
      <label className="relative block">
        <span className="sr-only">Search chats</span>
        <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-moss" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search chats"
          className="w-full rounded-2xl border border-transparent bg-white/80 py-2.5 pl-10 pr-4 text-sm placeholder:text-moss/80 transition-all duration-300 hover:bg-white focus:border-sky focus:bg-white focus:outline-none"
        />
      </label>

      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto pr-1">
        {groups.length > 0 && (
          <section aria-labelledby="groups-heading">
            <h2 id="groups-heading" className="mb-1 px-3 font-display text-sm font-semibold text-moss">
              Groups
            </h2>
            <ul className="space-y-0.5">
              {groups.map((c) => (
                <Row key={c.id} conv={c} selected={c.id === activeId} onSelect={onSelect} />
              ))}
            </ul>
          </section>
        )}
        {people.length > 0 && (
          <section aria-labelledby="people-heading">
            <h2 id="people-heading" className="mb-1 px-3 font-display text-sm font-semibold text-moss">
              People
            </h2>
            <ul className="space-y-0.5">
              {people.map((c) => (
                <Row key={c.id} conv={c} selected={c.id === activeId} onSelect={onSelect} />
              ))}
            </ul>
          </section>
        )}
        {conversations.length === 0 && (
          <p className="px-3 py-6 text-sm text-moss">No chats yet. Create a group or import a chat to get started.</p>
        )}
        {conversations.length > 0 && filtered.length === 0 && (
          <p className="px-3 py-6 text-sm text-moss">No chats match "{query}". Try a different name.</p>
        )}
      </div>
    </aside>
  )
}
