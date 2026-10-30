# Local embeddings lesson handoff

Use `nomic-ai/nomic-embed-text-v1.5` through local Python/Sentence Transformers, without Ollama. The model download and runtime installation are part of lesson 7.5. Verify the current official model-card instructions, pin the model revision and package versions, and record them with the output.

Embed only the historical demonstration inputs, using `search_document: ` plus subject and body. Use `search_query: ` for search queries. Keep the same model, 768 dimensions and normalisation for both. Export ticket_id and embedding to Parquet; reject non-finite or wrong-length vectors. Load into PostgreSQL vector(768), build a cosine index and verify a known near-duplicate query. Evaluation inputs/labels are excluded from the index.

Vectors have not yet been generated. The course must show download failures, local resource needs, prefixes and re-embedding when model/configuration changes. Official reference: https://huggingface.co/nomic-ai/nomic-embed-text-v1.5 .
