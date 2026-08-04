"""
Version 1 API router aggregator.

Each feature module (auth, users, prediction, transactions, analytics,
reports, review, notifications, metrics, drift, explainability, health)
registers its own APIRouter here as it is built. main.py only ever imports
`api_router` from this module, so it never needs to change as new endpoint
groups are added.
"""

from fastapi import APIRouter

from app.api.v1 import analytics, auth, dashboard, drift, explainability, health, notifications, prediction, reports, review, transactions, users, ws

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["User Management"])
api_router.include_router(prediction.router, tags=["Prediction"])
api_router.include_router(transactions.router, prefix="/transactions", tags=["Transactions"])
api_router.include_router(review.router, prefix="/review-queue", tags=["Manual Review"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(drift.router, prefix="/drift", tags=["Drift Detection"])
api_router.include_router(explainability.router, prefix="/explainability", tags=["Explainability"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
api_router.include_router(ws.router, tags=["WebSocket"])

# Registered incrementally in later steps.
