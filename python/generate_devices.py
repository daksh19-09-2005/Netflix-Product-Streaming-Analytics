"""
generate_devices.py

Generates the dim_devices.csv dataset for the Netflix Product Analytics project.

Schema (dim_devices):
    device_id     INTEGER     (PK)
    device_type   VARCHAR(30)
    device_brand  VARCHAR(50)
    os_name       VARCHAR(30)
    app_version   VARCHAR(20)
"""

import os
import pandas as pd


# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------

OUTPUT_DIR  = "data"
OUTPUT_FILE = "dim_devices.csv"

# Realistic app versions across the platform (shared across device types)
APP_VERSIONS = [
    "8.0.1",
    "8.1.0",
    "8.2.3",
    "9.0.0",
    "9.1.1",
]

# Device combinations defined per device type
# Structure: (device_type, device_brand, os_name)
# App version is assigned per combination during DataFrame build
# Brand/OS pairings follow real-world constraints (e.g. Apple Mobile → iOS only)
DEVICE_COMBINATIONS = [

    # ------------------------------------------------------------------
    # Mobile — Apple (iOS only)
    # ------------------------------------------------------------------
    ("Mobile", "Apple",   "iOS"),
    ("Mobile", "Apple",   "iOS"),

    # ------------------------------------------------------------------
    # Mobile — Samsung (Android only)
    # ------------------------------------------------------------------
    ("Mobile", "Samsung", "Android"),
    ("Mobile", "Samsung", "Android"),

    # ------------------------------------------------------------------
    # Mobile — Xiaomi (Android only)
    # ------------------------------------------------------------------
    ("Mobile", "Xiaomi",  "Android"),
    ("Mobile", "Xiaomi",  "Android"),

    # ------------------------------------------------------------------
    # Mobile — OnePlus (Android only)
    # ------------------------------------------------------------------
    ("Mobile", "OnePlus", "Android"),
    ("Mobile", "OnePlus", "Android"),

    # ------------------------------------------------------------------
    # Mobile — Google (Android only)
    # ------------------------------------------------------------------
    ("Mobile", "Google",  "Android"),
    ("Mobile", "Google",  "Android"),

    # ------------------------------------------------------------------
    # Smart TV — Samsung (Tizen OS)
    # ------------------------------------------------------------------
    ("Smart TV", "Samsung",        "Tizen"),
    ("Smart TV", "Samsung",        "Tizen"),

    # ------------------------------------------------------------------
    # Smart TV — LG (webOS)
    # ------------------------------------------------------------------
    ("Smart TV", "LG",             "webOS"),
    ("Smart TV", "LG",             "webOS"),

    # ------------------------------------------------------------------
    # Smart TV — Sony (Android TV)
    # ------------------------------------------------------------------
    ("Smart TV", "Sony",           "Android TV"),
    ("Smart TV", "Sony",           "Android TV"),

    # ------------------------------------------------------------------
    # Smart TV — Amazon Fire TV (Fire OS)
    # ------------------------------------------------------------------
    ("Smart TV", "Amazon Fire TV", "Fire OS"),
    ("Smart TV", "Amazon Fire TV", "Fire OS"),

    # ------------------------------------------------------------------
    # Smart TV — Roku (Roku OS)
    # ------------------------------------------------------------------
    ("Smart TV", "Roku",           "Roku OS"),
    ("Smart TV", "Roku",           "Roku OS"),

    # ------------------------------------------------------------------
    # Laptop/Desktop — HP (Windows)
    # ------------------------------------------------------------------
    ("Laptop/Desktop", "HP",     "Windows"),
    ("Laptop/Desktop", "HP",     "Windows"),

    # ------------------------------------------------------------------
    # Laptop/Desktop — Dell (Windows)
    # ------------------------------------------------------------------
    ("Laptop/Desktop", "Dell",   "Windows"),
    ("Laptop/Desktop", "Dell",   "Windows"),

    # ------------------------------------------------------------------
    # Laptop/Desktop — Lenovo (Windows / Linux)
    # ------------------------------------------------------------------
    ("Laptop/Desktop", "Lenovo", "Windows"),
    ("Laptop/Desktop", "Lenovo", "Linux"),

    # ------------------------------------------------------------------
    # Laptop/Desktop — Apple (macOS only)
    # ------------------------------------------------------------------
    ("Laptop/Desktop", "Apple",  "macOS"),
    ("Laptop/Desktop", "Apple",  "macOS"),

    # ------------------------------------------------------------------
    # Laptop/Desktop — Asus (Windows / Linux)
    # ------------------------------------------------------------------
    ("Laptop/Desktop", "Asus",   "Windows"),
    ("Laptop/Desktop", "Asus",   "Linux"),

    # ------------------------------------------------------------------
    # Tablet — Apple (iPadOS only)
    # ------------------------------------------------------------------
    ("Tablet", "Apple",   "iPadOS"),
    ("Tablet", "Apple",   "iPadOS"),

    # ------------------------------------------------------------------
    # Tablet — Samsung (Android only)
    # ------------------------------------------------------------------
    ("Tablet", "Samsung", "Android"),
    ("Tablet", "Samsung", "Android"),

    # ------------------------------------------------------------------
    # Tablet — Lenovo (Android only)
    # ------------------------------------------------------------------
    ("Tablet", "Lenovo",  "Android"),
    ("Tablet", "Lenovo",  "Android"),
]


