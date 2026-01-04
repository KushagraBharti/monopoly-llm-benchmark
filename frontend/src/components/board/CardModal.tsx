import { motion, AnimatePresence } from 'framer-motion';
import type { CardDefinition } from '@/domain/monopoly/cardData';
import { cn } from '@/components/ui/cn';

interface CardModalProps {
    isOpen: boolean;
    deck: 'CHANCE' | 'COMMUNITY_CHEST';
    card: CardDefinition;
    originOffset?: { x: number; y: number } | null;
    onClose?: () => void;
}

const ChanceIcon = () => (
    <svg viewBox="0 0 24 24" className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth="2.5">
        <path d="M9 9a3 3 0 016 0c0 2-3 2-3 4" strokeLinecap="round" />
        <circle cx="12" cy="18" r="1.4" fill="currentColor" stroke="none" />
        <circle cx="12" cy="12" r="9" stroke="currentColor" fill="none" />
    </svg>
);

const ChestIcon = () => (
    <svg viewBox="0 0 24 24" className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth="2">
        <rect x="3" y="8" width="18" height="10" rx="2" />
        <path d="M3 12h18" />
        <rect x="10.5" y="11" width="3" height="4" rx="1" fill="currentColor" stroke="none" />
    </svg>
);

export const CardModal = ({ isOpen, deck, card, originOffset, onClose }: CardModalProps) => {
    const isChance = deck === 'CHANCE';

    const primaryColor = isChance ? 'var(--color-neo-pink)' : 'var(--color-neo-blue)';
    const secondaryColor = isChance ? 'var(--color-neo-orange)' : 'var(--color-neo-cyan)';
    const Icon = isChance ? ChanceIcon : ChestIcon;
    const offsetX = originOffset?.x ?? 0;
    const offsetY = originOffset?.y ?? 0;

    return (
        <AnimatePresence mode="wait">
            {isOpen && (
                <motion.div
                    className="fixed inset-0 z-[70] flex items-center justify-center perspective-1000"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                >
                    <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" />

                    <motion.div
                        className="relative w-[340px] h-[210px] preserve-3d cursor-pointer"
                        initial={{ rotateY: 90, scale: 0.75, x: offsetX, y: offsetY }}
                        animate={{ rotateY: 0, scale: 1, x: 0, y: 0 }}
                        exit={{ rotateY: -90, scale: 0.8, opacity: 0 }}
                        transition={{ type: 'spring', stiffness: 110, damping: 16 }}
                        onClick={onClose}
                    >
                        <div
                            className={cn(
                                'absolute inset-0 bg-white border-4 border-black shadow-[10px_10px_0_0_rgba(0,0,0,1)] rounded-sm flex flex-col items-center text-center p-4 select-none'
                            )}
                        >
                            <div className="absolute inset-2 border border-black/10 pointer-events-none" />
                            <div className="absolute inset-0 opacity-5 bg-[repeating-linear-gradient(135deg,#000,#000_2px,transparent_2px,transparent_6px)]" />
                            <div
                                className="w-full flex justify-between items-center mb-2 border-b-2 border-black pb-1"
                                style={{ color: primaryColor }}
                            >
                                <span className="font-black uppercase tracking-tight text-sm">
                                    {isChance ? 'Chance' : 'Community Chest'}
                                </span>
                                <span className="text-xl leading-none">
                                    <Icon />
                                </span>
                            </div>

                            <div className="flex-1 flex flex-col justify-center items-center w-full">
                                <h3 className="font-black text-lg leading-tight uppercase mb-2">
                                    {card.title}
                                </h3>
                                <p className="font-mono text-[11px] leading-snug text-gray-700">
                                    {card.description}
                                </p>
                            </div>

                            <div className="w-full h-2 mt-2 bg-black" style={{ backgroundColor: secondaryColor }} />
                        </div>
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
    );
};
