## Creator decisions adopted 30 October 2026

These decisions supersede conflicting v4 stack, preparation and timing instructions.

- Prepare company facts, fictional datasets, visual brand assets and learner inputs before recording. Installation, configuration, first run, verification and actual troubleshooting are taught on camera. Do not hide the setup behind an already-working environment.
- Teaching sequence: why it is needed, install, configure, small example, connect to Orion, verify, troubleshoot. Expand or split lessons when needed; previous minutes are provisional estimates, not limits.
- Docker Desktop and Compose installation through working services is filmed separately on Mac and Windows, including WSL 2 where required.
- Anthropic API remains the main generative AI and agent provider. Classification uses a suitable available free OpenRouter model first. Jev is a paid decision-model alternative; request the creator's direct Jev access if needed. Evaluate classification against a held-out labelled set. Explain that model names, free availability and limits change while fundamentals remain.
- Embeddings run locally using Nomic Embed Text through Python/Sentence Transformers, without Ollama. Use one pinned model/configuration for documents and queries. PostgreSQL with pgvector stores/searches vectors.
- Separate optional Windows lessons demonstrate Ollama and LM Studio with Claude Code and Claude Desktop where actually supported. Neither is an active Orion dependency. Verify Windows Desktop integration before promising it. Local open models are not local Anthropic weights.
- Supplementary API examples use OpenRouter with the latest available OpenAI Luna and Google Gemini models at recording time. Show keys, request/response handling and differences; do not assume all APIs are interchangeable.
- Use rich six-month analytics data with customer segments, channels, queues, agent workloads, response/resolution times, SLA, satisfaction, billing and events. Dashboard calculations must come from records, with explicit denominators and snapshot dates.
- One learner resources repository: https://github.com/laxmimerit/orion-customer-support-agent-resources . Keep private through recording; public release is a later creator action. Keep instructor answer keys, credentials and recordings outside the repository.
- The dashboard mockup is an explicitly requested pre-production design reference. The working application is still built during the course.
