import { useEffect, useMemo, useRef, useState, type UIEvent } from 'react';
import type { Event } from '@/net/contracts';
import { getApiBaseUrl } from '@/net/ws';
import { useGameStore } from '@/state/store';
import { cn, NeoBadge } from '@/components/ui/NeoPrimitive';
import { getPlayerColor } from '@/domain/monopoly/colors';
import { formatMoney, formatSpaceLabel } from '@/domain/monopoly/formatters';

type DecisionAttempt = {
  attempt_index?: number;
  system_prompt?: string;
  user_payload?: unknown;
  tools?: unknown;
  response?: unknown;
  parsed_tool_call?: unknown;
  validation_errors?: string[];
  error_reason?: string | null;
  tool_action?: unknown;
};

type DecisionBundle = {
  decision_id: string;
  summary?: {
    decision_id: string;
    turn_index?: number | null;
    player_id?: string | null;
    decision_type?: string | null;
    retry_used?: boolean | null;
    fallback_used?: boolean | null;
    timestamp?: string | null;
    request_start_ms?: number | null;
    response_end_ms?: number | null;
    latency_ms?: number | null;
    phase?: string | null;
  } | null;
  attempts: DecisionAttempt[];
  final_action?: unknown;
  retry_used?: boolean | null;
  fallback_used?: boolean | null;
  fallback_reason?: string | null;
  timing?: {
    request_start_ms?: number | null;
    response_end_ms?: number | null;
    latency_ms?: number | null;
  };
};

type FeedItem =
  | { kind: 'system'; id: string; text: string }
  | {
    kind: 'llm';
    id: string;
    playerId: string;
    playerLabel: string;
    modelLabel?: string;
    message: string;
    privateThought: boolean;
    decisionId?: string;
  };

const SYSTEM_EVENT_TYPES = new Set<string>([
  'TURN_STARTED',
  'TURN_ENDED',
  'PROPERTY_PURCHASED',
  'PROPERTY_TRANSFERRED',
  'RENT_PAID',
  'SENT_TO_JAIL',
  'TRADE_PROPOSED',
  'TRADE_COUNTERED',
  'TRADE_ACCEPTED',
  'TRADE_REJECTED',
  'TRADE_EXPIRED',
  'GAME_ENDED',
]);

const Section = ({ label, value }: { label: string; value: unknown }) => {
  const content =
    typeof value === 'string' ? value : value === undefined ? 'None' : JSON.stringify(value, null, 2);
  return (
    <div className="flex flex-col gap-1">
      <span className="text-[9px] font-bold uppercase tracking-wide text-gray-500">{label}</span>
      <pre className="text-[10px] bg-neo-bg border-2 border-black p-2 font-mono whitespace-pre-wrap break-words shadow-inner">
        {content}
      </pre>
    </div>
  );
};

const BundleDetails = ({ bundle }: { bundle: DecisionBundle }) => (
  <div className="mt-2 space-y-3">
    {bundle.attempts.map((attempt, index) => (
      <div
        key={`attempt-${attempt.attempt_index ?? index}`}
        className="border-2 border-black bg-white p-2 shadow-neo-sm"
      >
        <div className="flex items-center justify-between mb-2">
          <span className="text-[10px] font-black uppercase">
            {attempt.attempt_index && attempt.attempt_index > 0
              ? `Retry ${attempt.attempt_index}`
              : 'Attempt 0'}
          </span>
          {attempt.validation_errors && attempt.validation_errors.length > 0 && (
            <NeoBadge variant="warning" className="text-[9px] py-0 px-1">
              {attempt.validation_errors.length} issue
            </NeoBadge>
          )}
        </div>
        <div className="space-y-2">
          <Section label="System Prompt" value={attempt.system_prompt ?? 'Missing'} />
          <Section label="User Payload" value={attempt.user_payload} />
          <Section label="Tools Schema" value={attempt.tools} />
          <Section label="Raw Response" value={attempt.response} />
          <Section label="Parsed Tool Call" value={attempt.parsed_tool_call} />
          <Section label="Validation Errors" value={attempt.validation_errors ?? []} />
          <Section label="Tool Action" value={attempt.tool_action} />
          {attempt.error_reason && <Section label="Error Reason" value={attempt.error_reason} />}
        </div>
      </div>
    ))}
    <div className="border-2 border-black bg-white p-2 shadow-neo-sm">
      <div className="text-[10px] font-black uppercase mb-2">Final Outcome</div>
      <div className="space-y-2">
        <Section label="Final Action" value={bundle.final_action ?? 'Missing'} />
        <Section
          label="Retry/Fallback"
          value={{
            retry_used: bundle.retry_used,
            fallback_used: bundle.fallback_used,
            fallback_reason: bundle.fallback_reason,
          }}
        />
        <Section label="Timing" value={bundle.timing} />
      </div>
    </div>
  </div>
);

