import { useMemo } from 'react';
import type { Space } from '@/net/contracts';
import { Tile } from '@/components/board/Tile';
import { cn } from '@/components/ui/NeoPrimitive';
import { TokenLayer } from '@/components/board/TokenLayer';
import { getGridPosition } from '@/components/board/utils';
import { useGameStore, type StoreState } from '@/state/store';

interface BoardProps {
    spaces: Space[];
    className?: string;
}

export const Board = ({ spaces, className }: BoardProps) => {
    const { deedHighlight, eventHighlight, decisionHighlight } = useGameStore(
        (state: StoreState) => state.ui
    );

    const highlightSets = useMemo(() => {
        return {
            event: new Set(eventHighlight ?? []),
            decision: new Set(decisionHighlight ?? []),
        };
    }, [eventHighlight, decisionHighlight]);

    // Ensure we have 40 spaces
    const safeSpaces = useMemo(() => {
        if (spaces.length === 40) return spaces;
        return Array.from({ length: 40 }).map((_, i) => ({
            index: i,
            kind: 'PROPERTY',
            name: `Space ${i}`,
            group: null,
            price: null,
            owner_id: null,
            mortgaged: false,
            houses: 0,
            hotel: false,
        } as Space));
    }, [spaces]);

    return (
        <div className={cn('relative p-3', className)} data-board-root="true">
            {/* Board Physical Base */}
            <div className="relative w-full h-full bg-[linear-gradient(135deg,#f7f3ea,#f0e8db)] border-[8px] border-black shadow-[16px_16px_0px_0px_rgba(0,0,0,1)] rounded-sm overflow-hidden">
                <div className="absolute inset-2 border-2 border-black/20 pointer-events-none" />
                <div className="absolute inset-0 opacity-10 bg-[radial-gradient(circle_at_20%_20%,#000_1px,transparent_1px)] bg-[length:18px_18px]" />

                {/* The Grid - Tight gaps for printed look */}
                <div className="absolute inset-0 grid grid-cols-11 grid-rows-11 gap-[1px] bg-[#1c1c1c] p-[2px]">
                    {safeSpaces.map((space) => {
                        const { row, col } = getGridPosition(space.index);
                        return (
                            <div
                                key={space.index}
                                style={{
                                    gridRow: row,
                                    gridColumn: col,
                                }}
                                className="relative bg-white"
                            >
                                <Tile
                                    space={space}
                                    highlightSource={
                                        deedHighlight === space.index
                                            ? 'deed'
                                            : highlightSets.decision.has(space.index)
                                                ? 'decision'
                                                : highlightSets.event.has(space.index)
                                                    ? 'event'
                                                    : null
                                    }
                                />
                            </div>
                        );
                    })}

                    {/* Center Board Area */}
                    <div className="row-start-2 row-end-11 col-start-2 col-end-11 bg-[#f8f5ef] flex items-center justify-center flex-col relative overflow-hidden">

                        {/* Subtle Center Texture */}
                        <div className="absolute inset-0 opacity-10 bg-[radial-gradient(circle_at_center,#000_1px,transparent_1px)] bg-[length:16px_16px]" />

                        {/* Branding */}
                        <div className="z-10 transform -rotate-6">
                            <img
                                src="/../logo2.png"
                                alt="Monopoly Bench"
                                className="w-auto h-64 md:h-150 drop-shadow-[4px_4px_0_rgba(0,0,0,0.12)]"
                            />
                        </div>
                    </div>
                </div>

                {/* Token Overlay */}
                <TokenLayer />
            </div>
        </div>
    );
};
