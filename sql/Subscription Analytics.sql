-- =============================================================
-- SECTION 2: SUBSCRIPTION ANALYTICS
-- =============================================================


-- -------------------------------------------------------------
-- 1. Total Subscriptions
-- KPI: Total number of subscriptions ever created on the platform
-- -------------------------------------------------------------
SELECT
    COUNT(subscription_id)  AS total_subscriptions
FROM fact_subscriptions;

-- Business Insight:
-- Total subscription count establishes the full scope of the platform's
-- commercial relationships. Compared against total users, it reveals
-- the subscription attachment rate and untapped monetisation potential.


-- -------------------------------------------------------------
-- 2. Subscription Status Distribution
-- KPI: Breakdown of subscriptions by current status
-- -------------------------------------------------------------
SELECT
    status,
    COUNT(subscription_id)                                                            AS subscription_count,
    ROUND(COUNT(subscription_id) * 100.0 / SUM(COUNT(subscription_id)) OVER(), 2)   AS pct_of_total
FROM fact_subscriptions
GROUP BY status
ORDER BY subscription_count DESC;

-- Business Insight:
-- Status distribution provides an instant snapshot of platform health.
-- A growing share of Cancelled or Paused subscriptions is an early
-- warning signal for revenue leakage and requires immediate retention action.


-- -------------------------------------------------------------
-- 3. Subscription Plan Distribution
-- KPI: Number of subscribers and revenue share per plan tier
-- -------------------------------------------------------------
SELECT
    sp.plan_name,
    sp.plan_tier,
    sp.monthly_price,
    COUNT(fs.subscription_id)                                                             AS subscriber_count,
    ROUND(COUNT(fs.subscription_id) * 100.0 / SUM(COUNT(fs.subscription_id)) OVER(), 2) AS pct_of_subscribers
FROM fact_subscriptions    fs
JOIN dim_subscription_plans sp ON fs.plan_id = sp.plan_id
GROUP BY sp.plan_name, sp.plan_tier, sp.monthly_price
ORDER BY sp.monthly_price DESC;

-- Business Insight:
-- Plan distribution shows how subscribers are spread across price tiers.
-- A high concentration in lower-tier plans suppresses ARPU (Average Revenue
-- Per User) and signals an opportunity to drive upsell campaigns to Standard
-- and Premium tiers.


-- -------------------------------------------------------------
-- 4. Trial Users Percentage
-- KPI: Proportion of all subscribers who started as trial users
-- -------------------------------------------------------------
SELECT
    COUNT(subscription_id)                                                        AS total_subscriptions,
    COUNT(subscription_id) FILTER (WHERE trial_user = TRUE)                       AS trial_users,
    ROUND(
        COUNT(subscription_id) FILTER (WHERE trial_user = TRUE) * 100.0
        / NULLIF(COUNT(subscription_id), 0),
    2)                                                                            AS trial_user_pct
FROM fact_subscriptions;

-- Business Insight:
-- Tracking trial user proportion helps evaluate the effectiveness of the
-- free-trial acquisition strategy. High trial rates with low conversion
-- indicate friction in the trial-to-paid journey and signal the need
-- for onboarding or product experience improvements.


-- -------------------------------------------------------------
-- 5. Trial User Retention Rate
-- KPI: Percentage of trial users whose subscription is currently Active,
--      indicating they were retained on the platform after their trial period.
--      Calculated as: Active Trial Users / Total Trial Users × 100
-- -------------------------------------------------------------
SELECT
    COUNT(subscription_id) FILTER (WHERE trial_user = TRUE)                       AS total_trial_users,
    COUNT(subscription_id) FILTER (WHERE trial_user = TRUE AND status = 'Active') AS active_trial_users,
    ROUND(
        COUNT(subscription_id) FILTER (WHERE trial_user = TRUE AND status = 'Active') * 100.0
        / NULLIF(COUNT(subscription_id) FILTER (WHERE trial_user = TRUE), 0),
    2)                                                                            AS trial_retention_rate_pct
