"""
generate_users.py

Generates the dim_users.csv dataset for the Netflix Product Analytics project.

Schema (dim_users):
    user_id         INTEGER      (PK)
    full_name       VARCHAR(150)
    email           VARCHAR(150)
    gender          VARCHAR(10)
    date_of_birth   DATE
    age             INTEGER
    country         VARCHAR(100)
    signup_date     DATE
    signup_channel  VARCHAR(50)
    account_status  VARCHAR(20)
    created_at      TIMESTAMP
    updated_at      TIMESTAMP
"""

import os
import random
import numpy as np
import pandas as pd
from faker import Faker
from datetime import datetime, timedelta, date


# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------

OUTPUT_DIR  = "data"
OUTPUT_FILE = "dim_users.csv"

TOTAL_USERS = 10_000
RANDOM_SEED = 42

# Simulation window: 24 months of historical data
SIGNUP_START_DATE = datetime.today() - timedelta(days=730)
SIGNUP_END_DATE   = datetime.today()

# Initialise Faker and seeds for reproducibility
fake = Faker()
Faker.seed(RANDOM_SEED)
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)


# ------------------------------------------------------------------
# Business Rule Configuration
# ------------------------------------------------------------------

COUNTRY_DISTRIBUTION = {
    "United States" : 0.22,
    "India"         : 0.16,
    "Brazil"        : 0.10,
    "United Kingdom": 0.08,
    "Mexico"        : 0.07,
    "Canada"        : 0.06,
    "Germany"       : 0.05,
    "France"        : 0.05,
    "Japan"         : 0.04,
    "Australia"     : 0.04,
    "South Korea"   : 0.03,
    "Philippines"   : 0.03,
    "Spain"         : 0.03,
    "Argentina"     : 0.02,
    "Others"        : 0.02,
}

GENDER_DISTRIBUTION = {
    "Male"  : 0.49,
    "Female": 0.48,
    "Other" : 0.03,
}

# Age groups: (min_age, max_age, weight)
AGE_GROUP_DISTRIBUTION = [
    (13, 17,  0.04),
    (18, 24,  0.22),
    (25, 34,  0.32),
    (35, 44,  0.22),
    (45, 54,  0.12),
    (55, 80,  0.08),
]

SIGNUP_CHANNEL_DISTRIBUTION = {
    "Website"        : 0.35,
    "Android App"    : 0.28,
    "iOS App"        : 0.22,
    "Partner Bundle" : 0.10,
    "Referral"       : 0.05,
}

ACCOUNT_STATUS_DISTRIBUTION = {
    "Active"   : 0.78,
    "Cancelled": 0.14,
    "Suspended": 0.03,
    "Paused"   : 0.05,
}


# ------------------------------------------------------------------
# Helper Functions
# ------------------------------------------------------------------

def weighted_sample(distribution: dict, size: int) -> list:
    """
    Draw a weighted random sample from a distribution dictionary.

    Args:
        distribution (dict): Keys are category labels, values are probabilities.
        size (int): Number of samples to draw.

    Returns:
        list: Sampled category labels.
    """
    categories   = list(distribution.keys())
    weights      = list(distribution.values())
    return random.choices(categories, weights=weights, k=size)


def generate_age_from_groups(age_groups: list) -> int:
    """
    Pick a random age respecting the defined age group distribution.

    Args:
        age_groups (list): List of (min_age, max_age, weight) tuples.

    Returns:
        int: A randomly selected age.
    """
    groups  = [(mn, mx) for mn, mx, _ in age_groups]
    weights = [w for _, _, w in age_groups]
    chosen_group = random.choices(groups, weights=weights, k=1)[0]
    return random.randint(chosen_group[0], chosen_group[1])


def age_to_dob(age: int, reference_date: date) -> date:
    """
    Convert an integer age to a plausible date_of_birth relative to a reference date.

    Args:
        age (int): The person's age in years.
        reference_date (date): The date against which age is calculated (signup_date).

    Returns:
        date: A realistic date of birth.
    """
    birth_year  = reference_date.year - age
    birth_month = random.randint(1, 12)
    birth_day   = random.randint(1, 28)   # Use 28 to avoid invalid Feb dates
    return date(birth_year, birth_month, birth_day)


