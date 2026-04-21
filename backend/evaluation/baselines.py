"""
Baseline recommenders for evaluation comparison.

PopularityBaseline  — always recommends globally most-rated items
NeighborhoodCF      — user-based collaborative filtering (cosine similarity, top-k neighbors)
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from sklearn.metrics.pairwise import cosine_similarity


class PopularityBaseline:
    def __init__(self) -> None:
        self._popular: list[int] = []

    def fit(self, ratings_df: pd.DataFrame) -> "PopularityBaseline":
        counts = ratings_df.groupby("movieId").size().sort_values(ascending=False)
        self._popular = counts.index.tolist()
        return self

    def recommend(self, user_id: int, seen: set[int], N: int = 10) -> list[int]:
        return [m for m in self._popular if m not in seen][:N]


class NeighborhoodCF:
    def __init__(self, k_neighbors: int = 20) -> None:
        self.k = k_neighbors
        self._user_index: dict[int, int] = {}
        self._index_user: dict[int, int] = {}
        self._item_index: dict[int, int] = {}
        self._matrix: csr_matrix | None = None

    def fit(self, ratings_df: pd.DataFrame) -> "NeighborhoodCF":
        users = sorted(ratings_df["userId"].unique())
        items = sorted(ratings_df["movieId"].unique())
        self._user_index = {u: i for i, u in enumerate(users)}
        self._index_user = {i: u for u, i in self._user_index.items()}
        self._item_index = {m: j for j, m in enumerate(items)}
        self._index_item = {j: m for m, j in self._item_index.items()}

        rows = ratings_df["userId"].map(self._user_index).values
        cols = ratings_df["movieId"].map(self._item_index).values
        vals = ratings_df["rating"].astype(float).values
        self._matrix = csr_matrix(
            (vals, (rows, cols)), shape=(len(users), len(items))
        )
        return self

    def recommend(self, user_id: int, seen: set[int], N: int = 10) -> list[int]:
        if self._matrix is None or user_id not in self._user_index:
            return []
        u_idx = self._user_index[user_id]
        user_vec = self._matrix[u_idx]
        sims = cosine_similarity(user_vec, self._matrix).flatten()
        sims[u_idx] = -1.0  # exclude self
        neighbor_idxs = np.argsort(sims)[::-1][: self.k]

        scores: dict[int, float] = {}
        for n_idx in neighbor_idxs:
            sim = sims[n_idx]
            if sim <= 0:
                continue
            for j in self._matrix[n_idx].nonzero()[1]:
                movie_id = self._index_item[j]
                if movie_id not in seen:
                    scores[movie_id] = scores.get(movie_id, 0.0) + sim * self._matrix[n_idx, j]

        ranked = sorted(scores, key=scores.__getitem__, reverse=True)
        return ranked[:N]
