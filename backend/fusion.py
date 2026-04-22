from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

try:
    from backend.models.occf import OCCFModel
    from backend.models.gru4rec import GRU4RecModel
    from backend.models.kg import KGRecommender
except ImportError:
    from models.occf import OCCFModel
    from models.gru4rec import GRU4RecModel
    from models.kg import KGRecommender


BASE_WEIGHTS: Dict[str, float] = {
    "OCCF": 0.40,
    "GRU4Rec": 0.30,
    "KnowledgeGraph": 0.30,
}

CANDIDATE_MULTIPLIER: int = 3


class HybridRecommender:
    def __init__(self) -> None:
        self.base_weights = BASE_WEIGHTS.copy()

        self.occf = OCCFModel()
        self.gru = GRU4RecModel(epochs=3, batch_size=256, embed_dim=64, hidden_dim=128)
        self.kg = KGRecommender()

        self.ratings_df: Optional[pd.DataFrame] = None

    @staticmethod
    def _repo_root() -> Path:
        return Path(__file__).resolve().parents[1]

    def _ratings_path(self) -> Path:
        return self._repo_root() / "data" / "processed" / "ratings.parquet"

    def _artifact_dir(self) -> Path:
        return self._repo_root() / "data" / "processed" / "model_artifacts"

    def _artifact_is_fresh(self, artifact_path: Path, source_paths: list[Path]) -> bool:
        if not artifact_path.exists():
            return False

        artifact_mtime = artifact_path.stat().st_mtime
        for path in source_paths:
            if path.exists() and path.stat().st_mtime > artifact_mtime:
                return False
        return True

    def load_models(self) -> None:
        ratings_path = self._ratings_path()
        movies_path = self.occf._default_movies_path()
        sessions_path = self.gru._default_sessions_path()
        occf_artifact = self.occf._default_artifact_path()
        gru_artifact = self.gru._default_artifact_path()

        if self._artifact_is_fresh(occf_artifact, [ratings_path, movies_path or ratings_path]):
            print(f"Loading OCCF artifact from {occf_artifact} ...")
            self.occf.load_artifact(occf_artifact)
        else:
            self.occf.load_data(ratings_path=ratings_path, movies_path=movies_path)
            self.occf.train()
            self.occf.save_artifact(occf_artifact)

        if self._artifact_is_fresh(gru_artifact, [sessions_path, movies_path or sessions_path]):
            print(f"Loading GRU4Rec artifact from {gru_artifact} ...")
            self.gru.load_artifact(gru_artifact)
        else:
            self.gru.load_data(sessions_path=sessions_path, movies_path=movies_path)
            self.gru.train()
            self.gru.save_artifact(gru_artifact)

        self.kg.load_data()

        if ratings_path.exists():
            self.ratings_df = pd.read_parquet(ratings_path)

    def _get_history(self, user_id: int, limit: int = 30) -> List[int]:
        if self.ratings_df is None or self.ratings_df.empty:
            return []

        df = self.ratings_df[self.ratings_df["userId"] == user_id].copy()
        if df.empty:
            return []

        if "timestamp" in df.columns:
            df = df.sort_values("timestamp")

        return df["movieId"].astype(int).tolist()[-limit:]

    @staticmethod
    def _normalize_scores(recs: List[Dict]) -> Dict[int, float]:
        if not recs:
            return {}

        scores = [float(r["score"]) for r in recs]
        mn, mx = min(scores), max(scores)

        if abs(mx - mn) < 1e-9:
            return {int(r["movieId"]): 1.0 for r in recs}

        return {int(r["movieId"]): (float(r["score"]) - mn) / (mx - mn) for r in recs}

    @staticmethod
    def _effective_weights(
        base_weights: Dict[str, float], active_models: List[str]
    ) -> Dict[str, float]:
        active = {k: v for k, v in base_weights.items() if k in active_models}
        total = sum(active.values())
        if total < 1e-9:
            equal = 1.0 / len(active) if active else 1.0
            return {k: equal for k in active}
        return {k: v / total for k, v in active.items()}

    def _fuse(
        self,
        occf_recs: List[Dict],
        gru_recs: List[Dict],
        kg_recs: List[Dict],
        N: int = 10,
    ) -> List[Dict]:
        norm_occf = self._normalize_scores(occf_recs)
        norm_gru = self._normalize_scores(gru_recs)
        norm_kg = self._normalize_scores(kg_recs)

        occf_map = {int(r["movieId"]): r for r in occf_recs}
        gru_map = {int(r["movieId"]): r for r in gru_recs}
        kg_map = {int(r["movieId"]): r for r in kg_recs}

        active_models = (
            (["OCCF"] if occf_map else [])
            + (["GRU4Rec"] if gru_map else [])
            + (["KnowledgeGraph"] if kg_map else [])
        )
        weights = self._effective_weights(self.base_weights, active_models)

        all_movie_ids = set(occf_map) | set(gru_map) | set(kg_map)
        fused: List[Dict] = []

        for mid in all_movie_ids:
            title = None
            final_score = 0.0
            sources: List[Dict] = []
            because: List[str] = []

            if mid in occf_map:
                r = occf_map[mid]
                title = title or r.get("title")
                final_score += weights.get("OCCF", 0.0) * norm_occf.get(mid, 0.0)
                sources.append(
                    {
                        "model": "OCCF",
                        "score": float(r["score"]),
                        "normalized": round(norm_occf.get(mid, 0.0), 4),
                    }
                )

            if mid in gru_map:
                r = gru_map[mid]
                title = title or r.get("title")
                final_score += weights.get("GRU4Rec", 0.0) * norm_gru.get(mid, 0.0)
                sources.append(
                    {
                        "model": "GRU4Rec",
                        "score": float(r["score"]),
                        "normalized": round(norm_gru.get(mid, 0.0), 4),
                    }
                )

            if mid in kg_map:
                r = kg_map[mid]
                title = title or r.get("title")
                final_score += weights.get("KnowledgeGraph", 0.0) * norm_kg.get(
                    mid, 0.0
                )
                because = r.get("because", [])
                sources.append(
                    {
                        "model": "KnowledgeGraph",
                        "score": float(r["score"]),
                        "normalized": round(norm_kg.get(mid, 0.0), 4),
                    }
                )

            entry: Dict = {
                "movieId": mid,
                "title": title or f"Movie {mid}",
                "score": round(final_score, 6),
                "model": "Hybrid",
                "sources": sources,
            }
            if because:
                entry["because"] = because

            fused.append(entry)

        fused.sort(key=lambda x: x["score"], reverse=True)
        return fused[:N]

    def recommend(
        self,
        user_id: int,
        N: int = 10,
        query: Optional[str] = None,
    ) -> Dict:
        history = self._get_history(user_id)
        pool = N * CANDIDATE_MULTIPLIER

        occf_recs = self.occf.recommend(user_id, N=pool)

        if history:
            gru_recs = self.gru.recommend_from_history(history, N=pool)
        else:
            gru_recs = self.gru.recommend_for_user(user_id, N=pool)

        if query and query.strip():
            kg_recs = self.kg.recommend_from_query(query, N=pool)
        elif history:
            kg_recs = self.kg.recommend_from_history(history, N=pool)
        else:
            kg_recs = self.kg.recommend_from_query("popular", N=pool)

        fused = self._fuse(occf_recs, gru_recs, kg_recs, N=N)

        return {
            "userId": user_id,
            "query": query,
            "historyMovieIds": history,
            "recommendations": fused,
        }


    def tune_weights(
        self,
        ratings_df: pd.DataFrame,
        val_users: list[int],
        k: int = 10,
        step: float = 0.1,
    ) -> dict[str, float]:
        """Grid-search fusion weights to maximise NDCG@k on val_users.

        Tries all (occf, gru, kg) weight triples that sum to 1.0 (step granularity).
        Updates self.base_weights in-place and returns the best weights found.
        """
        try:
            from evaluation.metrics import ndcg_at_k
        except ImportError:
            from backend.evaluation.metrics import ndcg_at_k

        # Build ground truth from last 20% of each validation user's ratings
        test_map: dict[int, set[int]] = {}
        for uid in val_users:
            user_ratings = ratings_df[ratings_df["userId"] == uid]
            if "timestamp" in user_ratings.columns:
                user_ratings = user_ratings.sort_values("timestamp")
            n = len(user_ratings)
            split = max(1, int(n * 0.8))
            held = set(user_ratings.iloc[split:]["movieId"].astype(int).tolist())
            if held:
                test_map[uid] = held

        if not test_map:
            return self.base_weights.copy()

        # Pre-fetch candidates for all val users
        pool = k * 3
        occf_cache: dict[int, list[dict]] = {}
        gru_cache: dict[int, list[dict]] = {}
        kg_cache: dict[int, list[dict]] = {}
        for uid in test_map:
            occf_cache[uid] = self.occf.recommend(uid, N=pool)
            history = self._get_history(uid)
            gru_cache[uid] = (
                self.gru.recommend_from_history(history, N=pool)
                if history
                else self.gru.recommend_for_user(uid, N=pool)
            )
            h5 = self._get_history(uid, limit=5)
            kg_cache[uid] = (
                self.kg.recommend_from_history(h5, N=pool)
                if h5
                else self.kg.recommend_from_query("popular", N=pool)
            )

        values = [round(i * step, 2) for i in range(int(1 / step) + 1)]
        best_score = -1.0
        best_weights = self.base_weights.copy()

        for w_occf in values:
            for w_gru in values:
                w_kg = round(1.0 - w_occf - w_gru, 2)
                if w_kg < 0 or w_kg > 1.0 + 1e-9:
                    continue
                trial = {"OCCF": w_occf, "GRU4Rec": w_gru, "KnowledgeGraph": max(0.0, w_kg)}
                self.base_weights = trial

                ndcgs = []
                for uid, rel in test_map.items():
                    fused = self._fuse(occf_cache[uid], gru_cache[uid], kg_cache[uid], N=k)
                    recs = [int(r["movieId"]) for r in fused]
                    ndcgs.append(ndcg_at_k(recs, rel, k))

                score = sum(ndcgs) / len(ndcgs)
                if score > best_score:
                    best_score = score
                    best_weights = trial.copy()

        self.base_weights = best_weights
        return best_weights


if __name__ == "__main__":
    hybrid = HybridRecommender()
    hybrid.load_models()

    result = hybrid.recommend(user_id=1, N=10)

    print(
        f"\nRecommendations for user {result['userId']} (history: {len(result['historyMovieIds'])} movies)\n"
    )

    for rec in result["recommendations"]:
        sources_str = ", ".join(
            f"{s['model']}={s['normalized']}" for s in rec["sources"]
        )
        because_str = (
            f"  because: {', '.join(rec['because'])}" if rec.get("because") else ""
        )
        print(f"  [{rec['score']:.4f}] {rec['title']}")
        print(f"          sources: {sources_str}{because_str}")
