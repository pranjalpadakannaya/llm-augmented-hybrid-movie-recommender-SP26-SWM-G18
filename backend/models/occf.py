from __future__ import annotations

import pickle
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix
from implicit.als import AlternatingLeastSquares


class OCCFModel:
    def __init__(
        self, factors: int = 50, regularization: float = 0.01, iterations: int = 10
    ):
        self.model = AlternatingLeastSquares(
            factors=factors,
            regularization=regularization,
            iterations=iterations,
        )
        self.user_item_matrix = None

        self.user_map: dict[int, int] = {}
        self.item_map: dict[int, int] = {}
        self.user_inv_map: dict[int, int] = {}
        self.item_inv_map: dict[int, int] = {}

        self.movie_titles: dict[int, str] = {}

    def _repo_root(self) -> Path:
        return Path(__file__).resolve().parents[2]

    def _default_ratings_path(self) -> Path:
        return self._repo_root() / "data" / "processed" / "ratings.parquet"

    def _default_movies_path(self) -> Path | None:
        candidates = [
            self._repo_root() / "data" / "processed" / "movies.parquet",
            self._repo_root() / "data" / "processed" / "movies.csv",
            self._repo_root() / "ml-20m" / "movies.csv",
        ]
        for path in candidates:
            if path.exists():
                return path
        return None

    def load_data(
        self,
        ratings_path: str | Path | None = None,
        movies_path: str | Path | None = None,
    ) -> None:
        print("Loading data...")

        ratings_path = (
            Path(ratings_path) if ratings_path else self._default_ratings_path()
        )
        movies_path = Path(movies_path) if movies_path else self._default_movies_path()

        if not ratings_path.exists():
            raise FileNotFoundError(f"Ratings file not found: {ratings_path}")

        df = pd.read_parquet(ratings_path)

        if (
            "userId" not in df.columns
            or "movieId" not in df.columns
            or "rating" not in df.columns
        ):
            raise ValueError(
                "ratings.parquet must contain userId, movieId, and rating columns"
            )

        # Implicit confidence weighting
        df = df.copy()
        df["confidence"] = 1.0 + df["rating"].astype(np.float32)

        # Encode IDs
        user_cat = df["userId"].astype("category")
        item_cat = df["movieId"].astype("category")

        user_codes = user_cat.cat.codes.to_numpy()
        item_codes = item_cat.cat.codes.to_numpy()

        self.user_map = dict(enumerate(user_cat.cat.categories.astype(int)))
        self.item_map = dict(enumerate(item_cat.cat.categories.astype(int)))
        self.user_inv_map = {v: k for k, v in self.user_map.items()}
        self.item_inv_map = {v: k for k, v in self.item_map.items()}

        # IMPORTANT: use CSR for indexing + implicit ALS
        self.user_item_matrix = coo_matrix(
            (df["confidence"].to_numpy(dtype=np.float32), (user_codes, item_codes))
        ).tocsr()

        print("Data loaded. Matrix shape:", self.user_item_matrix.shape)

        # Load movie titles for human-readable output
        self.movie_titles = {}
        if movies_path and movies_path.exists():
            if movies_path.suffix.lower() == ".parquet":
                movies_df = pd.read_parquet(movies_path)
            else:
                movies_df = pd.read_csv(movies_path)

            if "movieId" in movies_df.columns and "title" in movies_df.columns:
                self.movie_titles = dict(
                    zip(
                        movies_df["movieId"].astype(int),
                        movies_df["title"].astype(str),
                    )
                )

    def _default_artifact_path(self) -> Path:
        return self._repo_root() / "data" / "processed" / "model_artifacts" / "occf.pkl"

    def train(self) -> None:
        if self.user_item_matrix is None:
            raise RuntimeError("Call load_data() before train().")

        print("Training OCCF model...")
        self.model.fit(self.user_item_matrix)
        print("Training complete.")

    def save_artifact(self, artifact_path: str | Path | None = None) -> Path:
        artifact_path = Path(artifact_path) if artifact_path else self._default_artifact_path()
        artifact_path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "model": self.model,
            "user_item_matrix": self.user_item_matrix,
            "user_map": self.user_map,
            "item_map": self.item_map,
            "user_inv_map": self.user_inv_map,
            "item_inv_map": self.item_inv_map,
            "movie_titles": self.movie_titles,
        }
        with open(artifact_path, "wb") as f:
            pickle.dump(payload, f)
        return artifact_path

    def load_artifact(self, artifact_path: str | Path | None = None) -> None:
        artifact_path = Path(artifact_path) if artifact_path else self._default_artifact_path()
        if not artifact_path.exists():
            raise FileNotFoundError(f"OCCF artifact not found: {artifact_path}")

        with open(artifact_path, "rb") as f:
            payload = pickle.load(f)

        self.model = payload["model"]
        self.user_item_matrix = payload["user_item_matrix"]
        self.user_map = payload["user_map"]
        self.item_map = payload["item_map"]
        self.user_inv_map = payload["user_inv_map"]
        self.item_inv_map = payload["item_inv_map"]
        self.movie_titles = payload["movie_titles"]

    def recommend(self, user_id: int, N: int = 10) -> list[dict]:
        if user_id not in self.user_inv_map:
            print("User not found.")
            return []

        user_idx = self.user_inv_map[user_id]

        item_ids, scores = self.model.recommend(
            user_idx,
            self.user_item_matrix[user_idx],
            N,
            filter_already_liked_items=True,
        )

        results = []
        for item_idx, score in zip(item_ids, scores):
            movie_id = int(self.item_map[int(item_idx)])
            title = self.movie_titles.get(movie_id, f"Movie {movie_id}")
            results.append(
                {
                    "movieId": movie_id,
                    "title": title,
                    "score": float(score),
                    "model": "OCCF",
                }
            )

        return results


if __name__ == "__main__":
    model = OCCFModel()
    model.load_data()
    model.train()

    print("\nSample recommendations for user 1:")
    recs = model.recommend(user_id=1, N=10)

    for r in recs:
        print(r)
