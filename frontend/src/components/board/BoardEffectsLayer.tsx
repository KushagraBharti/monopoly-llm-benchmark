import { useEffect, useState, useRef } from 'react';
import { useGameStore } from '@/state/store';
import { CardModal } from '@/components/board/CardModal';
import { PropertyToast } from '@/components/board/PropertyToast';
import { getCardDetails } from '@/domain/monopoly/cardData';
import type { Event } from '@/net/contracts';
import { AnimatePresence, motion } from 'framer-motion';
import { getCSSPosition } from './utils';

type AnimationItem =
    | { type: 'CARD'; event: Event & { type: 'CARD_DRAWN' } }
    | { type: 'PROPERTY'; event: Event; method: 'BOUGHT' | 'WON' | 'TRADED'; spaceIndex: number; price?: number }
    | { type: 'JAIL'; event: Event & { type: 'SENT_TO_JAIL' } }
    | { type: 'CASH'; amount: number; playerId: string; reason?: string; key: string };

export const BoardEffectsLayer = () => {
    const events = useGameStore((state) => state.events);
    const snapshot = useGameStore((state) => state.snapshot);
    const [queue, setQueue] = useState<AnimationItem[]>([]);
    const [floatingTexts, setFloatingTexts] = useState<AnimationItem[]>([]); // allow multiple floating texts
    const [activeItem, setActiveItem] = useState<AnimationItem | null>(null);
    const processedEventIds = useRef<Set<string>>(new Set());

    // Ingest events
    useEffect(() => {
        if (!events.length) return;

        // Check new events (we usually get them LIFO or FIFO depending on store? Store pushes to front [event, ...state.events])
        // Actually store pushes: const nextEvents = isGameStart ? [event] : [event, ...state.events]
        // So events[0] is LATEST.
        // We need to process them in chronological order if possible, or just process the latest if we are live.
        // For simplicity, let's just look at events[0] if it's new.

        const latestInfo = events[0];
        if (!latestInfo || processedEventIds.current.has(latestInfo.event_id)) return;

        processedEventIds.current.add(latestInfo.event_id);

        let newItem: AnimationItem | null = null;

        if (latestInfo.type === 'CARD_DRAWN') {
            newItem = { type: 'CARD', event: latestInfo };
            setQueue(prev => [...prev, newItem!]);
        } else if (latestInfo.type === 'PROPERTY_PURCHASED') {
            newItem = {
                type: 'PROPERTY',
                event: latestInfo,
                method: 'BOUGHT',
                spaceIndex: latestInfo.payload.space_index,
                price: latestInfo.payload.price
            };
            setQueue(prev => [...prev, newItem!]);
        } else if (latestInfo.type === 'AUCTION_ENDED' && latestInfo.payload.winner_player_id) {
            // We need to find the space index from property name or wait?
            // snapshot has the board. We can find space by name.
            const board = snapshot?.board || [];
            const space = board.find(s => s.name === latestInfo.payload.property_space);
            if (space) {
                newItem = {
                    type: 'PROPERTY',
                    event: latestInfo,
                    method: 'WON',
                    spaceIndex: space.index,
                    price: latestInfo.payload.winning_bid || 0
                };
                setQueue(prev => [...prev, newItem!]);
            }
        } else if (latestInfo.type === 'SENT_TO_JAIL') {
            newItem = { type: 'JAIL', event: latestInfo };
            setQueue(prev => [...prev, newItem!]);
        } else if (latestInfo.type === 'RENT_PAID') {
            // Rent paid involves two players: Payer and Payee.
            // Show -Amount for Payer, +Amount for Payee.
            const { from_player_id, to_player_id, amount } = latestInfo.payload;
            addFloatingText(-amount, from_player_id, "Rent Paid", latestInfo.event_id + "_out");
            addFloatingText(amount, to_player_id, "Rent Received", latestInfo.event_id + "_in");
        } else if (latestInfo.type === 'CASH_CHANGED') {
            // Only show significant cash changes that aren't rent (covered above) or property buying (redundant with toast? maybe show both)
            // Let's filter out Reason: "Rent" if it acts as duplicate, but usually CASH_CHANGED comes with reasons like "Go", "Tax".
            const { player_id, delta, reason } = latestInfo.payload;
            if (reason.toLowerCase().includes('rent')) return; // handled by RENT_PAID usually, or ignore to avoid spam
            if (reason.toLowerCase().includes('buy')) return; // handled by PROPERTY_PURCHASED

            addFloatingText(delta, player_id, reason, latestInfo.event_id);
        }

    }, [events, snapshot?.board]);

    const addFloatingText = (amount: number, playerId: string, reason: string, key: string) => {
        setFloatingTexts(prev => [...prev, { type: 'CASH', amount, playerId, reason, key }]);
        // Auto remove floating text after animation
        setTimeout(() => {
            setFloatingTexts(prev => prev.filter(item => (item as any).key !== key));
        }, 2000);
    };

    // Process Main Queue (Modals/Blocking-ish animations)
    useEffect(() => {
        if (activeItem || queue.length === 0) return;

        const next = queue[0];
        setActiveItem(next);
        setQueue(q => q.slice(1));

        // Auto dismiss durations
        let duration = 2000;
        if (next.type === 'CARD') duration = 2500;
        if (next.type === 'PROPERTY') duration = 1500;
        if (next.type === 'JAIL') duration = 2000;

        const timer = setTimeout(() => {
            setActiveItem(null);
        }, duration);

        return () => clearTimeout(timer);
    }, [activeItem, queue]);

    // Helper to get Space object
    const getSpace = (index: number) => snapshot?.board?.[index];

    // Helper to get Player coordinates
    const getPlayerCoords = (playerId: string) => {
        const player = snapshot?.players.find(p => p.player_id === playerId);
        if (!player) return { left: '50%', top: '50%' };
        const { x, y } = getCSSPosition(player.position);
        return { left: `${x}%`, top: `${y}%` };
    };

    return (
        <div className="absolute inset-0 pointer-events-none z-50 flex items-center justify-center">
            {/* CARD MODAL */}
            {activeItem?.type === 'CARD' && (
                <div className="pointer-events-auto">
                    <CardModal
                        isOpen={true}
                        deck={activeItem.event.payload.deck_type}
                        card={getCardDetails(activeItem.event.payload.deck_type, activeItem.event.payload.card_id)}
                        onClose={() => setActiveItem(null)}
                    />
                </div>
            )}

            {/* PROPERTY TOAST */}
            {activeItem?.type === 'PROPERTY' && getSpace(activeItem.spaceIndex) && (
                <PropertyToast
                    isVisible={true}
                    space={getSpace(activeItem.spaceIndex)!}
                    method={activeItem.method}
                    price={activeItem.price}
                />
            )}

            {/* JAIL TOAST */}
            <AnimatePresence>
                {activeItem?.type === 'JAIL' && (
                    <motion.div
                        initial={{ opacity: 0, scale: 0.5, rotate: -20 }}
                        animate={{ opacity: 1, scale: 1, rotate: 0 }}
                        exit={{ opacity: 0, scale: 0.5, y: 100 }}
                        className="bg-black text-white border-4 border-neo-red p-4 shadow-neo-lg z-50 rotate-[-5deg]"
                    >
                        <h2 className="text-3xl font-black uppercase text-neo-red stroke-black drop-shadow-sm">GO TO JAIL!</h2>
                        <div className="text-center font-mono text-sm mt-2">{activeItem.event.payload.reason}</div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* FLOATING CASH TEXTS */}
            <AnimatePresence>
                {floatingTexts.map((item) => {
                    if (item.type !== 'CASH') return null;
                    const coords = getPlayerCoords(item.playerId);
                    const isPositive = item.amount > 0;
                    return (
                        <motion.div
                            key={item.key}
                            initial={{ opacity: 0, y: 0, scale: 0.5 }}
                            animate={{ opacity: 1, y: -40, scale: 1 }}
                            exit={{ opacity: 0, y: -60 }}
                            transition={{ duration: 1.5, ease: "easeOut" }}
                            className="absolute z-50 flex flex-col items-center"
                            style={{ left: coords.left, top: coords.top }}
                        >
                            <span className={`font-black text-lg drop-shadow-[2px_2px_0_#FFF] ${isPositive ? 'text-neo-green stroke-black' : 'text-neo-red'}`}
                                style={{ textShadow: '1px 1px 0 #000, -1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000' }}>
                                {isPositive ? '+' : ''}{item.amount}
                            </span>
                            {item.reason && (
                                <span className="bg-black text-white text-[8px] px-1 rounded-sm uppercase font-bold mt-1">
                                    {item.reason}
                                </span>
                            )}
                        </motion.div>
                    );
                })}
            </AnimatePresence>
        </div>
    );
};
