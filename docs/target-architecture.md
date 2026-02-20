# Target Architecture: Modular Monolith with Clean Architecture
> .NET 8 · Blazor Interactive Server · Oracle · MudBlazor · Entra ID · CQRS/MediatR

---

## 1. Guiding Principles

- **Simplicity over purity** — no abstractions unless they earn their keep
- **Modular monolith** — one deployable unit, strong logical module boundaries in code
- **AI-assisted development friendly** — consistent, predictable patterns across all modules
- **Testability at every layer** — domain unit tests, handler integration tests, E2E tests
- **Legacy schema respect** — EF configurations absorb Oracle schema ugliness; domain stays clean
- **No repository pattern** — EF Core DbContext used directly in handlers; it is already a repository and unit of work

---

## 2. Solution Structure

```
YourSolution.sln
│
├── src/
│   ├── YourApp.Domain
│   ├── YourApp.Application
│   ├── YourApp.Infrastructure
│   └── YourApp.Web
│
└── tests/
    ├── YourApp.Domain.Tests
    ├── YourApp.Application.Tests
    └── YourApp.E2E.Tests
```

Four projects. Not thirty.

---

## 3. Layer Responsibilities

### 3.1 Domain (`YourApp.Domain`)

- Rich domain entities with private setters and factory methods
- Value objects for typed identifiers and domain concepts
- Domain exceptions and status enums
- **No EF references. No infrastructure references. Pure C#.**

Organized by module, mirroring Oracle table prefixes:

```
Domain/
  Common/
    BaseEntity.cs
    DomainException.cs
    ValueObject.cs
  Agreements/            ← A_ tables
    Agreement.cs
    AgreementId.cs
    AgreementStatus.cs
    AgreementType.cs
  Counterparties/        ← CP_ tables (example)
    Counterparty.cs
    CounterpartyId.cs
    CounterpartyStatus.cs
  Netting/               ← N_ tables (example)
    NettingGroup.cs
    NettingGroupId.cs
  Dictionaries/          ← BD_ tables
    Currency.cs
    Product.cs
```

**Domain entity example:**

```csharp
public class Agreement : BaseEntity
{
    private Agreement() { }  // EF constructor

    public static Agreement Create(string name, CounterpartyId counterpartyId, DateOnly startDate)
    {
        if (string.IsNullOrEmpty(name))
            throw new DomainException("Agreement name is required");
        if (startDate < DateOnly.FromDateTime(DateTime.Today))
            throw new DomainException("Start date cannot be in the past");

        return new Agreement
        {
            Id = new AgreementId(Guid.NewGuid()),
            Name = name,
            CounterpartyId = counterpartyId,  // ID only — no navigation property
            StartDate = startDate,
            Status = AgreementStatus.Draft
        };
    }

    public AgreementId Id { get; private set; }
    public string Name { get; private set; }
    public CounterpartyId CounterpartyId { get; private set; }  // cross-module: ID only
    public DateOnly StartDate { get; private set; }
    public AgreementStatus Status { get; private set; }

    public void Activate()
    {
        if (Status != AgreementStatus.Draft)
            throw new DomainException("Only Draft agreements can be activated");
        Status = AgreementStatus.Active;
    }

    public void Terminate(string reason)
    {
        if (Status != AgreementStatus.Active)
            throw new DomainException("Only Active agreements can be terminated");
        Status = AgreementStatus.Terminated;
    }
}
```

---

### 3.2 Application (`YourApp.Application`)

- MediatR Commands, Queries, and Handlers (one file per feature)
- FluentValidation validators per command
- DTOs for data crossing handler boundaries
- Common interfaces (`ICurrentUserService`) implemented by Infrastructure
- MediatR pipeline behaviors (validation, logging, audit)
- **No EF references directly — only via injected DbContext**

Organized vertically by module:

```
Application/
  Common/
    Behaviors/
      ValidationBehavior.cs
      LoggingBehavior.cs
      AuditBehavior.cs
    Interfaces/
      ICurrentUserService.cs
    Exceptions/
      NotFoundException.cs
      ValidationException.cs
  Agreements/
    Commands/
      CreateAgreement.cs          ← Command record + Handler class in one file
      ActivateAgreement.cs
      TerminateAgreement.cs
    Queries/
      GetAgreementById.cs
      GetAgreementsList.cs
    Validators/
      CreateAgreementValidator.cs
    DTOs/
      AgreementDto.cs
      AgreementListItemDto.cs
  Counterparties/
    Commands/ Queries/ Validators/ DTOs/
  Netting/
  Dictionaries/
  Reports/
```

