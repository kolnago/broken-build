# Skill brick

Instructions and resources a model loads on demand, in the open Agent Skills format.

## Shape

```
modules/orders/agents/assistant/agents/analyst/skills/order_terms/   a part of the analyst (B8)
├── __init__.py            docstring; from .toolset import order_terms_skills; __all__
├── toolset.py             order_terms_skills(): a toolset an agent takes as a tool
├── order-terms/
│   └── SKILL.md           the skill itself: name, description, body
└── test_order_terms.py
```

A skill one agent loads is that agent's part; the analyst imports it as
`from .skills.order_terms import order_terms_skills`. A skill several agents in a module share
lives in the module's `skills/`; one that agents of several modules share lives in the module
that owns the method it describes and is exported from there (M2).

```python
# toolset.py
SKILL_DIR = Path(__file__).parent / "order-terms"

def order_terms_skills() -> SkillToolset:
    return SkillToolset(
        skills=[load_skill_from_dir(SKILL_DIR)], tool_filter=["list_skills", "load_skill"]
    )
```

Imports: `from google.adk.skills import load_skill_from_dir` and
`from google.adk.tools.skill_toolset import SkillToolset`. The agent's builder puts the
toolset in its `tools` list.

## Test

The toolset offers only `list_skills` and `load_skill`, and a strict agent may state a number
it read in the skill:

```python
model = ScriptedModel([call("load_skill", skill_name="order-terms"), "Payment is due 14 days after the invoice."])
answer = await ask(build_analyst(model, FakeOrders([])), "When do I have to pay?")
```

## Traps

- **The skill folder is named after the skill, with a hyphen** (`order-terms`), which is not
  a valid Python package name. Nest it inside the brick's package folder.
- **Name the skill exactly in the agent's prompt.** Told to "load the order terms skill", a
  real model called `load_skill` with `order_terms` and got "not found". The prompt now says:
  load the skill named `order-terms`.
- **Offer only listing and loading** with `tool_filter`, unless the skill needs its scripts
  run. The toolset also has `load_skill_resource` and `run_skill_script`.
- **A skill's text reaches the agent as a tool result,** so the number guard accepts numbers
  quoted from it.
- **Write the skill's body for the agent that will follow it,** including what it must not
  compute.
- **A skill is where an expert's method goes.** When business experts deliver their procedure
  as a document, the steps that need judgement become a skill in the module of that method,
  and the steps that compute become calculators beside it.
