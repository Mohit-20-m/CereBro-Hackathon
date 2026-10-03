import { useEffect, useRef, useState } from 'react'
import { FileUp, X } from 'lucide-react'

function Shell({ title, onClose, children }) {
  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center p-4">
      <button type="button" aria-label="Close" onClick={onClose} className="absolute inset-0 animate-fadeIn bg-ink/25" />
      <div role="dialog" aria-label={title} className="relative w-full max-w-md animate-pop rounded-3xl bg-cream p-6 shadow-2xl">
        <div className="mb-4 flex items-start justify-between gap-3">
          <h2 className="font-display text-2xl font-semibold leading-tight">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white/70 text-moss transition-colors duration-300 hover:bg-coral hover:text-white"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}

const inputClass =
  'w-full rounded-2xl border border-transparent bg-white/80 px-4 py-2.5 text-[15px] placeholder:text-moss/80 transition-all duration-300 hover:bg-white focus:border-sky focus:bg-white focus:outline-none'

const primaryClass =
  'rounded-2xl bg-moss px-5 py-2.5 text-sm font-semibold text-cream transition-all duration-300 hover:-translate-y-0.5 hover:bg-sky hover:text-ink hover:shadow-md disabled:cursor-not-allowed disabled:bg-sage disabled:text-moss disabled:hover:translate-y-0 disabled:hover:shadow-none'

export function NewGroupModal({ onClose, onCreate }) {
  const [name, setName] = useState('')
  const [members, setMembers] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const list = members.split(',').map((m) => m.trim()).filter(Boolean)

  const submit = async (e) => {
    e.preventDefault()
    if (!name.trim() || !list.length) return
    setBusy(true)
    setError(null)
    try {
      await onCreate(name.trim(), list)
      onClose()
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  return (
    <Shell title="New group" onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <label className="block space-y-1.5">
          <span className="text-sm font-medium">Group name</span>
          <input autoFocus value={name} onChange={(e) => setName(e.target.value)} placeholder="Project Alpha" className={inputClass} />
        </label>
        <label className="block space-y-1.5">
          <span className="text-sm font-medium">Members</span>
          <input value={members} onChange={(e) => setMembers(e.target.value)} placeholder="Aishu, Rahul, Keerti" className={inputClass} />
          <span className="block text-xs text-moss">Separate names with commas. You can type as any member.</span>
        </label>
        {error && <p className="rounded-2xl bg-blush/70 px-4 py-2 text-sm text-coral">{error}</p>}
        <div className="flex justify-end">
          <button type="submit" disabled={busy || !name.trim() || !list.length} className={primaryClass}>
            {busy ? 'Creating…' : 'Create group'}
          </button>
        </div>
      </form>
    </Shell>
  )
}

export function ImportModal({ onClose, onImport }) {
  const [file, setFile] = useState(null)
  const [name, setName] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const inputRef = useRef(null)

  const submit = async (e) => {
    e.preventDefault()
    if (!file) return
    setBusy(true)
    setError(null)
    try {
      await onImport(file, name.trim())
      onClose()
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  return (
    <Shell title="Import a chat" onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="flex w-full flex-col items-center gap-2 rounded-2xl border-2 border-dashed border-sage bg-white/60 px-4 py-6 text-center transition-colors duration-300 hover:border-sky hover:bg-white"
        >
          <FileUp className="h-6 w-6 text-moss" />
          <span className="text-sm font-semibold">{file ? file.name : 'Choose a .txt file'}</span>
          <span className="text-xs text-moss">WhatsApp export, "Name: message" lines, or "[Name] [10:21]" blocks</span>
        </button>
        <input
          ref={inputRef}
          type="file"
          accept=".txt,text/plain"
          className="hidden"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
        />
        <label className="block space-y-1.5">
          <span className="text-sm font-medium">Group name (optional)</span>
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Taken from the file if empty" className={inputClass} />
        </label>
        {error && <p className="rounded-2xl bg-blush/70 px-4 py-2 text-sm text-coral">{error}</p>}
        <div className="flex justify-end">
          <button type="submit" disabled={busy || !file} className={primaryClass}>
            {busy ? 'Importing…' : 'Import and analyze'}
          </button>
        </div>
      </form>
    </Shell>
  )
}
