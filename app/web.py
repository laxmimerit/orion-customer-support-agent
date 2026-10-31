import logging
from flask import Flask, abort, jsonify, render_template, request
from .store import database
from . import views

app = Flask(__name__)
app.config.update(MAX_CONTENT_LENGTH=4096)


def page(title, body, active):
    # body is produced exclusively by views.py, which escapes all database values.
    return render_template("base.html", title=title, content=body, active=active)


@app.after_request
def headers(response):
    response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self'; img-src 'self'; frame-ancestors 'none'; form-action 'self'; base-uri 'none'"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.errorhandler(404)
def not_found(error):
    return page("Page not found", '<p>The requested record does not exist. <a href="/tickets">Return to tickets</a>.</p>', ""), 404


@app.errorhandler(500)
def unavailable(error):
    return page("Service unavailable", "<p>The support desk could not load its records. Please try again.</p>", ""), 500


@app.get("/healthz")
def health():
    try:
        with database() as db:
            valid = db.metadata() is not None
        return jsonify(status="ok" if valid else "unseeded", baseline="orion-legacy-v1"), 200 if valid else 503
    except Exception:
        logging.warning("Database health check failed; credentials and driver details suppressed")
        return jsonify(status="unavailable"), 503


@app.get("/")
@app.get("/tickets")
def tickets():
    query = request.args.get("q", "")
    status = request.args.get("status", "")
    try:
        number = int(request.args.get("page", "1"))
    except ValueError:
        abort(400)
    if len(query) > 160 or number < 1 or number > 1000 or status not in ("", "open", "in progress", "pending", "resolved"):
        abort(400)
    with database() as db:
        rows, total = db.tickets(query, status, number)
    return page("Ticket queue", views.queue(rows, total, query, status, number), "tickets")


@app.get("/tickets/<ticket_id>")
def ticket(ticket_id):
    with database() as db:
        record = db.ticket(ticket_id)
        if not record:
            abort(404)
        messages = db.messages(ticket_id)
    return page(record["ticket_id"] + " · " + record["subject"], views.detail(record, messages), "tickets")


@app.get("/customers")
def customers():
    with database() as db:
        rows = db.customers()
    return page("Customers", views.customer_list(rows), "customers")


@app.get("/customers/<customer_id>")
def customer(customer_id):
    with database() as db:
        record = db.customer(customer_id)
        if not record:
            abort(404)
        tickets = db.customer_tickets(customer_id)
    return page(record["company"], views.customer_detail(record, tickets), "customers")


@app.get("/knowledge")
def knowledge():
    with database() as db:
        rows = db.articles()
    return page("Knowledge base", views.knowledge(rows), "knowledge")


@app.get("/company")
def company():
    with database() as db:
        rows, requests = db.documents(), db.requests()
    return page("Company handbook", views.documents(rows, requests), "company")


@app.get("/reports")
def reports():
    with database() as db:
        rows, meta = db.counts(), db.metadata()
    return page("Status report", views.reports(rows, meta["snapshot_utc"]), "reports")
