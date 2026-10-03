"""LangGraph orchestration for ANVAYA.

  START
    │
    ▼
  language ──► intent ──► topic ──► matcher ◄────────────┐
                                     │  │  ▲              │
                       more messages │  │  └── done ── investigator ◄─┐
                                     │  │ unsure                │      │
                                     │  └──────────────────────►┘──────┘ (one tool call per step)
                                     ▼ all threads checked
                                   detector ──► critic ◄──┐
                                                 │  └─────┘ (one gap per step)
                                                 ▼
                                              evidence ──► END

The matcher, investigator and critic loop through conditional edges: the graph
decides at run time which agent acts next.
"""
from __future__ import annotations

from functools import partial

from langgraph.graph import END, START, StateGraph

from .context import AgentContext
from .critic import critic
from .evidence import evidence_generator
from .gap_detector import gap_detector
from .intent import intent_agent
from .investigator import investigator
from .language import language_agent
from .matcher import response_matcher
from .state import AnvayaState
from .topic import topic_agent


def _after_matcher(state: AnvayaState) -> str:
    if state.get("current"):
        return "investigate"
    if state.get("pending"):
        return "next_message"
    return "detect"


def _after_investigator(state: AnvayaState) -> str:
    return "keep_searching" if state.get("current") else "back_to_matcher"


def _after_critic(state: AnvayaState) -> str:
    return "next_gap" if state.get("critic_queue") else "explain"


def build_graph(ctx: AgentContext):
    g = StateGraph(AnvayaState)
    g.add_node("language", partial(language_agent, ctx))
    g.add_node("intent", partial(intent_agent, ctx))
    g.add_node("topic", partial(topic_agent, ctx))
    g.add_node("matcher", partial(response_matcher, ctx))
    g.add_node("investigator", partial(investigator, ctx))
    g.add_node("detector", partial(gap_detector, ctx))
    g.add_node("critic", partial(critic, ctx))
    g.add_node("evidence", partial(evidence_generator, ctx))

    g.add_edge(START, "language")
    g.add_edge("language", "intent")
    g.add_edge("intent", "topic")
    g.add_edge("topic", "matcher")
    g.add_conditional_edges(
        "matcher", _after_matcher, {"investigate": "investigator", "next_message": "matcher", "detect": "detector"}
    )
    g.add_conditional_edges(
        "investigator", _after_investigator, {"keep_searching": "investigator", "back_to_matcher": "matcher"}
    )
    g.add_edge("detector", "critic")
    g.add_conditional_edges("critic", _after_critic, {"next_gap": "critic", "explain": "evidence"})
    g.add_edge("evidence", END)
    return g.compile()