FROM fact_subscriptions;

-- Business Insight:
-- Trial user retention rate measures how many users who started on a trial
-- are still active on the platform. Since the schema captures current status
-- rather than a historical upgrade event, this metric serves as a reliable
-- proxy for trial programme effectiveness. A low retention rate among trial
-- users signals a need to improve the onboarding experience or perceived
-- product value during the trial window.


-- -------------------------------------------------------------
-- 6. Auto-Renew Rate
-- KPI: Percentage of active subscriptions with auto-renewal enabled
-- -------------------------------------------------------------
SELECT
    COUNT(subscription_id)                                                        AS active_subscriptions,
    COUNT(subscription_id) FILTER (WHERE auto_renew = TRUE)                       AS auto_renew_enabled,
    ROUND(
        COUNT(subscription_id) FILTER (WHERE auto_renew = TRUE) * 100.0
        / NULLIF(COUNT(subscription_id), 0),
    2)                                                                            AS auto_renew_rate_pct
FROM fact_subscriptions
WHERE status = 'Active';

-- Business Insight:
-- Auto-renew rate is a leading indicator of future revenue predictability.
-- A high auto-renew rate stabilises MRR forecasting and reduces involuntary
-- churn caused by payment failures or forgotten renewals.


-- -------------------------------------------------------------
-- 7. Monthly Recurring Revenue (MRR)
-- KPI: Total recurring revenue generated by all active subscriptions per month
-- -------------------------------------------------------------
SELECT
    ROUND(SUM(sp.monthly_price), 2)   AS mrr
FROM fact_subscriptions    fs
JOIN dim_subscription_plans sp ON fs.plan_id = sp.plan_id
WHERE fs.status = 'Active';

-- Business Insight:
-- MRR is the single most important financial metric for any subscription
-- business. It provides a normalised view of predictable monthly revenue
-- and serves as the baseline for growth rate calculations, investor
-- reporting, and financial forecasting.


-- -------------------------------------------------------------
-- 8. Annual Recurring Revenue (ARR)
-- KPI: Projected annual revenue based on current active subscriptions
--      ARR = MRR × 12
-- -------------------------------------------------------------
SELECT
    ROUND(SUM(sp.monthly_price), 2)         AS mrr,
    ROUND(SUM(sp.monthly_price) * 12, 2)    AS arr
FROM fact_subscriptions    fs
JOIN dim_subscription_plans sp ON fs.plan_id = sp.plan_id
WHERE fs.status = 'Active';

-- Business Insight:
-- ARR translates the monthly revenue snapshot into an annualised figure
-- used for strategic planning, valuation, and fundraising conversations.
-- It provides the business with a long-range view of revenue trajectory
-- assuming no change in the current subscriber base.


-- -------------------------------------------------------------
-- 9. Revenue by Subscription Plan
-- KPI: MRR and subscriber count broken down by each plan tier
-- -------------------------------------------------------------
SELECT
    sp.plan_name,
    sp.plan_tier,
    sp.monthly_price,
    COUNT(fs.subscription_id)                                                             AS active_subscribers,
    ROUND(SUM(sp.monthly_price), 2)                                                       AS plan_mrr,
    ROUND(SUM(sp.monthly_price) * 100.0 / SUM(SUM(sp.monthly_price)) OVER(), 2)          AS pct_of_total_mrr
FROM fact_subscriptions    fs
JOIN dim_subscription_plans sp ON fs.plan_id = sp.plan_id
WHERE fs.status = 'Active'
GROUP BY sp.plan_name, sp.plan_tier, sp.monthly_price
ORDER BY plan_mrr DESC;

-- Business Insight:
-- Revenue breakdown by plan reveals which tiers are the primary MRR
-- drivers. Premium plans typically contribute disproportionately to
-- total revenue despite lower subscriber counts, reinforcing the
-- business case for upsell programmes targeting Basic plan subscribers.


