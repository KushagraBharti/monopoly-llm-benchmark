/* eslint-disable react-hooks/set-state-in-effect */
import { useCallback, useEffect, useRef, useState } from 'react';
import { useGameStore } from '@/state/store';
import { CardModal } from '@/components/board/CardModal';
import { PropertyToast } from '@/components/board/PropertyToast';
import { getCardDetails } from '@/domain/monopoly/cardData';
import type { Event } from '@/net/contracts';
import { AnimatePresence, motion } from 'framer-motion';
import { getCSSPosition } from './utils';
import { SPACE_INDEX_BY_KEY, normalizeSpaceKey } from '@/domain/monopoly/constants';

const CASH_TOAST_DURATION_MS = 1600;
const CASH_TOAST_COOLDOWN_MS = 800;

const resolveSpaceIndex = (value: string, board: { index: number; name: string }[]): number | null => {
    const normalized = normalizeSpaceKey(value);
    if (SPACE_INDEX_BY_KEY[normalized] !== undefined) {
        return SPACE_INDEX_BY_KEY[normalized];
    }
    const match = board.find((space) => normalizeSpaceKey(space.name) === normalized);
    return match ? match.index : null;
};

type PropertyMethod = 'BOUGHT' | 'WON' | 'TRADED';

type AnimationItem =
    | { type: 'CARD'; event: Event & { type: 'CARD_DRAWN' }; originOffset: { x: number; y: number } }
    | {
          type: 'PROPERTY';
          eventId: string;
          spaceIndex: number;
          method: PropertyMethod;
          price?: number;
          playerId?: string | null;
          start: { x: number; y: number };
          target?: { x: number; y: number } | null;
      }
    | { type: 'JAIL'; event: Event & { type: 'SENT_TO_JAIL' } };

type CashToast = {
    key: string;
    amount: number;
    playerId: string;
    reason?: string;
    origin: { x: number; y: number };
};

