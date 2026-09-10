"""
generate_watch_history.py

Generates the fact_watch_history.csv dataset based on dim_users.csv,
dim_profiles.csv, dim_content.csv, dim_devices.csv, fact_user_sessions.csv
and bridge_content_genre.csv.

Author: Senior Data Engineering Team
"""

import pandas as pd
import numpy as np
import random
import os
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

INPUT_USERS_PATH = "data/dim_users.csv"
INPUT_PROFILES_PATH = "data/dim_profiles.csv"
INPUT_CONTENT_PATH = "data/dim_content.csv"
INPUT_DEVICES_PATH = "data/dim_devices.csv"
INPUT_SESSIONS_PATH = "data/fact_user_sessions.csv"
INPUT_BRIDGE_GENRE_PATH = "data/bridge_content_genre.csv"

POSSIBLE_GENRE_DIM_PATHS = [
    "data/dim_genre.csv",
    "data/dim_genres.csv",
]

OUTPUT_PATH = "data/fact_watch_history.csv"

TARGET_WATCH_COUNT = 300_000

WATCH_STATUS_OPTIONS = ["Completed", "Started", "Paused", "Abandoned"]
WATCH_STATUS_WEIGHTS = [0.50, 0.20, 0.18, 0.12]

PERCENTAGE_RANGES = {
    "Completed": (90.0, 100.0),
    "Started": (5.0, 40.0),
    "Paused": (40.0, 80.0),
    "Abandoned": (10.0, 60.0),
}

DOWNLOAD_TRUE_RATIO = 0.22

GENRE_WEIGHTS = {
    "Drama": 0.24,
    "Action": 0.18,
    "Comedy": 0.16,
    "Thriller": 0.13,
    "Romance": 0.10,
    "Documentary": 0.07,
}
OTHERS_WEIGHT = 0.12

KIDS_GENRES = ["Animation", "Fantasy", "Family"]

MIN_WATCH_DURATION_MIN = 1

# Random variation applied on top of runtime x percentage_completed when
# computing watch_duration_min, expressed as a fraction (+/- 5-8%).
DURATION_VARIATION_MIN = 0.03
DURATION_VARIATION_MAX = 0.06


# ---------------------------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------------------------

def load_input_data():
    """Load all required dimension and fact tables."""
    print("Loading input tables...")

    users_df = pd.read_csv(INPUT_USERS_PATH)
    profiles_df = pd.read_csv(INPUT_PROFILES_PATH)
    content_df = pd.read_csv(INPUT_CONTENT_PATH)
    devices_df = pd.read_csv(INPUT_DEVICES_PATH)
    sessions_df = pd.read_csv(
        INPUT_SESSIONS_PATH,
        parse_dates=["session_start", "session_end"]
    )
    bridge_genre_df = pd.read_csv(INPUT_BRIDGE_GENRE_PATH)

    print(f"  -> Loaded {len(users_df):,} users")
    print(f"  -> Loaded {len(profiles_df):,} profiles")
    print(f"  -> Loaded {len(content_df):,} content items")
    print(f"  -> Loaded {len(devices_df):,} devices")
    print(f"  -> Loaded {len(sessions_df):,} sessions")
    print(f"  -> Loaded {len(bridge_genre_df):,} content-genre links")

    genre_dim_df = None
    for path in POSSIBLE_GENRE_DIM_PATHS:
        if os.path.exists(path):
            genre_dim_df = pd.read_csv(path)
            print(f"  -> Loaded genre dimension table from: {path} ({len(genre_dim_df):,} rows)")
            break

    return users_df, profiles_df, content_df, devices_df, sessions_df, bridge_genre_df, genre_dim_df


# ---------------------------------------------------------------------------
# HELPERS - GENRE / CONTENT POOLS
# ---------------------------------------------------------------------------

