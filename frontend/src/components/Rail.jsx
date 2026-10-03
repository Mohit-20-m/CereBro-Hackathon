import { Bell, LayoutDashboard, MessageCircle, MessagesSquare, Volume2, VolumeX } from 'lucide-react'
import { playClick } from '../utils/sound'

function RailButton({ label, active, onClick, badge, children }) {
  return (
    <button
      type="button"
      onClick={() => {
        playClick()
        onClick?.()
      }}
      aria-label={label}
      aria-current={active ? 'page' : undefined}
      title={label}
      className={`relative flex h-11 w-11 items-center justify-center rounded-2xl transition-all duration-300 hover:-translate-y-0.5 hover:bg-sky hover:text-ink ${
        active ? 'bg-cream text-moss shadow-md' : 'text-cream/90'
      }`}
    >
      {children}
      {badge > 0 && (
        <span className="absolute -right-1 -top-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-coral px-1 text-[11px] font-semibold text-white">
          {badge}
        </span>
      )}
    </button>
  )
}

export default function Rail({ page, setPage, sound, onToggleSound, alerts = 0, onAlerts }) {
  return (
    <nav
      aria-label="Main"
      className="flex w-[60px] shrink-0 flex-col items-center gap-3 bg-moss py-5 sm:w-[76px]"
    >
      <span className="mb-3 flex h-11 w-11 items-center justify-center rounded-2xl bg-blush text-ink" title="ANVAYA">
        <MessagesSquare className="h-6 w-6" />
      </span>
      <RailButton label="Chat" active={page === 'chat'} onClick={() => setPage('chat')}>
        <MessageCircle className="h-5 w-5" />
      </RailButton>
      <RailButton label="Dashboard" active={page === 'dashboard'} onClick={() => setPage('dashboard')}>
        <LayoutDashboard className="h-5 w-5" />
      </RailButton>
      <RailButton label={alerts ? `${alerts} open gap${alerts > 1 ? 's' : ''}` : 'No open gaps'} badge={alerts} onClick={onAlerts}>
        <Bell className="h-5 w-5" />
      </RailButton>
      <div className="flex-1" />
      <RailButton label={sound ? 'Mute sounds' : 'Turn sounds on'} onClick={onToggleSound}>
        {sound ? <Volume2 className="h-5 w-5" /> : <VolumeX className="h-5 w-5" />}
      </RailButton>
    </nav>
  )
}
