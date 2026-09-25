import type {AgentInfo, ChatRequest, StreamEvent} from './wire';

export async function fetchAgents(): Promise<AgentInfo[]> {
  const res = await fetch('/api/agents');
  if (!res.ok) throw new Error(`GET /api/agents failed: ${res.status}`);
  return res.json();
}

/** POST /api/chat and call `onEvent` for every SSE event (EventSource can't POST). */
export async function streamChat(
  req: ChatRequest,
  onEvent: (event: StreamEvent) => void,
): Promise<void> {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(req),
  });
  if (!res.ok || !res.body) throw new Error(`POST /api/chat failed: ${res.status}`);

  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = '';
  for (;;) {
    const {value, done} = await reader.read();
    if (done) break;
    buffer += value;
    // SSE frames are separated by a blank line.
    let sep: number;
    while ((sep = buffer.indexOf('\n\n')) !== -1) {
      const frame = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      const data = frame
        .split('\n')
        .filter(line => line.startsWith('data:'))
        .map(line => line.slice(5).trimStart())
        .join('\n');
      if (data) onEvent(JSON.parse(data) as StreamEvent);
    }
  }
}
