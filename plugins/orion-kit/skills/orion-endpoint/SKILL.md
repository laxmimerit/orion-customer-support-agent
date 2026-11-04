---
name: orion-endpoint
description: The rules every Orion desk API endpoint follows, taken from the routes in api/orion_api/main.py. Use this whenever you add, change or review a route under /api, a response model in models.py, a query in store.py or a report in api/reports, even if the request only says "expose", "return", "list" or "add a field" and never says endpoint.
---

# Build an Orion endpoint

Every route is built the same way, so a client, a test or a reader can trust one route after seeing another. Follow these rules for new routes. Where an older route differs, see "Where older routes differ".

## Stop first if the route writes

Every route today is `GET`, and three things hold that in place: `test_every_route_is_get_only`, read-only sessions in `Store`, and the deployed `orion_desk_reader` login. First writes belong to plan increments 10 and 11, and `docs/communication-contract.md` section 4 is still a proposal. Don't add a `POST`, `PATCH`, `PUT` or `DELETE` route, or loosen any of those three, until the creator authorises it. These rules cover read routes only.

## What one endpoint touches

| File | Add |
|---|---|
| `api/orion_api/models.py` | The response model |
| `api/orion_api/store.py` | The query constant and one `Store` method |
| `api/orion_api/main.py` | The route, next to its neighbours in the same tag |
| `api/tests/conftest.py` | The `FakeStore` method and sample rows |
| `api/tests/test_api.py` (or `test_reports.py`), `api/tests/test_live.py` | See "Tests" |
| `web/lib/api.ts` | The type and client function, if the desk reads the route |

## The route

```python
@app.get("/api/widgets/{widget_id}", response_model=Widget, tags=["widgets"],
         responses=errors(401, 404, 422, 503), summary="One widget with its parts")
def get_widget(widget_id: str = Path(max_length=32), _: str = Depends(role), db=Depends(store)):
    """Exact, case-sensitive ID lookup. Parts are oldest first."""
    widget = db.widget(widget_id)
    if widget is None:
        raise ApiError(404, "widget_not_found", f"No widget has the ID {widget_id!r}.")
    return widget
```

- **Path:** under `/api`, with the first segment naming the area (`tickets`, `customers`, `knowledge`). The path parameter is the column name (`{ticket_id}`). URLs use hyphens (`first-reply`).
- **Function:** a plain `def`, not `async def`. `Store` is synchronous, so FastAPI must run the route in its thread pool; `async def` would block every other request during a query.
- **Decorator:** every route sets `response_model`, `tags`, `responses` and `summary`. The tag is the first path segment. The summary is a short phrase with no full stop.
- **Arguments:** path and query parameters first, then `_: str = Depends(role)`, then `db=Depends(store)`, then any other dependency.
- **Access:** every data route takes `Depends(role)`, which accepts the agent or admin token. Routes under `/api/admin` take `Depends(require_admin)` instead. Auth runs before validation, so a bad request with no token answers 401, not 422. The tokens identify a role, not a person, so the one shared agent token reads every data route. If data should reach only some people, ask before building it.
- **Docstring:** add one when the route has behaviour the summary doesn't say, such as sort order, exact matching or what a count includes. It appears in the API docs.
- **Body:** keep it short. Queries belong in `store.py`; the route turns `None` into a 404 and builds the response dict.

### Which errors to declare

List only what the route can answer, so the docs stay true. Leave 500 out, as every route does.

| Status | Declare when |
|---|---|
| 401 | Always |
| 503 | Always, because every route reads the database |
| 403 | The route uses `require_admin` |
| 404 | The route looks something up by ID |
| 422 | The route has any path or query parameter |

## Parameters

- **IDs in the path:** `Path(max_length=32)`. Lookups are exact and case-sensitive, and an ID is never trimmed (M01). `t00727` and `T00727 ` are 404s.
- **Query parameters:** bound every one, with `ge`/`le` or `min_length`/`max_length`, so no request can ask for an unlimited amount of work. Existing limits: `page` 1 to 100,000, `page_size` default 25 and at most 100, `limit` default 10 and at most 50, `q` 1 to 500 characters.
- **Fixed choices:** type them as `Literal[...]`, as `priority` does. A bad value then answers 422 with no code of your own.
- **Free text:** `strip()` it, then raise `ApiError(422, "invalid_request", ...)` if nothing is left, because `min_length` counts spaces.

