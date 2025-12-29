import { getApiBaseUrl } from '@/net/ws';

export type DecisionSummary = {
  decision_id: string;
  turn_index: number | null;
  player_id?: string | null;
  decision_type?: string | null;
  retry_used?: boolean | null;
  fallback_used?: boolean | null;
  timestamp?: string | null;
  request_start_ms?: number | null;
  response_end_ms?: number | null;
  latency_ms?: number | null;
  phase?: string | null;
};

export type DecisionAttempt = {
  attempt_index: number;
  system_prompt?: string | null;
  user_payload?: unknown | null;
  tools?: unknown | null;
  response?: unknown | null;
  parsed_tool_call?: unknown | null;
  validation_errors?: string[] | null;
  error_reason?: string | null;
  tool_action?: unknown | null;
};

export type DecisionBundle = {
  decision_id: string;
  summary: DecisionSummary | null;
  attempts: DecisionAttempt[];
  final_action?: unknown | null;
  retry_used?: boolean | null;
  fallback_used?: boolean | null;
  fallback_reason?: string | null;
  timing?: {
    request_start_ms?: number | null;
    response_end_ms?: number | null;
    latency_ms?: number | null;
  };
};

export const fetchDecisionList = async (
  runId: string,
  limit?: number
): Promise<DecisionSummary[]> => {
  const base = getApiBaseUrl();
  const params = typeof limit === 'number' ? `?limit=${limit}` : '';
  const res = await fetch(`${base}/runs/${encodeURIComponent(runId)}/decisions${params}`);
  if (!res.ok) {
    throw new Error(`Failed to load decisions (${res.status})`);
  }
  const data = (await res.json()) as { decisions: DecisionSummary[] };
  return data.decisions ?? [];
};

export const fetchDecisionBundle = async (
  runId: string,
  decisionId: string
): Promise<DecisionBundle> => {
  const base = getApiBaseUrl();
  const res = await fetch(
    `${base}/runs/${encodeURIComponent(runId)}/decisions/${encodeURIComponent(decisionId)}`
  );
  if (!res.ok) {
    throw new Error(`Failed to load decision bundle (${res.status})`);
  }
  return (await res.json()) as DecisionBundle;
};
