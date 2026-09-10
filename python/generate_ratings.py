"""
generate_ratings.py

Generates the fact_ratings.csv dataset based on dim_users.csv,
dim_profiles.csv, dim_content.csv and fact_watch_history.csv.

NOTE (Principal Data Engineer review):
fact_watch_history.csv is now produced by the improved, finalized
generate_watch_history.py generator and carries realistic watch_status,
watch_duration_min, percentage_completed, viewing-hour, and weekend
behaviour. This generator no longer samples a fixed quota of "rating-active"
users up front -- instead, whether a watch event gets rated is now driven
directly by that event's own watch_status and watch_duration_min, so rating
volume and rating values emerge naturally from real viewing behaviour
instead of an artificial per-user sampling target.

Author: Senior Data Engineering Team
"""

import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
from faker import Faker

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

fake = Faker()
Faker.seed(RANDOM_SEED)

INPUT_USERS_PATH = "data/dim_users.csv"
INPUT_PROFILES_PATH = "data/dim_profiles.csv"
INPUT_CONTENT_PATH = "data/dim_content.csv"
INPUT_WATCH_HISTORY_PATH = "data/fact_watch_history.csv"

OUTPUT_PATH = "data/fact_ratings.csv"

# Safety cap only -- ratings are never padded up to this number, it simply
# bounds the dataset from above if the probability model over-produces.
TARGET_RATING_COUNT = 60_000

RATING_VALUES = [5, 4, 3, 2, 1]
RATING_WEIGHTS = [0.30, 0.35, 0.20, 0.10, 0.05]

REVIEW_TEXT_RATIO = 0.20

REVIEW_SNIPPETS_BY_RATING = {
    5: ["loved", "amazing", "fantastic", "brilliant", "must watch"],
    4: ["really enjoyed", "solid", "great", "well made", "worth it"],
    3: ["decent", "okay", "average", "watchable", "so so"],
    2: ["disappointing", "not great", "below average", "weak", "meh"],
    1: ["terrible", "waste of time", "boring", "poorly made", "avoid"],
}

# ---------------------------------------------------------------------------
# RATING PROBABILITY MODEL
#
# Whether a watch event ends up with a rating is driven by:
#   1. watch_status (primary driver) -- higher completion => higher
#      probability of rating.
#   2. watch_duration_min (secondary driver) -- a mild engagement boost on
#      top of the status-driven base probability, since longer viewing
#      generally signals higher engagement regardless of status.
#
# These base rates are tuned so that, applied across ~300,000 watch events
# with the WATCH_STATUS_WEIGHTS distribution used by generate_watch_history.py
# (Completed 50% / Started 20% / Paused 18% / Abandoned 12%), the resulting
# rating volume naturally lands in the ~18,000-22,000 range without being
# forced there directly.
# ---------------------------------------------------------------------------
RATING_BASE_PROBABILITY_BY_STATUS = {
    "Completed": 0.10,
    "Paused": 0.045,
    "Started": 0.018,
    "Abandoned": 0.010,
}

# Engagement boost from watch_duration_min: probability is multiplied by
# (1 + min(watch_duration_min / NORMALIZER, MAX_BOOST)), so longer viewing
# sessions increase rating likelihood up to a capped ceiling.
ENGAGEMENT_DURATION_NORMALIZER = 120.0
ENGAGEMENT_DURATION_MAX_BOOST = 0.40

RATING_PROBABILITY_CAP = 0.85

# ---------------------------------------------------------------------------
# RATING VALUE DISTRIBUTION BY WATCH STATUS
#
# Weighted probability distributions (never hardcoded exact values) over
# RATING_VALUES = [5, 4, 3, 2, 1], correlated with engagement level:
#   Completed  -> mostly 4-5 stars
#   Paused     -> mostly 3-4 stars
#   Started    -> mostly 2-4 stars
#   Abandoned  -> mostly 1-3 stars
# ---------------------------------------------------------------------------
RATING_WEIGHTS_BY_STATUS = {
    "Completed": [0.55, 0.33, 0.09, 0.02, 0.01],
    "Paused":    [0.15, 0.40, 0.32, 0.10, 0.03],
    "Started":   [0.08, 0.27, 0.33, 0.22, 0.10],
    "Abandoned": [0.03, 0.10, 0.32, 0.33, 0.22],
}


