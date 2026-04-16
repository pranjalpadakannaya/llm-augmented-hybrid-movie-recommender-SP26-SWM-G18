"""
Cleaning functions for each MovieLens 20M CSV file.
Each function accepts a raw DataFrame and returns a cleaned one.
"""

import re
import numpy as np
import pandas as pd

from .config import MIN_USER_RATINGS

_YEAR_RE = re.compile(r"\((\d{4})\)\s*$")


def clean_movies(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean movies.csv.

    Input columns: movieId, title, genres
    Output columns: movieId (int32), title (str), year (Int16), genres (object/list)
    """
    df = df.copy()
    df.dropna(subset=["movieId"], inplace=True)
    df.drop_duplicates(subset=["movieId"], inplace=True)

    # Extract year from title string, e.g. "Toy Story (1995)" -> year=1995
    years = df["title"].str.extract(_YEAR_RE, expand=False)
    df["year"] = pd.to_numeric(years, errors="coerce").astype("Int16")

    # Strip the "(YYYY)" suffix from the title
    df["title"] = df["title"].str.replace(_YEAR_RE, "", regex=True).str.strip()

    # Split pipe-separated genres into a Python list
    df["genres"] = df["genres"].apply(
        lambda g: []
        if pd.isna(g) or g.strip() == "(no genres listed)"
        else [x.strip() for x in g.split("|") if x.strip()]
    )

    df["movieId"] = df["movieId"].astype("int32")
    return df[["movieId", "title", "year", "genres"]].reset_index(drop=True)


def clean_ratings(df: pd.DataFrame, valid_movie_ids: set) -> pd.DataFrame:
    """
    Clean ratings.csv.

    Input columns: userId, movieId, rating, timestamp
    Output columns: userId (int32), movieId (int32), rating (float32), timestamp (int64)
    """
    df = df.copy()

    # Keep only ratings for movies we know about
    df = df[df["movieId"].isin(valid_movie_ids)]

    # Validate rating range
    df = df[(df["rating"] >= 0.5) & (df["rating"] <= 5.0)]

    # For duplicate (userId, movieId) pairs keep the most recent interaction
    df.sort_values("timestamp", inplace=True)
    df.drop_duplicates(subset=["userId", "movieId"], keep="last", inplace=True)

    # Drop users with too few interactions
    user_counts = df["userId"].value_counts()
    active_users = user_counts[user_counts >= MIN_USER_RATINGS].index
    df = df[df["userId"].isin(active_users)]

    df["userId"] = df["userId"].astype("int32")
    df["movieId"] = df["movieId"].astype("int32")
    df["rating"] = df["rating"].astype("float32")
    df["timestamp"] = df["timestamp"].astype("int64")

    return df[["userId", "movieId", "rating", "timestamp"]].reset_index(drop=True)


def clean_links(df: pd.DataFrame, valid_movie_ids: set) -> pd.DataFrame:
    """
    Clean links.csv.

    Input columns: movieId, imdbId, tmdbId
    Output columns: movieId (int32), imdbId (Int64), tmdbId (Int64)
    """
    df = df.copy()
    df = df[df["movieId"].isin(valid_movie_ids)]
    df["movieId"] = df["movieId"].astype("int32")
    df["imdbId"] = pd.to_numeric(df["imdbId"], errors="coerce").astype("Int64")
    df["tmdbId"] = pd.to_numeric(df["tmdbId"], errors="coerce").astype("Int64")
    return df[["movieId", "imdbId", "tmdbId"]].reset_index(drop=True)


def clean_tags(
    df: pd.DataFrame, valid_movie_ids: set, valid_user_ids: set
) -> pd.DataFrame:
    """
    Clean tags.csv.

    Input columns: userId, movieId, tag, timestamp
    Output columns: userId (int32), movieId (int32), tag (str), timestamp (int64)
    """
    df = df.copy()
    df["tag"] = df["tag"].astype(str).str.strip()
    df = df[df["tag"].notna() & (df["tag"] != "") & (df["tag"] != "nan")]
    df = df[df["movieId"].isin(valid_movie_ids)]
    df = df[df["userId"].isin(valid_user_ids)]
    df["userId"] = df["userId"].astype("int32")
    df["movieId"] = df["movieId"].astype("int32")
    df["timestamp"] = df["timestamp"].astype("int64")
    return df[["userId", "movieId", "tag", "timestamp"]].reset_index(drop=True)


def clean_genome_scores(df: pd.DataFrame, valid_movie_ids: set) -> pd.DataFrame:
    """
    Clean genome-scores.csv.

    Input columns: movieId, tagId, relevance
    Output columns: movieId (int32), tagId (int32), relevance (float32)
    """
    df = df.copy()
    df = df[df["movieId"].isin(valid_movie_ids)]

    out_of_range = (df["relevance"] < 0.0) | (df["relevance"] > 1.0)
    if out_of_range.any():
        print(
            f"  [warn] {out_of_range.sum()} genome-score rows outside [0,1] — clamping"
        )
        df["relevance"] = df["relevance"].clip(0.0, 1.0)

    df["movieId"] = df["movieId"].astype("int32")
    df["tagId"] = df["tagId"].astype("int32")
    df["relevance"] = df["relevance"].astype("float32")
    return df[["movieId", "tagId", "relevance"]].reset_index(drop=True)
