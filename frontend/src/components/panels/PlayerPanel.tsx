import { useMemo } from 'react';
import { useGameStore } from '../../state/store';
import { getPlayerColor, getPlayerInitials } from '../../domain/monopoly/colors';
import { selectLeaderboard } from '../../domain/monopoly/selectors';
import { NeoCard, cn } from '../ui/NeoPrimitive';

export const PlayerPanel = () => {
  const snapshot = useGameStore((state) => state.snapshot);
  const activePlayerId = snapshot?.active_player_id;
  const standings = useMemo(() => selectLeaderboard(snapshot), [snapshot]);

  return (
    <NeoCard className="flex flex-col gap-0 border-neo-border shadow-neo overflow-hidden bg-white">
      <div className="flex items-center justify-between border-b-2 border-black bg-neo-bg px-2 py-1">
        <h3 className="text-[10px] font-black uppercase tracking-wider">Players</h3>
        <span className="text-[9px] font-mono bg-black text-white px-1 rounded-sm leading-none">{standings.length}</span>
      </div>
      <div className="flex flex-col divide-y-2 divide-black bg-white">
        {standings.map((player, idx) => {
          const isActive = player.player_id === activePlayerId;
          return (
            <div
              key={player.player_id}
              className={cn(
                "flex items-center justify-between px-2 py-1 transition-all relative",
                isActive ? "bg-neo-yellow/30" : "hover:bg-gray-50"
              )}
            >
              {isActive && (
                <div className="absolute left-0 top-0 bottom-0 w-1 bg-neo-black animate-pulse" />
              )}

              <div className="flex items-center gap-1.5 pl-1">
                <span className="font-mono text-[9px] text-gray-400 w-3">#{idx + 1}</span>
                <div
                  className="w-5 h-5 rounded-full border border-black flex items-center justify-center font-black text-[9px] text-white shadow-[1px_1px_0_0_#000]"
                  style={{ backgroundColor: getPlayerColor(player.player_id) }}
                >
                  {getPlayerInitials(player.player_id, player.name)}
                </div>
                <div className="flex flex-col leading-none">
                  <span className="font-bold text-[9px] uppercase truncate max-w-[70px]">{player.name}</span>
                  {(player.inJail || player.bankrupt) && (
                    <div className="flex gap-1 mt-0.5">
                      {player.inJail && <span className="bg-neo-orange text-white text-[6px] px-1 font-bold">JAIL</span>}
                      {player.bankrupt && <span className="bg-neo-red text-white text-[6px] px-1 font-bold">DEAD</span>}
                    </div>
                  )}
                </div>
              </div>

              <div className="flex flex-col items-end leading-none">
                <span className={cn("font-mono font-bold text-[11px] tracking-tight", player.bankrupt ? 'line-through opacity-50' : '')}>
                  ${player.cash}
                </span>
                <div className="flex gap-1 mt-0.5">
                  <span className="text-[7px] text-gray-500 font-mono">
                    NW:${player.netWorthEstimate}
                  </span>
                  <span className="text-[7px] font-bold uppercase text-gray-400">
                    {player.propertyCount}P
                  </span>
                </div>
              </div>
            </div>
          );
        })}
        {standings.length === 0 && (
          <div className="p-2 text-center opacity-50 italic text-[10px]">Waiting to start...</div>
        )}
      </div>
    </NeoCard>
  );
};