export const BoardEffectsLayer = () => {
    const events = useGameStore((state) => state.events);
    const snapshot = useGameStore((state) => state.snapshot);
    const runId = useGameStore((state) => state.runStatus.runId);
    const logResetId = useGameStore((state) => state.logResetId);
    const [queue, setQueue] = useState<AnimationItem[]>([]);
    const [cashToasts, setCashToasts] = useState<CashToast[]>([]);
    const [activeItem, setActiveItem] = useState<AnimationItem | null>(null);
    const processedEventIds = useRef<Set<string>>(new Set());
    const lastCashTsByPlayer = useRef<Map<string, number>>(new Map());
    const hasHydrated = useRef(false);
    const activeItemRef = useRef<AnimationItem | null>(null);
    const lastTurnIndexRef = useRef<number | null>(null);

    useEffect(() => {
        processedEventIds.current.clear();
        lastCashTsByPlayer.current.clear();
        hasHydrated.current = false;
        setQueue([]);
        setCashToasts([]);
        setActiveItem(null);
    }, [logResetId, snapshot?.run_id, runId]);

    useEffect(() => {
        activeItemRef.current = activeItem;
    }, [activeItem]);

    useEffect(() => {
        const currentTurn = snapshot?.turn_index ?? null;
        if (
            currentTurn !== null &&
            lastTurnIndexRef.current !== null &&
            currentTurn < lastTurnIndexRef.current
        ) {
            processedEventIds.current.clear();
            lastCashTsByPlayer.current.clear();
            hasHydrated.current = false;
            setQueue([]);
            setCashToasts([]);
            setActiveItem(null);
        }
        lastTurnIndexRef.current = currentTurn;
    }, [snapshot?.turn_index]);

    useEffect(() => {
        if (events.length === 0 && processedEventIds.current.size) {
            processedEventIds.current.clear();
            lastCashTsByPlayer.current.clear();
            hasHydrated.current = false;
            setQueue([]);
            setCashToasts([]);
            setActiveItem(null);
        }
    }, [events.length]);

    const getBoardRect = useCallback(() => {
        const el = document.querySelector('[data-board-root="true"]') as HTMLElement | null;
        return el ? el.getBoundingClientRect() : null;
    }, []);

    const getBoardCenter = useCallback(() => {
        const rect = getBoardRect();
        if (!rect) {
            return { x: window.innerWidth / 2, y: window.innerHeight / 2 };
        }
        return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
    }, [getBoardRect]);

    const getBoardPoint = useCallback((spaceIndex: number): { x: number; y: number } => {
        const boardRect = getBoardRect();
        if (!boardRect) {
            return { x: window.innerWidth / 2, y: window.innerHeight / 2 };
        }
        const { x, y } = getCSSPosition(spaceIndex);
        return {
            x: boardRect.left + (x / 100) * boardRect.width,
            y: boardRect.top + (y / 100) * boardRect.height,
        };
    }, [getBoardRect]);

    const getPlayerAnchor = useCallback((playerId: string | null | undefined): { x: number; y: number } | null => {
        if (!playerId) return null;
        const el = document.querySelector(`[data-player-card-id="${playerId}"]`) as HTMLElement | null;
        if (!el) return null;
        const rect = el.getBoundingClientRect();
        return {
            x: rect.left + rect.width * 0.5,
            y: rect.top + rect.height * 0.45,
        };
    }, []);

    const getPlayerPosition = useCallback((playerId: string | null | undefined): number | null => {
        if (!playerId) return null;
        const player = snapshot?.players.find((entry) => entry.player_id === playerId);
        return player?.position ?? null;
    }, [snapshot]);

    const addCashToast = (payload: CashToast) => {
        setCashToasts((prev) => [...prev, payload]);
        window.setTimeout(() => {
            setCashToasts((prev) => prev.filter((item) => item.key !== payload.key));
        }, CASH_TOAST_DURATION_MS);
    };

    useEffect(() => {
        if (!events.length) return;

        const activeRunId = snapshot?.run_id ?? runId ?? null;
        if (!activeRunId) {
            return;
        }
        if (!hasHydrated.current) {
            for (const event of events) {
                if (event?.event_id) {
                    processedEventIds.current.add(event.event_id);
                }
            }
            hasHydrated.current = true;
            return;
        }
        const board = snapshot?.board ?? [];
        const newItems: AnimationItem[] = [];

        for (let i = events.length - 1; i >= 0; i -= 1) {
            const event = events[i];
            if (!event || processedEventIds.current.has(event.event_id)) continue;
            if (activeRunId && event.run_id !== activeRunId) {
                continue;
            }
            processedEventIds.current.add(event.event_id);

            if (event.type === 'CARD_DRAWN') {
                const origin = getBoardCenter();
                const offset = { x: origin.x - window.innerWidth / 2, y: origin.y - window.innerHeight / 2 };
                newItems.push({ type: 'CARD', event, originOffset: offset });
                continue;
            }

            if (event.type === 'PROPERTY_PURCHASED') {
                const start = getBoardCenter();
                const target = getPlayerAnchor(event.payload.player_id);
                newItems.push({
                    type: 'PROPERTY',
                    eventId: event.event_id,
                    spaceIndex: event.payload.space_index,
                    method: 'BOUGHT',
                    price: event.payload.price,
                    playerId: event.payload.player_id,
                    start,
                    target,
                });
                continue;
            }

            if (event.type === 'PROPERTY_TRANSFERRED' && event.payload.to_player_id) {
                const start = getBoardCenter();
                const target = getPlayerAnchor(event.payload.to_player_id);
                newItems.push({
                    type: 'PROPERTY',
                    eventId: event.event_id,
                    spaceIndex: event.payload.space_index,
                    method: 'TRADED',
                    playerId: event.payload.to_player_id,
                    start,
                    target,
                });
                continue;
            }

            if (event.type === 'AUCTION_ENDED' && event.payload.winner_player_id) {
                const resolvedIndex = resolveSpaceIndex(event.payload.property_space, board);
                if (resolvedIndex !== null) {
                    const start = getBoardCenter();
                    const target = getPlayerAnchor(event.payload.winner_player_id);
                    newItems.push({
                        type: 'PROPERTY',
                        eventId: event.event_id,
                        spaceIndex: resolvedIndex,
                        method: 'WON',
                        price: event.payload.winning_bid ?? 0,
                        playerId: event.payload.winner_player_id,
                        start,
                        target,
                    });
                }
                continue;
            }

            if (event.type === 'SENT_TO_JAIL') {
                newItems.push({ type: 'JAIL', event });
                continue;
            }

            if (event.type === 'RENT_PAID') {
                const timestamp = event.ts_ms ?? Date.now();
                const fromPos = getPlayerPosition(event.payload.from_player_id);
                const toPos = getPlayerPosition(event.payload.to_player_id);
                if (fromPos !== null) {
                    addCashToast({
                        key: `${event.event_id}-rent-out`,
                        amount: -event.payload.amount,
                        playerId: event.payload.from_player_id,
                        reason: 'Rent Paid',
                        origin: getBoardPoint(fromPos),
                    });
                    lastCashTsByPlayer.current.set(event.payload.from_player_id, timestamp);
                }
                if (toPos !== null) {
                    addCashToast({
                        key: `${event.event_id}-rent-in`,
                        amount: event.payload.amount,
                        playerId: event.payload.to_player_id,
                        reason: 'Rent Received',
                        origin: getBoardPoint(toPos),
                    });
                    lastCashTsByPlayer.current.set(event.payload.to_player_id, timestamp);
                }
                continue;
            }

            if (event.type === 'CASH_CHANGED') {
                const timestamp = event.ts_ms ?? Date.now();
                const lastTs = lastCashTsByPlayer.current.get(event.payload.player_id) ?? 0;
                const delta = event.payload.delta;
                const reason = event.payload.reason;
                const shouldShow =
                    Math.abs(delta) >= 20 || timestamp - lastTs >= CASH_TOAST_COOLDOWN_MS;
                if (!shouldShow) continue;
                if (reason.toLowerCase().includes('rent')) continue;
                if (reason.toLowerCase().includes('buy')) continue;
                const position = getPlayerPosition(event.payload.player_id);
                if (position !== null) {
                    addCashToast({
                        key: `${event.event_id}-cash`,
                        amount: delta,
                        playerId: event.payload.player_id,
                        reason,
                        origin: getBoardPoint(position),
                    });
                    lastCashTsByPlayer.current.set(event.payload.player_id, timestamp);
                }
            }
        }

        if (newItems.length) {
            setQueue((prev) => [...prev, ...newItems]);
        }
    }, [events, snapshot, runId, getBoardCenter, getBoardPoint, getPlayerPosition, getPlayerAnchor]);

    useEffect(() => {
        if (activeItem || queue.length === 0) return;
        const next = queue[0];
        setActiveItem(next);
        setQueue((prev) => prev.slice(1));
    }, [activeItem, queue]);

    useEffect(() => {
        if (!activeItem) return;
        if (activeItem.type === 'PROPERTY') return;
        let duration = 1900;
        if (activeItem.type === 'CARD') duration = 2300;
        if (activeItem.type === 'JAIL') duration = 1800;

        const timer = window.setTimeout(() => {
            setActiveItem(null);
        }, duration);

        return () => window.clearTimeout(timer);
    }, [activeItem]);

    const getSpace = (index: number) => snapshot?.board?.[index];

    return (
        <div className="fixed inset-0 pointer-events-none z-50">
            {activeItem?.type === 'CARD' && (
                <div className="pointer-events-auto">
                    <CardModal
                        isOpen={true}
                        deck={activeItem.event.payload.deck_type}
                        card={getCardDetails(activeItem.event.payload.deck_type, activeItem.event.payload.card_id)}
                        originOffset={activeItem.originOffset}
                        onClose={() => setActiveItem(null)}
                    />
                </div>
            )}

            {activeItem?.type === 'PROPERTY' && getSpace(activeItem.spaceIndex) && (
                <PropertyToast
                    key={activeItem.eventId}
                    isVisible={true}
                    space={getSpace(activeItem.spaceIndex)!}
                    method={activeItem.method}
                    price={activeItem.price}
                    start={activeItem.start}
                    target={activeItem.target}
                    onComplete={() => {
                        const current = activeItemRef.current;
                        if (current?.type === 'PROPERTY' && current.eventId === activeItem.eventId) {
                            setActiveItem(null);
                        }
                    }}
                />
            )}

            <AnimatePresence>
                {activeItem?.type === 'JAIL' && (
                    <motion.div
                        initial={{ opacity: 0, scale: 0.8, y: 40 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, y: 40 }}
                        className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-black text-white border-4 border-neo-red p-4 shadow-neo-lg z-[70]"
                    >
                        <div className="text-[18px] font-black uppercase text-neo-red tracking-tight">Sent to Jail</div>
                        <div className="text-center font-mono text-[11px] mt-2">
                            {activeItem.event.payload.reason || 'Jail'}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            <AnimatePresence>
                {cashToasts.map((item) => {
                    const isPositive = item.amount > 0;
                    return (
                        <motion.div
                            key={item.key}
                            initial={{ opacity: 0, y: 6, scale: 0.9 }}
                            animate={{ opacity: 1, y: -24, scale: 1 }}
                            exit={{ opacity: 0, y: -32 }}
                            transition={{ duration: 1.2, ease: 'easeOut' }}
                            className="fixed z-[60] flex flex-col items-center"
                            style={{ left: item.origin.x, top: item.origin.y }}
                        >
                            <span
                                className={`font-black text-[14px] drop-shadow-[1px_1px_0_#FFF] ${isPositive ? 'text-neo-green' : 'text-neo-red'}`}
                                style={{ textShadow: '1px 1px 0 #000, -1px -1px 0 #000' }}
                            >
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
