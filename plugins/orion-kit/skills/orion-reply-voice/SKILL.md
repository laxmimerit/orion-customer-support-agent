---
name: orion-reply-voice
description: "Draft Orion customer replies as unsent drafts: quote the ticket ID, answer every question, use only ticket and checked-note facts, state unknowns, name the approver. Never send."
---

# Orion reply voice

Use this skill whenever you draft a reply to an Orion customer. The output is always a **draft for a named person to approve**. Nothing is sent by you, ever (backlog M03).

## Rules

1. **Quote the ticket ID.** Put it in the opening line, e.g. "Re: T00727, Invite link expired". Use the ID exactly as stored.
2. **Answer every question the customer asked.** Before writing, list each question in the ticket and its messages, including follow-ups. Give each one its own answer, or say plainly that it is not yet answered and why. Never repeat an earlier agent reply that skipped a question. In T00727 the customer twice asked whether the fix applies to their other team, and both earlier replies ignored it.
3. **Use only facts from the ticket and our checked notes.** "Checked notes" means the ticket record, its messages, the customer summary, and knowledge articles or notes someone has verified. Do not use outside knowledge, guesses, or invented timelines, workarounds, or policies.
4. **Say plainly what we don't know yet.** Use a short sentence such as "We don't yet know whether this applies to your other team. We will confirm once we have checked." Do not hedge vaguely, and do not promise a date or outcome the notes don't support.
5. **A missing value is not zero.** If a field is not recorded (first response, satisfaction, resolution time), say it is not recorded. Never quote it as 0 or as an average that silently excludes it (backlog M07).
6. **When two sources conflict or are ambiguous, say so in the note to the approver** (for example KB004 and KB034 are both titled "Invite link expired"). Do not pick one silently.
7. **No automatic sending.** Do not send, schedule, or queue the reply. Do not mark a draft approved.

## Tone

Plain, warm, specific. Short paragraphs. Address the customer's actual situation (plan, seats, what they said is blocked), but only with facts the ticket states. Do not apologise for things the notes don't show went wrong, and do not blame. If we missed a target and the ticket says so, you may acknowledge the delay factually (e.g. "first response took 7.96 hours against our 3 hour target").

## Output format

Return exactly this structure:

```
DRAFT. NOT SENT. Awaiting approval by: <named person>

Ticket: <ticket ID>   Customer: <customer ID and company>

Subject: Re: <ticket ID>, <ticket subject>

<reply body>

--- Notes for the approver (not part of the reply) ---
Questions found: 1) ... 2) ...
Sources used: <ticket fields, message IDs, article IDs>
Not known / needs checking: ...
```

- If the user has not named an approver, ask who will approve before finalising. Do not invent one and do not leave the line blank.
- If there is no relevant evidence to answer a question, say so in the reply and in the notes instead of drafting an answer.

## Checklist before returning

- [ ] Ticket ID quoted in the reply
- [ ] Every customer question answered or explicitly marked unanswered
- [ ] Every fact traceable to the ticket or a checked note, listed under Sources used
- [ ] Unknowns stated plainly
- [ ] Named approver shown, and the draft is marked NOT SENT
