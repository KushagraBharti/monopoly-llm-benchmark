import { useEffect, useMemo, useRef, useState, type UIEvent } from 'react';
import type { Event } from '@/net/contracts';
import { useGameStore } from '@/state/store';
import { cn, NeoBadge } from '@/components/ui/NeoPrimitive';
import { getPlayerColor } from '@/domain/monopoly/colors';
import { formatCardTitle, formatMoney, formatSpaceLabel } from '@/domain/monopoly/formatters';
import { SPACE_INDEX_BY_KEY } from '@/domain/monopoly/constants';
import { ThoughtsPanel } from '@/components/panels/ThoughtsPanel';

type FeedSystemTone = 'neutral' | 'info' | 'success' | 'warning' | 'danger';

type FeedItem =
  | { kind: 'system'; id: string; text: string; tone?: FeedSystemTone }
  | { kind: 'group'; id: string; title: string; summary: string; lines: string[]; tone?: FeedSystemTone }
  | {
      kind: 'chat';
      id: string;
      playerId: string;
      playerLabel: string;
      modelLabel?: string;
      message: string;
      decisionId?: string;
    };

type TurnBlock = {
  id: string;
  turnIndex: number | null;
  playerId?: string | null;
  items: FeedItem[];
};

type RawTurnBlock = {
  id: string;
  turnIndex: number | null;
  events: Event[];
};

const SKIP_TYPES = new Set(['LLM_DECISION_REQUESTED']);

const toneClasses: Record<FeedSystemTone, string> = {
  neutral: 'border-black',
  info: 'border-neo-blue',
  success: 'border-neo-green',
  warning: 'border-neo-yellow',
  danger: 'border-neo-pink',
};

const toneTextClasses: Record<FeedSystemTone, string> = {
  neutral: 'text-gray-600',
  info: 'text-neo-blue',
  success: 'text-neo-green',
  warning: 'text-neo-yellow',
  danger: 'text-neo-pink',
};

const isAuctionUpdate = (
  event: Event
): event is Extract<Event, { type: 'AUCTION_BID_PLACED' | 'AUCTION_PLAYER_DROPPED' }> =>
  event.type === 'AUCTION_BID_PLACED' || event.type === 'AUCTION_PLAYER_DROPPED';

const isCardEffect = (
  event: Event
): event is Extract<Event, { type: 'PLAYER_MOVED' | 'CASH_CHANGED' | 'SENT_TO_JAIL' }> =>
  event.type === 'PLAYER_MOVED' || event.type === 'CASH_CHANGED' || event.type === 'SENT_TO_JAIL';

const isCashChanged = (event: Event): event is Extract<Event, { type: 'CASH_CHANGED' }> =>
  event.type === 'CASH_CHANGED';

const resolveSpaceLabel = (spaceKey: string): string => {
  const normalized = spaceKey.toUpperCase();
  const index = SPACE_INDEX_BY_KEY[normalized];
  if (index !== undefined) {
    return formatSpaceLabel(index);
  }
  return spaceKey.replace(/_/g, ' ');
};

const formatPlayer = (playerId: string | null | undefined, playerNames: Map<string, string>): string => {
  if (!playerId) return 'Unknown';
  return playerNames.get(playerId) ?? playerId;
};

const summarizeTradeBundle = (bundle: { cash?: number; properties?: string[]; get_out_of_jail_cards?: number }) => {
  const parts: string[] = [];
  if (bundle.cash && bundle.cash !== 0) {
    parts.push(formatMoney(bundle.cash));
  }
  if (bundle.properties && bundle.properties.length > 0) {
    parts.push(`${bundle.properties.length} prop${bundle.properties.length === 1 ? '' : 's'}`);
  }
  if (bundle.get_out_of_jail_cards && bundle.get_out_of_jail_cards > 0) {
    parts.push(`${bundle.get_out_of_jail_cards} card${bundle.get_out_of_jail_cards === 1 ? '' : 's'}`);
  }
  return parts.length ? parts.join(' + ') : 'none';
};

