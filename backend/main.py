from datetime import date
from pathlib import Path
import csv

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict

# ------------------------
# FastAPI app setup
# ------------------------
# Main FastAPI application instance
app = FastAPI(
    title="Customer Insights API",
    version="1.0.0",
)

# Allow the Angular frontend (localhost:4200) to talk to this backend
# This avoids CORS issues during local development
origins = [
    "http://localhost:4200",
    "http://127.0.0.1:4200",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------
# Data models session
# ------------------------


class AccountRecord(BaseModel):
    """
    Represents one validated row from sample_data.csv.
    This mirrors the raw dataset but enforces types and constraints.
    """
    account_uuid: str
    account_label: str
    subscription_status: str
    admin_seats: int = Field(ge=0)
    user_seats: int = Field(ge=0)
    read_only_seats: int = Field(ge=0)
    total_records: int = Field(ge=0)
    automation_count: int = Field(ge=0)
    workflow_title: Optional[str] = None
    messages_processed: int = Field(ge=0)
    notifications_sent: int = Field(ge=0)
    notifications_billed: int = Field(ge=0)


class AccountInsights(AccountRecord):
    """
    Enriched account record containing derived metrics
    used directly by the frontend dashboard.
    """
    total_seats: int
    seat_utilisation: float
    billing_utilisation: float
    health_score: int
    churn_risk: str  # "churned" | "at_risk" | "healthy"
    report_date: date  # synthetic date for time series


class SummaryResponse(BaseModel):
    """
    Aggregated KPIs displayed in the top summary cards.
    """
    total_accounts: int
    active_accounts: int
    inactive_accounts: int
    total_notifications_billed: int
    avg_notifications_billed_per_active: float
    total_messages_processed: int
    avg_messages_per_account: float
    avg_health_score: float
    at_risk_accounts: int
    churned_accounts: int


class PaginatedRecordsResponse(BaseModel):
    """
    Wrapper for paginated account records.
    """
    items: List[AccountInsights]
    page: int
    page_size: int
    total_items: int
    total_pages: int


class HealthByStatusItem(BaseModel):
    """
    Simple structure for health distribution analytics.
    """
    status: str
    account_count: int


class RevenueByStatusItem(BaseModel):
    """
    Aggregated billing totals grouped by churn risk.
    """
    status: str
    total_notifications_billed: int


class NotificationsOverTimeItem(BaseModel):
    """
    Time-series bucket used for the notifications trend chart.
    """
    date: date
    total_notifications_billed: int


# In-memory storage
# Raw validated records from CSV
raw_records: List[AccountRecord] = []

# Enriched insights derived from raw records
insights: List[AccountInsights] = []

# Rows that failed validation
invalid_rows: List[dict] = []

# Path to the CSV file
DATA_FILE_PATH = Path(__file__).resolve().parent.parent / "sample_data.csv"


# ------------------------
# Helper functions
# ------------------------
def compute_insights(record: AccountRecord, report_date: date) -> AccountInsights:
    """
    Derive business metrics, health score, and churn risk
    from a raw AccountRecord.
    """
    # Derived metrics # Seat footprint and utilisation
    total_seats = record.admin_seats + record.user_seats + record.read_only_seats
    seat_utilisation = (
        record.messages_processed / total_seats if total_seats > 0 else 0.0
    )
    billing_utilisation = (
        (record.notifications_billed / record.notifications_sent) * 100.0
        if record.notifications_sent > 0
        else 0.0
    )

    # Usage score 0–40
    if record.messages_processed < 100_000:
        usage_score = 10
    elif record.messages_processed < 1_000_000:
        usage_score = 25
    else:
        usage_score = 40

    # Automation score 0–20
    if record.automation_count == 0:
        automation_score = 0
    elif record.automation_count <= 3:
        automation_score = 10
    else:
        automation_score = 20

    # Footprint score 0–20
    if record.total_records < 10_000:
        footprint_score = 5
    elif record.total_records < 50_000:
        footprint_score = 15
    else:
        footprint_score = 20

    # Billing score 0–20
    if billing_utilisation == 0:
        billing_score = 0
    elif billing_utilisation <= 90:
        billing_score = 10
    else:
        billing_score = 20

    health_score = int(
        usage_score + automation_score + footprint_score + billing_score
    )  # 0–100

    # If subscription inactive, health is 0
    if record.subscription_status == "inactive":
        health_score = 0

    # Churn risk bucket
    if record.subscription_status == "inactive":
        churn_risk = "churned"
    elif health_score < 40:
        churn_risk = "at_risk"
    else:
        churn_risk = "healthy"

    return AccountInsights(
        **record.dict(),
        total_seats=total_seats,
        seat_utilisation=round(seat_utilisation, 2),
        billing_utilisation=round(billing_utilisation, 2),
        health_score=health_score,
        churn_risk=churn_risk,
        report_date=report_date,
    )


def load_data_from_csv() -> None:
    """
    Load and validate sample_data.csv into memory.
    Invalid rows are captured separately for transparency.
    """
    raw_records.clear()
    insights.clear()
    invalid_rows.clear()

    if not DATA_FILE_PATH.exists():
        print(f"[WARN] CSV file not found at: {DATA_FILE_PATH}")
        return

    print(f"[INFO] Loading data from: {DATA_FILE_PATH}")

    with DATA_FILE_PATH.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row_number, row in enumerate(reader, start=2):  # header is row 1
            try:
                # Map CSV headers to model fields
                mapped = {
                    "account_uuid": row["Account UUID"],
                    "account_label": row["Account Label"],
                    "subscription_status": row["Subscription Status"].strip().lower(),
                    "admin_seats": row["Admin Seats"],
                    "user_seats": row["User Seats"],
                    "read_only_seats": row["Read Only Seats"],
                    "total_records": row["Total Records"],
                    "automation_count": row["Automation Count"],
                    "workflow_title": row.get("Workflow Title") or None,
                    "messages_processed": row["Messages Processed"],
                    "notifications_sent": row["Notifications Sent"],
                    "notifications_billed": row["Notifications Billed"],
                }

                record = AccountRecord(**mapped)

                # Business validation: billed cannot exceed sent
                if record.notifications_billed > record.notifications_sent:
                    raise ValueError(
                        "Notifications billed cannot exceed notifications sent"
                    )

                raw_records.append(record)

                # Synthetic report date: cycle through 1–10 Jan 2025
                day = ((row_number - 2) % 10) + 1  # rows start at 2
                report_date = date(2025, 1, day)

                insights.append(compute_insights(record, report_date))

            except Exception as e:
                invalid_rows.append(
                    {"row_number": row_number, "raw_row": row, "error": str(e)}
                )

    print(
        f"[INFO] Loaded {len(raw_records)} valid records, "
        f"{len(invalid_rows)} invalid rows"
    )


# ------------------------
# Startup event
# ------------------------
@app.on_event("startup")
def startup_event():
    """Load CSV data into memory when the API starts."""
    load_data_from_csv()


# ------------------------
# Basic endpoints
# ------------------------
@app.get("/")
def read_root():
    return {"message": "Dashboard Page"}


@app.get("/health")
def health():
    """Lightweight health check for monitoring."""
    return {
        "status": "ok",
        "records_loaded": len(raw_records),
        "invalid_rows": len(invalid_rows),
    }


# ------------------------
# Raw data endpoints
# ------------------------
@app.get("/records/raw", response_model=List[AccountRecord])
def get_raw_records():
    """Return all valid records loaded from the CSV."""
    return raw_records


@app.get("/records/invalid")
def get_invalid_records():
    """Return rows that failed validation, if any."""
    return invalid_rows


# ------------------------
# Summary endpoint
# ------------------------
@app.get("/summary", response_model=SummaryResponse)
def get_summary():
    """High-level metrics for leadership."""
    total_accounts = len(insights)
    active_accounts = sum(
        1 for r in insights if r.subscription_status == "active"
    )
    inactive_accounts = sum(
        1 for r in insights if r.subscription_status == "inactive"
    )

    total_notifications_billed = sum(r.notifications_billed for r in insights)
    total_messages_processed = sum(r.messages_processed for r in insights)
    avg_notifications_billed_per_active = (
        total_notifications_billed / active_accounts if active_accounts > 0 else 0.0
    )
    avg_messages_per_account = (
        total_messages_processed / total_accounts if total_accounts > 0 else 0.0
    )
    avg_health_score = (
        sum(r.health_score for r in insights) / total_accounts
        if total_accounts > 0
        else 0.0
    )

    at_risk_accounts = sum(1 for r in insights if r.churn_risk == "at_risk")
    churned_accounts = sum(1 for r in insights if r.churn_risk == "churned")

    return SummaryResponse(
        total_accounts=total_accounts,
        active_accounts=active_accounts,
        inactive_accounts=inactive_accounts,
        total_notifications_billed=total_notifications_billed,
        avg_notifications_billed_per_active=round(
            avg_notifications_billed_per_active, 2
        ),
        total_messages_processed=total_messages_processed,
        avg_messages_per_account=round(avg_messages_per_account, 2),
        avg_health_score=round(avg_health_score, 2),
        at_risk_accounts=at_risk_accounts,
        churned_accounts=churned_accounts,
    )


# ------------------------
# Paginated & filterable records endpoint
# ------------------------
@app.get("/records", response_model=PaginatedRecordsResponse)
def get_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    subscription_status: Optional[str] = Query(
        None, description="Filter by 'active' or 'inactive'"
    ),
    min_health: Optional[int] = Query(
        None, ge=0, le=100, description="Minimum health score"
    ),
    search: Optional[str] = Query(
        None, description="Search by account label (case-insensitive)"
    ),
):
    """Paginated records with simple filters for the frontend table."""
    filtered = insights

    if subscription_status in {"active", "inactive"}:
        filtered = [
            r for r in filtered if r.subscription_status == subscription_status
        ]

    if min_health is not None:
        filtered = [r for r in filtered if r.health_score >= min_health]

    if search:
        s = search.lower()
        filtered = [r for r in filtered if s in r.account_label.lower()]

    total_items = len(filtered)
    total_pages = (total_items + page_size - 1) // page_size if total_items else 1

    start = (page - 1) * page_size
    end = start + page_size
    items = filtered[start:end]

    return PaginatedRecordsResponse(
        items=items,
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
    )