**Command + Handler in one file (key convention):**

```csharp
// Agreements/Commands/ActivateAgreement.cs
public record ActivateAgreementCommand(Guid AgreementId) : IRequest;

public class ActivateAgreementHandler : IRequestHandler<ActivateAgreementCommand>
{
    private readonly AgreementsDbContext _db;

    public ActivateAgreementHandler(AgreementsDbContext db) => _db = db;

    public async Task Handle(ActivateAgreementCommand command, CancellationToken ct)
    {
        var agreement = await _db.Agreements.FindAsync(command.AgreementId, ct)
            ?? throw new NotFoundException(nameof(Agreement), command.AgreementId);

        agreement.Activate();  // domain logic lives here
        await _db.SaveChangesAsync(ct);
    }
}
```

---

### 3.3 Infrastructure (`YourApp.Infrastructure`)

- Module-scoped DbContexts (one per module prefix group)
- EF entity type configurations mapping legacy Oracle schema
- `CurrentUserService` implementing `ICurrentUserService` via Entra ID / `AuthenticationStateProvider`
- External service integrations, Oracle stored proc wrappers if needed
- DI registration

```
Infrastructure/
  Persistence/
    Base/
      BaseAppDbContext.cs         ← audit logic, SaveChanges override
    Agreements/
      AgreementsDbContext.cs
      Configurations/
        AgreementConfiguration.cs
        AgreementVersionConfiguration.cs
    Counterparties/
      CounterpartiesDbContext.cs
      Configurations/
        CounterpartyConfiguration.cs
    Netting/
      NettingDbContext.cs
      Configurations/
    Dictionaries/
      DictionariesDbContext.cs
      Configurations/
  Identity/
    CurrentUserService.cs
  ExternalServices/
  DependencyInjection.cs
```

**Anti-corruption layer — EF configuration absorbs schema ugliness:**

```csharp
// Agreements/Configurations/AgreementConfiguration.cs
public class AgreementConfiguration : IEntityTypeConfiguration<Agreement>
{
    public void Configure(EntityTypeBuilder<Agreement> builder)
    {
        builder.ToTable("A_AGREEMENT");
        builder.HasKey(x => x.Id);
        builder.Property(x => x.Id)
               .HasColumnName("AGREEMENT_ID")
               .HasConversion(v => v.Value, v => new AgreementId(v));
        builder.Property(x => x.Name)
               .HasColumnName("AGREEMENT_NM")
               .HasMaxLength(200);
        builder.Property(x => x.CounterpartyId)
               .HasColumnName("CNTRPRTY_ID")
               .HasConversion(v => v.Value, v => new CounterpartyId(v));
        builder.Property(x => x.Status)
               .HasColumnName("STS_CD")
               .HasConversion<string>();
        builder.Property(x => x.StartDate)
               .HasColumnName("START_DT");
    }
}
```

Domain entity is clean. Oracle schema ugliness is isolated here.

**Module-scoped DbContexts enforce boundaries:**

```csharp
public class AgreementsDbContext : BaseAppDbContext
{
    public DbSet<Agreement> Agreements => Set<Agreement>();
    public DbSet<AgreementVersion> AgreementVersions => Set<AgreementVersion>();

    // Read model for cross-module display queries only
    public DbSet<CounterpartyReadModel> Counterparties => Set<CounterpartyReadModel>();
}
```

An Agreement handler cannot access `NettingGroups` — it's not on its DbContext.

---

### 3.4 Web (`YourApp.Web`)

- Blazor Interactive Server with MudBlazor
- Components organized by module, mirroring Application structure
- UI form/view models separate from Application DTOs
- Entra ID authentication configured here
- Injects Application handlers via MediatR — no API layer needed

```
Web/
  Components/
    Layout/
      MainLayout.razor
      NavMenu.razor             ← MudNavMenu with 10 module sections
      AppBar.razor
    Shared/
      ConfirmDialog.razor
      DataGridWrapper.razor
      LoadingIndicator.razor
  Modules/
    Agreements/
      AgreementList.razor
      AgreementDetail.razor
      AgreementForm.razor
    Counterparties/
    Netting/
    Dictionaries/
    Reports/
  Models/                       ← UI-specific form/view models
    AgreementFormModel.cs       ← MudBlazor form binding, data annotations
    CounterpartyFormModel.cs
  Program.cs
  appsettings.json
```

---

## 4. Module Boundary Rules

This is the discipline that keeps the modular monolith healthy.

