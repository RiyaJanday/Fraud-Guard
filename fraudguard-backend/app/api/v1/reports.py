"""
Report generation/download endpoints:

    GET /reports/transactions.csv  — raw transaction export, filterable
    GET /reports/summary.pdf       — aggregate fraud-summary PDF

Both stream the file directly in the response body with a
Content-Disposition header (rather than writing to disk and returning a
URL) — there's nowhere durable to store generated files in this deployment
(no S3/blob storage configured), and for report sizes this small,
generate-on-request is simpler and always reflects live data, with no
stale-file cleanup problem to solve.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.database.session import get_db
from app.models.fraud_prediction import Decision
from app.models.user import User, UserRole
from app.services.report_service import ReportService

router = APIRouter()

# Reports can contain PII-adjacent data (merchant names, transaction amounts) —
# Auditor is included since compliance review is exactly what this role exists for.
_ANY_ROLE = (UserRole.ADMIN, UserRole.ANALYST, UserRole.AUDITOR)


@router.get(
    "/transactions.csv",
    summary="Download a CSV export of transactions",
    responses={200: {"content": {"text/csv": {}}}},
)
def export_transactions_csv(
    decision: Optional[Decision] = Query(None),
    date_from: Optional[datetime] = Query(None, description="ISO 8601, e.g. 2026-07-01T00:00:00Z"),
    date_to: Optional[datetime] = Query(None, description="ISO 8601, e.g. 2026-07-31T23:59:59Z"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_ANY_ROLE)),
) -> Response:
    csv_content = ReportService(db).generate_transactions_csv(decision=decision, date_from=date_from, date_to=date_to)
    filename = f"fraudguard-transactions-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/summary.pdf",
    summary="Download a PDF fraud-summary report",
    responses={200: {"content": {"application/pdf": {}}}},
)
def export_summary_pdf(
    date_from: Optional[datetime] = Query(None, description="ISO 8601, e.g. 2026-07-01T00:00:00Z"),
    date_to: Optional[datetime] = Query(None, description="ISO 8601, e.g. 2026-07-31T23:59:59Z"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_ANY_ROLE)),
) -> Response:
    pdf_bytes = ReportService(db).generate_summary_pdf(date_from=date_from, date_to=date_to)
    filename = f"fraudguard-summary-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
