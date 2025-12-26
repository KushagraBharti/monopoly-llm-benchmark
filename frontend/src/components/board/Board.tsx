import { useMemo } from 'react';
import type { Space } from '../../net/contracts';
import { Tile } from './Tile';
import { cn } from '../ui/NeoPrimitive';
import { TokenLayer } from './TokenLayer';
import { getGridPosition } from './utils';

interface BoardProps {
    spaces: Space[];
    className?: string;
}

// Map logical index to Grid position (row, col)
// 11x11 Grid logic moved to utils.ts

export const Board = ({ spaces, className }: BoardProps) => {
    // Ensure we have 40 spaces to prevent sync errors, though snapshot should guarantee it.
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
        <div className={cn("relative", className)}>
            {/* Aspect Ratio Container */}
            <div className="relative w-full h-full bg-neo-bg border-4 border-black shadow-neo-lg">

                {/* The Grid */}
                <div className="absolute inset-0 grid grid-cols-11 grid-rows-11 gap-0.5 bg-black p-0.5">
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
                                <Tile space={space} />
                            </div>
                        );
                    })}

                    {/* Center Logo Area */}
                    <div className="row-start-2 row-end-11 col-start-2 col-end-11 bg-neo-bg flex items-center justify-center flex-col p-8 border-2 border-black m-0.5">
                        <h1 className="text-4xl md:text-6xl font-black uppercase text-center tracking-tighter rotate-[-15deg] text-black drop-shadow-[4px_4px_0_rgba(0,0,0,0.2)]">
                            Monopoly<br />
                            <span className="text-neo-pink">Arena</span>
                        </h1>
                        <div className="mt-8 font-mono text-xs md:text-sm text-center opacity-60">
                            REAL-TIME LLM BENCHMARK
                        </div>
                    </div>
                </div>

                {/* Token Layer (Absolute Overlay) */}
                <TokenLayer />
            </div>
        </div>
    );
};
