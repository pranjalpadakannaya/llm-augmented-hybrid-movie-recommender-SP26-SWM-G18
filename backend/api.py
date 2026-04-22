from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import hashlib
import re
import threading
import time

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
TMDB_POSTER_BASE = "https://image.tmdb.org/t/p/w500"
TMDB_BACKDROP_BASE = "https://image.tmdb.org/t/p/w1280"

GENRE_PALETTE = [
    "#4FC3F7",
    "#EF5350",
    "#FFD54F",
    "#69F0AE",
    "#CE93D8",
    "#FF8A65",
]

MODEL_META = {
    "OCCF": {
        "label": "Collaborative Filtering",
        "description": "Long-term taste patterns learned from your rating history.",
        "color": "#3B82F6",
    },
    "KnowledgeGraph": {
        "label": "Knowledge Graph",
        "description": "Semantic links across genres, cast, directors, and TMDB keywords.",
        "color": "#8B5CF6",
    },
    "GRU4Rec": {
        "label": "Session-Based",
        "description": "Short-term sequence modeling from the order of your recent watches.",
        "color": "#10B981",
    },
}

_recommender: Optional[HybridRecommender] = None
_movies_df: Optional[pd.DataFrame] = None
_links_df: Optional[pd.DataFrame] = None
_tmdb_df: Optional[pd.DataFrame] = None
_ratings_df: Optional[pd.DataFrame] = None

_user_profiles_cache: dict[int, dict] = {}
_user_cards_cache: dict[int, dict] = {}
_home_cache: dict[int, tuple[float, dict]] = {}

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


def _coerce_genres(value) -> list[str]:
    if isinstance(value, list):
        return [
            str(v).strip()
            for v in value
            if str(v).strip() and str(v).strip() != "(no genres listed)"
        ]

    if value is None:
        return []

    raw = str(value).strip()
    if not raw:
        return []

    if raw.startswith("[") and raw.endswith("]"):
        raw = raw.strip("[]").replace("'", "").replace('"', "")
        parts = [p.strip() for p in raw.split(",")]
    else:
        parts = [p.strip() for p in raw.split("|")]

    return [p for p in parts if p and p != "(no genres listed)"]


def _image_url(path: str, base: str) -> str:
    clean = (path or "").strip()
    if not clean:
        return ""
    return f"{base}{clean}"


def _avatar_color(user_id: int) -> str:
    palette = ["#E50914", "#EF5350", "#F59E0B", "#10B981", "#3B82F6", "#8B5CF6"]
    return palette[user_id % len(palette)]


def _initials(name: str) -> str:
    parts = [p[0] for p in name.split() if p]
    return "".join(parts[:2]).upper() or "MV"


def _meta(movie_id: int) -> dict:
    title, year, genres, tmdb_id = f"Movie {movie_id}", 0, [], 0
    overview, director, cast, runtime, rating = "", "", [], 0, 0.0
    poster_path, backdrop_path, maturity_rating = "", "", "NR"

    if _movies_df is not None:
        row = _movies_df[_movies_df["movieId"] == movie_id]
        if not row.empty:
            title, year = _parse_title(str(row.iloc[0].get("title", "")))
            genres = _coerce_genres(row.iloc[0].get("genres", []))

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
            poster_path = str(r.get("poster_path") or "").strip()
            backdrop_path = str(r.get("backdrop_path") or "").strip()
            maturity_rating = str(r.get("certification") or "").strip() or "NR"
            if not genres:
                genres = _coerce_genres(r.get("genre_names", ""))

    return {
        "title": title,
        "year": year,
        "genres": genres,
        "tmdb_id": tmdb_id,
        "overview": overview,
        "director": director,
        "cast": cast,
        "runtime": runtime,
        "rating": rating,
        "poster_path": poster_path,
        "backdrop_path": backdrop_path,
        "maturity_rating": maturity_rating,
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
        "gradient": list(_gradient(mid)),
        "accentColor": _accent(mid),
        "director": m["director"],
        "cast": m["cast"],
        "tmdbId": m["tmdb_id"],
        "maturityRating": m["maturity_rating"],
        "posterPath": m["poster_path"],
        "posterUrl": _image_url(m["poster_path"], TMDB_POSTER_BASE),
        "backdropPath": m["backdrop_path"],
        "backdropUrl": _image_url(m["backdrop_path"], TMDB_BACKDROP_BASE),
        "recommendationSources": sources,
        "score": round(float(rec.get("score", 0)), 4),
    }


