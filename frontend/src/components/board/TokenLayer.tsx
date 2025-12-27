import { motion } from 'framer-motion';
import { useGameStore } from '../../state/store';
import { getCSSPosition } from './utils';
import { getPlayerColor } from './constants';

export const TokenLayer = () => {
    const snapshot = useGameStore((state) => state.snapshot);
    const players = snapshot?.players || [];
    const activeId = snapshot?.active_player_id;

    return (
        <div className="absolute inset-0 pointer-events-none z-20 overflow-visible">
            {players.map((player) => {
                const { x, y } = getCSSPosition(player.position);
                const color = getPlayerColor(player.player_id);
                const isActive = activeId === player.player_id;

                // Offset logic for multiple players on same spot
                const offsetHash = player.player_id.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
                const offsetX = (offsetHash % 24) - 12; // slightly more spread
                const offsetY = (offsetHash % 24) - 12;

                return (
                    <motion.div
                        key={player.player_id}
                        initial={false}
                        animate={{
                            left: `calc(${x}% + ${offsetX}px)`,
                            top: `calc(${y}% + ${offsetY}px)`,
                            scale: isActive ? 1.2 : 1,
                            zIndex: isActive ? 50 : 20,
                        }}
                        transition={{
                            type: "spring",
                            stiffness: 80,
                            damping: 15,
                            mass: 0.8,
                        }}
                        className="absolute -ml-3 -mt-3"
                    >
                        {/* The Token Itself */}
                        <div
                            className="relative w-6 h-6 rounded-full border-2 border-black flex items-center justify-center shadow-[2px_2px_0px_0px_rgba(0,0,0,0.5)] bg-white"
                            style={{ backgroundColor: color }}
                        >
                            <span className="font-black text-[10px] text-white drop-shadow-md select-none">
                                {player.player_id.replace('player_', '')}
                            </span>

                            {/* Active Player Indicator Ring */}
                            {isActive && (
                                <motion.div
                                    className="absolute -inset-2 rounded-full border-2 border-black opacity-50"
                                    animate={{ scale: [1, 1.4, 1], opacity: [0.8, 0, 0.8] }}
                                    transition={{ repeat: Infinity, duration: 1.5, ease: "easeInOut" }}
                                />
                            )}
                        </div>
                    </motion.div>
                );
            })}
        </div>
    );
};
