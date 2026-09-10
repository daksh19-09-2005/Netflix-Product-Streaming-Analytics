-- =============================================================
-- SECTION 4: WATCH ANALYTICS
-- =============================================================


-- -------------------------------------------------------------
-- 1. Total Watch Records
-- KPI: Total number of watch events recorded across all users and profiles
-- -------------------------------------------------------------
SELECT
    COUNT(watch_id)   AS total_watch_records
FROM fact_watch_history;

-- Business Insight:
-- Total watch records establish the overall scale of platform engagement
-- and serve as the foundation for all content and user behaviour analysis.
-- Growth in watch records over time is a leading indicator of healthy
-- subscriber engagement and platform stickiness.


-- -------------------------------------------------------------
-- 2. Watch Status Distribution
-- KPI: Breakdown of watch events by current playback status
-- -------------------------------------------------------------
SELECT
    watch_status,
    COUNT(watch_id)                                                               AS watch_count,
    ROUND(COUNT(watch_id) * 100.0 / SUM(COUNT(watch_id)) OVER(), 2)              AS pct_of_total
FROM fact_watch_history
GROUP BY watch_status
ORDER BY watch_count DESC;

-- Business Insight:
-- Watch status distribution reveals how subscribers engage with content
-- beyond simply pressing play. High Abandoned or Paused rates signal
-- content quality issues or poor recommendation accuracy, both of which
-- directly suppress session depth and retention metrics.


-- -------------------------------------------------------------
-- 3. Overall Watch Completion Rate
-- KPI: Percentage of watch events where the content was fully completed
-- -------------------------------------------------------------
SELECT
    COUNT(watch_id)                                                               AS total_watch_events,
    COUNT(watch_id) FILTER (WHERE is_completed = TRUE)                            AS completed_watches,
    ROUND(
        COUNT(watch_id) FILTER (WHERE is_completed = TRUE) * 100.0
        / NULLIF(COUNT(watch_id), 0),
    2)                                                                            AS completion_rate_pct,
    ROUND(AVG(percentage_completed), 2)                                           AS avg_percentage_watched
FROM fact_watch_history;

-- Business Insight:
-- Completion rate is one of the strongest signals of content quality and
-- audience-content fit. A low overall completion rate suggests the platform
-- is surfacing titles that fail to hold viewer attention, indicating a need
-- to improve the recommendation engine or content acquisition criteria.


-- -------------------------------------------------------------
-- 4. Downloaded vs Streamed Content
-- KPI: Split between downloaded and streamed watch events
-- -------------------------------------------------------------
SELECT
    CASE
        WHEN is_downloaded = TRUE  THEN 'Downloaded'
        WHEN is_downloaded = FALSE THEN 'Streamed'
    END                                                                           AS delivery_method,
    COUNT(watch_id)                                                               AS watch_count,
    ROUND(COUNT(watch_id) * 100.0 / SUM(COUNT(watch_id)) OVER(), 2)              AS pct_of_total,
    ROUND(AVG(watch_duration_min), 2)                                             AS avg_duration_min,
    ROUND(AVG(percentage_completed), 2)                                           AS avg_completion_pct
FROM fact_watch_history
GROUP BY is_downloaded
ORDER BY watch_count DESC;

-- Business Insight:
-- Comparing download versus stream behaviour reveals offline usage patterns
-- critical for mobile product decisions. Higher completion rates on downloads
-- suggest that offline viewing delivers a better experience, reinforcing the
-- value of download features in subscriber retention for mobile-heavy markets.


-- -------------------------------------------------------------
-- 5. Average Watch Duration
-- KPI: Mean watch duration in minutes across all watch events,
--      segmented by content type
-- -------------------------------------------------------------
SELECT
    c.content_type,
    COUNT(wh.watch_id)                        AS watch_events,
    ROUND(AVG(wh.watch_duration_min), 2)      AS avg_duration_min,
    ROUND(MIN(wh.watch_duration_min), 2)      AS min_duration_min,
    ROUND(MAX(wh.watch_duration_min), 2)      AS max_duration_min
FROM fact_watch_history  wh
JOIN dim_content         c  ON wh.content_id = c.content_id
GROUP BY c.content_type
ORDER BY avg_duration_min DESC;

