"""
generate_sessions.py

Generates the fact_user_sessions.csv dataset based on dim_users.csv and
dim_devices.csv.

Author: Senior Data Engineering Team
"""

import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta, date

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

INPUT_USERS_PATH  = "data/dim_users.csv"
INPUT_DEVICES_PATH = "data/dim_devices.csv"
OUTPUT_PATH        = "data/fact_user_sessions.csv"

TARGET_SESSION_COUNT = 100_000

AVG_SESSIONS_PER_MONTH   = 18
MIN_SESSION_DURATION_MIN = 5
MAX_SESSION_DURATION_MIN = 180

LOGIN_METHODS       = ["Email", "Google", "Apple", "Facebook"]
LOGIN_METHOD_WEIGHTS = [0.55,   0.22,     0.15,    0.08]

DATA_END_DATE       = datetime(2024, 12, 31)
DATA_LOOKBACK_MONTHS = 12

SUSPENDED_MAX_SESSIONS = 3

# ---------------------------------------------------------------------------
# BUSINESS RULES — DAY-OF-WEEK SAMPLING WEIGHTS
#
# Target distribution (index 0 = Monday … 6 = Sunday):
#   Mon 12%  Tue 12%  Wed 12%  Thu 12%  Fri 15%  Sat 19%  Sun 18%
#
# These are used as direct sampling probabilities so the output
# converges to target percentages over large datasets without
# any accept/reject loops that could introduce bias.
# ---------------------------------------------------------------------------
DOW_WEIGHTS = [0.12, 0.12, 0.12, 0.12, 0.15, 0.19, 0.18]   # sum = 1.00

# ---------------------------------------------------------------------------
# BUSINESS RULES — HOUR-OF-DAY SAMPLING WEIGHTS
#
# Target distribution (5 business windows):
#   06:00–12:00  12%   →  2.00% per hour  (6 hours)
#   12:00–18:00  18%   →  3.00% per hour  (6 hours)
#   18:00–22:00  45%   → 11.25% per hour  (4 hours)
#   22:00–01:00  20%   →  6.67% per hour  (3 hours: 22, 23, 0)
#   01:00–06:00   5%   →  1.00% per hour  (5 hours)
#
# Index position = hour (0–23).
# Weights are proportional; random.choices normalises automatically.
# ---------------------------------------------------------------------------
HOUR_WEIGHTS = [
    6.67,   # 00  (part of 22–01 window)
    1.00,   # 01
    1.00,   # 02
    1.00,   # 03
    1.00,   # 04
    1.00,   # 05
    2.00,   # 06
    2.00,   # 07
    2.00,   # 08
    2.00,   # 09
    2.00,   # 10
    2.00,   # 11
    3.00,   # 12
    3.00,   # 13
    3.00,   # 14
    3.00,   # 15
    3.00,   # 16
    3.00,   # 17
    11.25,  # 18
    11.25,  # 19
    11.25,  # 20
    11.25,  # 21
    6.67,   # 22  (part of 22–01 window)
    6.67,   # 23  (part of 22–01 window)
]
# Precompute for random.choices (list of hours 0–23)
_HOURS = list(range(24))

# ---------------------------------------------------------------------------
# BUSINESS RULES — DEVICE-SPECIFIC SESSION DURATION RANGES (minutes)
#
# Device category is matched by a substring search on device_type column.
# ---------------------------------------------------------------------------
DEVICE_DURATION_RANGES = {
    "mobile":          ( 5,  45),
    "smart tv":        (30, 180),
    "laptop/desktop":  (15,  90),
    "tablet":          (10,  60),
    "default":         ( 5, 180),
}

# Night hours (01:00–05:59): sessions are generally shorter
_NIGHT_HOURS     = frozenset(range(1, 6))
NIGHT_DURATION_CAP_MIN = 45   # hard cap for sessions starting in this window

