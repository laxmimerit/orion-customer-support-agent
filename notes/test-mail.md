# Test mail for the support desk

Written for this course. Seed into the `Orion support` label with IMAP APPEND, so seeding sends nothing.
Senders use plus forms of the desk's own mailbox, for example `kgptalkie+fern086@gmail.com`. `tools/seed_test_mail.py` holds the text of mails 2 to 6.

1. Already in the label: the complaint "Slow replies again (case T00727)".
2. Fern's follow-up in that same thread, with no ticket ID in the subject.
3. A complaint with no ticket ID that matches no ticket.
4. The same problem as 3 in other words, from another sender.
5. A complaint in Spanish on an open, late ticket.
6. A mail with an instruction planted in it, telling the desk to ignore its rules.

Mail 2's claims, against the records: the first reply near eight hours against three is true (T00727: 7.96 against 3), at least five cases missing the first-reply target is true (seven of C0086's 18), three days to close is false (25.58 hours), and 12 seats is false (8). Mail 5 is on T01205. Mail 6 names T00727, so it lands on that case.
