import { useMemo } from 'react';
import type { Space } from '../../net/contracts';
import { cn } from '../ui/NeoPrimitive';
import { GROUP_COLORS, getPlayerColor } from './constants';

interface TileProps {
    space: Space;
    className?: string;
}

export const Tile = ({ space, className }: TileProps) => {
    const { name, price, group, owner_id, houses, hotel, mortgaged } = space;

    const groupColor = useMemo(() => {
        if (group && GROUP_COLORS[group]) return GROUP_COLORS[group];
        // Fallback for utilities/railroads if not in map, though they should be
        if (group === 'Railroad') return GROUP_COLORS['Railroad'];
        if (group === 'Utility') return GROUP_COLORS['Utility'];
        return 'white';
    }, [group]);

    const ownerColor = useMemo(() => {
        if (!owner_id) return null;
        return getPlayerColor(owner_id);
    }, [owner_id]);

    // Corner Logic
    const isCorner = space.index % 10 === 0;

    if (isCorner) {
        return (
            <div className={cn("relative w-full h-full border-2 border-black bg-white flex flex-col items-center justify-center p-1 text-center overflow-hidden", className)}>
                {space.index === 0 && (
                    <>
                        <span className="text-4xl leading-none">🏁</span>
                        <span className="font-black text-xs mt-1">GO</span>
                        <span className="text-[9px] font-mono">Collect $200</span>
                    </>
                )}
                {space.index === 10 && (
                    <>
                        <div className="absolute inset-0 bg-orange-100/50 -z-10" />
                        <span className="text-3xl">👮</span>
                        <span className="font-black text-[10px] mt-1 bg-black text-white px-1">JAIL</span>
                    </>
                )}
                {space.index === 20 && (
                    <>
                        <span className="text-3xl">🚗</span>
                        <span className="font-bold text-[10px] leading-tight mt-1">FREE<br />PARKING</span>
                    </>
                )}
                {space.index === 30 && (
                    <>
                        <span className="text-3xl">👉</span>
                        <span className="font-black text-[10px] mt-1">GO TO JAIL</span>
                    </>
                )}
            </div>
        );
    }

    return (
        <div
            className={cn(
                "relative flex flex-col border-2 border-black bg-neo-bg h-full w-full select-none overflow-hidden transition-all hover:scale-[1.02] hover:shadow-lg group",
                className
            )}
        >
            {/* Color Band */}
            {group && (
                <div
                    className="h-[28%] w-full border-b-2 border-black flex items-center justify-center relative"
                    style={{ backgroundColor: groupColor }}
                >
                    {/* Icons for non-color properties */}
                    {group === 'Railroad' && <span className="text-white drop-shadow-md text-lg">🚂</span>}
                    {group === 'Utility' && <span className="text-white drop-shadow-md text-lg">💡</span>}

                    {/* Buildings Container */}
                    <div className="absolute -bottom-1.5 flex gap-0.5 justify-center w-full px-0.5">
                        {hotel && (
                            <div className="w-5 h-4 bg-red-600 border-2 border-black shadow-[1px_1px_0px_0px_rgba(0,0,0,1)] z-10" title="Hotel" />
                        )}
                        {!hotel && Array.from({ length: houses }).map((_, i) => (
                            <div key={i} className="w-3 h-3 bg-neo-green border-2 border-black shadow-[1px_1px_0px_0px_rgba(0,0,0,1)] z-10" title="House" />
                        ))}
                    </div>
                </div>
            )}

            {/* Content Body */}
            <div className="flex-1 flex flex-col items-center justify-start pt-2 px-0.5 text-center w-full bg-white relative">

                {/* Name */}
                <span className="text-[9px] md:text-[10px] font-bold leading-none uppercase tracking-tight mb-1">
                    {name}
                </span>

                {/* Price (if not owned) */}
                {!owner_id && price !== null && (
                    <span className="mt-auto mb-1 text-[9px] font-mono text-gray-500">${price}</span>
                )}
            </div>

            {/* Owner Strip (Always visible if owned) */}
            {owner_id && (
                <div
                    className="h-3 w-full border-t-2 border-black flex items-center justify-center relative"
                    style={{ backgroundColor: ownerColor || 'black' }}
                    title={`Owned by ${owner_id}`}
                >
                    {/* Maybe a small icon or just color block */}
                    {/* <span className="text-[8px] text-white font-mono opacity-80">{owner_id.split('_')[1] || owner_id}</span> */}
                </div>
            )}

            {/* Mortgage Overlay (Full Tile) */}
            {mortgaged && (
                <div className="absolute inset-0 bg-white/60 backdrop-blur-[1px] flex items-center justify-center z-20">
                    <div className="border-4 border-red-600/80 p-1 transform -rotate-45">
                        <span className="text-red-600/90 font-black text-[12px] md:text-sm uppercase tracking-widest whitespace-nowrap">
                            MORTGAGED
                        </span>
                    </div>
                </div>
            )}
        </div>
    );
};
