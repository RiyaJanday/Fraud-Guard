"""
Business logic for the drift-detection endpoint. Deliberately thin — the
actual statistics live in app.ml_engine.drift_detector (pure functions, no
DB dependency, easy to unit test in isolation); this layer's only job is
pulling the live sample from the database and handing it off.
"""

from sqlalchemy.orm import Session

from app.ml_engine.drift_detector import compute_drift_report
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.drift import DriftReportOut


class DriftService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.transactions = TransactionRepository(db)

    def get_drift_report(self, sample_size: int = 500) -> DriftReportOut:
        live_rows = self.transactions.list_recent_features(limit=sample_size)
        report = compute_drift_report(live_rows)
        return DriftReportOut(**report)