const extractTurnPlayerId = (events: Event[]): string | null => {
  for (const event of events) {
    const payload = event.payload as any;
    if (payload?.player_id) return payload.player_id;
    if (payload?.from_player_id) return payload.from_player_id;
    if (payload?.bidder_player_id) return payload.bidder_player_id;
    if (payload?.initiator_player_id) return payload.initiator_player_id;
    if (event.actor?.player_id) return event.actor.player_id;
  }
  return null;
};

const formatSystemEvent = (
  event: Event,
  playerNames: Map<string, string>
): { text: string; tone?: FeedSystemTone } | null => {
  switch (event.type) {
    case 'GAME_STARTED':
      return { text: 'Game started.', tone: 'info' };
    case 'TURN_STARTED':
      return { text: `Turn ${event.turn_index} started.`, tone: 'info' };
    case 'TURN_ENDED':
      return { text: `Turn ${event.turn_index} ended.`, tone: 'neutral' };
    case 'DICE_ROLLED': {
      const total = event.payload.d1 + event.payload.d2;
      const doubleTag = event.payload.is_double ? ' (double)' : '';
      return { text: `Rolled ${event.payload.d1} + ${event.payload.d2} = ${total}${doubleTag}`, tone: 'neutral' };
    }
    case 'PLAYER_MOVED':
      return {
        text: `Moved ${formatSpaceLabel(event.payload.from)} -> ${formatSpaceLabel(event.payload.to)}`,
        tone: 'info',
      };
    case 'PROPERTY_PURCHASED': {
      const player = formatPlayer(event.payload.player_id, playerNames);
      return {
        text: `${player} bought ${formatSpaceLabel(event.payload.space_index)} for ${formatMoney(event.payload.price)}`,
        tone: 'success',
      };
    }
    case 'RENT_PAID': {
      const from = formatPlayer(event.payload.from_player_id, playerNames);
      const to = formatPlayer(event.payload.to_player_id, playerNames);
      return {
        text: `${from} paid ${formatMoney(event.payload.amount)} to ${to} for ${formatSpaceLabel(event.payload.space_index)}`,
        tone: 'danger',
      };
    }
    case 'PROPERTY_TRANSFERRED': {
      const from = event.payload.from_player_id
        ? formatPlayer(event.payload.from_player_id, playerNames)
        : 'Bank';
      const to = event.payload.to_player_id ? formatPlayer(event.payload.to_player_id, playerNames) : 'Bank';
      return {
        text: `${formatSpaceLabel(event.payload.space_index)} transferred from ${from} to ${to}`,
        tone: 'info',
      };
    }
    case 'SENT_TO_JAIL': {
      const player = formatPlayer(event.payload.player_id, playerNames);
      return { text: `${player} sent to jail (${event.payload.reason})`, tone: 'warning' };
    }
    case 'PROPERTY_MORTGAGED': {
      const player = formatPlayer(event.payload.player_id, playerNames);
      return {
        text: `${player} mortgaged ${formatSpaceLabel(event.payload.space_index)} for ${formatMoney(event.payload.amount)}`,
        tone: 'warning',
      };
    }
    case 'PROPERTY_UNMORTGAGED': {
      const player = formatPlayer(event.payload.player_id, playerNames);
      return {
        text: `${player} unmortgaged ${formatSpaceLabel(event.payload.space_index)} for ${formatMoney(event.payload.amount)}`,
        tone: 'success',
      };
    }
    case 'HOUSE_BUILT': {
      const player = formatPlayer(event.payload.player_id, playerNames);
      return {
        text: `${player} built ${event.payload.count} house(s) on ${formatSpaceLabel(event.payload.space_index)}`,
        tone: 'success',
      };
    }
    case 'HOTEL_BUILT': {
      const player = formatPlayer(event.payload.player_id, playerNames);
      return {
        text: `${player} built ${event.payload.count} hotel(s) on ${formatSpaceLabel(event.payload.space_index)}`,
        tone: 'success',
      };
    }
    case 'HOUSE_SOLD': {
      const player = formatPlayer(event.payload.player_id, playerNames);
      return {
        text: `${player} sold ${event.payload.count} house(s) on ${formatSpaceLabel(event.payload.space_index)}`,
        tone: 'warning',
      };
    }
    case 'HOTEL_SOLD': {
      const player = formatPlayer(event.payload.player_id, playerNames);
      return {
        text: `${player} sold ${event.payload.count} hotel(s) on ${formatSpaceLabel(event.payload.space_index)}`,
        tone: 'warning',
      };
    }
    case 'AUCTION_STARTED': {
      const propertyLabel = resolveSpaceLabel(event.payload.property_space);
      const initiator = formatPlayer(event.payload.initiator_player_id, playerNames);
      return { text: `Auction started for ${propertyLabel} (by ${initiator})`, tone: 'info' };
    }
    case 'AUCTION_ENDED': {
      const propertyLabel = resolveSpaceLabel(event.payload.property_space);
      if (event.payload.reason === 'SOLD' && event.payload.winner_player_id) {
        const winner = formatPlayer(event.payload.winner_player_id, playerNames);
        const price = event.payload.winning_bid ?? 0;
        return { text: `${propertyLabel} sold to ${winner} for ${formatMoney(price)}`, tone: 'success' };
      }
      return { text: `Auction ended for ${propertyLabel} (${event.payload.reason})`, tone: 'neutral' };
    }
    case 'TRADE_PROPOSED': {
      const initiator = formatPlayer(event.payload.initiator_player_id, playerNames);
      const counterparty = formatPlayer(event.payload.counterparty_player_id, playerNames);
      const offer = summarizeTradeBundle(event.payload.offer);
      const request = summarizeTradeBundle(event.payload.request);
      return { text: `Trade proposed: ${initiator} -> ${counterparty} (${offer} for ${request})`, tone: 'info' };
    }
    case 'TRADE_COUNTERED': {
      const actor = event.actor.player_id ?? event.payload.initiator_player_id;
      const actorLabel = formatPlayer(actor, playerNames);
      const counterparty =
        actor === event.payload.initiator_player_id
          ? event.payload.counterparty_player_id
          : event.payload.initiator_player_id;
      const counterpartyLabel = formatPlayer(counterparty, playerNames);
      return { text: `Trade countered: ${actorLabel} -> ${counterpartyLabel}`, tone: 'info' };
    }
    case 'TRADE_ACCEPTED': {
      const actor = event.actor.player_id ?? event.payload.counterparty_player_id;
      const actorLabel = formatPlayer(actor, playerNames);
      const counterparty =
        actor === event.payload.initiator_player_id
          ? event.payload.counterparty_player_id
          : event.payload.initiator_player_id;
      const counterpartyLabel = formatPlayer(counterparty, playerNames);
      return { text: `Trade accepted: ${actorLabel} -> ${counterpartyLabel}`, tone: 'success' };
    }
    case 'TRADE_REJECTED': {
      const actor = event.actor.player_id ?? event.payload.counterparty_player_id;
      const actorLabel = formatPlayer(actor, playerNames);
      const counterparty =
        actor === event.payload.initiator_player_id
          ? event.payload.counterparty_player_id
          : event.payload.initiator_player_id;
      const counterpartyLabel = formatPlayer(counterparty, playerNames);
      return { text: `Trade rejected: ${actorLabel} -> ${counterpartyLabel}`, tone: 'warning' };
    }
    case 'TRADE_EXPIRED': {
      const initiator = formatPlayer(event.payload.initiator_player_id, playerNames);
      const counterparty = formatPlayer(event.payload.counterparty_player_id, playerNames);
      return { text: `Trade expired: ${initiator} -> ${counterparty}`, tone: 'neutral' };
    }
    case 'GAME_ENDED': {
      const winner = formatPlayer(event.payload.winner_player_id, playerNames);
      return { text: `Game ended - ${winner} wins (${event.payload.reason})`, tone: 'success' };
    }
    case 'CASH_CHANGED': {
      const player = formatPlayer(event.payload.player_id, playerNames);
      const reason = event.payload.reason ? ` (${event.payload.reason})` : '';
      return { text: `${player} cash ${formatMoney(event.payload.delta, true)}${reason}`, tone: 'neutral' };
    }
    case 'LLM_DECISION_RESPONSE': {
      if (event.payload.valid) return null;
      const player = formatPlayer(event.payload.player_id, playerNames);
      const error = event.payload.error ?? 'invalid action';
      return { text: `${player} invalid action (${error})`, tone: 'danger' };
    }
    default:
      return null;
  }
};

