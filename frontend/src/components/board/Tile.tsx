import { memo, useMemo } from 'react';
import type { Space } from '@/net/contracts';
import { cn } from '@/components/ui/NeoPrimitive';
import { getGroupColor, getPlayerColor } from '@/domain/monopoly/colors';

interface TileProps {
  space: Space;
  className?: string;
  highlightSource?: 'deed' | 'event' | 'decision' | null;
}

// Brutal SVG Icons
const TrainIcon = () => (
  <div className="w-8 h-8 border-2 border-black rounded-full flex items-center justify-center bg-black text-white">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="w-5 h-5">
      <path d="M3 11h18M5 11V7a2 2 0 012-2h10a2 2 0 012 2v4M4 11l-1 9h18l-1-9m-4 5a2 2 0 11-4 0 2 2 0 014 0z" />
    </svg>
  </div>
);

const BulbIcon = () => (
  <div className="w-8 h-8 border-2 border-black rounded-full flex items-center justify-center bg-neo-yellow text-black shadow-neo-sm">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="w-5 h-5">
      <path d="M9 18h6m-5 4h4m-.9-22a5 5 0 014.9 6c0 1.9-1.3 3.4-3 4.1V15a1 1 0 01-1 1h-2a1 1 0 01-1-1v-4.9c-1.7-.7-3-2.2-3-4.1a5 5 0 015-6z" />
    </svg>
  </div>
);

const WaterIcon = () => (
  <div className="w-8 h-8 border-2 border-black rounded-full flex items-center justify-center bg-neo-cyan text-black shadow-neo-sm">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="w-5 h-5">
      <path d="M12 2c0 4-4 7-4 12a4 4 0 008 0c0-5-4-8-4-12z" />
    </svg>
  </div>
);

const ChestIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="w-8 h-8 text-black opacity-80 rotate-[-5deg]">
    <rect x="2" y="6" width="20" height="14" rx="2" />
    <path d="M12 6v14M2 10h20" />
  </svg>
);

const ChanceIcon = () => (
  <span className="font-serif font-black text-4xl text-neo-pink leading-none opacity-90 drop-shadow-md">?</span>
);

const TaxIcon = () => (
  <div className="font-black text-xl border-2 border-black w-8 h-8 flex items-center justify-center bg-gray-200 rounded-sm">
    $
  </div>
);

