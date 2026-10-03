import { Users } from 'lucide-react'

const tones = ['bg-sky', 'bg-blush', 'bg-sage', 'bg-mint', 'bg-cream']
const hash = (s) => [...s].reduce((a, c) => a + c.charCodeAt(0), 0)

const sizes = {
  sm: 'h-8 w-8 text-xs',
  md: 'h-10 w-10 text-sm',
  lg: 'h-12 w-12 text-base',
}

export default function Avatar({ name, size = 'md', group = false, className = '' }) {
  const initials = name
    .split(' ')
    .map((w) => w[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()

  return (
    <span
      aria-hidden="true"
      className={`inline-flex shrink-0 items-center justify-center rounded-full font-display font-semibold text-ink ring-2 ring-white/70 ${sizes[size]} ${tones[hash(name) % tones.length]} ${className}`}
    >
      {group ? <Users className="h-1/2 w-1/2" /> : initials}
    </span>
  )
}