def _movie_for_profile(movie_id: int, user_rating: Optional[float] = None) -> dict:
    movie = _to_movie({"movieId": movie_id, "score": 0.0, "sources": []})
    if user_rating is not None:
        movie["userRating"] = round(float(user_rating), 1)
    return movie


def _format_member_since(timestamp: Optional[float]) -> str:
    if not timestamp:
        return "Unknown"
    return datetime.fromtimestamp(float(timestamp), tz=timezone.utc).strftime("%B %Y")


def _preferred_era(years: list[int]) -> str:
    valid = [y for y in years if y > 0]
    if not valid:
        return "Unknown"

    buckets: dict[str, int] = {}
    for year in valid:
        decade = (year // 10) * 10
        label = f"{decade}s"
        buckets[label] = buckets.get(label, 0) + 1

    return max(buckets.items(), key=lambda item: item[1])[0]


def _profile_genres(user_movies: pd.DataFrame) -> list[dict]:
    counts: dict[str, int] = {}
    for _, row in user_movies.iterrows():
        for genre in _coerce_genres(row.get("genres", [])):
            counts[genre] = counts.get(genre, 0) + 1

    total = sum(counts.values())
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:5]
    return [
        {
            "genre": genre,
            "percentage": round((count / total) * 100) if total else 0,
            "color": GENRE_PALETTE[i % len(GENRE_PALETTE)],
        }
        for i, (genre, count) in enumerate(ranked)
    ]


def _profile_top_director(movie_ids: list[int]) -> str:
    counts: dict[str, int] = {}
    for movie_id in movie_ids:
        director = _meta(int(movie_id))["director"]
        if director:
            counts[director] = counts.get(director, 0) + 1
    if not counts:
        return "Unknown"
    return max(counts.items(), key=lambda item: item[1])[0]


def _history_summary(favorite_genres: list[dict], top_director: str) -> str:
    genres = [g["genre"] for g in favorite_genres[:2]]
    if len(genres) == 2:
        genre_text = f"{genres[0]} and {genres[1]}"
    elif genres:
        genre_text = genres[0]
    else:
        genre_text = "mixed genres"

    if top_director != "Unknown":
        return f"Leans toward {genre_text}, often overlapping with {top_director} titles."
    return f"Leans toward {genre_text} based on ratings history."


