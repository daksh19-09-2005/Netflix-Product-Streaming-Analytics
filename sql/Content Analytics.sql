-- =============================================================
-- SECTION 3: CONTENT ANALYTICS
-- =============================================================


-- -------------------------------------------------------------
-- 1. Total Content
-- KPI: Total number of titles available in the content library
-- -------------------------------------------------------------
SELECT
    COUNT(content_id)   AS total_content
FROM dim_content;

-- Business Insight:
-- Total content count establishes the size of the platform's library
-- and serves as the denominator for all content performance ratios.
-- Library size is a key competitive differentiator in the streaming market.


-- -------------------------------------------------------------
-- 2. Movies vs TV Shows Distribution
-- KPI: Count and percentage split between Movies and TV Shows
-- -------------------------------------------------------------
SELECT
    content_type,
    COUNT(content_id)                                                             AS title_count,
    ROUND(COUNT(content_id) * 100.0 / SUM(COUNT(content_id)) OVER(), 2)          AS pct_of_library
FROM dim_content
GROUP BY content_type
ORDER BY title_count DESC;

-- Business Insight:
-- The Movie vs TV Show ratio reflects content investment strategy.
-- Streaming platforms with a strong TV Show catalogue benefit from
-- higher engagement and session depth due to episodic viewing behaviour,
-- which directly supports subscriber retention.


-- -------------------------------------------------------------
-- 3. Content Status Distribution
-- KPI: Breakdown of content by availability status
-- -------------------------------------------------------------
SELECT
    content_status,
    COUNT(content_id)                                                             AS title_count,
    ROUND(COUNT(content_id) * 100.0 / SUM(COUNT(content_id)) OVER(), 2)          AS pct_of_library
FROM dim_content
GROUP BY content_status
ORDER BY title_count DESC;

-- Business Insight:
-- Content status distribution reveals how much of the catalogue is
-- actively available versus removed or upcoming. A high proportion of
-- Removed content signals licensing losses that may frustrate subscribers
-- and contribute to churn if key titles are affected.


-- -------------------------------------------------------------
-- 4. Original Language Distribution
-- KPI: Number of titles per original language across the content library
-- -------------------------------------------------------------
SELECT
    original_language,
    COUNT(content_id)                                                             AS title_count,
    ROUND(COUNT(content_id) * 100.0 / SUM(COUNT(content_id)) OVER(), 2)          AS pct_of_library
FROM dim_content
GROUP BY original_language
ORDER BY title_count DESC;

-- Business Insight:
-- Language distribution reflects the platform's commitment to global
-- content diversity. Non-English language content (Korean, Hindi, Spanish)
-- has demonstrated outsized engagement in recent streaming trends and is
-- a key driver of international subscriber acquisition.


-- -------------------------------------------------------------
-- 5. Production Country Distribution
-- KPI: Number of titles produced in each country
-- -------------------------------------------------------------
SELECT
    production_country,
    COUNT(content_id)                                                             AS title_count,
    ROUND(COUNT(content_id) * 100.0 / SUM(COUNT(content_id)) OVER(), 2)          AS pct_of_library
FROM dim_content
GROUP BY production_country
ORDER BY title_count DESC;

-- Business Insight:
-- Production country analysis identifies regional content concentration
-- and geographic diversity in the library. Over-reliance on a single
-- country's content creates catalogue risk; diversification across markets
-- broadens the platform's appeal to international audiences.


-- -------------------------------------------------------------
-- 6. Genre Distribution
-- KPI: Number of content titles tagged per genre via the bridge table
-- -------------------------------------------------------------
SELECT
    g.genre_name,
    COUNT(bcg.content_id)                                                         AS title_count,
    ROUND(COUNT(bcg.content_id) * 100.0 / SUM(COUNT(bcg.content_id)) OVER(), 2) AS pct_of_assignments
FROM bridge_content_genre  bcg
JOIN dim_genres            g   ON bcg.genre_id  = g.genre_id
GROUP BY g.genre_name
ORDER BY title_count DESC;

-- Business Insight:
-- Genre distribution exposes the content mix across the catalogue.
-- Dominant genres indicate editorial priorities while underrepresented
-- genres reveal whitespace opportunities where targeted acquisitions
-- could attract new audience segments and reduce churn.


-- -------------------------------------------------------------
-- 7. Average IMDb Rating by Genre
-- KPI: Mean IMDb rating for content titles associated with each genre
-- -------------------------------------------------------------
SELECT
    g.genre_name,
    COUNT(bcg.content_id)                         AS title_count,
    ROUND(AVG(c.imdb_rating), 2)                  AS avg_imdb_rating,
    ROUND(MIN(c.imdb_rating), 1)                  AS min_imdb_rating,
    ROUND(MAX(c.imdb_rating), 1)                  AS max_imdb_rating
FROM bridge_content_genre  bcg
JOIN dim_genres            g   ON bcg.genre_id  = g.genre_id
JOIN dim_content           c   ON bcg.content_id = c.content_id
GROUP BY g.genre_name
ORDER BY avg_imdb_rating DESC;