# ---------------------------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------------------------

def load_input_data():
    """Load all required dimension and fact tables."""
    print("Loading input tables...")

    users_df = pd.read_csv(INPUT_USERS_PATH)
    profiles_df = pd.read_csv(INPUT_PROFILES_PATH)
    content_df = pd.read_csv(INPUT_CONTENT_PATH)
    watch_history_df = pd.read_csv(
        INPUT_WATCH_HISTORY_PATH,
        parse_dates=["watch_date", "watch_start_time"]
    )

    print(f"  -> Loaded {len(users_df):,} users")
    print(f"  -> Loaded {len(profiles_df):,} profiles")
    print(f"  -> Loaded {len(content_df):,} content items")
    print(f"  -> Loaded {len(watch_history_df):,} watch history records")

    return users_df, profiles_df, content_df, watch_history_df


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def pick_rating_value(watch_status):
    """
    Pick a rating value using a weighted probability distribution that
    correlates with engagement level (watch_status). Highly engaged
    viewers (Completed) skew toward 4-5 stars, while low-engagement
    viewers (Abandoned) skew toward 1-3 stars. Falls back to the default
    RATING_WEIGHTS distribution for any unrecognised status.
    """
    weights = RATING_WEIGHTS_BY_STATUS.get(watch_status, RATING_WEIGHTS)
    return random.choices(RATING_VALUES, weights=weights, k=1)[0]


def generate_review_text(rating_value):
    """Generate a short realistic review text using Faker, biased by rating."""
    snippet = random.choice(REVIEW_SNIPPETS_BY_RATING.get(rating_value, ["okay"]))
    sentence = fake.sentence(nb_words=8)
    review = f"{snippet.capitalize()} - {sentence}"
    return review


def generate_rating_datetime(watch_start_time):
    """
    Generate a rating_date and created_at timestamp that always occurs on
    or after the watch_start_time of the underlying watch event (business
    rule: rating_timestamp >= watch_start_time). A random delay -- skewed
    toward a few days via an exponential distribution and capped at 30
    days -- models how long viewers typically wait before rating something.
    """
    days_after = int(np.random.exponential(scale=3))
    days_after = min(days_after, 30)
    extra_seconds = random.randint(0, 86_399)

    created_at = watch_start_time + timedelta(days=days_after, seconds=extra_seconds)
    rating_date = created_at.date()

    return rating_date, created_at


# ---------------------------------------------------------------------------
# GENERATION
# ---------------------------------------------------------------------------

