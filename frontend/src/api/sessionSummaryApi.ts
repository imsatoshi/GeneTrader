import { sessionSummary } from '../mocks/sessionSummary';
import type { SessionSummary } from '../types/sessionSummary';

export async function getSessionSummary(): Promise<SessionSummary> {
  return Promise.resolve(sessionSummary);
}