-- Business Insight:
-- Average watch duration segmented by content type informs session design
-- and autoplay timing decisions. TV Shows typically drive longer sessions
-- than Movies; a shrinking average duration across either category signals
-- declining engagement that warrants immediate investigation.


-- -------------------------------------------------------------
-- 6. Peak Viewing Hours
-- KPI: Distribution of watch events grouped into business-friendly time windows
-- -------------------------------------------------------------
SELECT
    CASE
        WHEN EXTRACT(HOUR FROM watch_start_time) >= 6
         AND EXTRACT(HOUR FROM watch_start_time) < 12  THEN '06 AM – 12 PM'
        WHEN EXTRACT(HOUR FROM watch_start_time) >= 12
         AND EXTRACT(HOUR FROM watch_start_time) < 18  THEN '12 PM – 06 PM'
        WHEN EXTRACT(HOUR FROM watch_start_time) >= 18
         AND EXTRACT(HOUR FROM watch_start_time) < 22  THEN '06 PM – 10 PM'
        WHEN EXTRACT(HOUR FROM watch_start_time) >= 22
          OR EXTRACT(HOUR FROM watch_start_time) < 1   THEN '10 PM – 01 AM'
        ELSE                                                 '01 AM – 06 AM'
    END                                                                           AS time_window,
    COUNT(watch_id)                                                               AS watch_events,
    ROUND(COUNT(watch_id) * 100.0 / SUM(COUNT(watch_id)) OVER(), 2)              AS pct_of_total
FROM fact_watch_history
GROUP BY time_window
ORDER BY watch_events DESC;

-- Business Insight:
-- Peak viewing hour analysis identifies when subscribers are most active
-- on the platform. This drives decisions around content release scheduling,
-- infrastructure scaling to handle peak traffic, and the optimal timing
-- for push notifications and promotional campaigns.


-- -------------------------------------------------------------
-- 7. Device Usage Distribution
-- KPI: Number of watch events per device type and brand
-- -------------------------------------------------------------
SSELECT
    d.device_type,
    COUNT(wh.watch_id) AS watch_events,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS pct_of_total,
    ROUND(AVG(wh.watch_duration_min), 2) AS avg_duration_min,
    ROUND(AVG(wh.percentage_completed), 2) AS avg_completion_pct
FROM fact_watch_history wh
JOIN dim_devices d
    ON wh.device_id = d.device_id
GROUP BY d.device_type
ORDER BY watch_events DESC;

-- Business Insight:
-- Device usage distribution shapes platform engineering and UX priorities.
-- Smart TV dominance in session duration justifies investment in the lean-back
-- experience, while high mobile usage volumes drive decisions around adaptive
-- bitrate streaming, download features, and screen-size optimised interfaces.


-- -------------------------------------------------------------
-- 8. Most Watched Genres
-- KPI: Total watch events and average completion rate per genre
--      using the bridge table for accurate multi-genre content mapping
-- -------------------------------------------------------------
SELECT
    g.genre_name,
    COUNT(wh.watch_id)                                                            AS watch_events,
    ROUND(COUNT(wh.watch_id) * 100.0 / SUM(COUNT(wh.watch_id)) OVER(), 2)        AS pct_of_total,
    ROUND(AVG(wh.percentage_completed), 2)                                        AS avg_completion_pct,
    ROUND(AVG(wh.watch_duration_min), 2)                                          AS avg_duration_min
FROM fact_watch_history    wh
JOIN bridge_content_genre  bcg ON wh.content_id  = bcg.content_id
JOIN dim_genres            g   ON bcg.genre_id   = g.genre_id
GROUP BY g.genre_name
ORDER BY watch_events DESC;

-- Business Insight:
-- Genre-level watch volume reveals true audience demand beyond what the
-- content catalogue size implies. Genres with high watch events but low
-- catalogue representation signal unmet demand where targeted content
-- acquisition would directly convert to measurable engagement uplift.


-- -------------------------------------------------------------
-- 9. Top 10 Most Watched Titles
-- KPI: Content titles ranked by total number of watch events
-- -------------------------------------------------------------
SELECT
    c.content_id,
    c.title,
    c.content_type,
    c.imdb_rating,
    COUNT(wh.watch_id)                                                            AS watch_events,
    ROUND(AVG(wh.percentage_completed), 2)                                        AS avg_completion_pct,
    ROUND(AVG(wh.watch_duration_min), 2)                                          AS avg_duration_min,
    RANK() OVER (ORDER BY COUNT(wh.watch_id) DESC)                                AS popularity_rank
