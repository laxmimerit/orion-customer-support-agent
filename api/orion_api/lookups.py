"""What the language model may read while it answers: tickets, customers and help articles.

Each tool calls a Store method the routes already use, so the model reaches nothing the desk can't show, and no tool
writes. Results go through named fields or a response model, so emails and dates stay out here as they do on the desk.
The tool arguments come from a model and are checked like any other request.

Lookups also remembers every record it handed over. A source under an answer must be one of these, so the model
cannot cite a record it never saw, and text inside a ticket cannot plant one.
"""
from dataclasses import dataclass
import re

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .assistant import as_data, case_text
from .models import Article, ArticleSummary, CustomerListItem, CustomerProfile, SearchHit

# Across one question. The largest ticket holds about 12,000 characters, so this also bounds the prompt.
MAX_LOOKUPS = 8
SEARCH_LIMIT = 8
CUSTOMER_LIMIT = 10


class NoArguments(BaseModel):
    pass


class ReadTicket(BaseModel):
    ticket_id: str = Field(max_length=32, description="The exact ticket ID, such as T00727")


class ReadCustomer(BaseModel):
    customer_id: str = Field(max_length=32, description="The exact customer ID, such as C0086")


class ReadArticle(BaseModel):
    article_id: str = Field(max_length=32, description="The exact article ID, such as KB004")


class SearchRecords(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    query: str = Field(min_length=1, max_length=500, description="Words describing the problem, or an exact ticket ID")


class FindCustomers(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=100, description="All or part of the company name")


@dataclass(frozen=True)
class Tool:
    description: str
    arguments: type[BaseModel]
    label: str  # What the agent sees while it runs. Fixed, so text planted in a ticket cannot write the desk's status line.


TOOLS = {
    "search_records": Tool("Find tickets and help articles by meaning, closest first, or one ticket by its exact ID. "
                           "Use it when you have no ID. Tickets far outnumber articles, so a search can show no "
                           "article even when one exists: use list_articles to look for articles.",
                           SearchRecords, "Searching the desk"),
    "list_articles": Tool("List every help article with its ID, title and category.", NoArguments,
                          "Listing the help articles"),
    "read_ticket": Tool("Read one ticket with its messages and its customer.", ReadTicket, "Reading a ticket"),
    "find_customers": Tool("Find customers by company name, with their plan and case counts.", FindCustomers,
                           "Finding the customer"),
    "read_customer": Tool("Read one customer's account, subscription, every ticket (newest first) and invoices.",
                          ReadCustomer, "Reading a customer"),
    "read_article": Tool("Read one help article, with tickets on the same subject and others in its category.",
                         ReadArticle, "Reading an article"),
}
SCHEMAS = [{"name": name, "description": tool.description, "input_schema": tool.arguments.model_json_schema()}
           for name, tool in TOOLS.items()]


class Lookups:
    """The tools for one question. It starts out knowing the open case, which is already in the prompt."""

    schemas = SCHEMAS

    def __init__(self, db, embedder, detail):
        self.db, self.embedder = db, embedder
        self.used = 0
        self.seen = {}
        self.note_ticket(detail)

    def note(self, kind, record_id, title):
        self.seen.setdefault(record_id, {"kind": kind, "id": record_id, "title": title})

    def note_ticket(self, detail):
        self.note("ticket", detail["ticket"]["ticket_id"], detail["ticket"].get("subject"))
        if detail["customer"] is not None:
            self.note("customer", detail["customer"]["customer_id"], detail["customer"].get("company"))

    @staticmethod
    def label(name):
        return TOOLS[name].label if name in TOOLS else "Looking something up"

    def run(self, name, arguments):
        """One tool result as (text, is_error). A bad call is told so, and the model can try again.

        A database failure is raised, not returned: the model would read it as a record that does not exist, and
        "the desk could not look" must never reach the agent as "the records don't show this".
        """
        tool = TOOLS.get(name)
        if tool is None:
            return "No tool has that name.", True
        if self.used >= MAX_LOOKUPS:
            return "The lookup limit is reached. Answer from what you have, and say what you could not check.", True
        self.used += 1
        try:
            request = tool.arguments.model_validate(arguments)
        except ValidationError:
            return "Those arguments are not valid for this tool.", True
        result = getattr(self, name)(request)
        if result is None:
            return "No record has that ID. IDs are exact and case-sensitive.", True
        return (result if isinstance(result, str) else as_data(result)), False

    def search_records(self, request):
        # The order of /api/search: an exact ticket ID wins, and only then is the query embedded.
        exact = self.db.exact_ticket(request.query)
        hits = [exact] if exact is not None else self.db.nearest(self.embedder.query(request.query), None, SEARCH_LIMIT)
        for hit in hits:
            self.note(hit["kind"], hit["id"], hit["title"])
        return {"items": [SearchHit.model_validate(hit).model_dump(mode="json") for hit in hits]}

    def list_articles(self, request):
        # The whole set is about 40 short rows. Search alone is not enough: 8 hits can all be tickets.
        rows = [ArticleSummary.model_validate(row) for row in self.db.articles()]
        for row in rows:
            self.note("article", row.article_id, row.title)
        return {"total": len(rows), "items": [row.model_dump() for row in rows]}

    def read_ticket(self, request):
        detail = self.db.ticket(request.ticket_id)
        if detail is None:
            return None
        self.note_ticket(detail)
        return case_text(detail)

    def find_customers(self, request):
        wanted = request.name.casefold()
        rows = [row for row in self.db.customers() if wanted in (row["company"] or "").casefold()]
        for row in rows[:CUSTOMER_LIMIT]:
            self.note("customer", row["customer_id"], row["company"])
        return {"total": len(rows),
                "items": [CustomerListItem.model_validate(row).model_dump(mode="json") for row in rows[:CUSTOMER_LIMIT]]}

    def read_customer(self, request):
        profile = self.db.customer(request.customer_id)
        if profile is None:
            return None
        result = CustomerProfile.model_validate(profile)
        self.note("customer", result.customer_id, result.company)
        for ticket in result.support_history.items:
            self.note("ticket", ticket.ticket_id, ticket.subject)
        return result.model_dump(mode="json")

    def read_article(self, request):
        article = self.db.article(request.article_id)
        if article is None:
            return None
        result = Article.model_validate(article)
        self.note("article", result.article_id, result.title)
        for other in result.more_in_category:
            self.note("article", other.article_id, other.title)
        for ticket in result.related_tickets.items:
            self.note("ticket", ticket.ticket_id, result.title)  # A related ticket's subject is the article's title.
        return result.model_dump(mode="json")

    def cited(self, text):
        """The records the answer names, in the order it names them. A name no lookup returned is left out.

        A record counts if any result held it, a row in a list included: the model's facts about it came from there.
        """
        named = [(match.start(), record) for record_id, record in self.seen.items()
                 if (match := re.search(rf"\b{re.escape(record_id)}\b", text))]
        return [record for _, record in sorted(named, key=lambda pair: pair[0])]
