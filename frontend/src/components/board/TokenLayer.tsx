import { motion } from 'framer-motion';
import { useGameStore } from '../../state/store';
import { getCSSPosition } from './utils';
import { getPlayerColor, getPlayerIndex } from './constants';

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

    // Track which players we've placed at each position
    const positionIndexes = new Map<number, number>();

    return (
        <div className="absolute inset-0 pointer-events-none z-20 overflow-visible">
            {players.map((player) => {
                const { x, y } = getCSSPosition(player.position);
                const color = getPlayerColor(player.player_id);
                const isActive = activeId === player.player_id;

                // Deterministic offset based on player index at this position
                const playersAtPos = positionCounts.get(player.position) || 1;
                const indexAtPos = positionIndexes.get(player.position) || 0;
                positionIndexes.set(player.position, indexAtPos + 1);

                // Spread tokens in a circle pattern for cleaner stacking
                let offsetX = 0;
                let offsetY = 0;
                if (playersAtPos > 1) {
                    const angle = (indexAtPos / playersAtPos) * 2 * Math.PI - Math.PI / 2;
                    const radius = 10 + (playersAtPos > 4 ? 4 : 0);
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
                            scale: isActive ? 1.25 : 1,
                            zIndex: isActive ? 50 : 20 + getPlayerIndex(player.player_id),
                        }}
                        transition={{
                            type: "spring",
                            stiffness: 100,
                            damping: 15,
                            mass: 0.6,
                        }}
                        className="absolute -ml-3 -mt-3"
                    >
                        {/* The Token Itself */}
                        <div
                            className="relative w-6 h-6 rounded-full border-2 border-black flex items-center justify-center shadow-[2px_2px_0px_0px_rgba(0,0,0,0.5)]"
                            style={{ backgroundColor: color }}
                        >
                            <span className="font-black text-[10px] text-white drop-shadow-md select-none">
                                {player.name?.[0]?.toUpperCase() || player.player_id.replace('player_', '').replace('p', '')}
                            </span>

                            {/* Active Player Indicator Ring */}
                            {isActive && (
                                <motion.div
                                    className="absolute -inset-1.5 rounded-full border-2 border-black"
                                    style={{ borderColor: color }}
                                    animate={{
                                        scale: [1, 1.3, 1],
                                        opacity: [0.8, 0.2, 0.8]
                                    }}
                                    transition={{
                                        repeat: Infinity,
                                        duration: 1.2,
                                        ease: "easeInOut"
                                    }}
                                />
                            )}
                        </div>
                    </motion.div>
                );
            })}
        </div>
    );
};
