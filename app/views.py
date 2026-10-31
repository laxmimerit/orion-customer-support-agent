"""Server-rendered, escaped views for the Classic support workspace."""
from datetime import datetime
from decimal import Decimal
from html import escape
from urllib.parse import urlencode


def e(value):
    return escape("" if value is None else str(value), quote=True)


def missing(value, unit=""):
    if isinstance(value, Decimal):
        value = format(value.normalize(), "f")
    return "Not recorded" if value is None else e(value) + unit


def stamp(value):
    if value is None:
        return "Not recorded"
    try:
        parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.strftime("%d %b %Y, %H:%M")
    except ValueError:
        return e(value)


def status_badge(value):
    state = {"open": "open", "in progress": "in-progress", "pending": "pending", "resolved": "resolved"}.get(value, "other")
    return '<span class="status status-' + state + '"><i aria-hidden="true"></i>' + e(value).title() + '</span>'


def priority_badge(value):
    state = value if value in ("P1", "P2", "P3", "P4") else "other"
    return '<span class="priority priority-' + state + '">' + e(value) + '</span>'


def panel(title, body, extra=""):
    return '<section class="panel ' + extra + '"><div class="panel-heading"><h2>' + e(title) + '</h2></div>' + body + '</section>'


def facts(rows):
    # Labels and values are built locally; database strings are escaped at each caller.
    return '<dl class="facts">' + ''.join('<div><dt>' + e(label) + '</dt><dd>' + value + '</dd></div>' for label, value in rows) + '</dl>'


def ticket_table(rows):
    head = '<thead><tr><th>Ticket / subject</th><th>Account</th><th>Priority</th><th>Status</th><th>Assigned to</th><th>Created · UTC</th></tr></thead>'
    body = ''
    for r in rows:
        body += '<tr><td class="subject-cell"><a class="ticket-number" href="/tickets/' + e(r['ticket_id']) + '">' + e(r['ticket_id']) + '</a><a class="subject" href="/tickets/' + e(r['ticket_id']) + '">' + e(r['subject']) + '</a><span class="cell-sub">' + e(r.get('component', '')) + ' · ' + e(r.get('channel', '')).title() + '</span></td>'
        body += '<td><a class="account-link" href="/customers/' + e(r.get('customer_id', '')) + '">' + e(r['company']) + '</a><span class="cell-sub">' + e(r.get('plan_id', '')).title() + '</span></td>'
        body += '<td>' + priority_badge(r['priority']) + '</td><td>' + status_badge(r['status']) + '</td><td>' + e(r.get('name') or 'Unassigned') + '<span class="cell-sub">' + e(r.get('team') or '') + '</span></td><td class="date-cell">' + stamp(r.get('created_at')) + '</td></tr>'
    return '<div class="table-wrap"><table class="ticket-table">' + head + '<tbody>' + (body or '<tr><td colspan="6" class="empty">No matching tickets. Try a different subject or clear the filters.</td></tr>') + '</tbody></table></div>'


def select(name, label, items, selected):
    return '<label>' + e(label) + '<select name="' + e(name) + '">' + ''.join('<option value="' + e(value) + '"' + (' selected' if value == selected else '') + '>' + e(text) + '</option>' for value, text in items) + '</select></label>'


def queue(rows, total, query, status, page, counts=None, agents=(), priority="", owner="", sort="newest"):
    counts = counts or {}
    overview = ''
    if counts:
        all_count = sum(counts.values())
        overview = '<div class="queue-summary"><span><strong>' + str(all_count) + '</strong> Total tickets</span><span><strong>' + str(all_count - counts.get('resolved', 0)) + '</strong> Active cases</span><span><strong>' + str(counts.get('pending', 0)) + '</strong> Pending</span><span><strong>' + str(counts.get('resolved', 0)) + '</strong> Resolved</span></div>'
    form = '<form method="get" action="/tickets" class="toolbar"><label class="search-field">Subject contains<input name="q" type="search" maxlength="160" placeholder="Search ticket subjects…" value="' + e(query) + '"></label>'
    form += select('status', 'Status', [('', 'All statuses')] + [(s, s.title()) for s in ('open', 'in progress', 'pending', 'resolved')], status)
    form += select('priority', 'Priority', [('', 'All priorities')] + [(s, s) for s in ('P1', 'P2', 'P3', 'P4')], priority)
    form += select('owner', 'Assigned to', [('', 'All agents')] + [(a['agent_id'], a['name']) for a in agents], owner)
    form += select('sort', 'Sort by', [('newest', 'Newest first'), ('oldest', 'Oldest first'), ('priority', 'Priority first')], sort)
    form += '<button type="submit">Apply filters</button><a class="clear" href="/tickets">Reset</a></form>'
    links = []
    for label, target in (("Previous", page - 1), ("Next", page + 1)):
        if target >= 1 and (target - 1) * 40 < total:
            links.append('<a href="/tickets?' + e(urlencode(dict(q=query, status=status, page=target, priority=priority, owner=owner, sort=sort))) + '">' + label + '</a>')
    end = min(page * 40, total)
    start = (page - 1) * 40 + 1 if rows else 0
    caption = '<div class="table-caption"><strong>' + str(total) + ' matching tickets</strong><span>Showing ' + str(start) + '–' + str(end if rows else 0) + ' · Page ' + str(page) + '</span></div>'
    return '<p class="page-description">Review customer requests, check ownership and follow the conversation.</p>' + overview + form + '<section class="queue-panel">' + caption + ticket_table(rows) + '<nav class="paging" aria-label="Ticket pages">' + ''.join(links) + '</nav></section>'


