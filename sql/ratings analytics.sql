-- =============================================================================
-- NETFLIX PRODUCT ANALYTICS
-- SECTION 5: RATINGS ANALYTICS
-- =============================================================================
-- Database   : PostgreSQL
-- Audience   : Executive / Product Analytics Stakeholders
-- Source     : fact_ratings, fact_watch_history, dim_users, dim_profiles,
--              dim_content, bridge_content_genre, dim_genres
-- Purpose    : Understand rating volume, rating quality, engagement with
--              reviews, and how user sentiment compares against IMDb scores.
-- =============================================================================


-- =============================================================================
-- QUERY 1: TOTAL RATINGS (EXECUTIVE KPI)
-- -----------------------------------------------------------------------------
-- KPI Description:
--   Headline volume metric for the ratings ecosystem -- total ratings
--   submitted, and the unique reach across users, profiles, and titles.
-- =============================================================================
SELECT
    COUNT(*)                                   AS total_ratings,
    COUNT(DISTINCT r.user_id)                  AS unique_users_rated,
    COUNT(DISTINCT r.profile_id)               AS unique_profiles_rated,
    COUNT(DISTINCT r.content_id)               AS unique_titles_rated
FROM fact_ratings r;

-- Business Insight:
-- This KPI anchors the health of the ratings feature as a feedback channel.
-- A large gap between unique_profiles_rated and unique_users_rated signals
-- that ratings are concentrated in specific profiles within a household
-- (e.g. one household member rates frequently while others never do). A low
-- ratio of unique_titles_rated to the overall catalog size indicates that
-- rating activity is highly concentrated on a small slice of content,
-- which should be factored into how confidently rating-based signals are
-- used for recommendations or content investment decisions.


-- =============================================================================
-- QUERY 2: RATING DISTRIBUTION
-- -----------------------------------------------------------------------------
-- KPI Description:
--   Distribution of ratings across the 1-5 star scale, both in absolute
--   count and as a percentage of total ratings submitted.
-- =============================================================================
SELECT
    r.rating_value                                                     AS star_rating,
    COUNT(*)                                                           AS rating_count,
    ROUND(
        100.0 * COUNT(*) / NULLIF(SUM(COUNT(*)) OVER (), 0),
        2
    )                                                                   AS pct_of_total_ratings
FROM fact_ratings r
GROUP BY r.rating_value
ORDER BY r.rating_value DESC;

-- Business Insight:
-- A distribution skewed heavily toward 4-5 stars is typical of engaged
-- streaming audiences who self-select content they expect to enjoy, and
-- generally reflects healthy content-discovery and recommendation quality.
-- A meaningful share of 1-2 star ratings warrants investigation into
-- content quality, mismatched expectations from marketing/thumbnails, or
-- technical playback issues, since low ratings are a leading indicator of
-- churn risk for the profiles submitting them.


-- =============================================================================
-- QUERY 3: OVERALL RATING KPIs
-- -----------------------------------------------------------------------------
-- KPI Description:
--   Summary statistics on rating values across the entire ratings dataset,
--   including the median rating computed via PERCENTILE_CONT.
-- =============================================================================
SELECT
    ROUND(AVG(r.rating_value), 2)                                      AS average_rating,
    MIN(r.rating_value)                                                AS minimum_rating,
    MAX(r.rating_value)                                                AS maximum_rating,
    ROUND(
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY r.rating_value)::numeric,
        2
    )                                                                   AS median_rating
FROM fact_ratings r;

-- Business Insight:
-- The average and median ratings should be viewed together: a median that
-- sits notably above the average suggests a long tail of low outlier
-- ratings dragging the mean down, while the reverse suggests a smaller
-- group of extremely enthusiastic raters inflating the average. Tracking
-- this pair over time is a more reliable satisfaction signal than the
-- average alone, since streaming rating scales are typically not normally
-- distributed.


-- =============================================================================
-- QUERY 4: RATINGS BY CONTENT TYPE
-- -----------------------------------------------------------------------------
-- KPI Description:
--   Compares rating volume, average rating, and review-attachment rate
--   between Movies and TV Shows (Series), highlighting engagement
--   differences by content format.
-- =============================================================================
SELECT
    c.content_type,
    COUNT(*)                                                           AS rating_count,
    ROUND(AVG(r.rating_value), 2)                                      AS average_rating,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE r.review_text IS NOT NULL) / NULLIF(COUNT(*), 0),
        2
    )                                                                   AS review_pct
FROM fact_ratings r
JOIN dim_content c
    ON c.content_id = r.content_id
GROUP BY c.content_type
ORDER BY rating_count DESC;

-- Business Insight:
-- Content types with a higher review-attachment rate indicate viewers are
-- more motivated to articulate their opinion -- often a marker of stronger
-- emotional engagement (positive or negative) than a bare star rating
-- alone. If TV Shows carry a materially higher average rating than Movies,
-- this supports continued investment in serialized content, since ongoing
-- engagement across episodes appears to correlate with higher satisfaction.


