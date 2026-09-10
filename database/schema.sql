-- =============================================================
-- Netflix Product Analytics
-- PostgreSQL Schema
-- =============================================================


-- =============================================================
-- DIMENSION TABLES
-- =============================================================


-- -------------------------------------------------------------
-- dim_users
-- -------------------------------------------------------------
CREATE TABLE dim_users (
    user_id         INTEGER         NOT NULL,
    full_name       VARCHAR(150)    NOT NULL,
    email           VARCHAR(150)    NOT NULL,
    gender          VARCHAR(10)     NOT NULL,
    date_of_birth   DATE            NOT NULL,
    age             INTEGER         NOT NULL CHECK (age >= 13 AND age <= 120),
    country         VARCHAR(100)    NOT NULL,
    signup_date     DATE            NOT NULL,
    signup_channel  VARCHAR(50)     NOT NULL,
    account_status  VARCHAR(20)     NOT NULL CHECK (account_status IN ('Active', 'Cancelled', 'Suspended', 'Paused')),
    created_at      TIMESTAMP       NOT NULL,
    updated_at      TIMESTAMP       NOT NULL,
    CONSTRAINT pk_dim_users         PRIMARY KEY (user_id),
    CONSTRAINT uq_dim_users_email   UNIQUE      (email),
    CONSTRAINT chk_updated_at_users CHECK       (updated_at >= created_at)
);


-- -------------------------------------------------------------
-- dim_profiles
-- -------------------------------------------------------------
CREATE TABLE dim_profiles (
    profile_id          INTEGER         NOT NULL,
    user_id             INTEGER         NOT NULL,
    profile_name        VARCHAR(100)    NOT NULL,
    profile_type        VARCHAR(10)     NOT NULL CHECK (profile_type IN ('Adult', 'Kids')),
    preferred_language  VARCHAR(50)     NOT NULL,
    created_at          TIMESTAMP       NOT NULL,
    updated_at          TIMESTAMP       NOT NULL,
    CONSTRAINT pk_dim_profiles          PRIMARY KEY (profile_id),
    CONSTRAINT fk_profiles_user_id      FOREIGN KEY (user_id)
        REFERENCES dim_users (user_id),
    CONSTRAINT chk_updated_at_profiles  CHECK (updated_at >= created_at)
);


-- -------------------------------------------------------------
-- dim_subscription_plans
-- -------------------------------------------------------------
CREATE TABLE dim_subscription_plans (
    plan_id         INTEGER         NOT NULL,
    plan_name       VARCHAR(50)     NOT NULL,
    plan_tier       VARCHAR(30)     NOT NULL,
    monthly_price   NUMERIC(8,2)    NOT NULL CHECK (monthly_price > 0),
    max_screens     SMALLINT        NOT NULL CHECK (max_screens > 0),
    video_quality   VARCHAR(20)     NOT NULL,
    is_active       BOOLEAN         NOT NULL DEFAULT TRUE,
    CONSTRAINT pk_dim_subscription_plans    PRIMARY KEY (plan_id),
    CONSTRAINT uq_dim_subscription_plans    UNIQUE      (plan_name)
);


-- -------------------------------------------------------------
-- dim_genres
-- -------------------------------------------------------------
CREATE TABLE dim_genres (
    genre_id    INTEGER         NOT NULL,
    genre_name  VARCHAR(50)     NOT NULL,
    CONSTRAINT pk_dim_genres        PRIMARY KEY (genre_id),
    CONSTRAINT uq_dim_genres_name   UNIQUE      (genre_name)
);


-- -------------------------------------------------------------
-- dim_content
-- -------------------------------------------------------------
CREATE TABLE dim_content (
    content_id              INTEGER         NOT NULL,
    title                   VARCHAR(200)    NOT NULL,
    content_type            VARCHAR(20)     NOT NULL CHECK (content_type IN ('Movie', 'TV Show')),
    release_year            SMALLINT        NOT NULL CHECK (release_year >= 1900),
    original_language       VARCHAR(50)     NOT NULL,
    maturity_rating         VARCHAR(10)     NOT NULL,
    total_seasons           SMALLINT        NOT NULL DEFAULT 0 CHECK (total_seasons >= 0),
    total_episodes          SMALLINT        NOT NULL DEFAULT 0 CHECK (total_episodes >= 0),
    runtime_minutes         INTEGER         NOT NULL CHECK (runtime_minutes > 0),
    content_length_category VARCHAR(20)     NOT NULL CHECK (content_length_category IN ('Short', 'Medium', 'Long')),
    production_country      VARCHAR(100)    NOT NULL,
    content_status          VARCHAR(20)     NOT NULL CHECK (content_status IN ('Available', 'Coming Soon', 'Removed')),
    imdb_rating             NUMERIC(3,1)    NOT NULL CHECK (imdb_rating >= 1.0 AND imdb_rating <= 10.0),
    added_date              DATE            NOT NULL,
    CONSTRAINT pk_dim_content       PRIMARY KEY (content_id),
    CONSTRAINT uq_dim_content_title UNIQUE      (title)
);


