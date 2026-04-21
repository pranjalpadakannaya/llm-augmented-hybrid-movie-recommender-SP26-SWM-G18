# LLM-Augmented Hybrid Movie Recommender

**CSE 573: Semantic Web Mining · Group 18 · Spring 2026 · Arizona State University**

A hybrid movie recommendation system that combines classical data mining with deep learning and semantic modeling, surfaced through a Netflix-style frontend called **Popcorn**.

---

## Overview

Popcorn addresses the limitations of single-model recommenders by fusing three parallel recommendation branches:

| Model | Purpose | Data |
|---|---|---|
| **OCCF** (One-Class Collaborative Filtering) | Long-term preference modeling via implicit feedback | MovieLens 20M |
| **GRU4Rec** | Session-based next-item prediction via Gated Recurrent Units | Timestamped interaction sequences |
| **Knowledge Graph** | Semantic relationships: genres, cast, directors, keywords | TMDB API (~24K movies) |

Scores from all three branches are normalized and fused through a weighted re-ranking layer. A local LLM (Phi-3 Mini via Ollama) interprets natural-language queries into structured filters and generates per-recommendation explanations.

---

## Repository Structure

```
.
├── backend/
│   ├── models/
│   │   ├── gru4rec.py           # session-based next-item recommendation (GRU)
│   │   ├── kg.py                # semantic similarity via in-memory knowledge graph
│   │   └── occf.py              # long-term preference via ALS (implicit feedback)
│   ├── preprocessing/
│   │   ├── __init__.py
│   │   ├── config.py            # paths, split ratios, session gap constant
│   │   ├── clean.py             # one cleaning function per CSV file
│   │   ├── split.py             # 80/10/10 chronological split per user
│   │   ├── sessions.py          # GRU4Rec session construction
│   │   ├── storage.py           # Parquet writer and SQLite schema builder
│   │   └── tmdb_fetch.py        # async bulk TMDB metadata fetcher
│   ├── evaluation/
│   │   ├── __init__.py
│   │   ├── metrics.py           # Precision@K, Recall@K, NDCG@K, MAP@K, HitRate@K, MRR@K
│   │   ├── baselines.py         # PopularityBaseline, NeighborhoodCF
│   │   └── run_eval.py          # full evaluation runner (all 6 models)
│   ├── api.py                   # FastAPI app (5 endpoints)
│   ├── fusion.py                # hybrid fusion layer + weight tuning
│   ├── llm.py                   # Phi-3 Mini (Ollama) query parsing + explanations
│   ├── preprocess.py            # preprocessing entry point
│   └── requirements.txt
├── data/
│   └── processed/               # output of preprocessing (gitignored, reproducible)
│       ├── movies.parquet
│       ├── ratings.parquet
│       ├── links.parquet
│       ├── tags.parquet
│       ├── genome_scores.parquet
│       ├── sessions.parquet
│       ├── tmdb_metadata.parquet  # produced by tmdb_fetch.py
│       └── popcorn.db
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   └── client.ts        # typed API client (proxied to backend)
│   │   ├── components/          # Navbar, HeroBanner, MovieCard, MovieRow, RecommendationBadge, Footer
│   │   ├── pages/               # Home, Search, MovieDetail, Profile
│   │   ├── data/                # mock dataset (fallback when API is warming up)
│   │   ├── hooks/               # useScrolled
│   │   └── types/               # TypeScript interfaces
│   ├── package.json
│   └── vite.config.ts           # proxies /api → http://localhost:8000
├── .env.example                 # environment variable template
├── ml-20m/                      # raw MovieLens 20M CSVs (gitignored)
├── report/
│   ├── SP26_Group_Proposal_Group18_Project8_PDF.pdf
│   └── Group18-Project8-SP26-Group-Project-Presentation.pptx.pdf
└── README.md
```

---

## Quick Start

### 1. Environment variables

```bash
cp .env.example .env
# Fill in TMDB_READ_TOKEN and TMDB_API_KEY
```

`.env.example`:
```
TMDB_READ_TOKEN=your_tmdb_read_access_token_here
TMDB_API_KEY=your_tmdb_api_key_here
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=phi3:mini
```

### 2. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Run preprocessing (once, from the repo root or from `backend/` as shown by the script docs):
```bash
python preprocess.py
```

Fetch TMDB metadata after preprocessing (once, or re-run any time you want to refresh/enrich metadata):
```bash
python -m backend.preprocessing.tmdb_fetch
```

### 3. LLM (optional but recommended)

