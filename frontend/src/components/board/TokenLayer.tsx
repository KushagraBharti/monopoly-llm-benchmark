import { motion } from 'framer-motion';
import { useGameStore } from '../../state/store';
import { getCSSPosition } from './utils';

// Deterministic pastel colors for players based on name/ID
const PLAYER_COLORS = [
    '#FF6B6B', // Red
    '#4ECDC4', // Teal
    '#FFE66D', // Yellow
    '#45B7D1', // Blue
    '#96CEB4', // Green
    '#D4A5A5', // Pink
];

export const TokenLayer = () => {
    const snapshot = useGameStore((state) => state.snapshot);
    const players = snapshot?.players || [];

    return (
        <div className="absolute inset-0 pointer-events-none z-10 overflow-hidden">
            {players.map((player, i) => {
                const { x, y } = getCSSPosition(player.position);

                // Offset logic for multiple players on same spot
                // Simple consistent jitter based on player ID
                const offsetHash = player.player_id.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
                const offsetX = (offsetHash % 20) - 10;
                const offsetY = (offsetHash % 15) - 7.5;

                // Calculate actual % position with offset
                // We act as if the parent 11x11 grid is the coordinate space
                // x, y are centers of tiles in %.

                return (
                    <motion.div
                        key={player.player_id}
                        initial={false}
                        animate={{
                            left: `calc(${x}% + ${offsetX}px)`,
                            top: `calc(${y}% + ${offsetY}px)`,
                        }}
                        transition={{
                            type: "spring",
                            stiffness: 60,
                            damping: 15,
                            mass: 1,
                        }}
                        className="absolute w-8 h-8 -ml-4 -mt-4 bg-white border-2 border-black rounded-full shadow-neo-sm flex items-center justify-center z-20"
                        style={{ backgroundColor: PLAYER_COLORS[i % PLAYER_COLORS.length] }}
                    >
                        <span className="font-bold text-xs text-black">{player.name[0]}</span>
                        {/* Outline ring if active player? */}
                        {snapshot?.active_player_id === player.player_id && (
                            <motion.div
                                className="absolute inset-0 rounded-full border-2 border-white"
                                animate={{ scale: [1, 1.3, 1] }}
                                transition={{ repeat: Infinity, duration: 1.5 }}
                            />
                        )}
                    </motion.div>
                );
            })}
        </div>
    );
};
