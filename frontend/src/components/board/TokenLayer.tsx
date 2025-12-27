import { motion } from 'framer-motion';
import { useGameStore } from '../../state/store';
import { getCSSPosition } from './utils';
import { getPlayerColor, getPlayerIndex, getPlayerInitials } from '../../domain/monopoly/colors';

export const TokenLayer = () => {
    const snapshot = useGameStore((state) => state.snapshot);
    const players = snapshot?.players || [];
    const activeId = snapshot?.active_player_id;

    // Group players by position for stacking
    const positionCounts = new Map<number, number>();
    players.forEach(p => {
        const count = positionCounts.get(p.position) || 0;
        positionCounts.set(p.position, count + 1);
    });

    const positionIndexes = new Map<number, number>();

    return (
        <div className="absolute inset-0 pointer-events-none z-20 overflow-visible">
            {players.map((player) => {
                const { x, y } = getCSSPosition(player.position);
                const color = getPlayerColor(player.player_id);
                const isActive = activeId === player.player_id;

                const playersAtPos = positionCounts.get(player.position) || 1;
                const indexAtPos = positionIndexes.get(player.position) || 0;
                positionIndexes.set(player.position, indexAtPos + 1);

                // Spiral/Cluster placement
                let offsetX = 0;
                let offsetY = 0;
                if (playersAtPos > 1) {
                    // Small jitter for "pile of chips" feel, consistent by index
                    const angle = (indexAtPos / playersAtPos) * 2 * Math.PI;
                    const radius = 8;
                    offsetX = Math.cos(angle) * radius;
                    offsetY = Math.sin(angle) * radius;
                }

                return (
                    <motion.div
                        key={player.player_id}
                        initial={false}
                        animate={{
                            left: `calc(${x}% + ${offsetX}px)`,
                            top: `calc(${y}% + ${offsetY}px)`,
                            scale: isActive ? 1.2 : 1,
                            zIndex: isActive ? 100 : 50 + indexAtPos,
                            y: isActive ? -5 : 0 // Physical "lift"
                        }}
                        transition={{
                            type: "spring",
                            stiffness: 120,
                            damping: 15,
                        }}
                        className="absolute w-0 h-0 flex items-center justify-center"
                    >
                        {/* Shadow blob */}
                        <div className="absolute w-6 h-2 bg-black/40 rounded-[100%] blur-[2px] translate-y-3 skew-x-12" />

                        {/* Chip Body */}
                        <div
                            className="relative w-7 h-7 rounded-full border-[2px] border-black flex items-center justify-center transition-shadow"
                            style={{
                                backgroundColor: color,
                                boxShadow: '0px 3px 0px 0px #000' // Material Thickness
                            }}
                        >
                            {/* Inner Rim */}
                            <div className="absolute inset-[3px] rounded-full border border-black/20 border-dashed opacity-50" />

                            <span className="font-black text-[9px] text-white drop-shadow-[0_1px_0_rgba(0,0,0,0.8)] select-none uppercase tracking-tighter">
                                {getPlayerInitials(player.player_id, player.name)}
                            </span>

                            {/* Active Shine */}
                            {isActive && (
                                <div className="absolute -top-1 -right-1 w-2 h-2 bg-white rounded-full animate-ping opacity-75" />
                            )}
                        </div>

                        {/* Label on Hover / Active (Optional tooltip) */}
                        {isActive && (
                            <motion.div
                                initial={{ opacity: 0, y: -10 }}
                                animate={{ opacity: 1, y: -24 }}
                                className="absolute bg-black text-white text-[8px] px-1.5 py-0.5 rounded-sm whitespace-nowrap z-50 pointer-events-auto"
                            >
                                {player.name}
                            </motion.div>
                        )}
                    </motion.div>
                );
            })}
        </div>
    );
};
