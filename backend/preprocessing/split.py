"""
Chronological 80/10/10 train/val/test split per user.
"""

import math
import numpy as np
import pandas as pd


def create_splits(
    ratings_df: pd.DataFrame,
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
) -> pd.DataFrame:
    """
    Assign each rating to train, val, or test based on per-user chronological order.

    For a user with n ratings:
      - positions [0, floor(n*train_ratio))                        → 'train'
      - positions [floor(n*train_ratio), floor(n*(train+val)))     → 'val'
      - remaining                                                   → 'test'

    Returns ratings_df with an added 'split' column (str).
    """
    df = ratings_df.copy()
    df = df.sort_values(["userId", "timestamp"]).reset_index(drop=True)

    # Rank each rating within its user group (0-indexed)
    df["_rank"] = df.groupby("userId").cumcount()
    df["_n"] = df.groupby("userId")["userId"].transform("count")

    train_end = (df["_n"] * train_ratio).apply(math.floor)
    val_end = (df["_n"] * (train_ratio + val_ratio)).apply(math.floor)

    conditions = [
        df["_rank"] < train_end,
        df["_rank"] < val_end,
    ]
    choices = ["train", "val"]
    df["split"] = np.select(conditions, choices, default="test")

    df.drop(columns=["_rank", "_n"], inplace=True)
    return df.reset_index(drop=True)
