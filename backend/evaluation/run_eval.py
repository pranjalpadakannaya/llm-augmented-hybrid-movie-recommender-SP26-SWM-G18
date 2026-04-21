"""
Evaluation runner: compares all recommenders on a held-out test set.

Usage:
    python -m backend.evaluation.run_eval [--users 500] [--k 10] [--k2 20]

Splits ratings into train (80%) / test (20%) per user (temporal if timestamp exists).
Evaluates: Popularity, NeighborhoodCF, OCCF, GRU4Rec, KG, Hybrid.
Outputs a results table to stdout and saves results.json to data/processed/.
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd

try:
    from backend.evaluation.metrics import (
        hit_rate_at_k, map_at_k, mrr_at_k, ndcg_at_k, precision_at_k, recall_at_k,
    )
    from backend.evaluation.baselines import NeighborhoodCF, PopularityBaseline
    from backend.models.occf import OCCFModel
    from backend.models.gru4rec import GRU4RecModel
    from backend.models.kg import KGRecommender
    from backend.fusion import HybridRecommender
except ImportError:
    from evaluation.metrics import (
        hit_rate_at_k, map_at_k, mrr_at_k, ndcg_at_k, precision_at_k, recall_at_k,
    )
    from evaluation.baselines import NeighborhoodCF, PopularityBaseline
    from models.occf import OCCFModel
    from models.gru4rec import GRU4RecModel
    from models.kg import KGRecommender
    from fusion import HybridRecommender

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"


def _split_ratings(ratings_df: pd.DataFrame) -> tuple[pd.DataFrame, dict[int, set[int]]]:
    """Return (train_df, {user_id: {held_out_movie_ids}})."""
    train_rows = []
    test_map: dict[int, set[int]] = {}

    for user_id, group in ratings_df.groupby("userId"):
        if "timestamp" in group.columns:
            group = group.sort_values("timestamp")
        else:
            group = group.sample(frac=1, random_state=42)

        n = len(group)
        split = max(1, int(n * 0.8))
        train_rows.append(group.iloc[:split])
        test_map[int(user_id)] = set(group.iloc[split:]["movieId"].astype(int).tolist())

    return pd.concat(train_rows, ignore_index=True), test_map


def _ids_from_recs(recs: list[dict]) -> list[int]:
    return [int(r["movieId"]) for r in recs]


def _evaluate_model(
    name: str,
    get_recs,             # callable(user_id, seen, N) -> list[int]
    test_map: dict[int, set[int]],
    train_seen: dict[int, set[int]],
    eval_users: list[int],
    k: int,
    k2: int,
) -> dict:
    p_k, r_k, ndcg_k, ndcg_k2, hits_k, mrr_k = [], [], [], [], [], []
    all_recs, all_rels = [], []

    for uid in eval_users:
        rel = test_map.get(uid, set())
        if not rel:
            continue
        seen = train_seen.get(uid, set())
        recs = get_recs(uid, seen, max(k, k2))

        p_k.append(precision_at_k(recs, rel, k))
        r_k.append(recall_at_k(recs, rel, k))
        ndcg_k.append(ndcg_at_k(recs, rel, k))
        ndcg_k2.append(ndcg_at_k(recs, rel, k2))
        hits_k.append(hit_rate_at_k(recs, rel, k))
        mrr_k.append(mrr_at_k(recs, rel, k))
        all_recs.append(recs)
        all_rels.append(rel)

    n = len(p_k)
    return {
        "model": name,
        "users_evaluated": n,
        f"precision@{k}": round(float(np.mean(p_k)), 4) if p_k else 0.0,
        f"recall@{k}": round(float(np.mean(r_k)), 4) if r_k else 0.0,
        f"ndcg@{k}": round(float(np.mean(ndcg_k)), 4) if ndcg_k else 0.0,
        f"ndcg@{k2}": round(float(np.mean(ndcg_k2)), 4) if ndcg_k2 else 0.0,
        f"hit_rate@{k}": round(float(np.mean(hits_k)), 4) if hits_k else 0.0,
        f"mrr@{k}": round(float(np.mean(mrr_k)), 4) if mrr_k else 0.0,
        f"map@{k}": round(map_at_k(all_recs, all_rels, k), 4),
    }


def run(n_users: int = 500, k: int = 10, k2: int = 20) -> None:
    print("Loading ratings …")
    ratings_path = DATA_DIR / "ratings.parquet"
    if not ratings_path.exists():
        raise FileNotFoundError(f"Ratings not found: {ratings_path}")
    ratings_df = pd.read_parquet(ratings_path)

    print("Splitting train / test (80/20 per user) …")
    train_df, test_map = _split_ratings(ratings_df)

    train_seen: dict[int, set[int]] = {
        int(uid): set(g["movieId"].astype(int).tolist())
        for uid, g in train_df.groupby("userId")
    }

    users_with_test = [u for u, rel in test_map.items() if rel]
    random.seed(42)
    eval_users = random.sample(users_with_test, min(n_users, len(users_with_test)))
    print(f"Evaluating on {len(eval_users)} users …\n")

    # ── Baselines ──────────────────────────────────────────────────────────────
    print("Fitting PopularityBaseline …")
    pop = PopularityBaseline().fit(train_df)

    print("Fitting NeighborhoodCF (k=20) …")
    ncf = NeighborhoodCF(k_neighbors=20).fit(train_df)

    # ── Full system ────────────────────────────────────────────────────────────
    print("Loading HybridRecommender (trains OCCF, GRU4Rec, KG) …")
    hybrid = HybridRecommender()
    hybrid.load_models()

    # ── Wrappers ───────────────────────────────────────────────────────────────
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
        ("Popularity",     pop_recs),
        ("NeighborhoodCF", ncf_recs),
        ("OCCF",           occf_recs),
        ("GRU4Rec",        gru_recs),
        ("KnowledgeGraph", kg_recs),
        ("Hybrid",         hybrid_recs),
    ]

    results = []
    for name, fn in models:
        print(f"  Evaluating {name} …")
        res = _evaluate_model(name, fn, test_map, train_seen, eval_users, k, k2)
        results.append(res)

    # ── Print table ────────────────────────────────────────────────────────────
    cols = [f"precision@{k}", f"recall@{k}", f"ndcg@{k}", f"ndcg@{k2}",
            f"hit_rate@{k}", f"map@{k}", f"mrr@{k}"]
    header = f"{'Model':<18}" + "".join(f"{c:>14}" for c in cols)
    print("\n" + "=" * len(header))
    print(header)
    print("-" * len(header))
    for r in results:
        row = f"{r['model']:<18}" + "".join(f"{r[c]:>14.4f}" for c in cols)
        print(row)
    print("=" * len(header))

    # ── Save JSON ──────────────────────────────────────────────────────────────
    out_path = DATA_DIR / "eval_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--users", type=int, default=500, help="Number of test users")
    parser.add_argument("--k", type=int, default=10, help="Primary cutoff K")
    parser.add_argument("--k2", type=int, default=20, help="Secondary cutoff K")
    args = parser.parse_args()
    run(n_users=args.users, k=args.k, k2=args.k2)


if __name__ == "__main__":
    main()
