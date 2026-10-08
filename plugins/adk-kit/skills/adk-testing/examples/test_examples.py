"""Offline tests for the adk-workflows examples (google-adk 2.11).

Run: pip install "google-adk>=2.11" pytest pytest-asyncio && pytest -q
"""
import importlib

import pytest
from adk_test_helpers import (FakeLlm, ScriptedLlm, answer, new_session, node_name,
                              outputs_of, pending_request_inputs, run_turn)


async def test_ex01():
  from examples import ex01_function_pipeline as ex
  runner, s = await new_session(ex.root_agent)
  ev = await run_turn(runner, s.id, 'Card outage in Prague')
  assert outputs_of(ev, 'report') == ['[high] Card outage in Prague']
  assert any(e.content and e.content.parts and e.content.parts[0].text == '[high] Card outage in Prague' for e in ev)
  got = await runner.session_service.get_session(app_name='test_app', user_id='u1', session_id=s.id)
  assert got.state['last_priority'] == 'high'


@pytest.mark.parametrize('text,expected', [
    ('I want a refund', 'refund queue: I want a refund (after 3 passes)'),
    ('hello', 'general queue: hello (after 3 passes)')])
async def test_ex02(text, expected):
  from examples import ex02_routing_loop as ex
  runner, s = await new_session(ex.root_agent)
  ev = await run_turn(runner, s.id, text)
  assert outputs_of(ev, 'finish') == [expected]


async def test_ex03():
  from examples import ex03_fan_out_join as ex
  runner, s = await new_session(ex.root_agent)
  ev = await run_turn(runner, s.id, 'a, bb, ccc')
  out = outputs_of(ev, 'combine')[-1]
  assert out['words'] == 3 and out['upper'] == 'A, BB, CCC'
  assert [x['len'] for x in out['scores']] == [1, 2, 3]


def load(monkeypatch, module, key, responses):
  model_id = ScriptedLlm.script(key, responses)
  monkeypatch.setenv('ADK_MODEL', model_id)
  from examples import _common
  importlib.reload(_common)
  mod = importlib.import_module(f'examples.{module}')
  return importlib.reload(mod), ScriptedLlm.calls[model_id]


async def test_ex04(monkeypatch):
  ex, calls = load(monkeypatch, 'ex04_llm_agent_nodes', 'ex04',
                   [{'category': 'complaint', 'confidence': 0.9}])
  runner, s = await new_session(ex.root_agent)
  ev = await run_turn(runner, s.id, 'You charged me twice!')
  assert outputs_of(ev, 'escalate') == ['Escalated complaint (confidence 0.90)']
  sys_instr = calls[0].config.system_instruction
  assert 'retail banking' in str(sys_instr)


async def test_ex05():
  from examples import ex05_human_in_the_loop as ex
  runner, s = await new_session(app=ex.app)
  ev = await run_turn(runner, s.id, 'Q3 note')
  fcs = pending_request_inputs(ev)
  assert len(fcs) == 1
  ev = await run_turn(runner, s.id, answer(fcs[0], {'approved': False, 'comment': 'shorter'}))
  fcs = pending_request_inputs(ev)
  assert len(fcs) == 1, [ (node_name(e), e.output) for e in ev]
  ev = await run_turn(runner, s.id, answer(fcs[0], {'approved': True}))
  assert outputs_of(ev, 'publish') == ['PUBLISHED: Draft v2: Q3 note']


async def test_ex06(monkeypatch):
  ex, calls = load(monkeypatch, 'ex06_dynamic_nodes', 'ex06', [
      'Bad headline', {'ok': False, 'reason': 'too long'},
      'Good headline', {'ok': True, 'reason': 'fine'}])
  runner, s = await new_session(ex.root_agent)
  ev = await run_turn(runner, s.id, 'rates')
  assert outputs_of(ev, 'orchestrate') == ['Good headline']
  assert 'too long' in str(calls[2].config.system_instruction)


def fc(name, **args):
  from google.genai import types
  return types.Part(function_call=types.FunctionCall(name=name, args=args))