const LlmBubble = ({
  playerId,
  playerLabel,
  modelLabel,
  message,
  privateThought,
  decisionId,
  bundle,
  loading,
  error,
  onToggle,
}: {
  playerId: string;
  playerLabel: string;
  modelLabel?: string;
  message: string;
  privateThought: boolean;
  decisionId?: string;
  bundle?: DecisionBundle;
  loading?: boolean;
  error?: string;
  onToggle?: (open: boolean) => void;
}) => {
  return (
    <div className="flex flex-col items-start gap-2">
      <div className="flex items-center gap-2 text-[10px] font-bold uppercase">
        <span
          className="inline-flex items-center px-2 py-0.5 border-2 border-black shadow-neo-sm"
          style={{ backgroundColor: getPlayerColor(playerId), color: 'white' }}
        >
          {playerLabel}
        </span>
        {modelLabel && <span className="text-gray-500 font-mono">{modelLabel}</span>}
        {privateThought && (
          <NeoBadge variant="error" className="text-[9px] py-0 px-1">
            PRIVATE
          </NeoBadge>
        )}
      </div>
      <div
        className={cn(
          'max-w-[90%] border-2 border-black p-3 text-sm shadow-neo-sm',
          privateThought ? 'bg-neo-pink text-white' : 'bg-white text-black'
        )}
      >
        <div className="whitespace-pre-wrap">{message}</div>
        <div className="mt-2">
          {decisionId ? (
            <details
              onToggle={(event) => onToggle?.((event.currentTarget as HTMLDetailsElement).open)}
              className="group"
            >
              <summary className="cursor-pointer text-[10px] font-bold uppercase text-neo-blue">
                Show LLM I/O
              </summary>
              {loading && <div className="text-[10px] text-gray-500 mt-2">Loading...</div>}
              {error && <div className="text-[10px] text-neo-red mt-2">{error}</div>}
              {bundle && <BundleDetails bundle={bundle} />}
            </details>
          ) : (
            <div className="text-[10px] text-gray-400 uppercase">LLM I/O unavailable</div>
          )}
        </div>
      </div>
    </div>
  );
};