def generate_ratings(users_df, profiles_df, content_df, watch_history_df):
    """Generate the fact_ratings dataset."""
    print("Generating ratings...")

    valid_user_ids = set(users_df["user_id"])
    valid_content_ids = set(content_df["content_id"])
    profile_owner_lookup = profiles_df.set_index("profile_id")["user_id"].to_dict()

    watch_history_df = watch_history_df[
        watch_history_df["user_id"].isin(valid_user_ids) &
        watch_history_df["content_id"].isin(valid_content_ids)
    ].copy()

    # Only one rating allowed per (profile_id, content_id) -> reduce watch
    # history down to a single representative watch event per profile/content
    # pair (the earliest watch of that content by that profile). A profile
    # can only rate a given piece of content once, regardless of rewatches.
    watch_history_df = watch_history_df.sort_values("watch_start_time")
    candidate_df = watch_history_df.drop_duplicates(
        subset=["profile_id", "content_id"], keep="first"
    ).copy()

    print(f"  -> {len(candidate_df):,} unique profile-content watch events eligible for rating")

    # ------------------------------------------------------------------
    # Rating probability model: driven by watch_status (primary) and
    # watch_duration_min (secondary engagement boost), computed vectorized
    # for efficiency across the full candidate pool.
    # ------------------------------------------------------------------
    base_prob = candidate_df["watch_status"].map(RATING_BASE_PROBABILITY_BY_STATUS)
    base_prob = base_prob.fillna(RATING_BASE_PROBABILITY_BY_STATUS["Started"])

    duration_factor = 1.0 + np.minimum(
        candidate_df["watch_duration_min"] / ENGAGEMENT_DURATION_NORMALIZER,
        ENGAGEMENT_DURATION_MAX_BOOST
    )

    rating_probability = (base_prob * duration_factor).clip(upper=RATING_PROBABILITY_CAP)

    random_draws = np.random.random(len(candidate_df))
    rated_mask = random_draws < rating_probability.to_numpy()

    rating_candidates_df = candidate_df.loc[rated_mask].reset_index(drop=True)

    print(f"  -> {len(rating_candidates_df):,} candidate watch records selected for rating")

    # Safety cap -- trims down only if the probability model happens to
    # over-produce; never pads the dataset up to this number.
    if len(rating_candidates_df) > TARGET_RATING_COUNT:
        rating_candidates_df = rating_candidates_df.sample(
            n=TARGET_RATING_COUNT, random_state=RANDOM_SEED
        ).reset_index(drop=True)

    records = []
    rating_id = 1

    for row in rating_candidates_df.itertuples(index=False):
        user_id = row.user_id
        profile_id = row.profile_id
        content_id = row.content_id
        watch_status = row.watch_status
        watch_start_time = row.watch_start_time

        # Safety check: profile must belong to the same user
        if profile_owner_lookup.get(profile_id) != user_id:
            continue

        rating_value = pick_rating_value(watch_status)

        has_review = random.random() < REVIEW_TEXT_RATIO
        review_text = generate_review_text(rating_value) if has_review else None

        rating_date, created_at = generate_rating_datetime(watch_start_time)
        updated_at = created_at + timedelta(minutes=random.randint(0, 120))

        records.append({
            "rating_id": rating_id,
            "user_id": user_id,
            "profile_id": profile_id,
            "content_id": content_id,
            "rating_value": rating_value,
            "review_text": review_text,
            "rating_date": rating_date,
            "created_at": created_at,
            "updated_at": updated_at,
        })

        rating_id += 1

    ratings_df = pd.DataFrame(records)

    print(f"  -> Generated {len(ratings_df):,} ratings")

    return ratings_df


# ---------------------------------------------------------------------------
# VALIDATION
# ---------------------------------------------------------------------------

