# <Project> architecture guide

| | |
|---|---|
| **Version** | 0.1 |
| **Date** | YYYY-MM-DD |
| **Applies to** | <repository, language and main frameworks with versions> |
| **Sibling of** | the `specfirst` workflow (the *how*); this document is the *what* |

<!-- The smallest guide the workflow can work with: one page. Keep the § numbers, plans and
     reviews cite them. Rule IDs never change meaning or number once a plan has cited them; a
     retired rule keeps its number with a note. Delete the comments when you fill a section. -->

## 0. What the application is
<Two or three sentences: who uses it, what it does, what it must never get wrong.>

## 1. How to use this document
Assistants read §1.1 before any code and say which layer a change touches. Plans cite rule IDs
per module; reviews cite them back. Breaking a rule needs a decision record (§7), drafted as
`proposed` by the assistant and accepted by a person before implementation (specfirst G1).

### 1.1 Non-negotiables
<!-- At most twelve. Only rules whose breach is visible in a diff. Examples, replace with yours: -->
1. Every change names the layer it touches and follows that layer's rules (§3).
2. Imports point inward: <inner layer> never imports <outer layers or frameworks>.
3. <Business logic lives in one place: where, and where it may not appear.>
4. <Input from users or other systems is never assembled into queries or commands.>
5. No secrets, personal data or credentials in code, tests, fixtures or logs.
6. No new dependency without a line in the plan (specfirst IMPL-1).

## 2. Principles
- **P1** <a principle that explains several rules, e.g. "the core can be tested without the framework">
- **P2**

## 3. Layers and the dependency rule

| Layer | Folder | Holds | May import | Rules |
|---|---|---|---|---|
| <domain> | `<path>` | <models, rules, calculations> | <standard library only> | `DOM-n` |
| <services> | `<path>` | <one use case each> | <domain> | `SVC-n` |
| <storage> | `<path>` | <queries, repositories> | <domain> | `STO-n` |
| <api / ui> | `<path>` | <endpoints, screens> | <services> | `API-n`, `UI-n` |

A new layer or top-level package is a decision record first (specfirst G9).

## 4. Rules per layer
<!-- A short list per layer, each rule with a stable ID. Start with three per layer; add one
     when a review or a learning shows it is needed, not before. -->
### <domain>
- **DOM-1**
### <services>
- **SVC-1**
### <storage>
- **STO-1**
### <api / ui>
- **API-1**

## 5. Testing by layer
<Which kind of test proves which layer: unit for the domain, fakes for services, a test database
for storage, contract tests for endpoints, end to end for the UI. Where expected values in tests
come from.>

## 6. Done and enforcement
<!-- The same commands go into AGENTS.md as `Done commands:`. -->
Done is mechanical, all green: `<lint>`, `<typecheck>`, `<import or dependency rule check, if
the language has one>`, `<tests>`, `specfirst.py check`. Rules that a tool can check are checked
by a tool in CI, not by memory.

## 7. Decision records
<`docs/adr/ADR-###.md` files | recorded here, sequential numbers (specfirst NAME-8)>

## 8. Anti-patterns

| Anti-pattern | Why it hurts | Rule |
|---|---|---|
| | | |

## 9. Change log

| Version | Date | Change |
|---|---|---|
| 0.1 | YYYY-MM-DD | First version |
