# Netflix Product & Streaming Analytics

An end-to-end Product Analytics project simulating a Netflix-style streaming platform using Python, PostgreSQL, and SQL.

The project covers synthetic data generation, relational database design, data validation, and business-focused analytics across users, subscriptions, content, viewing behaviour, and ratings.

> **Current Status:** Python data generation, PostgreSQL database, and SQL analytics completed. Power BI dashboard is the next phase.

---

## Project Overview

This project simulates a streaming platform and analyzes user behaviour, subscription activity, content performance, viewing patterns, and user ratings.

The project was designed to answer real-world product and business questions such as:

- How many users are active on the platform?
- Which countries have the largest user base?
- Which signup channels contribute the most users?
- Which subscription plans generate the most revenue?
- What is the trial retention rate?
- What is the platform's churn rate?
- When do users watch the most content?
- How does viewing behaviour differ between Movies and TV Shows?
- Which devices generate the most engagement?
- Which genres and titles perform best?
- How do user ratings compare with IMDb ratings?

---

## Project Architecture

```text
Python Data Generation
        │
        ▼
Synthetic CSV Datasets
        │
        ▼
PostgreSQL Database
        │
        ├── Data Validation
        │
        └── SQL Analytics
                │
                ├── User Analytics
                ├── Subscription Analytics
                ├── Content Analytics
                ├── Watch Analytics
                └── Ratings Analytics
                        │
                        ▼
                  Power BI Dashboard
                    (Next Phase)
