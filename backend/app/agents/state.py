"""Shared LangGraph state passed between the agents.

messages   [{seq, db_id, sender, text, time}]                (read-only snapshot)
analyses   {seq: {language_label, normalized, intent, topic_key, embedding, ...}}
topics     {topic_key: topic_name}                          (canonical topic registry)
pending    seqs still to be examined by the Response Matcher
items      open "threads": a question/request plus its follow-ups and matching results
current    the investigation the Investigator agent is running, or None
gaps       gap candidates produced by the Gap Detector
critic_queue  indexes into gaps still waiting for the Critic agent
"""
from typing import Any, TypedDict


class AnvayaState(TypedDict, total=False):
    conversation_id: int
    messages: list[dict[str, Any]]
    analyses: dict[int, dict[str, Any]]
    topics: dict[str, str]
    pending: list[int]
    items: list[dict[str, Any]]
    current: dict[str, Any] | None
    gaps: list[dict[str, Any]]
    topic_timeline: list[dict[str, Any]]
    critic_queue: list[int]
    insights: dict[str, Any]
