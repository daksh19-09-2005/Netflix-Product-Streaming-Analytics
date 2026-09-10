"""
generate_subscriptions.py

Generates the fact_subscriptions.csv dataset for the Netflix Product Analytics project.

Depends on:
    data/dim_users.csv                →  valid user_id, signup_date, account_status
    data/dim_subscription_plans.csv   →  valid plan_id values

Schema (fact_subscriptions):
    subscription_id       INTEGER      (PK)
    user_id               INTEGER      (FK → dim_users)
    plan_id               INTEGER      (FK → dim_subscription_plans)
    start_date            DATE
    end_date              DATE         (NULL for Active subscriptions)
    renewal_date          DATE
    trial_user            BOOLEAN
    status                VARCHAR(20)
    auto_renew            BOOLEAN
    subscription_source   VARCHAR(30)
    cancellation_reason   VARCHAR(150) (NULL for non-Cancelled subscriptions)
    created_at            TIMESTAMP
    updated_at            TIMESTAMP
"""

import os
import random
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, date


# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------

OUTPUT_DIR     = "data"
OUTPUT_FILE    = "fact_subscriptions.csv"
USERS_FILE     = os.path.join("data", "dim_users.csv")
PLANS_FILE     = os.path.join("data", "dim_subscription_plans.csv")

RANDOM_SEED    = 42

random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

# Reference date for end_date / renewal_date calculations
TODAY = datetime.today().date()


# ------------------------------------------------------------------
# Business Rule Configuration
# ------------------------------------------------------------------

# Plan distribution mapped by plan_name → weight
PLAN_DISTRIBUTION = {
    "Basic"    : 0.30,
    "Standard" : 0.45,
    "Premium"  : 0.25,
}

SUBSCRIPTION_SOURCE_DISTRIBUTION = {
    "Android"  : 0.32,
    "iOS"      : 0.26,
    "Website"  : 0.25,
    "Smart TV" : 0.10,
    "Partner"  : 0.07,
}

# Subscription status distribution (aligned with account_status in dim_users)
STATUS_DISTRIBUTION = {
    "Active"   : 0.78,
    "Cancelled": 0.14,
    "Suspended": 0.03,
    "Paused"   : 0.05,
}

TRIAL_USER_RATE = 0.12
AUTO_RENEW_RATE = 0.80

# Realistic cancellation reasons for cancelled subscriptions
CANCELLATION_REASONS = [
    "Too expensive",
    "Not enough content",
    "Found a better alternative",
    "Temporary financial reasons",
    "Technical issues",
    "No longer using the service",
    "Content not relevant",
    "Switched to a different plan",
    "Poor streaming quality",
    "Account security concern",
]

# Account status → subscription status alignment map
# Ensures subscription status reflects the parent user's account state
ACCOUNT_TO_SUBSCRIPTION_STATUS = {
    "Active"   : "Active",
    "Cancelled": "Cancelled",
    "Suspended": "Suspended",
    "Paused"   : "Paused",
}


# ------------------------------------------------------------------
# Helper Functions
# ------------------------------------------------------------------