Install [Ollama](https://ollama.com), then:
```bash
ollama pull phi3:mini
ollama serve          # runs on http://localhost:11434 by default
```

The backend falls back gracefully if Ollama is unavailable — search still works, just without LLM-parsed intent or per-movie explanations.

### 4. Start the backend

```bash
uvicorn backend.api:app --reload
# API available at http://localhost:8000
```

On startup, the backend loads:
- `data/processed/movies.parquet`
- `data/processed/ratings.parquet`
- `data/processed/links.parquet`
- `data/processed/tmdb_metadata.parquet` if present

It also warms the recommendation models, so the frontend may show a loading state until `/api/health` reports ready.

### 5. Frontend

```bash
cd frontend
npm install
npm run dev           # dev server at http://localhost:5173
```

The Vite dev server proxies all `/api` requests to `http://localhost:8000`. Start the backend first. The frontend now expects backend data and no longer uses mock movie/demo fallbacks.

### Recommended run order

For a fresh setup:

```bash
# 1. Install backend dependencies
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Build processed MovieLens artifacts
python preprocess.py

# 3. Enrich with TMDB metadata
python -m backend.preprocessing.tmdb_fetch

# 4. In another terminal, start Ollama
ollama pull phi3:mini
ollama serve

# 5. Start the backend API
uvicorn backend.api:app --reload

# 6. In another terminal, start the frontend
cd frontend
npm install
npm run dev
```

For normal daily development after setup:

```bash
# terminal 1
ollama serve

# terminal 2
cd backend
source .venv/bin/activate
uvicorn backend.api:app --reload

# terminal 3
cd frontend
npm run dev
```

Only re-run `python -m backend.preprocessing.tmdb_fetch` when you need to create or refresh `data/processed/tmdb_metadata.parquet`.

---

## Data Preprocessing

### Prerequisites

- Python 3.10+
- The `ml-20m/` folder at the repo root ([MovieLens 20M](https://grouplens.org/datasets/movielens/20m/))

### Run

```bash
python preprocess.py
```

### Expected Output

```
Movies   : 27,278
Users    : 138,493
Ratings  : 20,000,263  (split into train / val / test)
Sessions : 480,866  (GRU4Rec train sessions, avg length 32.5 items)

data/processed/
  movies.parquet           27,278 rows     0.7 MB
  ratings.parquet      20,000,263 rows   120.3 MB
  links.parquet            27,278 rows     0.5 MB
  tags.parquet            465,541 rows     4.3 MB
  genome_scores.parquet 11,709,768 rows    19.2 MB
  sessions.parquet      15,611,192 rows   100.9 MB
  popcorn.db                               3.3 MB
```

### TMDB Metadata Fetch

Enriches each movie with overview, cast, director, keywords, runtime, poster path, backdrop path, and certification. Run after preprocessing:

```bash
python -m backend.preprocessing.tmdb_fetch
```

- Reads `data/processed/links.parquet` for the movieId ↔ tmdbId mapping
- Writes `data/processed/tmdb_metadata.parquet`
- Resumable — already-fetched rows are skipped on re-run
- Rate-limited to 40 concurrent requests (TMDB free-tier safe)
- Reads `TMDB_READ_TOKEN` from `.env`

Once this file exists, the API and Knowledge Graph automatically use richer cast/director/keyword data, and the frontend can display TMDB-backed posters, backdrops, overview text, runtime, cast, director, and maturity ratings.

---

## Preprocessing Pipeline

The pipeline runs in 7 sequential stages:

```
ml-20m/ (raw CSVs)
       |
       v
[1] Load raw CSVs
       |
       v
[2] Clean movies          --> valid movieId universe
       |
       v
[3] Clean ratings         --> valid userId universe
       |
       v
[4] Clean links, tags,
    genome-scores
       |
       v
[5] Chronological
    train / val / test
    split per user
       |
       v
[6] Build GRU4Rec
    sessions (train only)
       |
       v
[7] Write Parquet files
    + SQLite database
       |
       v
data/processed/
```

### Stage-by-Stage Details

**Stage 1: Load**
Reads all six CSVs from `ml-20m/` using pandas with explicit dtypes to control memory usage.

**Stage 2: Clean movies (`movies.csv`)**
- Extracts the year from titles using the pattern `(YYYY)` and stores it in a separate `year` column.
- Strips the year suffix from the `title` string.
- Splits pipe-separated genre strings into Python lists. Rows tagged `(no genres listed)` become empty lists.
- Drops rows with a null `movieId` and duplicate `movieId` entries.
- Output columns: `movieId (int32)`, `title (str)`, `year (Int16)`, `genres (list[str])`

**Stage 3: Clean ratings (`ratings.csv`)**
- Removes ratings for movies not present in the cleaned movies table.
- Filters to the valid rating range: 0.5 to 5.0.
- For duplicate `(userId, movieId)` pairs, keeps the most recent interaction by timestamp.
- Drops users with fewer than 5 ratings (configurable via `MIN_USER_RATINGS` in `config.py`).
- Output columns: `userId (int32)`, `movieId (int32)`, `rating (float32)`, `timestamp (int64)`

**Stage 4: Clean remaining files**

`links.csv`: Filters to valid movie IDs; casts `imdbId` and `tmdbId` to nullable integers.

`tags.csv`: Strips whitespace, drops null/empty tags, filters to valid movie and user IDs.

`genome-scores.csv`: Filters to valid movie IDs; clamps relevance values to [0.0, 1.0].

**Stage 5: Train / val / test split**

Applied per user, in chronological order by timestamp:

| Subset | Fraction | Approx. rows |
|---|---|---|
| train | 80% | 15.9 M |
| val | 10% | 2.0 M |
| test | 10% | 2.1 M |

The `split` column is added directly to `ratings.parquet`. Downstream consumers filter with `df[df["split"] == "train"]`.

**Stage 6: GRU4Rec session construction**
- Uses only training ratings, sorted by timestamp per user.
- New session begins when the gap between consecutive interactions exceeds 30 minutes (`SESSION_GAP_SECONDS` in `config.py`).
- Sessions with only one item are discarded.
- Each row in `sessions.parquet` is one interaction, identified by `sessionId` (`"{userId}_{session_index}"`) with a 0-indexed `position` column.

**Stage 7: Write output**
- All DataFrames written as Snappy-compressed Parquet via PyArrow.
- `popcorn.db` is a SQLite database containing `movies`, `genres`, `movie_genres`, `links`, and `preprocessing_log` tables.

---

## Backend API

The FastAPI server exposes 5 endpoints at `http://localhost:8000`:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | `{ ready: bool, status: str }` — poll during model warmup |
| `GET` | `/api/recommendations` | Top-N recommendations (`model`, `user_id`, `n`, `query` params) |
| `GET` | `/api/movies/{movie_id}` | Full metadata for a single movie |
| `GET` | `/api/search` | LLM-parsed semantic search with intent chips and explanations |

### `model` parameter values

| Value | Description |
|---|---|
| `hybrid` | Weighted fusion of all three models (default) |
| `occf` | OCCF only |
| `gru4rec` | GRU4Rec only |
| `kg` | Knowledge Graph only |
| `trending` | Most-rated globally |

### Start the server

```bash
# from repo root
uvicorn backend.api:app --reload

# or from inside backend/
uvicorn api:app --reload
```

Models load in a background thread on startup. `/api/health` returns `ready: false` until training completes (typically 2–5 minutes on first run).

---

## Recommendation Models

### OCCF — One-Class Collaborative Filtering

Treats observed ratings as positive implicit feedback with confidence weighting. Factorizes the user-item matrix into latent embeddings via Alternating Least Squares. Captures stable, long-term taste preferences.

**Library:** `implicit` (ALS)

**Run standalone:**
```bash
python models/occf.py
```

### GRU4Rec — Session-Based Recommendation

Constructs user sessions from timestamped interactions using a time-gap rule. A Gated Recurrent Unit network predicts the next item given the session sequence. Handles short-term, rapidly-shifting interests.

**Library:** PyTorch

**Run standalone:**
```bash
python models/gru4rec.py
```

### Knowledge Graph — Semantic Similarity

Builds an in-memory heterogeneous graph where nodes are movies, genres, cast members, directors, and keywords, and edges encode semantic relationships. TF-IDF text similarity and entity-boost scoring provide semantic recommendations and cold-start support (no user history required).

Automatically uses TMDB metadata (`tmdb_metadata.parquet`) for richer cast/keyword edges when available.

**Library:** `scikit-learn` (TF-IDF)

**Run standalone:**
```bash
python models/kg.py
```

### Hybrid Fusion Layer

Scores from all three models are min-max normalized per request, then aggregated with tunable weights (default: OCCF 0.40, GRU4Rec 0.30, KG 0.30). Weights can be optimised on a validation set via `HybridRecommender.tune_weights()` (grid search, objective: NDCG@10).

---

## LLM Augmentation (Phi-3 Mini)

`backend/llm.py` wraps a locally-running Phi-3 Mini 3.8B model via Ollama. It provides two functions:

- **`parse_query(query)`** — converts a natural-language query into structured intent: `{genres, mood, seed_movies, keywords, constraints}`
- **`generate_explanations(movies, query, intent)`** — produces a ≤12-word explanation per recommended movie

The `/api/search` endpoint uses both. The frontend displays parsed intent as colour-coded chips (blue = genre, purple = mood, green = seed movie, amber = keyword).

The system degrades gracefully if Ollama is not running — search still works via KG semantic similarity.

### Setup

```bash
# Install Ollama: https://ollama.com
ollama pull phi3:mini
ollama serve
```

---

## Evaluation

Run the full evaluation suite comparing all models on a held-out test set:

```bash
python -m backend.evaluation.run_eval
# Options: --users 500 --k 10 --k2 20
```

**Split strategy:** 80/20 per-user temporal holdout (within the already-preprocessed training split).

**Models compared:** Popularity, NeighborhoodCF (cosine, k=20), OCCF, GRU4Rec, KnowledgeGraph, Hybrid.

**Metrics:**

| Metric | K values |
|---|---|
| Precision@K, Recall@K | 10 |
| NDCG@K | 10, 20 |
| MAP@K, HitRate@K, MRR@K | 10 |

Results are printed as a table and saved to `data/processed/eval_results.json`.

---

## Model Output Format

All models return the same structure for easy fusion:

```json
{
  "movieId": 1197,
  "title": "Princess Bride, The",
  "score": 1.092614,
  "model": "OCCF"
}
```

Knowledge Graph also includes an explanation field:

```json
{
  "movieId": 6934,
  "title": "Matrix Revolutions, The",
  "score": 0.587,
  "model": "KnowledgeGraph",
  "because": ["thriller", "action", "sci-fi"]
}
```

---

## Frontend

A Netflix-inspired UI called **Popcorn** that surfaces all three recommendation models with clear attribution.

### Stack

- **React 18** + **TypeScript**
- **Vite** — fast dev server with `/api` proxy to backend
- **Tailwind CSS** — utility-first styling
- **Framer Motion** — page transitions, scroll-reveal, animated score bars
- **React Router v6** — client-side routing
- **Lucide React** — icon set

### Pages

| Route | Description |
|---|---|
| `/` | Home: auto-rotating hero banner + 6 model-labeled recommendation rows (real API data with mock fallback) |
| `/search` | Discover: LLM query interpreter with parsed intent chips, genre/model/rating filters |
| `/movie/:id` | Movie Detail: backdrop, cast, model score breakdown, "More Like This" via KG |
| `/profile` | Profile: taste analytics, model contribution chart, watch history |

### Running the Frontend

```bash
cd frontend
npm install
npm run dev       # dev server at http://localhost:5173
npm run build     # production build
```

### Design System

- **Background:** `#0f0f0f` deep black base, `#1a1a1a` card surfaces
- **Accent:** `#E50914` red for primary CTAs
- **Model color coding:**
  - OCCF: Blue `#3B82F6`
  - GRU4Rec: Emerald `#10B981`
  - Knowledge Graph: Violet `#8B5CF6`
  - Hybrid Fusion: Amber `#F59E0B`
  - Trending: Red `#EF4444`

---

## Datasets

### MovieLens 20M

- 20 million ratings across 27,278 movies by 138,493 users
- Fields: `userId`, `movieId`, `rating` (0.5–5.0), `timestamp`
- Download: [https://grouplens.org/datasets/movielens/20m/](https://grouplens.org/datasets/movielens/20m/)
- Place the unzipped folder at `ml-20m/` in the repo root.

### TMDB API

- ~24,000 movies enriched with genres, cast, crew, keywords, poster paths, overview, runtime, vote average
- Joined to MovieLens via `tmdbId` from `links.csv` (~99% coverage)
- Get a free API key at [https://www.themoviedb.org/settings/api](https://www.themoviedb.org/settings/api)

---

## Team: Group 18

| Member | Primary Responsibility |
|---|---|
| **Pranjal Padakannaya** | Project repo, MovieLens preprocessing, train/val/test splits, API layer, frontend |
| **Atharva Bhavin Thaker** | Baselines (popularity, neighborhood CF), evaluation scripts |
| **Sanjay Soralamavu Dev** | OCCF implementation, hyperparameter tuning |
| **Sachin Shivanand Shankarikoppa** | GRU4Rec session construction, training, session metrics |
| **Rahma Abuhannoud** | TMDB enrichment pipeline, Knowledge Graph construction |
| **Mawadda Abuhannoud** | Evaluation scripts, score normalization, fusion layer |

---

## Timeline

| Milestone | Deadline |
|---|---|
| Proposal | Feb 25, 2026 |
| Data preprocessing + baselines | Mar 14, 2026 |
| Main model development | Mar 23, 2026 |
| Progress demo | Apr 1, 2026 |
| Model evaluation | Apr 12, 2026 |
| System refinement | Apr 20, 2026 |
| Final demo | Apr 29, 2026 |
| Final report | May 4, 2026 |

---

## References

1. Hidasi et al., "Session-based Recommendations with Recurrent Neural Networks," ICLR 2016
2. Wang et al., "RippleNet: Propagating User Preferences on the Knowledge Graph," CIKM 2018
3. Mazumder et al., "Top-N Recommender System via Matrix Completion," AAAI 2016
4. Li et al., "Addressing Cold Start in Recommender Systems: A Semi-Supervised Co-Training Algorithm," KDD 2016