## Errors

Every error has one body, which `web/lib/api.ts` reads:

```json
{"error": {"status": 404, "code": "ticket_not_found", "message": "No ticket has the ID 'T99999'."}}
```

- Raise `ApiError(status, code, message)`, never `HTTPException`, so the body is always this shape.
- `code` is snake_case, and a missing record is `<thing>_not_found`.
- `message` is a full sentence for a person. The desk shows it, with the status and code beneath.
- Pick the status with care, because the desk branches on it: a detail page turns 404 and 422 into its not-found page, and shows any other failure as an error.
- Don't catch database errors in a route. The handlers in `create_app` turn them into 503 or 500 and log only the exception type, since driver messages can carry host names. Never put exception text in a response or a log line.

## Response models

- **Always a model:** `response_model` is the filter on what leaves the API. A store row can be wider than the model, and the sample rows in `conftest.py` are wider on purpose, to prove the extra fields are dropped.
- **Field names are column names.** A name from a join or a rename (`plan`, `assigned_to`, `requested_by`) gets a mention in the comment above the models. A computed count reuses an existing name when it means the same thing (`active_cases`).
- **Nulls stay null (M07).** A column that can be null is `str | None` with no default, so the key is always present. Never turn a missing value into 0 or an empty string.
- **Counts are plain `int`.** An average is `Decimal | None`, with `<name>_counted` and `<name>_missing` beside it so nobody has to guess what was left out. If a count leaves rows out, say which in the route docstring.
- **Stored numbers and money are `Decimal`,** which reach the client as exact strings (`"7.9600"`). Use `float` only for a computed score, as `similarity` does.
- **No email, date or time field in a new shape.** The desk shows none, and the older routes that carry them are stripped in `web/lib/api.ts`. Sort by those columns in SQL without returning them. If a route truly needs one, ask the creator first, then use `UtcDatetime`, never a bare `datetime`, so it ends in `Z`.

### Lists

| The route returns | Use | Example |
|---|---|---|
| A whole small set | `Listing[Item]`: `total`, `items` | `/api/customers` (300), `/api/knowledge` (40) |
| A large set, one page at a time | `page`, `page_size`, `total`, `items`, as `TicketPage` | `/api/tickets` (4,000) |
| A ranked result with no full count | `items` and no `total`, as `SearchResults` | `/api/search` |
| A report | `Report[Row]`: `report`, `rows` | `/api/reports/volume` |

`total` always counts the full set, even when `items` is capped: `related_tickets` has a `total` of 111 and 5 items.

Inside a larger response, use `Listing` when the items are capped or the client shows the count; a complete list that needs no count can be a bare list. A nested list stays small: return it whole, or cap it with a true `total` as `related_tickets` does.

Two cases have no precedent, so ask rather than invent one: a set between 300 and 4,000 rows, where nothing yet sets the line for paging, and a nested list that seems to need paging.

## Queries

- **Shape:** a module-level constant in `store.py`, and one `Store` method that opens `with self.pool.connection() as db:` and returns rows as dicts. A method that also returns a count can return a tuple, as `ticket_page` does. An unknown ID returns `None`, and the route makes that a 404.
- **Columns:** when a query returns a model's columns unchanged, take them from the model with `columns(Model)`, so the two can't drift. A query with joins, renames or computed columns names them by hand; add it to `test_hand_written_queries_return_exactly_their_model_columns`.
- **Values:** only ever passed as parameters (`%s`). Request text never becomes part of the SQL string.
- **Sort order:** make it stable and explicit. End `ORDER BY` with the ID, or with the group key in a report, which has no ID. State `NULLS FIRST` or `NULLS LAST` on any column that can be null. The legacy desk ran on MySQL, which orders nulls the other way round from PostgreSQL.
- **Unresolved has two meanings, so choose on purpose.** A case count treats a missing status as still active: `status IS DISTINCT FROM 'resolved'`, as `active_cases` does. A report counts it separately: `unresolved` uses `status <> 'resolved'`, which leaves nulls out, and `status_missing` holds them, so the three columns add up to `tickets`. Using the first form in a report counts null-status tickets twice. No ticket has a null status today, so no test would catch the mistake.
- **Counting across a `LEFT JOIN`:** count the joined column, as `COUNT(t.ticket_id)` does, never `COUNT(*)`. A parent with no children still joins one all-null row, so `COUNT(*)` reports 1 instead of 0.
- **New tables:** the deployed `orion_desk_reader` login needs its own `GRANT SELECT` for a table added later. Without one, the route works locally and fails once deployed.

