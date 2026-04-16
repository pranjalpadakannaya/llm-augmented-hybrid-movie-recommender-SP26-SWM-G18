from pathlib import Path

# Raw data (ml-20m/ lives one level above backend/)
RAW_DIR = Path(__file__).parent.parent.parent / "ml-20m"

# Output directory for processed artifacts
PROCESSED_DIR = Path(__file__).parent.parent.parent / "data" / "processed"

# SQLite database path
DB_PATH = PROCESSED_DIR / "cineai.db"

# Split ratios (must sum to 1.0)
TRAIN_RATIO = 0.8
VAL_RATIO = 0.1
TEST_RATIO = 0.1

# Minimum number of ratings a user must have to be included
MIN_USER_RATINGS = 5

# Session gap threshold for GRU4Rec (seconds)
SESSION_GAP_SECONDS = 30 * 60  # 30 minutes
