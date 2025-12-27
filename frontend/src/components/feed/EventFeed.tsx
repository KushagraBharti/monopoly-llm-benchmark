import { useEffect, useMemo, useRef, useState } from 'react';
import type { Event } from '../../net/contracts';
import { useGameStore } from '../../state/store';
import { cn, NeoBadge } from '../ui/NeoPrimitive';
import { getPlayerColor } from '../../domain/monopoly/colors';
import {
  formatEventCard,
  formatMoney,
  formatSpaceLabel,
  type EventBadge,
  type EventCardPart,
  type EventSeverity,
} from '../../domain/monopoly/formatters';

const severityBorders: Record<EventSeverity, string> = {
  neutral: 'border-neo-border',
  info: 'border-neo-blue',
  success: 'border-neo-green',
  warning: 'border-neo-yellow',
  danger: 'border-neo-pink',
};

const KNOWN_EVENT_TYPES = new Set<string>([
  'GAME_STARTED',
  'TURN_STARTED',
  'DICE_ROLLED',
  'PLAYER_MOVED',
  'CASH_CHANGED',
  'PROPERTY_PURCHASED',
  'RENT_PAID',
  'SENT_TO_JAIL',
  'TURN_ENDED',
  'GAME_ENDED',
  'LLM_DECISION_REQUESTED',
  'LLM_DECISION_RESPONSE',
  'LLM_PUBLIC_MESSAGE',
  'LLM_PRIVATE_THOUGHT',
]);

const PlayerName = ({ id }: { id: string }) => (
  <span
    className="font-brutal px-1.5 py-0.5 border border-black text-[10px] items-center inline-flex shadow-[1px_1px_0px_0px_rgba(0,0,0,1)]"
    style={{ backgroundColor: getPlayerColor(id), color: 'white' }}
  >
    {id}
  </span>
);

const MoneyAmount = ({ amount, showSign }: { amount: number; showSign?: boolean }) => {
  const isNegative = amount < 0;
  return (
    <span className={cn('font-mono font-bold', isNegative ? 'text-neo-red' : 'text-neo-green')}>
      {formatMoney(amount, showSign)}
    </span>
  );
};

const SpaceLabel = ({ index }: { index: number }) => (
  <span className="font-mono text-[9px] border border-black px-1 py-0.5 bg-neo-white shadow-[1px_1px_0px_0px_rgba(0,0,0,1)]">
    {formatSpaceLabel(index)}
  </span>
);

const Badge = ({ badge }: { badge: EventBadge }) => {
  const variant = badge.tone === 'success'
    ? 'success'
    : badge.tone === 'warning'
      ? 'warning'
      : badge.tone === 'danger'
        ? 'error'
        : badge.tone === 'info'
          ? 'info'
          : 'neutral';
  return (
    <NeoBadge variant={variant} className="text-[9px]">
      {badge.text}
    </NeoBadge>
  );
};

const renderPart = (part: EventCardPart, index: number) => {
  switch (part.kind) {
    case 'text':
      return <span key={`part-${index}`} className="font-medium">{part.value}</span>;
    case 'player':
      return <PlayerName key={`part-${index}`} id={part.playerId} />;
    case 'money':
      return (
        <MoneyAmount key={`part-${index}`} amount={part.amount} showSign={part.showSign} />
      );
    case 'space':
      return <SpaceLabel key={`part-${index}`} index={part.spaceIndex} />;
    default:
      return null;
  }
};

const ChevronIcon = ({ expanded }: { expanded: boolean }) => (
  <svg
    className={cn("w-4 h-4 transition-transform duration-200", expanded && "rotate-180")}
    viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"
  >
    <path d="M6 9l6 6 6-6" />
  </svg>
);

const EventItem = ({ event }: { event: Event }) => {
  const [expanded, setExpanded] = useState(false);
  const card = useMemo(() => formatEventCard(event), [event]);

  // "Unknown" events should look distinct but clean
  const isUnknown = !KNOWN_EVENT_TYPES.has(event.type);

  return (
    <div
      onClick={() => setExpanded(!expanded)}
      className={cn(
        'group relative mb-2 cursor-pointer select-none outline-none',
        'animate-snap-in',
        card.isMinor && !expanded ? 'opacity-70 hover:opacity-100' : 'opacity-100'
      )}
    >
      <div className={cn(
        'bg-white border-2 p-2 shadow-neo transition-all duration-150',
        'group-hover:translate-x-[-1px] group-hover:translate-y-[-1px] group-hover:shadow-neo-lg',
        severityBorders[card.severity]
      )}>
        <div className="flex justify-between items-start gap-2">
          {/* Left: Icon */}
          <div className="flex-shrink-0 pt-0.5">
            <span className={cn(
              "flex items-center justify-center w-6 h-6 border-2 border-black bg-neo-bg font-mono text-sm shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]",
              isUnknown && "bg-gray-200 text-gray-500"
            )}>
              {card.icon}
            </span>
          </div>

          {/* Center: Content */}
          <div className="flex-1 min-w-0 flex flex-col gap-1">
            <div className="flex items-baseline justify-between">
              <span className="font-brutal text-xs uppercase tracking-wide leading-none">
                {card.title}
                <span className="ml-2 font-mono text-[9px] text-gray-400 font-normal">#{card.turnIndex}</span>
              </span>
            </div>

            <div className="text-xs leading-snug flex flex-wrap gap-x-1 gap-y-1 items-center">
              {card.parts.map(renderPart)}
            </div>
          </div>

          {/* Right: Chevron */}
          <div className="flex-shrink-0 text-black opacity-40 group-hover:opacity-100 transition-opacity self-start pt-1">
            <ChevronIcon expanded={expanded} />
          </div>
        </div>

        {/* Badges Footer (if any or expanded) */}
        {(card.badges.length > 0 || expanded) && (
          <div className={cn(
            "mt-2 pt-2 border-t-2 border-dashed border-gray-200 flex flex-wrap gap-1 transition-all",
            !expanded && card.badges.length === 0 && "hidden"
          )}>
            {card.badges.map((badge, idx) => (
              <Badge key={`${badge.text}-${idx}`} badge={badge} />
            ))}
          </div>
        )}

        {/* Expanded Details: Raw JSON */}
        {expanded && (
          <div className="mt-2 text-[10px] font-mono">
            <div className="bg-neo-bg border-2 border-black p-2 shadow-inner overflow-x-auto">
              <pre className="text-gray-700 whitespace-pre-wrap break-all">
                {JSON.stringify(card.details, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export const EventFeed = () => {
  const events = useGameStore((state) => state.events);
  const containerRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = 0;
    }
  }, [events, autoScroll]);

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const { scrollTop } = e.currentTarget;
    setAutoScroll(scrollTop < 20);
  };

  return (
    <div className="flex flex-col h-full bg-white border-t-2 border-black font-sans">
      {/* Resume Banner */}
      {!autoScroll && (
        <div className="absolute top-2 left-1/2 -translate-x-1/2 z-30">
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
        className="flex-1 overflow-y-auto p-2 brutal-scroll space-y-2 pb-10"
        onScroll={handleScroll}
      >
        {events.length === 0 && (
          <div className="flex flex-col items-center justify-center pt-20 text-gray-400 opacity-50">
            <span className="text-4xl mb-2">⚡</span>
            <span className="font-brutal text-xs">Waiting for events...</span>
          </div>
        )}

        {events.map((event, index) => (
          <EventItem key={`${event.event_id}-${index}`} event={event} />
        ))}
      </div>
    </div>
  );
};