### Rules

1. **Each module owns its Oracle table prefix.** Only Agreements module writes to `A_` tables. No exceptions.

2. **Cross-module references are IDs only.** Domain entities hold typed ID value objects (`CounterpartyId`), never navigation properties crossing module boundaries.

3. **Joins in query handlers are acceptable.** One database means SQL joins are cheap and fine. The result DTO belongs to the querying module.

4. **Cross-module operations use MediatR notifications.** No direct service-to-service calls between modules.

5. **Modules do not import each other's domain namespaces.** Enforced by architecture tests.

### Cross-module join pattern (read-only):

```csharp
// AgreementsDbContext — read model, no writes
public DbSet<CounterpartyReadModel> Counterparties => Set<CounterpartyReadModel>();

// CounterpartyReadModel in Agreements module
public class CounterpartyReadModel
{
    public CounterpartyId Id { get; set; }
    public string LegalName { get; set; }
}

// Configured as read-only
builder.ToTable("CP_COUNTERPARTY").HasNoKey(); // keyless = no insert/update/delete
```

### Cross-module event pattern:

```csharp
// Agreements module publishes
public record AgreementActivatedEvent(AgreementId AgreementId, NettingGroupId? NettingGroupId)
    : INotification;

// Netting module listens independently
public class AgreementActivatedHandler : INotificationHandler<AgreementActivatedEvent>
{
    public async Task Handle(AgreementActivatedEvent notification, CancellationToken ct)
    {
        // Netting module reacts — Agreements module has no knowledge of this
    }
}
```

---

## 5. Authentication — Entra ID

Configured in `Web/Program.cs`. Application layer never references Entra ID directly.

```csharp
// Web/Program.cs
builder.Services.AddAuthentication(OpenIdConnectDefaults.AuthenticationScheme)
    .AddMicrosoftIdentityWebApp(builder.Configuration.GetSection("AzureAd"));

// Application/Common/Interfaces/ICurrentUserService.cs
public interface ICurrentUserService
{
    string UserId { get; }
    string DisplayName { get; }
    IEnumerable<string> Roles { get; }
}

// Infrastructure/Identity/CurrentUserService.cs
public class CurrentUserService : ICurrentUserService
{
    private readonly AuthenticationStateProvider _authState;
    // resolves from Blazor AuthenticationStateProvider
}
```

---

## 6. Testing Strategy

Three distinct test suites, each testing a different layer.

```
tests/
  YourApp.Domain.Tests/           ← fast, pure C#, no infrastructure
  YourApp.Application.Tests/      ← integration, real EF + SQLite or Oracle
  YourApp.E2E.Tests/              ← Playwright, full stack
```

### Domain Tests — pure unit tests

```csharp
[Fact]
public void Agreement_Activate_FromDraft_ShouldSucceed()
{
    var agreement = Agreement.Create("Test", new CounterpartyId(Guid.NewGuid()), DateOnly.FromDateTime(DateTime.Today));
    agreement.Activate();
    Assert.Equal(AgreementStatus.Active, agreement.Status);
}

[Fact]
public void Agreement_Activate_FromTerminated_ShouldThrow()
{
    var agreement = Agreement.Create("Test", new CounterpartyId(Guid.NewGuid()), DateOnly.FromDateTime(DateTime.Today));
    agreement.Activate();
    agreement.Terminate("reason");
    Assert.Throws<DomainException>(() => agreement.Activate());
}
```

No mocks. No infrastructure. Milliseconds per test.

### Application Integration Tests — EF + real database

```csharp
public class AgreementHandlerTests : IClassFixture<TestDatabaseFixture>
{
    private readonly AgreementsDbContext _db;
    private readonly IMediator _mediator;

    public AgreementHandlerTests(TestDatabaseFixture fixture)
    {
        _db = fixture.CreateContext();
        _mediator = fixture.CreateMediator();
    }

    [Fact]
    public async Task ActivateAgreement_ValidDraft_ShouldPersistActiveStatus()
    {
        // Arrange
        var agreement = Agreement.Create("Test Agreement", SeedData.CounterpartyId, DateOnly.FromDateTime(DateTime.Today));
        _db.Agreements.Add(agreement);
        await _db.SaveChangesAsync();

        // Act
        await _mediator.Send(new ActivateAgreementCommand(agreement.Id.Value));

        // Assert
        var result = await _db.Agreements.FindAsync(agreement.Id);
        Assert.Equal(AgreementStatus.Active, result.Status);
    }
}
```