-- -------------------------------------------------------------
-- 10. Subscription Source Distribution
-- KPI: Number and percentage of subscriptions acquired per source channel
-- -------------------------------------------------------------
SELECT
    subscription_source,
    COUNT(subscription_id)                                                            AS subscription_count,
    ROUND(COUNT(subscription_id) * 100.0 / SUM(COUNT(subscription_id)) OVER(), 2)   AS pct_of_total,
    COUNT(subscription_id) FILTER (WHERE status = 'Active')                          AS active_count,
    ROUND(
        COUNT(subscription_id) FILTER (WHERE status = 'Active') * 100.0
        / NULLIF(COUNT(subscription_id), 0),
    2)                                                                                AS active_rate_pct
FROM fact_subscriptions
GROUP BY subscription_source
ORDER BY subscription_count DESC;

-- Business Insight:
-- Subscription source analysis connects acquisition channels directly to
-- commercial outcomes. Sources with a high active_rate_pct deliver
-- higher-quality subscribers, enabling smarter budget allocation toward
-- channels that generate retained, revenue-generating customers.


-- -------------------------------------------------------------
-- 11. Cancellation Reason Analysis
-- KPI: Frequency of each cancellation reason among cancelled subscriptions
-- -------------------------------------------------------------
SELECT
    cancellation_reason,
    COUNT(subscription_id)                                                            AS cancellation_count,
    ROUND(COUNT(subscription_id) * 100.0 / SUM(COUNT(subscription_id)) OVER(), 2)   AS pct_of_cancellations
FROM fact_subscriptions
WHERE status            = 'Cancelled'
  AND cancellation_reason IS NOT NULL
GROUP BY cancellation_reason
ORDER BY cancellation_count DESC;

-- Business Insight:
-- Cancellation reason analysis transforms churn data into actionable
-- product intelligence. Price sensitivity, content gaps, and competitive
-- losses each demand different retention strategies — this query identifies
-- which levers will have the highest impact on reducing churn.


-- -------------------------------------------------------------
-- 12. Average Subscription Tenure (Months)
-- KPI: Average duration of subscriptions in months per status group
--      Uses end_date for inactive subscriptions or CURRENT_DATE for active ones
-- -------------------------------------------------------------
SELECT
    status,
    COUNT(subscription_id)                                                AS subscription_count,
    ROUND(
        AVG(
            EXTRACT(YEAR FROM AGE(
                COALESCE(end_date, CURRENT_DATE),
                start_date
            )) * 12
            +
            EXTRACT(MONTH FROM AGE(
                COALESCE(end_date, CURRENT_DATE),
                start_date
            ))
        ),
    2)                                                                    AS avg_tenure_months
FROM fact_subscriptions
GROUP BY status
ORDER BY avg_tenure_months DESC;

-- Business Insight:
-- Average tenure measures customer loyalty and the lifetime value
-- potential of each subscriber cohort. A short average tenure for
-- cancelled subscribers highlights a retention window the business
-- should target with proactive intervention before the cancellation
-- decision is made.


-- -------------------------------------------------------------
-- 13. Churn Rate
-- KPI: Percentage of total subscriptions that have been cancelled
--      Churn Rate = Cancelled Subscriptions / Total Subscriptions × 100
-- -------------------------------------------------------------
SELECT
    COUNT(subscription_id)                                                            AS total_subscriptions,
    COUNT(subscription_id) FILTER (WHERE status = 'Cancelled')                       AS cancelled_subscriptions,
    ROUND(
        COUNT(subscription_id) FILTER (WHERE status = 'Cancelled') * 100.0
        / NULLIF(COUNT(subscription_id), 0),
    2)                                                                                AS churn_rate_pct
FROM fact_subscriptions;

-- Business Insight:
-- Churn rate is the inverse of retention and one of the most scrutinised
-- metrics in subscription analytics. Even a 1% reduction in monthly churn
-- compounded over 12 months can significantly increase LTV across the
-- subscriber base and reduce the cost of growth through organic retention.