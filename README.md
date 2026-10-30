# Orion customer support agent resources

Fictional teaching resources for the Claude Masterclass. Start with [the company brief](company/BRIEF.md), [course decisions](course/DECISIONS.md) and [resource readiness](docs/READINESS.md).

## Explore

- Open `dashboard/index.html` in a browser for the interactive analytics mockup. It embeds the supplied demonstration data and works offline.
- `data/` contains CSV, JSON and Parquet; evaluation inputs and labels are separate from history.
- `brand/` contains the visual system and logo assets; `skills/orion-brand/` applies it.
- `resources/part1/` contains lesson input files.
- `docs/METRICS.md` defines chart calculations and denominators.

Run `python3 tools/validate.py` to check the portable data package. Installation and service setup are taught on camera. Model names and free availability are checked at recording time. All companies, people, messages and business results here are synthetic.

## Package contents

4,000 historical tickets, 36,694 messages, 300 customers, nine agents, 1,800 invoices, 300 evaluation cases and 500 untriaged cases. Six months of data support demand, category, plan/region/channel, service, satisfaction, backlog and billing analysis. Forty screenshot attachments and thirty invoice PDFs support multimodal lessons.

See [data dictionary](docs/DATA_DICTIONARY.md), [metric definitions](docs/METRICS.md), [embedding lesson handoff](docs/EMBEDDING_HANDOFF.md) and [provenance](docs/PROVENANCE.md). Download `brand/orion-brand-skill.zip` for the self-contained visual skill.

The dashboard is a functional static design reference, not the completed course application. Live account resources, model installation and the application are tracked separately in [pre-production readiness](course/PREPRODUCTION.md).
