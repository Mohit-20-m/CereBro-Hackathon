import { useState } from 'react'
import { X } from 'lucide-react'
import Rail from './components/Rail'
import { ImportModal, NewGroupModal } from './components/Modals'
import { useConversation } from './hooks/useConversation'
import ChatPage from './pages/ChatPage'
import DashboardPage from './pages/DashboardPage'
import { playClick, setSoundEnabled } from './utils/sound'

function Splash({ online }) {
  return (
    <div className="flex h-full items-center justify-center p-8 text-center">
      <div>
        <h1 className="font-display text-5xl font-semibold tracking-tight">ANVAYA</h1>
        <p className="mt-2 text-moss">Connecting context. Detecting gaps.</p>
        <p className="mt-6 text-sm text-moss" role="status">
          {online ? 'Connecting to the server…' : 'The server is still starting. Retrying every few seconds.'}
        </p>
      </div>
    </div>
  )
}

export default function App() {
  const [page, setPage] = useState('chat')
  const [sound, setSound] = useState(true)
  const [modal, setModal] = useState(null) // 'group' | 'import' | null
  const convo = useConversation()

  const toggleSound = () => {
    const next = !sound
    setSound(next)
    setSoundEnabled(next)
    if (next) playClick()
  }

  const viewEvidence = (gapId) => {
    convo.setEvidenceGapId(gapId)
    setPage('chat')
  }

  const openAlerts = () => {
    setPage('chat')
    const withGaps = convo.conversations.find((c) => c.openGaps > 0)
    if (withGaps && withGaps.id !== convo.activeId) convo.selectConversation(withGaps.id)
  }

  if (!convo.booted) return <Splash online={convo.online} />

  return (
    <div className="h-full p-0 sm:p-4">
      <div className="flex h-full overflow-hidden bg-cream/50 shadow-[0_30px_80px_-30px_rgba(101,113,102,0.6)] ring-1 ring-white/60 backdrop-blur-xl sm:rounded-[2rem]">
        <Rail
          page={page}
          setPage={setPage}
          sound={sound}
          onToggleSound={toggleSound}
          alerts={convo.totalOpenGaps}
          onAlerts={openAlerts}
        />
        {page === 'chat' ? (
          <ChatPage
            convo={convo}
            onOpenDashboard={() => setPage('dashboard')}
            onNewGroup={() => setModal('group')}
            onImport={() => setModal('import')}
          />
        ) : (
          <DashboardPage convo={convo} onViewEvidence={viewEvidence} />
        )}
      </div>

      {modal === 'group' && <NewGroupModal onClose={() => setModal(null)} onCreate={convo.createGroup} />}
      {modal === 'import' && <ImportModal onClose={() => setModal(null)} onImport={convo.importChat} />}

      {convo.notice && (
        <div role="alert" className="fixed bottom-6 left-1/2 z-50 flex -translate-x-1/2 animate-pop items-center gap-3 rounded-2xl bg-ink px-4 py-3 text-sm text-cream shadow-2xl">
          {convo.notice}
          <button type="button" onClick={convo.clearNotice} aria-label="Dismiss" className="rounded-lg p-1 hover:bg-white/10">
            <X className="h-4 w-4" />
          </button>
        </div>
      )}
    </div>
  )
}