-- -------------------------------------------------------------
-- dim_devices
-- -------------------------------------------------------------
CREATE TABLE dim_devices (
    device_id     INTEGER         NOT NULL,
    device_type   VARCHAR(30)     NOT NULL,
    device_brand  VARCHAR(50)     NOT NULL,
    os_name       VARCHAR(30)     NOT NULL,
    app_version   VARCHAR(20)     NOT NULL,
    CONSTRAINT pk_dim_devices PRIMARY KEY (device_id)
);


-- =============================================================
-- BRIDGE TABLE
-- =============================================================


-- -------------------------------------------------------------
-- bridge_content_genre
-- -------------------------------------------------------------
CREATE TABLE bridge_content_genre (
    content_id  INTEGER     NOT NULL,
    genre_id    INTEGER     NOT NULL,
    CONSTRAINT pk_bridge_content_genre      PRIMARY KEY (content_id, genre_id),
    CONSTRAINT fk_bridge_content_id         FOREIGN KEY (content_id)
        REFERENCES dim_content (content_id),
    CONSTRAINT fk_bridge_genre_id           FOREIGN KEY (genre_id)
        REFERENCES dim_genres  (genre_id)
);


-- =============================================================
-- FACT TABLES
-- =============================================================


-- -------------------------------------------------------------
-- fact_subscriptions
-- -------------------------------------------------------------
CREATE TABLE fact_subscriptions (
    subscription_id     INTEGER         NOT NULL,
    user_id             INTEGER         NOT NULL,
    plan_id             INTEGER         NOT NULL,
    start_date          DATE            NOT NULL,
    end_date            DATE            NULL,
    renewal_date        DATE            NOT NULL,
    trial_user          BOOLEAN         NOT NULL DEFAULT FALSE,
    status              VARCHAR(20)     NOT NULL CHECK (status IN ('Active', 'Cancelled', 'Suspended', 'Paused')),
    auto_renew          BOOLEAN         NOT NULL DEFAULT TRUE,
    subscription_source VARCHAR(30)     NOT NULL CHECK (subscription_source IN ('Android', 'iOS', 'Website', 'Smart TV', 'Partner')),
    cancellation_reason VARCHAR(150)    NULL,
    created_at          TIMESTAMP       NOT NULL,
    updated_at          TIMESTAMP       NOT NULL,
    CONSTRAINT pk_fact_subscriptions            PRIMARY KEY (subscription_id),

    CONSTRAINT fk_subscriptions_user_id         FOREIGN KEY (user_id)
        REFERENCES dim_users              (user_id),
    CONSTRAINT fk_subscriptions_plan_id         FOREIGN KEY (plan_id)
        REFERENCES dim_subscription_plans (plan_id),
    CONSTRAINT chk_renewal_after_start          CHECK       (renewal_date > start_date),
    CONSTRAINT chk_end_after_start              CHECK       (end_date IS NULL OR end_date >= start_date),
    CONSTRAINT chk_updated_at_subscriptions     CHECK       (updated_at >= created_at)
);


-- -------------------------------------------------------------
-- fact_payments
-- -------------------------------------------------------------
CREATE TABLE fact_payments (
    payment_id      INTEGER         NOT NULL,
    subscription_id INTEGER         NOT NULL,
    user_id         INTEGER         NOT NULL,
    payment_date    DATE            NOT NULL,
    amount          NUMERIC(8,2)    NOT NULL CHECK (amount > 0),
    currency        VARCHAR(10)     NOT NULL,
    discount_amount NUMERIC(8,2)    NOT NULL DEFAULT 0.00 CHECK (discount_amount >= 0),
    tax_amount      NUMERIC(8,2)    NOT NULL DEFAULT 0.00 CHECK (tax_amount >= 0),
    final_amount    NUMERIC(8,2)    NOT NULL CHECK (final_amount >= 0),
    payment_method  VARCHAR(30)     NOT NULL,
    payment_status  VARCHAR(20)     NOT NULL CHECK (payment_status IN ('Completed', 'Failed')),
    invoice_number  VARCHAR(50)     NOT NULL,
    created_at      TIMESTAMP       NOT NULL,
    updated_at      TIMESTAMP       NOT NULL,
    CONSTRAINT pk_fact_payments                 PRIMARY KEY (payment_id),
    CONSTRAINT uq_fact_payments_invoice         UNIQUE      (invoice_number),
    CONSTRAINT fk_payments_subscription_id      FOREIGN KEY (subscription_id)
        REFERENCES fact_subscriptions (subscription_id),
    CONSTRAINT fk_payments_user_id              FOREIGN KEY (user_id)
        REFERENCES dim_users          (user_id),
    CONSTRAINT chk_updated_at_payments          CHECK       (updated_at >= created_at)
);


