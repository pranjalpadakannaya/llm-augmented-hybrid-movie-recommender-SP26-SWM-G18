from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from implicit.als import AlternatingLeastSquares
from scipy.sparse import coo_matrix, load_npz, save_npz


class OCCFModel:
    def __init__(
        self, factors: int = 50, regularization: float = 0.01, iterations: int = 10
    ):
        self.factors = factors
        self.regularization = regularization
        self.iterations = iterations

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

    def _artifact_dir(self) -> Path:
        return self._repo_root() / "data" / "artifacts" / "occf"

    def save_artifacts(self, dir_path: str | Path | None = None) -> None:
        if self.user_item_matrix is None:
            raise RuntimeError("Nothing to save. Call load_data() and train() first.")

        out_dir = Path(dir_path) if dir_path else self._artifact_dir()
        out_dir.mkdir(parents=True, exist_ok=True)

        save_npz(out_dir / "user_item_matrix.npz", self.user_item_matrix)
        joblib.dump(
            {
                "factors": self.factors,
                "regularization": self.regularization,
                "iterations": self.iterations,
                "user_map": self.user_map,
                "item_map": self.item_map,
                "user_inv_map": self.user_inv_map,
                "item_inv_map": self.item_inv_map,
                "movie_titles": self.movie_titles,
                "model": self.model,
            },
            out_dir / "occf_meta.pkl",
        )

    def load_artifacts(self, dir_path: str | Path | None = None) -> bool:
        out_dir = Path(dir_path) if dir_path else self._artifact_dir()
        matrix_path = out_dir / "user_item_matrix.npz"
        meta_path = out_dir / "occf_meta.pkl"

        if not matrix_path.exists() or not meta_path.exists():
            return False

        self.user_item_matrix = load_npz(matrix_path)
        meta = joblib.load(meta_path)

        self.factors = meta.get("factors", self.factors)
        self.regularization = meta.get("regularization", self.regularization)
        self.iterations = meta.get("iterations", self.iterations)

        self.user_map = meta.get("user_map", {})
        self.item_map = meta.get("item_map", {})
        self.user_inv_map = meta.get("user_inv_map", {})
        self.item_inv_map = meta.get("item_inv_map", {})
        self.movie_titles = meta.get("movie_titles", {})

        loaded_model = meta.get("model")
        if loaded_model is not None:
            self.model = loaded_model
        else:
            self.model = AlternatingLeastSquares(
                factors=self.factors,
                regularization=self.regularization,
                iterations=self.iterations,
            )

        return True

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

        df = df.copy()
        df["confidence"] = 1.0 + df["rating"].astype(np.float32)

        user_cat = df["userId"].astype("category")
        item_cat = df["movieId"].astype("category")

        user_codes = user_cat.cat.codes.to_numpy()
        item_codes = item_cat.cat.codes.to_numpy()

        self.user_map = dict(enumerate(user_cat.cat.categories.astype(int)))
        self.item_map = dict(enumerate(item_cat.cat.categories.astype(int)))
        self.user_inv_map = {v: k for k, v in self.user_map.items()}
        self.item_inv_map = {v: k for k, v in self.item_map.items()}

        self.user_item_matrix = coo_matrix(
            (df["confidence"].to_numpy(dtype=np.float32), (user_codes, item_codes))
        ).tocsr()

        print("Data loaded. Matrix shape:", self.user_item_matrix.shape)

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

    def train(self) -> None:
        if self.user_item_matrix is None:
            raise RuntimeError("Call load_data() before train().")

        print("Training OCCF model...")
        self.model.fit(self.user_item_matrix)
        print("Training complete.")

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