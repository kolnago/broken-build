# Claude Code for AI-Driven Development — Proposal for Security Approval

## Summary

This document outlines a proposal to adopt Claude Code as an agentic AI development tool, routed through our existing Google Cloud or Azure infrastructure, and identifies the key open items required for security approval.

---

## What is Claude Code

Claude Code is an agentic AI development tool built by Anthropic. It runs as a command-line application on a developer's local machine and connects to Claude — Anthropic's AI model — to autonomously perform software development tasks. Unlike traditional code assistants, Claude Code can read an entire codebase, plan and implement changes across multiple files, run tests, and iterate on results with minimal human intervention.

For more details: `docs.anthropic.com/claude-code`

---

## Why Claude Code — Not Just Another Copilot

The team currently uses GitHub Copilot for AI-assisted development. Claude Code represents a fundamentally different capability — the shift from **AI as assistant** to **AI as autonomous developer**.

### GitHub Copilot vs Claude Code

| | GitHub Copilot | Claude Code |
|---|---|---|
| Model | Autocomplete / suggest | Autonomous agent |
| Interaction | Developer drives, AI assists | AI drives, developer reviews |
| Scope | Current file / function | Entire codebase |
| Tasks | Write this function | Implement this feature end-to-end |
| Agentic | ❌ No | ✅ Yes |

### What Claude Code can do that Copilot cannot
- Read and understand the entire repository structure
- Make changes across multiple files in one task
- Run tests, observe failures, and fix them autonomously
- Execute terminal commands and iterate until the task is complete
- Reason about architecture, not just syntax

### Business case
The productivity gain is qualitatively different. Copilot saves seconds per line. Claude Code saves hours per feature. The developer shifts from writing code to reviewing and directing — significantly higher leverage, especially for complex enterprise applications.

---

## Security Architecture — Why This Is Safe Enough

### No new vendor relationship required
Claude is available via **Google Cloud Vertex AI** and **Azure AI Foundry** — both platforms where the bank already holds enterprise agreements. This is not introducing a new vendor. It is extending the use of existing approved infrastructure.

### Available routes

| Route | Infrastructure | Existing Agreement |
|---|---|---|
| GitHub Copilot | Microsoft/GitHub | ✅ Already approved |
| Vertex AI | Google Cloud | ✅ Existing agreement |
| Azure AI Foundry | Microsoft Azure | ✅ Existing agreement |

Vertex AI and Azure AI Foundry are **more controlled and auditable** than GitHub Copilot — they provide explicit EU data residency, VPC controls, and full audit logging that Copilot does not offer.

### Available Claude Models

All three models are generally available on Vertex AI and Azure AI Foundry:

| Model | Best for | Cost |
|---|---|---|
| **Claude Opus 4.6** | Complex reasoning, architecture decisions, hardest tasks | Highest |
| **Claude Sonnet 4.6** | Everyday development tasks, balanced performance | Medium |
| **Claude Haiku 4.5** | Simple/repetitive tasks, fast responses, high-volume | Lowest |

For most development workflows Sonnet 4.6 is the default. Haiku 4.5 is useful for simple or repetitive tasks where cost and speed matter. Opus 4.6 is reserved for the most demanding tasks.

---

## Compliance Points

| Concern | Status |
|---|---|
| EU data residency | ✅ Regional endpoints available (e.g. `europe-west1`) |
| Existing DPA covers usage | ✅ No new vendor DPA needed |
| FedRAMP High boundary | ✅ Operates within Google Cloud authorization |
| ISO 27001 / SOC 2 | ✅ Inherited from Google Cloud / Azure infrastructure |
| Data processed outside EU | ✅ Prevented when EU regional endpoint configured |
| Source code leaves corporate perimeter | ✅ Prevented via VPC Service Controls |
| Audit trail of AI usage | ✅ Full audit logging via Google Cloud / Azure audit trails |

---

## Data Retention & Zero Data Retention (ZDR)

