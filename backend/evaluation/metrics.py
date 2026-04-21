"""
Ranking evaluation metrics for recommendation systems.

All functions follow the convention:
    recommended: ordered list of item IDs (best first)
    relevant:    set / list of ground-truth item IDs
    k:           cut-off rank
"""
from __future__ import annotations

import math
from typing import Sequence


def precision_at_k(recommended: Sequence, relevant: set, k: int) -> float:
    if k <= 0:
        return 0.0
    hits = sum(1 for item in recommended[:k] if item in relevant)
    return hits / k


def recall_at_k(recommended: Sequence, relevant: set, k: int) -> float:
    if not relevant:
        return 0.0
    hits = sum(1 for item in recommended[:k] if item in relevant)
    return hits / len(relevant)


def hit_rate_at_k(recommended: Sequence, relevant: set, k: int) -> float:
    return 1.0 if any(item in relevant for item in recommended[:k]) else 0.0


def average_precision(recommended: Sequence, relevant: set, k: int) -> float:
    if not relevant:
        return 0.0
    hits = 0
    precision_sum = 0.0
    for i, item in enumerate(recommended[:k], start=1):
        if item in relevant:
            hits += 1
            precision_sum += hits / i
    return precision_sum / min(len(relevant), k)


def map_at_k(list_of_recommended: list[Sequence], list_of_relevant: list[set], k: int) -> float:
    if not list_of_recommended:
        return 0.0
    return sum(
        average_precision(rec, rel, k)
        for rec, rel in zip(list_of_recommended, list_of_relevant)
    ) / len(list_of_recommended)


def ndcg_at_k(recommended: Sequence, relevant: set, k: int) -> float:
    dcg = sum(
        1.0 / math.log2(i + 2)
        for i, item in enumerate(recommended[:k])
        if item in relevant
    )
    ideal_hits = min(len(relevant), k)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_hits))
    return dcg / idcg if idcg > 0 else 0.0


def mrr_at_k(recommended: Sequence, relevant: set, k: int) -> float:
    for i, item in enumerate(recommended[:k], start=1):
        if item in relevant:
            return 1.0 / i
    return 0.0
