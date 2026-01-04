import { useMemo, useState } from 'react';
import type { Space } from '@/net/contracts';
import { useGameStore } from '@/state/store';
import { getGroupColor, getPlayerColor } from '@/domain/monopoly/colors';
import { selectOwnershipGroups } from '@/domain/monopoly/selectors';
import { NeoCard } from '@/components/ui/NeoPrimitive';
import { cn } from '@/components/ui/cn';

const formatMiniLabel = (name: string): string => {
  const cleaned = name
    .replace(/\b(Avenue|Street|Place|Railroad|Company|Gardens|Park|Line|Works)\b/gi, '')
    .replace(/\s+/g, ' ')
    .trim();
  const base = cleaned.length > 0 ? cleaned : name;
  const words = base.split(' ');
  const short = words.slice(0, 2).join(' ');
  return short.length > 8 ? short.slice(0, 8) : short;
};

type MiniTileProps = {
  tile: Space;
  isSelected: boolean;
  onSelect: () => void;
};

const MiniTile = ({ tile, isSelected, onSelect }: MiniTileProps) => {
  const ownerColor = tile.owner_id ? getPlayerColor(tile.owner_id) : null;
  const label = formatMiniLabel(tile.name);

  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        'relative flex flex-col border-[1.5px] border-black h-14 w-11 text-[8px] text-center bg-white transition-all cursor-pointer overflow-hidden',
        isSelected
          ? 'scale-110 shadow-neo-lg z-10 ring-2 ring-neo-pink'
          : 'hover:scale-105 shadow-neo-sm hover:shadow-neo',
        tile.mortgaged && 'opacity-60 grayscale'
      )}
      title={`${tile.name}${tile.owner_id ? ` (Owned by ${tile.owner_id})` : ''}`}
    >
      <div
        className="h-2.5 w-full border-b-[1.5px] border-black shrink-0"
        style={{ backgroundColor: getGroupColor(tile.group) }}
      />

      <div className="flex-1 flex flex-col justify-between items-center p-0.5 w-full">
        <span className="uppercase font-bold text-[7px] leading-[0.95] tracking-tight break-words w-full line-clamp-2">
          {label}
        </span>

        <div className="flex gap-0.5 mb-0.5">
          {tile.hotel && <div className="w-2 h-2 bg-neo-red border border-black" />}
          {!tile.hotel &&
            Array.from({ length: tile.houses }).map((_, i) => (
              <div key={i} className="w-1.5 h-1.5 bg-neo-green border border-black" />
            ))}
        </div>

        {tile.mortgaged && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/40">
            <span className="text-neo-red font-black -rotate-45 text-[8px] border border-neo-red px-0.5 bg-white">M</span>
          </div>
        )}
      </div>

      {ownerColor && (
        <div className="h-1.5 w-full border-t border-black shrink-0" style={{ backgroundColor: ownerColor }} />
      )}
    </button>
  );
};

export const OwnershipPanel = () => {
  const snapshot = useGameStore((state) => state.snapshot);
  const deedHighlight = useGameStore((state) => state.ui.deedHighlight);
  const setDeedHighlight = useGameStore((state) => state.setDeedHighlight);
  const players = snapshot?.players ?? [];
  const [filterPlayerId, setFilterPlayerId] = useState<string | null>(null);

  const groups = useMemo(
    () => selectOwnershipGroups(snapshot, filterPlayerId),
    [snapshot, filterPlayerId]
  );

  if (!snapshot) return null;

  return (
    <NeoCard className="flex flex-col gap-0 border-neo-border shadow-neo overflow-hidden h-full min-h-0 bg-white">
      <div className="flex flex-col border-b-2 border-black bg-white p-2 gap-2 shadow-sm z-10">
        <div className="flex justify-between items-center">
          <h3 className="text-xs font-black uppercase tracking-wider">Deeds</h3>
          {filterPlayerId && (
            <button onClick={() => setFilterPlayerId(null)} className="text-[9px] font-bold underline hover:text-neo-blue">
              Show All
            </button>
          )}
        </div>

        {/* Filter Chips */}
        <div className="flex flex-wrap gap-1">
          <button
            onClick={() => setFilterPlayerId(null)}
            className={cn(
              "px-2 py-0.5 text-[8px] font-bold uppercase border border-black transition-all",
              filterPlayerId === null
                ? "bg-black text-white shadow-[1px_1px_0_0_rgba(0,0,0,0.5)]"
                : "bg-white hover:bg-gray-100"
            )}
          >
            ALL
          </button>
          {players.map(p => (
            <button
              key={p.player_id}
              onClick={() => setFilterPlayerId(p.player_id)}
              className={cn(
                "px-2 py-0.5 text-[8px] font-bold uppercase border border-black transition-all text-white shadow-[1px_1px_0_0_rgba(0,0,0,1)]",
                filterPlayerId === p.player_id ? "opacity-100 scale-105" : "opacity-60 hover:opacity-100"
              )}
              style={{ backgroundColor: getPlayerColor(p.player_id) }}
            >
              {p.name}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto brutal-scroll p-2 space-y-3 bg-white">
        {groups.map((group) => (
          <div key={group.key}>
            <div className="flex items-center gap-2 mb-1 pl-1">
              <span className="w-2 h-2 border border-black shadow-[1px_1px_0_0_#000]" style={{ backgroundColor: group.color }} />
              <span className="text-[9px] font-black uppercase text-gray-700">{group.label}</span>
              <div className="h-[1px] flex-1 bg-black/10" />
            </div>

            <div className="flex gap-1.5 flex-wrap pl-1">
              {group.tiles.map((tile) => (
                <MiniTile
                  key={tile.index}
                  tile={tile}
                  isSelected={deedHighlight === tile.index}
                  onSelect={() =>
                    setDeedHighlight(deedHighlight === tile.index ? null : tile.index)
                  }
                />
              ))}
            </div>
          </div>
        ))}

        {groups.length === 0 && (
          <div className="text-center py-8 opacity-50 text-[10px] font-mono">
            No properties found.
          </div>
        )}
      </div>
    </NeoCard>
  );
};
