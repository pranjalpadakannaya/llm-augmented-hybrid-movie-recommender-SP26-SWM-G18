"""
LLM augmentation layer via Ollama (local Phi-3 Mini).

Two responsibilities:
  1. parse_query   — converts a natural-language query into structured intent
  2. generate_explanations — produces one-sentence per-recommendation explanations
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Optional

import requests

logger = logging.getLogger(__name__)

_OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
_DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "phi3:mini")

_PARSE_PROMPT = """\
You are a structured data extractor for a movie recommendation system.
Parse the user query into a JSON object. Return ONLY valid JSON — no prose.

User query: "{query}"

JSON schema (fill every field; use empty list/string if not applicable):
{{
  "genres": [],
  "mood": "",
  "seed_movies": [],
  "keywords": [],
  "constraints": {{}}
}}

Rules:
- genres: subset of [Action, Adventure, Animation, Comedy, Crime, Documentary, Drama, Fantasy, Horror, Mystery, Romance, Sci-Fi, Thriller, War, Western]
- mood: 1-4 descriptive words, e.g. "dark cerebral intense"
- seed_movies: movie titles explicitly mentioned or directly implied
- keywords: thematic tags, e.g. ["time travel", "heist", "dystopia"]
- constraints: optional, e.g. {{"min_year": 2000}}
"""

_EXPLAIN_PROMPT = """\
You are a movie recommendation assistant. Generate a short, natural one-sentence explanation \
for why each movie matches the user's query. Return ONLY valid JSON.

User query: "{query}"
Query intent: {intent}

Movies (id → title, genres, graph links):
{movies_text}

Return JSON: {{"explanations": {{"<id>": "<≤12-word sentence>", ...}}}}
"""


def _call(prompt: str, model: str = _DEFAULT_MODEL, timeout: int = 30) -> Optional[str]:
    try:
        r = requests.post(
            f"{_OLLAMA_URL}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False, "format": "json"},
            timeout=timeout,
        )
        r.raise_for_status()
        return r.json().get("response", "")
    except Exception as exc:
        logger.warning("Ollama error: %s", exc)
        return None


def _parse_json(text: str) -> Optional[dict]:
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            pass
    return None


_INTENT_FALLBACK: dict = {
    "genres": [], "mood": "", "seed_movies": [], "keywords": [], "constraints": {}
}


def parse_query(query: str, model: str = _DEFAULT_MODEL) -> dict:
    """Parse a natural-language query → structured intent dict."""
    raw = _call(_PARSE_PROMPT.format(query=query), model=model, timeout=25)
    parsed = _parse_json(raw or "")
    if not parsed:
        return _INTENT_FALLBACK.copy()
    return {
        "genres": [g for g in parsed.get("genres", []) if isinstance(g, str)][:5],
        "mood": str(parsed.get("mood", ""))[:80],
        "seed_movies": [m for m in parsed.get("seed_movies", []) if isinstance(m, str)][:3],
        "keywords": [k for k in parsed.get("keywords", []) if isinstance(k, str)][:8],
        "constraints": parsed.get("constraints", {}),
    }


def generate_explanations(
    movies: list[dict],
    query: str,
    parsed_intent: dict,
    model: str = _DEFAULT_MODEL,
) -> dict[str, str]:
    """
    Generate one-sentence explanations for a list of movies.
    movies: list of dicts with keys id, title, year, genres, because (optional)
    Returns {str(movie_id): explanation}
    """
    if not movies:
        return {}

    lines = []
    for m in movies[:10]:
        because = ", ".join(m.get("because", [])[:3])
        genre_str = ", ".join((m.get("genres") or [])[:2])
        line = f'  {m["id"]}: {m["title"]} ({m.get("year", "")}) [{genre_str}]'
        if because:
            line += f' — links: {because}'
        lines.append(line)

    prompt = _EXPLAIN_PROMPT.format(
        query=query,
        intent=json.dumps(parsed_intent, ensure_ascii=False),
        movies_text="\n".join(lines),
    )
    raw = _call(prompt, model=model, timeout=40)
    parsed = _parse_json(raw or "")
    if not parsed or "explanations" not in parsed:
        return {}
    return {str(k): str(v) for k, v in parsed["explanations"].items()}


def is_available(model: str = _DEFAULT_MODEL) -> bool:
    """Return True if Ollama is running and the model is loaded."""
    try:
        r = requests.get(f"{_OLLAMA_URL}/api/tags", timeout=3)
        if r.status_code == 200:
            loaded = [m["name"] for m in r.json().get("models", [])]
            base = model.split(":")[0]
            return any(base in name for name in loaded)
    except Exception:
        pass
    return False
