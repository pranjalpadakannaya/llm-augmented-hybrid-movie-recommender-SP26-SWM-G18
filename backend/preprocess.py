#!/usr/bin/env python3
"""
MovieLens 20M preprocessing pipeline.

Run from the backend/ directory:
    python preprocess.py

Reads raw CSVs from ../ml-20m/
Writes Parquet + SQLite to  ../data/processed/
"""

import sys
import time
from pathlib import Path

import pandas as pd


# Allow running as a script without installing the package
sys.path.insert(0, str(Path(__file__).parent))

from preprocessing.clean import (
    clean_genome_scores,
    clean_links,
    clean_movies,
    clean_ratings,
    clean_tags,
)
from preprocessing.config import (
    DB_PATH,
    PROCESSED_DIR,
    RAW_DIR,
    SESSION_GAP_SECONDS,
    TRAIN_RATIO,
    VAL_RATIO,
)
from preprocessing.sessions import construct_sessions
from preprocessing.split import create_splits
from preprocessing.storage import save_parquet, save_sqlite


def _load(name: str, **kwargs) -> pd.DataFrame:
    path = RAW_DIR / name
    print(f"  Loading {path.name} ...", end=" ", flush=True)
    t0 = time.time()
    df = pd.read_csv(path, **kwargs)
    print(f"{len(df):,} rows  ({time.time() - t0:.1f}s)")
    return df


def main() -> None:
    print("=" * 60)
    print("CineAI — MovieLens 20M Preprocessing Pipeline")
    print("=" * 60)
    print(f"  Raw data : {RAW_DIR}")
    print(f"  Output   : {PROCESSED_DIR}")
    print()

    if not RAW_DIR.exists():
        print(f"[ERROR] Raw data directory not found: {RAW_DIR}")
        sys.exit(1)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    # 1. Load raw CSVs
    # ------------------------------------------------------------------ #
    print("[ 1/7 ] Loading raw CSVs")
    movies_raw = _load("movies.csv", dtype={"movieId": "int32"})
    ratings_raw = _load(
        "ratings.csv",
        dtype={"userId": "int32", "movieId": "int32", "rating": "float32"},
    )
    links_raw = _load("links.csv", dtype={"movieId": "int32"})
    tags_raw = _load("tags.csv", dtype={"userId": "int32", "movieId": "int32"})
    genome_raw = _load(
        "genome-scores.csv",
        dtype={"movieId": "int32", "tagId": "int32", "relevance": "float32"},
    )
    print()

    # ------------------------------------------------------------------ #
    # 2. Clean movies (establishes the valid movieId universe)
    # ------------------------------------------------------------------ #
    print("[ 2/7 ] Cleaning movies")
    movies = clean_movies(movies_raw)
    valid_movie_ids = set(movies["movieId"].tolist())
    print(f"  movies: {len(movies_raw):,} → {len(movies):,}")
    print()

    # ------------------------------------------------------------------ #
    # 3. Clean ratings (establishes the valid userId universe)
    # ------------------------------------------------------------------ #
    print("[ 3/7 ] Cleaning ratings")
    ratings_clean = clean_ratings(ratings_raw, valid_movie_ids)
    valid_user_ids = set(ratings_clean["userId"].tolist())
    print(
        f"  ratings: {len(ratings_raw):,} → {len(ratings_clean):,}  "
        f"({len(valid_user_ids):,} users)"
    )
    del ratings_raw
    print()

    # ------------------------------------------------------------------ #
    # 4. Clean remaining files
    # ------------------------------------------------------------------ #
    print("[ 4/7 ] Cleaning links, tags, genome-scores")
    links = clean_links(links_raw, valid_movie_ids)
    tags = clean_tags(tags_raw, valid_movie_ids, valid_user_ids)
    genome = clean_genome_scores(genome_raw, valid_movie_ids)

    tmdb_coverage = links["tmdbId"].notna().sum()
    print(f"  links  : {len(links_raw):,} → {len(links):,}  "
          f"(tmdbId coverage: {tmdb_coverage/len(links)*100:.1f}%)")
    print(f"  tags   : {len(tags_raw):,} → {len(tags):,}")
    print(f"  genome : {len(genome_raw):,} → {len(genome):,}")
    del links_raw, tags_raw, genome_raw
    print()

    # ------------------------------------------------------------------ #
    # 5. Train / val / test splits
    # ------------------------------------------------------------------ #
    print("[ 5/7 ] Creating train/val/test splits (80/10/10 per user, chronological)")
    ratings = create_splits(ratings_clean, train_ratio=TRAIN_RATIO, val_ratio=VAL_RATIO)
    split_counts = ratings["split"].value_counts()
    print(f"  train: {split_counts.get('train', 0):,}")
    print(f"  val  : {split_counts.get('val', 0):,}")
    print(f"  test : {split_counts.get('test', 0):,}")
    del ratings_clean
    print()

    # ------------------------------------------------------------------ #
    # 6. Session construction for GRU4Rec
    # ------------------------------------------------------------------ #
    print(
        f"[ 6/7 ] Building GRU4Rec sessions  "
        f"(gap threshold: {SESSION_GAP_SECONDS // 60} min)"
    )
    sessions = construct_sessions(ratings, gap_seconds=SESSION_GAP_SECONDS)
    n_sessions = sessions["sessionId"].nunique()
    avg_len = len(sessions) / n_sessions if n_sessions else 0
    print(f"  {n_sessions:,} sessions  |  avg length: {avg_len:.1f} items")
    print()

    # ------------------------------------------------------------------ #
    # 7. Save to Parquet + SQLite
    # ------------------------------------------------------------------ #
    print("[ 7/7 ] Writing output files")

    files = {
        "movies.parquet": movies,
        "ratings.parquet": ratings,
        "links.parquet": links,
        "tags.parquet": tags,
        "genome_scores.parquet": genome,
        "sessions.parquet": sessions,
    }

    for fname, df in files.items():
        path = PROCESSED_DIR / fname
        save_parquet(df, path)
        size_mb = path.stat().st_size / 1_048_576
        print(f"  {fname:<26} {len(df):>12,} rows  ({size_mb:.1f} MB)")

    # SQLite
    stats = {
        "n_movies": len(movies),
        "n_users": len(valid_user_ids),
        "n_ratings": len(ratings),
        "n_train": int(split_counts.get("train", 0)),
        "n_val": int(split_counts.get("val", 0)),
        "n_test": int(split_counts.get("test", 0)),
        "n_sessions": n_sessions,
    }
    save_sqlite(movies, links, DB_PATH, stats)
    db_size_mb = DB_PATH.stat().st_size / 1_048_576
    print(f"  cineai.db                    metadata SQLite  ({db_size_mb:.1f} MB)")
    print()

    # ------------------------------------------------------------------ #
    # Summary
    # ------------------------------------------------------------------ #
    print("=" * 60)
    print("Preprocessing complete.")
    print(f"  Movies   : {len(movies):,}")
    print(f"  Users    : {len(valid_user_ids):,}")
    print(f"  Ratings  : {len(ratings):,}  (train/val/test split)")
    print(f"  Sessions : {n_sessions:,}  (GRU4Rec, train only)")
    print(f"  Output   : {PROCESSED_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
