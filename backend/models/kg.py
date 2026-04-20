"""
Knowledge Graph Movie Recommender
==================================
Architecture
------------
1. KnowledgeGraph  – a typed, weighted heterogeneous graph.
   Nodes  : movies, persons, genres, keywords, studios
   Edges  : has_genre, acted_in, directed_by, written_by,
            tagged_with, produced_by  (all bidirectional)
2. KGRecommender   – loads data, builds the graph, scores
   candidates via multi-hop path traversal.

Scoring
-------
For a query movie q and a candidate c, the KG score sums
the weights of all entity paths connecting them:

    kg_score(q, c) = Σ  edge_weight(q, e) × edge_weight(e, c)
                      e ∈ shared_neighbors(q, c)

Each edge type carries a configurable base weight.
Two-hop paths (movie → entity → entity → movie) are included
with a configurable depth penalty so they contribute less
than direct 1-hop shared neighbors.

A lightweight TF-IDF index is retained as a semantic fallback
that adds a small signal for textual matches the graph doesn't
capture (e.g. thematic overlap with no shared cast/crew).
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel


EDGE_WEIGHTS: Dict[str, float] = {
    "directed_by": 0.30,
    "has_genre": 0.25,
    "acted_in": 0.20,
    "written_by": 0.15,
    "tagged_with": 0.10,
    "produced_by": 0.05,
}

TWO_HOP_DEPTH_PENALTY: float = 0.40   # multiplied onto two-hop path weights
TFIDF_BLEND_WEIGHT: float = 0.15      # share of the final score from TF-IDF


@dataclass(slots=True)
class Edge:
    """A directed, typed, weighted edge."""
    target: str
    edge_type: str
    weight: float


class KnowledgeGraph:
    """
    Lightweight in-memory heterogeneous graph.

    Node id format: "{type}:{name_slug}"
        movie:2571
        person:christopher_nolan
        genre:action
        keyword:heist
        studio:warner_bros
    """

    def __init__(self) -> None:
        self._adj: Dict[str, List[Edge]] = defaultdict(list)
        self._nodes: Set[str] = set()
        self._labels: Dict[str, str] = {}

    def add_node(self, node_id: str, label: str = "") -> None:
        self._nodes.add(node_id)
        if label:
            self._labels[node_id] = label

    def add_edge(
        self,
        src: str,
        dst: str,
        edge_type: str,
        weight: Optional[float] = None,
    ) -> None:
        """Add a bidirectional typed edge between src and dst."""
        self.add_node(src)
        self.add_node(dst)
        w = weight if weight is not None else EDGE_WEIGHTS.get(edge_type, 0.10)
        self._adj[src].append(Edge(dst, edge_type, w))
        self._adj[dst].append(Edge(src, edge_type, w))

    def neighbors(
        self,
        node_id: str,
        edge_type: Optional[str] = None,
    ) -> List[Edge]:
        edges = self._adj.get(node_id, [])
        if edge_type:
            return [e for e in edges if e.edge_type == edge_type]
        return edges

    def entity_neighbors(self, movie_node: str) -> Dict[str, float]:
        """Return {entity_node: edge_weight} for a movie node."""
        return {
            e.target: e.weight
            for e in self._adj.get(movie_node, [])
            if not e.target.startswith("movie:")
        }

    def movie_neighbors(self, entity_node: str) -> Dict[str, float]:
        """Return {movie_node: edge_weight} for an entity node."""
        return {
            e.target: e.weight
            for e in self._adj.get(entity_node, [])
            if e.target.startswith("movie:")
        }

    def __len__(self) -> int:
        return len(self._nodes)

    def label(self, node_id: str) -> str:
        return self._labels.get(node_id, node_id)


class KGRecommender:
    """
    Knowledge-graph-first movie recommender.

    Steps
    -----
    1. load_data()  – parse CSV/Parquet, build KG, build TF-IDF fallback
    2. recommend_from_movie(movie_id)
    3. recommend_from_history(movie_ids)
    4. recommend_from_query(text)
    """

    def __init__(
        self,
        edge_weights: Dict[str, float] = EDGE_WEIGHTS,
        two_hop_penalty: float = TWO_HOP_DEPTH_PENALTY,
        tfidf_blend: float = TFIDF_BLEND_WEIGHT,
        candidate_pool: int = 500,
        max_tfidf_features: int = 15_000,
    ) -> None:
        self.edge_weights = edge_weights
        self.two_hop_penalty = two_hop_penalty
        self.tfidf_blend = tfidf_blend
        self.candidate_pool = candidate_pool
        self.max_tfidf_features = max_tfidf_features

        self.graph: KnowledgeGraph = KnowledgeGraph()

        self._movie_index: Dict[int, int] = {}
        self._index_movie: Dict[int, int] = {}
        self._movie_titles: Dict[int, str] = {}

        self._movies_df: Optional[pd.DataFrame] = None
        self._vectorizer: Optional[TfidfVectorizer] = None
        self._tfidf_matrix = None
        self.model_name = "KnowledgeGraph"

    @staticmethod
    def _repo_root() -> Path:
        return Path(__file__).resolve().parents[2]

    @staticmethod
    def _read_any(path: Path) -> pd.DataFrame:
        return pd.read_parquet(path) if path.suffix.lower() == ".parquet" else pd.read_csv(path)

    @staticmethod
    def _safe(value) -> str:
        if value is None:
            return ""
        if isinstance(value, float) and np.isnan(value):
            return ""
        return str(value).strip()

    @staticmethod
    def _slug(text: str) -> str:
        """Normalise a name to a stable graph node slug."""
        return re.sub(r"[^a-z0-9]+", "_", text.strip().lower()).strip("_")

    @staticmethod
    def _tokens(value) -> List[str]:
        if value is None:
            return []
        if isinstance(value, (list, tuple, np.ndarray)):
            value = " ".join(map(str, value))
        text = str(value)
        if not text or text.lower() == "nan":
            return []
        text = re.sub(r"[|,\[\]'\"]+", " ", text)
        return [t for t in re.split(r"\s+", text.lower()) if len(t) > 1]

    def _pick_existing(self, candidates: List[Path]) -> Optional[Path]:
        for p in candidates:
            if p.exists():
                return p
        return None

    def _default_movies_path(self) -> Optional[Path]:
        root = self._repo_root()
        return self._pick_existing([
            root / "data" / "processed" / "movies.parquet",
            root / "data" / "processed" / "movies.csv",
            root / "ml-20m" / "movies.csv",
        ])

    def _default_metadata_path(self) -> Optional[Path]:
        root = self._repo_root()
        return self._pick_existing([
            root / "data" / "processed" / "tmdb_metadata.parquet",
            root / "data" / "processed" / "tmdb_metadata.csv",
            root / "data" / "processed" / "movie_metadata.parquet",
            root / "data" / "processed" / "movie_metadata.csv",
        ])

    def _build_graph(self, df: pd.DataFrame) -> None:
        """
        Populate the KnowledgeGraph from a merged movies DataFrame.

        Entity node types added
        -----------------------
        genre:    has_genre
        person:   acted_in, directed_by, written_by
        keyword:  tagged_with
        studio:   produced_by
        """
        print("Building knowledge graph …")

        for _, row in df.iterrows():
            mid = int(row["movieId"])
            title = self._safe(row.get("title", ""))
            mnode = f"movie:{mid}"
            self.graph.add_node(mnode, label=title)

            for tok in self._tokens(row.get("genres", "")):
                gnode = f"genre:{self._slug(tok)}"
                self.graph.add_node(gnode, label=tok)
                self.graph.add_edge(mnode, gnode, "has_genre")

            for tok in self._tokens(row.get("genre_names", "") or row.get("tmdb_genres", "")):
                gnode = f"genre:{self._slug(tok)}"
                self.graph.add_node(gnode, label=tok)
                self.graph.add_edge(mnode, gnode, "has_genre")

            for tok in self._tokens(row.get("cast", "")):
                pnode = f"person:{self._slug(tok)}"
                self.graph.add_node(pnode, label=tok)
                self.graph.add_edge(mnode, pnode, "acted_in")

            for col in ("director", "crew"):
                for tok in self._tokens(row.get(col, "")):
                    pnode = f"person:{self._slug(tok)}"
                    self.graph.add_node(pnode, label=tok)
                    edge_type = "directed_by" if col == "director" else "written_by"
                    self.graph.add_edge(mnode, pnode, edge_type)

            for col in ("keywords", "tags"):
                for tok in self._tokens(row.get(col, "")):
                    knode = f"keyword:{self._slug(tok)}"
                    self.graph.add_node(knode, label=tok)
                    self.graph.add_edge(mnode, knode, "tagged_with")

            for tok in self._tokens(row.get("production_companies", "")):
                snode = f"studio:{self._slug(tok)}"
                self.graph.add_node(snode, label=tok)
                self.graph.add_edge(mnode, snode, "produced_by")

        node_count = len(self.graph)
        movie_count = len([n for n in self.graph._nodes if n.startswith("movie:")])
        print(
            f"Graph built: {node_count} nodes  "
            f"({movie_count} movies + {node_count - movie_count} entities)"
        )

    def _build_tfidf(self, df: pd.DataFrame) -> None:
        """Build a lightweight TF-IDF index as a semantic fallback."""
        docs = []
        for _, row in df.iterrows():
            parts = [
                self._safe(row.get("title", "")) * 3,
                self._safe(row.get("overview", "")),
                self._safe(row.get("keywords", "")),
                self._safe(row.get("tags", "")),
            ]
            docs.append(" ".join(p for p in parts if p))

        df["__doc__"] = docs
        self._vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            max_features=self.max_tfidf_features,
        )
        self._tfidf_matrix = self._vectorizer.fit_transform(df["__doc__"].fillna(""))

    def load_data(
        self,
        movies_path: Optional[str | Path] = None,
        metadata_path: Optional[str | Path] = None,
    ) -> None:
        movies_path = Path(movies_path) if movies_path else self._default_movies_path()
        metadata_path = Path(metadata_path) if metadata_path else self._default_metadata_path()

        if movies_path is None or not movies_path.exists():
            raise FileNotFoundError("Cannot find a movies file. Pass movies_path explicitly.")

        print(f"Loading movies from {movies_path} …")
        df = self._read_any(movies_path)
        df["movieId"] = pd.to_numeric(df["movieId"], errors="coerce")
        df = df.dropna(subset=["movieId"])
        df["movieId"] = df["movieId"].astype(int)

        if metadata_path and metadata_path.exists():
            print(f"Merging metadata from {metadata_path} …")
            meta = self._read_any(metadata_path)
            meta["movieId"] = pd.to_numeric(meta["movieId"], errors="coerce")
            meta = meta.dropna(subset=["movieId"])
            meta["movieId"] = meta["movieId"].astype(int)
            df = df.merge(meta, on="movieId", how="left", suffixes=("", "_meta"))
        else:
            print(
                "WARNING: No metadata file found. Graph will only contain genres.\n"
                f"  Tried: {self._default_metadata_path()}\n"
                "  Pass metadata_path= explicitly, e.g.:\n"
                "    model.load_data(metadata_path='data/processed/tmdb_metadata.parquet')"
            )

        print(
            f"Columns available for graph: "
            f"{list(df.columns[:8])} … ({len(df.columns)} total)"
        )

        for col in (
            "title",
            "genres",
            "overview",
            "keywords",
            "cast",
            "crew",
            "director",
            "genre_names",
            "tags",
            "tmdb_genres",
            "production_companies",
        ):
            if col not in df.columns:
                df[col] = ""

        df = df.reset_index(drop=True)
        self._movies_df = df

        for idx, movie_id in enumerate(df["movieId"].tolist()):
            mid = int(movie_id)
            self._movie_index[mid] = idx
            self._index_movie[idx] = mid

        self._movie_titles = {
            int(mid): str(title)
            for mid, title in zip(df["movieId"], df["title"])
        }

        self._build_graph(df)
        self._build_tfidf(df)
        print(f"Ready. {len(self._movie_index)} movies indexed.")

    def _kg_score(
        self,
        query_movie_id: int,
        candidate_movie_id: int,
    ) -> Tuple[float, List[str]]:
        """
        Score candidate against query via shared entity paths.

        Returns (score, explanation_tokens).

        1-hop score  : Σ w(q→e) × w(e→c)              for e ∈ shared entities
        2-hop score  : Σ w(q→e1) × w(e1→e2) × w(e2→c) for 2-hop paths
                       × TWO_HOP_DEPTH_PENALTY
        """
        qnode = f"movie:{query_movie_id}"
        cnode = f"movie:{candidate_movie_id}"

        q_entities: Dict[str, float] = self.graph.entity_neighbors(qnode)
        c_entities: Dict[str, float] = self.graph.entity_neighbors(cnode)

        shared = set(q_entities) & set(c_entities)
        score = 0.0
        reasons: List[str] = []

        for entity in shared:
            contribution = q_entities[entity] * c_entities[entity]
            score += contribution
            reasons.append(self.graph.label(entity))

        for e1, w_qe1 in q_entities.items():
            for e2_edge in self.graph.neighbors(e1):
                e2 = e2_edge.target
                if e2.startswith("movie:") or e2 in q_entities:
                    continue
                w_c = c_entities.get(e2, 0.0)
                if w_c > 0:
                    contribution = w_qe1 * e2_edge.weight * w_c * self.two_hop_penalty
                    score += contribution

        return score, reasons[:5]

    def _tfidf_score(self, idx_q: int, idx_c: int) -> float:
        if self._tfidf_matrix is None:
            return 0.0
        q_vec = self._tfidf_matrix[idx_q]
        c_vec = self._tfidf_matrix[idx_c]
        return float(linear_kernel(q_vec, c_vec).flatten()[0])

    def _tfidf_top_candidates(
        self,
        query_vec,
        exclude_ids: Set[int],
    ) -> List[int]:
        """Return the top candidate movie_ids by TF-IDF for an initial pool."""
        if hasattr(query_vec, "A"):
            query_vec = query_vec.A
        elif hasattr(query_vec, "toarray"):
            query_vec = query_vec.toarray()

        sims = linear_kernel(query_vec, self._tfidf_matrix).flatten()
        top_indices = np.argpartition(
            -sims,
            kth=min(self.candidate_pool, len(sims)) - 1,
        )[:self.candidate_pool]

        return [
            self._index_movie[int(i)]
            for i in top_indices
            if self._index_movie[int(i)] not in exclude_ids
        ]

    def _build_result(
        self,
        movie_id: int,
        kg_score: float,
        tfidf_score: float,
        reasons: List[str],
    ) -> Dict:
        final = (1.0 - self.tfidf_blend) * kg_score + self.tfidf_blend * tfidf_score
        return {
            "movieId": movie_id,
            "title": self._movie_titles.get(movie_id, f"Movie {movie_id}"),
            "score": round(final, 6),
            "kg_score": round(kg_score, 6),
            "because": reasons,
        }

    def _require_loaded(self) -> None:
        if self._movies_df is None:
            raise RuntimeError("Call load_data() before recommend().")

    def recommend_from_movie(
        self,
        movie_id: int,
        N: int = 10,
    ) -> List[Dict]:
        """
        Recommend N movies similar to movie_id.

        Uses KG path traversal as primary signal, TF-IDF as blend.
        Returns results sorted by score descending, each entry includes
        a 'because' list of matched entity labels for interpretability.
        """
        self._require_loaded()
        if movie_id not in self._movie_index:
            raise KeyError(f"movie_id {movie_id} not found in graph.")

        idx_q = self._movie_index[movie_id]
        qnode = f"movie:{movie_id}"
        q_vec = self._tfidf_matrix[idx_q]

        kg_candidates: Set[int] = set()
        for entity_edge in self.graph.neighbors(qnode):
            entity = entity_edge.target
            for movie_edge in self.graph.movie_neighbors(entity):
                mid = int(movie_edge.split("movie:")[1])
                kg_candidates.add(mid)
        kg_candidates.discard(movie_id)

        tfidf_candidates = set(self._tfidf_top_candidates(q_vec, {movie_id}))
        all_candidates = kg_candidates | tfidf_candidates

        results = []
        for cid in all_candidates:
            if cid == movie_id:
                continue
            kg_s, reasons = self._kg_score(movie_id, cid)
            idx_c = self._movie_index.get(cid)
            tf_s = self._tfidf_score(idx_q, idx_c) if idx_c is not None else 0.0
            results.append(self._build_result(cid, kg_s, tf_s, reasons))

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:N]

    def recommend_from_history(
        self,
        history_movie_ids: List[int],
        N: int = 10,
    ) -> List[Dict]:
        """
        Recommend N movies based on a list of previously-watched movies.

        Entity importance is accumulated across the whole history so
        movies touching many of the user's interests rank higher.
        The most-recently-watched movie receives a recency boost (×1.5).
        """
        self._require_loaded()

        valid_ids = [mid for mid in history_movie_ids if mid in self._movie_index]
        if not valid_ids:
            return []

        seen = set(valid_ids)

        entity_profile: Dict[str, float] = defaultdict(float)
        for i, mid in enumerate(valid_ids):
            recency = 1.5 if i == len(valid_ids) - 1 else 1.0
            mnode = f"movie:{mid}"
            for e_edge in self.graph.neighbors(mnode):
                if not e_edge.target.startswith("movie:"):
                    entity_profile[e_edge.target] += e_edge.weight * recency

        candidates: Set[int] = set()
        for entity in entity_profile:
            for m_edge in self.graph.neighbors(entity):
                if m_edge.target.startswith("movie:"):
                    cid = int(m_edge.target.split("movie:")[1])
                    if cid not in seen:
                        candidates.add(cid)

        history_indices = [self._movie_index[mid] for mid in valid_ids]
        q_vec = np.asarray(self._tfidf_matrix[history_indices].mean(axis=0))
        tfidf_candidates = set(self._tfidf_top_candidates(q_vec, seen))
        all_candidates = candidates | tfidf_candidates

        results = []
        for cid in all_candidates:
            cnode = f"movie:{cid}"
            score = 0.0
            reasons: List[str] = []
            for e_edge in self.graph.neighbors(cnode):
                entity = e_edge.target
                if entity in entity_profile:
                    contribution = entity_profile[entity] * e_edge.weight
                    score += contribution
                    reasons.append(self.graph.label(entity))

            idx_c = self._movie_index.get(cid)
            tf_s = (
                float(linear_kernel(q_vec, self._tfidf_matrix[idx_c]).flatten()[0])
                if idx_c is not None
                else 0.0
            )
            final = (1.0 - self.tfidf_blend) * score + self.tfidf_blend * tf_s
            results.append({
                "movieId": cid,
                "title": self._movie_titles.get(cid, f"Movie {cid}"),
                "score": round(final, 6),
                "kg_score": round(score, 6),
                "because": sorted(reasons, key=reasons.count, reverse=True)[:5],
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:N]

    def recommend_from_query(
        self,
        query: str,
        N: int = 10,
    ) -> List[Dict]:
        """
        Recommend N movies matching a free-text query.

        TF-IDF is the primary signal here (no anchor movie for KG traversal).
        Entity nodes matching query tokens boost matched movies additionally.
        """
        self._require_loaded()
        if not query.strip():
            return []

        qvec = self._vectorizer.transform([query])
        sims = linear_kernel(qvec, self._tfidf_matrix).flatten()

        pool_size = min(self.candidate_pool, len(sims))
        top_idx = np.argpartition(-sims, kth=pool_size - 1)[:pool_size]

        query_tokens = set(self._slug(t) for t in query.lower().split() if len(t) > 2)
        entity_boost: Dict[int, float] = defaultdict(float)
        for node_id in self.graph._nodes:
            if node_id.startswith("movie:"):
                continue
            node_slug = node_id.split(":", 1)[1]
            if any(qt in node_slug for qt in query_tokens):
                for m_edge in self.graph.neighbors(node_id):
                    if m_edge.target.startswith("movie:"):
                        mid = int(m_edge.target.split("movie:")[1])
                        entity_boost[mid] += m_edge.weight * 0.10

        results = []
        for idx in top_idx:
            mid = self._index_movie[int(idx)]
            tf_s = float(sims[int(idx)])
            boost = entity_boost.get(mid, 0.0)
            final = tf_s + boost
            results.append({
                "movieId": mid,
                "title": self._movie_titles.get(mid, f"Movie {mid}"),
                "score": round(final, 6),
                "model": self.model_name,
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:N]

    def explain(self, movie_id_a: int, movie_id_b: int) -> str:
        """
        Return a human-readable explanation of why A and B are similar.
        Useful for debugging and UI tooltips.
        """
        self._require_loaded()
        score, reasons = self._kg_score(movie_id_a, movie_id_b)
        a_title = self._movie_titles.get(movie_id_a, str(movie_id_a))
        b_title = self._movie_titles.get(movie_id_b, str(movie_id_b))
        if not reasons:
            return f'"{a_title}" and "{b_title}" share no graph entities (KG score: 0).'
        shared = ", ".join(f'"{r}"' for r in reasons)
        return (
            f'"{a_title}" → "{b_title}"  |  '
            f"KG score: {score:.4f}  |  "
            f"Shared: {shared}"
        )


if __name__ == "__main__":
    model = KGRecommender(
        candidate_pool=500,
        max_tfidf_features=15_000,
    )
    model.load_data()

    print("\n── Recommendations for movieId=2571 ──")
    for r in model.recommend_from_movie(movie_id=2571, N=10):
        print(f"  [{r['score']:.4f}] {r['title']}")
        if r.get("because"):
            print(f"          because: {', '.join(r['because'])}")

    print("\n── History-based recommendations ──")
    for r in model.recommend_from_history([2571, 296, 318], N=5):
        print(f"  [{r['score']:.4f}] {r['title']}")

    print("\n── Query: 'crime heist thriller' ──")
    for r in model.recommend_from_query("crime heist thriller", N=5):
        print(f"  [{r['score']:.4f}] {r['title']}")

    print("\n── Explanation ──")
    print(model.explain(2571, 296))