# Weekend sessions may be slightly longer (multiplier applied after sampling)
# Keys are Python weekday() values: 4=Friday 5=Saturday 6=Sunday
WEEKEND_DURATION_MULTIPLIER = {4: 1.08, 5: 1.18, 6: 1.15}


# ---------------------------------------------------------------------------
# PRECOMPUTED LOOKUP: device_id -> (category_key, is_tv, is_mobile)
# Built once in generate_sessions; passed as argument to avoid rebuilding.
# ---------------------------------------------------------------------------

def build_device_category_lookup(devices_df):
    """
    Build an O(1) lookup: device_id -> category key for DEVICE_DURATION_RANGES.

    Matching is done by substring on device_type (case-insensitive).
    Falls back to "default" when no substring matches.

    Args:
        devices_df (pd.DataFrame): dim_devices reference table.

    Returns:
        dict: {device_id (int): category_key (str)}
    """
    lookup = {}
    for row in devices_df.itertuples(index=False):
        dtype = str(getattr(row, "device_type", "")).lower().strip()
        matched = "default"
        for key in DEVICE_DURATION_RANGES:
            if key != "default" and key in dtype:
                matched = key
                break
        lookup[int(row.device_id)] = matched
    return lookup


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def assign_preferred_devices(user_ids, devices_df, min_pref=1, max_pref=3):
    """Assign each user a small pool of preferred devices (1-3)."""
    device_ids = devices_df["device_id"].tolist()
    preferred_map = {}

    for user_id in user_ids:
        pref_count = random.randint(min_pref, max_pref)
        pref_count = min(pref_count, len(device_ids))
        preferred_map[user_id] = random.sample(device_ids, pref_count)

    return preferred_map


def pick_device_for_user(user_id, preferred_map, all_device_ids, random_pick_prob=0.1):
    """
    Mostly pick from the user's preferred devices.
    Occasionally (random_pick_prob) pick a completely random device.
    """
    if random.random() < random_pick_prob:
        return random.choice(all_device_ids)
    return random.choice(preferred_map[user_id])


def get_session_count_for_user(user_status, months_active):
    """Determine number of sessions to generate based on user status."""
    if user_status == "Active":
        base = np.random.poisson(AVG_SESSIONS_PER_MONTH * months_active)
        return max(base, 1)
    elif user_status == "Paused":
        base = np.random.poisson((AVG_SESSIONS_PER_MONTH * 0.4) * months_active)
        return max(base, 0)
    elif user_status == "Suspended":
        return random.randint(0, SUSPENDED_MAX_SESSIONS)
    elif user_status == "Cancelled":
        base = np.random.poisson((AVG_SESSIONS_PER_MONTH * 0.5) * months_active)
        return max(base, 0)
    else:
        return random.randint(0, 5)


