# Code Review Strategy with Claude

A practical guide for developers using Claude as a code review partner — how to structure reviews, what to ask, and which model to use at each stage.

---

## The Mental Model

Traditional code review happens after code is written. With Claude, you can shift review left — catching issues at the design stage, during implementation, and again before merge. Think of it as having a senior developer available at every stage of your work, not just at the end.

Claude as reviewer works best when you treat it like a real team member: give it context, be specific about what you want reviewed, and push back if something doesn't seem right.

---

## Review Stages

### Stage 1 — Design Review (Before You Write Code)
**Model: Opus**

Before writing a single line, validate your approach. This is the cheapest place to catch a mistake — changing your mind about architecture costs nothing at this stage and everything later.

Ask Claude to challenge your design:

```
I am planning to implement a payment retry mechanism. 
My approach: store failed payments in a Redis queue, retry every 5 minutes 
up to 3 times, then move to a dead letter queue and alert.

Stack: Node.js, Redis, PostgreSQL.

Review this approach. What are the failure modes I haven't considered? 
What would you do differently?
```

What to expect: Opus will surface edge cases, ask about idempotency, distributed locking, race conditions, what happens if Redis goes down — things you might not think of until you're debugging at 2am.

---

### Stage 2 — Implementation Review (During Development)
**Model: Sonnet**

As you write code, use Sonnet for iterative review. Paste a function or class and ask for targeted feedback. This is a conversation, not a one-shot request.

Good prompts for mid-implementation review:

```
Review this function for correctness and edge cases. 
Focus on error handling — I am not confident I've covered all paths.
```

```
I've implemented the repository layer. Review it for:
1. SQL injection risks
2. Missing null checks
3. Anything that will hurt at scale
```

```
This works but feels wrong. What is the cleaner way to do this?
```

Be specific about what you want reviewed. "Review this code" is too broad. "Review this for thread safety" is actionable.

---

### Stage 3 — Pre-Merge Review (Before Pull Request)
**Model: Sonnet or Opus depending on criticality**

Before opening a PR, do a structured final review. This is where you catch everything — not just bugs, but readability, test coverage, and consistency with the rest of the codebase.

**For standard features — Sonnet:**

Paste the full diff or the changed files and ask for a structured review:

```
Review this PR diff before I open it for team review.
Check for:
- Bugs and logic errors
- Missing error handling
- Security issues (this handles user authentication)
- Test coverage gaps
- Naming and readability issues
- Anything inconsistent with the patterns in the rest of the codebase

Context: This adds OAuth2 login alongside our existing email/password flow.
```

**For critical or complex changes — Opus:**

Use Opus when the change is high-risk: payments, authentication, data migrations, public APIs, anything that is hard to roll back.

---

### Stage 4 — Security Review
**Model: Opus**

Always use Opus for security review. This is not the place to optimise for cost.

Structure your security review with explicit categories:

```
Perform a security review of this code. Check specifically for:

1. Injection vulnerabilities (SQL, command, LDAP)
2. Authentication and authorisation issues
3. Sensitive data exposure (logs, error messages, API responses)
4. Input validation gaps
5. Insecure dependencies or patterns
6. GDPR / data handling concerns

This service handles customer payment data. Flag anything, even if you are not certain — I would rather investigate a false positive than miss something real.
```

---

## Review Prompts Cheat Sheet

### Bug Hunting
```
Review this code purely for bugs and logic errors. 
Ignore style. What will break in production?
```

### Edge Cases
```
What inputs or states would cause this function to behave incorrectly or throw?
List every edge case you can find.
```

### Performance
```
Review this for performance issues at scale.
Assume this endpoint will receive 10,000 requests per minute.
What breaks first?
```

### Readability
```
Review this for readability and maintainability.
Will a developer who has never seen this code understand it in 6 months?
What would you rename, extract, or simplify?
```

### Test Coverage
```
Review my test suite for this module.
What scenarios am I not testing?
What would cause these tests to pass but production to fail?
```

### Database / Query Review
```
Review these database queries.
Check for: N+1 problems, missing indexes, locking issues, 
queries that will degrade as the table grows.
```

