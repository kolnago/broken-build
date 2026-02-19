# Developer Guide to VS Code Copilot Chat Modes

> A practical guide to choosing the right chat mode for the right job — and keeping your premium request budget under control.

---

## Overview of Chat Modes

VS Code Copilot offers three distinct chat modes, each designed for a different type of interaction. Choosing the right one is the single biggest factor in both the **quality of results** and your **premium request (PR) cost**.

| Mode | PR Cost | Autonomy | Best For |
|------|---------|----------|----------|
| **Ask** | ~1 PR flat | None — you act | Questions, explanations, code review |
| **Edit** | 1–5 PRs | Partial — targets files you select | Targeted code changes in specific files |
| **Agent** | 5–50+ PRs | High — explores and acts autonomously | Complex multi-file tasks, refactoring, debugging |

---

## Ask Mode

### How it works
Ask is a single-shot question-answer interaction. You send a message (with optional context), the model responds once, and the loop ends. One conversation turn = one PR, regardless of how complex or long your question is.

### Advantages
- **Predictable cost** — always ~1 PR per question, no surprises
- **Fast** — no tool-calling overhead, response is immediate
- **Great for large context** — you can paste a lot of code and ask a focused question efficiently
- **Safe for sensitive analysis** — the model reads and responds but touches nothing

### When to use Ask
- Explaining what a piece of code does
- Reviewing code for bugs, smells, or violations of principles (SOLID, DDD, etc.)
- Asking architectural questions ("What pattern should I use here?")
- Generating a specific class, method, or snippet you will paste yourself
- Running the architecture analysis prompt from this guide (feed code in chunks, ask focused questions per turn)
- Comparing two approaches or technologies
- Getting a refactoring plan or roadmap (thinking, not doing)

### Tips
- Be specific — the more scoped your question, the more useful the answer
- Paste relevant code directly into the message rather than relying on file references
- Break complex analysis into multiple focused Ask turns instead of one giant prompt
- Use Ask to **plan** what you want Agent to **do**

---

## Edit Mode

### How it works
Edit mode targets one or more files you explicitly select. Copilot reads those files, makes changes, and shows you a diff to accept or reject. It does not autonomously explore your codebase — you control the scope.

### Advantages
- **Controlled scope** — you decide exactly which files are touched
- **Diff review** — every change is shown before being applied, nothing happens silently
- **Medium cost** — more than Ask but far less than Agent for the same targeted task
- **Good for refactoring known locations** — when you already know *where* the change needs to happen

### When to use Edit
- Refactoring a specific class or method you've already identified
- Applying a consistent pattern across a handful of files you select
- Renaming, restructuring, or reorganizing code in known files
- Fixing a bug in a specific file when you already know where it is
- Adding XML docs, comments, or implementing an interface on a specific class
- Migrating a single service or module to a new pattern (e.g. moving to Clean Architecture layers)

### Tips
- Select only the files that need changing — adding unrelated files wastes PRs and confuses the model
- Combine with Ask: use Ask to decide *what* to change, then use Edit to *apply* it
- Always review the diff before accepting — Edit can be overzealous with reformatting

---

## Agent Mode

### How it works
Agent mode runs an autonomous agentic loop. It can read files, search the codebase, run terminal commands, inspect errors, and decide what to do next — iterating until the task is complete or it gets stuck. Each step in the loop can consume one or more PRs, which is why complex tasks can reach 20–50 PRs.

### Advantages
- **Truly autonomous** — handles multi-step tasks without you guiding every action
- **Codebase-aware** — can search, explore, and understand context you didn't explicitly provide
- **End-to-end execution** — can write code, run tests, fix errors, and repeat the cycle
- **Great for cross-cutting concerns** — tasks that span many files or require discovery

### When to use Agent
- Large-scale refactoring across many files where you don't want to manually select each one
- Implementing a new feature that touches multiple layers (e.g. adding a new domain entity end-to-end)
- Debugging a complex issue where the root cause is unknown and needs investigation
- Running and fixing failing tests automatically
- Scaffolding a new module or bounded context from scratch
- Tasks where you want to say "make it work" and let it figure out the how

### When NOT to use Agent
- When you just have a question (use Ask — saves 10–50x the PR cost)
- When you know exactly which file to change (use Edit — more controlled and cheaper)
- When you're exploring or planning (use Ask — Agent will start acting, not just thinking)
- When you're on a tight PR budget and the task is well-defined

### Tips
- **Give precise, scoped instructions** — "refactor `OrderService.cs` to use the repository pattern" is better than "fix my architecture". Vague instructions cause Agent to explore excessively.
- **Point it to specific files** — reduce discovery time by telling Agent exactly where to start
- **Watch for loop behavior** — if Agent keeps re-reading the same files or retrying without progress, cancel and restart with more specific instructions. Runaway loops burn PRs fast.
- **Use Ask first to plan, then Agent to execute** — e.g. use Ask with the architecture analysis prompt to produce a refactoring roadmap, then run Agent on one phase at a time
- **Break big tasks into phases** — "Implement phase 1 of the roadmap: extract repository interfaces" is safer and cheaper than "refactor the whole monolith"

---

## Cost Reference

| Scenario | Recommended Mode | Estimated PRs |
|----------|-----------------|---------------|
| "What does this class do?" | Ask | 1 |
| "Review this file for SOLID violations" | Ask | 1 |
| "Generate a repository interface for this entity" | Ask | 1 |
| "Refactor this one service to use DI" | Edit | 2–5 |
| "Apply Clean Architecture layers to these 3 files" | Edit | 3–8 |
| "Find all places where business logic leaks into controllers" | Agent | 5–15 |
| "Implement a new bounded context end-to-end" | Agent | 15–40 |
| "Refactor the entire data access layer" | Agent | 20–50+ |

---

## Recommended Workflow for Legacy .NET Modernization

Given the goal of refactoring a .NET monolith to Blazor + Clean Architecture + DDD, here is the recommended mode strategy per phase:

**Phase 1 — Understand the codebase**
Use **Ask** exclusively. Feed code in chunks. Run the architecture analysis prompt. This costs ~1 PR per question and produces your roadmap.

**Phase 2 — Foundation work (low-risk fixes)**
Use **Edit** for targeted changes: extracting interfaces, splitting God classes, fixing obvious SOLID violations in known files.

**Phase 3 — Structural refactoring (Clean Architecture layers)**
Use **Agent** for one bounded context or layer at a time. Give it a precise goal and a specific starting file. Review each run before starting the next.

**Phase 4 — Blazor UI migration**
Use **Edit** for component-by-component migration when the target is clear. Use **Agent** only when a component has many dependencies that need discovery.

---

## Quick Decision Guide

```
Do you need an answer or explanation?
  → ASK

Do you need code changed and you know exactly where?
  → EDIT

Do you need the AI to find things, explore, and act autonomously?
  → AGENT
```

---

*Last updated: February 2026*
