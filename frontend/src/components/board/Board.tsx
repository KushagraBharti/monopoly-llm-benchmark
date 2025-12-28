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
        <div className={cn("relative p-2", className)}>
            {/* Board Physical Base */}
            <div className="relative w-full h-full bg-neo-bg border-[6px] border-black shadow-[12px_12px_0px_0px_rgba(0,0,0,1)] rounded-sm overflow-hidden">

                {/* The Grid - Tight gaps for printed look */}
                <div className="absolute inset-0 grid grid-cols-11 grid-rows-11 gap-[1px] bg-black p-[2px]">
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
                    <div className="row-start-2 row-end-11 col-start-2 col-end-11 bg-neo-bg flex items-center justify-center flex-col relative overflow-hidden">

                        {/* Subtle Center Texture */}
                        <div className="absolute inset-0 opacity-10 bg-[radial-gradient(circle_at_center,_var(--color-neo-black)_1px,_transparent_1px)] bg-[length:16px_16px]" />

                        {/* Branding */}
                        <div className="z-10 transform -rotate-6">
                            <h1 className="text-4xl md:text-7xl font-black uppercase text-center tracking-tighter leading-[0.85] drop-shadow-[4px_4px_0_rgba(0,0,0,0.1)]">
                                MONOPOLY<br />
                                <span className="text-neo-pink text-5xl md:text-8xl block mt-2">ARENA</span>
                            </h1>
                            <div className="w-full h-1 bg-black mt-4 mb-2" />
                        </div>
                    </div>
                </div>

                {/* Token Overlay */}
                <TokenLayer />
            </div>
        </div>
    );
};