This is a critical point for banking compliance.

### Default API behaviour
- API inputs and outputs are retained for **7 days** then automatically deleted
- Anthropic **does not use commercial API data for model training** by default — explicit opt-in required

### Zero Data Retention (ZDR) — available on request
- Enterprise API customers can request a ZDR agreement with Anthropic
- Under ZDR: prompts and responses are **processed in real-time and immediately discarded** — no logging, no storage beyond abuse detection
- ZDR applies to Claude Code when using a commercial API key
- ZDR must be **negotiated with Anthropic sales team** — not enabled by default

### Important nuance — Vertex AI and Azure AI Foundry
- ZDR applies to the Anthropic API directly only — for Vertex AI and Azure AI Foundry, the respective platform data retention policies apply instead
- On Vertex AI / Azure you rely on **Google Cloud / Azure data governance** rather than Anthropic ZDR
- For banking this is likely acceptable — it falls under already-approved vendor policies

### Summary

| Route | Data retention | Training on your data |
|---|---|---|
| Anthropic API (default) | 7 days | ❌ No |
| Anthropic API with ZDR | Immediate discard | ❌ No |
| Vertex AI | Google Cloud policy | ❌ No |
| Azure AI Foundry | Azure policy | ❌ No |

---

## Additional Security Controls

- **VPC Service Controls** — requests never leave defined network perimeter
- **Audit logging** — every API call logged and traceable
- **EU regional endpoint mandatory** — enforced at infrastructure level, not left to individual developers
- **No training on customer data** — confirmed across all commercial/enterprise routes

### Model Guardrails — Important Consideration

Both platforms offer an AI safety/filtering layer that sits in front of Claude. This is worth evaluating carefully for a developer tooling use case.

**Google Cloud — Model Armor**
Filters prompts and responses for harmful content. Configurable with custom policies.
⚠️ Risk: May false-positive on legitimate banking/security development tasks (encryption code, auth flows, vulnerability analysis). Configurability for enterprise developer use cases should be confirmed with Google before committing to this route.
More info: `cloud.google.com/security/products/model-armor`

**Azure AI Foundry — Azure AI Content Safety**
Microsoft's equivalent filtering layer, similarly configurable.
⚠️ Same risk applies — needs evaluation for developer tooling false positive rate.
More info: `azure.microsoft.com/products/ai-services/ai-content-safety`

**Key question for both platforms:** Can the filtering layer be tuned or selectively disabled for approved internal developer tooling use cases? This should be confirmed before final platform selection.

---

## Claude Code Setup (Vertex AI)
Three environment variables route Claude Code through existing Google Cloud infrastructure:

```bash
export CLAUDE_CODE_USE_VERTEX=1
export CLOUD_ML_REGION=europe-west1
export ANTHROPIC_VERTEX_PROJECT_ID=YOUR-GCP-PROJECT-ID
```

---

## Open Items for Security Approval

- [ ] Confirm Vertex AI or Azure AI Foundry is preferred route given existing agreements
- [ ] Confirm EU region is approved and configured at infrastructure level
- [ ] Confirm Claude Code usage is in scope of existing Google Cloud / Azure DPA
- [ ] Check with Google or Microsoft account manager if explicit sign-off needed for Claude models specifically
- [ ] Define internal policy on what code/data developers may share with Claude Code (e.g. no production data, no credentials)
- [ ] Confirm VPC Service Controls are configured to restrict egress appropriately
- [ ] Evaluate Model Armor (Vertex AI) / Azure AI Content Safety false positive rate for banking development tasks
- [ ] Confirm guardrail layer can be tuned or selectively disabled for internal developer tooling

---

## References
- Vertex AI Claude docs: `cloud.google.com/vertex-ai`
- Azure AI Foundry Claude docs: `ai.azure.com`
- Claude Code setup: `docs.anthropic.com/claude-code`
- Anthropic security & privacy: `anthropic.com/trust`