async def test_ex07(monkeypatch):
  ex, calls = load(monkeypatch, 'ex07_task_mode', 'ex07', [
      fc('investigator', case_id='LO-1'),
      fc('get_case', case_id='LO-1'),
      fc('finish_task', summary='Exposure 61.2k over 50k limit', risk_level='high'),
      'Case LO-1 is high risk.'])
  runner, s = await new_session(ex.root_agent)
  ev = await run_turn(runner, s.id, 'Investigate LO-1')
  tool_names = [d.name for d in (calls[0].config.tools[0].function_declarations or [])]
  assert 'investigator' in tool_names and 'summariser' in tool_names, tool_names
  frs = [fr for e in ev for fr in e.get_function_responses()]
  inv = [fr for fr in frs if fr.name == 'investigator']
  assert inv and 'high' in str(inv[0].response), frs
  assert ev[-1].content.parts[0].text == 'Case LO-1 is high risk.'


async def test_ex08(monkeypatch):
  ex, calls = load(monkeypatch, 'ex08_node_as_tool', 'ex08', [
      fc('customer_lookup', customer_id='C1'), 'C1 is an SME with 50k limit.',
      fc('format_report', case_id='LO-9')])
  runner, s = await new_session(ex.root_agent)
  ev = await run_turn(runner, s.id, 'Who is C1?')
  frs = [fr for e in ev for fr in e.get_function_responses() if fr.name == 'customer_lookup']
  assert '50000' in str(frs[0].response), frs
  ev = await run_turn(runner, s.id, 'Report LO-9')
  assert len(calls) == 3  # no summarising model call after format_report
  texts = [p.text for e in ev if e.content for p in e.content.parts if p.text]
  assert 'Case LO-9: report ready.' in texts, texts


async def test_ex09_confirmation(monkeypatch):
  ex, calls = load(monkeypatch, 'ex09_tools', 'ex09', [
      fc('block_card', card_id='K1'), 'Waiting for your approval.',
      'Card K1 is blocked.'])
  runner, s = await new_session(ex.root_agent)
  ev = await run_turn(runner, s.id, 'Block card K1')
  conf = [c for e in ev for c in e.get_function_calls() if c.name == 'adk_request_confirmation']
  assert conf, [c.name for e in ev for c in e.get_function_calls()]
  ev = await run_turn(runner, s.id, answer(conf[0], {'confirmed': True}))
  frs = [fr for e in ev for fr in e.get_function_responses() if fr.name == 'block_card']
  assert frs and frs[0].response['status'] == 'blocked', frs
  ex.mcp_tools  # import path checked separately (needs [mcp] extra)


async def test_ex10(monkeypatch):
  ex, calls = load(monkeypatch, 'ex10_app_plugins', 'ex10', [
      fc('lookup_rate', currency='CZK'), 'CZK is 0.04 EUR.'])
  runner, s = await new_session(app=ex.app)
  ev = await run_turn(runner, s.id, 'Rate for CZK?')
  assert ex.audit.tool_calls == ['lookup_rate']
  ev = await run_turn(runner, s.id, 'Send to CZ6508000000192000145399')
  assert ev[-1].content.parts[0].text == 'I cannot process account numbers here.'
  assert len(calls) == 2  # guardrail skipped the model
  runner, s = await new_session(app=ex.pipeline_app)
  ev = await run_turn(runner, s.id, 'rates')
  assert outputs_of(ev, 'flaky_fetch') == ['rates (fetched on attempt 2)']


async def test_abort_signal():
  import asyncio
  from examples import ex03_fan_out_join as ex
  runner, s = await new_session(ex.root_agent)
  stop = asyncio.Event(); stop.set()
  from adk_test_helpers import user_msg
  ev = [e async for e in runner.run_async(user_id='u1', session_id=s.id,
        new_message=user_msg('a, b'), abort_signal=stop)]
  assert any(getattr(e, 'error_code', None) == 'INVOCATION_ABORTED' for e in ev), [e.error_code for e in ev]


