import { useEffect, useRef, useState, useMemo } from 'react';
import type { Event } from '../../net/contracts';
import { useGameStore } from '../../state/store';
import { cn, NeoBadge } from '../ui/NeoPrimitive';
import { getPlayerColor } from '../board/constants';

/**
 * PlayerName component - renders a player name badge with their color
 */
const PlayerName = ({ id }: { id: string }) => (
    <span
        className="font-black px-1.5 py-0.5 border border-black text-[10px] uppercase align-middle mx-0.5 inline-flex items-center"
        style={{ backgroundColor: getPlayerColor(id), color: 'white' }}
    >
        {id}
    </span>
);

/**
 * Format a dollar amount with color for gains/losses
 */
const DollarAmount = ({ amount, showSign = false }: { amount: number; showSign?: boolean }) => {
    const isNegative = amount < 0;
    const displayAmount = Math.abs(amount);
    const sign = showSign ? (isNegative ? '-' : '+') : '';

    return (
        <span className={cn(
            "font-mono font-bold",
            isNegative ? "text-red-600" : "text-green-600"
        )}>
            {sign}${displayAmount}
        </span>
    );
};

/**
 * EventItem - renders a single event card
 */
const EventItem = ({ event }: { event: Event }) => {
    const [expanded, setExpanded] = useState(false);

    // Derive rendering properties based on event type
    const { icon, title, description, variant, borderColor, isMinor } = useMemo(() => {
        let icon = '📢';
        let title = event.type.replace(/_/g, ' ');
        let description: React.ReactNode = null;
        let variant: 'default' | 'flat' = 'flat';
        let borderColor = 'border-black/10';
        let isMinor = false;

        switch (event.type) {
            // === Game Lifecycle ===
            case 'GAME_STARTED':
                icon = '🎬';
                title = 'GAME STARTED';
                variant = 'default';
                borderColor = 'border-neo-green border-l-4';
                description = <span className="font-bold">The game has begun!</span>;
                break;

            case 'GAME_ENDED':
                icon = '🏆';
                variant = 'default';
                borderColor = 'border-neo-yellow border-4 bg-yellow-50';
                title = 'GAME OVER';
                description = (
                    <span className="font-black text-lg">
                        WINNER: <PlayerName id={event.payload.winner_player_id} />
                    </span>
                );
                break;

            // === Turn Lifecycle ===
            case 'TURN_STARTED':
                icon = '⏱️';
                borderColor = 'border-l-4 border-l-black';
                description = (
                    <span>
                        {event.actor?.player_id
                            ? <><PlayerName id={event.actor.player_id} /> is up!</>
                            : 'Turn started.'
                        }
                    </span>
                );
                break;

            case 'TURN_ENDED':
                icon = '✓';
                isMinor = true;
                description = <span className="opacity-60">Turn ended.</span>;
                break;

            // === Dice & Movement ===
            case 'DICE_ROLLED':
                icon = '🎲';
                description = (
                    <span>
                        Rolled <b className="text-lg font-mono">{event.payload.d1} + {event.payload.d2}</b>
                        {' = '}<b className="font-mono">{event.payload.d1 + event.payload.d2}</b>
                        {event.payload.is_double && (
                            <span className="text-neo-pink ml-2 font-black animate-pulse">DOUBLES!</span>
                        )}
                    </span>
                );
                break;

            case 'PLAYER_MOVED':
                icon = '🏃';
                description = (
                    <span>
                        Moved <b className="font-mono">{event.payload.from}</b> → <b className="font-mono">{event.payload.to}</b>
                        {event.payload.passed_go && (
                            <NeoBadge variant="success" className="ml-2">Passed GO!</NeoBadge>
                        )}
                    </span>
                );
                break;

            // === Property Actions ===
            case 'PROPERTY_PURCHASED':
                icon = '🏠';
                variant = 'default';
                borderColor = 'border-neo-green border-l-4';
                description = (
                    <span>
                        Purchased <b>Space {event.payload.space_index}</b> for
                        <NeoBadge variant="success" className="ml-2">${event.payload.price}</NeoBadge>
                    </span>
                );
                break;

            case 'RENT_PAID':
                icon = '💸';
                variant = 'default';
                borderColor = 'border-red-500 border-l-4';
                description = (
                    <span>
                        Paid rent <span className="text-red-600 font-mono font-bold text-lg">-${event.payload.amount}</span>
                        {' '}to <PlayerName id={event.payload.to_player_id} />
                    </span>
                );
                break;

            // === Cash Changes ===
            case 'CASH_CHANGED':
                icon = event.payload.delta >= 0 ? '💰' : '💳';
                isMinor = true;
                description = (
                    <span>
                        <PlayerName id={event.payload.player_id} />
                        {' '}<DollarAmount amount={event.payload.delta} showSign />
                        <span className="text-gray-500 ml-1 text-xs">({event.payload.reason})</span>
                    </span>
                );
                break;

            // === Jail ===
            case 'SENT_TO_JAIL':
                icon = '🔒';
                variant = 'default';
                borderColor = 'border-orange-500 border-l-4';
                description = (
                    <span>
                        <PlayerName id={event.payload.player_id} /> sent to jail!
                        <span className="text-gray-500 ml-1 text-xs">({event.payload.reason})</span>
                    </span>
                );
                break;

            // === LLM Events ===
            case 'LLM_DECISION_REQUESTED':
                icon = '🤖';
                isMinor = true;
                description = (
                    <span className="flex items-center gap-2">
                        <PlayerName id={event.payload.player_id} />
                        <span className="opacity-60">thinking...</span>
                        <span className="animate-pulse">💭</span>
                    </span>
                );
                break;

            case 'LLM_DECISION_RESPONSE':
                icon = event.payload.valid ? '✅' : '❌';
                isMinor = !event.payload.valid; // Show invalid decisions more prominently
                borderColor = event.payload.valid ? 'border-black/10' : 'border-red-400 border-l-4';
                description = (
                    <span>
                        <PlayerName id={event.payload.player_id} />
                        {' chose: '}<b className="font-mono">{event.payload.action_name}</b>
                        {!event.payload.valid && event.payload.error && (
                            <span className="text-red-500 text-xs block mt-1">⚠️ {event.payload.error}</span>
                        )}
                    </span>
                );
                break;

            case 'LLM_PUBLIC_MESSAGE':
                icon = '💬';
                description = (
                    <span className="italic font-serif bg-slate-100 p-2 block mt-1 border-l-2 border-gray-400">
                        "{event.payload.message}"
                    </span>
                );
                break;

            case 'LLM_PRIVATE_THOUGHT':
                // These are shown in inspector, render minimal in feed
                icon = '💭';
                isMinor = true;
                description = (
                    <span className="opacity-50 italic">
                        <PlayerName id={event.payload.player_id} /> thinking...
                    </span>
                );
                break;

            // === Fallback (handles any future or unknown event types) ===
            default: {
                // Cast to access properties on the exhausted type
                const unknownEvent = event as { type: string; payload?: Record<string, unknown> };
                icon = '📋';
                isMinor = true;
                description = (
                    <span className="text-xs text-gray-500">
                        Unknown event: <code className="bg-gray-100 px-1">{unknownEvent.type}</code>
                    </span>
                );
            }
        }

        return { icon, title, description, variant, borderColor, isMinor };
    }, [event]);

    return (
        <div
            className={cn(
                "relative transition-all duration-300 animate-fade-in-up hover:z-10",
                variant === 'default' ? "mb-3 scale-[1.01]" : "mb-1",
                isMinor && "opacity-80 hover:opacity-100"
            )}
        >
            <div className={cn(
                "bg-white border-2 p-2 shadow-sm text-sm flex flex-col gap-1",
                borderColor
            )}>
                {/* Header Line */}
                <div
                    className="flex justify-between items-start cursor-pointer select-none"
                    onClick={() => setExpanded(!expanded)}
                >
                    <div className="flex items-center gap-2">
                        <span className="text-lg">{icon}</span>
                        <div className="flex flex-col leading-none">
                            <span className="font-black text-[10px] uppercase text-gray-500 tracking-wider">
                                {title}
                                <span className="font-mono font-normal opacity-50 ml-1">#{event.turn_index}</span>
                            </span>
                            <div className="mt-1">
                                {description}
                            </div>
                        </div>
                    </div>
                    <button className="text-[10px] font-mono opacity-40 hover:opacity-100">
                        {expanded ? '▲' : '▼'}
                    </button>
                </div>

                {/* Expanded Details */}
                {expanded && (
                    <div className="mt-2 pt-2 border-t border-dashed border-gray-300">
                        <div className="flex justify-between items-center mb-1">
                            <span className="text-[9px] font-bold uppercase">Raw Payload</span>
                            {event.actor?.player_id && <PlayerName id={event.actor.player_id} />}
                        </div>
                        <pre className="text-[9px] font-mono bg-gray-50 p-1 overflow-x-auto text-gray-600">
                            {JSON.stringify(event.payload, null, 2)}
                        </pre>
                    </div>
                )}
            </div>
        </div>
    );
};