def resolve_genre_name_column(bridge_genre_df, genre_dim_df):
    """
    Ensure bridge_genre_df has a usable genre name column.
    Returns the (possibly merged) bridge_genre_df and the resolved genre
    name column to use. Only merges ONCE -- callers should reuse the result.
    """
    name_candidates = ["genre_name", "genre", "genre_type", "name"]
    id_candidates = ["genre_id", "genreid", "genre_code"]

    bridge_cols_lower = {c.lower(): c for c in bridge_genre_df.columns}

    for candidate in name_candidates:
        if candidate in bridge_cols_lower:
            return bridge_genre_df, bridge_cols_lower[candidate]

    bridge_id_col = None
    for candidate in id_candidates:
        if candidate in bridge_cols_lower:
            bridge_id_col = bridge_cols_lower[candidate]
            break

    if bridge_id_col is not None and genre_dim_df is not None:
        dim_cols_lower = {c.lower(): c for c in genre_dim_df.columns}

        dim_id_col = None
        for candidate in id_candidates:
            if candidate in dim_cols_lower:
                dim_id_col = dim_cols_lower[candidate]
                break

        dim_name_col = None
        for candidate in name_candidates:
            if candidate in dim_cols_lower:
                dim_name_col = dim_cols_lower[candidate]
                break

        if dim_id_col is not None and dim_name_col is not None:
            merged = bridge_genre_df.merge(
                genre_dim_df[[dim_id_col, dim_name_col]],
                left_on=bridge_id_col,
                right_on=dim_id_col,
                how="left"
            )
            merged = merged.rename(columns={dim_name_col: "genre_name"})
            print(f"  -> Merged bridge table with genre dimension on "
                  f"'{bridge_id_col}' -> '{dim_id_col}' to resolve genre names")
            return merged, "genre_name"

    if bridge_id_col is not None:
        print(f"  -> WARNING: No genre dimension table found. "
              f"Using raw '{bridge_id_col}' values as genre keys.")
        return bridge_genre_df, bridge_id_col

    raise ValueError(
        "Could not detect a usable genre column in bridge_content_genre.csv. "
        f"Available columns: {list(bridge_genre_df.columns)}"
    )


def build_genre_content_pools(resolved_bridge_df, genre_col, content_df):
    """
    Build a mapping of genre_name -> list of content_id, and also
    a weighted list of genres based on target popularity distribution.
    Takes an ALREADY-RESOLVED bridge dataframe (with genre_col present).
    """
    merged = resolved_bridge_df.merge(
        content_df[["content_id"]], on="content_id", how="inner"
    )

    genre_pools = {}
    all_genres_present = merged[genre_col].dropna().unique().tolist()

    for genre in all_genres_present:
        content_ids = merged.loc[merged[genre_col] == genre, "content_id"].unique().tolist()
        if content_ids:
            genre_pools[genre] = content_ids

    known_genres = list(GENRE_WEIGHTS.keys())
    other_genres = [g for g in all_genres_present if g not in known_genres]

    weighted_genres = []
    weighted_probs = []

    for genre, weight in GENRE_WEIGHTS.items():
        if genre in genre_pools:
            weighted_genres.append(genre)
            weighted_probs.append(weight)

    if other_genres:
        other_pool = []
        for g in other_genres:
            other_pool.extend(genre_pools.get(g, []))
        if other_pool:
            genre_pools["__OTHERS__"] = list(set(other_pool))
            weighted_genres.append("__OTHERS__")
            weighted_probs.append(OTHERS_WEIGHT)

    if not weighted_genres:
        weighted_genres = list(genre_pools.keys())
        weighted_probs = [1.0 / len(weighted_genres)] * len(weighted_genres)
    else:
        total_weight = sum(weighted_probs)
        weighted_probs = [w / total_weight for w in weighted_probs]

    return genre_pools, weighted_genres, weighted_probs


def build_kids_content_pool(resolved_bridge_df, genre_col, content_df):
    """Build a content pool suited for kids profiles."""
    merged = resolved_bridge_df.merge(
        content_df[["content_id"]], on="content_id", how="inner"
    )
    kids_mask = merged[genre_col].isin(KIDS_GENRES)
    kids_content_ids = merged.loc[kids_mask, "content_id"].unique().tolist()
    return kids_content_ids


def pick_content_id(profile_is_kids, kids_pool, weighted_genres, weighted_probs, genre_pools, all_content_ids):
    """Select a content_id respecting genre popularity and kids restrictions."""
    if profile_is_kids and kids_pool and random.random() < 0.85:
        return random.choice(kids_pool)

    if weighted_genres:
        genre = random.choices(weighted_genres, weights=weighted_probs, k=1)[0]
        pool = genre_pools.get(genre)
        if pool:
            return random.choice(pool)

    return random.choice(all_content_ids)


# ---------------------------------------------------------------------------
# HELPERS - PROFILES / DEVICES
# ---------------------------------------------------------------------------

def detect_kids_flag_column(profiles_df):
    """Detect which column identifies kids profiles."""
    for candidate in ["profile_type", "is_kids", "profile_category"]:
        if candidate in profiles_df.columns:
            return candidate
    return None


