import { memo, useMemo } from 'react';
import type { Space } from '@/net/contracts';
import { cn } from '@/components/ui/cn';
import { getGroupColor, getPlayerColor } from '@/domain/monopoly/colors';

interface TileProps {
  space: Space;
  className?: string;
  highlightSource?: 'deed' | 'event' | 'decision' | null;
}

const TrainIcon = () => (
  <div className="w-8 h-8 flex items-center justify-center bg-black text-white rounded-sm shadow-neo-sm transform -rotate-3">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
      <path d="M3 11h18M5 11V7a2 2 0 012-2h10a2 2 0 012 2v4M4 11l-1 9h18l-1-9m-4 5a2 2 0 11-4 0 2 2 0 014 0z" />
      <circle cx="6" cy="18" r="2" fill="white" stroke="none" />
      <circle cx="18" cy="18" r="2" fill="white" stroke="none" />
    </svg>
  </div>
);

const BulbIcon = () => (
  <div className="w-8 h-8 flex items-center justify-center bg-neo-yellow text-black border-2 border-black rounded-full shadow-[2px_2px_0_0_rgba(0,0,0,1)]">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="w-5 h-5">
      <path d="M9.5 9h5m-5 3h5m-6.9 8a5 5 0 014.9-6 5 5 0 014.9 6h-9.8z" />
      <path d="M12 3a6 6 0 00-6 6v7h12V9a6 6 0 00-6-6z" />
    </svg>
  </div>
);

const WaterIcon = () => (
  <div className="w-8 h-8 flex items-center justify-center bg-neo-cyan text-black border-2 border-black rounded-full shadow-[2px_2px_0_0_rgba(0,0,0,1)]">
    <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
      <path d="M12 2.6L12 2.6c-.1 0-.1.1-.2.1 0 .1-.2.2-.2.3l-1.3 2.1c-.8 1.4-1.9 2.6-2.5 3.9-.7 1.4-1.1 3-1.1 4.6 0 1.3.5 2.6 1.4 3.5.9.9 2.2 1.4 3.5 1.4s2.6-.5 3.5-1.4c.9-.9 1.4-2.2 1.4-3.5 0-1.6-.4-3.2-1.1-4.6-.6-1.3-1.7-2.6-2.5-3.9l-1.3-2.1c-.1-.1-.1-.2-.2-.3 0 0-.1-.1-.2-.1z" />
    </svg>
  </div>
);

const ChestIcon = () => (
  <div className="w-8 h-6 flex items-center justify-center">
    <svg viewBox="0 0 24 18" className="w-8 h-6" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="2" y="6" width="20" height="10" rx="2" />
      <path d="M2 10h20" />
      <rect x="10.5" y="9" width="3" height="4" rx="1" fill="currentColor" stroke="none" />
    </svg>
  </div>
);

const ChanceIcon = () => (
  <div className="w-9 h-9 flex items-center justify-center">
    <svg viewBox="0 0 24 24" className="w-8 h-8" fill="none" stroke="currentColor" strokeWidth="2.5">
      <circle cx="12" cy="12" r="9" />
      <path d="M9 9a3 3 0 016 0c0 2-3 2-3 4" strokeLinecap="round" />
      <circle cx="12" cy="18" r="1.4" fill="currentColor" stroke="none" />
    </svg>
  </div>
);

const TaxIcon = () => (
  <div className="font-black text-xl border-2 border-black w-8 h-8 flex items-center justify-center bg-gray-100 rounded-sm shadow-neo-sm text-neo-red relative overflow-hidden">
    <span className="z-10 relative">$</span>
    <div className="absolute inset-0 bg-[repeating-linear-gradient(45deg,transparent,transparent_2px,#000_2px,#000_3px)] opacity-10"></div>
  </div>
);

const HouseIndicator = () => (
  <div className="w-3 h-3 bg-neo-green border border-black shadow-[1px_1px_0_0_#000]" title="House" />
);

