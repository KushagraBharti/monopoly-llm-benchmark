import { motion } from 'framer-motion';
import { useGameStore } from '@/state/store';
import { getCSSPosition } from '@/components/board/utils';
import { getPlayerColor, getPlayerInitials } from '@/domain/monopoly/colors';
import { cn } from '@/components/ui/NeoPrimitive';

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
                const color = getPlayerColor(player.player_id);
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
                        {/* Shadow blob */}
                        <div className="absolute w-9 h-3 bg-black/35 rounded-[100%] blur-[2px] translate-y-4 skew-x-12" />

                        {/* Chip Body - Larger and thicker */}
                        <div
                            className={cn(
                                "relative w-10 h-10 rounded-full border-[3px] bg-white flex items-center justify-center transition-shadow",
                                isActive ? "ring-4 ring-neo-yellow ring-offset-2 ring-offset-white" : ""
                            )}
                            style={{
                                backgroundColor: color,
                                borderColor: 'black',
                                boxShadow: isActive
                                    ? '0px 0px 0px 2px rgba(0,0,0,0.5), 0px 10px 18px rgba(0,0,0,0.35)'
                                    : '0px 6px 0px 0px #000'
                            }}
                        >
                            <span className="font-black text-[12px] text-white drop-shadow-[0_1.5px_0_rgba(0,0,0,1)] select-none uppercase tracking-tighter">
                                {getPlayerInitials(player.player_id, player.name)}
                            </span>
                        </div>
                    </motion.div>
                );
            })}
        </div>
    );
};
