"""
API routers.
"""

from app.routers import (
    admin,
    auth,
    metric_synonyms,
    organizations,
    participants,
    prof_activities,
    reports,
    weights,
)

__all__ = [
    "auth",
    "admin",
    "metric_synonyms",
    "organizations",
    "participants",
    "prof_activities",
    "reports",
    "weights",
]
