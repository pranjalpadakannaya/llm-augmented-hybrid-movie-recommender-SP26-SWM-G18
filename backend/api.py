from __future__ import annotations

import hashlib
import re
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:
    pass

try:
    from backend.fusion import HybridRecommender
    from backend import llm as _llm
except ImportError:
    from fusion import HybridRecommender
    import llm as _llm

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "processed"

_recommender: Optional[HybridRecommender] = None
_movies_df: Optional[pd.DataFrame] = None
_links_df: Optional[pd.DataFrame] = None
_tmdb_df: Optional[pd.DataFrame] = None
_ready = False
_status = "initializing"


def _gradient(movie_id: int) -> tuple[str, str]:
    h = int(hashlib.md5(str(movie_id).encode()).hexdigest(), 16)
    hue1 = h % 360
    hue2 = (hue1 + 40 + (h >> 8) % 50) % 360
    return f"hsl({hue1},55%,10%)", f"hsl({hue2},55%,16%)"


def _accent(movie_id: int) -> str:
    h = int(hashlib.md5(f"ac{movie_id}".encode()).hexdigest(), 16)
    return f"hsl({h % 360},65%,65%)"


def _parse_title(raw: str) -> tuple[str, int]:
    m = re.search(r"\((\d{4})\)\s*$", raw)
    if m:
        return raw[: m.start()].strip(), int(m.group(1))
    return raw.strip(), 0


def _meta(movie_id: int) -> dict:
    title, year, genres, tmdb_id = f"Movie {movie_id}", 0, [], 0
    overview, director, cast, runtime, rating = "", "", [], 0, 0.0

    if _movies_df is not None:
        row = _movies_df[_movies_df["movieId"] == movie_id]
        if not row.empty:
            title, year = _parse_title(str(row.iloc[0].get("title", "")))
            genres = [
                g for g in str(row.iloc[0].get("genres", "")).split("|")
                if g and g != "(no genres listed)"
            ]

    if _links_df is not None:
        link = _links_df[_links_df["movieId"] == movie_id]
        if not link.empty:
            try:
                tmdb_id = int(link.iloc[0].get("tmdbId", 0) or 0)
            except (ValueError, TypeError):
                pass

    if _tmdb_df is not None:
        trow = _tmdb_df[_tmdb_df["movieId"] == movie_id]
        if not trow.empty:
            r = trow.iloc[0]
            overview = str(r.get("overview") or "").strip()
            director = str(r.get("director") or "").split("|")[0].strip()
            cast_raw = str(r.get("cast") or "")
            cast = [c.strip() for c in cast_raw.split("|") if c.strip()][:8]
            try:
                runtime = int(r.get("runtime") or 0)
            except (ValueError, TypeError):
                runtime = 0
            try:
                rating = round(float(r.get("vote_average") or 0.0), 1)
            except (ValueError, TypeError):
                rating = 0.0
            if not genres:
                genre_raw = str(r.get("genre_names") or "")
                genres = [g.strip() for g in genre_raw.split("|") if g.strip()]

    return {
        "title": title, "year": year, "genres": genres, "tmdb_id": tmdb_id,
        "overview": overview, "director": director, "cast": cast,
        "runtime": runtime, "rating": rating,
    }


def _build_sources(raw_sources: list[dict], because: list[str]) -> list[dict]:
    out = []
    for s in raw_sources:
        model = s["model"]
        norm = float(s.get("normalized", s.get("score", 0)))
        if model == "KnowledgeGraph" and because:
            reason = "Because: " + "; ".join(because[:2])
        elif model == "OCCF":
            reason = "Users with similar long-term taste also enjoyed this"
        elif model == "GRU4Rec":
            reason = "Follows naturally from your recent watch session"
        elif model == "KnowledgeGraph":
            reason = "Semantic match via knowledge graph"
        elif model == "Hybrid":
            reason = "Top-ranked by all three recommendation models combined"
        elif model == "Trending":
            reason = "Popular across all users this week"
        else:
            reason = "Recommended for you"
        out.append({"model": model, "score": round(norm, 3), "reason": reason})
    return out


