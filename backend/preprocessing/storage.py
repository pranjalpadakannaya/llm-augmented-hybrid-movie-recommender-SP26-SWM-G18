"""
Storage layer: write processed DataFrames to Parquet files and a SQLite database.
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


def save_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, engine="pyarrow", index=False, compression="snappy")


def save_sqlite(
    movies_df: pd.DataFrame,
    links_df: pd.DataFrame,
    db_path: Path,
    stats: dict,
) -> None:
    """
    Create / overwrite the SQLite metadata database.

    Tables:
        movies(movieId, title, year)
        genres(genre)
        movie_genres(movieId, genre)
        links(movieId, imdbId, tmdbId)
        preprocessing_log(run_ts, n_movies, n_users, n_ratings, n_train,
                          n_val, n_test, n_sessions)
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Remove stale database so schema is always fresh
    if db_path.exists():
        db_path.unlink()

    con = sqlite3.connect(db_path)
    cur = con.cursor()

    # --- movies ---
    cur.execute("""
        CREATE TABLE movies (
            movieId INTEGER PRIMARY KEY,
            title   TEXT NOT NULL,
            year    INTEGER
        )
        """)
    cur.executemany(
        "INSERT INTO movies VALUES (?, ?, ?)",
        [
            (int(r.movieId), r.title, None if pd.isna(r.year) else int(r.year))
            for r in movies_df.itertuples(index=False)
        ],
    )

    # --- genres (unique vocabulary) ---
    all_genres: set[str] = set()
    for g_list in movies_df["genres"]:
        all_genres.update(g_list)

    cur.execute("CREATE TABLE genres (genre TEXT PRIMARY KEY)")
    cur.executemany("INSERT INTO genres VALUES (?)", [(g,) for g in sorted(all_genres)])

    # --- movie_genres (many-to-many) ---
    cur.execute("""
        CREATE TABLE movie_genres (
            movieId INTEGER NOT NULL,
            genre   TEXT    NOT NULL,
            PRIMARY KEY (movieId, genre)
        )
        """)
    mg_rows = [
        (int(r.movieId), g) for r in movies_df.itertuples(index=False) for g in r.genres
    ]
    cur.executemany("INSERT INTO movie_genres VALUES (?, ?)", mg_rows)

    # --- links ---
    cur.execute("""
        CREATE TABLE links (
            movieId INTEGER PRIMARY KEY,
            imdbId  INTEGER,
            tmdbId  INTEGER
        )
        """)
    cur.executemany(
        "INSERT INTO links VALUES (?, ?, ?)",
        [
            (
                int(r.movieId),
                None if pd.isna(r.imdbId) else int(r.imdbId),
                None if pd.isna(r.tmdbId) else int(r.tmdbId),
            )
            for r in links_df.itertuples(index=False)
        ],
    )

    # --- preprocessing_log ---
    cur.execute("""
        CREATE TABLE preprocessing_log (
            run_ts     TEXT,
            n_movies   INTEGER,
            n_users    INTEGER,
            n_ratings  INTEGER,
            n_train    INTEGER,
            n_val      INTEGER,
            n_test     INTEGER,
            n_sessions INTEGER
        )
        """)
    cur.execute(
        "INSERT INTO preprocessing_log VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            datetime.now(timezone.utc).isoformat(),
            stats.get("n_movies", 0),
            stats.get("n_users", 0),
            stats.get("n_ratings", 0),
            stats.get("n_train", 0),
            stats.get("n_val", 0),
            stats.get("n_test", 0),
            stats.get("n_sessions", 0),
        ),
    )

    con.commit()
    con.close()