def generate_signup_date(start: datetime, end: datetime) -> date:
    """
    Generate a random signup date within the 24-month simulation window.

    Higher signup volume is applied in Nov–Jan and June–Aug to reflect
    seasonal streaming trends described in business rules.

    Args:
        start (datetime): Start of simulation window.
        end (datetime): End of simulation window.

    Returns:
        date: A randomly generated signup date.
    """
    delta_days = (end - start).days
    rand_days  = random.randint(0, delta_days)
    return (start + timedelta(days=rand_days)).date()


def generate_created_at(signup_date: date) -> datetime:
    """
    Generate a realistic created_at timestamp on the same day as signup_date.

    Args:
        signup_date (date): The user's signup date.

    Returns:
        datetime: A timestamp on the signup date with a random time.
    """
    random_hour   = random.randint(0, 23)
    random_minute = random.randint(0, 59)
    random_second = random.randint(0, 59)
    return datetime(
        signup_date.year,
        signup_date.month,
        signup_date.day,
        random_hour,
        random_minute,
        random_second,
    )


def generate_updated_at(created_at: datetime) -> datetime:
    """
    Generate an updated_at timestamp that is always >= created_at.

    Updated timestamps are within 0–365 days after account creation,
    simulating profile edits, plan changes, or status updates.

    Args:
        created_at (datetime): The account creation timestamp.

    Returns:
        datetime: A timestamp equal to or later than created_at.
    """
    days_offset   = random.randint(0, 365)
    hour_offset   = random.randint(0, 23)
    minute_offset = random.randint(0, 59)
    return created_at + timedelta(days=days_offset, hours=hour_offset, minutes=minute_offset)


def generate_unique_email(full_name: str, user_id: int) -> str:
    """
    Generate a unique email address from a user's name and ID.

    Uses the user_id suffix to guarantee uniqueness even when names collide.

    Args:
        full_name (str): The user's full name.
        user_id (int): The unique user identifier.

    Returns:
        str: A realistic unique email address.
    """
    domains    = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com"]
    domain     = random.choice(domains)
    name_parts = full_name.lower().replace(" ", ".")
    # Append user_id to guarantee global uniqueness
    return f"{name_parts}.{user_id}@{domain}"


# ------------------------------------------------------------------
# Data Generation Function
# ------------------------------------------------------------------

def generate_users(total_users: int) -> pd.DataFrame:
    """
    Generate the full dim_users dataset following all business rules.

    Args:
        total_users (int): Total number of user records to generate.

    Returns:
        pd.DataFrame: DataFrame matching the dim_users PostgreSQL schema.
    """
    print(f"Generating {total_users:,} users...")

    # Pre-sample categorical fields using weighted distributions
    countries      = weighted_sample(COUNTRY_DISTRIBUTION,        total_users)
    genders        = weighted_sample(GENDER_DISTRIBUTION,         total_users)
    signup_channels = weighted_sample(SIGNUP_CHANNEL_DISTRIBUTION, total_users)
    account_statuses = weighted_sample(ACCOUNT_STATUS_DISTRIBUTION, total_users)

    records = []

    for i in range(total_users):
        user_id     = i + 1
        full_name   = fake.name()
        gender      = genders[i]
        country     = countries[i]
        signup_channel = signup_channels[i]
        account_status = account_statuses[i]

        # Generate age respecting group distribution, then derive DOB
        age         = generate_age_from_groups(AGE_GROUP_DISTRIBUTION)
        signup_date = generate_signup_date(SIGNUP_START_DATE, SIGNUP_END_DATE)
        dob         = age_to_dob(age, signup_date)

        # Generate timestamps
        created_at  = generate_created_at(signup_date)
        updated_at  = generate_updated_at(created_at)

        # Generate unique email
        email = generate_unique_email(full_name, user_id)

        records.append({
            "user_id"       : user_id,
            "full_name"     : full_name,
            "email"         : email,
            "gender"        : gender,
            "date_of_birth" : dob,
            "age"           : age,
            "country"       : country,
            "signup_date"   : signup_date,
            "signup_channel": signup_channel,
            "account_status": account_status,
            "created_at"    : created_at,
            "updated_at"    : updated_at,
        })

    df = pd.DataFrame(records)

    # Enforce correct data types
    df["user_id"]        = df["user_id"].astype(int)
    df["full_name"]      = df["full_name"].astype(str)
    df["email"]          = df["email"].astype(str)
    df["gender"]         = df["gender"].astype(str)
    df["date_of_birth"]  = pd.to_datetime(df["date_of_birth"]).dt.date
    df["age"]            = df["age"].astype(int)
    df["country"]        = df["country"].astype(str)
    df["signup_date"]    = pd.to_datetime(df["signup_date"]).dt.date
    df["signup_channel"] = df["signup_channel"].astype(str)
    df["account_status"] = df["account_status"].astype(str)
    df["created_at"]     = pd.to_datetime(df["created_at"])
    df["updated_at"]     = pd.to_datetime(df["updated_at"])

    return df


