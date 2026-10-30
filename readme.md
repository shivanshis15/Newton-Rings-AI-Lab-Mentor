# 🔬 Newton's Rings AI Lab Mentor

An offline, locally-running AI lab assistant for the Newton's Rings optics
experiment, built for first-year engineering physics labs.

No internet connection or paid API is required at any point — the chatbot
runs entirely on your laptop using a local Python knowledge base and simple
keyword-based retrieval logic.

---

## ✨ Features

- Conversational chatbot that explains Theory, Apparatus, Principle,
  Formulae, Procedure, Observations, Calculations, Graph plotting,
  Precautions, Sources of Error, Applications, and Learning Outcomes.
- Interactive **Viva Mode**: asks basic → intermediate → advanced
  questions, evaluates your typed answers using keyword/concept matching,
  gives hints instead of immediately revealing the answer, and explains
  why an answer was incorrect.
- Built-in **Wavelength Calculator** (modal popup) for real observation data.
- Sidebar quick-action buttons that talk to the same chatbot (no separate
  pages to navigate).
- Clean, modern, physics-themed blue-and-white interface with chat
  bubbles, typing animation, and auto-scroll — works well for live
  presentations.

---

## 🗂 Project Structure
NewtonRingsAI/
│
├── app.py                  Flask application (all API routes)
├── requirements.txt        Python dependencies (Flask only)
├── README.md                This file
│
├── knowledge/               Local knowledge base (JSON files)
│   ├── theory.json
│   ├── apparatus.json
│   ├── principle.json
│   ├── formulae.json
│   ├── procedure.json
│   ├── observations.json
│   ├── calculations.json
│   ├── graph.json
│   ├── precautions.json
│   ├── errors.json
│   ├── applications.json
│   ├── learning_outcomes.json
│   └── viva_questions.json
│
├── engine/                  Local retrieval + chatbot logic (pure Python)
│   ├── init.py
│   ├── retriever.py          keyword search over the knowledge base
│   ├── responder.py          builds natural chatbot replies
│   └── viva_engine.py         viva session + answer evaluation
│
├── static/
│   ├── css/
│   │   └── style.css        all interface styling
│   └── js/
│       └── chat.js          chat, viva UI, and calculator modal logic
│
└── templates/
└── index.html            single-page chatbot interface

---

## ⚙️ Installation (Windows / macOS / Linux)

1. **Install Python 3.9+** if you don't already have it (check with
   `python --version` or `python3 --version`).

2. **Open the project folder in VS Code.**

3. **Create a virtual environment** (recommended, keeps things clean):

Activate it:

   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`

4. **Install dependencies:**

pip install -r requirements.txt

---

## ▶️ Running the Application

From the project root folder, with your virtual environment activated:

python app.py

You should see:
Newton's Rings AI Lab Mentor
Running locally at: http://127.0.0.1:5000

Open your browser and go to **http://127.0.0.1:5000**

That's it — everything runs locally, no internet needed after installation.

---

## 🧪 Using the App

- Type any question in the chat box, e.g. *"What is least count?"* or
  *"Explain the formula"*.
- Click sidebar buttons (Theory, Procedure, Precautions, etc.) to get
  an instant explanation without leaving the chat.
- Click **Start Viva Mode** to begin an adaptive oral-exam style quiz. Type
  your answers directly in the chat box; the mentor will evaluate them,
  give hints if you're stuck, and escalate difficulty as you improve.
- Click **Open Calculator** to launch the built-in wavelength calculator
  popup and plug in your own observation data.

---

## 🚀 Future Improvements

- Add speech-to-text so students can speak their viva answers aloud.
- Add a printable PDF lab-report generator from calculator results.
- Add support for multiple experiments beyond Newton's Rings.
- Add a lightweight local embeddings-based semantic search (still
  offline) for more flexible question understanding.

---

Built for offline, presentation-ready use — no cloud dependency, no API
keys, no internet required.