### API Design
```
Review this API design before I implement it.
Is it RESTful? Consistent? What will clients find confusing or painful?
What would you change before it is public?
```

---

## Giving Claude Enough Context

A review is only as good as the context you provide. Claude cannot read your mind or know your codebase — you have to tell it what matters.

**Always include:**

- What the code is supposed to do
- What you are most uncertain or worried about
- Any constraints (performance requirements, backwards compatibility, regulatory)
- What is out of scope for this review

**Example of a poor review request:**
```
Review this code.
```

**Example of a good review request:**
```
Review the PaymentProcessor class I've pasted below.

Context:
- This processes real financial transactions — correctness is critical
- It replaces a legacy implementation that had race condition bugs
- Must be idempotent: the same payment ID should never be charged twice
- We use PostgreSQL transactions for consistency

I am most worried about:
1. The retry logic in processWithRetry() — I'm not confident it handles partial failures
2. Whether my database transaction scope is correct

Don't review the logging setup — that's handled separately.
```

---

## Using CLAUDE.md for Consistent Reviews

If you use Claude Code, your `CLAUDE.md` file automatically gives Claude the project context it needs for reviews. Include your review standards there so you don't have to repeat them every time:

```markdown
## Code Review Standards

When reviewing code in this project:
- Error handling: use Result<T,E> pattern, never throw in service layer
- All database access must go through repository classes
- Every public method needs a unit test
- No raw SQL — use the query builder
- Log at info level for all external API calls (request + response)
- Never log PII or payment data
```

With this in place, you can simply say "review this against our project standards" and Claude already knows what that means.

---

## When to Use Claude vs Human Review

Claude is excellent at catching certain categories of issues and less reliable at others. Use both.

| Review Type | Claude | Human Reviewer |
|---|---|---|
| Logic bugs and edge cases | Excellent | Good |
| Security vulnerabilities | Very good (use Opus) | Essential for critical systems |
| Performance issues | Good | Good |
| Readability | Good | Better (knows team conventions) |
| Architecture alignment | Good with context | Essential |
| Business logic correctness | Limited — needs full context | Essential |
| Catching missing requirements | Poor | Essential |
| Political / team dynamics | N/A | Essential |

**The practical rule:** Use Claude to catch the mechanical and technical issues before human review. Your human reviewers then spend their time on business logic, architecture alignment, and the things only they can evaluate — not hunting for null pointer exceptions.

---

## Iterative Review — Push Back and Dig Deeper

If Claude flags something you disagree with, push back. If it approves something you're still unsure about, ask it to look harder.

```
You said the error handling looks fine, but I'm still not 
confident about what happens when the database connection drops 
mid-transaction. Look at it again specifically for that scenario.
```

```
You flagged the retry logic as a potential issue but I think 
it's fine because we use idempotency keys. Does that change 
your assessment?
```

Claude will update its assessment based on new information. Treat it as a dialogue, not a one-shot oracle.

---

## Privacy and Sensitive Code

Before pasting code into Claude, be aware of what it contains:

- **Personal subscription (Pro):** Opt out of training in Settings → Privacy. Your code is retained for 30 days but not used for training after opting out.
- **Enterprise / Team:** Data is not used for training by default. Use Zero Data Retention for maximum protection.
- **Never paste in production secrets, API keys, or credentials** — even for review. Redact them first.
- **For banking, healthcare, or regulated industries:** Ensure your organization has a DPA with Anthropic before using Claude for code review of sensitive systems. A personal Pro account is not sufficient.

---

## Quick Reference — Model Selection for Reviews

| Review Type | Model |
|---|---|
| Design / architecture review | Opus |
| Quick function review | Sonnet |
| Bug hunting | Sonnet |
| Edge case analysis | Sonnet |
| Full PR review (standard) | Sonnet |
| Full PR review (critical/payment/auth) | Opus |
| Security audit | Opus |
| Performance review | Sonnet |
| Test coverage review | Sonnet |
| Database / query review | Sonnet |
| Simple readability pass | Haiku |

---

*Last updated: February 2026*
