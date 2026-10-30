"""
KnowledgeRetriever
------------------
Loads all topic JSON files from the local knowledge/ directory into memory
and provides simple, fully offline keyword-based search over them.

No external ML libraries, no embeddings, no internet calls — just plain
Python set/string operations. This keeps the whole application dependency
light (Flask only) while still feeling "smart enough" for a lab-mentor
chatbot.
"""

import os
import json
import re


class KnowledgeRetriever:

    # Maps the topic key (used in URLs / sidebar buttons / session state)
    # to the corresponding JSON filename inside knowledge/.
    TOPIC_FILES = {
        "theory": "theory.json",
        "apparatus": "apparatus.json",
        "principle": "principle.json",
        "formulae": "formulae.json",
        "procedure": "procedure.json",
        "observations": "observations.json",
        "calculations": "calculations.json",
        "graph": "graph.json",
        "precautions": "precautions.json",
        "errors": "errors.json",
        "applications": "applications.json",
        "learning_outcomes": "learning_outcomes.json",
    }

    def __init__(self, knowledge_dir):
        self.knowledge_dir = knowledge_dir
        self.topics = {}
        self._load_all()

        print("\nLoaded topics:")
        print(self.topics.keys())

    def _load_all(self):
        """Load every topic JSON file into self.topics keyed by topic key."""
        for topic_key, filename in self.TOPIC_FILES.items():
            path = os.path.join(self.knowledge_dir, filename)
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    self.topics[topic_key] = json.load(f)
            else:
                print(f"[KnowledgeRetriever] Warning: missing file {path}")
        print("\nLOADED KNOWLEDGE")
        for k, v in self.topics.items():
            print(k, "->", v.get("title"))

    def get_topic(self, topic_key):
        """Return the raw dict for a given topic key, or None if not found."""
        print("LOOKING FOR:", topic_key)
        print("AVAILABLE:", self.topics.keys())
        return self.topics.get(topic_key)

    def all_topic_keys(self):
        """Return a list of every loaded topic key."""
        return list(self.topics.keys())

    @staticmethod
    def _tokenize(text):
        """Lowercase, strip punctuation, and split into a set of word tokens."""
        if not text:
            return set()
        return set(re.findall(r"[a-z0-9]+", text.lower()))

    def _topic_vocabulary(self, topic_key):
        """ Build a searchable vocabulary from the entire JSON document instead of only the title and keywords. """
        data = self.topics.get(topic_key, {})
        vocab = set()

        def extract_text(obj):
            if isinstance(obj, dict):
                for value in obj.values():
                    extract_text(value)
            elif isinstance(obj, list):
                for item in obj:
                    extract_text(item)
            elif isinstance(obj, str):
                vocab.update(self._tokenize(obj))
        extract_text(data)
        vocab.update(self._tokenize(topic_key.replace("_", " ")))
        return vocab

    def search(self, query):
        """
        Score every topic against the query using token overlap, and return
        the best matching (topic_key, score) pair.

        Scoring combines:
        - a Jaccard-style overlap ratio (intersection / union), so short,
          highly specific queries still score well
        - a small bonus per raw overlapping token, so topics that share more
          exact keywords are favored over topics that merely have a similar
          overall vocabulary size

        Returns (None, 0.0) if the query has no usable tokens or nothing
        matches at all.
        """
        print(f"\nIncoming query: {query}")

        intent_map = {
            # THEORY
            "thin film": "theory",
            "interference": "theory",
            "thin film interference": "theory",
            "newton's rings": "theory",
            "newton rings": "theory",
            "rings": "theory",
            "central spot": "theory",
            "dark fringe": "theory",
            "bright fringe": "theory",
            "concentric": "theory",
            "newton": "theory",
            "ring": "theory",
            "rings": "theory",
            "interference": "theory",
            "thin film": "theory",
            "thin-film": "theory",
            "air film": "theory",
            "dark": "theory",
            "bright": "theory",
            "fringe": "theory",
            "formation": "theory",
            "formed": "theory",
            "circular": "theory",
            "central": "theory",
            "theory": "theory",
            "explain the theory": "theory",

            # Principle
            "principle": "principle",
            "working principle": "principle",
            "how does it work": "principle",

            # Apparatus
            "apparatus": "apparatus",
            "equipment": "apparatus",
            "instrument": "apparatus",
            "setup":"apparatus",
            "microscope":"apparatus",
            "lens": "apparatus",
            "sodium": "apparatus",

            # Procedure
            "procedure": "procedure",
            "steps": "procedure",
            "perform": "procedure",
            "method": "procedure",
            "experiment": "procedure",

            # Formulae
            "formula": "formulae",
            "formulae": "formulae",
            "equation": "formulae",

            # Calculations
            "calculate": "calculations",
            "calculation": "calculations",
            "wavelength": "calculations",
            "least count": "calculations",

            # Graph
            "graph": "graph",
            "plot": "graph",

            # Observations
            "observation": "observations",
            "reading": "observations",

            # Precautions
            "precaution": "precautions",

            # Errors
            "error": "errors",
            "mistake": "errors",

            # Applications
            "application": "applications",
            "applications": "applications",
            "uses": "applications",

            # Learning outcomes
            "learning outcome": "learning_outcomes",
            "learning outcomes": "learning_outcomes",
            "objective": "learning_outcomes", }

        query_lower = query.lower()
        print("QUERY:", query_lower)

        for keyword, topic in intent_map.items():
            if keyword in query_lower:
                print (f"MATCHED -> {keyword} => {topic}")
                return topic, 1.0
            
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return None, 0.0

        best_topic = None
        best_score = 0.0

        for topic_key in self.topics.keys():
            vocab = self._topic_vocabulary(topic_key)
            if not vocab:
                continue

            overlap = query_tokens.intersection(vocab)
            if not overlap:
                continue

            union = query_tokens.union(vocab)
            jaccard = len(overlap) / len(union)
            bonus = 0.06 * len(overlap)
            score = jaccard + bonus

            if score > best_score:
                best_score = score
                best_topic = topic_key

        print(f"\nDEBUG: '{query}' -> {best_topic} ({best_score})")
        return best_topic, best_score

    def keyword_hits(self, query, topic_key):
        """
        Return the set of tokens from `query` that matched the given topic's
        vocabulary. Useful for debugging / potential future explanation of
        why a topic was chosen.
        """
        query_tokens = self._tokenize(query)
        vocab = self._topic_vocabulary(topic_key)
        return query_tokens.intersection(vocab)