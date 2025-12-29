import { motion, AnimatePresence } from 'framer-motion';
import type { Space } from '@/net/contracts';
import { getGroupColor } from '@/domain/monopoly/colors';

interface PropertyToastProps {
    isVisible: boolean;
    space: Space;
    method: 'BOUGHT' | 'WON' | 'TRADED';
    price?: number | null;
}

export const PropertyToast = ({ isVisible, space, method, price }: PropertyToastProps) => {
    const groupColor = getGroupColor(space.group);

    return (
        <AnimatePresence>
            {isVisible && (
                <motion.div
                    className="absolute top-1/4 left-1/2 -translate-x-1/2 z-50 pointer-events-none"
                    initial={{ y: 50, scale: 0.5, opacity: 0 }}
                    animate={{ y: 0, scale: 1, opacity: 1 }}
                    exit={{ x: 300, scale: 0.2, opacity: 0, transition: { duration: 0.5 } }} // Fly to right panel
                    transition={{ type: "spring", stiffness: 200, damping: 20 }}
                >
                    <div className="bg-white border-2 border-black shadow-[6px_6px_0_0_rgba(0,0,0,1)] p-1 w-48 rounded-sm">
                        {/* Title Bar */}
                        <div
                            className="w-full h-8 mb-2 border border-black flex items-center justify-center font-bold uppercase text-[10px] tracking-tight"
                            style={{ backgroundColor: groupColor }}
                        >
                            {space.kind === 'PROPERTY' ? 'Title Deed' : space.name}
                        </div>

                        {/* Body */}
                        <div className="text-center">
                            <h3 className="text-sm font-black uppercase leading-tight mb-2 px-1">
                                {space.name}
                            </h3>

                            <div className="border-t border-black pt-1 mt-1">
                                <span className="text-[9px] font-bold bg-black text-white px-1.5 py-0.5 rounded-sm uppercase">
                                    {method}
                                </span>
                                {price && (
                                    <span className="block mt-1 font-mono text-xs">
                                        -${price}
                                    </span>
                                )}
                            </div>
                        </div>
                    </div>
                </motion.div>
            )}
        </AnimatePresence>
    );
};