def _build_profile(user_id: int, recent_n: int = 6, top_n: int = 5) -> dict:
    ratings_df = (
        _recommender.ratings_df
        if _recommender is not None and _recommender.ratings_df is not None
        else _ratings_df
    )
    if ratings_df is None:
        raise HTTPException(503, "Ratings not loaded")

    user_ratings = ratings_df[ratings_df["userId"] == user_id].copy()
    if user_ratings.empty:
        raise HTTPException(404, f"Unknown user: {user_id}")

    if "timestamp" in user_ratings.columns:
        user_ratings = user_ratings.sort_values("timestamp")

    deduped = user_ratings.drop_duplicates(subset=["movieId"], keep="last").copy()
    total_watched = int(deduped["movieId"].nunique())
    avg_rating = round(float(user_ratings["rating"].mean()), 1)
    recent_activity = (
        int(
            (
                user_ratings["timestamp"]
                >= (user_ratings["timestamp"].max() - 30 * 24 * 60 * 60)
            ).sum()
        )
        if "timestamp" in user_ratings.columns
        else len(user_ratings)
    )

    if _movies_df is not None:
        user_movies = deduped.merge(
            _movies_df[["movieId", "title", "year", "genres"]],
            on="movieId",
            how="left",
        )
    else:
        user_movies = deduped.copy()
        user_movies["year"] = 0
        user_movies["genres"] = [[] for _ in range(len(user_movies))]

    recent_rows = (
        deduped.sort_values("timestamp", ascending=False).head(recent_n)
        if "timestamp" in deduped.columns
        else deduped.tail(recent_n)
    )
    top_rows = (
        deduped.sort_values(["rating", "timestamp"], ascending=[False, False]).head(
            top_n
        )
        if "timestamp" in deduped.columns
        else deduped.sort_values("rating", ascending=False).head(top_n)
    )

    favorite_genres = _profile_genres(user_movies)
    top_director = _profile_top_director(deduped["movieId"].astype(int).tolist())
    preferred_era = _preferred_era(
        [int(y) for y in user_movies.get("year", pd.Series(dtype=int)).fillna(0).tolist()]
    )
    favorite_theme = favorite_genres[0]["genre"] if favorite_genres else "Unknown"

    recent_movies = [
        _movie_for_profile(int(row.movieId), user_rating=float(row.rating))
        for row in recent_rows.itertuples(index=False)
    ]
    top_rated_movies = [
        _movie_for_profile(int(row.movieId), user_rating=float(row.rating))
        for row in top_rows.itertuples(index=False)
    ]

    display_name = f"User {user_id}"
    contributions = []
    weights = _recommender.base_weights if _recommender is not None else MODEL_META.keys()
    iterable = (
        weights.items()
        if isinstance(weights, dict)
        else [(model, {"OCCF": 0.4, "GRU4Rec": 0.3, "KnowledgeGraph": 0.3}[model]) for model in weights]
    )
    for model, weight in iterable:
        meta = MODEL_META.get(model)
        if not meta:
            continue
        contributions.append(
            {
                "model": model,
                "label": meta["label"],
                "percentage": round(weight * 100),
                "color": meta["color"],
                "description": meta["description"],
            }
        )

    return {
        "userId": user_id,
        "id": f"u-{user_id:04d}",
        "displayName": display_name,
        "initials": _initials(display_name),
        "avatarColor": _avatar_color(user_id),
        "favoriteGenres": favorite_genres,
        "totalWatched": total_watched,
        "memberSince": _format_member_since(float(user_ratings["timestamp"].min()))
        if "timestamp" in user_ratings.columns
        else "Unknown",
        "avgRating": avg_rating,
        "activeModels": len(contributions),
        "recentActivity": recent_activity,
        "modelContributions": contributions,
        "recentMovies": recent_movies,
        "topRatedMovies": top_rated_movies,
        "summaryStats": [
            {"label": "Preferred Era", "value": preferred_era},
            {"label": "Top Director", "value": top_director},
            {"label": "Favorite Genre", "value": favorite_theme},
            {"label": "Recent Activity", "value": f"{recent_activity} ratings / 30d"},
        ],
        "historySummary": _history_summary(favorite_genres, top_director),
    }


def _user_card(user_id: int) -> dict:
    ratings_df = (
        _recommender.ratings_df
        if _recommender is not None and _recommender.ratings_df is not None
        else _ratings_df
    )
    if ratings_df is None:
        raise HTTPException(503, "Ratings not loaded")

    user_ratings = ratings_df[ratings_df["userId"] == user_id]
    if user_ratings.empty:
        raise HTTPException(404, f"Unknown user: {user_id}")

    display_name = f"User {user_id}"

    favorite_genres: list[dict] = []
    if _movies_df is not None:
        user_movies = user_ratings.merge(
            _movies_df[["movieId", "genres"]],
            on="movieId",
            how="left",
        )
        favorite_genres = _profile_genres(user_movies)

    history_summary = favorite_genres[0]["genre"] if favorite_genres else ""

    return {
        "userId": user_id,
        "displayName": display_name,
        "initials": _initials(display_name),
        "avatarColor": _avatar_color(user_id),
        "historySummary": history_summary,
        "favoriteGenres": favorite_genres[:2],
    }


