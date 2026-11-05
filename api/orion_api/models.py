"""Response shapes. Field names are the orion_desk column names.

Nulls stay null (M07). Hours and other NUMERIC values are exact decimal strings
("7.9600"), and timestamps are UTC with a trailing Z.
"""
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field


def as_utc(value):
    # orion_desk stores UTC in TIMESTAMP WITHOUT TIME ZONE (ADR 0001, check 5).
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


UtcDatetime = Annotated[datetime, AfterValidator(as_utc)]


# age_hours is computed, not a column: hours from created_at to the data snapshot, as in reports/backlog.sql.
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
    sla_response_hours: Decimal | None
    sla_resolution_hours: Decimal | None
    first_response_hours: Decimal | None
    resolution_hours: Decimal | None
    age_hours: Decimal | None


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


# Similar tickets. message_count, last_author_role and last_body come from the ticket's messages;
# matched_on names the fields a ticket shares with the one being read, and may be empty.
class SimilarTicket(BaseModel):
    ticket_id: str
    priority: str | None
    similarity: float  # 1 - cosine distance between the two tickets' stored embeddings
    resolution_hours: Decimal | None
    sla_resolution_hours: Decimal | None
    first_response_hours: Decimal | None
    csat: int | None
    reopened_count: int | None
    escalated: int | None
    message_count: int
    agent_id: str | None
    plan_id: str | None
    channel: str | None
    last_author_role: str | None
    last_body: str | None
    matched_on: list[str]


class ReplySummary(BaseModel):
    distinct_replies: int
    top_reply: str | None
    top_reply_tickets: int
    tickets_without_reply: int


class SimilarTickets(BaseModel):
    total: int
    items: list[SimilarTicket]
    matched_on: list[str]  # the fields all `total` tickets share
    replies: ReplySummary
    articles: list[ArticleSummary]
    articles_read_same: bool


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


class Snapshot(BaseModel):
    snapshot_utc: UtcDatetime | None


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


# The language model connection. It names the provider and the model, and never holds the key.
class ModelConnection(BaseModel):
    provider: str
    model: str
    address: str
    sdk: str
    state: Literal["connected", "no_key", "key_refused", "model_unavailable", "not_answering"]


# One line of the allow-list in assistant.py. id is what a request sends; run is false for a line the desk won't call.
class AllowedModel(BaseModel):
    id: str
    label: str
    provider: str
    model: str
    paid: bool
    run: bool
    mail: bool


class ModelOption(AllowedModel):
    state: Literal["connected", "no_key", "key_refused", "model_unavailable", "not_answering", "not_run"]


class LanguageModels(BaseModel):
    connection: ModelConnection
    options: list[ModelOption]


# The customer mailbox. No mailbox address leaves the API. label, messages and unread are null when they aren't known.
class MailMessage(BaseModel):
    """A customer mail. No address and no date, as everywhere on the desk. `linked_by` is `subject`, `thread`, `manual` or
    null."""
    mail_id: str
    ticket_id: str | None
    linked_by: str | None
    sender_name: str | None
    subject: str | None
    body: str | None


class MatchedTicket(BaseModel):
    ticket_id: str
    subject: str | None
    status: str | None
    similarity: float


class MailMatch(BaseModel):
    match: MatchedTicket | None


class LinkRequest(BaseModel):
    ticket_id: str = Field(min_length=1, max_length=32)


# A log has to say when, so this shape carries a time. A note with `handed_to` is a handoff.
class CaseNote(BaseModel):
    note_id: str
    author: str
    handed_to: str | None
    body: str
    noted_at: UtcDatetime


class CaseNotes(Listing[CaseNote]):
    agents: list[str]


class NoteRequest(BaseModel):
    author: str = Field(min_length=1, max_length=100)
    body: str = Field(min_length=1, max_length=4000)
    handed_to: str | None = Field(default=None, min_length=1, max_length=100)


# `age_hours` is hours to the data snapshot, as on TicketSummary. `approver` is the case's agent, null if it has none.
class FollowUp(BaseModel):
    ticket_id: str
    subject: str | None
    status: str | None
    priority: str | None
    company: str | None
    approver: str | None
    late_reply: bool
    late_resolution: bool
    age_hours: Decimal | None
    draft: str


class MailSync(BaseModel):
    added: int
    linked: int
    unlinked: int
    skipped: int
    remaining: int


# Compose, Approve and Send. The recipient leaves the API here and nowhere else: a person can't approve what they can't read.
class ComposeRequest(BaseModel):
    mail_id: str = Field(min_length=1, max_length=16)
    template: Literal["Answer", "Apology", "Status update", "Ask for details"]
    tone: Literal["Warm", "Neutral", "Formal"]
    language: Literal["English", "Spanish", "French", "German", "Hindi"]


class ComposeDecision(BaseModel):
    """What the language model must return. A null `article_id` means no article supports a reply."""
    model_config = ConfigDict(extra="forbid")

    article_id: str | None
    reply: str = Field(max_length=6000)
    english: str = Field(max_length=6000)


class Draft(BaseModel):
    draft_id: str
    status: str
    recipient: str
    subject: str
    body: str
    english: str
    language: str
    article_id: str
    article_title: str | None
    approvers: list[str]


class ApproveRequest(BaseModel):
    approved_by: str = Field(min_length=1, max_length=100)


class DraftState(BaseModel):
    draft_id: str
    status: str
    approved_by: str


# A log has to say when (contract C10, C13), so this shape carries a time. `recipient`, `subject` and `article_id` come
# from the draft's first row.
class MailAction(BaseModel):
    draft_id: str
    action: str
    actor: str
    acted_at: UtcDatetime
    recipient: str | None
    subject: str | None
    article_id: str | None


class MailCheck(BaseModel):
    address: str
    state: Literal["connected", "not_set_up", "login_refused", "label_missing", "not_answering"]


class MailStatus(BaseModel):
    provider: str
    state: Literal["connected", "not_set_up", "login_refused", "label_missing", "not_answering"]
    label: str | None
    messages: int | None
    unread: int | None
    imap: MailCheck
    smtp: MailCheck


# Triage. The first three fields are closed lists so that results can be sorted and compared: a value outside them never
# leaves the API. test_live.py checks the lists against the values orion_desk holds.
REASON_LIMIT = 300
RECORD_ID_LIMIT = 20


class TriageDecision(BaseModel):
    """What the language model must return. Sent as the schema, and every answer is checked against it."""
    model_config = ConfigDict(extra="forbid")

    category: Literal["account access", "billing", "bug", "feature request", "how-to", "outage"]
    priority: Literal["P1", "P2", "P3", "P4"]
    team: Literal["Customer care", "Customer success", "Technical support"]
    reason: str = Field(min_length=1, max_length=REASON_LIMIT)
    record_ids: list[str] = Field(max_length=RECORD_ID_LIMIT)


# model names the model that decided. dropped_ids counts the IDs taken out because no tool returned them.
class Triage(TriageDecision):
    model: str
    dropped_ids: int