FROM fact_watch_history  wh
JOIN dim_content         c   ON wh.content_id = c.content_id
GROUP BY
    c.content_id,
    c.title,
    c.content_type,
    c.imdb_rating
ORDER BY watch_events DESC
LIMIT 10;

-- Business Insight:
-- The top 10 most watched titles represent the platform's highest-value
-- content assets. These titles should be prioritised in homepage placements,
-- marketing campaigns, and licence renewal negotiations. A mismatch between
-- high watch volume and low IMDb rating may suggest algorithmic over-promotion.


-- -------------------------------------------------------------
-- 10. Watch Activity by Day of Week
-- KPI: Total watch events distributed across each day of the week
-- -------------------------------------------------------------
SELECT
    TRIM(TO_CHAR(watch_date, 'Day'))                                              AS day_of_week,
    EXTRACT(DOW FROM watch_date)                                                  AS day_number,
    COUNT(watch_id)                                                               AS watch_events,
    ROUND(COUNT(watch_id) * 100.0 / SUM(COUNT(watch_id)) OVER(), 2)              AS pct_of_total,
    ROUND(AVG(watch_duration_min), 2)                                             AS avg_duration_min
FROM fact_watch_history
GROUP BY TRIM(TO_CHAR(watch_date, 'Day')), EXTRACT(DOW FROM watch_date)
ORDER BY day_number;

-- Business Insight:
-- Day-of-week activity patterns expose the weekend binge effect common in
-- streaming platforms. Friday through Sunday typically account for a
-- disproportionate share of total watch volume, informing the optimal
-- timing for new content releases to maximise opening weekend engagement.


-- -------------------------------------------------------------
-- 11. Top 10 Most Active Profiles
-- KPI: Profiles ranked by total watch events and cumulative watch time
-- -------------------------------------------------------------
SELECT
    p.profile_id,
    p.profile_name,
    p.profile_type,
    p.preferred_language,
    COUNT(wh.watch_id)                                                            AS total_watch_events,
    ROUND(SUM(wh.watch_duration_min), 0)                                          AS total_watch_minutes,
    ROUND(AVG(wh.percentage_completed), 2)                                        AS avg_completion_pct,
    RANK() OVER (ORDER BY COUNT(wh.watch_id) DESC)                                AS activity_rank
FROM fact_watch_history  wh
JOIN dim_profiles        p   ON wh.profile_id = p.profile_id
GROUP BY
    p.profile_id,
    p.profile_name,
    p.profile_type,
    p.preferred_language
ORDER BY total_watch_events DESC
LIMIT 10;

-- Business Insight:
-- Identifying the most active profiles highlights power users whose
-- engagement patterns represent the ideal subscriber behaviour the platform
-- should aim to cultivate broadly. Understanding their content preferences
-- and viewing habits provides a blueprint for personalisation strategies
-- that can lift engagement across the wider subscriber base.


-- -------------------------------------------------------------
-- 12. Average Completion Rate by Genre
-- KPI: Mean percentage of content watched per genre
--      using the bridge table for accurate multi-genre mapping
-- -------------------------------------------------------------
SELECT
    g.genre_name,
    COUNT(wh.watch_id)                                                            AS watch_events,
    ROUND(AVG(wh.percentage_completed), 2)                                        AS avg_completion_pct,
    ROUND(AVG(wh.watch_duration_min), 2)                                          AS avg_duration_min,
    RANK() OVER (ORDER BY AVG(wh.percentage_completed) DESC)                      AS completion_rank
FROM fact_watch_history    wh
JOIN bridge_content_genre  bcg ON wh.content_id = bcg.content_id
JOIN dim_genres            g   ON bcg.genre_id  = g.genre_id
GROUP BY g.genre_name
ORDER BY avg_completion_pct DESC;

-- Business Insight:
-- Completion rate by genre is a more reliable quality signal than watch
-- volume alone, as it measures sustained engagement rather than just
-- initial clicks. Genres with high completion rates validate content
-- investment decisions, while low-completion genres with high entry volumes
-- indicate a discovery-experience mismatch that warrants content or UX review.