import { STATUS_STYLES } from '../utils/analysis'

export default function TopicCard({ topic }) {
  const s = STATUS_STYLES[topic.status]
  return (
    <li className="flex items-center justify-between gap-3 rounded-xl bg-white/70 px-3.5 py-2.5 transition-colors duration-300 hover:bg-white">
      <span className="truncate text-sm font-medium">{topic.name}</span>
      <span className={`flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${s.pill}`}>
        <span className={`h-2 w-2 rounded-full ${s.dot}`} />
        {s.label}
      </span>
    </li>
  )
}