const systemMessageForEvent = (
  event: Event,
  playerNameById: Map<string, string>,
): string | null => {
  if (SYSTEM_EVENT_TYPES.has(event.type)) {
    switch (event.type) {
      case 'TURN_STARTED':
        return `Turn ${event.turn_index} started`;
      case 'TURN_ENDED':
        return `Turn ${event.turn_index} ended`;
      case 'PROPERTY_PURCHASED': {
        const player = playerNameById.get(event.payload.player_id) ?? event.payload.player_id;
        return `${player} bought ${formatSpaceLabel(event.payload.space_index)} for ${formatMoney(
          event.payload.price
        )}`;
      }
      case 'RENT_PAID': {
        const from = playerNameById.get(event.payload.from_player_id) ?? event.payload.from_player_id;
        const to = playerNameById.get(event.payload.to_player_id) ?? event.payload.to_player_id;
        return `${from} paid ${formatMoney(event.payload.amount)} to ${to} for ${formatSpaceLabel(
          event.payload.space_index
        )}`;
      }
      case 'SENT_TO_JAIL': {
        const player = playerNameById.get(event.payload.player_id) ?? event.payload.player_id;
        return `${player} sent to jail`;
      }
      case 'PROPERTY_TRANSFERRED': {
        const fromId = event.payload.from_player_id;
        const toId = event.payload.to_player_id;
        const from = fromId ? playerNameById.get(fromId) ?? fromId : 'Bank';
        const to = toId ? playerNameById.get(toId) ?? toId : 'Bank';
        return `${formatSpaceLabel(event.payload.space_index)} transferred from ${from} to ${to}`;
      }
      case 'TRADE_PROPOSED': {
        const initiator =
          playerNameById.get(event.payload.initiator_player_id) ?? event.payload.initiator_player_id;
        const counterparty =
          playerNameById.get(event.payload.counterparty_player_id) ?? event.payload.counterparty_player_id;
        return `${initiator} proposed a trade with ${counterparty}`;
      }
      case 'TRADE_COUNTERED': {
        const actor = event.actor.player_id ?? event.payload.initiator_player_id;
        const actorLabel = playerNameById.get(actor) ?? actor;
        const other =
          actor === event.payload.initiator_player_id
            ? event.payload.counterparty_player_id
            : event.payload.initiator_player_id;
        const otherLabel = playerNameById.get(other) ?? other;
        return `${actorLabel} countered the trade with ${otherLabel}`;
      }
      case 'TRADE_ACCEPTED': {
        const actor = event.actor.player_id ?? event.payload.counterparty_player_id;
        const actorLabel = playerNameById.get(actor) ?? actor;
        const other =
          actor === event.payload.initiator_player_id
            ? event.payload.counterparty_player_id
            : event.payload.initiator_player_id;
        const otherLabel = playerNameById.get(other) ?? other;
        return `${actorLabel} accepted the trade with ${otherLabel}`;
      }
      case 'TRADE_REJECTED': {
        const actor = event.actor.player_id ?? event.payload.counterparty_player_id;
        const actorLabel = playerNameById.get(actor) ?? actor;
        const other =
          actor === event.payload.initiator_player_id
            ? event.payload.counterparty_player_id
            : event.payload.initiator_player_id;
        const otherLabel = playerNameById.get(other) ?? other;
        return `${actorLabel} rejected the trade with ${otherLabel}`;
      }
      case 'TRADE_EXPIRED': {
        const initiator =
          playerNameById.get(event.payload.initiator_player_id) ?? event.payload.initiator_player_id;
        const counterparty =
          playerNameById.get(event.payload.counterparty_player_id) ?? event.payload.counterparty_player_id;
        const reason = event.payload.reason ? ` (${event.payload.reason})` : '';
        return `Trade expired between ${initiator} and ${counterparty}${reason}`;
      }
      case 'GAME_ENDED': {
        const winner = playerNameById.get(event.payload.winner_player_id) ?? event.payload.winner_player_id;
        return `Game ended - ${winner} wins (${event.payload.reason})`;
      }
      default:
        return null;
    }
  }
  if (event.type === 'LLM_DECISION_RESPONSE' && !event.payload.valid) {
    const player = playerNameById.get(event.payload.player_id) ?? event.payload.player_id;
    const error = event.payload.error ?? 'invalid action';
    const fallback = typeof error === 'string' && error.startsWith('fallback:');
    const detail = fallback ? `fallback used (${error.replace('fallback:', '')})` : error;
    return `${player} ${detail}`;
  }
  return null;
};