def load_csv(filepath: str, parse_dates: list = None) -> pd.DataFrame:
    """
    Load a CSV file and return a DataFrame.

    Args:
        filepath (str): Path to the CSV file.
        parse_dates (list): Optional list of columns to parse as dates.

    Returns:
        pd.DataFrame: Loaded DataFrame.

    Raises:
        FileNotFoundError: If the file does not exist at the given path.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(
            f"Dependency missing: '{filepath}' not found. "
            "Ensure all upstream generators have been run."
        )
    df = pd.read_csv(filepath, parse_dates=parse_dates)
    print(f"Loaded {len(df):,} records from '{filepath}'.")
    return df


def weighted_choice(distribution: dict) -> str:
    """
    Draw a single weighted random choice from a distribution dictionary.

    Args:
        distribution (dict): Keys are labels, values are probabilities.

    Returns:
        str: Randomly selected category label.
    """
    categories = list(distribution.keys())
    weights    = list(distribution.values())
    return random.choices(categories, weights=weights, k=1)[0]


def build_plan_id_map(plans_df: pd.DataFrame) -> dict:
    """
    Build a mapping from plan_name to plan_id using dim_subscription_plans.

    Args:
        plans_df (pd.DataFrame): Loaded subscription plans DataFrame.

    Returns:
        dict: {plan_name: plan_id}
    """
    return dict(zip(plans_df["plan_name"], plans_df["plan_id"].astype(int)))


def select_plan_id(plan_id_map: dict) -> int:
    """
    Select a plan_id based on the business rule plan distribution.

    Args:
        plan_id_map (dict): Mapping of plan_name → plan_id.

    Returns:
        int: Selected plan_id.
    """
    plan_name = weighted_choice(PLAN_DISTRIBUTION)
    return plan_id_map[plan_name]


def generate_start_date(signup_date: date) -> date:
    """
    Generate a subscription start_date on or after the user's signup_date.

    Most users subscribe within the first 7 days of signup.

    Args:
        signup_date (date): The user's account signup date.

    Returns:
        date: Subscription start date.
    """
    # 80% subscribe on the same day or within 7 days of signup
    # 20% take up to 30 days to subscribe
    if random.random() < 0.80:
        offset_days = random.randint(0, 7)
    else:
        offset_days = random.randint(8, 30)

    start_date = signup_date + timedelta(days=offset_days)

    # Ensure start_date does not exceed today
    return min(start_date, TODAY)


def generate_end_date(
    status: str,
    start_date: date,
    is_trial: bool,
) -> date | None:
    """
    Generate the subscription end_date based on status and trial flag.

    Rules:
        - Active subscriptions → end_date = None
        - Cancelled/Suspended/Paused → end_date set to a past or near date
        - Trial users → end_date closer to start (trial window)

    Args:
        status (str): Subscription status.
        start_date (date): Subscription start date.
        is_trial (bool): Whether the user is a trial user.

    Returns:
        date | None: End date or None for active subscriptions.
    """
    if status == "Active":
        return None

    if is_trial:
        # Trial users who cancelled/paused do so within the trial window
        end_offset = random.randint(7, 30)
    else:
        # Regular users cancel/pause after at least 1 billing cycle (30+ days)
        end_offset = random.randint(30, 540)

    end_date = start_date + timedelta(days=end_offset)

    # Ensure end_date does not exceed today
    return min(end_date, TODAY)


def generate_renewal_date(start_date: date, status: str) -> date:
    """
    Generate a renewal_date that is always after the start_date.

    Active subscriptions renew in the future.
    Inactive subscriptions may have a past renewal date that was not acted on.

    Args:
        start_date (date): Subscription start date.
        status (str): Subscription status.

    Returns:
        date: Renewal date (always > start_date).
    """
    if status == "Active":
        # Renews 30 days from now (next billing cycle)
        days_offset  = random.randint(1, 30)
        renewal_date = TODAY + timedelta(days=days_offset)
    else:
        # Past renewal that was not completed → between start and today
        days_offset  = random.randint(30, 365)
        renewal_date = start_date + timedelta(days=days_offset)
        renewal_date = min(renewal_date, TODAY)

    # Guarantee renewal_date > start_date
    if renewal_date <= start_date:
        renewal_date = start_date + timedelta(days=30)

    return renewal_date


def generate_created_at(start_date: date) -> datetime:
    """
    Generate a realistic created_at timestamp on the subscription start_date.

    Args:
        start_date (date): Subscription start date.

    Returns:
        datetime: Timestamp on start_date with a random time.
    """
    return datetime(
        start_date.year,
        start_date.month,
        start_date.day,
        random.randint(0, 23),
        random.randint(0, 59),
        random.randint(0, 59),
    )


def generate_updated_at(created_at: datetime) -> datetime:
    """
    Generate an updated_at timestamp that is always >= created_at.

    Args:
        created_at (datetime): Subscription creation timestamp.

    Returns:
        datetime: Timestamp equal to or later than created_at.
    """
    days_offset   = random.randint(0, 365)
    hour_offset   = random.randint(0, 23)
    minute_offset = random.randint(0, 59)

    updated_at = created_at + timedelta(
        days=days_offset,
        hours=hour_offset,
        minutes=minute_offset,
    )

    now = datetime.now()

    # Clamp to now, but never let it fall below created_at
    return max(created_at, min(updated_at, now))


# ------------------------------------------------------------------
# Data Generation Function
# ------------------------------------------------------------------

def generate_subscriptions(
    users_df: pd.DataFrame,
    plans_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Generate the full fact_subscriptions dataset following all business rules.

    One subscription is created per user. Subscription status is aligned
    with the user's account_status to maintain referential consistency.

    Args:
        users_df (pd.DataFrame): Loaded dim_users DataFrame.
        plans_df (pd.DataFrame): Loaded dim_subscription_plans DataFrame.

    Returns:
        pd.DataFrame: DataFrame matching the fact_subscriptions PostgreSQL schema.
    """
    print(f"Generating subscriptions for {len(users_df):,} users...")

    plan_id_map     = build_plan_id_map(plans_df)
    records         = []
    subscription_id = 1

    for _, user in users_df.iterrows():
        user_id        = int(user["user_id"])
        account_status = str(user["account_status"])
        signup_date    = pd.to_datetime(user["signup_date"]).date()

        # ------------------------------------------------------------------
        # Align subscription status with account_status
        # ------------------------------------------------------------------
        status = ACCOUNT_TO_SUBSCRIPTION_STATUS.get(account_status, "Active")

        # ------------------------------------------------------------------
        # Plan selection (weighted by business rule distribution)
        # ------------------------------------------------------------------
        plan_id = select_plan_id(plan_id_map)

        # ------------------------------------------------------------------
        # Trial and auto-renew flags
        # ------------------------------------------------------------------
        is_trial   = random.random() < TRIAL_USER_RATE
        auto_renew = random.random() < AUTO_RENEW_RATE

        # Cancelled subscriptions rarely have auto-renew still enabled
        if status == "Cancelled":
            auto_renew = random.random() < 0.10

        # ------------------------------------------------------------------
        # Subscription source
        # ------------------------------------------------------------------
        subscription_source = weighted_choice(SUBSCRIPTION_SOURCE_DISTRIBUTION)

        # ------------------------------------------------------------------
        # Dates
        # ------------------------------------------------------------------
        start_date   = generate_start_date(signup_date)
        end_date     = generate_end_date(status, start_date, is_trial)
        renewal_date = generate_renewal_date(start_date, status)

        # ------------------------------------------------------------------
        # Cancellation reason (only for Cancelled subscriptions)
        # ------------------------------------------------------------------
        cancellation_reason = (
            random.choice(CANCELLATION_REASONS)
            if status == "Cancelled"
            else None
        )

        # ------------------------------------------------------------------
        # Timestamps
        # ------------------------------------------------------------------
        created_at = generate_created_at(start_date)
        updated_at = generate_updated_at(created_at)

        records.append({
            "subscription_id"     : subscription_id,
            "user_id"             : user_id,
            "plan_id"             : plan_id,
            "start_date"          : start_date,
            "end_date"            : end_date,
            "renewal_date"        : renewal_date,
            "trial_user"          : is_trial,
            "status"              : status,
            "auto_renew"          : auto_renew,
            "subscription_source" : subscription_source,
            "cancellation_reason" : cancellation_reason,
            "created_at"          : created_at,
            "updated_at"          : updated_at,
        })

        subscription_id += 1

    df = pd.DataFrame(records)

    # Enforce correct data types to match PostgreSQL schema
    df["subscription_id"]     = df["subscription_id"].astype(int)
    df["user_id"]             = df["user_id"].astype(int)
    df["plan_id"]             = df["plan_id"].astype(int)
    df["start_date"]          = pd.to_datetime(df["start_date"]).dt.date
    df["end_date"]            = pd.to_datetime(df["end_date"], errors="coerce").dt.date
    df["renewal_date"]        = pd.to_datetime(df["renewal_date"]).dt.date
    df["trial_user"]          = df["trial_user"].astype(bool)
    df["status"]              = df["status"].astype(str)
    df["auto_renew"]          = df["auto_renew"].astype(bool)
    df["subscription_source"] = df["subscription_source"].astype(str)
    df["created_at"]          = pd.to_datetime(df["created_at"])
    df["updated_at"]          = pd.to_datetime(df["updated_at"])

    return df