## A new report

Reports skip the hand-written route:

1. Add `api/reports/<name>.sql`: one `SELECT` or `WITH`, no parameters, and no `COALESCE`, `NULLIF` or `IFNULL`. The leading comment defines every column and becomes the API docs.
2. Add a total row labelled `All`, sorted last, with `GROUPING SETS`.
3. Add the row model. Its field order matches the SQL column order. A report shaped like `priority` reuses `Breakdown` with the key base last, as in `class PriorityRow(Breakdown, PriorityKey)`; the other way round passes every offline test and fails only live.
4. Add one line to `REPORT_ROUTES` in `main.py`. The URL uses a hyphen and the file an underscore (`first-reply`, `first_reply`).
5. Add the path to the `reports` set in `test_every_route_is_under_api_apart_from_docs`.
6. In `test_live.py`, add the report wherever its siblings are named by hand: the `averages` dict and the loops in `test_every_average_counts_what_it_leaves_out` and `test_totals_match_the_ticket_table`.
7. If the desk reads it, follow "The desk".

`test_reports.py` then checks the file against the route, and `test_each_report_returns_exactly_its_model_columns` checks its columns against the model, with no further edits. The token and private-field lists under "Tests" don't apply: all reports share one route factory, and those tests already cover it. To test values, add sample rows to `REPORT_ROWS` in `conftest.py`, which returns `[]` for a report it doesn't know.

## Tests

`FakeStore` returns whatever you gave it, so offline tests prove the route and the response shape, never the SQL. A broken `ORDER BY`, join or count passes them all, and pull-request CI runs nothing else. Only `test_live.py` proves a query, so every new query needs a live test.

In `test_api.py`, which runs against `FakeStore` with no database:

- Add the path to the exact set in `test_every_route_is_under_api_apart_from_docs`, in `pages` unless it is a report.
- Add the path to `test_a_token_is_required`.
- Add the path to `test_no_email_or_date_field_reaches_a_page_route`.
- Assert the full response body with `==`, so an extra field fails.
- Cover a row with nothing recorded: nulls stay null, counts are 0, lists are empty.
- For a lookup: an unknown ID and a wrong-case ID are 404 with the right code; 33 characters is 422; 32 characters gets past validation to a 404.
- For query parameters: each bad value is 422 with code `invalid_request`.

In `test_live.py`, against the real `orion_desk`: check real counts and sort order for a known record such as T00727 or C0086. Where no expected number is on record, compare with direct SQL inside the test, as `test_customer_profile_tickets_are_newest_first` does. Fetch through the `page()` helper, which also checks that no email or date field came back.

## The desk

If the desk reads the route, add a type with the same field names to `web/lib/api.ts`, and a function that wraps IDs in `encodeURIComponent`. Exact decimals are `string | null`. That file is server-only, because it holds the token; a client component reaches the API through a server action in `web/app/actions.ts`, which returns only the fields the browser needs.

## Check it

```bash
cd api && uv run --locked pytest -m "not live"
```

```bash
cd api && uv run --locked pytest -m live
```

```bash
npm run --prefix web typecheck
```

```bash
npm run --prefix web build
```

The first, third and fourth are what pull-request CI runs. The live tests need the database settings in the repository's `.env`, so CI never runs them and they skip themselves without it. A skipped live test proves nothing: if they skipped, say that the new SQL has not run. Then use the `orion-kit:verify` skill to call the route at the running app, and report which checks you actually ran.

## Where older routes differ

Follow the rules above for new work. Don't change these routes unless asked: the desk and the tests depend on them.

- `/api/tickets`, `/api/tickets/{ticket_id}`, `/api/reports/backlog` and `/api/reports/volume` return dates, and the ticket detail also returns `contact_email`. `LEFT_OUT` in `web/lib/api.ts` strips the named date and email fields; `month` passes through because the desk numbers periods itself.
- Nested lists aren't uniform: `support_history` is a `Listing`, while `invoice_history` and `messages` are bare lists.
- `CUSTOMER_INVOICES` sorts on `month` with no `NULLS` clause. The column can be null, though no row is today.
