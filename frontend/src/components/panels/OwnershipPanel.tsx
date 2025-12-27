import { useMemo, useState } from 'react';
import type { Space } from '../../net/contracts';
import { useGameStore } from '../../state/store';
import { getGroupColor, getPlayerColor } from '../../domain/monopoly/colors';
import { selectOwnershipGroups } from '../../domain/monopoly/selectors';
import { NeoBadge, NeoCard, cn } from '../ui/NeoPrimitive';

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
        'relative flex flex-col border-2 border-black h-14 w-11 text-[8px] text-center bg-white transition-transform hover:scale-105 cursor-pointer shadow-neo-sm',
        isSelected && 'outline outline-2 outline-black',
        tile.mortgaged && 'opacity-60 grayscale'
      )}
      title={`${tile.name}${tile.owner_id ? ` (Owned by ${tile.owner_id})` : ''}`}
    >
      <div
        className="h-2 w-full border-b border-black"
        style={{ backgroundColor: getGroupColor(tile.group) }}
      />

      <div className="flex-1 flex flex-col justify-center items-center leading-none p-0.5 relative">
        <span className="uppercase font-bold text-[7px] leading-[1.1] break-words px-0.5">
          {label}
        </span>

        <div className="flex gap-0.5 mt-1">
          {tile.hotel && <div className="w-2 h-2 bg-red-600 border border-black" />}
          {!tile.hotel &&
            Array.from({ length: tile.houses }).map((_, i) => (
              <div key={i} className="w-1.5 h-1.5 bg-green-500 border border-black rounded-full" />
            ))}
        </div>

        {tile.mortgaged && (
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-red-600 font-bold -rotate-45 opacity-80 text-[8px]">M</span>
          </div>
        )}
      </div>

      {ownerColor && (
        <div className="h-1.5 w-full border-t border-black" style={{ backgroundColor: ownerColor }} />
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
    <NeoCard className="flex flex-col gap-2 p-2 max-h-full overflow-y-auto">
      <div className="flex items-center justify-between border-b-2 border-black pb-1">
        <h3 className="text-xs font-bold uppercase">Property Deeds</h3>
        {filterPlayerId && (
          <button
            type="button"
            onClick={() => setFilterPlayerId(null)}
            className="text-[9px] font-mono underline"
          >
            Clear
          </button>
        )}
      </div>

      <div className="flex flex-wrap gap-1">
        <button
          type="button"
          onClick={() => setFilterPlayerId(null)}
          className={cn(
            'px-2 py-0.5 text-[9px] font-bold uppercase border-2 border-black',
            filterPlayerId === null ? 'bg-black text-white shadow-neo-sm' : 'bg-white'
          )}
        >
          All
        </button>
        {players.map((player) => (
          <button
            key={player.player_id}
            type="button"
            onClick={() => setFilterPlayerId(player.player_id)}
            className={cn(
              'px-2 py-0.5 text-[9px] font-bold uppercase border-2 border-black text-white',
              filterPlayerId === player.player_id ? 'shadow-neo-sm' : 'opacity-80'
            )}
            style={{ backgroundColor: getPlayerColor(player.player_id) }}
          >
            {player.name}
          </button>
        ))}
      </div>

      <div className="space-y-2">
        {groups.map((group) => (
          <div key={group.key} className="border-2 border-black bg-white p-1 shadow-neo-sm">
            <div className="flex items-center justify-between gap-2 mb-1">
              <div className="flex items-center gap-1">
                <span
                  className="w-3 h-3 border border-black"
                  style={{ backgroundColor: group.color }}
                />
                <span className="text-[10px] font-bold uppercase">{group.label}</span>
              </div>
              <div className="flex items-center gap-1">
                <span className="text-[9px] font-mono">
                  {(filterPlayerId ? group.ownedByPlayerCount ?? 0 : group.ownedCount)}/{group.totalCount}
                </span>
                {group.isComplete && group.monopolyOwnerId && (
                  <NeoBadge
                    variant="success"
                    className="text-[8px]"
                    style={{ backgroundColor: getPlayerColor(group.monopolyOwnerId), color: 'white' }}
                  >
                    MONO
                  </NeoBadge>
                )}
              </div>
            </div>

            <div className="flex gap-1 flex-wrap justify-center">
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
          <div className="text-xs italic text-gray-500 text-center py-4">
            No properties for the current filter.
          </div>
        )}
      </div>
    </NeoCard>
  );
};