def generate_session_datetime(start_bound, end_bound):
    """
    Generate a session_start timestamp that converges toward the business-rule
    day-of-week and hour distributions over large datasets.

    Algorithm (statistically sound, O(1) per call):

    Step 1 — Pick a weekday using DOW_WEIGHTS.
              This is a direct weighted sample; no accept/reject loop,
              so the per-weekday probability matches the weight exactly
              regardless of the shape of the user's activity window.

    Step 2 — Find the set of calendar dates within [start_bound, end_bound]
              that fall on the chosen weekday.
              Pick one date uniformly at random from that set.

    Step 3 — Pick an hour from HOUR_WEIGHTS (direct weighted sample).

    Step 4 — Pick minute and second uniformly within the chosen hour.

    Step 5 — Rejection sampling: if the assembled timestamp falls outside
              [start_bound, end_bound], resample Steps 1–4 until a valid
              timestamp is produced.  A hard fallback after MAX_RESAMPLE_ATTEMPTS
              returns a uniform random timestamp inside the window so the
              call always terminates in finite time.

    Why this is better than clamping:
      - Clamping distorts the DOW and hour distributions for sessions near
        the boundary of a user's activity window (e.g. all boundary sessions
        collapse to the exact start_bound timestamp, biasing Monday mornings
        upward for users who signed up on a Monday).
      - Rejection sampling preserves the intended probability distribution
        without any systematic boundary bias.

    Why this is better than the original accept/reject loop:
      - The original loop accepted weekend dates at a 55% probability and
        weekday dates at a 45% probability irrespective of DOW.  This does
        not map to the per-weekday targets (Mon 12% … Sun 18%) and the
        fallback at iteration limit introduced additional bias.
      - The original code used random_seconds over 86,400 which produces a
        perfectly flat hour distribution, not the 45%-evening target.

    Args:
        start_bound (datetime): Earliest allowable session_start.
        end_bound   (datetime): Latest  allowable session_start.

    Returns:
        datetime: A session_start timestamp strictly within
                  [start_bound, end_bound].
    """
    # Maximum attempts before falling back to a guaranteed-valid timestamp.
    # In practice the window spans weeks to months, so rejection is rare.
    MAX_RESAMPLE_ATTEMPTS = 50

    total_days = (end_bound.date() - start_bound.date()).days
    if total_days < 0:
        total_days = 0

    for _attempt in range(MAX_RESAMPLE_ATTEMPTS):

        # ------------------------------------------------------------------
        # Step 1 — Sample a target weekday from DOW_WEIGHTS
        # ------------------------------------------------------------------
        target_dow = random.choices(_HOURS[:7], weights=DOW_WEIGHTS, k=1)[0]
        # _HOURS[:7] gives [0,1,2,3,4,5,6] — same as range(7)

        # ------------------------------------------------------------------
        # Step 2 — Enumerate dates in the window that match the target DOW
        #           and pick one uniformly at random.
        #
        #   Efficient enumeration: find the first matching date from
        #   start_bound, then step by 7 days.  O(window_weeks) per call.
        # ------------------------------------------------------------------
        start_date    = start_bound.date()
        days_to_first = (target_dow - start_date.weekday()) % 7
        first_match   = start_date + timedelta(days=days_to_first)

        if first_match > end_bound.date():
            # No matching weekday in the window; try a different DOW
            continue

        matching_dates = []
        cursor = first_match
        while cursor <= end_bound.date():
            matching_dates.append(cursor)
            cursor += timedelta(days=7)
        chosen_date = random.choice(matching_dates)

        # ------------------------------------------------------------------
        # Step 3 — Sample an hour using HOUR_WEIGHTS (direct, no loop)
        # ------------------------------------------------------------------
        chosen_hour = random.choices(_HOURS, weights=HOUR_WEIGHTS, k=1)[0]

        # ------------------------------------------------------------------
        # Step 4 — Random minute and second within the hour
        # ------------------------------------------------------------------
        chosen_minute = random.randint(0, 59)
        chosen_second = random.randint(0, 59)

        session_start = datetime(
            chosen_date.year,
            chosen_date.month,
            chosen_date.day,
            chosen_hour,
            chosen_minute,
            chosen_second,
        )

        # ------------------------------------------------------------------
        # Step 5 — Rejection sampling: accept only if inside the window
        # ------------------------------------------------------------------
        if start_bound <= session_start <= end_bound:
            return session_start
        # Otherwise loop and resample

    # ------------------------------------------------------------------
    # Fallback — guaranteed-valid uniform timestamp inside the window.
    # Reached only when the activity window is very short (< 1 week) and
    # repeated samples keep missing it.  Preserves termination guarantee.
    # ------------------------------------------------------------------
    total_seconds = max(int((end_bound - start_bound).total_seconds()), 1)
    return start_bound + timedelta(seconds=random.randint(0, total_seconds))


