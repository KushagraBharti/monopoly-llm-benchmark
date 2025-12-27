import { memo, useMemo } from 'react';
import type { Space } from '../../net/contracts';
import { cn } from '../ui/NeoPrimitive';
import { getGroupColor, getPlayerColor } from '../../domain/monopoly/colors';

interface TileProps {
  space: Space;
  className?: string;
  highlightSource?: 'deed' | 'event' | 'decision' | null;
}

export const Tile = memo(({ space, className, highlightSource = null }: TileProps) => {
  const { name, kind, price, group, owner_id, houses, hotel, mortgaged } = space;

  const groupColor = useMemo(() => getGroupColor(group), [group]);
  const hasColorBand = !!group && groupColor !== 'transparent';

  // Detect special types (case-insensitive for safety)
  const groupUpper = group?.toUpperCase() || '';
  const isRailroad = kind === 'RAILROAD' || groupUpper === 'RAILROAD';
  const isUtility = kind === 'UTILITY' || groupUpper === 'UTILITY';

  const ownerColor = useMemo(() => {
    if (!owner_id) return null;
    return getPlayerColor(owner_id);
  }, [owner_id]);

  // Corner Logic - special landmark tiles
  const isCorner = space.index % 10 === 0;
  const highlightStyle = highlightSource
    ? {
        borderColor:
          highlightSource === 'deed'
            ? 'var(--color-neo-pink)'
            : highlightSource === 'event'
              ? 'var(--color-neo-yellow)'
              : 'var(--color-neo-cyan)',
        borderStyle: highlightSource === 'decision' ? 'dashed' : 'solid',
      }
    : undefined;

  if (isCorner) {
    const cornerStyles: Record<number, { bg: string; accent: string }> = {
      0: { bg: 'bg-gradient-to-br from-green-100 to-green-200', accent: 'text-green-700' },
      10: { bg: 'bg-gradient-to-br from-orange-100 to-orange-200', accent: 'text-orange-700' },
      20: { bg: 'bg-gradient-to-br from-red-100 to-red-200', accent: 'text-red-700' },
      30: { bg: 'bg-gradient-to-br from-slate-100 to-slate-300', accent: 'text-slate-700' },
    };
    const style = cornerStyles[space.index] || { bg: 'bg-white', accent: 'text-black' };

    return (
      <div
        className={cn(
          'relative w-full h-full border-3 border-black flex flex-col items-center justify-center p-1 text-center overflow-hidden shadow-inner',
          style.bg,
          className
        )}
      >
        {highlightSource && (
          <div
            className={cn(
              'absolute inset-0 pointer-events-none border-[3px] z-30',
              highlightSource === 'event' && 'animate-pulse'
            )}
            style={highlightStyle}
          />
        )}
        {space.index === 0 && (
          <>
            <div className="absolute top-0 left-0 w-6 h-6 bg-green-500 flex items-center justify-center">
              <span className="text-white text-[8px] font-bold">GO</span>
            </div>
            <span className="text-3xl leading-none drop-shadow-sm">GO</span>
            <span className={cn('font-black text-lg mt-1 tracking-tight', style.accent)}>GO</span>
            <span className="text-[8px] font-bold bg-green-600 text-white px-1.5 py-0.5 mt-0.5">
              COLLECT $200
            </span>
          </>
        )}

        {space.index === 10 && (
          <>
            <div className="absolute inset-1 border-4 border-orange-300 border-dashed rounded-sm" />
            <span className="text-2xl">J</span>
            <span className={cn('font-black text-sm mt-1', style.accent)}>JAIL</span>
            <span className="text-[8px] font-mono opacity-60">Just Visiting</span>
          </>
        )}

        {space.index === 20 && (
          <>
            <span className="text-2xl">P</span>
            <span className={cn('font-black text-[11px] leading-tight mt-1 uppercase', style.accent)}>
              FREE<br />PARKING
            </span>
          </>
        )}

        {space.index === 30 && (
          <>
            <span className="text-2xl">GJ</span>
            <span className={cn('font-black text-[10px] mt-1 bg-black text-white px-1.5 py-0.5')}>
              GO TO JAIL
            </span>
            <span className="text-[8px] font-mono opacity-60 mt-0.5">Do not pass GO</span>
          </>
        )}
      </div>
    );
  }

  return (
    <div
      className={cn(
        'relative flex flex-col border-2 border-black bg-neo-bg h-full w-full select-none overflow-hidden transition-all hover:scale-[1.02] hover:shadow-lg group',
        className
      )}
    >
      {highlightSource && (
        <div
          className={cn(
            'absolute inset-0 pointer-events-none border-[3px] z-30',
            highlightSource === 'event' && 'animate-pulse'
          )}
          style={highlightStyle}
        />
      )}
      {hasColorBand && (
        <div
          className="h-[28%] w-full border-b-2 border-black flex items-center justify-center relative"
          style={{ backgroundColor: groupColor }}
        >
          {isRailroad && <span className="text-white drop-shadow-md text-lg">RR</span>}
          {isUtility && (
            <span className="text-white drop-shadow-md text-lg">
              {name.toLowerCase().includes('electric') ? 'EL' : 'WW'}
            </span>
          )}

          <div className="absolute -bottom-1.5 flex gap-0.5 justify-center w-full px-0.5">
            {hotel && (
              <div
                className="w-5 h-4 bg-red-600 border-2 border-black shadow-[1px_1px_0px_0px_rgba(0,0,0,1)] z-10"
                title="Hotel"
              />
            )}
            {!hotel &&
              Array.from({ length: houses }).map((_, i) => (
                <div
                  key={i}
                  className="w-3 h-3 bg-neo-green border-2 border-black shadow-[1px_1px_0px_0px_rgba(0,0,0,1)] z-10"
                  title="House"
                />
              ))}
          </div>
        </div>
      )}

      <div className="flex-1 flex flex-col items-center justify-between pt-2 px-0.5 text-center w-full bg-white relative">
        <span className="text-[8px] md:text-[9px] font-bold leading-[1.1] uppercase tracking-tight px-1 text-center break-words max-h-[24px] overflow-hidden">
          {name}
        </span>

        {!owner_id && price !== null && (
          <span className="mb-1 text-[8px] font-mono text-gray-500">${price}</span>
        )}
      </div>

      {owner_id && (
        <div
          className="h-3 w-full border-t-2 border-black flex items-center justify-center relative"
          style={{ backgroundColor: ownerColor || 'black' }}
          title={`Owned by ${owner_id}`}
        />
      )}

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
});

Tile.displayName = 'Tile';