-- Business Insight:
-- Average IMDb rating by genre signals which content categories the
-- platform executes well versus where quality lags. Genres with high
-- average ratings and high title counts represent core strengths;
-- low-rated genres with many titles may be diluting perceived quality.


-- -------------------------------------------------------------
-- 8. Top 10 Highest Rated Genres
-- KPI: The ten genres with the highest average IMDb rating
--      Filtered to genres with at least 10 titles for statistical reliability
-- -------------------------------------------------------------
SELECT
    g.genre_name,
    COUNT(bcg.content_id)              AS title_count,
    ROUND(AVG(c.imdb_rating), 2)       AS avg_imdb_rating,
    RANK() OVER (
        ORDER BY AVG(c.imdb_rating) DESC
    )                                  AS quality_rank
FROM bridge_content_genre  bcg
JOIN dim_genres            g   ON bcg.genre_id  = g.genre_id
JOIN dim_content           c   ON bcg.content_id = c.content_id
GROUP BY g.genre_name
HAVING COUNT(bcg.content_id) >= 10
ORDER BY avg_imdb_rating DESC
LIMIT 10;

-- Business Insight:
-- Ranking genres by quality (IMDb rating) helps content strategy teams
-- identify which categories deliver the strongest viewer satisfaction.
-- Investing further in high-ranking genres with proven quality track
-- records maximises the return on content acquisition spend.


-- -------------------------------------------------------------
-- 9. Maturity Rating Distribution
-- KPI: Count and share of titles per maturity rating classification
-- -------------------------------------------------------------
SELECT
    maturity_rating,
    COUNT(content_id)                                                             AS title_count,
    ROUND(COUNT(content_id) * 100.0 / SUM(COUNT(content_id)) OVER(), 2)          AS pct_of_library
FROM dim_content
GROUP BY maturity_rating
ORDER BY title_count DESC;

-- Business Insight:
-- Maturity rating distribution is essential for understanding the
-- platform's suitability across age groups. A balanced mix of family-
-- friendly (G, PG) and mature content (R, TV-MA) ensures the platform
-- serves both Kids profiles and adult subscribers effectively.


-- -------------------------------------------------------------
-- 10. Release Year Trend
-- KPI: Number of titles released per year across the content library
-- -------------------------------------------------------------
SELECT
    release_year,
    COUNT(content_id)                                                             AS title_count,
    ROUND(COUNT(content_id) * 100.0 / SUM(COUNT(content_id)) OVER(), 2)          AS pct_of_library
FROM dim_content
GROUP BY release_year
ORDER BY release_year;

-- Business Insight:
-- Release year trend reveals how much of the catalogue is recent versus
-- archival content. Platforms skewed toward older titles may struggle to
-- retain younger subscribers who prioritise new releases, making content
-- freshness a key driver of ongoing acquisition investment decisions.


-- -------------------------------------------------------------
-- 11. Content Length Distribution by Content Type
-- KPI: Breakdown of Short, Medium, and Long titles segmented by Movies and TV Shows
-- -------------------------------------------------------------
SELECT
    content_length_category,
    content_type,
    COUNT(content_id)                                                             AS title_count,
    ROUND(COUNT(content_id) * 100.0 / SUM(COUNT(content_id)) OVER(), 2)          AS pct_of_library,
    ROUND(AVG(runtime_minutes), 1)                                                AS avg_runtime_minutes
FROM dim_content
GROUP BY content_length_category, content_type
ORDER BY content_type, title_count DESC;

-- Business Insight:
-- Content length distribution informs platform UX decisions such as
-- autoplay settings, mobile download recommendations, and session
-- duration design. Short-form content drives mobile engagement while
-- Long content is better suited to lean-back Smart TV viewing sessions.


-- -------------------------------------------------------------
-- 12. Top Languages by Average IMDb Rating
-- KPI: Average IMDb rating grouped by original language
--      Filtered to languages with at least 10 titles for statistical validity
-- -------------------------------------------------------------
SELECT
    original_language,
    COUNT(content_id)                                                             AS title_count,
    ROUND(AVG(imdb_rating), 2)                                                    AS avg_imdb_rating,
    ROUND(MIN(imdb_rating), 1)                                                    AS min_imdb_rating,
    ROUND(MAX(imdb_rating), 1)                                                    AS max_imdb_rating,
    RANK() OVER (
        ORDER BY AVG(imdb_rating) DESC
    )                                                                             AS quality_rank
FROM dim_content
GROUP BY original_language
HAVING COUNT(content_id) >= 10
ORDER BY avg_imdb_rating DESC;

-- Business Insight:
-- Language-level quality ranking helps the content team identify which
-- regional productions consistently deliver higher-rated titles. Languages
-- with both high volume and strong average ratings represent proven content
-- markets where increased investment is most likely to generate positive
-- subscriber engagement outcomes.