export const ChatFeed = () => {
  const events = useGameStore((state) => state.events);
  const players = useGameStore((state) => state.runStatus.players ?? []);
  const logResetId = useGameStore((state) => state.logResetId);
  const apiBase = useMemo(() => getApiBaseUrl(), []);
  const containerRef = useRef<HTMLDivElement>(null);
  const [showThoughts, setShowThoughts] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const [bundleCache, setBundleCache] = useState<Record<string, DecisionBundle>>({});
  const [bundleLoading, setBundleLoading] = useState<Record<string, boolean>>({});
  const [bundleError, setBundleError] = useState<Record<string, string>>({});

  const playerMetaById = useMemo(() => {
    const map = new Map<string, { name: string; model?: string }>();
    players.forEach((player) => {
      map.set(player.player_id, { name: player.name, model: player.model_display_name });
    });
    return map;
  }, [players]);
  const playerNameById = useMemo(() => {
    const map = new Map<string, string>();
    players.forEach((player) => {
      map.set(player.player_id, player.name);
    });
    return map;
  }, [players]);

  const feedItems = useMemo<FeedItem[]>(() => {
    const ordered = [...events].reverse();
    const items: FeedItem[] = [];
    for (const event of ordered) {
      if (event.type === 'LLM_PUBLIC_MESSAGE') {
        items.push({
          kind: 'llm',
          id: event.event_id,
          playerId: event.payload.player_id,
          playerLabel: playerMetaById.get(event.payload.player_id)?.name ?? event.payload.player_id,
          modelLabel: playerMetaById.get(event.payload.player_id)?.model,
          message: event.payload.message,
          privateThought: false,
          decisionId: event.payload.decision_id ?? undefined,
        });
        continue;
      }
      if (event.type === 'LLM_PRIVATE_THOUGHT') {
        if (!showThoughts) {
          continue;
        }
        items.push({
          kind: 'llm',
          id: event.event_id,
          playerId: event.payload.player_id,
          playerLabel: playerMetaById.get(event.payload.player_id)?.name ?? event.payload.player_id,
          modelLabel: playerMetaById.get(event.payload.player_id)?.model,
          message: event.payload.thought,
          privateThought: true,
          decisionId: event.payload.decision_id ?? undefined,
        });
        continue;
      }
      const systemText = systemMessageForEvent(event, playerNameById);
      if (systemText) {
        items.push({ kind: 'system', id: event.event_id, text: systemText });
      }
    }
    return items;
  }, [events, playerMetaById, playerNameById, showThoughts]);

  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [autoScroll, feedItems]);

  useEffect(() => {
    setBundleCache({});
    setBundleLoading({});
    setBundleError({});
    setAutoScroll(true);
  }, [logResetId]);

  const handleScroll = (event: UIEvent<HTMLDivElement>) => {
    const { scrollTop, scrollHeight, clientHeight } = event.currentTarget;
    const nearBottom = scrollHeight - scrollTop - clientHeight < 40;
    setAutoScroll(nearBottom);
  };

  const requestBundle = async (decisionId: string) => {
    if (bundleCache[decisionId] || bundleLoading[decisionId]) {
      return;
    }
    setBundleLoading((prev) => ({ ...prev, [decisionId]: true }));
    setBundleError((prev) => ({ ...prev, [decisionId]: '' }));
    try {
      const response = await fetch(`${apiBase}/run/decision/${encodeURIComponent(decisionId)}`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const payload = (await response.json()) as DecisionBundle;
      setBundleCache((prev) => ({ ...prev, [decisionId]: payload }));
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Fetch failed';
      setBundleError((prev) => ({ ...prev, [decisionId]: message }));
    } finally {
      setBundleLoading((prev) => ({ ...prev, [decisionId]: false }));
    }
  };

  return (
    <div className="flex flex-col h-full bg-white border-t-2 border-black font-sans">
      <div className="flex items-center justify-between gap-2 px-3 py-2 border-b-2 border-black bg-gray-50">
        <span className="text-[10px] font-black uppercase tracking-wider">Feed</span>
        <label className="flex items-center gap-2 text-[10px] font-bold uppercase">
          <input
            type="checkbox"
            checked={showThoughts}
            onChange={(event) => setShowThoughts(event.target.checked)}
            className="accent-black w-4 h-4"
          />
          Show private thoughts
        </label>
      </div>
      {!autoScroll && (
        <div className="absolute top-12 left-1/2 -translate-x-1/2 z-30">
          <button
            type="button"
            onClick={() => setAutoScroll(true)}
            className="brutal-btn bg-neo-yellow text-[10px] py-1 shadow-neo"
          >
            RESUME LIVE
          </button>
        </div>
      )}
      <div
        ref={containerRef}
        className="flex-1 overflow-y-auto p-3 brutal-scroll space-y-4"
        onScroll={handleScroll}
      >
        {feedItems.length === 0 && (
          <div className="flex flex-col items-center justify-center pt-12 text-gray-400 opacity-60">
            <span className="text-3xl mb-2">?</span>
            <span className="font-brutal text-xs">Waiting for messages...</span>
          </div>
        )}

        {feedItems.map((item) => {
          if (item.kind === 'system') {
            return (
              <div key={item.id} className="flex justify-center">
                <span className="text-[10px] uppercase font-bold bg-neo-bg px-3 py-1 border-2 border-black shadow-neo-sm">
                  {item.text}
                </span>
              </div>
            );
          }
          const decisionId = item.decisionId;
          return (
            <LlmBubble
              key={item.id}
              playerId={item.playerId}
              playerLabel={item.playerLabel}
              modelLabel={item.modelLabel}
              message={item.message}
              privateThought={item.privateThought}
              decisionId={decisionId}
              bundle={decisionId ? bundleCache[decisionId] : undefined}
              loading={decisionId ? bundleLoading[decisionId] : false}
              error={decisionId ? bundleError[decisionId] : undefined}
              onToggle={(open) => {
                if (open && decisionId) {
                  void requestBundle(decisionId);
                }
              }}
            />
          );
        })}
      </div>
    </div>
  );
};
