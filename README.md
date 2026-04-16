# LLM-Augmented Hybrid Movie Recommender

**CSE 573: Semantic Web Mining · Group 18 · Spring 2026 · Arizona State University**

A hybrid movie recommendation system that combines classical data mining with deep learning and semantic modeling, surfaced through a Netflix-style frontend.

---

## Overview

CineAI addresses the limitations of single-model recommenders by fusing three parallel recommendation branches:

| Model | Purpose | Data |
|---|---|---|
| **OCCF** (One-Class Collaborative Filtering) | Long-term preference modeling via implicit feedback | MovieLens 20M |
| **GRU4Rec** | Session-based next-item prediction via Gated Recurrent Units | Timestamped interaction sequences |
| **Knowledge Graph** (Neo4j + TMDB) | Semantic relationships: genres, cast, directors, keywords | TMDB API (~24K movies) |

Scores from all three branches are normalized and fused through a weighted re-ranking layer. An LLM layer interprets natural-language queries into structured filters applied before retrieval.

---

## Repository Structure

```
.
├── backend/
│   ├── preprocessing/
│   │   ├── __init__.py
│   │   ├── config.py        # paths, split ratios, session gap constant
│   │   ├── clean.py         # one cleaning function per CSV file
│   │   ├── split.py         # 80/10/10 chronological split per user
│   │   ├── sessions.py      # GRU4Rec session construction
│   │   └── storage.py       # Parquet writer and SQLite schema builder
│   ├── preprocess.py        # main entry point
│   └── requirements.txt
├── data/
│   └── processed/           # output of preprocessing (gitignored, reproducible)
│       ├── movies.parquet
│       ├── ratings.parquet
│       ├── links.parquet
│       ├── tags.parquet
│       ├── genome_scores.parquet
│       ├── sessions.parquet
│       └── cineai.db
├── frontend/
│   ├── src/
│   │   ├── components/      # Navbar, HeroBanner, MovieCard, MovieRow, RecommendationBadge, Footer
│   │   ├── pages/           # Home, Search, MovieDetail, Profile
│   │   ├── data/            # Mock dataset (20 movies, recommendation rows, user profile)
│   │   ├── hooks/           # useScrolled
│   │   └── types/           # TypeScript interfaces
│   ├── package.json
│   └── vite.config.ts
├── ml-20m/                  # raw MovieLens 20M CSVs (gitignored)
├── report/
│   ├── SP26_Group_Proposal_Group18_Project8_PDF.pdf
│   └── Group18-Project8-SP26-Group-Project-Presentation.pptx.pdf
└── README.md
```

---

## Data Preprocessing

### Prerequisites

