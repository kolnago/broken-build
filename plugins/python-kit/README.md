# python-kit

What a Python application built with AI assistants must look like, packaged once instead of
copied into every project.

| Skill | Use it for | Origin |
|---|---|---|
| `python-architecture` | the shape of a project architecture guide and the rules every project shares (layers, exact money, no implicit today, SQL in files, ports with fakes, testing by layer); a template to start one | the common ground of `adk-architecture` and `prijmy-architecture.md` |

The spec-first workflow (`specfirst`, its templates, check script and the implementer and
reviewer subagents) lived here until v0.1.8. Since v0.2.0 it is its own plugin, `specfirst`,
because it works for any language. This kit is the Python-specific half: the *what*, where
`specfirst` is the *how*.

## The architecture guide is the project's

Each project has its own architecture guide, named in its `AGENTS.md`: an ADK app uses the
`adk-architecture` skill from `adk-kit`, Příjmy keeps `prijmy-architecture.md` in its
repository, a new Python project starts from
`skills/python-architecture/templates/architecture-guide.md`. The guide's `§1.1` non-negotiables
and its rule IDs are what `specfirst` plans, briefs and reviews cite.

## Install

```bash
claude plugin marketplace add kolnago/claude-plugins --scope project
claude plugin install specfirst@kolnago-plugins --scope project
claude plugin install python-kit@kolnago-plugins --scope project
```

Other tools: copy or symlink the folders under `skills/` into the tool's skills directory.

## Updating

- `python-architecture` holds only rules that are identical in every project guide. A rule that
  applies to one project belongs in that project's guide.
- Bump `version` in `plugin.json` when a skill changes.
