import { CloudOff, Cpu, LoaderCircle } from 'lucide-react'

// Tells the user what the backend is doing when it isn't simply ready:
// unreachable, downloading models on first start, or running without the LLM.
export default function StatusBanner({ online, health }) {
  if (!online) {
    return (
      <div role="status" className="flex items-center gap-2 border-b border-white/50 bg-blush/70 px-4 py-2 text-sm">
        <CloudOff className="h-4 w-4 shrink-0 text-coral" />
        Can't reach the ANVAYA server. Retrying automatically.
      </div>
    )
  }
  const ai = health?.ai
  if (!ai || ai.state === 'ready') return null

  if (ai.state === 'heuristic') {
    return (
      <div role="status" className="flex items-center gap-2 border-b border-white/50 bg-cream px-4 py-2 text-xs text-moss">
        <Cpu className="h-4 w-4 shrink-0" />
        {ai.message}
      </div>
    )
  }

  return (
    <div role="status" className="flex items-center gap-2 border-b border-white/50 bg-mint px-4 py-2.5 text-sm font-medium">
      <LoaderCircle className="h-4 w-4 shrink-0 animate-spin text-moss" />
      {ai.message}. This takes a few seconds after each start.
    </div>
  )
}
