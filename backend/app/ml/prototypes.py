"""Example phrases for each intent. The Intent Analyzer embeds these once and
labels a message by the intent whose examples it is closest to in meaning."""

INTENT_EXAMPLES = {
    "QUESTION": [
        "Who is doing this task?", "What is the status of the report?", "When is the meeting?",
        "Which database are we using?", "Did anyone send the file?", "Is the meeting at 4?",
        "Where is the document?", "How do we deploy this?", "Has anyone finished the slides?",
        "Who will handle the API?", "Did you watch the match yesterday?", "Are we meeting today?",
    ],
    "REQUEST": [
        "Please send me the report.", "Can you share the file?", "I asked about this earlier, still no answer.",
        "Any update on this?", "Someone please reply.", "Still waiting for an answer.",
        "Could someone take care of this?", "I asked about the schema.",
    ],
    "CLARIFICATION": [
        "I mean which one exactly?", "To be clear, which option?", "I meant the one we are actually using.",
        "No, I am asking specifically about that.", "Sorry, which one do you mean?", "Which of the two?",
    ],
    "ANSWER": [
        "Yes, it is done.", "No, not yet.", "Rahul is handling it.", "We are using PostgreSQL.",
        "It is at 4 pm.", "I sent it yesterday.", "Yes, fixed for 4.", "Yes, the last over was great.",
        "Yes, I will join.",
    ],
    "PROMISE": [
        "I will do it tomorrow.", "I will send it in 5 minutes.", "I'll check.", "Let me look into it later.",
        "I will update the docs tomorrow.", "I'll take care of it.", "I will share it tonight.",
    ],
    "STATEMENT": [
        "The frontend is almost done.", "The presentation is ready.", "Docker is ready for deployment.",
        "The UI is complete.", "The build passed.", "The server is down again.", "Presentation done.",
    ],
    "CONFIRMATION": ["Okay.", "Sure, works for me.", "Thanks!", "Great, thank you.", "Sounds good.", "Noted."],
    "GREETING": ["Good morning everyone.", "Hi guys.", "Hello team.", "Bye, see you.", "Good night."],
}

# Labels for the NLI fallback (mDeBERTa zero-shot), mapped back to intents.
NLI_INTENT_LABELS = {
    "a question asking for information": "QUESTION",
    "a request asking someone to do something": "REQUEST",
    "an answer to a question": "ANSWER",
    "a promise to do something later": "PROMISE",
    "a statement sharing information": "STATEMENT",
    "an acknowledgement like okay or thanks": "CONFIRMATION",
    "a greeting": "GREETING",
}