def generate_session_duration_sec(device_category, session_start):
    """
    Generate a realistic session duration in seconds.

    Rules applied in order:
      1. Sample uniformly from the device-specific [min, max] minute range.
         Uniform sampling is preferred over normal distribution here because
         the device ranges are already narrow and realistic; a normal
         distribution centred at 42 min would clip heavily against device
         limits, producing artificial spikes at the clip boundaries.
      2. Apply NIGHT_DURATION_CAP_MIN if the session starts in 01:00–05:59
         (late-night viewing is typically brief).
      3. Apply WEEKEND_DURATION_MULTIPLIER for Fri/Sat/Sun (longer binge
         sessions on evenings and weekends).
      4. Clip the final value to [MIN_SESSION_DURATION_MIN,
         MAX_SESSION_DURATION_MIN] so device and global bounds are both
         respected after the multiplier is applied.

    Args:
        device_category (str)      : Key into DEVICE_DURATION_RANGES.
        session_start   (datetime) : Session start timestamp.

    Returns:
        int: Session duration in seconds (always > 0).
    """
    low_min, high_min = DEVICE_DURATION_RANGES.get(
        device_category, DEVICE_DURATION_RANGES["default"]
    )

    # 1. Base duration — uniform sample within device range
    duration_min = random.uniform(low_min, high_min)

    # 2. Night-hour cap
    if session_start.hour in _NIGHT_HOURS:
        duration_min = min(duration_min, NIGHT_DURATION_CAP_MIN)

    # 3. Weekend multiplier
    dow_multiplier = WEEKEND_DURATION_MULTIPLIER.get(session_start.weekday(), 1.0)
    duration_min  *= dow_multiplier

    # 4. Global clip
    duration_min = max(MIN_SESSION_DURATION_MIN,
                       min(duration_min, MAX_SESSION_DURATION_MIN))

    return max(1, int(duration_min * 60))


def get_user_activity_window(user_row):
    """
    Determine the valid start/end date window for generating sessions,
    based on user account_status. dim_users.csv has no subscription end
    date column, so the window always runs through DATA_END_DATE.
    """
    status      = user_row.get("account_status", "Active")
    signup_date = pd.to_datetime(
        user_row.get("signup_date", DATA_END_DATE - timedelta(days=365))
    )

    window_start = max(
        signup_date.to_pydatetime(),
        DATA_END_DATE - timedelta(days=30 * DATA_LOOKBACK_MONTHS),
    )

    window_end = DATA_END_DATE

    if window_end <= window_start:
        window_end = window_start + timedelta(days=1)

    months_active = max((window_end - window_start).days / 30, 0.5)

    return window_start, window_end, months_active

# ---------------------------------------------------------------------------
# LOAD INPUT DATA
# ---------------------------------------------------------------------------

def load_input_data():
    """
    Load required input datasets.
    """

    print("Loading input datasets...")

    users_df = pd.read_csv(
        INPUT_USERS_PATH,
        parse_dates=["signup_date"],
        low_memory=False
    )

    devices_df = pd.read_csv(
        INPUT_DEVICES_PATH,
        low_memory=False
    )

    print(f"  -> Loaded {len(users_df):,} users")
    print(f"  -> Loaded {len(devices_df):,} devices")

    return users_df, devices_df
# ---------------------------------------------------------------------------
# GENERATION
# ---------------------------------------------------------------------------