def _normalize(recs: list[dict]) -> list[dict]:
    if not recs:
        return recs
    scores = [float(r["score"]) for r in recs]
    mn, mx = min(scores), max(scores)
    spread = mx - mn
    return [
        {**r, "_norm": (float(r["score"]) - mn) / spread if spread > 1e-9 else 1.0}
        for r in recs
    ]


def _wrap_model(recs: list[dict], model_name: str, n: int) -> list[dict]:
    normed = _normalize(recs[:n])
    return [
        {
            **r,
            "sources": [
                {
                    "model": model_name,
                    "score": r["score"],
                    "normalized": r.get("_norm", 0),
                }
            ],
        }
        for r in normed
    ]


def _load_dataframe(path: Path) -> Optional[pd.DataFrame]:
    if not path.exists():
        return None
    return pd.read_parquet(path)


def _load() -> None:
    global _recommender, _movies_df, _links_df, _tmdb_df, _ratings_df
    global _user_profiles_cache, _user_cards_cache, _ready, _status

    try:
        _user_profiles_cache = {}
        _user_cards_cache = {}
        _status = "loading metadata"

        _movies_df = _load_dataframe(DATA_DIR / "movies.parquet")
        _links_df = _load_dataframe(DATA_DIR / "links.parquet")
        _tmdb_df = _load_dataframe(DATA_DIR / "tmdb_metadata.parquet")
        _ratings_df = _load_dataframe(DATA_DIR / "ratings.parquet")

        _status = "loading recommendation models"
        _recommender = HybridRecommender()

        loaded_from_cache = False
        if hasattr(_recommender, "load_artifacts"):
            try:
                loaded_from_cache = bool(_recommender.load_artifacts())
            except Exception:
                loaded_from_cache = False

        if not loaded_from_cache:
            _status = "training models (first run only)"
            _recommender.load_models()

            if hasattr(_recommender, "save_artifacts"):
                try:
                    _recommender.save_artifacts()
                except Exception:
                    pass

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


@app.get("/api/home")
def home(user_id: int = 1):
    _require_ready()

    cached = _home_cache.get(user_id)
    if cached and (time.time() - cached[0]) < 300:
        return cached[1]

    rows = [
        {
            "id": "hybrid-picks",
            "title": "Hybrid Picks For You",
            "subtitle": "Fusion ranking across collaborative, session, and knowledge-graph signals",
            "query": None,
        },
        {
            "id": "hybrid-sci-fi",
            "title": "Hybrid Sci-Fi Picks",
            "subtitle": "Fusion model boosted by a science-fiction query",
            "query": "science fiction space future artificial intelligence dystopia",
        },
        {
            "id": "hybrid-thrillers",
            "title": "Hybrid Thriller Picks",
            "subtitle": "Fusion model boosted by suspense, crime, and psychological themes",
            "query": "psychological thriller crime suspense mystery dark",
        },
        {
            "id": "hybrid-drama",
            "title": "Hybrid Drama Picks",
            "subtitle": "Fusion model boosted by drama, emotion, and character-driven storytelling",
            "query": "drama emotional character relationships award-winning",
        },
        {
            "id": "hybrid-classics",
            "title": "Hybrid Classics",
            "subtitle": "Fusion model boosted by timeless, critically acclaimed cinema",
            "query": "classic masterpiece iconic cinema all-time great",
        },
        {
            "id": "hybrid-trending",
            "title": "Hybrid Trending",
            "subtitle": "Fusion model over popular and active taste signals",
            "query": "popular trending widely loved recent favorites",
        },
    ]

    hero = _recommender.recommend(user_id=user_id, N=5)["recommendations"]

    out_rows = []
    for row in rows:
        if row["query"]:
            recs = _recommender.recommend(
                user_id=user_id, N=10, query=row["query"]
            )["recommendations"]
        else:
            recs = _recommender.recommend(user_id=user_id, N=10)["recommendations"]

        out_rows.append(
            {
                "id": row["id"],
                "title": row["title"],
                "subtitle": row["subtitle"],
                "movies": [_to_movie(r) for r in recs],
            }
        )

    data = {
        "heroMovies": [_to_movie(r) for r in hero],
        "rows": out_rows,
    }

    _home_cache[user_id] = (time.time(), data)
    return data


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
            raw.append(
                {
                    "movieId": movie_id,
                    "score": norm_score,
                    "sources": [
                        {
                            "model": "Trending",
                            "score": norm_score,
                            "normalized": norm_score,
                        }
                    ],
                }
            )
    else:
        raise HTTPException(400, f"Unknown model: {model}")

    return {"movies": [_to_movie(r) for r in raw]}


