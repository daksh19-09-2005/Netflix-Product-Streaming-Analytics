"""
generate_subscription_plans.py

Generates the dim_subscription_plans.csv dataset for the Netflix Product Analytics project.

Schema (dim_subscription_plans):
    plan_id         INTEGER     (PK)
    plan_name       VARCHAR(50)
    plan_tier       VARCHAR(30)
    monthly_price   NUMERIC(8,2)
    max_screens     SMALLINT
    video_quality   VARCHAR(20)
    is_active       BOOLEAN
"""

import os
import pandas as pd


# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------

OUTPUT_DIR  = "data"
OUTPUT_FILE = "dim_subscription_plans.csv"

# Static plan definitions based on finalized business rules
# Basic  → 30% of users  | Standard → 45% | Premium → 25%
SUBSCRIPTION_PLANS = [
    {
        "plan_id"       : 1,
        "plan_name"     : "Basic",
        "plan_tier"     : "Basic",
        "monthly_price" : 6.99,
        "max_screens"   : 1,
        "video_quality" : "HD",
        "is_active"     : True,
    },
    {
        "plan_id"       : 2,
        "plan_name"     : "Standard",
        "plan_tier"     : "Standard",
        "monthly_price" : 12.99,
        "max_screens"   : 2,
        "video_quality" : "Full HD",
        "is_active"     : True,
    },
    {
        "plan_id"       : 3,
        "plan_name"     : "Premium",
        "plan_tier"     : "Premium",
        "monthly_price" : 17.99,
        "max_screens"   : 4,
        "video_quality" : "4K",
        "is_active"     : True,
    },
]


# ------------------------------------------------------------------
# Functions
# ------------------------------------------------------------------

def build_subscription_plans_dataframe(plans: list) -> pd.DataFrame:
    """
    Build the dim_subscription_plans DataFrame from the static plan definitions.

    Args:
        plans (list): List of plan dictionaries containing all schema fields.

    Returns:
        pd.DataFrame: DataFrame matching the dim_subscription_plans schema.
    """
    df = pd.DataFrame(plans)

    # Enforce correct data types to match PostgreSQL schema
    df["plan_id"]       = df["plan_id"].astype(int)
    df["plan_name"]     = df["plan_name"].astype(str)
    df["plan_tier"]     = df["plan_tier"].astype(str)
    df["monthly_price"] = df["monthly_price"].astype(float).round(2)
    df["max_screens"]   = df["max_screens"].astype(int)
    df["video_quality"] = df["video_quality"].astype(str)
    df["is_active"]     = df["is_active"].astype(bool)

    return df


def validate_subscription_plans_dataframe(df: pd.DataFrame) -> None:
    """
    Run validation checks on the dim_subscription_plans DataFrame before saving.

    Args:
        df (pd.DataFrame): The generated subscription plans DataFrame.

    Raises:
        ValueError: If any validation check fails.
    """
    # Check required columns are present
    required_columns = {
        "plan_id", "plan_name", "plan_tier",
        "monthly_price", "max_screens", "video_quality", "is_active"
    }
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    # Check for null values in any column
    if df.isnull().values.any():
        raise ValueError("Validation failed: Null values found in dim_subscription_plans dataset.")

    # Check plan_id is unique
    if not df["plan_id"].is_unique:
        raise ValueError("Validation failed: plan_id values must be unique.")

    # Check plan_name is unique
    if not df["plan_name"].is_unique:
        raise ValueError("Validation failed: plan_name values must be unique.")

    # Check monthly_price is strictly positive
    if (df["monthly_price"] <= 0).any():
        raise ValueError("Validation failed: monthly_price must be greater than 0.")

    # Check max_screens is strictly positive
    if (df["max_screens"] <= 0).any():
        raise ValueError("Validation failed: max_screens must be greater than 0.")

    # Check plan_name does not exceed VARCHAR(50) limit
    if (df["plan_name"].str.len() > 50).any():
        raise ValueError("Validation failed: plan_name exceeds VARCHAR(50) limit.")

    # Check plan_tier does not exceed VARCHAR(30) limit
    if (df["plan_tier"].str.len() > 30).any():
        raise ValueError("Validation failed: plan_tier exceeds VARCHAR(30) limit.")

    # Check video_quality does not exceed VARCHAR(20) limit
    if (df["video_quality"].str.len() > 20).any():
        raise ValueError("Validation failed: video_quality exceeds VARCHAR(20) limit.")

    print("Validation passed: dim_subscription_plans dataset is clean and schema-compliant.")


def save_dataframe_to_csv(df: pd.DataFrame, output_dir: str, file_name: str) -> None:
    """
    Save the DataFrame to a CSV file inside the specified output directory.

    Args:
        df (pd.DataFrame): DataFrame to save.
        output_dir (str): Target directory for the CSV file.
        file_name (str): Name of the output CSV file.
    """
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(output_dir, file_name)
    df.to_csv(output_path, index=False)

    print(f"Saved {len(df)} records to {output_path}")


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main():
    """
    Main execution flow for generating dim_subscription_plans.csv.
    """
    plans_df = build_subscription_plans_dataframe(SUBSCRIPTION_PLANS)
    validate_subscription_plans_dataframe(plans_df)
    save_dataframe_to_csv(plans_df, OUTPUT_DIR, OUTPUT_FILE)


if __name__ == "__main__":
    main()