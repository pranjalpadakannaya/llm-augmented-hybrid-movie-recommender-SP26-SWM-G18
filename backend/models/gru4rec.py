from __future__ import annotations

from pathlib import Path
from typing import Optional, List, Dict, Tuple

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader


class SessionDataset(Dataset):
    def __init__(self, samples: List[Tuple[List[int], int]]):
        self.samples = samples

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int):
        seq, target = self.samples[idx]
        return torch.tensor(seq, dtype=torch.long), torch.tensor(target, dtype=torch.long)


def collate_batch(batch):
    sequences, targets = zip(*batch)
    lengths = torch.tensor([len(s) for s in sequences], dtype=torch.long)

    max_len = max(lengths).item()
    padded = torch.zeros(len(sequences), max_len, dtype=torch.long)

    for i, seq in enumerate(sequences):
        padded[i, : len(seq)] = seq

    targets = torch.stack(targets)
    return padded, lengths, targets


class GRU4RecNet(nn.Module):
    def __init__(self, num_items: int, embed_dim: int = 64, hidden_dim: int = 128, dropout: float = 0.2):
        super().__init__()
        self.embedding = nn.Embedding(num_items, embed_dim, padding_idx=0)
        self.gru = nn.GRU(embed_dim, hidden_dim, batch_first=True)
        self.dropout = nn.Dropout(dropout)
        self.output = nn.Linear(hidden_dim, num_items)

    def forward(self, x: torch.Tensor, lengths: torch.Tensor) -> torch.Tensor:
        emb = self.embedding(x)
        packed_out, _ = self.gru(emb)

        batch_size, seq_len, hidden_dim = packed_out.shape
        lengths = lengths.clamp(min=1)

        idx = (lengths - 1).view(-1, 1, 1).expand(batch_size, 1, hidden_dim)
        last_hidden = packed_out.gather(1, idx).squeeze(1)

        last_hidden = self.dropout(last_hidden)
        logits = self.output(last_hidden)
        return logits


