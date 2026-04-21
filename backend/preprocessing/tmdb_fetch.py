"""
Bulk-fetch TMDB metadata for all MovieLens movies.

Usage:
    TMDB_READ_TOKEN=<token> python -m backend.preprocessing.tmdb_fetch

Reads  : data/processed/links.parquet   (movieId ↔ tmdbId mapping)
Writes : data/processed/tmdb_metadata.parquet

Supports resuming: already-fetched movieIds are skipped on re-run.
Rate limit: capped at 40 concurrent requests (TMDB free-tier safe).
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pandas as pd

try:
    import httpx
except ImportError:
    sys.exit("Install httpx first:  pip install httpx")

BASE_URL = "https://api.themoviedb.org/3"
DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"
OUT_PATH = DATA_DIR / "tmdb_metadata.parquet"
CONCURRENCY = 40
BATCH_SAVE = 500          # save to disk every N records


async def _fetch_one(
    client: httpx.AsyncClient,
    tmdb_id: int,
    token: str,
    sem: asyncio.Semaphore,
) -> dict | None:
    async with sem:
        url = f"{BASE_URL}/movie/{tmdb_id}?append_to_response=credits,keywords"
        headers = {"Authorization": f"Bearer {token}"}
        try:
            r = await client.get(url, headers=headers, timeout=15)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 429:
                await asyncio.sleep(3)
        except Exception:
            pass
        return None


def _extract(data: dict, movielens_id: int) -> dict:
    credits = data.get("credits", {})
    cast_names = [c["name"] for c in credits.get("cast", [])[:10]]
    directors = [c["name"] for c in credits.get("crew", []) if c.get("job") == "Director"]
    kw_names = [k["name"] for k in data.get("keywords", {}).get("keywords", [])[:20]]
    genre_names = [g["name"] for g in data.get("genres", [])]
    companies = [c["name"] for c in data.get("production_companies", [])[:5]]

    return {
        "movieId": movielens_id,
        "tmdbId": data.get("id"),
        "overview": (data.get("overview") or "").strip(),
        "cast": "|".join(cast_names),
        "director": "|".join(directors),
        "keywords": "|".join(kw_names),
        "genre_names": "|".join(genre_names),
        "runtime": int(data.get("runtime") or 0),
        "release_date": str(data.get("release_date") or ""),
        "vote_average": float(data.get("vote_average") or 0.0),
        "popularity": float(data.get("popularity") or 0.0),
        "poster_path": str(data.get("poster_path") or ""),
        "production_companies": "|".join(companies),
    }


async def fetch_all(token: str) -> None:
    links = pd.read_parquet(DATA_DIR / "links.parquet")
    links = links.dropna(subset=["tmdbId"]).copy()
    links["tmdbId"] = links["tmdbId"].astype(int)
    links["movieId"] = links["movieId"].astype(int)

    # Resume: skip already-fetched rows
    done_ids: set[int] = set()
    accumulated: list[dict] = []
    if OUT_PATH.exists():
        existing = pd.read_parquet(OUT_PATH)
        done_ids = set(existing["movieId"].tolist())
        accumulated = existing.to_dict("records")
        print(f"Resuming — {len(done_ids)} already fetched, {len(links) - len(done_ids)} remaining.")
    else:
        print(f"Starting fresh — {len(links)} movies to fetch.")

    pending = links[~links["movieId"].isin(done_ids)].reset_index(drop=True)
    if pending.empty:
        print("All movies already fetched.")
        return

    sem = asyncio.Semaphore(CONCURRENCY)
    total = len(pending)
    fetched = 0

    async with httpx.AsyncClient() as client:
        for start in range(0, total, BATCH_SAVE):
            chunk = pending.iloc[start : start + BATCH_SAVE]
            tasks = [
                _fetch_one(client, int(row.tmdbId), token, sem)
                for _, row in chunk.iterrows()
            ]
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            for (_, row), resp in zip(chunk.iterrows(), responses):
                if isinstance(resp, dict):
                    accumulated.append(_extract(resp, int(row.movieId)))

            fetched += len(chunk)
            print(f"  {fetched}/{total} fetched — saving checkpoint …")
            pd.DataFrame(accumulated).to_parquet(OUT_PATH, index=False)

    print(f"\nDone. {len(accumulated)} records saved to {OUT_PATH}")


def main() -> None:
    token = os.getenv("TMDB_READ_TOKEN")
    if not token:
        sys.exit("Error: set TMDB_READ_TOKEN environment variable.")
    asyncio.run(fetch_all(token))


if __name__ == "__main__":
    main()
