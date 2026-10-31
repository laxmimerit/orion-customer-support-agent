"""Escaped table views shared by Flask routes and the static layout preview."""
from html import escape
from urllib.parse import urlencode


def e(value):
    return escape("" if value is None else str(value), quote=True)


def missing(value, unit=""):
    return "Not recorded" if value is None else e(value) + unit


def ticket_table(rows):
    head = "<thead><tr><th>Case</th><th>Subject</th><th>Customer</th><th>Priority</th><th>Status</th><th>Owner</th></tr></thead>"
    body = "".join(
        '<tr><td><a href="/tickets/' + e(r["ticket_id"]) + '">' + e(r["ticket_id"]) + '</a></td>'
        '<td><a href="/tickets/' + e(r["ticket_id"]) + '">' + e(r["subject"]) + '</a></td>'
        '<td>' + e(r["company"]) + '</td><td>' + e(r["priority"]) + '</td><td><span class="status">' +
        e(r["status"]) + '</span></td><td>' + e(r["name"] or "Unassigned") + '</td></tr>' for r in rows)
    return '<div class="table-wrap"><table>' + head + '<tbody>' + (body or '<tr><td colspan="6">No matching tickets.</td></tr>') + '</tbody></table></div>'


def queue(rows, total, query, status, page):
    options = '<option value="">All statuses</option>' + ''.join(
        '<option value="' + s + '"' + (' selected' if s == status else '') + '>' + s.title() + '</option>'
        for s in ("open", "in progress", "pending", "resolved"))
    form = '<form method="get" action="/tickets" class="toolbar"><label>Subject contains <input name="q" maxlength="160" value="' + e(query) + '"></label><label>Status <select name="status">' + options + '</select></label><button>Search</button><a href="/tickets">Clear</a></form>'
    links = []
    for label, target in (("Previous", page - 1), ("Next", page + 1)):
        if target >= 1 and (target - 1) * 40 < total:
            links.append('<a href="/tickets?' + e(urlencode({"q": query, "status": status, "page": target})) + '">' + label + '</a>')
    return form + '<p class="muted">' + str(total) + ' matching tickets · Page ' + str(page) + '</p>' + ticket_table(rows) + '<nav class="paging" aria-label="Ticket pages">' + ' · '.join(links) + '</nav>'


def detail(ticket, messages):
    rows = [("Customer", '<a href="/customers/' + e(ticket["customer_id"]) + '">' + e(ticket["company"]) + '</a>'),
            ("Status", e(ticket["status"])), ("Priority", e(ticket["priority"])),
            ("Owner", e(ticket["agent_name"] or "Unassigned")), ("Created (UTC)", e(ticket["created_at"])),
            ("First response", missing(ticket["first_response_hours"], " hours")),
            ("Customer satisfaction", missing(ticket["csat"], " / 5"))]
    attributes = '<dl>' + ''.join('<dt>' + label + '</dt><dd>' + value + '</dd>' for label, value in rows) + '</dl>'
    thread = ''.join('<article class="message"><header>' + e(m["author_role"]).title() + '<span>' + e(m["created_at"]) + ' UTC</span></header><p>' + e(m["body"]) + '</p></article>' for m in messages)
    return '<p><a href="/tickets">← Ticket queue</a></p><div class="detail-grid"><section><h2>Case information</h2>' + attributes + '</section><section><h2>Conversation</h2>' + thread + '</section></div>'


def customer_list(rows):
    return '<div class="table-wrap"><table><thead><tr><th>Customer</th><th>Plan</th><th>Seats</th><th>Region</th></tr></thead><tbody>' + ''.join('<tr><td><a href="/customers/' + e(r["customer_id"]) + '">' + e(r["company"]) + '</a></td><td>' + e(r["plan_id"]) + '</td><td>' + e(r["seats"]) + '</td><td>' + e(r["region"]) + '</td></tr>' for r in rows) + '</tbody></table></div>'


def customer_detail(customer, tickets):
    return '<p><a href="/customers">← Customers</a></p><p>' + e(customer["plan_id"]) + ' · ' + e(customer["seats"]) + ' seats · ' + e(customer["region"]) + '</p><h2>Support cases</h2><ul>' + ''.join('<li><a href="/tickets/' + e(r["ticket_id"]) + '">' + e(r["ticket_id"]) + ': ' + e(r["subject"]) + '</a> — ' + e(r["status"]) + '</li>' for r in tickets) + '</ul>'


def documents(rows, requests):
    return ''.join('<article class="document"><h2>' + e(r["title"]) + '</h2><p class="muted">Owner: ' + e(r["owner"]) + '</p><p>' + e(r["body"]).replace('\n', '<br>') + '</p></article>' for r in rows) + '<h2>Staff requests</h2>' + ''.join('<article class="document"><h3>' + e(r["request_id"]) + ' · ' + e(r["title"]) + '</h3><p>' + e(r["requester"]) + ' · ' + e(r["body"]) + '</p></article>' for r in requests)


def knowledge(rows):
    return ''.join('<article class="document"><h2>' + e(r["title"]) + '</h2><p class="muted">' + e(r["article_id"]) + ' · ' + e(r["category"]) + '</p><p>' + e(r["body"]) + '</p></article>' for r in rows)


def reports(rows, snapshot):
    return '<p>Ticket status at the supplied snapshot: ' + e(snapshot) + '.</p><table><thead><tr><th>Status</th><th>Tickets</th></tr></thead><tbody>' + ''.join('<tr><td>' + e(r["status"]) + '</td><td>' + e(r["total"]) + '</td></tr>' for r in rows) + '</tbody></table><p class="muted">This report has no date, channel or customer-segment filters.</p>'
