"""
Sampled evaluation runner for comparing traditional baselines, component models,
and hybrid fusion before/after weight tuning.

This script reuses the repository's evaluation metrics and split logic, but adds
an explicit "Hybrid (Tuned)" pass so we can report default-vs-tuned fusion.

Usage:
    python -m backend.evaluation.run_eval_comparison --users 100 --k 10 --k2 20
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import pandas as pd

try:
    from backend.evaluation.run_eval import _evaluate_model, _split_ratings
    from backend.evaluation.baselines import NeighborhoodCF, PopularityBaseline
    from backend.fusion import HybridRecommender
except ImportError:
    from evaluation.run_eval import _evaluate_model, _split_ratings
    from evaluation.baselines import NeighborhoodCF, PopularityBaseline
    from fusion import HybridRecommender


DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"


def run(n_users: int = 100, k: int = 10, k2: int = 20, gru_epochs: int = 1) -> dict:
    ratings_path = DATA_DIR / "ratings.parquet"
    ratings_df = pd.read_parquet(ratings_path)

    train_df, test_map = _split_ratings(ratings_df)
    train_seen: dict[int, set[int]] = {
        int(uid): set(g["movieId"].astype(int).tolist())
        for uid, g in train_df.groupby("userId")
    }

    users_with_test = [u for u, rel in test_map.items() if rel]
    random.seed(42)
    eval_users = random.sample(users_with_test, min(n_users, len(users_with_test)))

    pop = PopularityBaseline().fit(train_df)
    ncf = NeighborhoodCF(k_neighbors=20).fit(train_df)

    hybrid = HybridRecommender()
    hybrid.gru.epochs = gru_epochs
    hybrid.load_models()

    def pop_recs(uid, seen, n):
        return pop.recommend(uid, seen, n)

    def ncf_recs(uid, seen, n):
        return ncf.recommend(uid, seen, n)

    def occf_recs(uid, seen, n):
        raw = hybrid.occf.recommend(uid, N=n * 2)
        return [int(r["movieId"]) for r in raw if int(r["movieId"]) not in seen][:n]

    def gru_recs(uid, seen, n):
        history = hybrid._get_history(uid)
        if history:
            raw = hybrid.gru.recommend_from_history(history, N=n * 2)
        else:
            raw = hybrid.gru.recommend_for_user(uid, N=n * 2)
        return [int(r["movieId"]) for r in raw if int(r["movieId"]) not in seen][:n]

    def kg_recs(uid, seen, n):
        history = hybrid._get_history(uid, limit=5)
        if history:
            raw = hybrid.kg.recommend_from_history(history, N=n * 2)
        else:
            raw = hybrid.kg.recommend_from_query("popular movies", N=n * 2)
        return [int(r["movieId"]) for r in raw if int(r["movieId"]) not in seen][:n]

    def hybrid_recs(uid, seen, n):
        result = hybrid.recommend(user_id=uid, N=n * 2)
        return [
            int(r["movieId"]) for r in result["recommendations"]
            if int(r["movieId"]) not in seen
        ][:n]

    models = [
        ("Popularity", pop_recs),
        ("NeighborhoodCF", ncf_recs),
        ("OCCF", occf_recs),
        ("GRU4Rec", gru_recs),
        ("KnowledgeGraph", kg_recs),
        ("Hybrid (Default)", hybrid_recs),
    ]

    results = []
    for name, fn in models:
        results.append(_evaluate_model(name, fn, test_map, train_seen, eval_users, k, k2))

    default_weights = hybrid.base_weights.copy()
    tuned_weights = hybrid.tune_weights(ratings_df, eval_users[: min(30, len(eval_users))], k=k, step=0.1)
    tuned_result = _evaluate_model("Hybrid (Tuned)", hybrid_recs, test_map, train_seen, eval_users, k, k2)
    results.append(tuned_result)

    payload = {
        "config": {
            "users": len(eval_users),
            "k": k,
            "k2": k2,
            "gru_epochs": gru_epochs,
            "tuning_users": min(30, len(eval_users)),
        },
        "default_weights": default_weights,
        "tuned_weights": tuned_weights,
        "results": results,
    }

    out_path = DATA_DIR / "eval_comparison_results.json"
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)

    print(json.dumps(payload, indent=2))
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--users", type=int, default=100)
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--k2", type=int, default=20)
    parser.add_argument("--gru-epochs", type=int, default=1)
    args = parser.parse_args()
    run(n_users=args.users, k=args.k, k2=args.k2, gru_epochs=args.gru_epochs)


if __name__ == "__main__":
    main()