@app.get("/api/movies/{movie_id}")
def movie_detail(movie_id: int):
    _require_ready()
    m = _meta(movie_id)
    return {
        "id": movie_id,
        "movieLensId": movie_id,
        "title": m["title"],
        "year": m["year"],
        "rating": m["rating"],
        "runtime": m["runtime"],
        "genres": m["genres"] or ["Unknown"],
        "overview": m["overview"],
        "gradient": list(_gradient(movie_id)),
        "accentColor": _accent(movie_id),
        "director": m["director"],
        "cast": m["cast"],
        "tmdbId": m["tmdb_id"],
        "maturityRating": m["maturity_rating"],
        "posterPath": m["poster_path"],
        "posterUrl": _image_url(m["poster_path"], TMDB_POSTER_BASE),
        "backdropPath": m["backdrop_path"],
        "backdropUrl": _image_url(m["backdrop_path"], TMDB_BACKDROP_BASE),
        "recommendationSources": [],
        "score": 0.0,
    }


@app.get("/api/profile")
def profile(user_id: int = 1, recent_n: int = 6, top_n: int = 5):
    _require_ready()
    return _build_profile(user_id=user_id, recent_n=recent_n, top_n=top_n)


@app.get("/api/users")
def users(limit: int = 8):
    ratings_df = (
        _recommender.ratings_df
        if _recommender is not None and _recommender.ratings_df is not None
        else _ratings_df
    )
    if ratings_df is None:
        raise HTTPException(503, "Ratings not loaded")

    counts = ratings_df.groupby("userId").size().sort_values(ascending=False)
    user_ids = counts.index.astype(int).tolist()[:limit]

    results = []
    for user_id in user_ids:
        cached = _user_cards_cache.get(user_id)
        if cached is None:
            cached = _user_card(user_id)
            _user_cards_cache[user_id] = cached
        results.append(cached)

    return {"users": results}


@app.get("/api/search")
def search(query: str, user_id: int = 1, n: int = 20):
    _require_ready()

    intent = _llm.parse_query(query)

    effective_query = query
    seed = intent.get("seed_movies", [])
    keywords = intent.get("keywords", [])
    if seed or keywords:
        parts = list(seed) + list(keywords) + intent.get("genres", [])
        effective_query = " ".join(parts) if parts else query

    raw = _recommender.kg.recommend_from_query(effective_query, N=n * 2)

    if seed and len(raw) < n:
        for title in seed[:2]:
            extra = _recommender.kg.recommend_from_query(title, N=10)
            seen_ids = {int(r["movieId"]) for r in raw}
            raw += [r for r in extra if int(r["movieId"]) not in seen_ids]

    normed = _normalize(raw[:n])
    movie_dicts = [
        {
            **r,
            "sources": [
                {
                    "model": "KnowledgeGraph",
                    "score": r["score"],
                    "normalized": r.get("_norm", 0),
                }
            ],
        }
        for r in normed
    ]

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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)