const buildTurnBlocks = (events: Event[], playerNames: Map<string, string>): TurnBlock[] => {
  const chronological = [...events].reverse();
  const blocks: RawTurnBlock[] = [];
  let current: RawTurnBlock | null = null;

  const ensurePrelude = () => {
    if (!current) {
      current = { id: 'prelude', turnIndex: null, events: [] };
      blocks.push(current);
    }
  };

  for (const event of chronological) {
    if (event.type === 'TURN_STARTED') {
      current = {
        id: `turn-${event.turn_index}-${event.event_id}`,
        turnIndex: event.turn_index,
        events: [event],
      };
      blocks.push(current);
      continue;
    }

    if (!current) {
      ensurePrelude();
    }

    current?.events.push(event);
  }

  return blocks.map((block) => {
    const rawEvents = block.events;
    const playerId = block.turnIndex === null ? null : extractTurnPlayerId(rawEvents);
    const items: FeedItem[] = [];

    const addSystem = (event: Event, text: string, tone?: FeedSystemTone) => {
      items.push({ kind: 'system', id: event.event_id, text, tone });
    };

    let i = 0;
    while (i < rawEvents.length) {
      const event = rawEvents[i];

      if (event.type === 'TURN_STARTED') {
        const playerLabel = playerId ? formatPlayer(playerId, playerNames) : 'Unknown player';
        addSystem(event, `Turn ${event.turn_index} started - ${playerLabel}`, 'info');
        i += 1;
        continue;
      }

      if (event.type === 'TURN_ENDED') {
        const playerLabel = playerId ? formatPlayer(playerId, playerNames) : 'Unknown player';
        addSystem(event, `Turn ${event.turn_index} ended - ${playerLabel}`, 'neutral');
        i += 1;
        continue;
      }

      if (event.type === 'LLM_PUBLIC_MESSAGE') {
        items.push({
          kind: 'chat',
          id: event.event_id,
          playerId: event.payload.player_id,
          playerLabel: formatPlayer(event.payload.player_id, playerNames),
          modelLabel: undefined,
          message: event.payload.message,
          decisionId: event.payload.decision_id ?? undefined,
        });
        i += 1;
        continue;
      }

      if (event.type === 'LLM_PRIVATE_THOUGHT') {
        i += 1;
        continue;
      }

      if (event.type === 'CARD_DRAWN') {
        const deckLabel = event.payload.deck_type === 'CHANCE' ? 'Chance' : 'Community Chest';
        const cardTitle = formatCardTitle(event.payload.card_id);
        const detailLines: string[] = [`${deckLabel} card: ${cardTitle}`];
        const effectParts: string[] = [];
        let moveTo: number | null = null;
        let cashDelta = 0;
        let sentToJail = false;

        let j = i + 1;
        while (j < rawEvents.length) {
          const next = rawEvents[j];
          if (!isCardEffect(next)) break;
          if (next.type === 'PLAYER_MOVED') {
            moveTo = next.payload.to;
            detailLines.push(`Moved ${formatSpaceLabel(next.payload.from)} -> ${formatSpaceLabel(next.payload.to)}`);
          } else if (next.type === 'CASH_CHANGED') {
            cashDelta += next.payload.delta;
            detailLines.push(`Cash ${formatMoney(next.payload.delta, true)} (${next.payload.reason})`);
          } else if (next.type === 'SENT_TO_JAIL') {
            sentToJail = true;
            detailLines.push(`Sent to jail (${next.payload.reason})`);
          }
          j += 1;
        }

        if (moveTo !== null) {
          effectParts.push(`Moved to ${formatSpaceLabel(moveTo)}`);
        }
        if (cashDelta !== 0) {
          effectParts.push(formatMoney(cashDelta, true));
        }
        if (sentToJail) {
          effectParts.push('Sent to jail');
        }
        const effectSummary = effectParts.length ? ` - ${effectParts.join(', ')}` : '';
        items.push({
          kind: 'group',
          id: event.event_id,
          title: `${deckLabel} card`,
          summary: `Card: ${cardTitle}${effectSummary}`,
          lines: detailLines,
          tone: 'info',
        });
        i = j;
        continue;
      }

      if (isAuctionUpdate(event)) {
        const detailLines: string[] = [];
        let lastBid: { amount: number; playerId: string } | null = null;
        let propertyLabel: string | null = null;
        let j = i;
        while (j < rawEvents.length) {
          const next = rawEvents[j];
          if (!isAuctionUpdate(next)) break;
          if (!propertyLabel) {
            propertyLabel = resolveSpaceLabel(next.payload.property_space);
          }
          if (next.type === 'AUCTION_BID_PLACED') {
            const bidder = formatPlayer(next.payload.bidder_player_id, playerNames);
            detailLines.push(`${bidder} bid ${formatMoney(next.payload.bid_amount)}`);
            lastBid = { amount: next.payload.bid_amount, playerId: next.payload.bidder_player_id };
          }
          if (next.type === 'AUCTION_PLAYER_DROPPED') {
            const bidder = formatPlayer(next.payload.player_id, playerNames);
            detailLines.push(`${bidder} dropped out`);
          }
          j += 1;
        }
        const summaryParts = [`Auction updates (${detailLines.length})`];
        if (propertyLabel) summaryParts.push(propertyLabel);
        if (lastBid) {
          const bidder = formatPlayer(lastBid.playerId, playerNames);
          summaryParts.push(`High bid ${formatMoney(lastBid.amount)} by ${bidder}`);
        }
        items.push({
          kind: 'group',
          id: event.event_id,
          title: 'Auction updates',
          summary: summaryParts.join(' - '),
          lines: detailLines,
          tone: 'info',
        });
        i = j;
        continue;
      }

      if (event.type === 'CASH_CHANGED') {
        const playerId = event.payload.player_id;
        const detailLines: string[] = [];
        let total = 0;
        const reasons: string[] = [];
        let j = i;
        while (j < rawEvents.length) {
          const next = rawEvents[j];
          if (!isCashChanged(next)) break;
          if (next.payload.player_id !== playerId) break;
          total += next.payload.delta;
          reasons.push(next.payload.reason);
          detailLines.push(`${formatMoney(next.payload.delta, true)} (${next.payload.reason})`);
          j += 1;
        }
        const playerLabel = formatPlayer(playerId, playerNames);
        const uniqueReasons = Array.from(new Set(reasons));
        const reasonText = uniqueReasons.length ? ` (${uniqueReasons.join(', ')})` : '';
        items.push({
          kind: 'group',
          id: event.event_id,
          title: 'Cash updates',
          summary: `${playerLabel} cash ${formatMoney(total, true)}${reasonText}`,
          lines: detailLines,
          tone: total >= 0 ? 'success' : 'danger',
        });
        i = j;
        continue;
      }

      if (!SKIP_TYPES.has(event.type)) {
        const systemLine = formatSystemEvent(event, playerNames);
        if (systemLine) {
          items.push({ kind: 'system', id: event.event_id, text: systemLine.text, tone: systemLine.tone });
        }
      }
      i += 1;
    }

    return {
      id: block.id,
      turnIndex: block.turnIndex,
      playerId,
      items,
    };
  });
};

