"""
Newton's Rings AI Lab Mentor
Main Flask application entry point.

This file wires together:
- knowledge/*.json  -> the local knowledge base
- engine/retriever.py -> keyword-based local search over the knowledge base
- engine/responder.py -> turns retrieved knowledge into natural chatbot replies
- engine/viva_engine.py -> interactive viva examination logic

Everything runs 100% locally. No external APIs, no internet required.
"""

from flask import Flask, render_template, request, jsonify, session
import os
import random

from engine.retriever import KnowledgeRetriever
from engine.responder import ChatResponder
from engine.viva_engine import VivaEngine

app = Flask(__name__)
app.secret_key = "newton_rings_ai_lab_mentor_secret_key_2024"  # local session use only

# ---------------------------------------------------------------------------
# Initialize the knowledge base, retriever, responder, and viva engine once
# at startup so every request reuses the same in-memory objects (fast, no
# repeated disk reads).
# ---------------------------------------------------------------------------
KNOWLEDGE_DIR = os.path.join(os.path.dirname(__file__), "knowledge")

retriever = KnowledgeRetriever(knowledge_dir=KNOWLEDGE_DIR)
responder = ChatResponder(retriever=retriever)
viva_engine = VivaEngine(knowledge_dir=KNOWLEDGE_DIR)


# ---------------------------------------------------------------------------
# PAGE ROUTE
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    """Single-page chatbot interface (chat + sidebar quick-action buttons)."""
    return render_template("index.html")


# ---------------------------------------------------------------------------
# CHAT API
# ---------------------------------------------------------------------------
@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Main chat endpoint. Accepts a free-text message from the student and
    returns a natural-language reply plus a list of suggested follow-up
    topics. Maintains light conversation context via Flask session
    (last topic discussed) so the responder can handle follow-ups like
    "explain more" or "why is that?".
    """
    data = request.get_json(silent=True) or {}
    user_message = (data.get("message") or "").strip()

    if not user_message:
        return jsonify({
            "reply": "I didn't catch that — could you type your question again?",
            "suggestions": []
        })

    # If the student is currently in an active viva session, route their
    # message to the viva engine instead of the general knowledge responder.
    if session.get("viva_active"):
        result = viva_engine.handle_answer(session, user_message)
        return jsonify(result)

    last_topic = session.get("last_topic")
    result = responder.respond(user_message, last_topic=last_topic)

    # Remember topic for contextual follow-ups ("tell me more", "why?")
    session["last_topic"] = result.get("topic", last_topic)

    return jsonify({
        "reply": result["reply"],
        "suggestions": result.get("suggestions", [])
    })


# ---------------------------------------------------------------------------
# QUICK ACTION BUTTONS (Theory / Procedure / Precautions / Applications /
# Calculator-intro). These reuse the same responder so the sidebar buttons
# feel like part of the same conversation rather than separate pages.
# ---------------------------------------------------------------------------
@app.route("/api/topic/<topic_name>", methods=["GET"])
def topic_shortcut(topic_name):
    """
    Called when the student clicks a sidebar button (Theory, Apparatus,
    Principle, Formulae, Procedure, Observation, Calculations, Graph,
    Precautions, Errors, Applications, Learning Outcomes).
    """
    result = responder.respond_to_topic(topic_name)
    session["last_topic"] = topic_name
    return jsonify({
        "reply": result["reply"],
        "suggestions": result.get("suggestions", [])
    })


# ---------------------------------------------------------------------------
# VIVA MODE API
# ---------------------------------------------------------------------------
@app.route("/api/viva/start", methods=["POST"])
def viva_start():
    """
    Starts a new viva session. Resets any previous viva state in the
    session, picks a random Basic-level question to begin with, and marks
    the session as being 'in viva mode' so subsequent /api/chat messages
    are routed to the viva engine instead of general chat.
    """
    result = viva_engine.start_session(session)
    return jsonify(result)


@app.route("/api/viva/next", methods=["POST"])
def viva_next():
    """Skip current question and get a new one at the same difficulty level."""
    result = viva_engine.next_question(session)
    return jsonify(result)


@app.route("/api/viva/hint", methods=["POST"])
def viva_hint():
    """Student explicitly asks for a hint on the current viva question."""
    result = viva_engine.give_hint(session)
    return jsonify(result)


@app.route("/api/viva/end", methods=["POST"])
def viva_end():
    """Ends the viva session and returns a summary/performance report."""
    result = viva_engine.end_session(session)
    return jsonify(result)


# ---------------------------------------------------------------------------
# CALCULATOR API
# ---------------------------------------------------------------------------
@app.route("/api/calculate", methods=["POST"])
def calculate():
    """
    Computes the wavelength of sodium light from Newton's Rings data.

    Expects JSON body with:
        d_n_plus_m : float  (D^2 of the (n+m)th ring, in cm^2)  [already squared]
        d_n        : float  (D^2 of the nth ring, in cm^2)      [already squared]
        m          : int    (ring interval)
        R          : float  (radius of curvature of lens, in cm)

    Returns computed wavelength in cm and Angstrom, plus percentage error
    against the standard sodium light value (5893 Angstrom).
    """
    data = request.get_json(silent=True) or {}
    try:
        d_n_plus_m = float(data.get("d_n_plus_m"))
        d_n = float(data.get("d_n"))
        m = float(data.get("m"))
        R = float(data.get("R"))
    except (TypeError, ValueError):
        return jsonify({
            "error": "Please provide valid numeric values for D²(n+m), D²(n), m, and R."
        }), 400

    if m == 0 or R == 0:
        return jsonify({"error": "m and R must not be zero."}), 400

    diff = d_n_plus_m - d_n
    wavelength_cm = diff / (4 * m * R)
    wavelength_angstrom = wavelength_cm * 1e8  # 1 cm = 1e8 Angstrom

    standard_value = 5893.0  # Angstrom
    percent_error = abs(standard_value - wavelength_angstrom) / standard_value * 100

    # Simple sanity flag for the student, mirroring what a real lab mentor
    # would point out (visible spectrum range check).
    warning = None
    if not (4000 <= wavelength_angstrom <= 7000):
        warning = (
            "This value falls outside the visible spectrum (4000–7000 Å). "
            "Double-check your value of R — this is the most common cause "
            "of an unrealistic result."
        )
    elif percent_error > 10:
        warning = (
            f"Your percentage error ({percent_error:.2f}%) is quite high for "
            "this experiment. Recheck your least count and R value first."
        )

    return jsonify({
        "diff_d_squared": round(diff, 6),
        "wavelength_cm": wavelength_cm,
        "wavelength_angstrom": round(wavelength_angstrom, 2),
        "percent_error": round(percent_error, 2),
        "standard_value_angstrom": standard_value,
        "warning": warning
    })


if __name__ == "__main__":
    print("=" * 60)
    print(" Newton's Rings AI Lab Mentor")
    print(" Running locally at: http://127.0.0.1:5000")
    print(" Press CTRL+C to stop the server.")
    print("=" * 60)
    app.run(debug=True, host="127.0.0.1", port=5000)