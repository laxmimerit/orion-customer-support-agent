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
