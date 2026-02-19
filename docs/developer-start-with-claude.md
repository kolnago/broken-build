# Developer's Guide: Choosing the Right Claude Model

A practical guide for developers on when to use Haiku, Sonnet, and Opus — and how to get the most out of each.

---

## The Models at a Glance

| Model | Speed | Cost (relative) | Best For |
|---|---|---|---|
| Haiku | Fastest | 0.33x | Simple, repetitive, well-defined tasks |
| Sonnet | Balanced | 1x | Most coding tasks — your daily driver |
| Opus | Slowest | 3x | Complex reasoning, architecture, hard bugs |

The goal is not to always use the best model — it's to use the **right model for the task**. Defaulting to Opus for everything is like using a sledgehammer to hang a picture frame.

---

## Haiku — The Junior Developer

Think of Haiku as a fast, reliable junior dev. Give it clear, well-scoped tasks with no ambiguity and it will deliver quickly. Ask it to reason about complex business logic and it will disappoint you.

**Good tasks for Haiku:**

- Generating boilerplate code — constructors, getters/setters, CRUD scaffolding
- Writing simple unit tests for straightforward, pure functions
- Generating docstrings and inline comments
- Renaming variables, extracting constants, simple refactors
- Writing simple regex patterns
- JSON and config file manipulation
- Simple SQL queries with no complex joins or subqueries
- Translating straightforward code between similar languages (e.g. Java → C#)
- Git commit message generation
- Formatting and linting fixes

**Avoid Haiku for:**

- Anything requiring understanding of business logic
- Multi-file changes where context matters
- Debugging non-obvious bugs
- Any security-sensitive code
- Tasks where a mistake would be expensive to fix

**Rule of thumb:** If you could hand the task to a junior dev with a clear spec and expect it done right first time, Haiku can handle it.

---

## Sonnet — Your Daily Driver

Sonnet is where you spend most of your time. It has strong reasoning, understands context across files, and handles the majority of real-world coding tasks well. It is fast enough for interactive use and smart enough for serious work.

**Good tasks for Sonnet:**

- Implementing features from requirements or tickets
- Debugging — including non-obvious bugs with some reasoning required
- Multi-file refactoring with clear goals
- Writing comprehensive test suites
- Code reviews and identifying issues
- API integration and working with third-party SDKs
- Database schema design and query optimization
- Understanding and explaining unfamiliar codebases
- Writing technical documentation
- Implementing design patterns
- Most day-to-day agentic coding tasks in Claude Code

**Avoid Sonnet for:**

- Highly complex architectural decisions across a large system
- Deep algorithmic problems requiring extended reasoning
- Situations where you've already tried Sonnet and it got stuck

**Rule of thumb:** Start with Sonnet. If it struggles or produces inconsistent results after a couple of attempts, escalate to Opus.

---

## Opus — The Senior Architect

Opus is slower and significantly more expensive, but it reasons at a different level. Use it when the task genuinely requires deep thinking, not just as a safety net for everything important.

**Good tasks for Opus:**

- System architecture design and technology selection
- Complex refactoring across large codebases — extracting patterns, mapping dependencies, planning migrations
- Debugging subtle, hard-to-reproduce bugs where the cause is non-obvious
- Security audit and identifying vulnerabilities in code
- Performance analysis and optimization strategy
- Designing complex data models and relationships
- Reviewing critical code before production deployment
- Synthesizing requirements from vague or incomplete briefs
- Tasks where Sonnet has already failed or produced inconsistent results

**Avoid Opus for:**

- Anything Sonnet handles well — you're paying 3x for no gain
- Simple or well-defined tasks where speed matters
- High-volume, repetitive generation tasks

**Rule of thumb:** If the task requires a senior developer who understands the bigger picture, not just the immediate file — that's Opus territory.

---

## Cost Optimization Strategy

Since the pricing ratio is roughly **Haiku 0.33x : Sonnet 1x : Opus 3x**, a practical approach is to layer your workflow:

```
Haiku   → first pass for mechanical tasks (boilerplate, comments, simple tests)
Sonnet  → feature implementation, debugging, most agentic tasks
Opus    → architecture, hard problems, final review of critical code
```

A concrete example for a feature ticket:

1. **Haiku** — scaffold the new files, generate the boilerplate class structure
2. **Sonnet** — implement the business logic, write the tests, wire up the integration
3. **Opus** — review the overall approach, catch edge cases, validate the architecture decision

This is how a real team works. Junior handles setup, mid-level does the implementation, senior reviews.

---

## Working with Claude Code (Agentic Workflow)

If you are using Claude Code — either via CLI or the VS Code extension — your workflow shifts from chat to delegation. You are the lead developer. Claude is the team member you assign tasks to.

**How to give good tasks:**

Be specific and contextual. Don't say "fix the bug." Say:

> "In `UserService.ts`, the `getUser` method throws a `NullReferenceException` when the user ID does not exist in the database. It should return `null` instead. Add a null check before the database call and update the unit tests in `UserService.test.ts` accordingly."

The more context you provide upfront, the less back-and-forth — exactly how you'd brief a human developer.

**Use a CLAUDE.md file:**

Add a `CLAUDE.md` file to your project root. This is Claude's onboarding document — treat it like you'd treat the README you'd write for a new team member joining the project.

Include:
- Project overview and architecture
- Key conventions (naming, folder structure, patterns used)
- Tech stack and versions
- What to avoid (legacy patterns being phased out, known workarounds)
- How to run tests and build

Example `CLAUDE.md`:

```markdown
# Project: Payment Service

## Stack
- Node.js 20, TypeScript 5, Express, PostgreSQL
- Jest for testing, Prisma as ORM

## Conventions
- All service files in /src/services, one class per file
- Use Result<T, E> pattern for error handling, never throw in service layer
- Database access only through repository classes, never direct from controllers

## Current Migration
- Migrating from REST to GraphQL — new endpoints should be GraphQL, don't add new REST routes

## Tests
- Run: npm test
- Coverage required: 80% minimum
- Integration tests require local Docker (docker-compose up -d)
```

---

## Quick Reference Card

| Task | Model |
|---|---|
| Generate boilerplate / scaffolding | Haiku |
| Write docstrings and comments | Haiku |
| Simple unit tests | Haiku |
| Git commit messages | Haiku |
| Simple SQL queries | Haiku |
| Implement a feature from a ticket | Sonnet |
| Debug a bug (non-trivial) | Sonnet |
| Multi-file refactoring | Sonnet |
| Write comprehensive test suite | Sonnet |
| Third-party API integration | Sonnet |
| Code review | Sonnet |
| Technical documentation | Sonnet |
| System architecture design | Opus |
| Complex codebase analysis | Opus |
| Migration planning | Opus |
| Hard bug (Sonnet already failed) | Opus |
| Security audit | Opus |
| Critical production code review | Opus |

---

## Privacy Reminder

If you are on a **Pro plan**, go to **Settings → Privacy** and opt out of training data collection. This ensures your code is not used to train future models. Takes 30 seconds and is worth doing immediately after subscribing.

For team or enterprise use, ensure your organization has a formal **Data Processing Agreement** with Anthropic and consider the **Zero Data Retention** addendum — especially relevant in regulated industries like banking or healthcare.

---

*Last updated: February 2026*
