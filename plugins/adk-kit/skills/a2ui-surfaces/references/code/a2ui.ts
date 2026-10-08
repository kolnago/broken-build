import {basicCatalog, type ReactComponentImplementation} from '@a2ui/react/v0_9';
import {MessageProcessor, type A2uiClientAction, type A2uiMessage} from '@a2ui/web_core/v0_9';
import {weatherCatalog} from './catalog';

export type Processor = MessageProcessor<ReactComponentImplementation>;

/** One processor per assistant turn; it owns that turn's surfaces and reports their actions. */
export function createProcessor(onAction: (action: A2uiClientAction) => void): Processor {
  return new MessageProcessor([weatherCatalog, basicCatalog], onAction);
}

/** The backend already validated these with the Python SDK against the same v0.9 schema. */
export function applyMessages(processor: Processor, messages: Record<string, unknown>[]) {
  processor.processMessages(messages as unknown as A2uiMessage[]);
}
