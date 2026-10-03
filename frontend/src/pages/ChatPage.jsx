import { useState } from 'react'
import { FileUp, Plus } from 'lucide-react'
import ChatHeader from '../components/ChatHeader'
import ChatWindow from '../components/ChatWindow'
import ConversationList from '../components/ConversationList'
import EvidencePanel from '../components/EvidencePanel'
import InsightPanel from '../components/InsightPanel'
import MessageInput from '../components/MessageInput'
import StatusBanner from '../components/StatusBanner'

function EmptyState({ loading, onNewGroup, onImport }) {
  return (
    <div className="flex flex-1 items-center justify-center px-8 text-center">
      <div className="max-w-sm">
        <p className="font-display text-2xl font-semibold">{loading ? 'Opening chat…' : 'Start a conversation'}</p>
        {!loading && (
          <>
            <p className="mt-2 text-sm text-moss">
              Create a group and type as its members, or import a chat export. The agents will find what was left unanswered.
            </p>
            <div className="mt-5 flex justify-center gap-2">
              <button type="button" onClick={onNewGroup} className="flex items-center gap-1.5 rounded-2xl bg-moss px-4 py-2.5 text-sm font-semibold text-cream transition-all duration-300 hover:bg-sky hover:text-ink">
                <Plus className="h-4 w-4" /> New group
              </button>
              <button type="button" onClick={onImport} className="flex items-center gap-1.5 rounded-2xl bg-white/80 px-4 py-2.5 text-sm font-semibold transition-all duration-300 hover:bg-blush">
                <FileUp className="h-4 w-4" /> Import chat
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default function ChatPage({ convo, onOpenDashboard, onNewGroup, onImport }) {
  const [showList, setShowList] = useState(false) // mobile only
  const [showInsights, setShowInsights] = useState(false) // below xl only
  const {
    conversations, active, activeId, messages, gaps, topics, insights, replaying, typingName,
    evidenceGapId, setEvidenceGapId, selectConversation, startReplay, stopReplay, send, members,
    currentSender, setSender, addMember, reanalyze, online, health,
  } = convo

  const evidenceGap = gaps.find((g) => g.id === evidenceGapId) || null
  const viewEvidence = (id) => {
    setEvidenceGapId(id)
    setShowInsights(false)
  }

  return (
    <div className="relative flex min-w-0 flex-1 overflow-hidden">
      <ConversationList
        conversations={conversations}
        activeId={activeId}
        onSelect={(id) => {
          selectConversation(id)
          setShowList(false)
        }}
        onNewGroup={onNewGroup}
        onImport={onImport}
        className={`${showList || activeId == null ? 'flex w-full' : 'hidden'} lg:flex lg:w-80 lg:shrink-0`}
      />

      <section className={`${showList || activeId == null ? 'hidden' : 'flex'} min-w-0 flex-1 flex-col lg:flex`}>
        <StatusBanner online={online} health={health} />
        {active ? (
          <>
            <ChatHeader
              conv={active}
              typingName={typingName}
              replaying={replaying}
              gapCount={gaps.filter((g) => !g.resolved).length}
              onBack={() => setShowList(true)}
              onReplay={startReplay}
              onStop={stopReplay}
              onReanalyze={reanalyze}
              onToggleInsights={() => setShowInsights(true)}
            />
            <ChatWindow
              conv={active}
              messages={messages}
              gaps={gaps}
              evidenceGap={evidenceGap}
              typingName={typingName}
              onViewEvidence={viewEvidence}
            />
            <MessageInput
              onSend={send}
              members={members}
              sender={currentSender}
              onSenderChange={setSender}
              onAddMember={addMember}
            />
          </>
        ) : (
          <EmptyState loading={activeId != null} onNewGroup={onNewGroup} onImport={onImport} />
        )}
      </section>

      {active && (
        <InsightPanel
          insights={insights}
          gaps={gaps}
          topics={topics}
          evidenceGapId={evidenceGapId}
          onViewEvidence={viewEvidence}
          onOpenDashboard={onOpenDashboard}
          onClose={() => setShowInsights(false)}
          className={`${
            showInsights ? 'absolute inset-y-0 right-0 z-20 flex w-[min(22rem,100%)] bg-cream shadow-2xl' : 'hidden'
          } xl:static xl:z-auto xl:flex xl:w-80 xl:shrink-0 xl:bg-white/30 xl:shadow-none`}
        />
      )}

      {evidenceGap && (
        <EvidencePanel gap={evidenceGap} messages={messages} onClose={() => setEvidenceGapId(null)} />
      )}
    </div>
  )
}
