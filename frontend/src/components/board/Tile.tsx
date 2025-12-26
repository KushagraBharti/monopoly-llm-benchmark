import { useMemo } from 'react';
import type { Space } from '../../net/contracts';
import { cn } from '../ui/NeoPrimitive';

interface TileProps {
    space: Space;
    className?: string;
}

const GROUP_COLORS: Record<string, string> = {
    Brown: "var(--color-neo-black)", // Or specific brown if needed, but neo-black is high contrast
    LightBlue: "var(--color-neo-cyan)",
    Pink: "var(--color-neo-pink)",
    Orange: "#ff9f43",
    Red: "#ff6b6b", // Map to neo-pink or red
    Yellow: "var(--color-neo-yellow)",
    Green: "var(--color-neo-green)",
    Blue: "var(--color-neo-blue)",
    Railroad: "black",
    Utility: "#a4b0be",
};

export const Tile = ({ space, className }: TileProps) => {
    const { name, price, group, owner_id, houses, hotel, mortgaged } = space;

    const colorStyle = useMemo(() => {
        if (group && GROUP_COLORS[group]) return { backgroundColor: GROUP_COLORS[group] };
        return { backgroundColor: 'white' };
    }, [group]);

    // Corner Logic
    const isCorner = space.index % 10 === 0;

    if (isCorner) {
        return (
            <div className={cn("relative w-full h-full border-2 border-black bg-white flex items-center justify-center p-2 text-center overflow-hidden", className)}>
                {/* Simplified Corner Visuals */}
                {space.index === 0 && <span className="text-4xl">🏁</span>}
                {space.index === 10 && <span className="text-4xl">👮</span>}
                {space.index === 20 && <span className="text-4xl">🚗</span>}
                {space.index === 30 && <span className="text-4xl flex flex-col items-center"><span className="text-xs">GO TO</span>👮</span>}
                <span className="absolute bottom-1 text-[10px] font-bold">{name}</span>
            </div>
        );
    }

    return (
        <div
            className={cn(
                "relative flex flex-col border-2 border-black bg-neo-bg h-full w-full select-none overflow-hidden transition-colors hover:bg-white group",
                className
            )}
        >
            {/* Color Bar */}
            {group && (
                <div
                    className="h-[25%] min-h-[15px] w-full border-b-2 border-black flex items-center justify-center relative"
                    style={group === 'Railroad' || group === 'Utility' ? { backgroundColor: 'white' } : colorStyle}
                >
                    {/* Railroad/Utility Icon placeholders */}
                    {group === 'Railroad' && <span className="text-lg">🚂</span>}
                    {group === 'Utility' && <span className="text-lg">💡</span>}

                    {/* Houses/Hotels Overlay */}
                    <div className="flex gap-0.5 absolute bottom-0.5">
                        {hotel && <div className="w-3 h-3 bg-red-600 border border-black rotate-45" />}
                        {!hotel && Array.from({ length: houses }).map((_, i) => (
                            <div key={i} className="w-2 h-2 bg-neo-green border border-black rounded-full" />
                        ))}
                    </div>
                </div>
            )}

            {/* Content */}
            <div className="flex-1 flex flex-col items-center justify-between p-1 text-center w-full">
                <span className="text-[9px] md:text-[10px] mobile:text-[8px] font-bold leading-tight uppercase line-clamp-2">{name}</span>

                {/* Price Tag (hidden on small screens if needed, but vital for monopoly) */}
                {price !== null && (
                    <span className="text-[9px] font-mono opacity-80 mb-0.5">${price}</span>
                )}
            </div>

            {/* Owner Indicator Overlay */}
            {owner_id && (
                <div className="absolute inset-x-0 bottom-0 h-2 bg-black flex items-center justify-center" title={`Owned by ${owner_id}`}>
                    {/* Optional Small owner initial if needed */}
                </div>
            )}

            {/* Mortgage Overlay */}
            {mortgaged && (
                <div className="absolute inset-0 bg-black/80 flex items-center justify-center z-10 backdrop-blur-[1px]">
                    <span className="text-neo-pink font-black text-[10px] uppercase border border-neo-pink px-1 -rotate-45">Mortgaged</span>
                </div>
            )}
        </div>
    );
};