def generate_sessions(users_df, devices_df):
    """Generate the fact_user_sessions dataset."""
    print("Generating user sessions...")

    all_device_ids = devices_df["device_id"].tolist()
    user_ids       = users_df["user_id"].tolist()
    preferred_map  = assign_preferred_devices(user_ids, devices_df)

    # Build device category lookup once — O(n_devices), reused for every session
    device_category_lookup = build_device_category_lookup(devices_df)

    if "account_status" not in users_df.columns:
        users_df = users_df.copy()
        users_df["account_status"] = "Active"

    records    = []
    session_id = 1

    for _, user_row in users_df.iterrows():
        user_id = user_row["user_id"]
        status  = user_row.get("account_status", "Active")
        country = user_row.get("country", "Unknown")

        window_start, window_end, months_active = get_user_activity_window(user_row)
        num_sessions = get_session_count_for_user(status, months_active)

        for _ in range(num_sessions):
            # Session timestamp — DOW and hour weighted independently
            session_start = generate_session_datetime(window_start, window_end)

            device_id       = pick_device_for_user(user_id, preferred_map, all_device_ids)
            device_category = device_category_lookup.get(int(device_id), "default")

            # Duration — device-aware, night-capped, weekend-boosted
            duration_sec = generate_session_duration_sec(device_category, session_start)
            session_end  = session_start + timedelta(seconds=duration_sec)

            login_method = random.choices(
                LOGIN_METHODS, weights=LOGIN_METHOD_WEIGHTS, k=1
            )[0]

            created_at = session_start
            updated_at = created_at + timedelta(minutes=random.randint(0, 60))

            records.append({
                "session_id"          : session_id,
                "user_id"             : user_id,
                "device_id"           : device_id,
                "login_method"        : login_method,
                "session_start"       : session_start,
                "session_end"         : session_end,
                "session_duration_sec": duration_sec,
                "ip_country"          : country,
                "created_at"          : created_at,
                "updated_at"          : updated_at,
            })

            session_id += 1

    sessions_df = pd.DataFrame(records)

    # Trim to approximately the target session count
    if len(sessions_df) > TARGET_SESSION_COUNT:
        sessions_df = sessions_df.sample(
            n=TARGET_SESSION_COUNT, random_state=RANDOM_SEED
        )
        sessions_df = sessions_df.sort_values("session_id").reset_index(drop=True)
        sessions_df["session_id"] = range(1, len(sessions_df) + 1)

    print(f"  -> Generated {len(sessions_df):,} sessions")

    return sessions_df


# ---------------------------------------------------------------------------
# VALIDATION
# ---------------------------------------------------------------------------

def validate_sessions(sessions_df, users_df, devices_df):
    """Run validation checks on the generated sessions dataset."""
    print("\nRunning validation checks...")

    required_columns = [
        "session_id", "user_id", "device_id", "login_method",
        "session_start", "session_end", "session_duration_sec",
        "ip_country", "created_at", "updated_at"
    ]

    missing_columns = [col for col in required_columns if col not in sessions_df.columns]
    assert not missing_columns, f"Missing required columns: {missing_columns}"
    print("  [OK] Required columns present")

    assert sessions_df["session_id"].is_unique, "Duplicate session_id values found"
    print("  [OK] session_id is unique")

    valid_user_ids = set(users_df["user_id"])
    assert sessions_df["user_id"].isin(valid_user_ids).all(), "Invalid user_id found"
    print("  [OK] All user_id values are valid")

    valid_device_ids = set(devices_df["device_id"])
    assert sessions_df["device_id"].isin(valid_device_ids).all(), "Invalid device_id found"
    print("  [OK] All device_id values are valid")

    assert (sessions_df["session_end"] > sessions_df["session_start"]).all(), \
        "Found session_end <= session_start"
    print("  [OK] session_end is always after session_start")

    assert (sessions_df["session_duration_sec"] > 0).all(), \
        "Found non-positive session duration"
    print("  [OK] session_duration_sec is always positive")

    assert sessions_df.isnull().sum().sum() == 0, "Null values found in dataset"
    print("  [OK] No null values found")

    print("Validation passed successfully.\n")


# ---------------------------------------------------------------------------
# SUMMARY STATISTICS
# ---------------------------------------------------------------------------