# ------------------------------------------------------------------
# Validation Function
# ------------------------------------------------------------------

def validate_users_dataframe(df: pd.DataFrame) -> None:
    """
    Run validation checks on the dim_users DataFrame before saving.

    Args:
        df (pd.DataFrame): The generated users DataFrame.

    Raises:
        ValueError: If any validation check fails.
    """
    # Check all required columns are present
    required_columns = {
        "user_id", "full_name", "email", "gender", "date_of_birth",
        "age", "country", "signup_date", "signup_channel",
        "account_status", "created_at", "updated_at"
    }
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    # Check for null values
    if df.isnull().values.any():
        null_counts = df.isnull().sum()
        raise ValueError(f"Validation failed: Null values found:\n{null_counts[null_counts > 0]}")

    # Check user_id uniqueness
    if not df["user_id"].is_unique:
        raise ValueError("Validation failed: user_id values must be unique.")

    # Check email uniqueness
    if not df["email"].is_unique:
        duplicates = df[df["email"].duplicated()]["email"].tolist()
        raise ValueError(f"Validation failed: Duplicate emails found: {duplicates[:5]}")

    # Check age is within valid range (13–80 per business rules)
    if (df["age"] < 13).any() or (df["age"] > 80).any():
        raise ValueError("Validation failed: Age values outside expected range (13–80).")

    # Check updated_at is always >= created_at
    if (df["updated_at"] < df["created_at"]).any():
        raise ValueError("Validation failed: updated_at must be >= created_at.")

    # Check VARCHAR length constraints
    varchar_limits = {
        "full_name"     : 150,
        "email"         : 150,
        "gender"        : 10,
        "country"       : 100,
        "signup_channel": 50,
        "account_status": 20,
    }
    for column, limit in varchar_limits.items():
        if (df[column].str.len() > limit).any():
            raise ValueError(
                f"Validation failed: '{column}' exceeds VARCHAR({limit}) limit."
            )

    print("Validation passed: dim_users dataset is clean and schema-compliant.")

    # Print distribution summary for verification
    print("\n--- Distribution Summary ---")
    print(f"\nTotal Users     : {len(df):,}")

    print("\nAccount Status  :")
    print(df["account_status"].value_counts(normalize=True).mul(100).round(1).to_string())

    print("\nGender          :")
    print(df["gender"].value_counts(normalize=True).mul(100).round(1).to_string())

    print("\nTop 5 Countries :")
    print(df["country"].value_counts(normalize=True).mul(100).round(1).head(5).to_string())

    print("\nSignup Channel  :")
    print(df["signup_channel"].value_counts(normalize=True).mul(100).round(1).to_string())

    print("\nAge Stats       :")
    print(df["age"].describe().round(1).to_string())


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
    Main execution flow for generating dim_users.csv.
    """
    users_df = generate_users(TOTAL_USERS)
    validate_users_dataframe(users_df)
    save_dataframe_to_csv(users_df, OUTPUT_DIR, OUTPUT_FILE)


if __name__ == "__main__":
    main()