def detail(ticket, messages):
    t = ticket
    back = '<a class="back-link" href="/tickets">← Back to ticket workspace</a>'
    ribbon = '<div class="case-ribbon">' + status_badge(t['status']) + priority_badge(t['priority']) + '<span>' + e(t['category']) + '</span><span>' + e(t['component']) + '</span><span>Via ' + e(t['channel']) + '</span></div>'
    info = facts([('Assigned to', e(t.get('agent_name') or 'Unassigned')), ('Team', e(t.get('agent_team') or 'Unassigned')), ('Created · UTC', stamp(t['created_at'])), ('First response · UTC', stamp(t.get('first_response_at'))), ('Resolved · UTC', stamp(t.get('resolved_at'))), ('Reopened', e(t['reopened_count'])), ('Escalated', 'Yes' if t['escalated'] else 'No')])
    account = '<a class="account-title" href="/customers/' + e(t['customer_id']) + '">' + e(t['company']) + '</a>' + facts([('Customer ID', e(t['customer_id'])), ('Plan', e(t['plan_id']).title()), ('Seats', e(t.get('seats'))), ('Region', e(t['region'])), ('Contact', e(t.get('contact_email')))])
    service = facts([('Response target', missing(t.get('sla_response_hours'), ' hours')), ('First response', missing(t.get('first_response_hours'), ' hours')), ('Resolution target', missing(t.get('sla_resolution_hours'), ' hours')), ('Resolution time', missing(t.get('resolution_hours'), ' hours')), ('Satisfaction', missing(t['csat'], ' / 5'))])
    if t.get('first_response_hours') is not None and t.get('sla_response_hours') is not None:
        met = float(t['first_response_hours']) <= float(t['sla_response_hours'])
        service = '<p class="service-outcome ' + ('met' if met else 'missed') + '">Response target ' + ('met' if met else 'missed') + '</p>' + service
    thread = ''
    for m in messages:
        customer = m['author_role'] == 'customer'
        # The snapshot stores message roles, not individual author identities.
        author = t['company'] if customer else 'Orion Support' if m['author_role'] == 'agent' else str(m['author_role']).title()
        thread += '<article class="message ' + ('customer-message' if customer else 'agent-message') + '"><header><div class="avatar" aria-hidden="true">' + e(str(author)[:1]).upper() + '</div><div><strong>' + e(author) + '</strong><span class="cell-sub">' + e(m['author_role']).title() + '</span></div><time>' + stamp(m['created_at']) + ' UTC</time></header><div class="message-body">' + e(m['body']).replace('\n', '<br>') + '</div></article>'
    conversation = '<section class="panel conversation"><div class="panel-heading"><h2>Conversation</h2><span>' + str(len(messages)) + ' messages</span></div>' + (thread or '<p class="empty">No messages recorded.</p>') + '</section>'
    return back + ribbon + '<div class="case-layout"><div class="case-main">' + panel('Request summary', '<p class="request-summary">' + e(t['body']).replace('\n', '<br>') + '</p>') + conversation + '</div><aside class="case-sidebar">' + panel('Case ownership', info) + panel('Customer account', account) + panel('Service levels', service) + '</aside></div>'


