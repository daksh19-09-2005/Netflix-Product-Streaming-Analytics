# Netflix Product & Streaming Analytics

An end-to-end Product Analytics project built around a synthetic Netflix-style streaming platform. The project covers data generation, relational database design, PostgreSQL, advanced SQL analytics, and business intelligence using Power BI.

The project analyzes the complete streaming lifecycle — from user acquisition and subscriptions to content consumption, viewing behaviour, and customer ratings.

---

## 📌 Project Overview

Streaming platforms generate large volumes of user, subscription, content, and behavioural data.

This project was designed to simulate that environment and answer real-world product and business questions such as:

- How many users are active on the platform?
- Which countries contribute the largest user base?
- Which signup channels acquire the most users?
- Which subscription plans generate the most revenue?
- What is the trial retention rate?
- What is the platform churn rate?
- When are users most likely to watch content?
- How does viewing behaviour differ between Movies and TV Shows?
- Which devices generate the most engagement?
- Which genres and titles receive the highest engagement?
- How do user ratings compare with IMDb ratings?
- Which audience segments contribute the most ratings?

---

# 🏗️ Project Architecture

```text
                    ┌──────────────────────┐
                    │   Python Data        │
                    │      Generation     │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  Synthetic Datasets  │
                    │        (CSV)         │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │      PostgreSQL      │
                    │       Database       │
                    └──────────┬───────────┘
                               │
                    ┌──────────┴───────────┐
                    │                      │
                    ▼                      ▼
             Data Validation         SQL Analytics
                                           │
             ┌─────────────────────────────┼──────────────────────────┐
             │                             │                          │
             ▼                             ▼                          ▼
       User Analytics              Subscription Analytics       Content Analytics
             │                             │                          │
             └─────────────────────────────┼──────────────────────────┘
                                           │
                         ┌─────────────────┴─────────────────┐
                         │                                   │
                         ▼                                   ▼
                  Watch Analytics                    Ratings Analytics
                         │                                   │
                         └─────────────────┬─────────────────┘
                                           │
                                           ▼
                                     Power BI
                                      Dashboard
