import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api } from '../services/api'
import { applyMeta, computeInsights, resolveGaps, resolveTopics } from '../utils/analysis'
import { playAlert, playReceive, playSend } from '../utils/sound'

const BUSY = new Set(['queued', 'running'])
const AI_SETTLED = new Set(['ready', 'heuristic'])

const nowTime = () => {
  const d = new Date()
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

export function useConversation() {
  const [meta, setMeta] = useState(null)
  const [health, setHealth] = useState(null)
  const [online, setOnline] = useState(true)
  const [booted, setBooted] = useState(false)
  const [list, setList] = useState([])
  const [activeId, setActiveId] = useState(null)
  const [detail, setDetail] = useState(null)
  const [count, setCount] = useState(null) // visible messages while replaying
  const [replaying, setReplaying] = useState(false)
  const [typingName, setTypingName] = useState(null)
  const [evidenceGapId, setEvidenceGapId] = useState(null)
  const [outbox, setOutbox] = useState([]) // messages sent but not yet confirmed
  const [senders, setSenders] = useState({}) // conversation id -> who you are typing as
  const [notice, setNotice] = useState(null)
  const timers = useRef([])
  const activeRef = useRef(null)
  const seenGaps = useRef({}) // conversation id -> { version, open }
  const replayingRef = useRef(false)

  activeRef.current = activeId
  replayingRef.current = replaying

  // ---- loading ---------------------------------------------------------------
  const refreshList = useCallback(async () => {
    try {
      const data = await api.conversations()
      setList(data)
      setOnline(true)
      return data
    } catch {
      setOnline(false)
      return null
    }
  }, [])

  const refreshDetail = useCallback(async (id) => {
    if (id == null) return null
    try {
      const data = await api.conversation(id)
      setOnline(true)
      if (activeRef.current !== id) return data
      const open = data.gaps.filter((g) => g.resolvedAt == null).length
      const prev = seenGaps.current[id]
      if (prev && data.analysis.version > prev.version && open > prev.open && !replayingRef.current) playAlert()
      seenGaps.current[id] = { version: data.analysis.version, open }
      setDetail(data)
      return data
    } catch (err) {
      if (String(err.message).includes('not found')) {
        setDetail(null)
        setActiveId(null)
      } else setOnline(false)
      return null
    }
  }, [])

  const refreshHealth = useCallback(async () => {
    try {
      setHealth(await api.health())
    } catch {
      setOnline(false)
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    let retry
    const boot = async () => {
      try {
        const [m, h, convs] = await Promise.all([api.meta(), api.health(), api.conversations()])
        if (cancelled) return
        applyMeta(m)
        setMeta(m)
        setHealth(h)
        setList(convs)
        setActiveId((current) => current ?? convs[0]?.id ?? null)
        setOnline(true)
        setBooted(true)
      } catch {
        if (cancelled) return
        setOnline(false)
        retry = setTimeout(boot, 3000)
      }
    }
    boot()
    return () => {
      cancelled = true
      clearTimeout(retry)
    }
  }, [])

  const clearTimers = useCallback(() => {
    timers.current.forEach(clearTimeout)
    timers.current = []
  }, [])

  useEffect(() => clearTimers, [clearTimers])

  // Load the selected conversation.
  useEffect(() => {
    clearTimers()
    setReplaying(false)
    setTypingName(null)
    setCount(null)
    setOutbox([])
    setEvidenceGapId(null)
    setDetail(null)
    if (activeId != null) refreshDetail(activeId)
  }, [activeId, clearTimers, refreshDetail])

  // Poll quickly while agents work or models download, slowly otherwise.
  const busy =
    (detail && (BUSY.has(detail.analysis.status) || !detail.analysis.upToDate)) ||
    list.some((c) => BUSY.has(c.analysis.status))
  const aiBusy = !health || !AI_SETTLED.has(health.ai.state)
  useEffect(() => {
    if (!booted) return undefined
    const id = setInterval(
      () => {
        refreshList()
        if (activeRef.current != null) refreshDetail(activeRef.current)
        if (aiBusy || !online) refreshHealth()
      },
      busy || aiBusy || !online ? 1500 : 6000,
    )
    return () => clearInterval(id)
  }, [booted, busy, aiBusy, online, refreshList, refreshDetail, refreshHealth])

  // ---- actions ---------------------------------------------------------------
  const selectConversation = useCallback((id) => setActiveId(id), [])

  const members = useMemo(() => detail?.members ?? [], [detail])
  const currentSender = (activeId != null && senders[activeId]) || members[0] || 'You'
  const setSender = useCallback((name) => setSenders((s) => ({ ...s, [activeRef.current]: name })), [])

  const stopReplay = useCallback(() => {
    clearTimers()
    setReplaying(false)
    setTypingName(null)
    setCount(null)
  }, [clearTimers])

  const startReplay = useCallback(() => {
    if (!detail?.messages.length) return
    clearTimers()
    setEvidenceGapId(null)
    setCount(0)
    setReplaying(true)
    const alertAt = new Set(detail.gaps.flatMap((g) => g.stages.map((s) => s.at)))
    let t = 600
    detail.messages.forEach((m, i) => {
      timers.current.push(setTimeout(() => setTypingName(m.sender), t))
      t += 900 + Math.min(m.text.length * 20, 900)
      timers.current.push(
        setTimeout(() => {
          setTypingName(null)
          setCount(i + 1)
          playReceive()
          if (alertAt.has(m.id)) timers.current.push(setTimeout(playAlert, 380))
          if (i === detail.messages.length - 1) {
            setReplaying(false)
            setCount(null)
          }
        }, t),
      )
      t += 450
    })
  }, [detail, clearTimers])

  const send = useCallback(
    async (text) => {
      const clean = text.trim()
      if (!clean || activeId == null) return
      if (replayingRef.current) stopReplay()
      const temp = { id: `tmp-${Date.now()}`, sender: currentSender, time: nowTime(), text: clean, pending: true }
      setOutbox((o) => [...o, temp])
      playSend()
      try {
        await api.sendMessage(activeId, currentSender, clean, temp.time)
        await refreshDetail(activeId)
        refreshList()
      } catch (err) {
        setNotice(`Message not sent: ${err.message}`)
      } finally {
        setOutbox((o) => o.filter((m) => m.id !== temp.id))
      }
    },
    [activeId, currentSender, refreshDetail, refreshList, stopReplay],
  )

  const createGroup = useCallback(
    async (name, memberNames) => {
      const conv = await api.createConversation(name, memberNames)
      await refreshList()
      setActiveId(conv.id)
      return conv
    },
    [refreshList],
  )

  const importChat = useCallback(
    async (file, name) => {
      const conv = await api.importChat(file, name)
      await refreshList()
      setActiveId(conv.id)
      return conv
    },
    [refreshList],
  )

  const addMember = useCallback(
    async (name) => {
      if (activeId == null) return
      await api.addMember(activeId, name)
      await refreshDetail(activeId)
      setSender(name.trim())
    },
    [activeId, refreshDetail, setSender],
  )

  const reanalyze = useCallback(async () => {
    if (activeId == null) return
    await api.analyze(activeId)
    refreshDetail(activeId)
  }, [activeId, refreshDetail])

  const deleteConversation = useCallback(
    async (id) => {
      await api.deleteConversation(id)
      const convs = await refreshList()
      if (id === activeRef.current) setActiveId(convs?.[0]?.id ?? null)
    },
    [refreshList],
  )

  // ---- derived view ------------------------------------------------------------
  const total = detail?.messages.length ?? 0
  const visibleCount = count ?? total
  const shown = useMemo(() => (detail ? detail.messages.slice(0, visibleCount) : []), [detail, visibleCount])
  const messages = useMemo(
    () => [...shown, ...(count == null ? outbox : [])].map((m) => ({ ...m, mine: m.sender === currentSender })),
    [shown, outbox, count, currentSender],
  )
  const gaps = useMemo(() => resolveGaps(detail, visibleCount), [detail, visibleCount])
  const topics = useMemo(() => resolveTopics(detail, visibleCount), [detail, visibleCount])
  const insights = useMemo(() => computeInsights(shown, messages.length, gaps, topics), [shown, messages.length, gaps, topics])
  const totalOpenGaps = list.reduce((sum, c) => sum + (c.openGaps || 0), 0)

  return {
    meta,
    health,
    online,
    booted,
    conversations: list,
    active: detail,
    activeId,
    messages,
    gaps,
    topics,
    insights,
    totalOpenGaps,
    replaying,
    typingName,
    evidenceGapId,
    setEvidenceGapId,
    selectConversation,
    startReplay,
    stopReplay,
    send,
    members,
    currentSender,
    setSender,
    addMember,
    createGroup,
    importChat,
    reanalyze,
    deleteConversation,
    notice,
    clearNotice: () => setNotice(null),
  }
}
