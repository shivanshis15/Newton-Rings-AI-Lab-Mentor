"""
VivaEngine
----------
Runs an interactive, adaptive viva (oral exam) session entirely offline.

Responsibilities:
- Load viva_questions.json (basic / intermediate / advanced questions,
  each with a model answer, keyword list for evaluation, and progressive
  hints).
- Track session state (current question, difficulty level, score,
  questions already asked) using the Flask session object passed in by
  app.py.
- Evaluate a student's typed answer using keyword/concept overlap against
  the question's keyword list (no ML model needed).
- Escalate difficulty on correct answers, de-escalate on incorrect ones.
- Provide hints progressively instead of revealing the answer immediately.
- Explain why an answer was marked incorrect, then reveal the full model
  answer so the student still learns the concept.
- Produce a final performance summary when the session ends.
"""

import os
import json
import random


class VivaEngine:

    LEVEL_ORDER = ["basic", "intermediate", "advanced"]

    HINT_TRIGGER_WORDS = {"hint", "clue", "help me", "give me a hint", "i need a hint", "stuck"}
    SKIP_TRIGGER_WORDS = {"skip", "next question", "pass", "skip this question", "skip question"}
    END_TRIGGER_WORDS = {"end viva", "stop viva", "quit viva", "end the viva", "finish viva", "exit viva"}

    def __init__(self, knowledge_dir):
        path = os.path.join(knowledge_dir, "viva_questions.json")
        with open(path, "r", encoding="utf-8") as f:
            self.questions = json.load(f)

        self.by_level = {
            level: [q for q in self.questions if q.get("level") == level]
            for level in self.LEVEL_ORDER
        }
        self.by_id = {q["id"]: q for q in self.questions}

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def start_session(self, session):
        session["viva_active"] = True
        session["viva_level"] = "basic"
        session["viva_asked_ids"] = []
        session["viva_correct_count"] = 0
        session["viva_total_count"] = 0
        session["viva_hint_count"] = 0
        session["viva_current_id"] = None

        question = self._pick_question(session, "basic")
        if not question:
            session["viva_active"] = False
            return {
                "reply": "I couldn't find any viva questions in the knowledge base.",
                "suggestions": ["Explain the theory"],
            }

        session["viva_current_id"] = question["id"]
        session["viva_asked_ids"].append(question["id"])
        session["viva_hint_count"] = 0

        reply = (
            "🎓 Let's begin your viva! I'll start with a basic-level question "
            "and increase the difficulty as you answer correctly.\n\n"
            f"Q: {question['question']}\n\n"
            "Type your answer below — or ask for a hint if you're stuck."
        )
        return {
            "reply": reply,
            "suggestions": ["Give me a hint", "Skip this question", "End Viva"],
        }

    def end_session(self, session):
        correct = session.get("viva_correct_count", 0)
        total = session.get("viva_total_count", 0)
        level_reached = session.get("viva_level", "basic")

        session["viva_active"] = False
        session["viva_current_id"] = None

        if total == 0:
            reply = (
                "Viva ended. You didn't answer any questions this time — "
                "come back whenever you're ready to try again!"
            )
        else:
            pct = round((correct / total) * 100)
            reply = (
                "🏁 Viva session complete!\n\n"
                f"Questions answered: {total}\n"
                f"Correct answers: {correct}\n"
                f"Score: {pct}%\n"
                f"Highest level reached: {level_reached.title()}\n\n"
                f"{self._final_comment(pct)}"
            )

        return {
            "reply": reply,
            "suggestions": ["Start Viva Mode", "Explain the theory"],
            "viva_ended": True,
        }

    # ------------------------------------------------------------------
    # Answer handling
    # ------------------------------------------------------------------

    def handle_answer(self, session, message):
        text = message.strip().lower()

        if not session.get("viva_active"):
            return {
                "reply": "You're not currently in a viva session. Click 'Start Viva Mode' to begin.",
                "suggestions": ["Start Viva Mode"],
            }

        if self._matches_any(text, self.HINT_TRIGGER_WORDS):
            return self.give_hint(session)

        if self._matches_any(text, self.SKIP_TRIGGER_WORDS):
            return self.next_question(session)

        if self._matches_any(text, self.END_TRIGGER_WORDS):
            return self.end_session(session)

        current_id = session.get("viva_current_id")
        question = self.by_id.get(current_id)
        if not question:
            return self.start_session(session)

        score = self._evaluate_answer(text, question)
        session["viva_total_count"] = session.get("viva_total_count", 0) + 1

        if score >= 0.6:
            session["viva_correct_count"] = session.get("viva_correct_count", 0) + 1
            feedback = f"✅ Correct! {self._praise()}\n\nModel answer: {question['answer']}"
            session["viva_level"] = self._escalate(session.get("viva_level", "basic"))
        elif score >= 0.3:
            feedback = (
                "🟡 You're partially right, but a few key ideas are missing.\n\n"
                f"Complete answer: {question['answer']}"
            )
        else:
            feedback = (
                f"❌ Not quite. {self._explain_why_wrong(question)}\n\n"
                f"Correct explanation: {question['answer']}"
            )
            session["viva_level"] = self._deescalate(session.get("viva_level", "basic"))

        next_question = self._pick_question(session, session["viva_level"])
        if not next_question:
            closing = self.end_session(session)
            closing["reply"] = feedback + "\n\n---\n\n" + closing["reply"]
            return closing

        session["viva_current_id"] = next_question["id"]
        session.setdefault("viva_asked_ids", []).append(next_question["id"])
        session["viva_hint_count"] = 0

        reply = (
            f"{feedback}\n\n---\n\n"
            f"Next question ({session['viva_level'].title()} level):\n"
            f"{next_question['question']}"
        )
        return {
            "reply": reply,
            "suggestions": ["Give me a hint", "Skip this question", "End Viva"],
        }

    def next_question(self, session):
        if not session.get("viva_active"):
            return {"reply": "Start a viva session first.", "suggestions": ["Start Viva Mode"]}

        level = session.get("viva_level", "basic")
        question = self._pick_question(session, level)
        if not question:
            return self.end_session(session)

        session["viva_current_id"] = question["id"]
        session.setdefault("viva_asked_ids", []).append(question["id"])
        session["viva_hint_count"] = 0

        return {
            "reply": f"No problem — here's another question:\n\n{question['question']}",
            "suggestions": ["Give me a hint", "Skip this question", "End Viva"],
        }

    def give_hint(self, session):
        if not session.get("viva_active"):
            return {"reply": "Start a viva session first.", "suggestions": ["Start Viva Mode"]}

        current_id = session.get("viva_current_id")
        question = self.by_id.get(current_id)
        if not question:
            return {"reply": "No active question found — try starting a new viva session.", "suggestions": ["Start Viva Mode"]}

        hints = question.get("hints", [])
        idx = session.get("viva_hint_count", 0)

        if idx >= len(hints):
            reply = "I've already given you every hint I have for this one — give it your best attempt!"
        else:
            reply = f"💡 Hint: {hints[idx]}"
            session["viva_hint_count"] = idx + 1

        return {
            "reply": reply,
            "suggestions": ["Give me a hint", "Skip this question", "End Viva"],
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _pick_question(self, session, level):
        asked = session.get("viva_asked_ids", [])
        pool = [q for q in self.by_level.get(level, []) if q["id"] not in asked]
        if not pool:
            pool = self.by_level.get(level, [])
        if not pool:
            return None
        return random.choice(pool)

    def _evaluate_answer(self, text, question):
        keywords = [k.lower() for k in question.get("keywords", [])]
        if not keywords:
            return 0.5
        matched = sum(1 for k in keywords if k in text)
        return matched / len(keywords)

    def _explain_why_wrong(self, question):
        keywords = question.get("keywords", [])
        if len(keywords) >= 2:
            hint_terms = ", ".join(keywords[:2])
        elif keywords:
            hint_terms = keywords[0]
        else:
            hint_terms = "the key concept"
        return f"Your answer doesn't quite cover the key idea here — think again about {hint_terms}."

    def _praise(self):
        return random.choice([
            "Well explained.",
            "Great answer.",
            "Nicely reasoned.",
            "That's exactly right.",
            "Spot on.",
        ])

    def _escalate(self, level):
        idx = self.LEVEL_ORDER.index(level)
        return self.LEVEL_ORDER[min(idx + 1, len(self.LEVEL_ORDER) - 1)]

    def _deescalate(self, level):
        idx = self.LEVEL_ORDER.index(level)
        return self.LEVEL_ORDER[max(idx - 1, 0)]

    def _final_comment(self, pct):
        if pct >= 80:
            return "Excellent work — you have a strong grasp of this experiment! 🌟"
        elif pct >= 50:
            return "Good effort! Review the topics you found tricky, then try again."
        else:
            return "Don't worry — revisit the theory and procedure sections, then give the viva another go."

    @staticmethod
    def _matches_any(text, phrase_set):
        return any(phrase in text for phrase in phrase_set)