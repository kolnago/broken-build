# Enterprise Application Review Checklist
> Tailored for .NET (Blazor / OData+EF) applications in banking/financial context  
> Use this as a prompt for Claude Code: *"Review my application against this checklist and report findings per section"*

---

## 1. Security

### Authentication & Authorization
- [ ] Authentication implemented (e.g. Azure AD, OpenID Connect, OAuth2)
- [ ] Authorization enforced at API/controller level, not just UI level
- [ ] Role-based or claims-based access control in place
- [ ] No hardcoded credentials or secrets in codebase
- [ ] Secrets managed via environment variables, Azure Key Vault, or similar
- [ ] JWT tokens validated properly (expiry, signature, audience)
- [ ] Refresh token rotation implemented

### API Security
- [ ] All endpoints require authentication (no accidental anonymous endpoints)
- [ ] OData query depth/complexity limits configured (prevent expensive queries)
- [ ] Input validation on all user-supplied parameters
- [ ] SQL injection not possible (EF parameterized queries — verify no raw SQL interpolation)
- [ ] CORS policy configured restrictively (not wildcard *)
- [ ] HTTPS enforced, HTTP redirected
- [ ] Rate limiting configured per client/IP

### Sensitive Data
- [ ] No PII or sensitive data logged
- [ ] No sensitive data in query strings (appears in logs/browser history)
- [ ] Sensitive fields not returned in OData responses unless explicitly needed
- [ ] Data masking for fields like account numbers, personal IDs
- [ ] Data classification documented (what data lives where)

---

## 2. Observability & Monitoring

### Logging
- [ ] Structured logging in place (Serilog with named properties)
- [ ] Log levels used correctly (Debug/Info/Warning/Error/Critical)
- [ ] No sensitive data in log messages
- [ ] Correlation ID / trace ID attached to all log events per request
- [ ] Query start/complete logged with: ViewName, DurationMs, RowCount
- [ ] Slow query threshold alerting (e.g. warn if > 1000ms)
- [ ] Errors logged with full exception details and stack trace
- [ ] Logs shipped to ELK / centralized store
- [ ] Log retention policy defined

### Tracing
- [ ] OpenTelemetry instrumentation added
- [ ] Distributed trace ID propagated across service boundaries
- [ ] EF Core queries appear in traces with duration

### Metrics & Dashboards
- [ ] Basic health check endpoint (`/health`) implemented
- [ ] Readiness vs liveness endpoints separated
- [ ] Request rate, error rate, duration metrics exposed
- [ ] Kibana dashboards for: P95 query duration per view, error rate, request volume
- [ ] Alerting configured for critical thresholds

---

## 3. Reliability & Error Handling

### Exception Handling
- [ ] Global exception handler middleware configured
- [ ] API returns consistent error response format (RFC 7807 Problem Details)
- [ ] No raw exception details exposed to clients in production
- [ ] Unhandled exceptions logged with full context

### Resilience
- [ ] Database connection retry policy configured (Polly or EF Core built-in)
- [ ] Timeout policies defined for all external calls
- [ ] Circuit breaker pattern for downstream dependencies
- [ ] Graceful degradation when non-critical services are unavailable
- [ ] Application handles database failover gracefully

### Blazor Specific
- [ ] Blazor circuit disconnect handled gracefully (user-friendly reconnect UI)
- [ ] Long-running operations use cancellation tokens
- [ ] Component dispose pattern implemented (IDisposable/IAsyncDisposable) to prevent memory leaks
- [ ] SignalR connection limits and timeouts configured

---

## 4. Performance

### Database & EF Core
- [ ] EF Core queries reviewed for N+1 problems
- [ ] AsNoTracking() used for read-only queries
- [ ] Pagination implemented (no unbounded result sets)
- [ ] OData max page size configured ($top limit enforced)
- [ ] Oracle indexes align with common OData filter patterns
- [ ] No lazy loading in production (explicit eager loading)

### Application
- [ ] Response compression enabled (Gzip/Brotli)
- [ ] Static assets cached with appropriate headers
- [ ] No blocking synchronous calls in async code paths (no .Result or .Wait())
- [ ] Memory allocations profiled (no large object allocations in hot paths)

### Caching (future readiness)
- [ ] IDistributedCache abstraction used (not IMemoryCache directly) for portability
- [ ] Cache keys follow consistent naming convention
- [ ] Cache invalidation strategy defined for any cached data

---

## 5. Code Quality & Maintainability

