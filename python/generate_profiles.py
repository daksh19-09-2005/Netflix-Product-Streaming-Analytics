"""
generate_profiles.py

Generates the dim_profiles.csv dataset for the Netflix Product Analytics project.

Depends on:
    data/dim_users.csv  →  to extract valid user_id values, names, and created_at timestamps

Schema (dim_profiles):
    profile_id          INTEGER      (PK)
    user_id             INTEGER      (FK → dim_users)
    profile_name        VARCHAR(100)
    profile_type        VARCHAR(10)
    preferred_language  VARCHAR(50)
    created_at          TIMESTAMP
    updated_at          TIMESTAMP
"""

import os
import random
import numpy as np
import pandas as pd
from faker import Faker
from datetime import datetime, timedelta


# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------

OUTPUT_DIR   = "data"
OUTPUT_FILE  = "dim_profiles.csv"
USERS_FILE   = os.path.join("data", "dim_users.csv")

RANDOM_SEED  = 42

fake = Faker()
Faker.seed(RANDOM_SEED)
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)


# ------------------------------------------------------------------
# Business Rule Configuration
# ------------------------------------------------------------------

# Profile count distribution per account
# (num_profiles_options, weights)
PROFILE_COUNT_GROUPS = [
    ([1],      0.30),   # 30% of accounts → exactly 1 profile
    ([2, 3],   0.50),   # 50% of accounts → 2 or 3 profiles
    ([4, 5],   0.20),   # 20% of accounts → 4 or 5 profiles
]

PROFILE_TYPE_DISTRIBUTION = {
    "Adult": 0.72,
    "Kids" : 0.28,
}

LANGUAGE_DISTRIBUTION = {
    "English"   : 0.40,
    "Spanish"   : 0.15,
    "Portuguese": 0.10,
    "Hindi"     : 0.10,
    "French"    : 0.08,
    "German"    : 0.06,
    "Japanese"  : 0.05,
    "Korean"    : 0.03,
    "Others"    : 0.03,
}


# ------------------------------------------------------------------
# Helper Functions
# ------------------------------------------------------------------

def load_users(filepath: str) -> pd.DataFrame:
    """
    Load dim_users.csv and return a cleaned DataFrame.

    Args:
        filepath (str): Path to the dim_users.csv file.

    Returns:
        pd.DataFrame: Users DataFrame with user_id, full_name, and created_at columns.

    Raises:
        FileNotFoundError: If dim_users.csv does not exist.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(
            f"Dependency missing: '{filepath}' not found. "
            "Run generate_users.py first."
        )

    df = pd.read_csv(filepath, parse_dates=["created_at", "updated_at"])
    print(f"Loaded {len(df):,} users from '{filepath}'.")
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


def determine_profile_count() -> int:
    """
    Determine how many profiles an account should have
    based on the profile count group distribution.

    Returns:
        int: Number of profiles to generate for this account.
    """
    groups  = [group for group, _ in PROFILE_COUNT_GROUPS]
    weights = [weight for _, weight in PROFILE_COUNT_GROUPS]

    chosen_group = random.choices(groups, weights=weights, k=1)[0]
    return random.choice(chosen_group)


def extract_first_name(full_name: str) -> str:
    """
    Extract the first name from a full name string.

    Args:
        full_name (str): The user's full name.

    Returns:
        str: First name only, capitalised.
    """
    return str(full_name).strip().split()[0].capitalize()


def generate_kids_profile_name() -> str:
    """
    Generate a realistic kids profile name.

    Returns:
        str: A short first name suitable for a kids profile.
    """
    return fake.first_name()


def generate_profile_created_at(user_created_at: pd.Timestamp) -> datetime:
    """
    Generate a profile created_at timestamp that is on or after the user's created_at.

    Additional profiles on an account may be created days or months after
    the account was originally opened.

    Args:
        user_created_at (pd.Timestamp): The parent user's account creation timestamp.

    Returns:
        datetime: A valid profile creation timestamp.
    """
    # Additional profiles can be created 0–365 days after account creation
    days_offset   = random.randint(0, 365)
    hour_offset   = random.randint(0, 23)
    minute_offset = random.randint(0, 59)
    second_offset = random.randint(0, 59)

    profile_created_at = user_created_at + timedelta(
        days=days_offset,
        hours=hour_offset,
        minutes=minute_offset,
        seconds=second_offset,
    )

    # Cap at current time to avoid future timestamps
    now = datetime.now()
    if profile_created_at > now:
        profile_created_at = user_created_at

    return profile_created_at


def generate_updated_at(created_at: datetime) -> datetime:
    """
    Generate an updated_at timestamp that is always >= created_at.

    Args:
        created_at (datetime): The profile's creation timestamp.

    Returns:
        datetime: A timestamp equal to or later than created_at.
    """
    days_offset   = random.randint(0, 180)
    hour_offset   = random.randint(0, 23)
    minute_offset = random.randint(0, 59)

    updated_at = created_at + timedelta(
        days=days_offset,
        hours=hour_offset,
        minutes=minute_offset,
    )

    # Cap at current time
    now = datetime.now()
    if updated_at > now:
        updated_at = created_at

    return updated_at


# ------------------------------------------------------------------
# Data Generation Function
# ------------------------------------------------------------------

def generate_profiles(users_df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate the full dim_profiles dataset following all business rules.

    For each user:
      - Determine how many profiles the account will have.
      - The first profile is always a primary Adult profile named after the account owner.
      - Subsequent profiles are either Adult or Kids with realistic names.
      - All profiles receive independent language preferences, timestamps.

    Args:
        users_df (pd.DataFrame): The loaded dim_users DataFrame.

    Returns:
        pd.DataFrame: DataFrame matching the dim_profiles PostgreSQL schema.
    """
    print(f"Generating profiles for {len(users_df):,} users...")

    records    = []
    profile_id = 1

    for _, user in users_df.iterrows():
        user_id          = int(user["user_id"])
        full_name        = str(user["full_name"])
        user_created_at  = user["created_at"]

        # Determine how many profiles this account gets
        num_profiles = determine_profile_count()

        for profile_index in range(num_profiles):

            # ----------------------------------------------------------
            # Primary profile (index 0): always Adult, named after owner
            # ----------------------------------------------------------
            if profile_index == 0:
                profile_name = extract_first_name(full_name)
                profile_type = "Adult"

            # ----------------------------------------------------------
            # Additional profiles: Adult or Kids based on distribution
            # ----------------------------------------------------------
            else:
                profile_type = weighted_choice(PROFILE_TYPE_DISTRIBUTION)
                if profile_type == "Kids":
                    profile_name = generate_kids_profile_name()
                else:
                    profile_name = fake.first_name()

            # Language preference — independent per profile
            preferred_language = weighted_choice(LANGUAGE_DISTRIBUTION)

            # Timestamps
            created_at = generate_profile_created_at(user_created_at)
            updated_at = generate_updated_at(created_at)

            records.append({
                "profile_id"        : profile_id,
                "user_id"           : user_id,
                "profile_name"      : profile_name,
                "profile_type"      : profile_type,
                "preferred_language": preferred_language,
                "created_at"        : created_at,
                "updated_at"        : updated_at,
            })

            profile_id += 1

    df = pd.DataFrame(records)

    # Enforce correct data types to match PostgreSQL schema
    df["profile_id"]         = df["profile_id"].astype(int)
    df["user_id"]            = df["user_id"].astype(int)
    df["profile_name"]       = df["profile_name"].astype(str)
    df["profile_type"]       = df["profile_type"].astype(str)
    df["preferred_language"] = df["preferred_language"].astype(str)
    df["created_at"]         = pd.to_datetime(df["created_at"])
    df["updated_at"]         = pd.to_datetime(df["updated_at"])

    return df


