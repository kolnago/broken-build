# Working Effectively with Claude in VS Code

A practical workflow for AI-assisted development — especially for complex tasks like refactoring.

---

## The Core Problem

Claude has a finite context window. In long sessions, earlier content gets compressed or dropped, and Claude starts losing track of decisions, constraints, and progress. The solution is to **manage context deliberately** across short, focused sessions.

---

## The WIP Document System

For any non-trivial task, create a temporary working document in a `/wip` folder at the root of your project.

```
/wip
  auth-refactor.md
  payment-module.md
```

> **These are temporary.** Delete the file when the task is done. No long-term maintenance needed.

---

## Workflow: Phase by Phase

### Phase 1 — User Story

Start a new chat. Ask Claude to draft a user story for the task.

```
Write a user story for refactoring the auth module to use JWT tokens instead of sessions.
```

Paste the result into your `/wip` file.

---

### Phase 2 — Analysis

In the same chat, ask Claude to analyze the story.

```
Analyze this user story. Identify risks, dependencies, edge cases, and things to watch out for.
```

Append the analysis to your `/wip` file.

---

### Phase 3 — Action Plan

Still in the same chat, ask for a concrete action plan.

```
Based on the story and analysis, create a numbered action plan. Each task should be small enough to complete in one focused session.
```

Append this to your `/wip` file. If any tasks feel too large or vague, ask Claude to break them down further before you start executing.

Your `/wip` file now looks like this:

```
## User Story
...

## Analysis
...

## Action Plan
1. Replace session middleware with JWT middleware
2. Update login endpoint to issue JWT tokens
3. Update logout to handle stateless flow
4. Update auth guards across routes
5. Update tests
```

---

### Phase 4 — Execute Tasks (One Chat Per Task)

**Start a fresh chat for each task.** Open your `/wip` file and paste the relevant context at the start of every session:

```
Here's my project doc: [paste /wip/auth-refactor.md]

We're working on task 2: Update login endpoint to issue JWT tokens.

Here's the current state of the relevant file: [paste file content]
```

Work through the task. When it's done, ask Claude to summarize what was done:

```
Summarize what we changed, any decisions we made, and any deviations from the plan.
```

---

### Phase 5 — Update the WIP File

After each task, update your `/wip` file with the outcome before starting the next task. Add a progress log section:

```
## Progress

### Task 1 — Done
Replaced session middleware. Kept legacy session support behind a feature flag
because removing it immediately would break the admin panel.

### Task 2 — Done
Login now issues a signed JWT with 1h expiry. Decided to use RS256 instead of
HS256 for easier key rotation.

### Task 3 — In Progress
...
```

> **Log deviations explicitly.** When reality differs from the plan, write it down. The next chat will make wrong assumptions if it only sees the original plan.

---

### Phase 6 — Done? Delete the File

When all tasks are complete, delete the `/wip` file. It served its purpose. No ongoing maintenance.

---

## Key Principles

**One task per chat.** Mixing concerns (rename + logic change + test update) causes context bloat and confusion.

**Front-load important constraints.** State non-negotiables at the top of every session. Don't assume Claude remembers from 50 messages ago.

**Add a `CLAUDE.md` to your project root.** Claude Code reads this automatically. Put your architectural conventions, patterns, and standing constraints there — so every session starts with the right foundation without you having to paste anything.

**Keep action plan items atomic.** If a task takes more than one session, it's too big. Break it down.

---

## Session Starter Template

Copy-paste this at the start of each task session:

```
Here's my project context:
[paste /wip/your-task.md]

Current task: [task number and description]

Relevant files:
[paste file content]

Constraints to keep in mind:
- [e.g. do not break the public API]
- [e.g. all new code must be TypeScript strict]
```
