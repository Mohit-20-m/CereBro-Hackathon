// Presentation helpers. All analysis happens in the backend agents; these
// helpers only decide what to show after `visibleCount` messages (which lets a
// replay show gaps developing) and hold the labels the backend sends in /api/meta.

let META = {
  signals: [],
  gapTypes: {},
  severity: { possible: 0.3, strong: 0.6 },
  agents: [],
}

export const applyMeta = (meta) => {
  if (meta) META = { ...META, ...meta }
}
export const getSignals = () => META.signals
export const gapLabel = (type) => META.gapTypes[type] || type
export const severityThresholds = () => META.severity

export const SEVERITY_LABELS = { normal: 'Normal', possible: 'Possible gap', strong: 'Strong gap' }

export const ROLE_LABELS = {
  question: 'Question',
  unrelated: 'No relevant response',
  deflection: 'Deflection',
  followup: 'Clarification',
  repeat: 'Repeated request',
  resolution: 'Resolved here',
}

export const NODE_LABELS = {
  question: 'Question asked',
  unrelated: 'No relevant response',
  deflection: 'Deflected',
  followup: 'Clarification',
  repeat: 'Repeated request',
  resolution: 'Response received',
}

// Work out what the UI should show after `visibleCount` messages have arrived.
export function resolveGaps(conv, visibleCount) {
  if (!conv) return []
  return conv.gaps
    .map((gap) => {
      const stages = gap.stages.filter((s) => s.at <= visibleCount)
      if (!stages.length) return null
      const stage = stages[stages.length - 1]
      const resolved = gap.resolvedAt != null && gap.resolvedAt <= visibleCount
      return {
        ...gap,
        type: stage.type,
        signals: stage.signals,
        confidence: stage.confidence,
        reasons: stage.reasons,
        latestAt: stage.at,
        evidence: gap.evidence.filter((e) => e.id <= visibleCount),
        resolved,
        score: stage.score,
        severity: { key: stage.severity, label: SEVERITY_LABELS[stage.severity] },
        isFinal: stage === gap.stages[gap.stages.length - 1],
      }
    })
    .filter(Boolean)
}

export function resolveTopics(conv, visibleCount) {
  if (!conv) return []
  return conv.topics
    .map((topic) => {
      const entries = topic.timeline.filter((t) => t.at <= visibleCount)
      if (!entries.length) return null
      return { key: topic.key, name: topic.name, status: entries[entries.length - 1].status }
    })
    .filter(Boolean)
}

export function computeInsights(visibleMessages, totalMessages, gaps, topics) {
  const count = (...intents) => visibleMessages.filter((m) => intents.includes(m.intent)).length
  const questions = count('QUESTION')
  const unanswered = gaps.filter((g) => !g.resolved).length
  return {
    messages: totalMessages,
    questions,
    unanswered,
    answered: Math.max(0, questions - unanswered),
    requests: count('REQUEST', 'CLARIFICATION'),
    loops: gaps.filter((g) => g.type === 'CLARIFICATION_LOOP').length,
    unresolvedTopics: topics.filter((t) => t.status === 'unresolved').length,
    resolvedTopics: topics.filter((t) => t.status === 'resolved').length,
    pendingTopics: topics.filter((t) => t.status === 'pending').length,
  }
}

// Build the timeline chips for a gap from its evidence.
export function buildTimeline(gap) {
  const nodes = []
  gap.evidence.forEach((e) => {
    const last = nodes[nodes.length - 1]
    if (last && last.role === e.role) last.count += 1
    else nodes.push({ role: e.role, label: NODE_LABELS[e.role] || e.role, count: 1 })
  })
  const gapNode = { role: 'gap', label: 'Gap', count: 1 }
  const resolutionIndex = nodes.findIndex((n) => n.role === 'resolution')
  if (resolutionIndex === -1) nodes.push(gapNode)
  else nodes.splice(resolutionIndex, 0, gapNode)
  if (gap.resolved) nodes.push({ role: 'resolved', label: 'Resolved', count: 1 })
  return nodes
}

export const STATUS_STYLES = {
  resolved: { label: 'Resolved', dot: 'bg-moss', pill: 'bg-mint text-moss' },
  pending: { label: 'Pending', dot: 'bg-amber', pill: 'bg-cream text-ink' },
  unresolved: { label: 'Unresolved', dot: 'bg-coral', pill: 'bg-blush/70 text-coral' },
}

export const SEVERITY_STYLES = {
  normal: 'bg-mint text-moss',
  possible: 'bg-cream text-ink ring-1 ring-amber/60',
  strong: 'bg-coral text-white',
}
