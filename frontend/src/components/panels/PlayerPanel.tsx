import { useMemo } from 'react';
import { useGameStore } from '../../state/store';
import { getPlayerColor, getPlayerInitials } from '../../domain/monopoly/colors';
import { selectLeaderboard } from '../../domain/monopoly/selectors';
import { NeoCard, NeoBadge } from '../ui/NeoPrimitive';

export const PlayerPanel = () => {
  const snapshot = useGameStore((state) => state.snapshot);
  const activePlayerId = snapshot?.active_player_id;
  const standings = useMemo(() => selectLeaderboard(snapshot), [snapshot]);

  return (
    <NeoCard className="flex flex-col gap-3">
      <div className="flex items-center justify-between border-b-2 border-black pb-1">
        <h3 className="text-xs font-bold uppercase">Players</h3>
        <span className="text-[9px] font-mono">{standings.length}</span>
      </div>
      <div className="flex flex-col gap-2">
        {standings.map((player) => (
          <div
            key={player.player_id}
            className={`flex items-center justify-between p-2 border-2 ${
              player.player_id === activePlayerId
                ? 'border-black bg-neo-yellow shadow-neo-sm'
                : 'border-transparent bg-gray-100'
            }`}
          >
            <div className="flex items-center gap-2">
              <div
                className="w-6 h-6 rounded-full border border-black flex items-center justify-center font-bold text-[10px] text-white"
                style={{ backgroundColor: getPlayerColor(player.player_id) }}
              >
                {getPlayerInitials(player.player_id, player.name)}
              </div>
              <div className="flex flex-col leading-tight">
                <span className="font-bold text-xs">{player.name}</span>
                <span className="text-[9px] text-gray-500 font-mono">
                  Props: {player.propertyCount}
                </span>
              </div>
              {player.inJail && <NeoBadge variant="error">JAIL</NeoBadge>}
              {player.bankrupt && <NeoBadge variant="warning">BK</NeoBadge>}
            </div>

            <div className="flex flex-col items-end">
              <span className="font-mono font-bold">${player.cash}</span>
              <span className="text-[9px] text-gray-500">
                Net: ${player.netWorthEstimate}
              </span>
            </div>
          </div>
        ))}
        {standings.length === 0 && <span className="opacity-50 italic">Waiting to start...</span>}
      </div>
    </NeoCard>
  );
};
