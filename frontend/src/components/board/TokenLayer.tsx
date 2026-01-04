import { motion } from 'framer-motion';
import { useGameStore } from '@/state/store';
import { getCSSPosition } from '@/components/board/utils';
import { getPlayerTokenSrc } from '@/domain/monopoly/colors';
import { cn } from '@/components/ui/cn';

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
        <div className="absolute inset-0 pointer-events-none z-30 overflow-visible">
            {players.map((player) => {
                const { x, y } = getCSSPosition(player.position);
                const tokenSrc = getPlayerTokenSrc(player.player_id);
                const isActive = activeId === player.player_id;

                const playersAtPos = positionCounts.get(player.position) || 1;
                const indexAtPos = positionIndexes.get(player.position) || 0;
                positionIndexes.set(player.position, indexAtPos + 1);

                // Cluster placement
                let offsetX = 0;
                let offsetY = 0;
                if (playersAtPos > 1) {
                    const angle = (indexAtPos / playersAtPos) * 2 * Math.PI;
                    const radius = 14; // Increased separation
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
                            // Scale active player slightly, but no pulsing
                            scale: isActive ? 1.06 : 1.0,
                            zIndex: isActive ? 100 : 50 + indexAtPos,
                            y: isActive ? -10 : 0,
                        }}
                        transition={{
                            type: "spring",
                            stiffness: 150,
                            damping: 18,
                        }}
                        className="absolute w-0 h-0 flex items-center justify-center"
                    >
                        <div
                            className={cn("relative w-10 h-10 shrink-0")}
                            style={{
                                filter: isActive
                                    ? 'drop-shadow(0px 0px 10px rgba(255, 242, 0, 0.9)) drop-shadow(0px 6px 0px rgba(0,0,0,1))'
                                    : 'drop-shadow(0px 6px 0px rgba(0,0,0,1))',
                            }}
                        >
                            <img
                                src={tokenSrc}
                                alt={player.name ? `${player.name} token` : `${player.player_id} token`}
                                className="block w-full h-full object-contain select-none pointer-events-none"
                                draggable={false}
                            />
                        </div>
                    </motion.div>
                );
            })}
        </div>
    );
};