def validate_ratings(ratings_df, users_df, profiles_df, content_df, watch_history_df):
    """Run validation checks on the generated ratings dataset."""
    print("\nRunning validation checks...")

    required_columns = [
        "rating_id", "user_id", "profile_id", "content_id", "rating_value",
        "review_text", "rating_date", "created_at", "updated_at"
    ]

    missing_columns = [col for col in required_columns if col not in ratings_df.columns]
    assert not missing_columns, f"Missing required columns: {missing_columns}"
    print("  [OK] Required columns present")

    assert ratings_df["rating_id"].is_unique, "Duplicate rating_id values found"
    print("  [OK] rating_id is unique")

    assert ratings_df["user_id"].isin(set(users_df["user_id"])).all(), "Invalid user_id found"
    print("  [OK] All user_id values are valid")

    assert ratings_df["profile_id"].isin(set(profiles_df["profile_id"])).all(), "Invalid profile_id found"
    print("  [OK] All profile_id values are valid")

    assert ratings_df["content_id"].isin(set(content_df["content_id"])).all(), "Invalid content_id found"
    print("  [OK] All content_id values are valid")

    profile_owner_lookup = profiles_df.set_index("profile_id")["user_id"].to_dict()
    profile_owner_check = ratings_df["profile_id"].map(profile_owner_lookup)
    assert (ratings_df["user_id"] == profile_owner_check).all(), \
        "Found rating where profile does not belong to the linked user"
    print("  [OK] Profile ownership matches user_id on every record")

    dup_check = ratings_df.duplicated(subset=["profile_id", "content_id"]).sum()
    assert dup_check == 0, f"Found {dup_check} duplicate (profile_id, content_id) ratings"
    print("  [OK] No duplicate (profile_id, content_id) ratings")

    assert ratings_df["rating_value"].between(1, 5).all(), "Found rating_value outside 1-5 range"
    print("  [OK] rating_value is always between 1 and 5")

    # Required columns not null (review_text is allowed to be null by design)
    non_nullable_cols = [c for c in required_columns if c != "review_text"]
    assert ratings_df[non_nullable_cols].isnull().sum().sum() == 0, \
        "Null values found in non-nullable columns"
    print("  [OK] No null values in required (non-nullable) columns")

    watch_date_lookup = watch_history_df.groupby(
        ["profile_id", "content_id"]
    )["watch_date"].min().to_dict()

    ratings_df["_watch_date_check"] = ratings_df.apply(
        lambda r: watch_date_lookup.get((r["profile_id"], r["content_id"])), axis=1
    )
    rating_dates = pd.to_datetime(ratings_df["rating_date"])
    watch_dates = pd.to_datetime(ratings_df["_watch_date_check"])
    assert (rating_dates >= watch_dates).all(), "Found rating_date earlier than watch_date"
    ratings_df.drop(columns=["_watch_date_check"], inplace=True)
    print("  [OK] rating_date is always on or after watch_date")

    print("Validation passed successfully.\n")


# ---------------------------------------------------------------------------
# SUMMARY STATISTICS
# ---------------------------------------------------------------------------

def print_summary_statistics(ratings_df):
    """Print summary statistics about the generated dataset."""
    print("=" * 60)
    print("SUMMARY STATISTICS - fact_ratings.csv")
    print("=" * 60)

    print(f"Total ratings generated   : {len(ratings_df):,}")
    print(f"Unique rating users       : {ratings_df['user_id'].nunique():,}")
    print(f"Unique profiles           : {ratings_df['profile_id'].nunique():,}")
    print(f"Unique content rated      : {ratings_df['content_id'].nunique():,}")

    print("\nRating value distribution:")
    print((ratings_df["rating_value"].value_counts(normalize=True) * 100).round(2).sort_index(ascending=False).astype(str) + " %")

    avg_rating = ratings_df["rating_value"].mean()
    print(f"\nAverage rating value      : {avg_rating:.2f}")

    reviews_present = ratings_df["review_text"].notna().sum()
    review_ratio = (reviews_present / len(ratings_df)) * 100
    print(f"Ratings with review_text  : {reviews_present:,} ({review_ratio:.2f} %)")

    avg_ratings_per_user = ratings_df.groupby("user_id").size().mean()
    print(f"Average ratings per user  : {avg_ratings_per_user:.2f}")

    print(f"Date range                : {ratings_df['rating_date'].min()} -> {ratings_df['rating_date'].max()}")

    print("=" * 60)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    print("Starting fact_ratings.csv generation...\n")

    users_df, profiles_df, content_df, watch_history_df = load_input_data()

    ratings_df = generate_ratings(users_df, profiles_df, content_df, watch_history_df)

    validate_ratings(ratings_df, users_df, profiles_df, content_df, watch_history_df)

    ratings_df.to_csv(OUTPUT_PATH, index=False)
    print(f"Saved dataset to: {OUTPUT_PATH}")

    print_summary_statistics(ratings_df)

    print("\nfact_ratings.csv generation completed successfully.")


if __name__ == "__main__":
    main()