# ------------------------------------------------------------------
# Validation Function
# ------------------------------------------------------------------

def validate_profiles_dataframe(df: pd.DataFrame, users_df: pd.DataFrame) -> None:
    """
    Run validation checks on the dim_profiles DataFrame before saving.

    Args:
        df (pd.DataFrame): The generated profiles DataFrame.
        users_df (pd.DataFrame): The source users DataFrame for FK validation.

    Raises:
        ValueError: If any validation check fails.
    """
    # Check all required columns are present
    required_columns = {
        "profile_id", "user_id", "profile_name",
        "profile_type", "preferred_language", "created_at", "updated_at"
    }
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    # Check for null values
    if df.isnull().values.any():
        null_counts = df.isnull().sum()
        raise ValueError(
            f"Validation failed: Null values found:\n{null_counts[null_counts > 0]}"
        )

    # Check profile_id uniqueness
    if not df["profile_id"].is_unique:
        raise ValueError("Validation failed: profile_id values must be unique.")

    # Check all user_id values exist in dim_users
    valid_user_ids   = set(users_df["user_id"].astype(int))
    profile_user_ids = set(df["user_id"].astype(int))
    invalid_ids      = profile_user_ids - valid_user_ids
    if invalid_ids:
        raise ValueError(
            f"Validation failed: {len(invalid_ids)} profile(s) have user_id "
            f"values not found in dim_users."
        )

    # Check every user has at least one profile
    users_with_profiles = set(df["user_id"].unique())
    all_users           = set(users_df["user_id"].astype(int).unique())
    users_without       = all_users - users_with_profiles
    if users_without:
        raise ValueError(
            f"Validation failed: {len(users_without)} user(s) have no profiles assigned."
        )

    # Check updated_at is always >= created_at
    if (df["updated_at"] < df["created_at"]).any():
        raise ValueError("Validation failed: updated_at must be >= created_at.")

    # Check VARCHAR length constraints
    varchar_limits = {
        "profile_name"      : 100,
        "profile_type"      : 10,
        "preferred_language": 50,
    }
    for column, limit in varchar_limits.items():
        if (df[column].str.len() > limit).any():
            raise ValueError(
                f"Validation failed: '{column}' exceeds VARCHAR({limit}) limit."
            )

    print("Validation passed: dim_profiles dataset is clean and schema-compliant.")

    # Print distribution summary for verification
    print("\n--- Distribution Summary ---")
    print(f"\nTotal Profiles Generated : {len(df):,}")
    print(f"Total Users Covered      : {df['user_id'].nunique():,}")
    print(f"Avg Profiles per User    : {len(df) / df['user_id'].nunique():.2f}")

    print("\nProfile Type Distribution:")
    print(df["profile_type"].value_counts(normalize=True).mul(100).round(1).to_string())

    print("\nPreferred Language Distribution:")
    print(df["preferred_language"].value_counts(normalize=True).mul(100).round(1).to_string())

    print("\nProfiles per User (sample stats):")
    profiles_per_user = df.groupby("user_id")["profile_id"].count()
    print(profiles_per_user.describe().round(2).to_string())


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
    Main execution flow for generating dim_profiles.csv.
    """
    users_df    = load_users(USERS_FILE)
    profiles_df = generate_profiles(users_df)
    validate_profiles_dataframe(profiles_df, users_df)
    save_dataframe_to_csv(profiles_df, OUTPUT_DIR, OUTPUT_FILE)


if __name__ == "__main__":
    main()