# n8n Workflows - Production-style Automation Portfolio

A small collection of n8n workflows, each solving a real business case, exported as importable JSON and documented node by node. They are written the way I build client automations: input validation before any external call, explicit error paths, idempotent writes, credentials referenced by name, and sticky notes on the canvas so the next person can read the workflow without me.

Built and maintained by **Juan Ignacio Viglianco** - n8n / AI automation engineer (Python, TypeScript, 6+ years backend).

## Workflows

| # | Workflow | One-liner | Trigger | Integrations |
|---|----------|-----------|---------|--------------|
| 01 | [Lead Intake, Enrichment & CRM Routing](./01-lead-intake-enrich-crm/) | Website form → validate → enrich via API → business leads to HubSpot + Slack `#sales`, personal-domain leads to a "Low priority" Google Sheet; form gets a real 200/400. | Webhook | HTTP (enrichment API), HubSpot, Slack, Google Sheets |
| 02 | [Webhook Validation → Sheets + Slack (with Daily Digest)](./02-webhook-validate-sheets-slack/) | Order events → Set mapping → Code validation + dedupe → valid rows to Google Sheets + Slack `#orders` (200), invalid ones alert `#ops` (422); a second Schedule trigger posts yesterday's summary at 08:00. | Webhook + Schedule | Google Sheets, Slack |
| 03 | [Upwork Job Monitor](./03-upwork-job-monitor/) | Every 15 min: poll a job feed → keyword + budget filter + dedupe → Claude scores the fit against my profile → Telegram alert for fit >= 7. My own client-acquisition automation (dogfooding). | Schedule | RSS, Anthropic Messages API, Telegram |

Each folder contains `workflow.json` (the n8n export) and a `README.md` with: what it does, trigger, node-by-node walkthrough, required credentials, how to test (sample `curl` / pinned data), error-handling notes and a Mermaid flowchart. Canvas screenshots: TODO after import.

## Import

**n8n → Workflows → Import from file** (or *Import from URL* pointing at the raw `workflow.json`). Then:

1. Create the credentials listed in the workflow README using the exact names shown (the JSON references credentials by name with placeholder ids; n8n will ask you to map them on first open).
2. Replace the obvious placeholders (`PLACEHOLDER_SPREADSHEET_ID`, `PLACEHOLDER_TELEGRAM_CHAT_ID`, placeholder API URLs).
3. Run the test in the README, then activate.

Tested export format: n8n 1.x (`executionOrder: v1`). Node versions used: webhook 2, set 3.4, if 2.2, filter 2.2, code 2, httpRequest 4.2, scheduleTrigger 1.2, slack 2.2, googleSheets 4.5, hubspot 2.1, telegram 1.2, rssFeedRead 1, respondToWebhook 1.1.

## Conventions

- **No secrets in the repo.** Credentials are referenced by *name* only (`credentials: { slackApi: { id: "PLACEHOLDER_...", name: "Slack Bot Token" } }`). All URLs, ids and chat ids are obvious placeholders.
- **Sticky notes on every workflow.** Each canvas is split into numbered sections (Intake / Validation / Enrichment / Routing, etc.) with a sticky note explaining the why, not just the what.
- **Validate first, call APIs second.** Every inbound payload is normalised and validated in a Code node before anything external is touched; webhooks always answer with a meaningful status (200 / 400 / 422) via *Respond to Webhook* nodes.
- **Explicit error paths.** External HTTP calls use retries with back-off and either *continue (error output)* or *continue (regular output)* so a vendor outage degrades gracefully instead of dropping data.
- **Error workflow.** Attach an *Error Workflow* (Workflow settings → Error workflow) that posts failed executions to a Slack/Telegram channel, and enable *Save failed executions*. It is intentionally not embedded in the exports because the id is instance-specific.
- **Idempotency.** CRM writes are upserts keyed by e-mail; event ingestion carries a `dedupe_key`; the job monitor remembers processed GUIDs in workflow static data.
- **Left-to-right layout.** Nodes are positioned so the flow reads left to right, branches top (happy path) / bottom (reject path).

## Validation

`scripts/validate.py` checks every `workflow.json`: valid JSON, required top-level keys, every node has `id` / `name` / `type` / `typeVersion` / `position`, unique node names, and every connection points at an existing node. It prints a per-workflow node count.

```bash
python scripts/validate.py
```

## License

MIT - see [LICENSE](./LICENSE).