-- -------------------------------------------------------------
-- fact_user_sessions
-- -------------------------------------------------------------
CREATE TABLE fact_user_sessions (
    session_id          INTEGER         NOT NULL,
    user_id             INTEGER         NOT NULL,
    device_id           INTEGER         NOT NULL,
    login_method        VARCHAR(20)     NOT NULL CHECK (login_method IN ('Email', 'Google', 'Apple', 'Facebook')),
    session_start       TIMESTAMP       NOT NULL,
    session_end         TIMESTAMP       NULL,
    session_duration_sec INTEGER        NULL CHECK (session_duration_sec >= 0),
    ip_country          VARCHAR(100)    NOT NULL,
    created_at          TIMESTAMP       NOT NULL,
    updated_at          TIMESTAMP       NOT NULL,
    CONSTRAINT pk_fact_user_sessions            PRIMARY KEY (session_id),
    CONSTRAINT fk_sessions_user_id              FOREIGN KEY (user_id)
        REFERENCES dim_users    (user_id),
    CONSTRAINT fk_sessions_device_id            FOREIGN KEY (device_id)
        REFERENCES dim_devices  (device_id),
    CONSTRAINT chk_session_end_after_start      CHECK       (session_end IS NULL OR session_end >= session_start),
    CONSTRAINT chk_updated_at_sessions          CHECK       (updated_at >= created_at)
);


-- -------------------------------------------------------------
-- fact_watch_history
-- -------------------------------------------------------------
CREATE TABLE fact_watch_history (
    watch_id             BIGINT          NOT NULL,
    user_id              INTEGER         NOT NULL,
    profile_id           INTEGER         NOT NULL,
    content_id           INTEGER         NOT NULL,
    session_id           INTEGER         NOT NULL,
    device_id            INTEGER         NOT NULL,
    watch_date           DATE            NOT NULL,
    watch_start_time     TIMESTAMP       NOT NULL,
    watch_duration_min   INTEGER         NOT NULL CHECK (watch_duration_min >= 0),
    percentage_completed NUMERIC(5,2)    NOT NULL CHECK (percentage_completed >= 0 AND percentage_completed <= 100),
    watch_status         VARCHAR(20)     NOT NULL CHECK (watch_status IN ('Started', 'Paused', 'Completed', 'Abandoned')),
    is_completed         BOOLEAN         NOT NULL DEFAULT FALSE,
    is_downloaded        BOOLEAN         NOT NULL DEFAULT FALSE,
    created_at           TIMESTAMP       NOT NULL,
    updated_at           TIMESTAMP       NOT NULL,
    CONSTRAINT pk_fact_watch_history            PRIMARY KEY (watch_id),
    CONSTRAINT fk_watch_user_id                 FOREIGN KEY (user_id)
        REFERENCES dim_users          (user_id),
    CONSTRAINT fk_watch_profile_id              FOREIGN KEY (profile_id)
        REFERENCES dim_profiles       (profile_id),
    CONSTRAINT fk_watch_content_id              FOREIGN KEY (content_id)
        REFERENCES dim_content        (content_id),
    CONSTRAINT fk_watch_session_id              FOREIGN KEY (session_id)
        REFERENCES fact_user_sessions (session_id),
    CONSTRAINT fk_watch_device_id               FOREIGN KEY (device_id)
        REFERENCES dim_devices        (device_id),
    CONSTRAINT chk_updated_at_watch             CHECK (updated_at >= created_at)
);


-- -------------------------------------------------------------
-- fact_ratings
-- -------------------------------------------------------------
CREATE TABLE fact_ratings (
    rating_id    INTEGER         NOT NULL,
    user_id      INTEGER         NOT NULL,
    profile_id   INTEGER         NOT NULL,
    content_id   INTEGER         NOT NULL,
    rating_value SMALLINT        NOT NULL CHECK (rating_value >= 1 AND rating_value <= 5),
    review_text  TEXT            NULL,
    rating_date  DATE            NOT NULL,
    created_at   TIMESTAMP       NOT NULL,
    updated_at   TIMESTAMP       NOT NULL,
    CONSTRAINT pk_fact_ratings                  PRIMARY KEY (rating_id),
    CONSTRAINT uq_fact_ratings_profile_content  UNIQUE      (profile_id, content_id),
    CONSTRAINT fk_ratings_user_id               FOREIGN KEY (user_id)
        REFERENCES dim_users    (user_id),
    CONSTRAINT fk_ratings_profile_id            FOREIGN KEY (profile_id)
        REFERENCES dim_profiles (profile_id),
    CONSTRAINT fk_ratings_content_id            FOREIGN KEY (content_id)
        REFERENCES dim_content  (content_id),
    CONSTRAINT chk_updated_at_ratings           CHECK (updated_at >= created_at)
);