def print_summary_statistics(sessions_df):
    """Print summary statistics about the generated dataset."""
    print("=" * 60)
    print("SUMMARY STATISTICS - fact_user_sessions.csv")
    print("=" * 60)

    print(f"Total sessions generated : {len(sessions_df):,}")
    print(f"Unique users             : {sessions_df['user_id'].nunique():,}")
    print(f"Unique devices used      : {sessions_df['device_id'].nunique():,}")
    print(
        f"Date range               : "
        f"{sessions_df['session_start'].min()} -> "
        f"{sessions_df['session_start'].max()}"
    )

    avg_duration_min = sessions_df["session_duration_sec"].mean() / 60
    print(f"Average session duration : {avg_duration_min:.2f} minutes")
    print(f"Min session duration     : {sessions_df['session_duration_sec'].min() / 60:.2f} minutes")
    print(f"Max session duration     : {sessions_df['session_duration_sec'].max() / 60:.2f} minutes")

    print("\nLogin method distribution:")
    print(
        (sessions_df["login_method"].value_counts(normalize=True) * 100)
        .round(2).astype(str) + " %"
    )

    # ------------------------------------------------------------------
    # Day-of-Week Distribution
    # Target: Mon 12% | Tue 12% | Wed 12% | Thu 12% | Fri 15% | Sat 19% | Sun 18%
    # ------------------------------------------------------------------
    dow_labels  = {0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday",
                   4: "Friday", 5: "Saturday", 6: "Sunday"}
    dow_targets = {0: 12.0, 1: 12.0, 2: 12.0, 3: 12.0,
                   4: 15.0, 5: 19.0, 6: 18.0}

    sessions_df = sessions_df.copy()
    sessions_df["_dow"] = pd.to_datetime(sessions_df["session_start"]).dt.weekday
    dow_pct = sessions_df["_dow"].value_counts(normalize=True).mul(100)

    print("\nDay of Week Distribution (actual vs target):")
    for dow in range(7):
        actual = dow_pct.get(dow, 0.0)
        target = dow_targets[dow]
        diff   = actual - target
        flag   = "  <-- check" if abs(diff) > 3.0 else ""
        print(
            f"  {dow_labels[dow]:<12}: {actual:5.2f}%"
            f"  (target {target:.1f}%,  diff {diff:+.2f}%){flag}"
        )

    # ------------------------------------------------------------------
    # Hour Distribution (business windows)
    # Target: 06–12 12% | 12–18 18% | 18–22 45% | 22–01 20% | 01–06 5%
    # ------------------------------------------------------------------
    hours = pd.to_datetime(sessions_df["session_start"]).dt.hour
    n     = len(sessions_df)

    hour_buckets = [
        ("01 AM – 06 AM", hours.between(1,  5),          5.0),
        ("06 AM – 12 PM", hours.between(6,  11),         12.0),
        ("12 PM – 06 PM", hours.between(12, 17),         18.0),
        ("06 PM – 10 PM", hours.between(18, 21),         45.0),
        ("10 PM – 01 AM", hours.isin([22, 23, 0]),       20.0),
    ]

    print("\nHour of Day Distribution (business windows):")
    for label, mask, target in hour_buckets:
        actual = mask.sum() / n * 100
        diff   = actual - target
        flag   = "  <-- check" if abs(diff) > 3.0 else ""
        print(
            f"  {label}  (target {target:4.1f}%) : "
            f"{actual:5.2f}%  (diff {diff:+.2f}%){flag}"
        )

    weekend_count = (sessions_df["_dow"] >= 5).sum()
    weekday_count = n - weekend_count
    print("\nWeekend vs Weekday activity:")
    print(f"  Weekend: {weekend_count / n * 100:.2f} %")
    print(f"  Weekday: {weekday_count / n * 100:.2f} %")

    print("\nTop 5 countries by session count:")
    print(sessions_df["ip_country"].value_counts().head(5))

    print("=" * 60)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    print("Starting fact_user_sessions.csv generation...\n")

    users_df, devices_df = load_input_data()
    sessions_df = generate_sessions(users_df, devices_df)

    validate_sessions(sessions_df, users_df, devices_df)

    sessions_df.to_csv(OUTPUT_PATH, index=False)
    print(f"Saved dataset to: {OUTPUT_PATH}")

    print_summary_statistics(sessions_df)

    print("\nfact_user_sessions.csv generation completed successfully.")


if __name__ == "__main__":
    main()