**Database options by priority:**
- **SQLite in-memory** — fast, no infrastructure, catches most bugs, small Oracle fidelity gap
- **Testcontainers + Oracle Free** — full fidelity, requires Docker, ideal for CI pipeline
- **Shared Oracle dev schema** — pragmatic if Oracle container setup is too heavy initially

### Where NSubstitute still belongs

Mock non-database dependencies only:

```csharp
var currentUser = Substitute.For<ICurrentUserService>();
currentUser.UserId.Returns("test-user-123");
```

### Architecture Tests — enforce module boundaries automatically

```csharp
[Fact]
public void AgreementsModule_ShouldNotReference_CounterpartiesDomain()
{
    var result = Types.InAssembly(typeof(Agreement).Assembly)
        .That().ResideInNamespace("Application.Agreements")
        .ShouldNot().HaveDependencyOn("Domain.Counterparties")
        .GetResult();

    Assert.True(result.IsSuccessful);
}
```

### E2E Tests — Playwright

```csharp
[Fact]
public async Task AgreementList_ShouldDisplayActiveAgreements()
{
    await Page.GotoAsync("/agreements");
    await Page.WaitForSelectorAsync("[data-testid='agreement-list']");
    var rows = await Page.Locator("tr.agreement-row").CountAsync();
    Assert.True(rows > 0);
}
```

---

## 7. AI-Assisted Development Workflow

The consistent pattern across modules is what makes AI code generation reliable.

### Per-feature generation prompt pattern

> "Using our established pattern, implement the full vertical slice for [feature]:
> - Domain: already exists at `Domain/Agreements/Agreement.cs`
> - Command: `TerminateAgreement.cs` with handler
> - Validator: `TerminateAgreementValidator.cs`
> - DTO: update `AgreementDto.cs` if needed
> - Blazor component: `AgreementDetail.razor` — add Terminate button with MudBlazor confirm dialog
> - Integration test: `TerminateAgreementTests.cs`
>
> Follow the exact pattern in `ActivateAgreement.cs`"

### Migration from legacy system

- Do not migrate old code 1:1 — implement against business requirements
- Use old system as reference only, not as source to translate
- Migrate module by module, strangler-fig style
- Old Angular/API system stays live until each Blazor module is UAT approved
- EF configurations absorb legacy Oracle schema — no schema changes required initially
- Start with low-risk modules (Dictionaries) to prove the pattern, then tackle complex domains (Agreements, Netting)

### Module migration order (suggested)

1. **Dictionaries** — read-heavy, no complex business logic, proves the stack
2. **Counterparties** — moderate complexity, foundational for other modules
3. **Reports** — read-only queries, validates cross-module join patterns
4. **Agreements** — complex domain logic, status machine
5. **Netting** — most complex, depends on Agreements and Counterparties being stable

---

## 8. Key Technology Decisions Summary

| Concern | Decision | Rationale |
|---|---|---|
| Architecture | Modular Monolith | No microservice orchestration overhead; clean module boundaries in code |
| UI | Blazor Interactive Server + MudBlazor | No separate API needed; direct MediatR calls from components |
| Authentication | Entra ID via Microsoft.Identity.Web | Corporate standard; isolated in Infrastructure |
| CQRS | MediatR | Self-contained feature files; AI-friendly; pipeline behaviors |
| Data Access | EF Core direct, no repository | Less abstraction, EF is already repository+UoW, better testability |
| Module Isolation | Module-scoped DbContexts | Compiler-enforced boundary; impossible to accidentally cross modules |
| Schema Strategy | Map to existing Oracle schema via EF configs | Zero migration risk; anti-corruption layer pattern |
| Testing | Domain unit + Application integration + E2E | Right tool per layer; no over-mocking |
| DB for Tests | SQLite (dev) + Testcontainers Oracle (CI) | Fast local feedback; full fidelity in pipeline |
| Cross-module ops | MediatR INotification events | Loose coupling; modules don't know about each other |

---

## 9. Oracle Table Prefix → Module Mapping

Map your actual Oracle prefixes here to finalize module list:

| Oracle Prefix | Module | DbContext |
|---|---|---|
| `A_` | Agreements | `AgreementsDbContext` |
| `BD_` | Dictionaries | `DictionariesDbContext` |
| `N_` | Netting | `NettingDbContext` |
| `CP_` | Counterparties | `CounterpartiesDbContext` |
| _(add your prefixes)_ | | |

---

*Document reflects decisions made in architecture planning session. Update prefix mapping table once all Oracle prefixes are confirmed.*
