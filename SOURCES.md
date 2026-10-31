# Technical sources and provenance

Checked 31 October 2026. All provider claims are from official documentation. Documentation support is separate from live execution evidence in `review/`.

- Flask deployment: https://vercel.com/docs/frameworks/backend/flask — Flask WSGI application on Vercel; entrypoints, runtime and assets. Actual Python 3.12 deployment tested separately.
- Container support: https://vercel.com/docs/functions/runtimes/container — beta OCI container Functions; this sample uses the native Flask deployment, while retaining a Dockerfile for reproducibility.
- TiDB connection: https://docs.pingcap.com/ai/connect/ — MySQL-compatible connection with verified TLS.
- TiDB plans: https://docs.pingcap.com/tidbcloud/select-cluster-tier/ — MySQL-compatible Starter quotas; PostgreSQL-compatible Starter is a separate public-preview choice. No paid upgrade was performed.
- PostgreSQL capabilities: https://docs.pingcap.com/tidbcloud/pg-extensions-overview/ — vector capability is built in and pgvector-compatible; extension metadata can be registered. Arbitrary upstream extensions are not assumed.
- PostgreSQL vector behaviour: https://docs.pingcap.com/tidbcloud/pg-vector-search/ — fixed-dimension vectors, distance operators, HNSW. Documentation describes index restrictions. Our live preview exposes an adaptive HNSW candidate for a bound vector and an exact scan for a filtered query; EXPLAIN/ANALYZE evidence is needed for actual use. IVFFlat is unavailable.
- TiDB introduction: https://docs.pingcap.com/tidbcloud/tidb-cloud-intro/ — PostgreSQL preview is for development/evaluation; do not describe the course sample as a validated production deployment.
- PyMySQL/TiDB: https://github.com/pingcap/docs/blob/master/develop/dev-guide-sample-application-python-pymysql.md — compatible Python driver and TLS verification.
- MCP server: creator supplied `uvx --from 'pytidb[mcp]' tidb-mcp-server` and the existing TiDB instance. Actual package/server testing found the unbounded MCP v2 dependency failure. Tested pins are recorded in `review/mcp-live-check.json`; credentials remain private.

## Data and company context

`tools/package_database.py` reads existing synthetic CSV/JSON inputs without changing them. The generated SQL manifest records source hashes, table counts and the SQL hash. Full historical messages, null scores, IDs and joins are preserved. Company handbook and staff requests are newly authored fictional context for the creator-approved operating-company scenario. They do not claim real revenue, customers won, business performance or measured AI quality.

The original Orion logo is copied from the existing brand assets without redrawing or distortion. The correct light-surface variants are used. Evaluation answers, security fixtures, credentials and original application source are excluded from the learner database.

## Migration boundary

One provider does not mean one instance or an in-place protocol switch. Course migration must read the learner's MySQL-compatible source, map types/schema, write a separate PostgreSQL-compatible target, and reconcile records before switching the new application. Existing Flask source is not refactored or supplied. TiDB's MySQL-compatible mode also supports vector search; do not manufacture a claim that MySQL or SQL prevents semantic retrieval.
