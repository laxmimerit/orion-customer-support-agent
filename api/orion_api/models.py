"""Response shapes. Field names are the orion_desk column names.

Nulls stay null (M07). Hours and other NUMERIC values are exact decimal strings
("7.9600"), and timestamps are UTC with a trailing Z.
"""
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel


def as_utc(value):
    # orion_desk stores UTC in TIMESTAMP WITHOUT TIME ZONE (ADR 0001, check 5).
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


UtcDatetime = Annotated[datetime, AfterValidator(as_utc)]


class TicketSummary(BaseModel):
    ticket_id: str
    subject: str | None
    status: str | None
    priority: str | None
    channel: str | None
    category: str | None
    customer_id: str | None
    agent_id: str | None
    created_at: UtcDatetime | None


class TicketPage(BaseModel):
    items: list[TicketSummary]
    page: int
    page_size: int
    total: int


class Ticket(BaseModel):
    ticket_id: str
    customer_id: str | None
    agent_id: str | None
    created_at: UtcDatetime | None
    first_response_at: UtcDatetime | None
    resolved_at: UtcDatetime | None
    category: str | None
    priority: str | None
    status: str | None
    channel: str | None
    component: str | None
    subject: str | None
    body: str | None
    sla_response_hours: Decimal | None
    sla_resolution_hours: Decimal | None
    first_response_hours: Decimal | None
    resolution_hours: Decimal | None
    csat: int | None
    reopened_count: int | None
    escalated: int | None
    sentiment: str | None
    plan_id: str | None
    industry: str | None
    region: str | None
    company_size: str | None


class Customer(BaseModel):
    customer_id: str
    company: str | None
    industry: str | None
    country: str | None
    region: str | None
    company_size: str | None
    plan_id: str | None
    seats: int | None
    signup_date: date | None
    contact_email: str | None
    acquisition_source: str | None


class Message(BaseModel):
    message_id: str
    ticket_id: str | None
    created_at: UtcDatetime | None
    author_role: str | None
    body: str | None


class TicketDetail(BaseModel):
    ticket: Ticket
    customer: Customer | None
    messages: list[Message]


class SearchHit(BaseModel):
    kind: Literal["ticket", "article"]
    id: str
    title: str | None
    status: str | None
    priority: str | None
    category: str | None
    similarity: float | None  # 1 - cosine distance; null for an exact ID match


class SearchResults(BaseModel):
    query: str
    match: Literal["exact_id", "semantic"]
    items: list[SearchHit]


class Listing[Item: BaseModel](BaseModel):
    total: int
    items: list[Item]


# Customers, knowledge and company pages (web/lib/api.ts has the same names). These shapes carry no email
# and no date or time field: rows are ordered by those columns in SQL, but they are never returned.
# plan, assigned_to, team and requested_by are names from a join or a rename, not columns of the main table.

class CustomerListItem(BaseModel):
    customer_id: str
    company: str | None
    plan: str | None
    seats: int | None
    region: str | None
    industry: str | None
    active_cases: int
    all_cases: int


class AccountDetails(BaseModel):
    industry: str | None
    country: str | None
    region: str | None
    company_size: str | None


class CustomerSubscription(BaseModel):
    subscription_id: str
    plan: str | None
    seats: int | None
    status: str | None


class CustomerTicket(BaseModel):
    ticket_id: str
    subject: str | None
    component: str | None
    channel: str | None
    priority: str | None
    status: str | None
    assigned_to: str | None
    team: str | None


class Invoice(BaseModel):
    seats: int | None
    unit_price_usd: Decimal | None
    total_usd: Decimal | None
    status: str | None


class CustomerProfile(BaseModel):
    customer_id: str
    company: str | None
    account_details: AccountDetails
    subscription: CustomerSubscription | None
    support_history: Listing[CustomerTicket]
    invoice_history: list[Invoice]


class ArticleSummary(BaseModel):
    article_id: str
    title: str | None
    category: str | None


class ArticleText(ArticleSummary):
    body: str | None


class ArticleTicket(BaseModel):
    ticket_id: str
    customer_id: str | None
    priority: str | None
    status: str | None


class Article(ArticleText):
    related_tickets: Listing[ArticleTicket]
    more_in_category: list[ArticleSummary]


class CompanySection(BaseModel):
    document_id: str
    title: str | None
    owner: str | None
    team: str | None
    body: str | None


class StaffRequest(BaseModel):
    request_id: str
    title: str | None
    requested_by: str | None
    body: str | None


class Company(BaseModel):
    sections: list[CompanySection]
    staff_requests: list[StaffRequest]


# Reports (api/reports/*.sql). Field names and order are the SQL column names; each file's header
# defines its columns. Averages are exact decimal strings rounded to 2 places, null when nothing is counted.

class VolumeRow(BaseModel):
    month: str | None
    tickets: int
    resolved: int
    unresolved: int
    status_missing: int


class BacklogRow(BaseModel):
    status: str
    tickets: int
    no_first_reply: int
    no_first_reply_past_target: int
    oldest_created_at: UtcDatetime | None
    avg_age_hours: Decimal | None
    age_counted: int
    age_missing: int


class Breakdown(BaseModel):
    tickets: int
    resolved: int
    unresolved: int
    status_missing: int
    avg_first_response_hours: Decimal | None
    first_response_counted: int
    first_response_missing: int
    avg_resolution_hours: Decimal | None
    resolution_counted: int
    resolution_missing: int
    avg_csat: Decimal | None
    csat_counted: int
    csat_missing: int


class PriorityKey(BaseModel):
    priority: str | None


class CategoryKey(BaseModel):
    category: str | None


# The key base comes last so its field comes first, as in the SQL.
class PriorityRow(Breakdown, PriorityKey):
    pass


class CategoryRow(Breakdown, CategoryKey):
    pass


class FirstReplyRow(BaseModel):
    priority: str | None
    tickets: int
    met: int
    missed: int
    no_first_reply: int
    no_target: int
    avg_csat_met: Decimal | None
    csat_met_counted: int
    csat_met_missing: int
    avg_csat_missed: Decimal | None
    csat_missed_counted: int
    csat_missed_missing: int


class Report[Row: BaseModel](BaseModel):
    report: str
    rows: list[Row]


class TableCount(BaseModel):
    table: str
    rows: int


class AdminStatus(BaseModel):
    database: str
    tables: list[TableCount]


class ErrorDetail(BaseModel):
    status: int
    code: str
    message: str
    details: list[dict] | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail
