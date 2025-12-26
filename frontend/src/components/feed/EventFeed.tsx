import { useEffect, useRef } from 'react';
import type { Event } from '../../net/contracts';
import { useGameStore } from '../../state/store';
import { cn } from '../ui/NeoPrimitive';

const EventItem = ({ event }: { event: Event }) => {
    // Render specific event types differently
    let content = null;
    let icon = '📢';

    switch (event.type) {
        case 'DICE_ROLLED':
            icon = '🎲';
            content = (
                <span>
                    Rolled <b>{event.payload.d1} + {event.payload.d2}</b>
                    {event.payload.is_double && <span className="text-neo-pink ml-2 font-black">DOUBLES!</span>}
                </span>
            );
            break;
        case 'PLAYER_MOVED':
            icon = '🏃';
            content = <span>Moved {event.payload.from} &rarr; {event.payload.to}</span>;
            break;
        case 'PROPERTY_PURCHASED':
            icon = '🏠';
            content = (
                <span>
                    Bought property at {event.payload.space_index} for
                    <b className="text-green-600 ml-1">${event.payload.price}</b>
                </span>
            );
            break;
        case 'RENT_PAID':
            icon = '💸';
            content = (
                <span>
                    Paid rent: <b className="text-red-600">${event.payload.amount}</b> to {event.payload.to_player_id}
                </span>
            );
            break;
        case 'LLM_PUBLIC_MESSAGE':
            icon = '💬';
            content = <span className="italic">"{event.payload.message}"</span>;
            break;
        default:
            // Generic payload rendering
            content = <span className="text-xs opacity-70">{JSON.stringify(event.payload)}</span>;
    }

    return (
        <div className="border-b-2 border-black/10 last:border-0 py-2 flex gap-2 items-start animate-fade-in-up">
            <span className="text-lg select-none">{icon}</span>
            <div className="flex flex-col">
                <span className="text-[10px] uppercase font-bold text-gray-400">{event.type.replace(/_/g, ' ')}</span>
                <div className="text-sm leading-tight">{content}</div>
            </div>
        </div>
    );
};

export const EventFeed = () => {
    const events = useGameStore((state) => state.events);
    const bottomRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [events]);

    return (
        <div className="flex flex-col h-full space-y-2">
            <div className="flex-1 overflow-y-auto pr-1 space-y-1">
                {[...events].reverse().map((event, index) => (
                    <div
                        key={`${event.event_id}-${index}`}
                        className={cn("animate-fade-in-up")}
                        style={{ animationDelay: `${index * 50}ms` }}
                    >
                        <EventItem event={event} />
                    </div>
                ))}
                <div ref={bottomRef} />
            </div>
        </div>
    );
};