const HotelIndicator = () => (
  <div className="w-6 h-4 bg-neo-red border border-black shadow-[1px_1px_0_0_#000] flex items-center justify-center" title="Hotel">
    <div className="w-1 h-1 bg-white rounded-full mx-[1px]"></div>
    <div className="w-1 h-1 bg-white rounded-full mx-[1px]"></div>
    <div className="w-1 h-1 bg-white rounded-full mx-[1px]"></div>
  </div>
);

const FreeParkingIcon = () => (
  <svg viewBox="0 0 24 24" className="w-8 h-8" fill="none" stroke="currentColor" strokeWidth="2.2">
    <path d="M5 13l2-6h10l2 6" />
    <path d="M7 13h10v4H7z" />
    <circle cx="8" cy="18" r="1.3" fill="currentColor" stroke="none" />
    <circle cx="16" cy="18" r="1.3" fill="currentColor" stroke="none" />
  </svg>
);

const GoToJailIcon = () => (
  <svg viewBox="0 0 24 24" className="w-8 h-8" fill="none" stroke="currentColor" strokeWidth="2">
    <rect x="5" y="4" width="14" height="16" rx="2" />
    <path d="M9 4v16M12 4v16M15 4v16" />
  </svg>
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
      ? 'ring-[3px] ring-neo-yellow ring-offset-2 shadow-[0_0_0_2px_rgba(0,0,0,0.35)]'
      : highlightSource === 'deed'
        ? 'ring-[3px] ring-neo-pink ring-offset-2 shadow-[0_0_0_2px_rgba(0,0,0,0.35)]'
        : 'ring-[2px] ring-neo-cyan ring-offset-2 border-dashed'
    : '';

  if (space.index % 10 === 0) {
    return (
      <div
        className={cn(
          'relative w-full h-full border-2 border-neo-border bg-white flex flex-col items-center justify-center text-center select-none overflow-hidden group',
          highlightClass,
          className
        )}
      >
        {space.index === 0 && (
          <div className="w-full h-full bg-[#CEE6D0] relative flex items-center justify-center">
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,theme(colors.neo-green),transparent)] opacity-15"></div>
            <span className="absolute top-1 left-1 text-[8px] font-black transform -rotate-45 opacity-60">COLLECT<br />$200</span>
            <span className="text-4xl font-black text-neo-black tracking-tighter drop-shadow-[2px_2px_0_rgba(255,255,255,0.5)] transform -rotate-45 relative z-10">GO</span>
            <div className="absolute bottom-0 right-0 w-8 h-8 border-l-2 border-t-2 border-black bg-neo-green hover:bg-neo-green/90 transition-colors">
              <svg viewBox="0 0 24 24" stroke="currentColor" className="w-full h-full p-1 text-white" strokeWidth="3"><path d="M5 12h14m-7-7l7 7-7 7" /></svg>
            </div>
          </div>
        )}
        {space.index === 10 && (
          <div className="w-full h-full bg-[#F3D2C1] p-1 flex relative">
            <div className="w-2/3 h-full border-2 border-black bg-neo-orange flex items-center justify-center relative shadow-sm overflow-hidden">
              <div className="absolute inset-0 flex justify-evenly">
                <div className="w-0.5 h-full bg-black"></div>
                <div className="w-0.5 h-full bg-black"></div>
                <div className="w-0.5 h-full bg-black"></div>
              </div>
              <div className="absolute inset-0 flex items-center justify-center z-10">
                <div className="bg-neo-orange border border-black px-1 py-0.5 rotate-[-15deg] shadow-sm">
                  <span className="text-[7px] font-black">IN JAIL</span>
                </div>
              </div>
            </div>
            <div className="flex-1 flex items-center justify-center">
              <span className="text-[9px] font-bold text-center leading-none transform -rotate-90 whitespace-nowrap">JUST<br />VISITING</span>
            </div>
          </div>
        )}
        {space.index === 20 && (
          <div className="w-full h-full bg-[#FDF3C8] flex flex-col items-center justify-center p-1 relative">
            <div className="absolute top-1 rotate-12 bg-neo-red text-white text-[8px] font-black px-1 border border-black shadow-sm">FREE</div>
            <div className="mt-2 text-3xl font-black drop-shadow-sm">
              <FreeParkingIcon />
            </div>
            <span className="text-[9px] font-bold uppercase mt-1 tracking-tight">Parking</span>
          </div>
        )}
        {space.index === 30 && (
          <div className="w-full h-full bg-[#CFE1EA] flex flex-col items-center justify-center p-1 relative group-hover:bg-[#C6D9E3] transition-colors">
            <span className="text-[9px] font-bold uppercase mb-1">GO TO</span>
            <div className="w-10 h-10 border-2 border-black bg-neo-blue flex items-center justify-center shadow-neo-sm relative overflow-hidden">
              <div className="absolute inset-0 opacity-10 bg-[repeating-linear-gradient(45deg,black,black_1px,transparent_1px,transparent_4px)]"></div>
              <span className="text-2xl relative z-10">
                <GoToJailIcon />
              </span>
            </div>
            <span className="text-[9px] font-bold uppercase mt-1">JAIL</span>
          </div>
        )}
      </div>
    );
  }

  const bandStyle = hasColorBand
    ? {
        backgroundImage: `linear-gradient(180deg, ${groupColor} 0%, ${groupColor} 70%, rgba(0,0,0,0.1) 100%)`,
      }
    : undefined;

  return (
    <div
      className={cn(
        'relative flex flex-col border-[1.5px] border-neo-border bg-[#fbfaf7] h-full w-full select-none overflow-hidden',
        highlightClass,
        className
      )}
    >
      {hasColorBand ? (
        <div
          className={cn(
            'h-[24%] w-full border-b-[1.5px] border-black relative',
            "after:content-[''] after:absolute after:inset-0 after:bg-[url('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI0IiBoZWlnaHQ9IjQiPgo8cmVjdCB3aWR0aD0iNCIgaGVpZ2h0PSI0IiBmaWxsPSIjZmZmIiBmaWxsLW9wYWNpdHk9IjAuMSIvPgo8cGF0aCBkPSJNMSAzaDJ2MUgxVjN6bTIgMGgydjFIM1YzeiIgZmlsbD0iIzAwMCIgZmlsbC1vcGFjaXR5PSIwLjEiLz4KPC9zdmc+')] after:opacity-20"
          )}
          style={bandStyle}
        >
          <div className="absolute -bottom-1.5 inset-x-0 flex justify-center gap-0.5 z-10">
            {hotel && <HotelIndicator />}
            {!hotel && Array.from({ length: houses }).map((_, i) => (
              <HouseIndicator key={i} />
            ))}
          </div>
        </div>
      ) : (
        <div className="h-[10%]" />
      )}

      <div className="flex-1 flex flex-col items-center p-1 text-center w-full relative z-0">
        <span className="text-[8px] font-bold uppercase leading-tight tracking-tight line-clamp-3 mb-1 min-h-[2.2em]">
          {name}
        </span>

        <div className="flex-1 flex items-center justify-center scale-90 text-black">
          {isRailroad && <TrainIcon />}
          {isUtility && name.toLowerCase().includes('water') && <WaterIcon />}
          {isUtility && name.toLowerCase().includes('electric') && <BulbIcon />}
          {isChest && <ChestIcon />}
          {isChance && <ChanceIcon />}
          {isTax && <TaxIcon />}
        </div>

        {!owner_id && price !== null && (
          <span className="text-[8px] font-mono mt-auto pt-1 text-gray-600">{`$${price}`}</span>
        )}
      </div>

      {owner_id && (
        <div
          className="h-[5px] w-full border-t border-black absolute bottom-0 left-0"
          style={{ backgroundColor: ownerColor || 'black' }}
        />
      )}

      {mortgaged && (
        <div className="absolute inset-0 bg-white/90 backdrop-blur-[1px] flex items-center justify-center z-20">
          <div className="border-2 border-neo-red px-1 py-0.5 transform -rotate-12 bg-white shadow-sm">
            <span className="font-black text-[10px] text-neo-red uppercase tracking-wide block">MORTGAGED</span>
          </div>
        </div>
      )}
    </div>
  );
});

Tile.displayName = 'Tile';
