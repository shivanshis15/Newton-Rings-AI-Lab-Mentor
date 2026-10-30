"""
ChatResponder
-------------
Turns a raw student message (or a sidebar button click) into a natural,
conversational reply using the KnowledgeRetriever. Handles greetings,
thanks, follow-up phrases ("tell me more", "why?"), redirects to Viva Mode
and the Calculator, and falls back to a clarifying question when nothing
matches well.

This is intentionally simple, transparent, rule-based logic — no ML model,
no external API — so it is completely explainable and runs instantly and
offline.
"""

import random
import re


class ChatResponder:

    TOPIC_LABELS = {
        "theory": "Explain the theory",
        "apparatus": "Explain the apparatus",
        "principle": "Explain the principle",
        "formulae": "Explain the formulae",
        "procedure": "Explain the procedure",
        "observations": "Show observation tables",
        "calculations": "Explain the calculations",
        "graph": "Explain graph plotting",
        "precautions": "List the precautions",
        "errors": "Explain sources of error",
        "applications": "Explain applications",
        "learning_outcomes": "Explain learning outcomes",
    }

    GREETING_WORDS = {
        "hi", "hii", "hiii", "hello", "hey", "heyy",
        "good morning", "good afternoon", "good evening", "greetings"
    }

    THANKS_WORDS = {"thanks", "thank you", "thank", "thx", "ty", "appreciate it"}

    FOLLOWUP_WORDS = {
        "more", "explain more", "tell me more", "why", "why is that",
        "elaborate", "go on", "continue", "expand", "explain further", "in detail"
    }

    VIVA_TRIGGER_WORDS = {
        "viva", "quiz me", "test me", "ask me questions",
        "start viva", "quiz", "examine me"
    }

    CALCULATOR_TRIGGER_WORDS = {
        "calculator", "calculate", "compute wavelength", "compute the wavelength",
        "find wavelength", "wavelength calculator"
    }

    TOPIC_ALIASES = {
        "theory": [
            "theory",
            "concept",
            "interference",
            "thin film",
            "newton rings",
            "newton's rings",
            "ring formation"
        ],

        "principle": [
            "principle",
            "working principle",
            "working",
            "how does it work"
        ],

        "apparatus": [
            "apparatus",
            "equipment",
            "instrument",
            "setup",
            "components"
        ],

        "procedure": [
            "procedure",
            "steps",
            "method",
            "perform experiment"
        ],

        "formulae": [
            "formula",
            "formulae",
            "equation"
        ],

        "calculations": [
            "calculation",
            "calculate",
            "wavelength"
        ],

        "graph": [
            "graph",
            "plot"
        ],

        "observations": [
            "observation",
            "reading"
        ],

        "precautions": [
            "precaution",
            "safety"
        ],

        "errors": [
            "error",
            "mistake"
        ],

        "applications": [
            "application",
            "applications",
            "uses"
        ],

        "learning_outcomes": [
            "objective",
            "learning outcome"
        ]
    }

    DEFAULT_SUGGESTIONS = [
        "Explain the theory",
        "Explain the procedure",
        "Explain the formulae",
        "Start Viva Mode",
    ]

    def __init__(self, retriever):
        self.retriever = retriever

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def respond(self, message, last_topic=None):
        """
        Main entry point for free-text chat messages.
        Returns a dict: {"reply": str, "suggestions": list[str], "topic": str|None}
        """
        text = message.lower().strip()

        print("\nUSER:", message)
        print("TEXT:", text)

        if self._matches_any(text, self.GREETING_WORDS) and len(text.split()) <= 5:
            return self._greeting_reply(last_topic)

        if "principle" in text:
            print("Matched principle")
            return self._topic_reply("principle")
        
        if (
            text == "help"
            or text == "what can you do"
            or text == "what all can you do"
            or text == "capabilities"
            or text == "commands"
            ):
            return {
                "reply": (
                    "I am the Newton's Rings AI Lab Mentor. I can help you with:\n\n"
                    "• Theory\n"
                    "• Principle\n"
                    "• Apparatus\n"
                    "• Procedure\n"
                    "• Observations\n"
                    "• Calculations\n"
                    "• Graph Plotting\n"
                    "• Precautions\n"
                    "• Sources of Error\n"
                    "• Applications\n"
                    "• Viva Questions\n"
                    "• Wavelength Calculator"
                ),
                "suggestions": self.DEFAULT_SUGGESTIONS,
                "topic": None,
            }

        if self._matches_any(text, self.THANKS_WORDS):
            return self._thanks_reply(last_topic)

        if self._matches_any(text, self.VIVA_TRIGGER_WORDS):
            return {
                "reply": (
                    "Great — I'd love to quiz you! Click the '🎓 Start Viva Mode' "
                    "button in the sidebar and I'll begin with a basic question "
                    "and adapt the difficulty as we go."
                ),
                "suggestions": ["Explain the theory", "Explain the procedure"],
                "topic": last_topic,
            }

        if self._matches_any(text, self.CALCULATOR_TRIGGER_WORDS):
            return {
                "reply": (
                    "Sure! Click the '🧮 Open Calculator' button in the sidebar — "
                    "enter your D²(n+m), D²(n), m, and R values and I'll compute "
                    "the wavelength and percentage error for you instantly."
                ),
                "suggestions": ["Explain the calculations", "Explain the formulae"],
                "topic": last_topic,
            }

        if self._matches_any(text, self.FOLLOWUP_WORDS) and last_topic:
            data = self.retriever.get_topic(last_topic)
            if data:
                related = data.get("related_topics", [])
                reply = (
                    f"Sure, let's go a bit deeper into {data.get('title', last_topic.title())}.\n\n"
                    f"{data.get('content', '')}"
                )
                return {
                    "reply": reply,
                    "suggestions": self._labels_for(related),
                    "topic": last_topic,
                }
            
        topic_key, score = self.retriever.search(text)
        print(">>> Calling retriever")
        
        print(f"Retriever returned: {topic_key} ({score})")

        if topic_key:
            return self._topic_reply(topic_key)
        
        for topic, aliases in self.TOPIC_ALIASES.items():
        
            if any(alias in text for alias in aliases):
                return self._topic_reply(topic)

        topic_key, score = self.retriever.search(text)
        if topic_key and score >= 0.15:
            result = self._topic_reply(topic_key)
            return result

        return {
            "reply": (
                "I'm not fully sure what you're asking — could you rephrase that, "
                "or pick one of the topics below and I'll explain it right away?"
            ),
            "suggestions": self.DEFAULT_SUGGESTIONS,
            "topic": last_topic,
        }

    def respond_to_topic(self, topic_key):
        """Entry point for sidebar quick-action buttons."""
        return self._topic_reply(topic_key)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _topic_reply(self, topic_key):
        
        print("TOPIC REQUESTED:", topic_key)
        data = self.retriever.get_topic(topic_key)

        print("DATA TITLE:", data.get("title") if data else "NONE")
        if not data:
            return {
                "reply": "I don't have information on that topic yet — try one of the sidebar buttons.",
                "suggestions": self.DEFAULT_SUGGESTIONS,
                "topic": None,
            }

        title = data.get("title", topic_key.replace("_", " ").title())
        content = data.get("content", "")
        reply = f"{title}\n\n{content}"

        related = data.get("related_topics", [])
        suggestions = self._labels_for(related)
        if not suggestions:
            suggestions = self.DEFAULT_SUGGESTIONS

        return {"reply": reply, "suggestions": suggestions, "topic": topic_key}

    def _labels_for(self, topic_keys):
        labels = []
        for key in topic_keys:
            labels.append(self.TOPIC_LABELS.get(key, key.replace("_", " ").title()))
        return labels[:4]

    def _greeting_reply(self, last_topic):
        reply = (
            "Hello! 👋 I'm the Newton's Rings AI Lab Mentor.\n\n"
            "I can help you understand the experiment, explain concepts, solve calculations, "
            "conduct viva practice, and answer questions about:\n\n"
            "• Theory\n"
            "• Principle\n"
            "• Apparatus\n"
            "• Procedure\n"
            "• Observations\n"
            "• Calculations\n"
            "• Graph Plotting\n"
            "• Precautions\n"
            "• Sources of Error\n"
            "• Applications\n\n"
            "How can I help you today?"
        )
        return {"reply": reply, "suggestions": self.DEFAULT_SUGGESTIONS, "topic": last_topic}

    def _thanks_reply(self, last_topic):
        replies = [
            "You're very welcome! 😊 Let me know if you'd like to explore anything else.",
            "Happy to help! Feel free to ask another question anytime.",
            "Anytime! Good luck with your experiment and presentation.",
        ]
        return {
            "reply": random.choice(replies),
            "suggestions": self.DEFAULT_SUGGESTIONS,
            "topic": last_topic,
        }

    @staticmethod
    def _matches_any(text, phrase_set):
        text = text.lower()

        for phrase in phrase_set:
            pattern = r"\b" + re.escape(phrase.lower()) + r"\b"
            if re.search(pattern, text):
                return True

        return False