const LlmBubble = ({
  playerId,
  playerLabel,
  modelLabel,
  message,
  onInspect,
}: {
  playerId: string;
  playerLabel: string;
  modelLabel?: string;
  message: string;
  onInspect: () => void;
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
        <button
          type="button"
          onClick={onInspect}
          className="brutal-btn bg-neo-yellow text-[9px] py-0.5 px-2"
        >
          Inspect
        </button>
      </div>
      <div className="max-w-[90%] border-2 border-black p-3 text-sm shadow-neo-sm bg-white text-black">
        <div className="whitespace-pre-wrap">{message}</div>
      </div>
    </div>
  );
};

const SystemCard = ({ text, tone }: { text: string; tone?: FeedSystemTone }) => (
  <div className="flex justify-center">
    <div
      className={cn(
        'px-3 py-1 text-[11px] font-bold uppercase border-2 shadow-neo-sm bg-neo-bg',
        tone ? toneClasses[tone] : 'border-black'
      )}
    >
      {text}
    </div>
  </div>
);

const GroupCard = ({
  title,
  summary,
  lines,
  tone,
}: {
  title: string;
  summary: string;
  lines: string[];
  tone?: FeedSystemTone;
}) => (
  <details className="border-2 border-black bg-white shadow-neo-sm">
    <summary className="cursor-pointer list-none px-3 py-2 flex items-center justify-between gap-2">
      <div className="text-[10px] font-bold uppercase text-gray-500">{title}</div>
      <div className="text-[11px] font-medium text-gray-900 flex-1">{summary}</div>
      <span className={cn('text-[9px] font-bold uppercase', tone ? toneTextClasses[tone] : 'text-gray-500')}>
        Details
      </span>
    </summary>
    <div className="border-t-2 border-black/10 px-3 py-2 text-[11px] text-gray-700 space-y-1">
      {lines.map((line, index) => (
        <div key={`${title}-line-${index}`}>{line}</div>
      ))}
    </div>
  </details>
);

