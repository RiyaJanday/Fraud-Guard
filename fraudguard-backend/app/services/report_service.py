"""
Generates downloadable reports: a raw transaction CSV export and an
aggregate PDF fraud-summary (built with reportlab, already a pinned
dependency — see requirements.txt's "Reporting" section).

Deliberately built on top of the SAME repositories the dashboard/analytics
endpoints already query (TransactionRepository, AnalyticsRepository) rather
than writing parallel raw SQL for reports — a PDF summary showing different
numbers than the live dashboard for the same period would undermine trust
in both, and duplicated aggregate SQL is exactly the kind of thing that
quietly drifts apart over time as one copy gets a bugfix the other doesn't.
"""

import csv
import io
from datetime import datetime, timezone
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import ValidationException
from app.models.fraud_prediction import Decision
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.model_registry_repository import ModelRegistryRepository
from app.repositories.transaction_repository import TransactionRepository

settings = get_settings()

# Hard cap on rows in a single CSV export. A demo/small-scale deployment
# will never approach this; it exists so the endpoint can never turn into
# an unbounded multi-GB response if the transactions table grows large —
# callers who need more should page through /transactions instead.
_MAX_EXPORT_ROWS = 10_000


def _validate_range(date_from: Optional[datetime], date_to: Optional[datetime]) -> None:
    if date_from and date_to and date_from > date_to:
        raise ValidationException("date_from must be before date_to.")


def _styled_table(data: list[list[str]]) -> Table:
    """Shared table styling so the CSV/PDF's brand look-and-feel (purple
    header, matching FraudGuard's #7C3AED primary) doesn't get re-typed at
    every call site."""
    table = Table(data, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#7C3AED")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                ("TOPPADDING", (0, 0), (-1, 0), 6),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F3FF")]),
            ]
        )
    )
    return table


class ReportService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.transactions = TransactionRepository(db)
        self.analytics = AnalyticsRepository(db)
        self.model_registry = ModelRegistryRepository(db)

    # ------------------------------------------------------------------ #
    # CSV — raw transaction export
    # ------------------------------------------------------------------ #
    def generate_transactions_csv(
        self,
        decision: Optional[Decision] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> str:
        _validate_range(date_from, date_to)
        items, _ = self.transactions.list_paginated(
            page=1, page_size=_MAX_EXPORT_ROWS, decision=decision, date_from=date_from, date_to=date_to
        )

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            [
                "Transaction ID", "Created At (UTC)", "Amount", "Currency", "Merchant",
                "Risk Score", "Fraud Probability", "Decision", "Is Fraud", "Model Version",
            ]
        )
        for txn in items:
            pred = txn.prediction
            writer.writerow(
                [
                    str(txn.id),
                    txn.created_at.isoformat(),
                    f"{txn.amount:.2f}",
                    txn.currency,
                    txn.merchant or "",
                    f"{pred.risk_score:.2f}" if pred else "",
                    f"{pred.fraud_probability:.4f}" if pred else "",
                    pred.decision.value if pred else "",
                    pred.is_fraud if pred else "",
                    pred.model_version if pred else "",
                ]
            )
        return buffer.getvalue()

    # ------------------------------------------------------------------ #
    # PDF — aggregate fraud summary
    # ------------------------------------------------------------------ #
    def generate_summary_pdf(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> bytes:
        _validate_range(date_from, date_to)

        total = self.analytics.count_transactions(since=date_from)
        fraud = self.analytics.count_fraud(since=date_from)
        blocked = self.analytics.count_blocked(since=date_from)
        avg_risk = self.analytics.avg_risk_score(since=date_from)
        distribution = self.analytics.decision_distribution(since=date_from)
        top_merchants = self.analytics.top_merchants_by_risk(limit=5)
        active_model = self.model_registry.get_active()

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            topMargin=20 * mm,
            bottomMargin=20 * mm,
            leftMargin=18 * mm,
            rightMargin=18 * mm,
        )
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "FraudGuardTitle", parent=styles["Title"], textColor=colors.HexColor("#7C3AED"), fontSize=20
        )
        heading_style = ParagraphStyle(
            "FraudGuardHeading", parent=styles["Heading2"], textColor=colors.HexColor("#09090B"), spaceBefore=14
        )
        muted_style = ParagraphStyle("Muted", parent=styles["Normal"], textColor=colors.HexColor("#666666"))

        now = datetime.now(timezone.utc)
        period = "All time"
        if date_from and date_to:
            period = f"{date_from.strftime('%Y-%m-%d')} to {date_to.strftime('%Y-%m-%d')}"
        elif date_from:
            period = f"Since {date_from.strftime('%Y-%m-%d')}"

        elements: list = [
            Paragraph(f"{settings.PROJECT_NAME} \u2014 Fraud Summary Report", title_style),
            Paragraph(f"Period: {period} | Generated: {now.strftime('%Y-%m-%d %H:%M UTC')}", muted_style),
            Spacer(1, 10 * mm),
            Paragraph("Headline Statistics", heading_style),
        ]

        stats_data = [
            ["Metric", "Value"],
            ["Total Transactions", str(total)],
            ["Fraud Detected", str(fraud)],
            ["Fraud Blocked", str(blocked)],
            ["Average Risk Score", f"{avg_risk:.2f} / 100"],
        ]
        if active_model:
            stats_data.append(
                ["Active Model", f"{active_model.version} (accuracy {round((active_model.accuracy or 0) * 100, 1)}%)"]
            )
        elements.append(_styled_table(stats_data))

        elements.append(Paragraph("Decision Distribution", heading_style))
        dist_data = [["Decision", "Count"]] + [
            [label, str(value)] for label, value in zip(distribution["labels"], distribution["values"])
        ]
        elements.append(_styled_table(dist_data))

        if top_merchants:
            elements.append(Paragraph("Top Merchants by Flagged Volume (all-time)", heading_style))
            merch_data = [["Merchant", "Flagged", "Total"]] + [
                [m["merchant"], str(m["flagged_count"]), str(m["total_count"])] for m in top_merchants
            ]
            elements.append(_styled_table(merch_data))

        doc.build(elements)
        return buffer.getvalue()