export const Tile = memo(({ space, className, highlightSource = null }: TileProps) => {
  const { name, kind, price, group, owner_id, houses, hotel, mortgaged } = space;

  const groupColor = useMemo(() => getGroupColor(group), [group]);
  const hasColorBand = !!group && groupColor !== 'transparent';

  const groupUpper = group?.toUpperCase() || '';
  const isRailroad = kind === 'RAILROAD' || groupUpper === 'RAILROAD';
  const isUtility = kind === 'UTILITY' || groupUpper === 'UTILITY';
  const isChest = name.toUpperCase().includes('CHEST');
  const isChance = name.toUpperCase().includes('CHANCE');
  const isTax = name.toUpperCase().includes('TAX');

  const ownerColor = useMemo(() => {
    if (!owner_id) return null;
    return getPlayerColor(owner_id);
  }, [owner_id]);

  const highlightClass = highlightSource
    ? highlightSource === 'event'
      ? 'ring-4 ring-neo-yellow animate-pulse z-40'
      : highlightSource === 'deed'
        ? 'ring-4 ring-neo-pink z-30 scale-[1.05]'
        : 'ring-4 ring-neo-cyan border-dashed z-30'
    : '';

  // Corner Tiles (Square layout handled by parent Grid generally, but content here)
  if (space.index % 10 === 0) {
    return (
      <div
        className={cn(
          "relative w-full h-full border-2 border-neo-border bg-white flex flex-col items-center justify-center text-center select-none overflow-hidden",
          highlightClass,
          className
        )}
      >
        {space.index === 0 && ( /* GO */
          <div className="w-full h-full bg-[#CEE6D0] relative flex items-center justify-center">
            <span className="absolute top-1 left-1 text-[8px] font-black transform -rotate-45 opacity-50">COLLECT<br />$200</span>
            <span className="text-4xl font-black text-neo-black tracking-tighter drop-shadow-md transform -rotate-45">GO</span>
            <div className="absolute bottom-0 right-0 w-8 h-8 border-l-2 border-t-2 border-black bg-neo-green">
              <svg viewBox="0 0 24 24" stroke="currentColor" className="w-full h-full p-1 text-white" strokeWidth="3"><path d="M5 12h14m-7-7l7 7-7 7" /></svg>
            </div>
          </div>
        )}
        {space.index === 10 && ( /* JAIL */
          <div className="w-full h-full bg-[#F3D2C1] p-1 flex relative">
            <div className="w-2/3 h-full border-2 border-black bg-neo-orange flex items-center justify-center relative shadow-sm">
              <div className="absolute inset-0 bg-[repeating-linear-gradient(90deg,transparent,transparent_4px,black_4px,black_6px)] opacity-30"></div>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="bg-white border text-[8px] font-bold px-1 rotate-[-15deg]">IN JAIL</span>
              </div>
            </div>
            <div className="flex-1 flex items-center justify-center">
              <span className="text-[9px] font-bold text-center leading-none transform -rotate-90 whitespace-nowrap">JUST<br />VISITING</span>
            </div>
          </div>
        )}
        {space.index === 20 && ( /* FREE PARKING */
          <div className="w-full h-full bg-[#FDFD96] flex flex-col items-center justify-center p-1 relative">
            <div className="absolute top-1 rotate-12 bg-neo-red text-white text-[8px] font-black px-1 border border-black shadow-sm">FREE</div>
            <div className="mt-2 text-3xl font-black">🚗</div>
            <span className="text-[9px] font-bold uppercase mt-1">Parking</span>
          </div>
        )}
        {space.index === 30 && ( /* GO TO JAIL */
          <div className="w-full h-full bg-[#AEC6CFA0] flex flex-col items-center justify-center p-1 relative">
            <span className="text-[9px] font-bold uppercase mb-1">GO TO</span>
            <div className="w-10 h-10 border-2 border-black bg-neo-blue flex items-center justify-center shadow-neo-sm relative">
              <span className="text-2xl">👮</span>
            </div>
            <span className="text-[9px] font-bold uppercase mt-1">JAIL</span>
          </div>
        )}
      </div>
    );
  }

  // Regular Tiles
  return (
    <div
      className={cn(
        'relative flex flex-col border-[1.5px] border-neo-border bg-white h-full w-full select-none overflow-hidden hover:z-20 transition-transform duration-100',
        highlightClass,
        className
      )}
    >
      {/* Header Band */}
      {hasColorBand ? (
        <div
          className="h-[22%] w-full border-b-[1.5px] border-black relative transition-all"
          style={{ backgroundColor: groupColor }}
        >
          {/* Housing Indicators */}
          <div className="absolute -bottom-1.5 inset-x-0 flex justify-center gap-0.5 z-10">
            {hotel && (
              <div className="w-6 h-4 bg-neo-red border border-black shadow-[1px_1px_0_0_#000]" title="Hotel" />
            )}
            {!hotel && Array.from({ length: houses }).map((_, i) => (
              <div key={i} className="w-3 h-3 bg-neo-green border border-black shadow-[1px_1px_0_0_#000]" title="House" />
            ))}
          </div>
        </div>
      ) : (
        // Spacer for non-colored props to keep alignment roughly similar? 
        // Actually keep layout distinct for utilities/railroads
        <div className="h-[10%]" />
      )}

      {/* Content Body */}
      <div className="flex-1 flex flex-col items-center p-1 text-center w-full relative z-0">

        {/* Name */}
        <span className="text-[8px] font-bold uppercase leading-tight tracking-tight line-clamp-3 mb-1 min-h-[2.2em]">
          {name}
        </span>

        {/* Icon / Central Graphic */}
        <div className="flex-1 flex items-center justify-center">
          {isRailroad && <TrainIcon />}
          {isUtility && name.toLowerCase().includes('water') && <WaterIcon />}
          {isUtility && name.toLowerCase().includes('electric') && <BulbIcon />}
          {isChest && <ChestIcon />}
          {isChance && <ChanceIcon />}
          {isTax && <TaxIcon />}
        </div>

        {/* Price */}
        {!owner_id && price !== null && (
          <span className="text-[9px] font-mono mt-auto pt-1">{`$${price}`}</span>
        )}
      </div>

      {/* Owner Strip */}
      {owner_id && (
        <div
          className="h-[4px] w-full border-t border-black absolute bottom-0 left-0"
          style={{ backgroundColor: ownerColor || 'black' }}
        />
      )}

      {/* Mortgaged Overlay */}
      {mortgaged && (
        <div className="absolute inset-0 bg-white/80 flex items-center justify-center z-20">
          <span className="font-black text-[10px] text-neo-red border-2 border-neo-red px-1 transform -rotate-12 bg-white">
            MORTGAGED
          </span>
        </div>
      )}
    </div>
  );
});

Tile.displayName = 'Tile';