# ------------------------------------------------------------------
# Validation Function
# ------------------------------------------------------------------

def validate_subscriptions_dataframe(
    df: pd.DataFrame,
    users_df: pd.DataFrame,
    plans_df: pd.DataFrame,
) -> None:
    """
    Run validation checks on the fact_subscriptions DataFrame before saving.

    Args:
        df (pd.DataFrame): The generated subscriptions DataFrame.
        users_df (pd.DataFrame): Source dim_users DataFrame for FK validation.
        plans_df (pd.DataFrame): Source dim_subscription_plans DataFrame for FK validation.

    Raises:
        ValueError: If any validation check fails.
    """
    # Check all required columns are present
    required_columns = {
        "subscription_id", "user_id", "plan_id", "start_date", "end_date",
        "renewal_date", "trial_user", "status", "auto_renew",
        "subscription_source", "cancellation_reason", "created_at", "updated_at"
    }
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    # Check non-nullable columns have no nulls
    non_nullable = [
        "subscription_id", "user_id", "plan_id", "start_date",
        "renewal_date", "trial_user", "status", "auto_renew",
        "subscription_source", "created_at", "updated_at"
    ]
    for col in non_nullable:
        if df[col].isnull().any():
            raise ValueError(f"Validation failed: Null values found in column '{col}'.")

    # end_date must be NULL for Active subscriptions
    active_with_end = df[(df["status"] == "Active") & (df["end_date"].notnull())]
    if not active_with_end.empty:
        raise ValueError(
            f"Validation failed: {len(active_with_end)} Active subscription(s) "
            "have a non-null end_date."
        )

    # Cancelled subscriptions must have both end_date and cancellation_reason
    cancelled = df[df["status"] == "Cancelled"]
    if cancelled["end_date"].isnull().any():
        raise ValueError(
            "Validation failed: Cancelled subscriptions must have an end_date."
        )
    if cancelled["cancellation_reason"].isnull().any():
        raise ValueError(
            "Validation failed: Cancelled subscriptions must have a cancellation_reason."
        )

    # Check subscription_id uniqueness
    if not df["subscription_id"].is_unique:
        raise ValueError("Validation failed: subscription_id values must be unique.")

    # Check one subscription per user
    if not df["user_id"].is_unique:
        dupes = df[df["user_id"].duplicated()]["user_id"].tolist()
        raise ValueError(
            f"Validation failed: Multiple subscriptions found for user_id(s): {dupes[:5]}"
        )

    # Foreign key — user_id must exist in dim_users
    valid_user_ids   = set(users_df["user_id"].astype(int))
    sub_user_ids     = set(df["user_id"].astype(int))
    invalid_user_ids = sub_user_ids - valid_user_ids
    if invalid_user_ids:
        raise ValueError(
            f"Validation failed: {len(invalid_user_ids)} user_id(s) not found in dim_users."
        )

    # Foreign key — plan_id must exist in dim_subscription_plans
    valid_plan_ids   = set(plans_df["plan_id"].astype(int))
    sub_plan_ids     = set(df["plan_id"].astype(int))
    invalid_plan_ids = sub_plan_ids - valid_plan_ids
    if invalid_plan_ids:
        raise ValueError(
            f"Validation failed: {len(invalid_plan_ids)} plan_id(s) not found "
            "in dim_subscription_plans."
        )

    # renewal_date must always be after start_date
    renewal_before_start = df[
        pd.to_datetime(df["renewal_date"]) <= pd.to_datetime(df["start_date"])
    ]
    if not renewal_before_start.empty:
        raise ValueError(
            f"Validation failed: {len(renewal_before_start)} renewal_date(s) "
            "are not after start_date."
        )

    # updated_at must always be >= created_at
    if (df["updated_at"] < df["created_at"]).any():
        raise ValueError("Validation failed: updated_at must be >= created_at.")

    # VARCHAR length constraints
    varchar_limits = {
        "status"              : 20,
        "subscription_source" : 30,
        "cancellation_reason" : 150,
    }
    for column, limit in varchar_limits.items():
        exceeded = df[column].dropna().str.len() > limit
        if exceeded.any():
            raise ValueError(
                f"Validation failed: '{column}' exceeds VARCHAR({limit}) limit."
            )

    print("Validation passed: fact_subscriptions dataset is clean and schema-compliant.")

    # Distribution summary
    print("\n--- Distribution Summary ---")
    print(f"\nTotal Subscriptions  : {len(df):,}")

    print("\nStatus Distribution:")
    print(df["status"].value_counts(normalize=True).mul(100).round(1).to_string())

    print("\nPlan Distribution (by plan_id):")
    print(df["plan_id"].value_counts(normalize=True).mul(100).round(1).to_string())

    print("\nSubscription Source:")
    print(df["subscription_source"].value_counts(normalize=True).mul(100).round(1).to_string())

    print(f"\nTrial Users         : {df['trial_user'].sum():,} ({df['trial_user'].mean() * 100:.1f}%)")
    print(f"Auto-Renew Enabled  : {df['auto_renew'].sum():,} ({df['auto_renew'].mean() * 100:.1f}%)")
    print(f"Active (no end_date): {df['end_date'].isnull().sum():,}")


# ------------------------------------------------------------------
# Save CSV Function
# ------------------------------------------------------------------

def save_dataframe_to_csv(df: pd.DataFrame, output_dir: str, file_name: str) -> None:
    """
    Save the DataFrame to a CSV file inside the specified output directory.

    Args:
        df (pd.DataFrame): DataFrame to save.
        output_dir (str): Target directory for the CSV file.
        file_name (str): Name of the output CSV file.
    """
    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(output_dir, file_name)
    df.to_csv(output_path, index=False)

    print(f"\nSaved {len(df):,} records to {output_path}")


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main():
    """
    Main execution flow for generating fact_subscriptions.csv.
    """
    users_df = load_csv(USERS_FILE, parse_dates=["signup_date", "created_at"])
    plans_df = load_csv(PLANS_FILE)

    subs_df  = generate_subscriptions(users_df, plans_df)
    validate_subscriptions_dataframe(subs_df, users_df, plans_df)
    save_dataframe_to_csv(subs_df, OUTPUT_DIR, OUTPUT_FILE)


if __name__ == "__main__":
    main()