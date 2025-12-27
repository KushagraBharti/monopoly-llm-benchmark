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

const severityStyles: Record<EventSeverity, string> = {
  neutral: 'border-black/20 bg-white',
  info: 'border-l-4 border-neo-blue bg-blue-50',
  success: 'border-l-4 border-neo-green bg-green-50',
  warning: 'border-l-4 border-neo-yellow bg-yellow-50',
  danger: 'border-l-4 border-neo-pink bg-red-50',
};

const PlayerName = ({ id }: { id: string }) => (
  <span
    className="font-black px-1.5 py-0.5 border border-black text-[10px] uppercase align-middle inline-flex items-center"
    style={{ backgroundColor: getPlayerColor(id), color: 'white' }}
  >
    {id}
  </span>
);

const MoneyAmount = ({ amount, showSign }: { amount: number; showSign?: boolean }) => {
  const isNegative = amount < 0;
  return (
    <span className={cn('font-mono font-bold', isNegative ? 'text-red-600' : 'text-green-600')}>
      {formatMoney(amount, showSign)}
    </span>
  );
};

const SpaceLabel = ({ index }: { index: number }) => (
  <span className="font-mono text-[9px] border border-black px-1 py-0.5 bg-white">
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
      return <span key={`part-${index}`}>{part.value}</span>;
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

const EventItem = ({ event }: { event: Event }) => {
  const [expanded, setExpanded] = useState(false);
  const card = useMemo(() => formatEventCard(event), [event]);

  return (
    <div
      className={cn(
        'relative transition-all duration-300 animate-fade-in-up hover:z-10 mb-1',
        card.isMinor && 'opacity-70 hover:opacity-100'
      )}
    >
      <div className={cn('border-2 p-2 shadow-sm text-sm flex flex-col gap-1', severityStyles[card.severity])}>
        <div className="flex justify-between items-start gap-2">
          <div className="flex items-start gap-2">
            <span className="text-[10px] font-mono bg-black text-white px-1 py-0.5 border border-black">
              {card.icon}
            </span>
            <div className="flex flex-col">
              <span className="font-black text-[10px] uppercase text-gray-600 tracking-wider">
                {card.title}
                <span className="font-mono font-normal opacity-50 ml-1">#{card.turnIndex}</span>
              </span>
              <div className="mt-1 flex flex-wrap gap-1 items-center">
                {card.parts.map(renderPart)}
              </div>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setExpanded((prev) => !prev)}
            className="text-[10px] font-mono opacity-50 hover:opacity-100"
          >
            {expanded ? 'HIDE' : 'DETAILS'}
          </button>
        </div>

        {card.badges.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {card.badges.map((badge, idx) => (
              <Badge key={`${badge.text}-${idx}`} badge={badge} />
            ))}
          </div>
        )}

        {expanded && (
          <div className="mt-2 pt-2 border-t border-dashed border-gray-300">
            <div className="flex justify-between items-center mb-1">
              <span className="text-[9px] font-bold uppercase">Raw Event</span>
            </div>
            <pre className="text-[9px] font-mono bg-gray-50 p-1 overflow-x-auto text-gray-700">
              {JSON.stringify(card.details, null, 2)}
            </pre>
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
    <div className="flex flex-col h-full bg-slate-50 border-t-2 border-black relative">
      <div ref={containerRef} className="flex-1 overflow-y-auto p-2 space-y-2" onScroll={handleScroll}>
        {events.length === 0 && (
          <div className="text-center text-gray-400 mt-10 italic text-sm">Waiting for events...</div>
        )}

        {events.map((event, index) => (
          <EventItem key={`${event.event_id}-${index}`} event={event} />
        ))}
      </div>

      {!autoScroll && (
        <button
          type="button"
          onClick={() => setAutoScroll(true)}
          className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-black text-white text-xs px-3 py-1 shadow-lg z-20 hover:bg-gray-800 transition border-2 border-black"
        >
          Resume Auto-scroll
        </button>
      )}
    </div>
  );
};
