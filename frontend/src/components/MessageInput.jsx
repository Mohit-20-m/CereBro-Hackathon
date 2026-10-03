import { useState } from 'react'
import { Check, Send, Smile, X } from 'lucide-react'
import { playClick, playKey } from '../utils/sound'

const emojis = ['😊', '👍', '🎉', '🙏', '😄', '🤔']
const NEW_MEMBER = '__new__'

function SenderPicker({ members, sender, onChange, onAddMember }) {
  const [adding, setAdding] = useState(false)
  const [name, setName] = useState('')

  const confirm = async () => {
    const clean = name.trim()
    if (!clean) return
    await onAddMember(clean)
    setName('')
    setAdding(false)
  }

  if (adding) {
    return (
      <div className="flex shrink-0 items-center gap-1">
        <input
          autoFocus
          value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') confirm()
            if (e.key === 'Escape') setAdding(false)
          }}
          placeholder="Name"
          aria-label="New member name"
          className="h-11 w-28 rounded-2xl border border-transparent bg-white/80 px-3 text-sm focus:border-sky focus:outline-none"
        />
        <button type="button" onClick={confirm} aria-label="Add member" className="flex h-11 w-9 items-center justify-center rounded-xl bg-moss text-cream hover:bg-sky hover:text-ink">
          <Check className="h-4 w-4" />
        </button>
        <button type="button" onClick={() => setAdding(false)} aria-label="Cancel" className="flex h-11 w-9 items-center justify-center rounded-xl bg-white/70 text-moss hover:bg-blush">
          <X className="h-4 w-4" />
        </button>
      </div>
    )
  }

  return (
    <label className="relative shrink-0">
      <span className="sr-only">Send as</span>
      <select
        value={sender}
        onChange={(e) => (e.target.value === NEW_MEMBER ? setAdding(true) : onChange(e.target.value))}
        title="Who you are typing as"
        className="h-11 max-w-[8.5rem] cursor-pointer appearance-none truncate rounded-2xl bg-white/70 pl-3 pr-7 text-sm font-semibold text-ink transition-colors duration-300 hover:bg-blush focus:outline-none"
      >
        {!members.includes(sender) && <option value={sender}>{sender}</option>}
        {members.map((m) => (
          <option key={m} value={m}>
            {m}
          </option>
        ))}
        <option value={NEW_MEMBER}>+ Add member…</option>
      </select>
      <span aria-hidden="true" className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-xs text-moss">▾</span>
    </label>
  )
}

export default function MessageInput({ onSend, members, sender, onSenderChange, onAddMember }) {
  const [text, setText] = useState('')
  const [emojiIndex, setEmojiIndex] = useState(0)

  const submit = () => {
    if (!text.trim()) return
    onSend(text)
    setText('')
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
      return
    }
    if (e.metaKey || e.ctrlKey || e.altKey) return
    if (e.key === 'Backspace') playKey('back')
    else if (e.key === ' ') playKey('space')
    else if (e.key.length === 1) playKey('key')
  }

  return (
    <div className="flex items-center gap-2 border-t border-white/50 bg-white/40 px-4 py-3">
      <SenderPicker members={members} sender={sender} onChange={onSenderChange} onAddMember={onAddMember} />
      <button
        type="button"
        onClick={() => {
          playClick()
          setText((t) => t + emojis[emojiIndex])
          setEmojiIndex((i) => (i + 1) % emojis.length)
        }}
        aria-label="Add emoji"
        className="hidden h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-white/70 text-moss transition-all duration-300 hover:rotate-6 hover:bg-blush hover:text-ink sm:flex"
      >
        <Smile className="h-5 w-5" />
      </button>
      <input
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={`Message as ${sender}…`}
        aria-label="Type a message"
        autoComplete="off"
        maxLength={4000}
        className="h-11 min-w-0 flex-1 rounded-2xl border border-transparent bg-cream/80 px-4 text-[15px] placeholder:text-moss/80 transition-all duration-300 hover:bg-cream focus:border-sky focus:bg-white focus:outline-none"
      />
      <button
        type="button"
        onClick={submit}
        disabled={!text.trim()}
        aria-label="Send message"
        className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-moss text-cream transition-all duration-300 hover:-translate-y-0.5 hover:bg-sky hover:text-ink hover:shadow-md disabled:cursor-not-allowed disabled:bg-sage disabled:text-moss disabled:hover:translate-y-0 disabled:hover:shadow-none"
      >
        <Send className="h-5 w-5" />
      </button>
    </div>
  )
}
