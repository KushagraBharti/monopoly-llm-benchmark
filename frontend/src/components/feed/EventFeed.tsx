import { useEffect, useRef, useState } from 'react';
import type { Event } from '../../net/contracts';
import { useGameStore } from '../../state/store';
import { cn, NeoBadge } from '../ui/NeoPrimitive';
import { getPlayerColor } from '../board/constants';

const EventItem = ({ event }: { event: Event }) => {
    const [expanded, setExpanded] = useState(false);

    // Default Styling
    let icon = '📢';
    let title = event.type.replace(/_/g, ' ');
    let description: React.ReactNode = null;
    let variant: 'default' | 'flat' = 'flat';
    let borderColor = 'border-black/10';

    // Helper to colorize player names
    const PlayerName = ({ id }: { id: string }) => (
        <span
            className="font-black px-1 border border-black text-[10px] uppercase align-middle mx-1"
            style={{ backgroundColor: getPlayerColor(id), color: 'white' }}
        >
            {id}
        </span>
    );

    switch (event.type) {
        case 'TURN_STARTED':
            icon = '⏱️';
            borderColor = 'border-l-4 border-l-black';
            description = <span>Turn started.</span>;
            break;
        case 'DICE_ROLLED':
            icon = '🎲';
            description = (
                <span>
                    Rolled <b>{event.payload.d1} + {event.payload.d2}</b>
                    {event.payload.is_double && <span className="text-neo-pink ml-2 font-black animate-pulse">DOUBLES!</span>}
                </span>
            );
            break;
        case 'PLAYER_MOVED':
            icon = '🏃';
            description = (
                <span>
                    Moved from <b className="font-mono">{event.payload.from}</b> &rarr; <b className="font-mono">{event.payload.to}</b>
                </span>
            );
            break;
        case 'PROPERTY_PURCHASED':
            icon = '🏠';
            variant = 'default'; // Pop out a bit
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
            borderColor = 'border-red-500 border-2'; // Drama
            description = (
                <span>
                    Paid rent <b className="text-red-600 font-mono text-lg">-${event.payload.amount}</b> to <PlayerName id={event.payload.to_player_id} />
                </span>
            );
            break;
        case 'TURN_ENDED':
            icon = 'zzz';
            description = <span className="opacity-50">Turn ended.</span>;
            break;
        case 'GAME_ENDED':
            icon = '🏆';
            variant = 'default';
            borderColor = 'border-gold border-4 bg-yellow-50';
            title = "GAME OVER";
            description = <span className="font-black text-lg">WINNER: {event.payload.winner_player_id}</span>;
            break;
        case 'LLM_PUBLIC_MESSAGE':
            icon = '💬';
            description = <span className="italic font-serif bg-slate-100 p-1 block mt-1 border-l-2 border-gray-400">"{event.payload.message}"</span>;
            break;
        default:
            description = <span className="text-xs opacity-50">Unparsed event type</span>;
    }

    return (
        <div
            className={cn(
                "relative transition-all duration-300 animate-fade-in-up hover:z-10",
                variant === 'default' ? "mb-3 scale-[1.01]" : "mb-1 opacity-90 hover:opacity-100"
            )}
        >
            <div className={cn("bg-white border-2 p-2 shadow-sm text-sm flex flex-col gap-1", borderColor)}>
                {/* Header Line */}
                <div className="flex justify-between items-start cursor-pointer select-none" onClick={() => setExpanded(!expanded)}>
                    <div className="flex items-center gap-2">
                        <span className="text-lg">{icon}</span>
                        <div className="flex flex-col leading-none">
                            <span className="font-black text-[10px] uppercase text-gray-500 tracking-wider">
                                {title} <span className="font-mono font-normal opacity-50 ml-1">#{event.turn_index}</span>
                            </span>
                            <div className="mt-1">
                                {description}
                            </div>
                        </div>
                    </div>
                    <button className="text-[10px] font-mono opacity-40 hover:opacity-100">{expanded ? '▲' : '▼'}</button>
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

export const EventFeed = () => {
    const events = useGameStore((state) => state.events);
    const bottomRef = useRef<HTMLDivElement>(null);
    const [autoScroll, setAutoScroll] = useState(true);

    // Auto-scroll logic
    useEffect(() => {
        if (autoScroll && bottomRef.current) {
            bottomRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [events, autoScroll]);

    // Detect if user scrolled up to disable auto-scroll (simplistic)
    const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
        const { scrollTop, scrollHeight, clientHeight } = e.currentTarget;
        if (scrollHeight - scrollTop - clientHeight > 50) {
            setAutoScroll(false);
        } else {
            setAutoScroll(true);
        }
    };

    return (
        <div className="flex flex-col h-full bg-slate-50 border-t-2 border-black relative">
            <div
                className="flex-1 overflow-y-auto p-2 space-y-2 pb-10"
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

                <div ref={bottomRef} className="h-4" />
            </div>

            {/* Auto-scroll resume button */}
            {!autoScroll && (
                <button
                    onClick={() => setAutoScroll(true)}
                    className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-blue-500 text-white text-xs px-3 py-1 rounded-full shadow-lg z-20 hover:bg-blue-600 transition"
                >
                    Resume Scroll ⬇
                </button>
            )}
        </div>
    );
};