- Python 3.10+
- The `ml-20m/` folder present at the repo root (download from [MovieLens 20M](https://grouplens.org/datasets/movielens/20m/))

### Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Run

```bash
python preprocess.py
```

All output is written to `../data/processed/` (relative to `backend/`).

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
  cineai.db                                3.3 MB
```

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

`links.csv`:
- Filters to movie IDs present in the cleaned movies table.
- Casts `imdbId` and `tmdbId` to nullable integers (some entries are missing).

`tags.csv`:
- Strips whitespace from tag strings and drops null or empty tags.
- Filters to valid movie IDs and user IDs from the cleaned ratings.

`genome-scores.csv`:
- Filters to valid movie IDs.
- Clamps any relevance values outside [0.0, 1.0] and logs a warning if any are found.

**Stage 5: Train / val / test split**

Applied per user, in chronological order by timestamp:

| Subset | Fraction | Approx. rows |
|---|---|---|
| train | 80% | 15.9 M |
| val | 10% | 2.0 M |
| test | 10% | 2.1 M |

The `split` column is added directly to `ratings.parquet` rather than creating three separate files. Downstream consumers can filter with `df[df["split"] == "train"]`.

**Stage 6: GRU4Rec session construction**

- Uses only training ratings.
- Sorts interactions per user by timestamp.
- A new session begins when the gap between consecutive interactions exceeds 30 minutes (configurable via `SESSION_GAP_SECONDS` in `config.py`).
- Sessions with only one item are discarded (not useful for next-item prediction).
- Each row in `sessions.parquet` is one interaction, identified by `sessionId` (`"{userId}_{session_index}"`), with a 0-indexed `position` column tracking placement within the session.

**Stage 7: Write output**

- All DataFrames are written as Snappy-compressed Parquet via PyArrow for fast columnar reads by pandas and PyTorch data loaders.
- `cineai.db` is a SQLite database containing:
  - `movies` table: `movieId`, `title`, `year`
  - `genres` table: unique genre vocabulary (19 genres)
  - `movie_genres` table: normalized many-to-many join table
  - `links` table: `movieId`, `imdbId`, `tmdbId` (key for TMDB enrichment)
  - `preprocessing_log` table: row counts and timestamps for each run

---

## How to Test the Preprocessing

After running `python preprocess.py`, verify correctness with these checks:

**1. Confirm files exist and are non-empty**

```bash
ls -lh ../data/processed/
```

**2. Verify split ratios**

```python
import pandas as pd
r = pd.read_parquet("../data/processed/ratings.parquet")
print(r.groupby("split").size())
# Expected: train ~15.9M, val ~2.0M, test ~2.1M
```

**3. Check no data leaks across splits (per user, train is always older)**

```python
import pandas as pd
r = pd.read_parquet("../data/processed/ratings.parquet")
sample_user = r["userId"].iloc[0]
user = r[r["userId"] == sample_user].sort_values("timestamp")
print(user[["timestamp", "split"]].to_string())
# All train rows should have earlier timestamps than val, val before test
```

**4. Check session structure**

```python
import pandas as pd
s = pd.read_parquet("../data/processed/sessions.parquet")
print(f"Unique sessions : {s['sessionId'].nunique():,}")
print(f"Avg session len : {len(s) / s['sessionId'].nunique():.1f}")
print(f"Min session len : {s.groupby('sessionId').size().min()}")
# Min should be 2 (single-item sessions are filtered)
```

**5. Check movie-links coverage**

```python
import pandas as pd
links = pd.read_parquet("../data/processed/links.parquet")
coverage = links["tmdbId"].notna().mean() * 100
print(f"TMDB coverage: {coverage:.1f}%")
# Expected: ~99%
```

**6. Query the SQLite database**

```python
import sqlite3
con = sqlite3.connect("../data/processed/cineai.db")
print(con.execute("SELECT * FROM preprocessing_log").fetchall())
print(con.execute("SELECT genre FROM genres ORDER BY genre").fetchall())
print(con.execute(
    "SELECT m.title, m.year, l.tmdbId FROM movies m JOIN links l USING(movieId) LIMIT 5"
).fetchall())
con.close()
```

**7. Spot-check a known movie**

```python
import pandas as pd
movies = pd.read_parquet("../data/processed/movies.parquet")
toy_story = movies[movies["movieId"] == 1]
print(toy_story[["movieId", "title", "year", "genres"]])
# Expected: title="Toy Story", year=1995, genres=["Adventure", "Animation", ...]
```

---

## Frontend

A Netflix-inspired UI that surfaces all three recommendation models with clear attribution.

### Stack

- **React 18** + **TypeScript**: component model and type safety
- **Vite**: fast dev server and build
- **Tailwind CSS**: utility-first styling
- **Framer Motion**: page transitions, scroll-reveal animations, animated score bars
- **React Router v6**: client-side routing
- **Lucide React**: icon set

### Pages

| Route | Description |
|---|---|
| `/` | Home: auto-rotating hero banner + 6 model-labeled recommendation carousels |
| `/search` | Discover: LLM query interpreter with genre, model, and rating filters |
| `/movie/:id` | Movie Detail: backdrop, cast, model score breakdown, similar movies |
| `/profile` | Profile: taste analytics, model contribution chart, watch history |

### Running the Frontend

```bash
cd frontend
npm install
npm run dev       # dev server at http://localhost:5173
npm run build     # production build
```

### Design System

- **Background:** `#0f0f0f` deep black base with `#1a1a1a` card surfaces
- **Accent:** `#E50914` Netflix red for primary CTAs and branding
- **Model color coding:**
  - OCCF: Blue `#3B82F6`
  - GRU4Rec: Emerald `#10B981`
  - Knowledge Graph: Violet `#8B5CF6`
  - Hybrid Fusion: Amber `#F59E0B`
  - Trending: Red `#EF4444`
- Movie posters use CSS gradients with no external image dependencies in the scaffold.

---

## Datasets

### MovieLens 20M

- 20 million ratings across 27,278 movies by 138,493 users
- Fields: `userId`, `movieId`, `rating` (0.5 to 5.0), `timestamp`
- Used for: OCCF training (implicit feedback) and GRU4Rec session construction
- Download: [https://grouplens.org/datasets/movielens/20m/](https://grouplens.org/datasets/movielens/20m/)
- Place the unzipped folder at `ml-20m/` in the repo root before running preprocessing.

### TMDB API

- ~24,000 movies enriched with genres, cast, crew, keywords, poster paths, overview
- Joined to MovieLens via `tmdbId` from `links.csv` (99.1% coverage)
- Used for: Knowledge Graph construction and LLM query metadata

---

## Models

### OCCF: One-Class Collaborative Filtering

Treats all observed ratings as positive implicit feedback with confidence weighting. Factorizes the user-item matrix into latent embeddings. Captures stable, long-term taste preferences.

**Libraries:** `implicit`, `LightFM`

### GRU4Rec: Session-Based Recommendation

Constructs user sessions from timestamped interactions using a time-gap rule. A Gated Recurrent Unit network predicts the next item given the session sequence. Handles short-term, rapidly-shifting interests.

**Libraries:** PyTorch, RecBole

### Knowledge Graph: Neo4j + TMDB

Builds a graph where nodes are movies, genres, actors, directors, and keywords, and edges encode semantic relationships (`DIRECTED_BY`, `HAS_GENRE`, `FEATURES_ACTOR`). Graph traversal and embedding via PyKEEN provide semantic similarity and cold-start recommendations.

**Libraries:** Neo4j, PyKEEN

### Hybrid Fusion Layer

Scores from all three models are min-max normalized per user, then aggregated with tunable weights optimized on the validation set (objective: NDCG@10). A local Mistral 7B model re-ranks the top-K candidates when a natural-language query is present.

---

## Evaluation

**Split strategy:** 80/10/10 train/validation/test per user, chronological holdout

**Baselines:** Popularity, neighborhood-based CF, individual model branches

**Metrics:**

| Task | Metrics |
|---|---|
| Top-N recommendation | Precision@K, Recall@K, NDCG@K, MAP@K (K = 10, 20) |
| Session-based (GRU4Rec) | HitRate@K, MRR@K |
| Cold-start / long-tail | Broken out separately per user group |

---

## Team: Group 18

| Member | Primary Responsibility |
|---|---|
| **Pranjal Padakannaya** | Project repo, MovieLens preprocessing, train/val/test splits |
| **Atharva Bhavin Thaker** | Baselines (popularity, neighborhood CF), evaluation scripts |
| **Sanjay Soralamavu Dev** | OCCF implementation, hyperparameter tuning |
| **Sachin Shivanand Shankarikoppa** | GRU4Rec session construction, training, session metrics |
| **Rahma Abuhannoud** | TMDB enrichment pipeline, Neo4j Knowledge Graph construction |
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