def _to_movie(rec: dict, explanation: str = "") -> dict:
    mid = int(rec["movieId"])
    m = _meta(mid)
    grad = _gradient(mid)
    sources = _build_sources(rec.get("sources", []), rec.get("because", []))
    if explanation and sources:
        sources[0]["reason"] = explanation
    return {
        "id": mid,
        "movieLensId": mid,
        "title": m["title"],
        "year": m["year"],
        "rating": m["rating"],
        "runtime": m["runtime"],
        "genres": m["genres"] or ["Unknown"],
        "overview": m["overview"],
        "gradient": list(grad),
        "accentColor": _accent(mid),
        "director": m["director"],
        "cast": m["cast"],
        "tmdbId": m["tmdb_id"],
        "maturityRating": "NR",
        "recommendationSources": sources,
        "score": round(float(rec.get("score", 0)), 4),
    }


def _normalize(recs: list[dict]) -> list[dict]:
    if not recs:
        return recs
    scores = [float(r["score"]) for r in recs]
    mn, mx = min(scores), max(scores)
    spread = mx - mn
    return [{**r, "_norm": (float(r["score"]) - mn) / spread if spread > 1e-9 else 1.0} for r in recs]


def _wrap_model(recs: list[dict], model_name: str, n: int) -> list[dict]:
    normed = _normalize(recs[:n])
    return [
        {**r, "sources": [{"model": model_name, "score": r["score"], "normalized": r.get("_norm", 0)}]}
        for r in normed
    ]


def _load() -> None:
    global _recommender, _movies_df, _links_df, _tmdb_df, _ready, _status
    try:
        _status = "loading metadata"
        if (DATA_DIR / "movies.parquet").exists():
            _movies_df = pd.read_parquet(DATA_DIR / "movies.parquet")
        if (DATA_DIR / "links.parquet").exists():
            _links_df = pd.read_parquet(DATA_DIR / "links.parquet")
        if (DATA_DIR / "tmdb_metadata.parquet").exists():
            _tmdb_df = pd.read_parquet(DATA_DIR / "tmdb_metadata.parquet")

        _status = "training models (this takes a few minutes on first run)"
        _recommender = HybridRecommender()
        _recommender.load_models()

        _ready = True
        _status = "ready"
    except Exception as exc:
        _status = f"error: {exc}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    threading.Thread(target=_load, daemon=True).start()
    yield


