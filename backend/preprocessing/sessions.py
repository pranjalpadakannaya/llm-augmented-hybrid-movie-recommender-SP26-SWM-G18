"""
Session construction for GRU4Rec.

A new session is started for a user when the gap between consecutive
interactions exceeds SESSION_GAP_SECONDS. Sessions with only one item
are dropped (not useful for next-item prediction).
"""

import pandas as pd

from .config import SESSION_GAP_SECONDS


def construct_sessions(
    ratings_df: pd.DataFrame,
    gap_seconds: int = SESSION_GAP_SECONDS,
) -> pd.DataFrame:
    """
    Build GRU4Rec-style interaction sessions from training ratings.

    Only rows with split == 'train' are used.

    Returns a DataFrame with columns:
        sessionId (str)    — unique identifier: "{userId}_{session_idx}"
        userId    (int32)
        movieId   (int32)
        rating    (float32)
        timestamp (int64)
        position  (int32)  — 0-indexed position within the session
    """
    train = ratings_df[ratings_df["split"] == "train"].copy()
    train = train.sort_values(["userId", "timestamp"])

    records = []
    for user_id, group in train.groupby("userId", sort=False):
        timestamps = group["timestamp"].values
        movie_ids = group["movieId"].values
        ratings = group["rating"].values

        session_idx = 0
        session_start = 0

        for i in range(1, len(timestamps)):
            gap = timestamps[i] - timestamps[i - 1]
            if gap > gap_seconds:
                # Flush current session
                session_len = i - session_start
                if session_len > 1:
                    sid = f"{user_id}_{session_idx}"
                    for pos in range(session_len):
                        records.append(
                            (
                                sid,
                                user_id,
                                movie_ids[session_start + pos],
                                ratings[session_start + pos],
                                timestamps[session_start + pos],
                                pos,
                            )
                        )
                session_idx += 1
                session_start = i

        # Flush the last session
        session_len = len(timestamps) - session_start
        if session_len > 1:
            sid = f"{user_id}_{session_idx}"
            for pos in range(session_len):
                records.append(
                    (
                        sid,
                        user_id,
                        movie_ids[session_start + pos],
                        ratings[session_start + pos],
                        timestamps[session_start + pos],
                        pos,
                    )
                )

    sessions_df = pd.DataFrame(
        records,
        columns=["sessionId", "userId", "movieId", "rating", "timestamp", "position"],
    )
    sessions_df["userId"] = sessions_df["userId"].astype("int32")
    sessions_df["movieId"] = sessions_df["movieId"].astype("int32")
    sessions_df["rating"] = sessions_df["rating"].astype("float32")
    sessions_df["timestamp"] = sessions_df["timestamp"].astype("int64")
    sessions_df["position"] = sessions_df["position"].astype("int32")
    return sessions_df.reset_index(drop=True)
