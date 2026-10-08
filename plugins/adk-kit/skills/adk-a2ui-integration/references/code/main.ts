// Minimal Lit client for the own-SSE transport; imports checked against @a2ui/web_core and @a2ui/lit
// 0.12.0. Bundle with Vite; everything vendored, nothing from a CDN.
// React: same processor, render <A2uiSurface surface={...}/> from @a2ui/react/v0_9 (see a2ui-surfaces).
import {MessageProcessor} from '@a2ui/web_core/v0_9';
import {basicCatalog} from '@a2ui/lit/v0_9';
import '@a2ui/lit/v0_9'; // registers <a2ui-surface>

const sessionId = crypto.randomUUID();
const host = document.getElementById('surfaces')!;

// One processor for the page: surface ids are stable and unique per session (state["ui:surfaces"]).
// A chat transcript with fresh surfaces per answer uses one per assistant turn (a2ui-surfaces).
const processor = new MessageProcessor([basicCatalog], async (action) => {
  await stream(`/api/action/${sessionId}`, {version: 'v0.9.1', action});
});
processor.onSurfaceCreated((surface) => {
  const el = document.createElement('a2ui-surface') as any;
  el.surface = surface;
  el.id = `s-${surface.id}`;
  host.append(el);
});
processor.onSurfaceDeleted((id) => document.getElementById(`s-${id}`)?.remove()); // handler gets the id

async function stream(url: string, body: unknown) {
  const res = await fetch(url, {
    method: 'POST', credentials: 'include',
    headers: {'content-type': 'application/json'}, body: JSON.stringify(body),
  });
  const reader = res.body!.pipeThrough(new TextDecoderStream()).getReader();
  let buf = '';
  for (;;) {
    const {value, done} = await reader.read();
    if (done) break;
    buf += value;
    let i: number;
    while ((i = buf.indexOf('\n\n')) >= 0) {
      const evt = JSON.parse(buf.slice(0, i).replace(/^data: /, ''));
      buf = buf.slice(i + 2);
      if (evt.type === 'a2ui') {
        try {
          processor.processMessages(evt.messages);
        } catch {
          showText('This view could not be displayed.'); // never show renderer error details
        }
      } else if (evt.type === 'text') {
        showText(evt.text);
      }
    }
  }
}

function showText(t: string) {
  const p = document.createElement('p');
  p.textContent = t; // plain text, never innerHTML
  host.append(p);
}

document.querySelector('form')!.addEventListener('submit', (e) => {
  e.preventDefault();
  const input = (e.target as HTMLFormElement).querySelector('input')!;
  void stream(`/api/chat/${sessionId}`, {text: input.value});
  input.value = '';
});