export const ChatFeed = () => {
  const events = useGameStore((state) => state.events);
  const players = useGameStore((state) => state.runStatus.players ?? []);
  const setInspectorOpen = useGameStore((state) => state.setInspectorOpen);
  const setInspectorFocus = useGameStore((state) => state.setInspectorFocus);
  const logResetId = useGameStore((state) => state.logResetId);
  const containerRef = useRef<HTMLDivElement>(null);
  const [showThoughts, setShowThoughts] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);

  const playerNames = useMemo(() => {
    const map = new Map<string, string>();
    players.forEach((player) => {
      map.set(player.player_id, player.name);
    });
    return map;
  }, [players]);

  const modelByPlayerId = useMemo(() => {
    const map = new Map<string, string>();
    players.forEach((player) => {
      map.set(player.player_id, player.model_display_name);
    });
    return map;
  }, [players]);

  const turnBlocks = useMemo(() => buildTurnBlocks(events, playerNames), [events, playerNames]);

  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [autoScroll, turnBlocks]);

  useEffect(() => {
    setAutoScroll(true);
  }, [logResetId]);

  const handleScroll = (event: UIEvent<HTMLDivElement>) => {
    const { scrollTop, scrollHeight, clientHeight } = event.currentTarget;
    const nearBottom = scrollHeight - scrollTop - clientHeight < 40;
    setAutoScroll(nearBottom);
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
        className="flex-1 overflow-y-auto p-3 brutal-scroll space-y-6"
        onScroll={handleScroll}
      >
        {turnBlocks.length === 0 && (
          <div className="flex flex-col items-center justify-center pt-12 text-gray-400 opacity-60">
            <span className="text-3xl mb-2">?</span>
            <span className="font-brutal text-xs">Waiting for messages...</span>
          </div>
        )}

        {turnBlocks.map((block) => {
          const playerLabel = block.playerId ? formatPlayer(block.playerId, playerNames) : 'System';
          return (
            <div key={block.id} className="space-y-3">
              <div className="flex items-center gap-2">
                <NeoBadge variant="neutral" className="text-[9px]">
                  {block.turnIndex !== null ? `Turn ${block.turnIndex}` : 'Setup'}
                </NeoBadge>
                <span className="text-[10px] font-bold uppercase text-gray-600">{playerLabel}</span>
                <div className="h-[1px] flex-1 bg-black/10" />
              </div>

              <div className="space-y-3">
                {block.items.map((item) => {
                  if (item.kind === 'system') {
                    return <SystemCard key={item.id} text={item.text} tone={item.tone} />;
                  }
                  if (item.kind === 'group') {
                    return (
                      <GroupCard
                        key={item.id}
                        title={item.title}
                        summary={item.summary}
                        lines={item.lines}
                        tone={item.tone}
                      />
                    );
                  }
                  return (
                    <LlmBubble
                      key={item.id}
                      playerId={item.playerId}
                      playerLabel={item.playerLabel}
                      modelLabel={modelByPlayerId.get(item.playerId)}
                      message={item.message}
                      onInspect={() => {
                        setInspectorFocus({ decisionId: item.decisionId, eventId: item.id });
                        setInspectorOpen(true);
                      }}
                    />
                  );
                })}
              </div>
            </div>
          );
        })}

        {showThoughts && players.length > 0 && <ThoughtsPanel />}
      </div>
    </div>
  );
};
