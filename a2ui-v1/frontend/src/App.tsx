import {useEffect, useRef, useState} from 'react';
import {A2uiView} from './A2uiView';
import {applyMessages, createProcessor, type Processor} from './a2ui';
import {fetchAgents, streamChat} from './api/client';
import type {A2UiClientAction, AgentInfo, ChatRequest, StreamEvent} from './api/wire';

type UserTurn = {id: number; role: 'user'; text: string};
type AssistantTurn = {
  id: number;
  role: 'assistant';
  texts: string[];
  progress: string | null;
  processor: Processor | null;
  actions: string[]; // A2UI actions sent from this turn's surfaces (client → agent)
  error: string | null;
  done: boolean;
};
type Turn = UserTurn | AssistantTurn;

let nextId = 1;

export function App() {
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [agent, setAgent] = useState('');
  const [sessions, setSessions] = useState<Record<string, string>>({});
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const bottom = useRef<HTMLDivElement>(null);
  // Processors live outside React state: state updaters may run twice (StrictMode), and
  // applying A2UI messages is a side effect that must happen exactly once.
  const processors = useRef(new Map<number, Processor>());

  useEffect(() => {
    fetchAgents()
      .then(list => {
        setAgents(list);
        setAgent(list[0]?.name ?? '');
      })
      .catch(() => setAgents([]));
  }, []);

  useEffect(() => {
    bottom.current?.scrollIntoView({behavior: 'smooth'});
  }, [turns]);

  const updateTurn = (id: number, patch: (t: AssistantTurn) => Partial<AssistantTurn>) =>
    setTurns(ts =>
      ts.map(t => (t.id === id && t.role === 'assistant' ? {...t, ...patch(t)} : t)),
    );

  const handleEvent = (id: number, agentName: string, event: StreamEvent) => {
    switch (event.type) {
      case 'progress':
        updateTurn(id, () => ({progress: event.tool}));
        break;
      case 'text':
        updateTurn(id, t => ({texts: [...t.texts, event.text]}));
        break;
      case 'a2ui':
        {
          let processor = processors.current.get(id);
          if (!processor) {
            // Actions from this turn's surfaces go to the same agent and update this turn.
            processor = createProcessor(action => void sendAction(id, agentName, action));
            processors.current.set(id, processor);
          }
          applyMessages(processor, event.messages);
          updateTurn(id, () => ({processor}));
        }
        break;
      case 'error':
        updateTurn(id, () => ({error: event.message}));
        break;
      case 'done':
        if (event.session_id) setSessions(s => ({...s, [agentName]: event.session_id!}));
        updateTurn(id, () => ({done: true, progress: null}));
        break;
    }
  };

  // The action handler is created once per processor, so it reads sessions through a ref.
  const sessionsRef = useRef(sessions);
  sessionsRef.current = sessions;

  /** Streams one request's events into assistant turn `id`. */
  const run = async (id: number, req: ChatRequest) => {
    setBusy(true);
    try {
      await streamChat(req, ev => handleEvent(id, req.agent, ev));
    } catch {
      updateTurn(id, () => ({error: 'Could not reach the backend.', done: true}));
    } finally {
      setBusy(false);
    }
  };

  const send = async (e: React.FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || !agent || busy) return;
    const id = nextId++;
    setTurns(ts => [
      ...ts,
      {id: nextId++, role: 'user', text},
      {id, role: 'assistant', texts: [], progress: null, processor: null, actions: [], error: null, done: false},
    ]);
    setInput('');
    await run(id, {agent, session_id: sessions[agent] ?? null, text});
  };

  /** A2UI user action (e.g. WeatherCard Refresh): answered into the turn that owns the surface. */
  const sendAction = async (id: number, agentName: string, action: A2UiClientAction) => {
    const sent = `${action.name} ${JSON.stringify(action.context)}`;
    updateTurn(id, t => ({done: false, error: null, actions: [...t.actions, sent]}));
    await run(id, {agent: agentName, session_id: sessionsRef.current[agentName] ?? null, action});
  };

  const current = agents.find(a => a.name === agent);

  return (
    <div className="app">
      <header>
        <h1>A2UI demo</h1>
        <select value={agent} onChange={e => setAgent(e.target.value)} disabled={busy}>
          {agents.map(a => (
            <option key={a.name} value={a.name}>
              {a.name} {a.renders_a2ui ? '(A2UI)' : '(text)'}
            </option>
          ))}
        </select>
        {current && <span className="desc">{current.description}</span>}
      </header>

      <main>
        {turns.map(t =>
          t.role === 'user' ? (
            <div key={t.id} className="msg user">{t.text}</div>
          ) : (
            <div key={t.id} className="msg assistant">
              {t.texts.map((s, i) => (
                <p key={i}>{s}</p>
              ))}
              {t.processor && <A2uiView processor={t.processor} />}
              {t.actions.map((a, i) => (
                <p key={i} className="action">↑ sent action {a}</p>
              ))}
              {t.progress && <p className="progress">using {t.progress}…</p>}
              {!t.done && !t.progress && t.texts.length === 0 && (
                <p className="progress">thinking…</p>
              )}
              {t.error && <p className="error">{t.error}</p>}
            </div>
          ),
        )}
        <div ref={bottom} />
      </main>

      <form onSubmit={send}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder={agent === 'weather_ui' ? 'weather in Prague' : 'Say something'}
          autoFocus
        />
        <button disabled={busy || !input.trim()}>Send</button>
      </form>
    </div>
  );
}
