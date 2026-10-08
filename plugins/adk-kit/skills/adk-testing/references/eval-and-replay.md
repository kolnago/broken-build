# Golden replay and evaluation (ADK 2.x)

## `adk test` (golden replay)

- Layout: `<agents_dir>/<agent>/tests/<case>.json`, each a recorded session
  (`{"events": [...]}` with user messages, model function calls, tool
  responses, `nodeInfo.path`).
- `adk test <agents_dir>` replays: model responses are served from the
  recording (mock model), the agent runs for real, and normalised events are
  compared (ids, timestamps, usage metadata excluded).
- Create/refresh: write a JSON with just the user events (or copy one), then
  `adk test --rebuild <agents_dir>` runs the real model and rewrites the file.
  Review the diff like code.
- Examples: `contributing/samples/hitl/tool_confirmation/tests/*.json`,
  `contributing/samples/workflows/*/tests/`.
- Good for: ADK upgrades, prompt/graph refactors, HITL flows.

## `adk eval` / AgentEvaluator

```bash
adk eval my_agents/home_automation tests/home.evalset.json \
  --config_file_path tests/eval_config.json --print_detailed_results
```

```python
from google.adk.evaluation import AgentEvaluator

async def test_quality():
  await AgentEvaluator.evaluate(
      agent_module='my_agents.home_automation',
      eval_dataset_file_path_or_dir='tests/eval/home/simple.test.json',
      num_runs=2)
```

`*.test.json` files sit next to a `test_config.json`; `.evalset.json` files go
with `--config_file_path`.

`eval_config.json`:

```json
{"criteria": {
  "tool_trajectory_avg_score": {"threshold": 1.0, "match_type": "EXACT"},
  "response_match_score": 0.6}}
```

| Criterion | Measures |
|---|---|
| `tool_trajectory_avg_score` | exact tool calls per turn (`match_type` EXACT / IN_ORDER / ANY_ORDER) |
| `response_match_score` | ROUGE-1 vs reference |
| `final_response_match_v2` | LLM judge semantic match |
| `rubric_based_final_response_quality_v1`, `rubric_based_tool_use_quality_v1` | rubric judge |
| `rubric_based_multi_turn_trajectory_quality_v1` | multi-turn trajectory rubric |
| `hallucinations_v1`, `safety_v1` | grounding, safety |
| `multi_turn_task_success_v1`, `multi_turn_trajectory_quality_v1`, `multi_turn_tool_use_quality_v1` | multi-turn quality |
| `per_turn_user_simulator_quality_v1` | user simulation |
| `token_usage_v1`, `tool_call_count_v1`, `inference_call_count_v1`, `invocation_duration_v1` | efficiency (always reported, 2.10+) |

No criteria set → defaults `tool_trajectory_avg_score: 1.0`, `response_match_score: 0.8`. Reference-based criteria cannot be combined with user simulation.

Eval runs the real agent (credentials needed). Set thresholds a little below
what a trusted agent scores. Custom metrics: implement an `Evaluator`
(`docs/guides/evaluation/evaluator`). Instruction tuning: `adk optimize`.
Samples: `contributing/samples/evaluation/*`.
