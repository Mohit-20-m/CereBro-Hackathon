"""Prompts for the optional LLM. It is only used by the Investigator (to pick
tools), the Critic (to re-read the chat) and gap summaries. None of them asks
"is there a gap?" – that decision belongs to the Gap Detector."""

INVESTIGATOR_TOOLS = ["search_messages", "find_similar", "get_messages_by_speaker", "get_messages_after", "final"]
INVESTIGATOR_SYSTEM = (
    "You are the Investigator agent. A question in a group chat got no answer in the next few replies. "
    "Use tools to search the rest of the conversation and decide whether someone answered it later.\n"
    "Tools (set \"action\" and \"input\"):\n"
    "- search_messages: input is one keyword\n"
    "- find_similar: input is a sentence; finds messages with similar meaning, in any language\n"
    "- get_messages_by_speaker: input is a person's name\n"
    "- get_messages_after: input is a message number\n"
    "- final: set answer_seq to the number of the message that answers the question, or 0 if none does\n"
    "Postponing (\"I'll check\") is not an answer. Use at most {steps} tools, then call final. "
    "Reply only with JSON."
)
INVESTIGATOR_SCHEMA = {
    "type": "object",
    "properties": {
        "thought": {"type": "string"},
        "action": {"type": "string", "enum": INVESTIGATOR_TOOLS},
        "input": {"type": "string"},
        "answer_seq": {"type": "integer"},
    },
    "required": ["thought", "action", "input", "answer_seq"],
}

CRITIC_SYSTEM = (
    "You are the Critic agent. Another agent claims that a question in a group chat was never answered. "
    "Challenge that claim: read the later messages and check whether any of them answers or resolves the "
    "question. Be strict. Postponing (\"I'll check\") or talking about other topics does not resolve it. "
    "If a message resolves it, set message_seq to its number, otherwise 0. Give a reason of at most 15 "
    "words. Reply only with JSON."
)
CRITIC_SCHEMA = {
    "type": "object",
    "properties": {
        "resolved": {"type": "boolean"},
        "message_seq": {"type": "integer"},
        "reason": {"type": "string"},
    },
    "required": ["resolved", "message_seq", "reason"],
}

SUMMARY_SYSTEM = (
    "You are the Evidence Generator. Using only the facts given, write one plain sentence (at most 30 "
    "words) telling the team what was left unanswered and why it matters. Reply only with JSON."
)
SUMMARY_SCHEMA = {"type": "object", "properties": {"summary": {"type": "string"}}, "required": ["summary"]}
