import { useGameStore } from '../../state/store';
import { getPlayerColor, getGroupColor } from '../board/constants';
import { cn, NeoCard } from '../ui/NeoPrimitive';

export const OwnershipPanel = () => {
    const snapshot = useGameStore((state) => state.snapshot);
    const board = snapshot?.board || [];

    // Use normalized group names (match backend format)
    const propertyGroups = ["BROWN", "LIGHT_BLUE", "PINK", "ORANGE", "RED", "YELLOW", "GREEN", "DARK_BLUE"];
    const specialGroups = ["RAILROAD", "UTILITY"];

    // Helper to get tiles for a group (case-insensitive matching)
    const getTiles = (groupName: string) => board.filter(t =>
        t.group?.toUpperCase().replace(/\s+/g, '_') === groupName
    );

    // Mini Tile Component
    const MiniTile = ({ tile }: { tile: any }) => {
        const ownerColor = tile.owner_id ? getPlayerColor(tile.owner_id) : null;

        return (
            <div
                className={cn(
                    "flex flex-col border border-black h-12 w-10 text-[8px] text-center bg-white relative transition-transform hover:scale-110 cursor-pointer",
                    tile.mortgaged && "opacity-50 grayscale"
                )}
                title={`${tile.name} ${tile.owner_id ? `(Owned by ${tile.owner_id})` : ''}`}
            >
                {/* Header - use getGroupColor for normalized lookup */}
                <div
                    className="h-3 w-full border-b border-black"
                    style={{ backgroundColor: getGroupColor(tile.group) }}
                />

                {/* Body */}
                <div className="flex-1 flex flex-col justify-center items-center leading-none p-0.5 relative">
                    <span className="truncate w-full">{tile.name.substring(0, 6)}..</span>

                    {/* Visual Indicators */}
                    <div className="flex gap-0.5 mt-1">
                        {tile.hotel && <div className="w-1.5 h-1.5 bg-red-600 border border-black" />}
                        {!tile.hotel && Array.from({ length: tile.houses }).map((_, i) => (
                            <div key={i} className="w-1 h-1 bg-green-500 border border-black rounded-full" />
                        ))}
                    </div>

                    {tile.mortgaged && (
                        <div className="absolute inset-0 flex items-center justify-center">
                            <span className="text-red-600 font-bold -rotate-45 opacity-80 text-[8px]">M</span>
                        </div>
                    )}
                </div>

                {/* Owner Footer */}
                {ownerColor && (
                    <div className="h-2 w-full border-t border-black" style={{ backgroundColor: ownerColor }} />
                )}
            </div>
        );
    };

    if (!snapshot) return null;

    return (
        <NeoCard className="flex flex-col gap-2 p-2 max-h-full overflow-y-auto">
            <h3 className="text-xs font-bold uppercase border-b-2 border-black pb-1 mb-1">Property Deeds</h3>

            {/* Standard Property Groups */}
            <div className="space-y-2">
                {propertyGroups.map((group: string) => {
                    const tiles = getTiles(group);
                    if (tiles.length === 0) return null;
                    return (
                        <div key={group} className="flex gap-1 justify-center">
                            {tiles.map(tile => <MiniTile key={tile.index} tile={tile} />)}
                        </div>
                    );
                })}
            </div>

            <div className="h-px bg-black/20 my-1" />

            {/* Special Groups (Railroads & Utilities) */}
            <div className="flex flex-wrap gap-2 justify-center">
                {specialGroups.map((group: string) => {
                    const tiles = getTiles(group);
                    if (tiles.length === 0) return null;
                    return (
                        <div key={group} className="flex gap-1">
                            {tiles.map(tile => <MiniTile key={tile.index} tile={tile} />)}
                        </div>
                    );
                })}
            </div>
        </NeoCard>
    );
};