# ------------------------------------------------------------------
# Functions
# ------------------------------------------------------------------

def build_devices_dataframe(combinations: list, app_versions: list) -> pd.DataFrame:
    """
    Build the dim_devices DataFrame from the defined device combinations.

    App versions are cycled across combinations to simulate a realistic
    distribution of platform versions in the wild.

    Args:
        combinations (list): List of (device_type, device_brand, os_name) tuples.
        app_versions (list): List of app version strings to cycle through.

    Returns:
        pd.DataFrame: DataFrame matching the dim_devices schema.
    """
    records = []

    for idx, (device_type, device_brand, os_name) in enumerate(combinations):
        # Cycle through app versions evenly across all device rows
        app_version = app_versions[idx % len(app_versions)]

        records.append({
            "device_id"   : idx + 1,
            "device_type" : device_type,
            "device_brand": device_brand,
            "os_name"     : os_name,
            "app_version" : app_version,
        })

    df = pd.DataFrame(records)

    # Enforce correct data types to match PostgreSQL schema
    df["device_id"]    = df["device_id"].astype(int)
    df["device_type"]  = df["device_type"].astype(str)
    df["device_brand"] = df["device_brand"].astype(str)
    df["os_name"]      = df["os_name"].astype(str)
    df["app_version"]  = df["app_version"].astype(str)

    return df


def validate_devices_dataframe(df: pd.DataFrame) -> None:
    """
    Run validation checks on the dim_devices DataFrame before saving.

    Args:
        df (pd.DataFrame): The generated devices DataFrame.

    Raises:
        ValueError: If any validation check fails.
    """
    # Check all required columns are present
    required_columns = {
        "device_id", "device_type", "device_brand", "os_name", "app_version"
    }
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    # Check for null values in any column
    if df.isnull().values.any():
        raise ValueError("Validation failed: Null values found in dim_devices dataset.")

    # Check device_id is unique
    if not df["device_id"].is_unique:
        raise ValueError("Validation failed: device_id values must be unique.")

    # Check all device_id values are positive integers
    if (df["device_id"] <= 0).any():
        raise ValueError("Validation failed: All device_id values must be positive.")

    # Check for fully duplicate rows (same type + brand + os + version)
    duplicate_mask = df.duplicated(
        subset=["device_type", "device_brand", "os_name", "app_version"]
    )
    if duplicate_mask.any():
        raise ValueError(
            f"Validation failed: Duplicate device combinations found:\n"
            f"{df[duplicate_mask]}"
        )

    # Enforce VARCHAR length constraints
    varchar_limits = {
        "device_type" : 30,
        "device_brand": 50,
        "os_name"     : 30,
        "app_version" : 20,
    }
    for column, limit in varchar_limits.items():
        if (df[column].str.len() > limit).any():
            raise ValueError(
                f"Validation failed: '{column}' exceeds VARCHAR({limit}) limit."
            )

    print(
        f"Validation passed: dim_devices dataset is clean and schema-compliant. "
        f"({len(df)} device combinations generated)"
    )


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
    Main execution flow for generating dim_devices.csv.
    """
    devices_df = build_devices_dataframe(DEVICE_COMBINATIONS, APP_VERSIONS)
    validate_devices_dataframe(devices_df)
    save_dataframe_to_csv(devices_df, OUTPUT_DIR, OUTPUT_FILE)


if __name__ == "__main__":
    main()