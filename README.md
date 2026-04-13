# CineAI — LLM-Augmented Hybrid Movie Recommender

**CSE 573: Semantic Web Mining · Group 18 · Spring 2026 · Arizona State University**

A hybrid movie recommendation system that combines classical data mining with deep learning and semantic modeling, surfaced through a Netflix-style frontend.

---

## Overview

CineAI addresses the limitations of single-model recommenders by fusing three parallel recommendation branches:

| Model | Purpose | Data |
|---|---|---|
| **OCCF** (One-Class Collaborative Filtering) | Long-term preference modeling via implicit feedback | MovieLens 20M |
| **GRU4Rec** | Session-based next-item prediction via Gated Recurrent Units | Timestamped interaction sequences |
| **Knowledge Graph** (Neo4j + TMDB) | Semantic relationships — genres, cast, directors, keywords | TMDB API (~24K movies) |

Scores from all three branches are normalized and fused through a weighted re-ranking layer. An LLM layer interprets natural-language queries into structured filters that are applied before retrieval.

---

## Repository Structure

```
.
├── frontend/               # React/TypeScript UI scaffold (Netflix-style)
│   ├── src/
│   │   ├── components/     # Navbar, HeroBanner, MovieCard, MovieRow, RecommendationBadge, Footer
│   │   ├── pages/          # Home, Search, MovieDetail, Profile
│   │   ├── data/           # Mock dataset (20 movies, recommendation rows, user profile)
│   │   ├── hooks/          # useScrolled
│   │   └── types/          # TypeScript interfaces
│   ├── package.json
│   └── vite.config.ts
├── report/
│   ├── SP26_Group_Proposal_Group18_Project8_PDF.pdf
│   └── Group18-Project8-SP26-Group-Project-Presentation.pptx.pdf
└── README.md
```

---

## Frontend

A Netflix-inspired UI that surfaces all three recommendation models with clear attribution.

### Stack

- **React 18** + **TypeScript** — component model and type safety
- **Vite** — fast dev server and build
- **Tailwind CSS** — utility-first styling
- **Framer Motion** — page transitions, scroll-reveal animations, animated score bars
- **React Router v6** — client-side routing
- **Lucide React** — icon set

### Pages

| Route | Description |
|---|---|
| `/` | Home — auto-rotating hero banner + 6 model-labeled recommendation carousels |
| `/search` | Discover — LLM query interpreter with genre, model, and rating filters |
| `/movie/:id` | Movie Detail — backdrop, cast, model score breakdown, similar movies |
| `/profile` | Profile — taste analytics, model contribution chart, watch history |

### Running the Frontend

```bash
cd frontend
npm install
npm run dev       # dev server at http://localhost:5173
npm run build     # production build
```

### Design System

- **Background:** `#0f0f0f` — deep black base with `#1a1a1a` card surfaces
- **Accent:** `#E50914` — Netflix red for primary CTAs and branding
- **Model color coding:**
  - OCCF → Blue (`#3B82F6`)
  - GRU4Rec → Emerald (`#10B981`)
  - Knowledge Graph → Violet (`#8B5CF6`)
  - Hybrid Fusion → Amber (`#F59E0B`)
  - Trending → Red (`#EF4444`)
- Movie posters use CSS gradients — no external image dependencies in the scaffold

---

## Datasets

### MovieLens 20M
- 20 million ratings across 27,278 movies by 138,493 users
- Fields: `userId`, `movieId`, `rating` (0.5–5.0), `timestamp`
- Used for: OCCF training (implicit feedback) and GRU4Rec session construction

### TMDB API
- ~24,000 movies enriched with genres, cast, crew, keywords, poster paths, overview
- Joined to MovieLens via `tmdbId` from `links.csv`
- Used for: Knowledge Graph construction and LLM query metadata

---

## Models

### OCCF — One-Class Collaborative Filtering
Treats all observed ratings as positive implicit feedback with confidence weighting. Factorizes the user–item matrix into latent embeddings. Captures stable, long-term taste preferences.

**Libraries:** `implicit`, `LightFM`

### GRU4Rec — Session-Based Recommendation
Constructs user sessions from timestamped interactions using a time-gap rule. A Gated Recurrent Unit network predicts the next item given the session sequence. Handles short-term, rapidly-shifting interests.

**Libraries:** PyTorch, RecBole

### Knowledge Graph — Neo4j + TMDB
Builds a graph where nodes are movies, genres, actors, directors, and keywords, and edges encode semantic relationships (e.g., `DIRECTED_BY`, `HAS_GENRE`, `FEATURES_ACTOR`). Graph traversal and embedding (PyKEEN / DGL-KE) provide semantic similarity and cold-start recommendations.

**Libraries:** Neo4j, PyKEEN

### Hybrid Fusion Layer
Scores from all three models are min-max normalized per user, then aggregated with tunable weights optimized on the validation set. Final ranking is re-ranked based on fused scores.

---

## Evaluation

**Split strategy:** 80/10/10 train/validation/test per user + chronological holdout

**Baselines:** Popularity, neighborhood-based CF, individual model branches

**Metrics:**

| Task | Metrics |
|---|---|
| Top-N recommendation | Precision@K, Recall@K, NDCG@K, MAP@K (K = 10, 20) |
| Session-based (GRU4Rec) | HitRate@K, MRR@K |
| Cold-start / long-tail | Broken out separately per user group |

---

## Team — Group 18

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