-- =============================================================================
-- QUERY 5: TOP RATED GENRES
-- -----------------------------------------------------------------------------
-- KPI Description:
--   Ranks genres by average rating (minimum volume threshold applied) to
--   surface which genres resonate most with the audience.
-- =============================================================================
WITH genre_ratings AS (
    SELECT
        g.genre_name,
        r.rating_value
    FROM fact_ratings r
    JOIN bridge_content_genre bcg
        ON bcg.content_id = r.content_id
    JOIN dim_genres g
        ON g.genre_id = bcg.genre_id
),
genre_summary AS (
    SELECT
        genre_name,
        COUNT(*)                       AS rating_count,
        ROUND(AVG(rating_value), 2)    AS average_rating
    FROM genre_ratings
    GROUP BY genre_name
    HAVING COUNT(*) >= 30
)
SELECT
    genre_name,
    rating_count,
    average_rating,
    RANK() OVER (ORDER BY average_rating DESC, rating_count DESC) AS genre_rank
FROM genre_summary
ORDER BY genre_rank;

-- Business Insight:
-- Genres ranking at the top with sufficient rating volume represent the
-- strongest candidates for content-acquisition and original-production
-- investment, as they combine both audience reach and satisfaction. The
-- minimum-volume filter (30+ ratings) protects against small-sample noise
-- inflating niche genres to the top of the ranking, ensuring the insight
-- is statistically meaningful rather than an artifact of low sample size.


-- =============================================================================
-- QUERY 6: TOP RATED TITLES
-- -----------------------------------------------------------------------------
-- KPI Description:
--   Surfaces the top 10 highest-rated titles by average user rating
--   (minimum volume threshold applied), alongside their IMDb rating for
--   external benchmarking.
-- =============================================================================
WITH title_ratings AS (
    SELECT
        c.content_id,
        c.title,
        c.content_type,
        c.imdb_rating,
        r.rating_value
    FROM fact_ratings r
    JOIN dim_content c
        ON c.content_id = r.content_id
),
title_summary AS (
    SELECT
        content_id,
        title,
        content_type,
        imdb_rating,
        COUNT(*)                       AS rating_count,
        ROUND(AVG(rating_value), 2)    AS avg_user_rating
    FROM title_ratings
    GROUP BY content_id, title, content_type, imdb_rating
    HAVING COUNT(*) >= 10
)
SELECT
    title,
    content_type,
    imdb_rating,
    avg_user_rating,
    rating_count,
    RANK() OVER (ORDER BY avg_user_rating DESC, rating_count DESC) AS title_rank
FROM title_summary
ORDER BY title_rank
LIMIT 10;

-- Business Insight:
-- These titles are the platform's strongest performers by direct user
-- sentiment and should anchor homepage merchandising, "Top 10" rows, and
-- renewal/sequel decisions. Comparing avg_user_rating against imdb_rating
-- for each title highlights whether the platform's own audience skews
-- more or less favorable than the general public -- a useful signal for
-- how well content curation matches the existing subscriber base's taste.


-- =============================================================================
-- QUERY 7: RATINGS BY PROFILE TYPE
-- -----------------------------------------------------------------------------
-- KPI Description:
--   Breaks down rating volume and average rating across Adult and Kids
--   profiles to understand rating behaviour by audience segment.
-- =============================================================================

SELECT
    p.profile_type AS profile_segment,
    COUNT(*) AS rating_count,
    ROUND(AVG(r.rating_value), 2) AS average_rating,
    ROUND(
        100.0 * COUNT(*) / SUM(COUNT(*)) OVER (),
        2
    ) AS pct_of_total_ratings
FROM fact_ratings r
JOIN dim_profiles p
    ON p.profile_id = r.profile_id
GROUP BY p.profile_type
ORDER BY rating_count DESC;

-- Business Insight:
-- Adult profiles are expected to contribute the majority of ratings,
-- reflecting higher engagement with the rating feature. Kids profiles
-- generally generate fewer ratings, making their average rating more
-- sensitive to changes in viewing behaviour.


-- =============================================================================
-- QUERY 8: RATINGS BY COUNTRY
-- -----------------------------------------------------------------------------
-- KPI Description:
--   Identifies the top 10 countries by rating volume and their average
--   rating, highlighting regional engagement and sentiment differences.
-- =============================================================================
SELECT
    u.country,
    COUNT(*)                                                           AS rating_count,
    ROUND(AVG(r.rating_value), 2)                                      AS average_rating
FROM fact_ratings r
JOIN dim_users u
    ON u.user_id = r.user_id
GROUP BY u.country
ORDER BY rating_count DESC
LIMIT 10;

-- Business Insight:
-- Countries combining high rating_count with high average_rating represent
-- markets with both strong engagement and strong satisfaction, making them
-- priority markets for continued content-localization investment. A
-- country with high volume but comparatively low average rating deserves
-- a deeper look into local content fit, dubbing/subtitling quality, or
-- regional catalog gaps.