-- =============================================================
-- INDEXES
-- =============================================================


-- -------------------------------------------------------------
-- dim_users indexes
-- -------------------------------------------------------------
CREATE INDEX idx_users_email          ON dim_users (email);
CREATE INDEX idx_users_country        ON dim_users (country);
CREATE INDEX idx_users_signup_date    ON dim_users (signup_date);
CREATE INDEX idx_users_account_status ON dim_users (account_status);


-- -------------------------------------------------------------
-- dim_profiles indexes
-- -------------------------------------------------------------
CREATE INDEX idx_profiles_user_id      ON dim_profiles (user_id);
CREATE INDEX idx_profiles_profile_type ON dim_profiles (profile_type);


-- -------------------------------------------------------------
-- dim_content indexes
-- -------------------------------------------------------------
CREATE INDEX idx_content_content_type            ON dim_content (content_type);
CREATE INDEX idx_content_content_status          ON dim_content (content_status);
CREATE INDEX idx_content_release_year            ON dim_content (release_year);
CREATE INDEX idx_content_content_length_category ON dim_content (content_length_category);
CREATE INDEX idx_content_original_language       ON dim_content (original_language);


-- -------------------------------------------------------------
-- dim_devices indexes
-- -------------------------------------------------------------
CREATE INDEX idx_devices_device_type ON dim_devices (device_type);


-- -------------------------------------------------------------
-- bridge_content_genre indexes
-- -------------------------------------------------------------
CREATE INDEX idx_bridge_content_id ON bridge_content_genre (content_id);
CREATE INDEX idx_bridge_genre_id   ON bridge_content_genre (genre_id);


-- -------------------------------------------------------------
-- fact_subscriptions indexes
-- -------------------------------------------------------------
CREATE INDEX idx_subscriptions_user_id             ON fact_subscriptions (user_id);
CREATE INDEX idx_subscriptions_plan_id             ON fact_subscriptions (plan_id);
CREATE INDEX idx_subscriptions_status              ON fact_subscriptions (status);
CREATE INDEX idx_subscriptions_start_date          ON fact_subscriptions (start_date);
CREATE INDEX idx_subscriptions_renewal_date        ON fact_subscriptions (renewal_date);
CREATE INDEX idx_subscriptions_subscription_source ON fact_subscriptions (subscription_source);


-- -------------------------------------------------------------
-- fact_payments indexes
-- -------------------------------------------------------------
CREATE INDEX idx_payments_user_id         ON fact_payments (user_id);
CREATE INDEX idx_payments_subscription_id ON fact_payments (subscription_id);
CREATE INDEX idx_payments_payment_date    ON fact_payments (payment_date);
CREATE INDEX idx_payments_payment_status  ON fact_payments (payment_status);
CREATE INDEX idx_payments_payment_method  ON fact_payments (payment_method);


-- -------------------------------------------------------------
-- fact_user_sessions indexes
-- -------------------------------------------------------------
CREATE INDEX idx_sessions_user_id     ON fact_user_sessions (user_id);
CREATE INDEX idx_sessions_device_id   ON fact_user_sessions (device_id);
CREATE INDEX idx_sessions_session_start ON fact_user_sessions (session_start);
CREATE INDEX idx_sessions_login_method ON fact_user_sessions (login_method);


-- -------------------------------------------------------------
-- fact_watch_history indexes
-- -------------------------------------------------------------
CREATE INDEX idx_watch_user_id     ON fact_watch_history (user_id);
CREATE INDEX idx_watch_profile_id  ON fact_watch_history (profile_id);
CREATE INDEX idx_watch_content_id  ON fact_watch_history (content_id);
CREATE INDEX idx_watch_session_id  ON fact_watch_history (session_id);
CREATE INDEX idx_watch_device_id   ON fact_watch_history (device_id);
CREATE INDEX idx_watch_watch_date  ON fact_watch_history (watch_date);
CREATE INDEX idx_watch_watch_status ON fact_watch_history (watch_status);
CREATE INDEX idx_watch_is_downloaded ON fact_watch_history (is_downloaded);


-- -------------------------------------------------------------
-- fact_ratings indexes
-- -------------------------------------------------------------
CREATE INDEX idx_ratings_user_id    ON fact_ratings (user_id);
CREATE INDEX idx_ratings_profile_id ON fact_ratings (profile_id);
CREATE INDEX idx_ratings_content_id ON fact_ratings (content_id);
CREATE INDEX idx_ratings_rating_date ON fact_ratings (rating_date);
CREATE INDEX idx_ratings_rating_value ON fact_ratings (rating_value);