# Baseline verification

Verified on 31 October 2026. This records instructor preparation, not a filmed lesson or production-readiness claim.

- Live MySQL-compatible TiDB: all 15 table counts verified, including 4,000 tickets, 36,694 messages, 300 customers and 1,800 invoices. Missing scores remain null; selected conversation joins correctly.
- Real Flask test client against the live database: 18 successful routes/assets, seven negative route/method cases, and denial of a zero-row database write probe under the reference account.
- TiDB MCP: server initialisation and a read-only ticket-count query passed. Tested package pins: pytidb 0.0.14 and MCP 1.30.0. The unpinned MCP v2 dependency was incompatible.
- Learner restore/reset: tested using the real helper on an isolated validation database. Wrong confirmation refused; a changed test subject returned to its baseline after reset. Shared reference unchanged.
- PostgreSQL-compatible TiDB: TLS connection, vector type, cosine distance, HNSW index creation and nearest-fixture result passed. Tiny vectors were capability fixtures, not generated ticket embeddings. Filtered query used an exact scan; bound-vector plan exposed an adaptive candidate requiring runtime interpretation.
- Migration rehearsal: read the actual MySQL source through a SELECT-only account, copied all 15 tables into an isolated schema on the separate PostgreSQL-compatible instance, and reconciled every row/column by canonical checksum. IDs, dates, decimals, booleans, nulls and selected relationships matched.
- Source-only tests: 11 passed, including full original message preservation, search escaping, missing values, pagination, joins and HTML escaping. Original instructor provenance checks are skipped when that separate archive is unavailable in a fresh clone.
- Vercel: deployed actual Flask/Python runtime with sensitive environment variables and read-only credentials; source upload excludes environment files, SQL backups, tools and review artifacts. Requested production domain is https://orion-legacy.vercel.app .
- Browser inspection covered queue, subject search, case, customer, company context and limited reporting. Teaching disclaimer was removed at creator request; synthetic-data explanation remains in course materials.
- Local Docker engine is unavailable: Dockerfile prepared; no local container execution pass claimed. Native Flask deployment is independently exercised.

Private detailed reports and screenshots stay under ignored review/. Credentials remain in ignored owner-only .env files. No original course recordings or voice files were deleted or regenerated.