# ------------------------
# Analytics endpoints
# ------------------------
@app.get("/analytics/health-by-status", response_model=List[HealthByStatusItem])
def health_by_status():
    """Counts of accounts by churn_risk (healthy / at_risk / churned)."""
    buckets: Dict[str, int] = {"healthy": 0, "at_risk": 0, "churned": 0}
    for r in insights:
        buckets[r.churn_risk] = buckets.get(r.churn_risk, 0) + 1

    return [
        HealthByStatusItem(status=status, account_count=count)
        for status, count in buckets.items()
    ]


@app.get(
    "/analytics/revenue-by-status",
    response_model=List[RevenueByStatusItem],
)
def revenue_by_status():
    """Total notifications billed by churn_risk category."""
    totals: Dict[str, int] = {"healthy": 0, "at_risk": 0, "churned": 0}
    for r in insights:
        totals[r.churn_risk] = totals.get(r.churn_risk, 0) + r.notifications_billed

    return [
        RevenueByStatusItem(status=status, total_notifications_billed=total)
        for status, total in totals.items()
    ]


@app.get(
    "/analytics/notifications-over-time",
    response_model=List[NotificationsOverTimeItem],
)
def notifications_over_time(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
):
    """
    Time series of total notifications billed per report_date.
    If start_date / end_date not provided, uses min/max available dates.
    """
    if not insights:
        return []

    dates = [r.report_date for r in insights]
    min_date = min(dates)
    max_date = max(dates)

    start = start_date or min_date
    end = end_date or max_date

    bucket: Dict[date, int] = {}

    for r in insights:
        if start <= r.report_date <= end:
            bucket[r.report_date] = bucket.get(r.report_date, 0) + r.notifications_billed

    sorted_items = sorted(bucket.items(), key=lambda x: x[0])

    return [
        NotificationsOverTimeItem(date=d, total_notifications_billed=total)
        for d, total in sorted_items
    ]