/**
 * EventFeed - scrollable feed of game events
 */
export const EventFeed = () => {
    const events = useGameStore((state) => state.events);
    const containerRef = useRef<HTMLDivElement>(null);
    const [autoScroll, setAutoScroll] = useState(true);

    // Auto-scroll to top (newest events) when new events arrive
    useEffect(() => {
        if (autoScroll && containerRef.current) {
            containerRef.current.scrollTop = 0;
        }
    }, [events, autoScroll]);

    // Detect if user scrolled away from top to disable auto-scroll
    const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
        const { scrollTop } = e.currentTarget;
        setAutoScroll(scrollTop < 20);
    };

    return (
        <div className="flex flex-col h-full bg-slate-50 border-t-2 border-black relative">
            <div
                ref={containerRef}
                className="flex-1 overflow-y-auto p-2 space-y-2"
                onScroll={handleScroll}
            >
                {events.length === 0 && (
                    <div className="text-center text-gray-400 mt-10 italic text-sm">
                        Waiting for events...
                    </div>
                )}

                {events.map((event, index) => (
                    <EventItem key={`${event.event_id}-${index}`} event={event} />
                ))}
            </div>

            {/* Auto-scroll resume button */}
            {!autoScroll && (
                <button
                    onClick={() => setAutoScroll(true)}
                    className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-black text-white text-xs px-3 py-1 shadow-lg z-20 hover:bg-gray-800 transition border-2 border-black"
                >
                    ⬆ Resume Auto-scroll
                </button>
            )}
        </div>
    );
};