def customer_list(rows):
    table = '<div class="table-wrap"><table><thead><tr><th>Account</th><th>Plan</th><th>Seats</th><th>Region</th><th>Industry</th><th>Active cases</th><th>All cases</th></tr></thead><tbody>'
    for r in rows:
        table += '<tr><td><a class="account-link" href="/customers/' + e(r['customer_id']) + '">' + e(r['company']) + '</a><span class="cell-sub">' + e(r['customer_id']) + ' · ' + e(r['contact_email']) + '</span></td><td>' + e(r['plan_id']).title() + '</td><td>' + e(r['seats']) + '</td><td>' + e(r['region']) + '</td><td>' + e(r['industry']) + '</td><td>' + e(r['active_count']) + '</td><td>' + e(r['case_count']) + '</td></tr>'
    return '<p class="page-description">Customer accounts, subscription details and support history.</p><section class="queue-panel"><div class="table-caption"><strong>' + str(len(rows)) + ' customer accounts</strong><span>Company name · A–Z</span></div>' + table + '</tbody></table></div></section>'


def customer_detail(customer, tickets, invoices=(), subscription=None):
    c = customer
    overview = facts([('Account ID', e(c['customer_id'])), ('Industry', e(c['industry'])), ('Country', e(c['country'])), ('Region', e(c['region'])), ('Company size', e(c['company_size'])), ('Contact', e(c['contact_email'])), ('Joined', stamp(c['signup_date']))])
    sub = subscription or {}
    details = facts([('Plan', e(sub.get('plan_name') or c['plan_id']).title()), ('Seats', e(c['seats'])), ('Subscription', e(sub.get('subscription_id')) or 'Not recorded'), ('Status', e(sub.get('status')) or 'Not recorded'), ('Started · UTC', stamp(sub.get('started_at')))])
    billing = '<div class="table-wrap"><table><thead><tr><th>Month</th><th>Seats</th><th>Unit price · USD</th><th>Total · USD</th><th>Status</th></tr></thead><tbody>' + ''.join('<tr><td>' + e(r['month']) + '</td><td>' + e(r['seats']) + '</td><td>' + format(Decimal(str(r['unit_price_usd'])), ',.2f') + '</td><td>' + format(Decimal(str(r['total_usd'])), ',.2f') + '</td><td>' + e(r['status']).title() + '</td></tr>' for r in invoices) + '</tbody></table></div>'
    return '<a class="back-link" href="/customers">← Back to customer accounts</a><div class="account-overview">' + panel('Account details', overview) + panel('Subscription', details) + '</div>' + panel('Support history · ' + str(len(tickets)) + ' tickets', ticket_table(tickets)) + panel('Invoice history', billing)


def documents(rows, requests):
    return '<p class="page-description">Operating context, support policies and current improvement requests.</p>' + ''.join('<article class="document"><h2>' + e(r['title']) + '</h2><p class="muted">Owner: ' + e(r['owner']) + '</p><p>' + e(r['body']).replace('\n', '<br>') + '</p></article>' for r in rows) + '<h2>Staff requests</h2>' + ''.join('<article class="document"><h3>' + e(r['request_id']) + ' · ' + e(r['title']) + '</h3><p class="muted">' + e(r['requester']) + '</p><p>' + e(r['body']) + '</p></article>' for r in requests)


def knowledge(rows):
    table = '<div class="table-wrap"><table><thead><tr><th>Article</th><th>Title</th><th>Category</th></tr></thead><tbody>' + ''.join('<tr><td>' + e(r['article_id']) + '</td><td><a class="account-link" href="/knowledge/' + e(r['article_id']) + '">' + e(r['title']) + '</a></td><td>' + e(r['category']) + '</td></tr>' for r in rows) + '</tbody></table></div>'
    return '<p class="page-description">Product guidance and troubleshooting references for customer support.</p><section class="queue-panel"><div class="table-caption"><strong>' + str(len(rows)) + ' published articles</strong></div>' + table + '</section>'


def knowledge_article(row):
    return '<a class="back-link" href="/knowledge">← Back to knowledge base</a><article class="document"><p class="muted">' + e(row['article_id']) + ' · ' + e(row['category']) + '</p><p>' + e(row['body']).replace('\n', '<br>') + '</p></article>'


def reports(rows, snapshot):
    table = '<div class="table-wrap"><table><thead><tr><th>Status</th><th>Tickets</th></tr></thead><tbody>' + ''.join('<tr><td>' + status_badge(r['status']) + '</td><td>' + e(r['total']) + '</td></tr>' for r in rows) + '</tbody></table></div>'
    return '<p class="page-description">Ticket status at the supplied snapshot: ' + e(snapshot) + '.</p>' + panel('Ticket status summary', table) + '<p class="muted">This report has no date, channel or customer-segment filters.</p>'