### General
- [ ] Solution follows consistent project structure
- [ ] No commented-out dead code committed
- [ ] No TODO/FIXME left in production code paths
- [ ] Dependency injection used throughout (no static/singleton anti-patterns)
- [ ] Configuration via IOptions pattern (not hardcoded values)

### .NET Specific
- [ ] Nullable reference types enabled
- [ ] No suppressed warnings without justification
- [ ] Target framework is current LTS version (.NET 8 or later)
- [ ] NuGet packages up to date, no known vulnerable versions
- [ ] EF Core migrations or DB versioning strategy in place

### Testing
- [ ] Unit tests present for business logic
- [ ] Integration tests for API/OData endpoints
- [ ] Test coverage measured and tracked
- [ ] Tests run in CI pipeline

---

## 6. Deployment & CI/CD

### Pipeline
- [ ] CI pipeline runs on every pull request (build + tests)
- [ ] CD pipeline automates deployment to at least staging
- [ ] No manual steps required for standard deployments
- [ ] Pipeline fails on test failure (no skipped tests in gate)
- [ ] Container image built and versioned per release

### Configuration Management
- [ ] Environment-specific config separated from code
- [ ] No environment-specific code branches (if prod / if staging)
- [ ] Feature flags used for risky changes (not long-lived branches)
- [ ] Database migrations run automatically on deploy or have clear runbook

### Rollback
- [ ] Rollback procedure documented and tested
- [ ] Previous container image versions retained
- [ ] Database migrations are backwards compatible (no breaking schema changes)
- [ ] Deployment produces zero downtime (rolling update or blue/green)

---

## 7. DORA (Digital Operational Resilience Act)
> EU regulation in force from January 2025 — mandatory for financial entities

### ICT Risk Management
- [ ] ICT risk register maintained (what systems, what risks, what mitigations)
- [ ] Application classified by criticality (is this a critical ICT system?)
- [ ] Business Impact Analysis (BIA) documented for this application
- [ ] Recovery Time Objective (RTO) defined — how long can this be down?
- [ ] Recovery Point Objective (RPO) defined — how much data loss is acceptable?
- [ ] ICT risk reviewed at least annually

### Incident Management
- [ ] Incident classification scheme defined (major/minor per DORA thresholds)
- [ ] Incident response procedure documented and known to team
- [ ] Major ICT incidents reported to competent authority within DORA timelines
  - Initial notification: 4 hours after classification
  - Intermediate report: 72 hours
  - Final report: 1 month
- [ ] Incidents logged with timeline, root cause, resolution
- [ ] Post-incident review process in place

### Business Continuity
- [ ] Business Continuity Plan (BCP) covers this application
- [ ] Disaster Recovery (DR) plan documented and tested
- [ ] DR test performed at least annually with results recorded
- [ ] Backup strategy defined, tested, and documented
- [ ] Backup restoration tested (not just backup creation)

### Third Party / Supply Chain
- [ ] All ICT third-party providers identified and documented
- [ ] Contracts with critical ICT providers include DORA-required clauses
  - Audit rights
  - Data access and portability
  - Termination rights
  - Security standards
- [ ] Critical third-party concentration risk assessed (e.g. single cloud provider)
- [ ] Exit strategy documented for critical providers

### Testing & Resilience
- [ ] Vulnerability assessments performed regularly
- [ ] Penetration testing performed at least annually (required for significant institutions)
- [ ] Threat-Led Penetration Testing (TLPT) assessed if applicable (significant institutions)
- [ ] Test results documented and findings remediated with tracking

### Governance
- [ ] Management body has oversight of ICT risk (board level awareness)
- [ ] ICT-related policies reviewed and approved annually
- [ ] Staff training on ICT security and DORA obligations documented
- [ ] DORA compliance owner/contact designated

---

## 8. Documentation

- [ ] README covers: purpose, setup, local dev, deployment
- [ ] Architecture decision records (ADRs) for key technical choices
- [ ] API documented (Swagger/OpenAPI spec published)
- [ ] Runbook exists for common operational tasks (restart, clear cache, check health)
- [ ] On-call/escalation contacts documented
- [ ] Data flow diagram exists (especially important for banking/GDPR)

---

## How to use with Claude Code

Feed this file to Claude Code with a prompt like:

```
Review this application codebase against the attached enterprise checklist.
For each item:
- Mark as PASS, FAIL, PARTIAL, or NOT APPLICABLE
- For FAIL and PARTIAL items, reference the specific file/line where the issue is found
- Prioritize findings by severity: Critical, High, Medium, Low
- Suggest a concrete fix for each failed item
Focus especially on Security and DORA sections given this is a banking application.
```