class GRU4RecModel:
    def __init__(
        self,
        embed_dim: int = 64,
        hidden_dim: int = 128,
        batch_size: int = 256,
        lr: float = 1e-3,
        epochs: int = 3,
        max_seq_len: int = 50,
        gap_threshold_minutes: int = 30,
        device: Optional[str] = None,
    ):
        self.embed_dim = embed_dim
        self.hidden_dim = hidden_dim
        self.batch_size = batch_size
        self.lr = lr
        self.epochs = epochs
        self.max_seq_len = max_seq_len
        self.gap_threshold_seconds = gap_threshold_minutes * 60

        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        self.model: Optional[GRU4RecNet] = None
        self.optimizer = None
        self.criterion = nn.CrossEntropyLoss()

        self.movie_titles: Dict[int, str] = {}
        self.item2idx: Dict[int, int] = {}
        self.idx2item: Dict[int, int] = {}
        self.user_sessions: Dict[int, List[List[int]]] = {}

        self.train_samples: List[Tuple[List[int], int]] = []
        self.val_samples: List[Tuple[List[int], int]] = []

    def _repo_root(self) -> Path:
        return Path(__file__).resolve().parents[2]

    def _default_sessions_path(self) -> Path:
        return self._repo_root() / "data" / "processed" / "sessions.parquet"

    def _default_movies_path(self) -> Optional[Path]:
        candidates = [
            self._repo_root() / "data" / "processed" / "movies.parquet",
            self._repo_root() / "data" / "processed" / "movies.csv",
            self._repo_root() / "ml-20m" / "movies.csv",
        ]
        for path in candidates:
            if path.exists():
                return path
        return None

    def _load_movies(self, movies_path: Optional[Path]):
        self.movie_titles = {}
        if movies_path is None or not movies_path.exists():
            return

        if movies_path.suffix.lower() == ".parquet":
            movies_df = pd.read_parquet(movies_path)
        else:
            movies_df = pd.read_csv(movies_path)

        if "movieId" in movies_df.columns and "title" in movies_df.columns:
            self.movie_titles = dict(
                zip(
                    movies_df["movieId"].astype(int),
                    movies_df["title"].astype(str),
                )
            )

    def _build_sessions(self, df: pd.DataFrame) -> pd.DataFrame:
        required_cols = {"userId", "movieId", "timestamp"}
        if not required_cols.issubset(df.columns):
            raise ValueError(f"sessions.parquet must contain at least {required_cols}")

        df = df.copy()
        df["timestamp"] = pd.to_numeric(df["timestamp"], errors="coerce")
        df = df.dropna(subset=["timestamp", "userId", "movieId"])
        df["timestamp"] = df["timestamp"].astype(np.int64)
        df["userId"] = df["userId"].astype(int)
        df["movieId"] = df["movieId"].astype(int)

        if "session_id" in df.columns:
            df["session_key"] = df["session_id"].astype(str)
        else:
            df = df.sort_values(["userId", "timestamp"])
            gap = df.groupby("userId")["timestamp"].diff().fillna(0)
            new_session = (gap > self.gap_threshold_seconds).astype(int)
            df["session_id"] = new_session.groupby(df["userId"]).cumsum()
            df["session_key"] = df["userId"].astype(str) + "_" + df["session_id"].astype(str)

        df = df.sort_values(["userId", "session_key", "timestamp"])
        return df

    def _build_samples(self, sessions_df: pd.DataFrame):
        grouped = sessions_df.groupby("session_key", sort=False)

        sessions = []
        users = []
        end_times = []

        for session_key, g in grouped:
            seq = g["movieId"].tolist()
            if len(seq) < 2:
                continue
            sessions.append(seq)
            users.append(int(g["userId"].iloc[0]))
            end_times.append(int(g["timestamp"].max()))

        # Build item vocabulary
        all_items = sorted({item for seq in sessions for item in seq})
        self.item2idx = {item_id: idx + 1 for idx, item_id in enumerate(all_items)}
        self.idx2item = {idx: item_id for item_id, idx in self.item2idx.items()}

        # Keep per-user session history for inference
        self.user_sessions = {}
        for uid, seq in zip(users, sessions):
            self.user_sessions.setdefault(uid, []).append(seq)

        # Convert each session into one training example:
        # input = all but last item, target = last item
        samples = []
        for seq in sessions:
            encoded = [self.item2idx[i] for i in seq if i in self.item2idx]
            if len(encoded) < 2:
                continue
            encoded = encoded[-self.max_seq_len :]
            samples.append((encoded[:-1], encoded[-1]))

        # Chronological split by session end time
        order = np.argsort(np.array(end_times))
        samples_sorted = [samples[i] for i in order if i < len(samples)]

        if len(samples_sorted) < 10:
            self.train_samples = samples_sorted
            self.val_samples = []
            return

        val_size = max(1, int(0.1 * len(samples_sorted)))
        self.train_samples = samples_sorted[:-val_size]
        self.val_samples = samples_sorted[-val_size:]

    def load_data(self, sessions_path: str | Path | None = None, movies_path: str | Path | None = None):
        print("Loading data...")

        sessions_path = Path(sessions_path) if sessions_path else self._default_sessions_path()
        movies_path = Path(movies_path) if movies_path else self._default_movies_path()

        if not sessions_path.exists():
            raise FileNotFoundError(f"Sessions file not found: {sessions_path}")

        if sessions_path.suffix.lower() == ".parquet":
            df = pd.read_parquet(sessions_path)
        else:
            df = pd.read_csv(sessions_path)

        df = self._build_sessions(df)
        self._load_movies(movies_path)

        self._build_samples(df)

        num_items = len(self.item2idx) + 1  # 0 is PAD
        self.model = GRU4RecNet(
            num_items=num_items,
            embed_dim=self.embed_dim,
            hidden_dim=self.hidden_dim,
        ).to(self.device)
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=self.lr)

        print(f"Data loaded. Train samples: {len(self.train_samples)} | Val samples: {len(self.val_samples)}")
        print(f"Items: {len(self.item2idx)} | Device: {self.device}")

    def train(self):
        if self.model is None:
            raise RuntimeError("Call load_data() before train().")

        if len(self.train_samples) == 0:
            raise RuntimeError("No training samples found.")

        train_loader = DataLoader(
            SessionDataset(self.train_samples),
            batch_size=self.batch_size,
            shuffle=True,
            collate_fn=collate_batch,
        )

        self.model.train()
        print("Training GRU4Rec model...")

        for epoch in range(self.epochs):
            total_loss = 0.0

            for x, lengths, targets in train_loader:
                x = x.to(self.device)
                lengths = lengths.to(self.device)
                targets = targets.to(self.device)

                self.optimizer.zero_grad()
                logits = self.model(x, lengths)
                loss = self.criterion(logits, targets)
                loss.backward()
                self.optimizer.step()

                total_loss += loss.item()

            avg_loss = total_loss / max(1, len(train_loader))
            print(f"Epoch {epoch + 1}/{self.epochs} - loss: {avg_loss:.4f}")

        print("Training complete.")

    @torch.no_grad()
    def recommend_from_history(self, history_movie_ids: List[int], N: int = 10) -> List[Dict]:
        if self.model is None:
            raise RuntimeError("Model is not trained. Call load_data() and train() first.")

        encoded = [self.item2idx[m] for m in history_movie_ids if m in self.item2idx]
        if len(encoded) == 0:
            return []

        encoded = encoded[-self.max_seq_len :]
        x = torch.tensor(encoded, dtype=torch.long, device=self.device).unsqueeze(0)
        lengths = torch.tensor([len(encoded)], dtype=torch.long, device=self.device)

        self.model.eval()
        logits = self.model(x, lengths).squeeze(0)

        # Exclude PAD and already seen items
        seen = set(encoded)
        for item_idx in seen:
            logits[item_idx] = -1e9
        logits[0] = -1e9

        topk = torch.topk(logits, k=min(N, logits.shape[0] - 1))
        recs = []

        for idx, score in zip(topk.indices.tolist(), topk.values.tolist()):
            movie_id = self.idx2item.get(idx)
            if movie_id is None:
                continue
            recs.append(
                {
                    "movieId": int(movie_id),
                    "title": self.movie_titles.get(int(movie_id), f"Movie {movie_id}"),
                    "score": float(score),
                    "model": "GRU4Rec",
                }
            )

        return recs

    def recommend_for_user(self, user_id: int, N: int = 10) -> List[Dict]:
        sessions = self.user_sessions.get(int(user_id))
        if not sessions:
            return []

        # Use the most recent session for inference
        history = sessions[-1]
        return self.recommend_from_history(history, N=N)


if __name__ == "__main__":
    model = GRU4RecModel(epochs=3, batch_size=256, embed_dim=64, hidden_dim=128)
    model.load_data()
    model.train()

    print("\nSample recommendations for user 1:")
    recs = model.recommend_for_user(user_id=1, N=10)

    for r in recs:
        print(r)