async def test_ex05_approve_first():
  from examples import ex05_human_in_the_loop as ex
  runner, s = await new_session(app=ex.app)
  ev = await run_turn(runner, s.id, 'Q3 note')
  fc_ = pending_request_inputs(ev)[0]
  ev = await run_turn(runner, s.id, answer(fc_, {'approved': True}))
  assert outputs_of(ev, 'publish') == ['PUBLISHED: Draft v1: Q3 note']


# ---------------------------------------------------------------------------
# Canary tests: framework behaviours the skills rely on (verified on 2.11).
# If one of these fails after an ADK upgrade, update the matching rule in
# adk-workflows/SKILL.md (rules 16-19) instead of "fixing" the test.
# ---------------------------------------------------------------------------
from google.adk import Agent, Context, Event, Workflow
from google.adk.events import RequestInput
from google.adk.workflow import START
from google.adk.tools import ToolContext
from pydantic import BaseModel as _BM


class _LimitRequest(_BM):
  amount: int


def _form(node_input: str):
  return RequestInput(interrupt_id='form_1', message='Fill', response_schema=_LimitRequest)


def _after(node_input: dict) -> str:
  return f"amount={node_input['amount']}"


async def test_canary_invalid_request_input_answer_poisons_interrupt():
  wf = Workflow(name='ri', edges=[(START, _form, _after)])
  runner, s = await new_session(wf)
  fc_ = pending_request_inputs(await run_turn(runner, s.id, 'go'))[0]
  assert fc_.id == 'form_1'                      # call id == interrupt_id
  with pytest.raises(Exception):                 # WorkflowDataError
    await run_turn(runner, s.id, answer(fc_, {'amount': 'lots'}))
  with pytest.raises(Exception):                 # still failing for a valid answer
    await run_turn(runner, s.id, answer(fc_, {'amount': 5}))
  runner, s = await new_session(wf, app_name='ri2')
  fc_ = pending_request_inputs(await run_turn(runner, s.id, 'go'))[0]
  ev = await run_turn(runner, s.id, answer(fc_, {'amount': '500'}))  # coerced
  assert outputs_of(ev, '_after') == ['amount=500']


def test_canary_no_end_sentinel():
  def a(node_input: str) -> str:
    return node_input
  with pytest.raises(Exception):
    Workflow(name='bad', edges=[(START, a), (a, 'END')])


async def test_canary_single_turn_loop_back_sees_only_new_input():
  def get_util(portfolio: str, tool_context: ToolContext) -> dict:
    """Utilisation for a portfolio."""
    tool_context.state['temp:ledger'] = {'util': '0.82'}
    return {'status': 'ok', 'util': '82%'}

  llm = FakeLlm([fc('get_util', portfolio='P1'), 'It is 99%.', 'It is 82%.'])
  agent = Agent(name='analyst', model=llm, instruction='Use tools.', tools=[get_util])

  def verify(ctx: Context, node_input: str):
    assert ctx.state.get('temp:ledger') == {'util': '0.82'}  # tool's temp: write visible
    if '99' in node_input:
      return Event(output='Rewrite without 99.', route='retry')
    return Event(output=node_input, route='pass')

  def deliver(node_input: str) -> str:
    return node_input

  wf = Workflow(name='shell', edges=[(START, agent, verify),
                                     (verify, {'retry': agent, 'pass': deliver})])
  runner, s = await new_session(wf)
  ev = await run_turn(runner, s.id, 'How close is P1 to its limit?')
  assert outputs_of(ev, 'deliver') == ['It is 82%.']
  retry_texts = [p.text for c in llm.requests[2].contents for p in c.parts if p.text]
  assert retry_texts == ['Rewrite without 99.']    # original question NOT visible
  got = await runner.session_service.get_session(app_name='test_app', user_id='u1', session_id=s.id)
  assert not [k for k in got.state if k.startswith('temp:')]   # temp: not persisted


async def test_canary_routed_message_only_event_gives_none():
  def router(node_input: str):
    return Event(message='done', route='go')
  seen = []
  def target(node_input=None):
    seen.append(node_input)
    return 'ok'
  wf = Workflow(name='r', edges=[(START, router), (router, {'go': target})])
  runner, s = await new_session(wf)
  await run_turn(runner, s.id, 'x')
  assert seen == [None]