app = FastAPI(title="Popcorn Recommender API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _require_ready():
    if not _ready:
        raise HTTPException(503, detail={"ready": False, "status": _status})


@app.get("/api/health")
def health():
    return {"ready": _ready, "status": _status}


@app.get("/api/recommendations")
def recommendations(
    user_id: int = 1,
    model: str = "hybrid",
    n: int = 10,
    query: Optional[str] = None,
):
    _require_ready()
    pool = n * 3

    if model == "hybrid":
        result = _recommender.recommend(user_id=user_id, N=n, query=query)
        return {"movies": [_to_movie(r) for r in result["recommendations"]]}

    if model == "occf":
        raw = _wrap_model(_recommender.occf.recommend(user_id, N=pool), "OCCF", n)

    elif model == "gru4rec":
        history = _recommender._get_history(user_id)
        base = (
            _recommender.gru.recommend_from_history(history, N=pool)
            if history
            else _recommender.gru.recommend_for_user(user_id, N=pool)
        )
        raw = _wrap_model(base, "GRU4Rec", n)

    elif model == "kg":
        history = _recommender._get_history(user_id, limit=5)
        if query:
            base = _recommender.kg.recommend_from_query(query, N=pool)
        elif history:
            base = _recommender.kg.recommend_from_history(history, N=pool)
        else:
            base = _recommender.kg.recommend_from_query("popular movies", N=pool)
        raw = _wrap_model(base, "KnowledgeGraph", n)

    elif model == "trending":
        if _recommender.ratings_df is None:
            raise HTTPException(503, "Ratings not loaded")
        counts = _recommender.ratings_df.groupby("movieId").size().nlargest(n)
        mx = float(counts.max())
        raw = []
        for movie_id, count in counts.items():
            norm_score = float(count) / mx
            raw.append({
                "movieId": movie_id,
                "score": norm_score,
                "sources": [{"model": "Trending", "score": norm_score, "normalized": norm_score}],
            })
    else:
        raise HTTPException(400, f"Unknown model: {model}")

    return {"movies": [_to_movie(r) for r in raw]}


@app.get("/api/movies/{movie_id}")
def movie_detail(movie_id: int):
    _require_ready()
    m = _meta(movie_id)
    grad = _gradient(movie_id)
    return {
        "id": movie_id,
        "movieLensId": movie_id,
        "title": m["title"],
        "year": m["year"],
        "rating": m["rating"],
        "runtime": m["runtime"],
        "genres": m["genres"] or ["Unknown"],
        "overview": m["overview"],
        "gradient": list(grad),
        "accentColor": _accent(movie_id),
        "director": m["director"],
        "cast": m["cast"],
        "tmdbId": m["tmdb_id"],
        "maturityRating": "NR",
        "recommendationSources": [],
        "score": 0.0,
    }


@app.get("/api/search")
def search(query: str, user_id: int = 1, n: int = 20):
    _require_ready()

    # Parse query with LLM (graceful fallback if Ollama unavailable)
    intent = _llm.parse_query(query)

    # Build effective search query from structured intent
    effective_query = query
    seed = intent.get("seed_movies", [])
    keywords = intent.get("keywords", [])
    if seed or keywords:
        parts = list(seed) + list(keywords) + intent.get("genres", [])
        effective_query = " ".join(parts) if parts else query

    # Use KG for semantic search; boost with seed movies
    raw = _recommender.kg.recommend_from_query(effective_query, N=n * 2)

    # If seed movies mentioned, also pull KG results for each seed title
    if seed and len(raw) < n:
        for title in seed[:2]:
            extra = _recommender.kg.recommend_from_query(title, N=10)
            seen_ids = {int(r["movieId"]) for r in raw}
            raw += [r for r in extra if int(r["movieId"]) not in seen_ids]

    normed = _normalize(raw[:n])
    movie_dicts = [
        {
            **r,
            "sources": [{"model": "KnowledgeGraph", "score": r["score"], "normalized": r.get("_norm", 0)}],
        }
        for r in normed
    ]

    # Generate LLM explanations (no-op if Ollama unavailable)
    explanations = _llm.generate_explanations(
        movies=[
            {
                "id": int(r["movieId"]),
                "title": _meta(int(r["movieId"]))["title"],
                "year": _meta(int(r["movieId"]))["year"],
                "genres": _meta(int(r["movieId"]))["genres"],
                "because": r.get("because", []),
            }
            for r in normed[:10]
        ],
        query=query,
        parsed_intent=intent,
    )

    movies = [
        _to_movie(r, explanation=explanations.get(str(int(r["movieId"])), ""))
        for r in movie_dicts
    ]

    # Build human-readable interpretation text
    parts = []
    if intent.get("genres"):
        parts.append("genres: " + ", ".join(intent["genres"]))
    if intent.get("mood"):
        parts.append("mood: " + intent["mood"])
    if intent.get("keywords"):
        parts.append("themes: " + ", ".join(intent["keywords"][:4]))
    interpreted = f'"{query}"' + (f" — {'; '.join(parts)}" if parts else "")

    return {
        "interpreted": interpreted,
        "filters": intent.get("genres", []) or ["Knowledge Graph"],
        "parsedIntent": intent,
        "movies": movies,
    }