def is_kids_profile(profile_row, kids_col):
    if kids_col is None:
        return False
    value = profile_row.get(kids_col)
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return False
    return "kid" in str(value).lower()


def detect_device_type_column(devices_df):
    for candidate in ["device_type", "device_category", "type"]:
        if candidate in devices_df.columns:
            return candidate
    return None


def build_device_type_lookup(devices_df, device_type_col):
    """Precompute device_id -> (is_tv, is_mobile) as a dict for O(1) lookups."""
    lookup = {}
    if device_type_col is None:
        for device_id in devices_df["device_id"]:
            lookup[device_id] = (False, False)
        return lookup

    for device_id, dtype in zip(devices_df["device_id"], devices_df[device_type_col]):
        dtype_str = str(dtype).lower()
        is_tv = "tv" in dtype_str
        is_mobile = "mobile" in dtype_str or "phone" in dtype_str
        lookup[device_id] = (is_tv, is_mobile)

    return lookup


# ---------------------------------------------------------------------------
# HELPERS - TIME / STATUS
# ---------------------------------------------------------------------------

def pick_watch_start_time(session_start, session_end):
    """
    Pick a random watch_start_time anywhere inside the session window.
    This is independent of watch_duration_min -- the session only
    determines WHEN the watch event started, never how long it lasted.
    """
    session_duration_sec = (session_end - session_start).total_seconds()

    if session_duration_sec <= 0:
        return session_start

    random_offset = random.uniform(0, session_duration_sec)
    return session_start + timedelta(seconds=random_offset)


def generate_watch_duration_min(runtime_minutes, percentage, duration_bias):
    """
    Compute a realistic watch_duration_min directly from the content's
    runtime and the percentage_completed for this watch event, instead of
    truncating to whatever time happens to be left in the session.

    Steps:
      1. base_duration = runtime_minutes x (percentage_completed / 100)
      2. Apply a small random variation of +/- 5-8%
      3. Apply the device bias (TV slightly longer, Mobile slightly shorter)
      4. Clamp the result to [MIN_WATCH_DURATION_MIN, runtime_minutes]
    """
    base_duration = runtime_minutes * (percentage / 100.0)

    variation_pct = random.uniform(DURATION_VARIATION_MIN, DURATION_VARIATION_MAX)
    if random.random() < 0.5:
        variation_pct = -variation_pct

    varied_duration = base_duration * (1 + variation_pct)
    biased_duration = varied_duration * duration_bias

    watch_duration_min = int(round(biased_duration))
    watch_duration_min = min(watch_duration_min, int(runtime_minutes))
    watch_duration_min = max(watch_duration_min, MIN_WATCH_DURATION_MIN)

    return watch_duration_min


def pick_status_and_percentage():
    """Pick a watch_status and a matching percentage_completed value."""
    status = random.choices(WATCH_STATUS_OPTIONS, weights=WATCH_STATUS_WEIGHTS, k=1)[0]
    low, high = PERCENTAGE_RANGES[status]
    percentage = round(random.uniform(low, high), 2)
    return status, percentage


# ---------------------------------------------------------------------------
# GENERATION
# ---------------------------------------------------------------------------

