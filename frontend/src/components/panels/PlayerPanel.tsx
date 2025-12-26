import { useGameStore } from '../../state/store';
import { NeoCard, NeoBadge } from '../ui/NeoPrimitive';

export const PlayerPanel = () => {
    const snapshot = useGameStore((state) => state.snapshot);
    const players = snapshot?.players || [];
    const activePlayerId = snapshot?.active_player_id;

    // Sort by cash descending? Or just keep order? Keep order is usually better for tracking.
    // Maybe indicate active player.

    return (
        <NeoCard className="flex flex-col gap-4">
            <h3 className="text-xl">Players</h3>
            <div className="flex flex-col gap-2">
                {players.map((player) => (
                    <div
                        key={player.player_id}
                        className={`flex items-center justify-between p-2 border-2 ${player.player_id === activePlayerId
                                ? 'border-black bg-neo-yellow shadow-neo-sm'
                                : 'border-transparent bg-gray-100'
                            }`}
                    >
                        <div className="flex items-center gap-2">
                            {/* Avatar circle */}
                            <div className="w-6 h-6 rounded-full border border-black bg-white flex items-center justify-center font-bold text-xs">
                                {player.name[0]}
                            </div>
                            <span className="font-bold">{player.name}</span>
                            {player.in_jail && <NeoBadge variant="error">JAIL</NeoBadge>}
                        </div>

                        <div className="flex flex-col items-end">
                            <span className="font-mono font-bold">${player.cash}</span>
                            <span className="text-[10px] text-gray-500">Pos: {player.position}</span>
                        </div>
                    </div>
                ))}
                {players.length === 0 && <span className="opacity-50 italic">Waiting to start...</span>}
            </div>
        </NeoCard>
    );
};
