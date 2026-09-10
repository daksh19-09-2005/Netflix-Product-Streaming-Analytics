-- =============================================================
-- Netflix Product Analytics
-- analytics.sql
-- =============================================================


-- =============================================================
-- SECTION 1: USER ANALYTICS
-- =============================================================


-- -------------------------------------------------------------
-- 1. Total Users
-- KPI: Total number of registered users on the platform
-- -------------------------------------------------------------
SELECT
    COUNT(user_id) AS total_users
FROM dim_users;

-- Business Insight:
-- The total user count is the foundational metric for the platform.
-- It establishes the size of the addressable base for all downstream
-- engagement, retention, and revenue analysis.


-- -------------------------------------------------------------
-- 2. Active Users
-- KPI: Number and percentage of users with Active account status
-- -------------------------------------------------------------
SELECT
    COUNT(*) AS active_users,
    ROUND(
        COUNT(*) * 100.0 /
        (SELECT COUNT(*) FROM dim_users),
        2
    ) AS active_pct
FROM dim_users
WHERE account_status = 'Active';

-- Business Insight:
-- Active user count is the most critical health indicator for a
-- subscription platform. A declining active rate signals churn risk
-- and directly impacts Monthly Recurring Revenue (MRR).

-- -------------------------------------------------------------
-- 3. Account Status Distribution
-- KPI: Breakdown of all users by account status
-- -------------------------------------------------------------
SELECT
    account_status,
    COUNT(user_id)                                                        AS user_count,
    ROUND(COUNT(user_id) * 100.0 / SUM(COUNT(user_id)) OVER (), 2)       AS pct_of_total
FROM dim_users
GROUP BY account_status
ORDER BY user_count DESC;

-- Business Insight:
-- Understanding the distribution across Active, Cancelled, Suspended,
-- and Paused statuses helps the business prioritize win-back campaigns,
-- identify payment failure patterns, and measure overall platform health.


-- -------------------------------------------------------------
-- 4. Users by Country
-- KPI: Total registered users grouped by country
-- -------------------------------------------------------------
SELECT
    country,
    COUNT(user_id)                                                        AS user_count,
    ROUND(COUNT(user_id) * 100.0 / SUM(COUNT(user_id)) OVER (), 2)       AS pct_of_total
FROM dim_users
GROUP BY country
ORDER BY user_count DESC;

-- Business Insight:
-- Country-level user distribution informs regional content investment,
-- localisation strategy, pricing decisions, and where to focus
-- marketing spend for the highest growth potential.


-- -------------------------------------------------------------
-- 5. Users by Signup Channel
-- KPI: Number of users acquired through each signup channel
-- -------------------------------------------------------------
SELECT
    signup_channel,
    COUNT(user_id)                                                        AS user_count,
    ROUND(COUNT(user_id) * 100.0 / SUM(COUNT(user_id)) OVER (), 2)       AS pct_of_total
FROM dim_users
GROUP BY signup_channel
ORDER BY user_count DESC;

-- Business Insight:
-- Signup channel analysis reveals which acquisition sources drive the
-- most users. This guides budget allocation across channels such as
-- Website, Android, iOS, Partner Bundles, and Referrals.


-- -------------------------------------------------------------
-- 6. Users by Gender
-- KPI: Gender distribution across all registered users
-- -------------------------------------------------------------
SELECT
    gender,
    COUNT(user_id)                                                        AS user_count,
    ROUND(COUNT(user_id) * 100.0 / SUM(COUNT(user_id)) OVER (), 2)       AS pct_of_total
FROM dim_users
GROUP BY gender
ORDER BY user_count DESC;

-- Business Insight:
-- Gender distribution informs content acquisition and marketing
-- personalisation strategies. Significant skews may indicate
-- opportunities to better serve underrepresented audience segments.


-- -------------------------------------------------------------
-- 7. Age Group Distribution
-- KPI: Number of users segmented into defined age brackets
-- -------------------------------------------------------------
SELECT
    CASE
        WHEN age BETWEEN 13 AND 17 THEN '13–17'
        WHEN age BETWEEN 18 AND 24 THEN '18–24'
        WHEN age BETWEEN 25 AND 34 THEN '25–34'
        WHEN age BETWEEN 35 AND 44 THEN '35–44'
        WHEN age BETWEEN 45 AND 54 THEN '45–54'
        WHEN age >= 55             THEN '55+'
        ELSE 'Unknown'
    END                                                                   AS age_group,
    COUNT(user_id)                                                        AS user_count,
    ROUND(COUNT(user_id) * 100.0 / SUM(COUNT(user_id)) OVER (), 2)       AS pct_of_total
FROM dim_users
GROUP BY age_group
ORDER BY MIN(age);

-- Business Insight:
-- Age segmentation is essential for tailoring content recommendations,
-- UI/UX design, and targeted advertising. The 25–34 bracket is
-- typically the highest-value streaming demographic.


-- -------------------------------------------------------------
-- 8. Monthly Signup Trend
-- KPI: Number of new user registrations per month over time
-- -------------------------------------------------------------
SELECT
    TO_CHAR(DATE_TRUNC('month', signup_date), 'YYYY-MM')  AS signup_month,
    COUNT(user_id)                                         AS new_signups
FROM dim_users
GROUP BY DATE_TRUNC('month', signup_date)
ORDER BY DATE_TRUNC('month', signup_date);

-- Business Insight:
-- Monthly signup trends expose seasonality patterns, the impact of
-- marketing campaigns, and periods of organic growth or decline.
-- Spikes often correlate with content releases or promotional offers.


-- -------------------------------------------------------------
-- 9. Top 10 Countries by Users
-- KPI: The ten countries with the highest number of registered users
-- -------------------------------------------------------------
SELECT
    country,
    COUNT(user_id)                                                        AS user_count,
    ROUND(COUNT(user_id) * 100.0 / SUM(COUNT(user_id)) OVER (), 2)       AS pct_of_total
FROM dim_users
GROUP BY country
ORDER BY user_count DESC
LIMIT 10;

-- Business Insight:
-- Identifying the top 10 markets helps the business prioritise
-- infrastructure investment, content localisation, customer support
-- capacity, and region-specific subscription pricing strategies.


-- -------------------------------------------------------------
-- 10. Signup Channel Conversion Share
-- KPI: Active user rate per signup channel
--      Measures which channels bring the highest-quality users
-- -------------------------------------------------------------
SELECT
    signup_channel,
    COUNT(user_id)                                                            AS total_users,
    COUNT(user_id) FILTER (WHERE account_status = 'Active')                  AS active_users,
    ROUND(
        COUNT(user_id) FILTER (WHERE account_status = 'Active') * 100.0
        / NULLIF(COUNT(user_id), 0),
    2)                                                                        AS active_rate_pct
FROM dim_users
GROUP BY signup_channel
ORDER BY active_rate_pct DESC;

-- Business Insight:
-- Not all acquisition channels deliver equally engaged users.
-- A channel with high signups but a low active rate may indicate
-- low-quality traffic or a misaligned onboarding experience.
-- This metric helps optimise channel mix for long-term retention.