def generate_watch_history(users_df, profiles_df, content_df, devices_df,
                            sessions_df, bridge_genre_df, genre_dim_df):
    """Generate the fact_watch_history dataset."""
    print("Generating watch history records...")

    # Resolve genre names ONCE and reuse everywhere below
    resolved_bridge_df, genre_col = resolve_genre_name_column(bridge_genre_df, genre_dim_df)

    genre_pools, weighted_genres, weighted_probs = build_genre_content_pools(
        resolved_bridge_df, genre_col, content_df
    )
    kids_pool = build_kids_content_pool(resolved_bridge_df, genre_col, content_df)
    all_content_ids = content_df["content_id"].tolist()

    kids_col = detect_kids_flag_column(profiles_df)
    device_type_col = detect_device_type_column(devices_df)
    device_type_lookup = build_device_type_lookup(devices_df, device_type_col)

    runtime_lookup = content_df.set_index("content_id")["runtime_minutes"].to_dict()
    profiles_by_user = profiles_df.groupby("user_id")["profile_id"].apply(list).to_dict()
    profile_rows_by_id = profiles_df.set_index("profile_id").to_dict("index")

    valid_sessions = sessions_df[sessions_df["session_duration_sec"] > 60].copy()
    valid_sessions = valid_sessions[valid_sessions["user_id"].isin(profiles_by_user.keys())]

    total_sessions = len(valid_sessions)
    print(f"  -> {total_sessions:,} sessions eligible for watch events")

    records = []
    watch_id = 1

    # Estimate how many watch events per session on average to hit target count
    avg_events_per_session = max(TARGET_WATCH_COUNT / max(total_sessions, 1), 1)

    progress_step = max(total_sessions // 10, 1)

    for i, session_row in enumerate(valid_sessions.itertuples(index=False), start=1):
        user_id = session_row.user_id
        device_id = session_row.device_id
        session_id = session_row.session_id
        session_start = session_row.session_start
        session_end = session_row.session_end
        watch_date = session_start.date()

        user_profiles = profiles_by_user.get(user_id, [])
        if not user_profiles:
            continue

        num_events = np.random.poisson(avg_events_per_session)
        num_events = max(num_events, 0)
        if num_events == 0 and random.random() < 0.5:
            num_events = 1

        is_tv, is_mobile = device_type_lookup.get(device_id, (False, False))
        if is_tv:
            duration_bias = 1.03
        elif is_mobile:
            duration_bias = 0.98
        else:
            duration_bias = 1.00

        for _ in range(num_events):
            profile_id = random.choice(user_profiles)
            profile_row = profile_rows_by_id.get(profile_id, {})
            kids_flag = is_kids_profile(profile_row, kids_col)

            content_id = pick_content_id(
                kids_flag, kids_pool, weighted_genres, weighted_probs,
                genre_pools, all_content_ids
            )
            runtime_minutes = runtime_lookup.get(content_id, 60)
            if pd.isna(runtime_minutes) or runtime_minutes <= 0:
                runtime_minutes = 60

            watch_start_time = pick_watch_start_time(session_start, session_end)

            status, percentage = pick_status_and_percentage()

            watch_duration_min = generate_watch_duration_min(
                runtime_minutes, percentage, duration_bias
            )

            is_completed = bool(percentage >= 90.0)
            is_downloaded = random.random() < DOWNLOAD_TRUE_RATIO

            created_at = watch_start_time
            updated_at = created_at + timedelta(minutes=random.randint(0, 30))

            records.append({
                "watch_id": watch_id,
                "user_id": user_id,
                "profile_id": profile_id,
                "content_id": content_id,
                "session_id": session_id,
                "device_id": device_id,
                "watch_date": watch_date,
                "watch_start_time": watch_start_time,
                "watch_duration_min": watch_duration_min,
                "percentage_completed": percentage,
                "watch_status": status,
                "is_completed": is_completed,
                "is_downloaded": is_downloaded,
                "created_at": created_at,
                "updated_at": updated_at,
            })

            watch_id += 1

        if i % progress_step == 0 or i == total_sessions:
            print(f"  -> Processed {i:,}/{total_sessions:,} sessions "
                  f"({len(records):,} watch records so far)")

    watch_df = pd.DataFrame(records)

    # Trim / adjust to approximately the target record count
    if len(watch_df) > TARGET_WATCH_COUNT:
        watch_df = watch_df.sample(n=TARGET_WATCH_COUNT, random_state=RANDOM_SEED)
        watch_df = watch_df.sort_values("watch_id").reset_index(drop=True)
        watch_df["watch_id"] = range(1, len(watch_df) + 1)

    print(f"  -> Generated {len(watch_df):,} watch history records")

    return watch_df


# ---------------------------------------------------------------------------
# VALIDATION
# ---------------------------------------------------------------------------

def validate_watch_history(watch_df, users_df, profiles_df, content_df,
                            devices_df, sessions_df):
    """Run validation checks on the generated watch history dataset."""
    print("\nRunning validation checks...")

    required_columns = [
        "watch_id", "user_id", "profile_id", "content_id", "session_id",
        "device_id", "watch_date", "watch_start_time", "watch_duration_min",
        "percentage_completed", "watch_status", "is_completed",
        "is_downloaded", "created_at", "updated_at"
    ]

    missing_columns = [col for col in required_columns if col not in watch_df.columns]
    assert not missing_columns, f"Missing required columns: {missing_columns}"
    print("  [OK] Required columns present")

    assert watch_df["watch_id"].is_unique, "Duplicate watch_id values found"
    print("  [OK] watch_id is unique")

    assert watch_df["user_id"].isin(set(users_df["user_id"])).all(), "Invalid user_id found"
    print("  [OK] All user_id values are valid")

    assert watch_df["profile_id"].isin(set(profiles_df["profile_id"])).all(), "Invalid profile_id found"
    print("  [OK] All profile_id values are valid")

    assert watch_df["content_id"].isin(set(content_df["content_id"])).all(), "Invalid content_id found"
    print("  [OK] All content_id values are valid")

    assert watch_df["session_id"].isin(set(sessions_df["session_id"])).all(), "Invalid session_id found"
    print("  [OK] All session_id values are valid")

    assert watch_df["device_id"].isin(set(devices_df["device_id"])).all(), "Invalid device_id found"
    print("  [OK] All device_id values are valid")

    assert watch_df.isnull().sum().sum() == 0, "Null values found in dataset"
    print("  [OK] No null values found")

    assert (watch_df["watch_duration_min"] > 0).all(), "Found non-positive watch duration"
    print("  [OK] watch_duration_min is always positive")

    runtime_lookup = content_df.set_index("content_id")["runtime_minutes"].to_dict()
    runtime_check = watch_df["content_id"].map(runtime_lookup)
    assert (watch_df["watch_duration_min"] <= runtime_check).all(), \
        "Found watch_duration_min exceeding content runtime_minutes"
    print("  [OK] watch_duration_min never exceeds runtime_minutes")

    profile_owner_lookup = profiles_df.set_index("profile_id")["user_id"].to_dict()
    profile_owner_check = watch_df["profile_id"].map(profile_owner_lookup)
    assert (watch_df["user_id"] == profile_owner_check).all(), \
        "Found watch record where profile does not belong to the linked user"
    print("  [OK] Profile ownership matches user_id on every record")

    print("Validation passed successfully.\n")


# ---------------------------------------------------------------------------
# SUMMARY STATISTICS
# ---------------------------------------------------------------------------

def print_summary_statistics(watch_df):
    """Print summary statistics about the generated dataset."""
    print("=" * 60)
    print("SUMMARY STATISTICS - fact_watch_history.csv")
    print("=" * 60)

    print(f"Total watch records      : {len(watch_df):,}")
    print(f"Unique users              : {watch_df['user_id'].nunique():,}")
    print(f"Unique profiles           : {watch_df['profile_id'].nunique():,}")
    print(f"Unique content items      : {watch_df['content_id'].nunique():,}")
    print(f"Date range                : {watch_df['watch_date'].min()} -> {watch_df['watch_date'].max()}")

    print("\nWatch status distribution:")
    print((watch_df["watch_status"].value_counts(normalize=True) * 100).round(2).astype(str) + " %")

    completion_rate = (watch_df["is_completed"].sum() / len(watch_df)) * 100
    print(f"\nOverall completion rate   : {completion_rate:.2f} %")

    avg_duration = watch_df["watch_duration_min"].mean()
    print(f"Average watch duration    : {avg_duration:.2f} minutes")

    download_rate = (watch_df["is_downloaded"].sum() / len(watch_df)) * 100
    print(f"Downloaded content rate   : {download_rate:.2f} %")

    hours = pd.to_datetime(watch_df["watch_start_time"]).dt.hour
    print("\nViewing hour distribution (sample bucket check):")
    bucket_labels = {
        "6AM-12PM": hours.between(6, 11).sum(),
        "12PM-6PM": hours.between(12, 17).sum(),
        "6PM-10PM": hours.between(18, 21).sum(),
        "10PM-1AM": (hours.isin([22, 23, 0])).sum(),
        "1AM-6AM": hours.between(1, 5).sum(),
    }
    for label, count in bucket_labels.items():
        print(f"  {label}: {count / len(watch_df) * 100:.2f} %")

    print("=" * 60)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    print("Starting fact_watch_history.csv generation...\n")

    (users_df, profiles_df, content_df, devices_df,
     sessions_df, bridge_genre_df, genre_dim_df) = load_input_data()

    watch_df = generate_watch_history(
        users_df, profiles_df, content_df, devices_df,
        sessions_df, bridge_genre_df, genre_dim_df
    )

    validate_watch_history(
        watch_df, users_df, profiles_df, content_df, devices_df, sessions_df
    )

    watch_df.to_csv(OUTPUT_PATH, index=False)
    print(f"Saved dataset to: {OUTPUT_PATH}")

    print_summary_statistics(watch_df)

    print("\nfact_watch_history.csv generation completed successfully.")


if __name__ == "__main__":
    main()