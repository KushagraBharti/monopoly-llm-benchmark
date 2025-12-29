import { motion, AnimatePresence } from 'framer-motion';
import type { CardDefinition } from '@/domain/monopoly/cardData';
import { cn } from '@/components/ui/NeoPrimitive';

interface CardModalProps {
    isOpen: boolean;
    deck: 'CHANCE' | 'COMMUNITY_CHEST';
    card: CardDefinition;
    onClose?: () => void;
}

export const CardModal = ({ isOpen, deck, card, onClose }: CardModalProps) => {
    const isChance = deck === 'CHANCE';

    // Theme colors
    const primaryColor = isChance ? 'var(--color-neo-pink)' : 'var(--color-neo-blue)';
    const secondaryColor = isChance ? 'var(--color-neo-orange)' : 'var(--color-neo-cyan)';
    const icon = isChance ? "?" : "📦";

    return (
        <AnimatePresence mode="wait">
            {isOpen && (
                <motion.div
                    className="absolute inset-0 z-50 flex items-center justify-center perspective-1000"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                >
                    {/* Backdrop Blur */}
                    <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" />

                    {/* Card Container - Flip Effect */}
                    <motion.div
                        className="relative w-64 h-40 preserve-3d cursor-pointer"
                        initial={{ rotateY: 90, scale: 0.8 }}
                        animate={{ rotateY: 0, scale: 1 }}
                        exit={{ rotateY: -90, scale: 0.8, opacity: 0 }}
                        transition={{ type: "spring", stiffness: 100, damping: 15 }}
                        onClick={onClose}
                    >
                        <div
                            className={cn(
                                "absolute inset-0 bg-white border-4 border-black shadow-[8px_8px_0_0_rgba(0,0,0,1)] rounded-sm flex flex-col items-center text-center p-4 select-none",
                            )}
                        >
                            {/* Header */}
                            <div className="w-full flex justify-between items-start mb-2 border-b-2 border-black pb-1"
                                style={{ color: primaryColor }}
                            >
                                <span className="font-black uppercase tracking-tight text-sm">
                                    {isChance ? "Chance" : "Comm. Chest"}
                                </span>
                                <span className="text-xl leading-none">{icon}</span>
                            </div>

                            {/* Content */}
                            <div className="flex-1 flex flex-col justify-center items-center w-full">
                                <h3 className="font-bold text-lg leading-tight uppercase mb-2">
                                    {card.title}
                                </h3>
                                <p className="font-mono text-xs leading-snug">
                                    {card.description}
                                </p>
                            </div>

                            {/* Decorative Bottom Strip */}
                            <div className="w-full h-2 mt-2 bg-black opacity-10"
                                style={{ backgroundColor: secondaryColor, opacity: 1 }}
                            />
                        </div>
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
    );
};