-- =============================================================================
-- QUERY 9: REVIEWS VS NO REVIEWS
-- -----------------------------------------------------------------------------
-- KPI Description:
--   Measures what share of ratings are accompanied by written review text
--   versus a star rating alone.
-- =============================================================================
SELECT
    CASE
        WHEN r.review_text IS NOT NULL THEN 'Review'
        ELSE 'No Review'
    END                                                                 AS review_segment,
    COUNT(*)                                                           AS rating_count,
    ROUND(
        100.0 * COUNT(*) / NULLIF(SUM(COUNT(*)) OVER (), 0),
        2
    )                                                                   AS pct_of_total_ratings
FROM fact_ratings r
GROUP BY review_segment
ORDER BY rating_count DESC;

-- Business Insight:
-- Written reviews are a richer, higher-effort engagement signal than a
-- star rating alone and are disproportionately valuable for qualitative
-- product feedback and NLP-driven sentiment analysis. Tracking this ratio
-- over time helps evaluate whether UI/UX changes to the rating flow (e.g.
-- prompting for a review after a completed binge) are successfully
-- increasing the depth of user feedback rather than just its volume.


-- =============================================================================
-- QUERY 10: MONTHLY RATING TREND
-- -----------------------------------------------------------------------------
-- KPI Description:
--   Tracks ratings volume and average rating by calendar month, revealing
--   seasonality and shifts in sentiment over time.
-- =============================================================================
SELECT
    TO_CHAR(DATE_TRUNC('month', r.rating_date), 'YYYY-MM')             AS rating_month,
    COUNT(*)                                                           AS rating_count,
    ROUND(AVG(r.rating_value), 2)                                      AS average_rating
FROM fact_ratings r
GROUP BY DATE_TRUNC('month', r.rating_date)
ORDER BY DATE_TRUNC('month', r.rating_date);

-- Business Insight:
-- Sustained month-over-month growth in rating_count signals healthy,
-- compounding engagement with the ratings feature, while a declining
-- average_rating trend alongside stable or growing volume is an early
-- warning sign of catalog fatigue or a content-quality slump that
-- deserves cross-referencing against new release schedules for the
-- corresponding months.


-- =============================================================================
-- QUERY 11: IMDb RATING VS USER RATING
-- -----------------------------------------------------------------------------
-- KPI Description:
--   Compares each title's average platform user rating against its IMDb
--   rating to surface where subscriber sentiment most diverges from
--   general public opinion.
-- =============================================================================
WITH title_comparison AS (
    SELECT
        c.content_id,
        c.title,
        c.imdb_rating,
        ROUND(AVG(r.rating_value), 2)  AS avg_user_rating,
        COUNT(*)                       AS rating_count
    FROM fact_ratings r
    JOIN dim_content c
        ON c.content_id = r.content_id
    GROUP BY c.content_id, c.title, c.imdb_rating
    HAVING COUNT(*) >= 10
)
SELECT
    title,
    imdb_rating,
    avg_user_rating,
    ROUND(avg_user_rating - imdb_rating, 2)                            AS rating_difference,
    RANK() OVER (ORDER BY (avg_user_rating - imdb_rating) DESC)        AS overperformance_rank
FROM title_comparison
ORDER BY rating_difference DESC
LIMIT 10;

-- Business Insight:
-- Titles where avg_user_rating substantially exceeds imdb_rating indicate
-- content that resonates unusually well with this platform's specific
-- subscriber base relative to the general public -- strong candidates for
-- increased promotion since they may be under-marketed relative to their
-- true audience fit. Conversely, titles with a large negative difference
-- suggest a mismatch between platform expectations (set by thumbnails,
-- categorization, or promotion) and delivered viewer experience.


-- =============================================================================
-- QUERY 12: EXECUTIVE RATING DASHBOARD
-- -----------------------------------------------------------------------------
-- KPI Description:
--   Single-row consolidated view of the platform's ratings health,
--   combining volume, sentiment, review depth, and reach metrics for
--   executive reporting.
-- =============================================================================
SELECT
    COUNT(*)                                                           AS total_ratings,
    ROUND(AVG(r.rating_value), 2)                                      AS average_rating,
    COUNT(*) FILTER (WHERE r.review_text IS NOT NULL)                  AS review_count,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE r.review_text IS NOT NULL) / NULLIF(COUNT(*), 0),
        2
    )                                                                   AS review_pct,
    COUNT(DISTINCT r.user_id)                                          AS unique_rated_users,
    COUNT(DISTINCT r.profile_id)                                       AS unique_rated_profiles,
    COUNT(DISTINCT r.content_id)                                       AS unique_rated_titles,
    ROUND(
        COUNT(*)::numeric / NULLIF(COUNT(DISTINCT r.user_id), 0),
        2
    )                                                                   AS avg_ratings_per_user
FROM fact_ratings r;

-- Business Insight:
-- This dashboard row is the single reference point for leadership on
-- ratings-feature health: average_rating tracks overall sentiment,
-- review_pct tracks feedback depth, and avg_ratings_per_user tracks how
-- habitual the rating behavior is among engaged users. Sustained growth
-- across unique_rated_users and unique_rated_titles alongside a stable or
-- improving average_rating indicates the ratings feature is scaling
-- healthily in parallel with the broader subscriber base rather than
-- being driven by a small, saturated group of power users.