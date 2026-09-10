"""
generate_content.py

Generates the dim_content.csv dataset for the Netflix Product Analytics project.

Schema (dim_content):
    content_id              INTEGER      (PK)
    title                   VARCHAR(200)
    content_type            VARCHAR(20)
    release_year            SMALLINT
    original_language       VARCHAR(50)
    maturity_rating         VARCHAR(10)
    total_seasons           SMALLINT
    total_episodes          SMALLINT
    runtime_minutes         INTEGER
    content_length_category VARCHAR(20)
    production_country      VARCHAR(100)
    content_status          VARCHAR(20)
    imdb_rating             NUMERIC(3,1)
    added_date              DATE
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

OUTPUT_DIR    = "data"
OUTPUT_FILE   = "dim_content.csv"

TOTAL_CONTENT = 2_000
RANDOM_SEED   = 42

# Simulation window: content added within the last 10 years
ADDED_DATE_START = datetime.today() - timedelta(days=365 * 10)
ADDED_DATE_END   = datetime.today()

fake = Faker()
Faker.seed(RANDOM_SEED)
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)


# ------------------------------------------------------------------
# Business Rule Configuration
# ------------------------------------------------------------------

CONTENT_TYPE_DISTRIBUTION = {
    "Movie"   : 0.65,
    "TV Show" : 0.35,
}

LANGUAGE_DISTRIBUTION = {
    "English"   : 0.45,
    "Spanish"   : 0.12,
    "Hindi"     : 0.10,
    "Korean"    : 0.08,
    "French"    : 0.07,
    "Portuguese": 0.06,
    "Japanese"  : 0.05,
    "German"    : 0.04,
    "Others"    : 0.03,
}

PRODUCTION_COUNTRY_DISTRIBUTION = {
    "United States": 0.38,
    "India"        : 0.12,
    "United Kingdom": 0.08,
    "South Korea"  : 0.07,
    "Spain"        : 0.06,
    "Mexico"       : 0.05,
    "Brazil"       : 0.05,
    "France"       : 0.05,
    "Japan"        : 0.04,
    "Others"       : 0.10,
}

# IMDb rating bands: (min, max, weight)
IMDB_RATING_BANDS = [
    (8.0, 10.0, 0.12),
    (7.0,  7.9, 0.30),
    (6.0,  6.9, 0.32),
    (5.0,  5.9, 0.18),
    (1.0,  4.9, 0.08),
]

CONTENT_STATUS_DISTRIBUTION = {
    "Available"  : 0.90,
    "Coming Soon": 0.05,
    "Removed"    : 0.05,
}

MATURITY_RATINGS = ["G", "PG", "PG-13", "R", "NC-17", "TV-Y", "TV-G", "TV-PG", "TV-14", "TV-MA"]

# Netflix-style title component pools for realistic title generation
TITLE_ADJECTIVES = [
    "Dark", "Lost", "Broken", "Silent", "Wild", "Last", "Hidden", "Black",
    "Red", "Burning", "Frozen", "Fallen", "Rising", "Unknown", "Hollow",
    "Sacred", "Shattered", "Cold", "Empty", "Twisted", "Neon", "Midnight",
    "Ancient", "Crimson", "Rogue", "Savage", "Iron", "Golden", "Cursed",
    "Electric", "Shadow", "Dead", "Blind", "Hungry", "Restless",
]

TITLE_NOUNS = [
    "Kingdom", "City", "Night", "Season", "Storm", "Blood", "Fire", "Heart",
    "World", "Mind", "Code", "Signal", "Road", "Empire", "Mirror", "Valley",
    "Ocean", "Forest", "Mountain", "Tower", "Circle", "Line", "Echo", "Gate",
    "Bridge", "Edge", "Horizon", "Crown", "Wolf", "Throne", "Origin", "Fall",
    "Frontier", "Paradise", "Abyss", "Legacy", "Tide", "Veil", "Ghost", "Rebel",
]

TITLE_SUFFIXES = [
    "Chronicles", "Files", "Diaries", "Stories", "Untold", "Returns",
    "Reborn", "Revisited", "Rising", "Unleashed", "Unlimited", "Forever",
    "Begins", "Reloaded", "Part II", "Origins", "Uncut", "Uncensored",
]

TITLE_PREFIXES = [
    "The", "A", "My", "Our", "No", "Beyond", "Inside", "After", "Before",
    "Project", "Operation", "Mission", "Chronicles of", "Rise of", "Fall of",
    "Return to", "Escape from", "Into the", "Out of", "Tales of",
]


# ------------------------------------------------------------------
# Helper Functions
# ------------------------------------------------------------------

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


def generate_imdb_rating() -> float:
    """
    Generate a realistic IMDb rating based on the defined band distribution.

    Returns:
        float: IMDb rating rounded to 1 decimal place.
    """
    bands   = [(mn, mx) for mn, mx, _ in IMDB_RATING_BANDS]
    weights = [w for _, _, w in IMDB_RATING_BANDS]

    chosen_band = random.choices(bands, weights=weights, k=1)[0]
    rating      = random.uniform(chosen_band[0], chosen_band[1])
    return round(rating, 1)


def generate_title(existing_titles: set) -> str:
    """
    Generate a unique Netflix-style content title.

    Combines prefixes, adjectives, nouns, and suffixes randomly.
    Retries until a unique title is produced.

    Args:
        existing_titles (set): Set of already generated titles to avoid duplicates.

    Returns:
        str: A unique content title.
    """
    attempts = 0
    while True:
        pattern = random.randint(1, 6)

        if pattern == 1:
            title = f"{random.choice(TITLE_PREFIXES)} {random.choice(TITLE_NOUNS)}"
        elif pattern == 2:
            title = f"{random.choice(TITLE_ADJECTIVES)} {random.choice(TITLE_NOUNS)}"
        elif pattern == 3:
            title = (
                f"{random.choice(TITLE_PREFIXES)} "
                f"{random.choice(TITLE_ADJECTIVES)} "
                f"{random.choice(TITLE_NOUNS)}"
            )
        elif pattern == 4:
            title = (
                f"{random.choice(TITLE_ADJECTIVES)} "
                f"{random.choice(TITLE_NOUNS)}: "
                f"{random.choice(TITLE_SUFFIXES)}"
            )
        elif pattern == 5:
            title = (
                f"{random.choice(TITLE_NOUNS)} "
                f"{random.choice(TITLE_SUFFIXES)}"
            )
        else:
            # Faker-based fallback for variety
            title = f"{fake.last_name()}'s {random.choice(TITLE_NOUNS)}"

        # Guarantee uniqueness; on repeated collisions add a numeric suffix
        if title not in existing_titles:
            return title

        attempts += 1
        if attempts > 10:
            title = f"{title} {random.randint(2, 99)}"
            if title not in existing_titles:
                return title


def generate_runtime(content_type: str) -> int:
    """
    Generate a realistic runtime in minutes based on content type.

    For TV Shows the runtime represents the average episode duration.

    Runtime category targets:
        Movies   → Short (<45 min): 10% | Medium (45–90 min): 25% | Long (>90 min): 65%
        TV Shows → Short (<45 min): 50% | Medium (45–90 min): 40% | Long (>90 min): 10%

    Args:
        content_type (str): 'Movie' or 'TV Show'.

    Returns:
        int: Runtime in minutes.
    """
    if content_type == "Movie":
        # Weighted selection of runtime category for Movies
        category = random.choices(
            ["Short", "Medium", "Long"],
            weights=[0.10, 0.25, 0.65],
            k=1
        )[0]

        if category == "Short":
            return random.randint(10, 44)    # Short Movie  → < 45 min
        elif category == "Medium":
            return random.randint(45, 90)    # Medium Movie → 45–90 min
        else:
            return random.randint(91, 210)   # Long Movie   → > 90 min

    else:
        # Weighted selection of runtime category for TV Shows (episode duration)
        category = random.choices(
            ["Short", "Medium", "Long"],
            weights=[0.50, 0.40, 0.10],
            k=1
        )[0]

        if category == "Short":
            return random.randint(10, 44)    # Short episode  → < 45 min
        elif category == "Medium":
            return random.randint(45, 90)    # Medium episode → 45–90 min
        else:
            return random.randint(91, 120)   # Long episode   → > 90 min


def derive_content_length_category(runtime_minutes: int) -> str:
    """
    Derive content_length_category from runtime_minutes.

    Rules:
        Short  → runtime < 45
        Medium → 45 <= runtime <= 90
        Long   → runtime > 90

    Args:
        runtime_minutes (int): Runtime duration in minutes.

    Returns:
        str: 'Short', 'Medium', or 'Long'.
    """
    if runtime_minutes < 45:
        return "Short"
    elif runtime_minutes <= 90:
        return "Medium"
    else:
        return "Long"


def generate_seasons_and_episodes(content_type: str) -> tuple:
    """
    Generate total_seasons and total_episodes based on content type.

    Movies always return (0, 0).
    TV Shows return a realistic (seasons, episodes) pair.

    Args:
        content_type (str): 'Movie' or 'TV Show'.

    Returns:
        tuple: (total_seasons, total_episodes)
    """
    if content_type == "Movie":
        return 0, 0

    total_seasons  = random.randint(1, 10)

    # Realistic episode count: roughly 6–20 episodes per season
    episodes_per_season = random.randint(6, 20)
    total_episodes = min(total_seasons * episodes_per_season, 150)

    return total_seasons, total_episodes


def generate_added_date(start: datetime, end: datetime) -> date:
    """
    Generate a random added_date within the last 10 years.

    Args:
        start (datetime): Start of the window.
        end (datetime): End of the window.

    Returns:
        date: A randomly generated added date.
    """
    delta_days = (end - start).days
    rand_days  = random.randint(0, delta_days)
    return (start + timedelta(days=rand_days)).date()


def generate_release_year(added_date: date) -> int:
    """
    Generate a realistic release year at or before the added_date year.

    Content on Netflix can range from older classics to brand-new releases.

    Args:
        added_date (date): The date the content was added to the platform.

    Returns:
        int: A release year between 1970 and the added_date year.
    """
    return random.randint(1970, added_date.year)


# ------------------------------------------------------------------
# Data Generation Function
# ------------------------------------------------------------------

def generate_content(total_content: int) -> pd.DataFrame:
    """
    Generate the full dim_content dataset following all business rules.

    Args:
        total_content (int): Total number of content records to generate.

    Returns:
        pd.DataFrame: DataFrame matching the dim_content PostgreSQL schema.
    """
    print(f"Generating {total_content:,} content records...")

    # Pre-sample categorical fields using weighted distributions
    content_types        = [weighted_choice(CONTENT_TYPE_DISTRIBUTION)    for _ in range(total_content)]
    original_languages   = [weighted_choice(LANGUAGE_DISTRIBUTION)         for _ in range(total_content)]
    production_countries = [weighted_choice(PRODUCTION_COUNTRY_DISTRIBUTION) for _ in range(total_content)]
    content_statuses     = [weighted_choice(CONTENT_STATUS_DISTRIBUTION)   for _ in range(total_content)]

    existing_titles: set = set()
    records = []

    for i in range(total_content):
        content_id       = i + 1
        content_type     = content_types[i]
        original_language   = original_languages[i]
        production_country  = production_countries[i]
        content_status   = content_statuses[i]
        maturity_rating  = random.choice(MATURITY_RATINGS)

        # Generate unique title
        title = generate_title(existing_titles)
        existing_titles.add(title)

        # Runtime and derived category
        runtime_minutes         = generate_runtime(content_type)
        content_length_category = derive_content_length_category(runtime_minutes)

        # Seasons and episodes
        total_seasons, total_episodes = generate_seasons_and_episodes(content_type)

        # Dates
        added_date   = generate_added_date(ADDED_DATE_START, ADDED_DATE_END)
        release_year = generate_release_year(added_date)

        # IMDb rating
        imdb_rating = generate_imdb_rating()

        records.append({
            "content_id"             : content_id,
            "title"                  : title,
            "content_type"           : content_type,
            "release_year"           : release_year,
            "original_language"      : original_language,
            "maturity_rating"        : maturity_rating,
            "total_seasons"          : total_seasons,
            "total_episodes"         : total_episodes,
            "runtime_minutes"        : runtime_minutes,
            "content_length_category": content_length_category,
            "production_country"     : production_country,
            "content_status"         : content_status,
            "imdb_rating"            : imdb_rating,
            "added_date"             : added_date,
        })

    df = pd.DataFrame(records)

    # Enforce correct data types to match PostgreSQL schema
    df["content_id"]              = df["content_id"].astype(int)
    df["title"]                   = df["title"].astype(str)
    df["content_type"]            = df["content_type"].astype(str)
    df["release_year"]            = df["release_year"].astype(int)
    df["original_language"]       = df["original_language"].astype(str)
    df["maturity_rating"]         = df["maturity_rating"].astype(str)
    df["total_seasons"]           = df["total_seasons"].astype(int)
    df["total_episodes"]          = df["total_episodes"].astype(int)
    df["runtime_minutes"]         = df["runtime_minutes"].astype(int)
    df["content_length_category"] = df["content_length_category"].astype(str)
    df["production_country"]      = df["production_country"].astype(str)
    df["content_status"]          = df["content_status"].astype(str)
    df["imdb_rating"]             = df["imdb_rating"].astype(float).round(1)
    df["added_date"]              = pd.to_datetime(df["added_date"]).dt.date

    return df


# ------------------------------------------------------------------
# Validation Function
# ------------------------------------------------------------------

def validate_content_dataframe(df: pd.DataFrame) -> None:
    """
    Run validation checks on the dim_content DataFrame before saving.

    Args:
        df (pd.DataFrame): The generated content DataFrame.

    Raises:
        ValueError: If any validation check fails.
    """
    # Check all required columns are present
    required_columns = {
        "content_id", "title", "content_type", "release_year",
        "original_language", "maturity_rating", "total_seasons",
        "total_episodes", "runtime_minutes", "content_length_category",
        "production_country", "content_status", "imdb_rating", "added_date"
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

    # Check content_id uniqueness
    if not df["content_id"].is_unique:
        raise ValueError("Validation failed: content_id values must be unique.")

    # Check title uniqueness
    if not df["title"].is_unique:
        duplicates = df[df["title"].duplicated()]["title"].tolist()
        raise ValueError(
            f"Validation failed: Duplicate titles found: {duplicates[:5]}"
        )

    # Movies must have total_seasons = 0 and total_episodes = 0
    movies = df[df["content_type"] == "Movie"]
    if (movies["total_seasons"] != 0).any() or (movies["total_episodes"] != 0).any():
        raise ValueError(
            "Validation failed: Movies must have total_seasons = 0 and total_episodes = 0."
        )

    # TV Shows must have at least one season
    tv_shows = df[df["content_type"] == "TV Show"]
    if (tv_shows["total_seasons"] < 1).any():
        raise ValueError(
            "Validation failed: TV Shows must have at least one season."
        )

    # Runtime must be strictly positive
    if (df["runtime_minutes"] <= 0).any():
        raise ValueError("Validation failed: runtime_minutes must be positive.")

    # IMDb rating must be between 1.0 and 10.0
    if (df["imdb_rating"] < 1.0).any() or (df["imdb_rating"] > 10.0).any():
        raise ValueError(
            "Validation failed: imdb_rating must be between 1.0 and 10.0."
        )

    # Validate content_length_category is correctly derived
    def expected_category(runtime: int) -> str:
        if runtime < 45:
            return "Short"
        elif runtime <= 90:
            return "Medium"
        else:
            return "Long"

    derived = df["runtime_minutes"].apply(expected_category)
    if not (derived == df["content_length_category"]).all():
        raise ValueError(
            "Validation failed: content_length_category does not match runtime_minutes."
        )

    # Check VARCHAR length constraints
    varchar_limits = {
        "title"                  : 200,
        "content_type"           : 20,
        "original_language"      : 50,
        "maturity_rating"        : 10,
        "content_length_category": 20,
        "production_country"     : 100,
        "content_status"         : 20,
    }
    for column, limit in varchar_limits.items():
        if (df[column].str.len() > limit).any():
            raise ValueError(
                f"Validation failed: '{column}' exceeds VARCHAR({limit}) limit."
            )

    print("Validation passed: dim_content dataset is clean and schema-compliant.")

    # Print distribution summary
    print("\n--- Distribution Summary ---")
    print(f"\nTotal Content Records    : {len(df):,}")

    print("\nContent Type Distribution:")
    print(df["content_type"].value_counts(normalize=True).mul(100).round(1).to_string())

    print("\nContent Status Distribution:")
    print(df["content_status"].value_counts(normalize=True).mul(100).round(1).to_string())

    print("\nContent Length Category:")
    print(df["content_length_category"].value_counts(normalize=True).mul(100).round(1).to_string())

    print("\nTop 5 Original Languages:")
    print(df["original_language"].value_counts(normalize=True).mul(100).round(1).head(5).to_string())

    print("\nTop 5 Production Countries:")
    print(df["production_country"].value_counts(normalize=True).mul(100).round(1).head(5).to_string())

    print("\nIMDb Rating Stats:")
    print(df["imdb_rating"].describe().round(2).to_string())

    print("\nRuntime (minutes) Stats:")
    print(df["runtime_minutes"].describe().round(1).to_string())


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
    Main execution flow for generating dim_content.csv.
    """
    content_df = generate_content(TOTAL_CONTENT)
    validate_content_dataframe(content_df)
    save_dataframe_to_csv(content_df, OUTPUT_DIR, OUTPUT_FILE)


if __name__ == "__main__":
    main()